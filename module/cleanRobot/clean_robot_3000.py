# -*- coding: utf-8 -*-
# @Date: 2024/06/24
# @Author: zhong
# @Version: 1.4
# @Project: SRC3000 清洁机器人
# @Coding: https://seer-group.coding.net/p/robokit/assignments/issues/2631/detail
# @Update: 更新了开机复位，水位满足时自动清除水位报错
# @Doc: https://seer-group.feishu.cn/wiki/PPFjwE99KitmUSk22rpcJAkYnDe?fromScene=spaceOverview
import sys
import time
import can
from enum import IntEnum
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp
import os
sys.path.append(os.path.dirname(__file__) + "/syspy")
sys.path.append("../syspy")
sys.path.append("../../genetic")
import json
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import ModuleTool

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "",
        "default_value":["WashStart", "WashEnd", "DustStart", "DustEnd", "AddWater", "CheckInfo"],
        "tips": "操作选项",
        "type": "complex"
    },
    "auto_adjust":{
        "value": 1,
        "tips": "是否启动电机功率自动调节模式, 1: 启动, 0: 不启动, 参数可缺省",
        "type": "int"
    },
    "brush_power":{
        "value": 67,
        "tips": "刷盘电机功率, 取值: 0-100, 0即关闭，100即满功率, 参数可缺省",
        "type": "int"
    },
    "suck_power":{
        "value": 50,
        "tips": "吸风电机功率, 取值: 0-100, 0即关闭, 100即满功率, 参数可缺省",
        "type": "int"
    },
    "jet_power":{
        "value": 20,
        "tips": "喷水电机功率, 取值: 0-100, 0即关闭, 100即满功率, 参数可缺省",
        "type": "int"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.min_clean_water_level = p.loadParam("min_clean_water_level", type="float", default=5.0,
                                                 comment="清水液位最小值，达到此值机器人停止工作去加水")
        self.max_clean_water_level = p.loadParam("max_clean_water_level", type="float", default=95.0,
                                                 comment="清水液位最大值，达到此值机器人停止加水")
        self.min_waste_water_level = p.loadParam("min_waste_water_level", type="float", default=1.0,
                                                 comment="污水液位最小值，达到此值机器人停止排污")
        self.max_waste_water_level = p.loadParam("max_waste_water_level", type="float", default=90.0,
                                                 comment="污水液位最大值，达到此值机器人停止工作去排污")
        self.add_water_do = p.loadParam("add_water_do", type="int", default=4, comment="加水DO")
        self.brush_power = p.loadParam("brush_power", type="int", default=67, comment="刷盘电机默认功率")
        self.suck_power = p.loadParam("suck_power", type="int", default=50, comment="吸风电机默认功率")
        self.jet_power = p.loadParam("jet_power", type="int", default=20, comment="喷水泵电机默认功率")
        self.auto_adjust_power = p.loadParam("auto_adjust_power", type="int", default=1,
                                             comment="是否启动电机功率自动调节模式, 1: 启动， 0: 不启动")
        self.add_water_delay_time = p.loadParam("add_water_delay_time", type="float", default=5.0,
                                                comment="加水延时关闭时间")
        self.close_jet_delay_time = p.loadParam("close_jet_delay_time", type="float", default=5.0,
                                                comment="关闭喷水电机后延时停止清洁工作的时间")
        self.high_mode_x_speed = p.loadParam("high_mode_x_speed", type="float", default=0.8,
                                             comment="x速度大于该值时, 清洁机构以高功率工作")
        self.std_mode_x_speed = p.loadParam("std_mode_x_speed", type="float", default=0.4,
                                            comment="x速度大于该值时, 清洁机构以标准功率工作")
        self.stop_x_speed = p.loadParam("stop_x_speed", type="float", default=0.05,
                                        comment="x速度大于该值时, 清洁机构以低功率工作, x速度小于该值时, 清洁机构停止工作")
        
        self.ip = "127.0.0.1"  # 机器人上报数据 ip
        self.port = 502
        self.modbus_tcp = modbus_tcp.TcpMaster(self.ip, self.port, 1)
        self.is_connected = False
        self.rbk_addr = 110  # rbk寄存器清水液位数据地址
        
        # 清洁机构工作状态
        self.brush_status = None
        self.jet_status = None
        self.suck_status = None
        self.brush_lift_status = None
        self.mop_lift_status = None
        self.clean_valve_status = None
        self.waste_valve_status = None  # 只有加水排污时才工作
        self.clean_robot_working = None  # 所有机构全部工作
        self.clean_robot_closed = None  # 所有机构全部停止
        self.work_mode = WorkMode.STD
        
        self.period_run_start = time.time()
        self.task_update_start = time.time()
        self.period_run_counter = 0
        self.opt_run_counter = 0
        self.report_info = {}
        self.status = MoveStatus.NONE
        self.operation = None
        self.init = False
        self.args = args
        
        self.wash_start_time = None
        self.add_water_time_start = None
        self.close_jet_pump_start = None
        self.add_water_opt_start = False
        
        self.clean_robot = CleanRobot(self)
        self.clean_water_level = -1
        self.waste_water_level = -1
        self.clean_filter = MeanValue(1000)  # 清水液位滤波
        self.waste_filter = MeanValue(1000)  # 污水液位滤波
        r.logInfo(f"init args: {args}")
    
    def periodRun(self, r: SimModule) -> bool:
        self.period_run_counter += 1
        if (self.args == {} or self.args == [""]) and self.period_run_counter == 1:  # 刚开机时, 复位机构
            self.reset(r)
        self.update_report_info(r)  # 更新上报数据
        self.update_all_info(r)  # 同步清洁机器人各机构的工作状态
        
        if not self.is_connected:
            self.connect(r)
        if time.time() - self.task_update_start > 0.2:  # 0.2秒更新一次
            self.task_update_start = time.time()
            self.save_to_rbk(r)  # 同步液位数据到RBK
            self.update_by_task_status(r)  # 根据任务状态处理业务逻辑
        if time.time() - self.period_run_start > 0.5:  # 0.5秒更新一次
            self.period_run_start = time.time()
            r.setInfo(json.dumps(self.report_info))  # 数据上报
            r.logInfo(json.dumps(self.report_info))  # 日志打印
        return True
    
    def run(self, r: SimModule, args: dict):
        self.opt_run_counter += 1
        self.status = MoveStatus.RUNNING
        if not self.init:
            self.init = True
            self.update_all_info(r)  # 同步清洁机器人各机构的工作状态
            self.operation = args.get("operation", None)
            self.auto_adjust_power = args.get("auto_adjust", self.auto_adjust_power)
            self.jet_power = int(args.get("jet_power", self.jet_power))
            self.brush_power = int(args.get("brush_power", self.brush_power))
            self.suck_power = int(args.get("suck_power", self.suck_power))
        
        if self.operation == "WashStart":
            self.wash_start(r)
        elif self.operation == "WashEnd":
            self.wash_end(r)
        elif self.operation == "DustStart":
            self.dust_start(r)
        elif self.operation == "DustEnd":
            self.dust_end(r)
        elif self.operation == "AddWater":
            self.add_water(r)
        elif self.operation == "CheckInfo":
            self.update_all_info(r)
        else:
            r.setUserError(53910, f"args error: {self.operation}")
            self.status = MoveStatus.FAILED
        self.report_info['args'] = args
        self.report_info['operation'] = self.operation
        # r.setInfo(json.dumps(self.report_info))
        r.logInfo(f"clean robot info: {json.dumps(self.report_info)}")
        return self.status
    
    def update_by_task_status(self, r: SimModule):
        task_status = r.getCurrentTaskStatus()
        if task_status == 2:  # Running
            if self.operation == "WashStart" and self.status == MoveStatus.FINISHED:
                self.update_power_by_speed(r)
        elif task_status == 3:  # Suspended
            self.wash_suspend(r)
        elif task_status == 5:  # Failed
            self.wash_suspend(r)
        elif task_status == 6:  # Canceled
            self.wash_suspend(r)
        
        # 急停信号检测
        if r.controller().get("emc", False):
            self.wash_suspend(r)
        
        # 水位检测，清水空了或者污水满了，结束清洁任务
        if (self.filter_waste_water_level() > self.max_waste_water_level or
                self.filter_clean_water_level() < self.min_clean_water_level):
            r.setUserError(53980, f"Clean water is empty or waste water is full!")
            if self.operation != "AddWater":  # 终止任务，过滤加水任务
                self.wash_end(r)
        else:
            if r.errorExits(53980):
                r.clearError(53980)
    
    def update_power_by_speed(self, r: SimModule):
        agv_speed = r.getNextSpeed()
        if bool(self.auto_adjust_power):
            if agv_speed['x'] > self.high_mode_x_speed:
                self.work_mode = WorkMode.HIGH
                self.suck_power, self.jet_power, self.brush_power = (70, 50, 67)
            if self.std_mode_x_speed < agv_speed['x'] < self.high_mode_x_speed:
                self.work_mode = WorkMode.STD
                self.suck_power, self.jet_power, self.brush_power = (50, 20, 67)
            if self.stop_x_speed < agv_speed['x'] < self.std_mode_x_speed or agv_speed['x'] < agv_speed['rotate']:
                self.work_mode = WorkMode.LOW
                self.suck_power, self.jet_power, self.brush_power = (40, 10, 50)
        if agv_speed['x'] < self.stop_x_speed:
            self.wash_suspend(r)
        else:
            self.wash_open(r)
    
    def connect(self, r: SimModule):
        try:
            self.modbus_tcp.open()
        except Exception as e:
            r.logInfo(f"connect error: {e}")
        else:
            self.is_connected = True

    def save_to_rbk(self, r: SimModule):
        try:
            self.modbus_tcp.execute(1, cst.WRITE_MULTIPLE_REGISTERS, self.rbk_addr,
                                    output_value=[round(self.filter_clean_water_level()),
                                                  round(self.filter_waste_water_level())])
        except Exception as e:
            r.logInfo(f"save_to_rbk error: {e}")
    
    def update_report_info(self, r: SimModule):
        clean_robot = dict()
        clean_robot["cleanWaterLevel"] = self.filter_clean_water_level()
        clean_robot["wasteWaterLevel"] = self.filter_waste_water_level()
        agv_speed = dict()
        cur_speed = r.getNextSpeed()
        agv_speed['x'] = round(cur_speed.get('x', 0), 6)
        agv_speed['y'] = round(cur_speed.get('y', 0), 6)
        agv_speed['rotate'] = round(cur_speed.get('rotate', 0), 6)
        auto_adjust = dict()
        auto_adjust["auto_adjust"] = bool(self.auto_adjust_power)
        auto_adjust["work_mode"] = self.work_mode.name
        auto_adjust["suck_power"] = self.suck_power
        auto_adjust["jet_power"] = self.jet_power
        auto_adjust["brush_power"] = self.brush_power
        self.report_info["auto_adjust"] = auto_adjust
        self.report_info["cleanRobot"] = clean_robot
        self.report_info["connected"] = self.is_connected
        self.report_info["script_status"] = self.status
        self.report_info["agv_speed"] = agv_speed
        self.report_info["operation"] = self.operation
        self.report_info["period_run_counter"] = self.period_run_counter
        self.report_info["task_status"] = r.getCurrentTaskStatus()
        self.report_info["time"] = time.strftime('%Y-%m-%d %H:%M:%S')
    
    def wash_open(self, r: SimModule):
        if self.brush_lift_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_brush_lift(r, WorkState.OPEN)
        if self.mop_lift_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_mop_lift(r, WorkState.OPEN)
        elif self.clean_valve_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_clean_valve(r, WorkState.OPEN)
        elif self.suck_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_suck(r, self.suck_power)
        elif self.brush_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_brush(r, self.brush_power)
        elif self.jet_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_jet_pump(r, self.jet_power)
    
    def wash_start(self, r: SimModule):
        self.wash_open(r)
        if self.clean_robot_working:
            self.status = MoveStatus.FINISHED
    
    def wash_end(self, r: SimModule):
        self.operation = "WashEnd"  # 通过函数调用时，同步更新 self.operation
        self.wash_suspend(r)
        r.setDO(self.add_water_do, False)
        # 暂停工作时，不关闭升降杆，停止工作时，关闭升降杆
        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > self.close_jet_delay_time:
            if self.brush_lift_status != WorkingStatus.INIT:
                self.clean_robot.ctrl_brush_lift(r, WorkState.CLOSE)
            if self.mop_lift_status != WorkingStatus.INIT:
                self.clean_robot.ctrl_mop_lift(r, WorkState.CLOSE)
        if self.clean_robot_closed:
            self.close_jet_pump_start = None
            self.status = MoveStatus.FINISHED
    
    def wash_suspend(self, r: SimModule):
        if self.jet_status == WorkingStatus.RUNNING:
            self.clean_robot.ctrl_jet_pump(r, 0)
        if self.brush_status == WorkingStatus.RUNNING:
            self.clean_robot.ctrl_brush(r, 0)
        if self.clean_valve_status == WorkingStatus.RUNNING:
            self.clean_robot.ctrl_clean_valve(r, WorkState.CLOSE)
        if self.waste_valve_status == WorkingStatus.RUNNING:
            self.clean_robot.ctrl_waste_valve(r, WorkState.CLOSE)
        if bool(self.auto_adjust_power):
            self.work_mode = WorkMode.STOP
            self.suck_power, self.jet_power, self.brush_power = (0, 0, 0)
        
        # 延时 close_jet_delay_time 秒关闭吸风电机
        if not self.close_jet_pump_start:
            self.close_jet_pump_start = time.time()
        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > self.close_jet_delay_time:
            if self.suck_status == WorkingStatus.RUNNING:
                self.clean_robot.ctrl_suck(r, 0)
    
    def reset(self, r: SimModule):
        self.clean_robot.ctrl_close_all(r)  # 关闭全部机构
        # self.clean_robot.ctrl_jet_pump(r, 0)
        # self.clean_robot.ctrl_brush(r, 0)
        # self.clean_robot.ctrl_suck(r, 0)
        # self.clean_robot.ctrl_mop_lift(r, WorkState.CLOSE)
        # self.clean_robot.ctrl_brush_lift(r, WorkState.CLOSE)
        # self.clean_robot.ctrl_clean_valve(r, WorkState.CLOSE)
        # self.clean_robot.ctrl_waste_valve(r, WorkState.CLOSE)
    
    def dust_start(self, r: SimModule):
        if self.mop_lift_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_mop_lift(r, WorkState.OPEN)
        else:
            self.status = MoveStatus.FINISHED
    
    def dust_end(self, r: SimModule):
        if self.mop_lift_status != WorkingStatus.INIT:
            self.clean_robot.ctrl_mop_lift(r, WorkState.CLOSE)
        else:
            self.status = MoveStatus.FINISHED
    
    def add_water(self, r: SimModule):
        is_charging = r.battery().get("is_charging", False)
        if not is_charging:
            r.setDO(self.add_water_do, False)
            self.clean_robot.ctrl_waste_valve(r, WorkState.CLOSE)
            r.setError(f"Not in charging state!")
            self.status = MoveStatus.FAILED
        else:
            if not self.add_water_opt_start:
                r.setDO(self.add_water_do, True)
                self.clean_robot.ctrl_waste_valve(r, WorkState.OPEN)
        
        # 加水排污已处于工作状态
        if ModuleTool.check_DO(r, self.add_water_do) and self.waste_valve_status == WorkingStatus.RUNNING:
            self.add_water_opt_start = True
        
        # 停止加水
        if self.clean_water_level >= self.max_clean_water_level:
            r.setDO(self.add_water_do, False)
        
        # 停止排污
        if self.waste_water_level <= self.min_waste_water_level:
            self.clean_robot.ctrl_waste_valve(r, WorkState.CLOSE)
        
        # 加水排污任务延时 add_water_delay_time 秒结束
        if self.waste_water_level <= self.min_waste_water_level and self.clean_water_level >= self.max_clean_water_level:
            if not self.add_water_time_start:
                self.add_water_time_start = time.time()
            if time.time() - self.add_water_time_start > self.add_water_delay_time:
                self.add_water_time_start = None
                self.add_water_opt_start = False
                self.status = MoveStatus.FINISHED
        self.report_info["add_water_opt_start"] = self.add_water_opt_start
        self.report_info["is_charging"] = is_charging
    
    def filter_clean_water_level(self):
        if self.clean_water_level >= 0:
            self.clean_filter.add_value(self.clean_water_level)
            return self.clean_filter.get_mean_value()
        return self.clean_water_level
    
    def filter_waste_water_level(self):
        if self.waste_water_level >= 0:
            self.waste_filter.add_value(self.waste_water_level)
            return self.waste_filter.get_mean_value()
        return self.waste_water_level
    
    def update_all_info(self, r: SimModule):
        """
        CAN报文数据解析:
        Bit0-7：   清水液位（类型：uint8 范围：0-100）
        Bit8-15：  污水液位（类型：uint8 范围：0-100）
        Bit16：    刷盘位置状态（类型：bit, 0:收起状态 1：工作状态，默认0）
        Bit17：    水扒位置状态（类型：bit, 0:收起状态 1：工作状态，默认0）
        Bit18：    清水阀门状态（类型：bit, 0:关闭状态 1：打开状态，默认0）
        Bit19：    污水阀门状态（类型：bit, 0:关闭状态 1：打开状态，默认0）
        Bit20：    吸风开关状态（类型：bit, 0:关闭状态 1：工作状态，默认0）
        Bit21：    刷盘开关状态（类型：bit, 0:关闭状态 1：工作状态，默认0）
        Bit22：    喷水电机状态（类型：bit, 0:关闭状态 1：工作状态，默认0）
        Bit23-31： 预留
        示例：清水100，污水99，吸风开启状态（0x00106364）
        605：40 03 40 00 00 00 00 00
        585: 43 03 40 00 64 63 10 00
        """
        info = {}
        recv_data = self.clean_robot.query_all_info(r)
        if self.clean_robot.query_all_cmd_status == WorkingStatus.FINISHED:
            self.clean_robot.query_all_cmd_status = WorkingStatus.INIT
            # 报文数据解析
            state = bin(int(recv_data[12:14], 16))[2:].zfill(8)  # 状态数据变为8位2进制
            self.clean_water_level = int(recv_data[8:10], 16)  # 清水液位
            self.waste_water_level = int(recv_data[10:12], 16)  # 污水液位
            self.jet_status = WorkingStatus(int(state[1:2]))
            self.brush_status = WorkingStatus(int(state[2:3]))
            self.suck_status = WorkingStatus(int(state[3:4]))
            self.waste_valve_status = WorkingStatus(int(state[4:5]))
            self.clean_valve_status = WorkingStatus(int(state[5:6]))
            self.mop_lift_status = WorkingStatus(int(state[6:7]))
            self.brush_lift_status = WorkingStatus(int(state[7:8]))
            self.clean_robot_working = all(list(map(int, state[1:4] + state[5:8])))  # 全工作时为 True
            self.clean_robot_closed = not bool(max(list(map(int, state[1:4] + state[5:8]))))  # 全关闭时为 True
        info['suck_state'] = self.suck_status
        info['brush_state'] = self.brush_status
        info['jet_pump_state'] = self.jet_status
        info['mop_lift_state'] = self.mop_lift_status
        info['brush_lift_state'] = self.brush_lift_status
        info['waste_valve_state'] = self.waste_valve_status
        info['clean_valve_state'] = self.clean_valve_status
        self.report_info["work_status"] = info
    
    def cancel(self, r: SimModule):
        r.setNotice(f"script cancel")
        r.setDO(self.add_water_do, False)
        self.close_jet_delay_time = -1
        self.wash_end(r)
        self.status = MoveStatus.FAILED


class CleanRobot:
    def __init__(self, module_obj: Module):
        self.chanel = "can1"
        self.can_id = 0x605
        self.dlc = 8
        self.extend = False
        self.agv = module_obj
        self.brush_start_time = None
        self.default_data = '0' * 16
        self.has_send = False
        self.send_start = None
        self.send_wait_time = 0.01
        self.query_all_cmd_status = WorkingStatus.INIT
        self.can_arch64 = CanPassAarch64()
        self.can_arch64.createCanBus(channel="can1", bitrate=250)
        self.can_arch64.attachCanID(0x585)
    
    def ctrl_suck(self, r: SimModule, power=0):
        cmd = Cmd.SUCK
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        self.send_cmd(r, cmd)
    
    def ctrl_brush(self, r: SimModule, power=0):
        cmd = Cmd.BRUSH
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        self.send_cmd(r, cmd)
    
    def ctrl_jet_pump(self, r: SimModule, power=0):
        cmd = Cmd.JET_PUMP
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        self.send_cmd(r, cmd)
    
    def ctrl_brush_lift(self, r: SimModule, state):
        if state is WorkState.OPEN:
            cmd = Cmd.BRUSH_LIFT_DOWN
        else:
            cmd = Cmd.BRUSH_LIFT_UP
        self.send_cmd(r, cmd)
    
    def ctrl_mop_lift(self, r: SimModule, state):
        if state is WorkState.OPEN:
            cmd = Cmd.MOP_LIFT_DOWN
        else:
            cmd = Cmd.MOP_LIFT_UP
        self.send_cmd(r, cmd)
    
    def ctrl_clean_valve(self, r: SimModule, state):
        if state is WorkState.OPEN:
            cmd = Cmd.WATER_VALVE_OPEN
        else:
            cmd = Cmd.WATER_VALVE_CLOSE
        self.send_cmd(r, cmd)
    
    def ctrl_waste_valve(self, r: SimModule, state):
        if state is WorkState.OPEN:
            cmd = Cmd.BRAIN_BALL_VALVE_OPEN
        else:
            cmd = Cmd.BRAIN_BALL_VALVE_CLOSE
        self.send_cmd(r, cmd)
    
    def ctrl_open_all(self, r: SimModule, mode):
        cmd = Cmd.SET_ALL_STD
        if mode == WorkMode.STD:
            cmd = Cmd.SET_ALL_STD  # 标准功率打开
        elif mode == WorkMode.LOW:
            cmd = Cmd.SET_ALL_LOW  # 低功率打开
        elif mode == WorkMode.HIGH:
            cmd = Cmd.SET_ALL_HIGH  # 高功率打开
        elif mode == WorkMode.STOP:
            cmd = Cmd.SET_ALL_CLOSED  # 关闭
        self.agv.report_info['ctrl_open_all'] = cmd
        self.send_cmd(r, cmd)
    
    def ctrl_close_all(self, r: SimModule):
        cmd = Cmd.SET_ALL_CLOSED
        self.send_cmd(r, cmd)
    
    def query_all_info(self, r: SimModule):
        self.query_all_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_ALL_INFO)
        if recv_data[:8] == "43034000":  # 报文地址匹配
            self.query_all_cmd_status = WorkingStatus.FINISHED
            self.agv.report_info['query_all_info'] = recv_data
            return recv_data
        return self.default_data
    
    def send_cmd(self, r: SimModule, cmd):
        lst_cmd = [int(i, 16) for i in cmd.split()]
        self.can_arch64.sendCanframe(r, self.chanel, self.can_id, self.dlc, self.extend, lst_cmd)
        data = self.can_arch64.recvCan(r)
        self.agv.report_info['recv_data'] = data
        r.logDebug(f"send cmd: {cmd}, recv msg: {data}")
        return data
        
        # r.sendCanFrame(self.chanel, self.can_id, self.dlc, self.extend, cmd)
        # data = r.getCanFrame()
        # b64_str = data.get('Data', '')
        # can_id = data.get('ID', 0)
        # hex_str = base64.b64decode(b64_str).hex().upper()
        # if can_id + 128 == self.can_id:
        #     return hex_str
        # return self.default_data


class WorkingStatus(IntEnum):
    INIT = 0
    RUNNING = 1
    FINISHED = 2


class WorkState(IntEnum):
    CLOSE = 0
    OPEN = 1


class WorkMode(IntEnum):
    LOW = 0
    STD = 1
    HIGH = 2
    STOP = 3


class Cmd:
    """
    电机控制指令格式   "2B 80 30 " + "addr" + "power" + " 00 00 00"
    电机查询指令格式   "40 80 30 " + "addr" + " 00 00 00 00"
    """
    SUCK = "2B 80 30 01 00 00 00 00"  # 吸风电机
    BRUSH = "2B 80 30 02 00 00 00 00"  # 刷盘电机
    JET_PUMP = "2B 80 30 03 00 00 00 00"  # 清水喷水泵
    BRUSH_LIFT_UP = "2B 80 30 04 64 00 00 00"  # 刷盘升降推杆上升
    BRUSH_LIFT_DOWN = "2B 80 30 04 FF 9C 00 00"  # 刷盘升降推杆下降
    MOP_LIFT_UP = "2B 80 30 05 FF 9C 00 00"  # 水扒升降推杆上升
    MOP_LIFT_DOWN = "2B 80 30 05 64 00 00 00"  # 水扒升降推杆下降
    WATER_VALVE_OPEN = "2B 80 30 06 64 00 00 00"  # 喷水阀开
    WATER_VALVE_CLOSE = "2B 80 30 06 00 00 00 00"  # 喷水阀关
    BRAIN_BALL_VALVE_OPEN = "2B 80 30 07 64 00 00 00"  # 排水球阀开
    BRAIN_BALL_VALVE_CLOSE = "2B 80 30 07 00 00 00 00"  # 排水球阀关
    
    QUERY_SUCK = "40 80 30 01 00 00 00 00"  # 查询吸风电机信息
    QUERY_BRUSH = "40 80 30 02 00 00 00 00"  # 查询刷盘电机信息
    QUERY_JET_PUMP = "40 80 30 03 00 00 00 00"  # 查询喷水泵电机信息
    QUERY_BRUSH_LIFT = "40 80 30 04 00 00 00 00"  # 查询刷盘推杆电机信息
    QUERY_MOP_LIFT = "40 80 30 05 00 00 00 00"  # 查询水扒升降信息
    QUERY_WATER_VALVE = "40 80 30 06 00 00 00 00"  # 查询喷水阀信息
    QUERY_BALL_VALVE = "40 80 30 07 00 00 00 00"  # 查询排水球阀信息
    
    QUERY_CLEAN_WATER_LEVEL = "40 8B 30 03 00 00 00 00"  # 查询清水液位计
    QUERY_WASTE_WATER_LEVEL = "40 8B 30 04 00 00 00 00"  # 查询污水液位计
    
    SET_CAN_TIMEOUT = "2B 01 40 00 00 00 00 00"  # 设置CAN通信超时时间, 2字节
    SET_ALL_STD = "23 02 40 00 32 43 1E 07"  # 以标准功率设定全部机构
    SET_ALL_LOW = "23 02 40 00 28 32 14 07"  # 以低档模式设定全部机构
    SET_ALL_HIGH = "23 02 40 00 46 50 32 07"  # 以高档模式设定全部机构
    SET_ALL_CLOSED = "23 02 40 00 00 00 00 00"  # 设定全部机构关闭
    QUERY_ALL_INFO = "40 03 40 00 00 00 00 00"  # 查询所有机构的运行状态


class MeanValue:
    """均值滤波"""
    
    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.data = []
        self.threshold = 10
    
    def add_value(self, v):
        self.data.append(v)
        while len(self.data) > self.window_size:
            self.data.pop(0)
    
    def get_mean_value(self) -> float:
        return round(sum(self.data) / len(self.data), 3)


class CanPassAarch64:
    def __init__(self):
        print("canPassAarch64 start!")
        self.bus = None
        self.__callback = None
        self.__should_close = False
        self.can_ids = []
        self.send_time = 0
        self.res_timeout = 2
        self.default_data = '0' * 16
    
    def setCallBack(self, handleData):
        if not handleData:
            print("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__callback = handleData
    
    def createCanBus(self, channel, bitrate):
        self.bus = can.interface.Bus(bustype='socketcan', channel=channel, bitrate=bitrate)
    
    # 过滤器函数
    def can_filter(self, msg):
        if msg.arbitration_id in self.can_ids:
            return True
        else:
            return False
    
    def attachCanID(self, *canid):
        for i in range(len(canid)):
            self.can_ids.append(canid[i])
        filters = []
        for id_ in self.can_ids:
            if id_ < 0x800:
                can_mask = 0x7FF
            else:
                can_mask = 0x1FFFFFFF
            filters.append({"can_id": id_, "can_mask": can_mask})
        self.bus.set_filters(filters)
        # print('Attached CAN IDs:', end=' ')
        for id_ in self.can_ids:
            print(hex(id_), end=' ')
    
    def sendCanframe(self, r: SimModule, channel, can_id, dlc, extend, can_string):
        self.send_time = time.time()
        bus = can.interface.Bus(channel, bustype='socketcan')
        msg = can.Message(arbitration_id=can_id, data=can_string, is_extended_id=extend, dlc=dlc)
        bus.send(msg)
        r.logInfo(
            f'message send: channel={channel}, can_id={hex(can_id)}, dlc={dlc}, extend={extend}, can_string={can_string}')
        bus.shutdown()
    
    def recvCan(self, r) -> str:
        try:
            start = time.time()
            msg = self.bus.recv(0.1)
            ret_data = self.default_data
            r.logInfo(f"self.bus start {self.bus},{type(self.bus)}")
            if msg and self.can_filter(msg):
                if self.__callback is not None:
                    self.__callback(r, msg)
                r.logInfo(f"start time end {time.time() - start},has rec")
                ret_data = ''.join(
                    hex(int.from_bytes(msg.data[i:i + 1], 'big'))[2:].zfill(2) for i in range(len(msg.data)))
            r.logInfo(f"start time end {time.time() - start},nor rec")
            return ret_data
        except Exception as e:
            r.setWarning(f"can 通信接受异常,{e}")
            return self.default_data
    
    def __del__(self):
        self.bus.shutdown()
    
    def close(self):
        self.bus.shutdown()


if __name__ == '__main__':
    r1 = SimModule()
    m1 = Module(r1, {})
    m1.periodRun(r1)
    operation = ["WashStart", "WashEnd", "DustStart", "DustEnd", "AddWater", "CloseJetPump"]
    for opt in operation:
        args1 = {"operation": opt}
        print("*" * 100)
        m1.run(r1, args1)
        # m1.periodRun(r1)
    m1.periodRun(r1)
