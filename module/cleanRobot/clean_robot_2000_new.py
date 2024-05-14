# -*- coding: utf-8 -*-
# @Date: 2024/04/10
# @Author: zhong
# @Version: 1.1
# @Project: SRC2000 清洁机器人
# @Coding: https://seer-group.coding.net/p/robokit/assignments/issues/2631/detail
# @Update: 更新一键控制协议
import base64
import sys
import time
import socket
from enum import IntEnum
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp

sys.path.append("../syspy")
import json
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "",
        "default_value":["WashStart", "WashEnd", "DustStart", "DustEnd", "AddWater",  "CheckInfo"],
        "tips": "操作选项",
        "type": "complex"
    },
    "brush_power":{
        "value": 67,
        "tips": "刷盘电机功率, 取值: 0-100, 0即关闭，100即满功率, 参数可缺省",
        "type": "int"
    },
    "suction_power":{
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
        self.min_clean_water_level = p.loadParam("min_clean_water_level", type="float", default=1.0,
                                                 comment="清水液位最小值，达到此值机器人停止工作去加水")
        self.max_clean_water_level = p.loadParam("max_clean_water_level", type="float", default=99.0,
                                                 comment="清水液位最大值，达到此值机器人停止加水")
        self.min_waste_water_level = p.loadParam("min_waste_water_level", type="float", default=1.0,
                                                 comment="污水液位最小值，达到此值机器人停止排污")
        self.max_waste_water_level = p.loadParam("max_waste_water_level", type="float", default=90.0,
                                                 comment="污水液位最大值，达到此值机器人停止工作去排污")
        self.end_close_time = p.loadParam("end_close_time", type="float", default=5.0,
                                             comment="任务结束缓冲时间,即水泵关闭后阻塞时间")
        self.add_water_do = p.loadParam("add_water_do", type="int", default=4, comment="加水DO")
        self.brush_power = p.loadParam("brush_power", type="int", default=67, comment="刷盘电机默认功率")
        self.suction_power = p.loadParam("suction_power", type="int", default=50, comment="吸风电机默认功率")
        self.jet_power = p.loadParam("jet_power", type="int", default=20, comment="喷水泵电机默认功率")
        self.auto_adjust_power = p.loadParam("auto_adjust_power", type="int", default=1,
                                             comment="是否启动电机功率自动调节模式, 1: 启动， 0: 不启动")
        self.add_water_delay_time = p.loadParam("add_water_delay_time", type="float", default=5.0,
                                                comment="加水延时关闭时间，即加水任务结束后阻塞时间")
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
        self.suction_status = None
        self.brush_lift_status = None
        self.mop_lift_status = None
        self.clean_valve_status = None
        self.waste_valve_status = None
        self.work_mode = WorkMode.STD

        #清扫结束进入结束状态检测
        self.end_start_flag=True
        self.end_start_time=time.time()
        
        self.period_run_start = time.time()
        self.period_run_counter = 0
        self.opt_run_counter = 0
        self.report_info = {}
        self.status = MoveStatus.NONE
        self.operation = None
        self.init = False
        self.wash_start_time = None
        self.add_water_time_start = None
        self.add_water_begin = False #开始加水
        
        self.clean_robot = CleanRobot(self)
        self.clean_water_level = -1
        self.waste_water_level = -1
        self.clean_filter = MeanValue(1000)  # 清水液位滤波
        self.waste_filter = MeanValue(1000)  # 污水液位滤波
        r.logInfo(f"init args: {args}")
    
    def periodRun(self, r: SimModule) -> bool:
        self.period_run_counter += 1
        clean_robot = dict()
        clean_robot["cleanWaterLevel"] = self.filter_clean_water_level()
        clean_robot["wasteWaterLevel"] = self.filter_waste_water_level()
        agv_speed = dict()
        cur_speed = r.getNextSpeed()
        agv_speed['x'] = round(cur_speed.get('x', 0), 6)
        agv_speed['y'] = round(cur_speed.get('y', 0), 6)
        agv_speed['rotate'] = round(cur_speed.get('rotate', 0), 6)
        self.report_info["cleanRobot"] = clean_robot
        self.report_info["connected"] = self.is_connected
        self.report_info["script_status"] = self.status
        self.report_info["agv_speed"] = agv_speed
        self.report_info["operation"] = self.operation
        self.report_info["period_run_counter"] = self.period_run_counter
        self.report_info["task_status"] = r.getCurrentTaskStatus()
        self.report_info["time"] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.report_info["work_mode"] = self.work_mode.name
        self.report_info["suction_power"] = self.suction_power
        self.report_info["jet_power"] = self.jet_power
        self.report_info["brush_power"] = self.brush_power
        self.report_info["endclosetime"] = self.end_close_time
        # 同步清洁机器人各机构的工作状态
        self.update_all_info(r)
        # 同步液位数据到RBK
        if not self.is_connected:
            self.connect(r)
        self.save_to_rbk(r)
        if time.time() - self.period_run_start > 0.5:
            self.period_run_start = time.time()
            if not self.end_start_flag:
                self.wash_suspend(r)
            # 根据任务状态处理业务逻辑
            self.update_by_task_status(r)
            # 数据上报及日志打印
            r.setInfo(json.dumps(self.report_info))
            r.logInfo(json.dumps(self.report_info))
        return True
    
    def run(self, r: SimModule, args: dict):
        self.status = MoveStatus.RUNNING
        if not self.init:
            self.init = True
            self.update_all_info(r)  # 同步清洁机器人各机构的工作状态
            self.operation = args.get("operation", None)
            self.jet_power = int(args.get("jet_power", self.jet_power))
            self.brush_power = int(args.get("brush_power", self.brush_power))
            self.suction_power = int(args.get("suction_power", self.suction_power))
        
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
        if self.filter_waste_water_level() > self.max_waste_water_level or \
                self.filter_clean_water_level() < self.min_clean_water_level:
            self.wash_end(r)
            
    def update_power_by_speed(self, r: SimModule):
        agv_speed = r.getNextSpeed()
        if bool(self.auto_adjust_power):
            if agv_speed['x'] > self.high_mode_x_speed:
                self.work_mode = WorkMode.HIGH
                self.suction_power, self.jet_power, self.brush_power = (70, 50, 67)
            if self.std_mode_x_speed < agv_speed['x'] < self.high_mode_x_speed:
                self.work_mode = WorkMode.STD
                self.suction_power, self.jet_power, self.brush_power = (50, 20, 67)
            if self.stop_x_speed < agv_speed['x'] < self.std_mode_x_speed or agv_speed['x'] < agv_speed['rotate']:
                self.work_mode = WorkMode.LOW
                self.suction_power, self.jet_power, self.brush_power = (40, 10, 50)
        if agv_speed['x'] < self.stop_x_speed:
            self.wash_suspend(r)
        else:
            self.end_start_flag = True
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

    def status_check(self, r: SimModule):
        if self.brush_lift_status and self.suction_status and self.brush_status and self.mop_lift_status and self.clean_valve_status and self.jet_status:
            return MachineState.WASHING
        elif not self.brush_lift_status and not self.suction_status and not self.brush_status and not self.mop_lift_status\
            and not self.clean_valve_status and not self.waste_valve_status and not self.jet_status:
            return MachineState.STANDBY
        elif not self.brush_lift_status and not self.suction_status and not self.brush_status and  self.mop_lift_status\
            and not self.clean_valve_status and not self.waste_valve_status and not self.jet_status:
            return MachineState.DUSTING
        elif not self.brush_lift_status and not self.suction_status and not self.brush_status and not self.mop_lift_status\
            and not self.clean_valve_status and self.waste_valve_status and not self.jet_status:
            return MachineState.MAINTAINING
        elif not self.suction_status and not self.brush_status and not self.clean_valve_status and self.waste_valve_status and not self.jet_status:
            return MachineState.SUSPEND
        elif self.suction_status and self.brush_status and not self.clean_valve_status and self.waste_valve_status and not self.jet_status:
            return MachineState.FINISHING
    
    def wash_open(self, r: SimModule):
        if self.brush_lift_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_brush_lift(r, WorkState.OPEN)
        if self.mop_lift_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_mop_lift(r, WorkState.OPEN)
        elif self.clean_valve_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_clean_valve(r, WorkState.OPEN)
        elif self.suction_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_suction(r, self.suction_power)
        elif self.brush_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_brush(r, self.brush_power)
        elif self.jet_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_jet_pump(r, self.jet_power)
    
    def wash_start(self, r: SimModule):
        self.wash_open(r)
        if (self.status_check(r)==MachineState.WASHING):
            self.status = MoveStatus.FINISHED
    
    def close_jet_pump(self, r: SimModule):
        if self.jet_status == WorkingStatus.RUNNING:
            self.clean_robot.ctrl_jet_pump(r, 0)
        if self.clean_valve_status == WorkingStatus.RUNNING:
            self.clean_robot.ctrl_clean_valve(r, WorkState.CLOSE)

    def wash_end(self, r: SimModule):
        self.operation = "WashEnd"
        self.wash_suspend(r)
        if self.end_start_flag:
            if self.brush_lift_status != WorkingStatus.INIT:
                self.clean_robot.ctrl_brush_lift(r, WorkState.CLOSE)
            if self.mop_lift_status != WorkingStatus.INIT:
                    self.clean_robot.ctrl_mop_lift(r, WorkState.CLOSE)
            if (self.status_check(r)==MachineState.STANDBY):
                    self.status = MoveStatus.FINISHED

            
    def wash_suspend(self, r: SimModule):
        if self.end_start_flag:
            if bool(self.auto_adjust_power):
                self.work_mode = WorkMode.STOP
                self.jet_power = 0
            self.close_jet_pump(r)
            self.end_start_flag=False
            self.end_start_time=time.time()
        elif time.time()-self.end_start_time>self.end_close_time:
            if bool(self.auto_adjust_power):
                self.suction_power, self.brush_power = (0,0)
            if self.brush_status == WorkingStatus.RUNNING:
                self.clean_robot.ctrl_brush(r, 0)
            if self.suction_status == WorkingStatus.RUNNING:
                self.clean_robot.ctrl_suction(r, 0)
            if self.waste_valve_status == WorkingStatus.RUNNING:
                self.clean_robot.ctrl_waste_valve(r, WorkState.CLOSE)
            self.end_start_flag=True
    
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
        if is_charging:
            # 加水排污
            if not self.add_water_begin:
                self.add_water_begin=True
                r.setDO(self.add_water_do, True)
                self.clean_robot.ctrl_waste_valve(r, WorkState.OPEN)
        else:
            r.setDO(self.add_water_do, False)
            self.clean_robot.ctrl_waste_valve(r, WorkState.CLOSE)
            r.setError(f"Not in charging state!")
            self.status = MoveStatus.FAILED
            
        if self.clean_water_level >= self.max_clean_water_level:
            r.setDO(self.add_water_do, False)
        
        if self.waste_water_level <= self.min_waste_water_level:
            self.clean_robot.ctrl_waste_valve(r, WorkState.CLOSE)
        
        if self.waste_water_level <= self.min_waste_water_level and self.clean_water_level >= self.max_clean_water_level:
            if not self.add_water_time_start:
                self.add_water_time_start = time.time()
            if time.time() - self.add_water_time_start > self.add_water_delay_time:
                self.add_water_time_start = None
                self.status = MoveStatus.FINISHED
                self.add_water_begin=False
    
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
            self.suction_status = WorkingStatus(int(state[3:4]))
            self.waste_valve_status = WorkingStatus(int(state[4:5]))
            self.clean_valve_status = WorkingStatus(int(state[5:6]))
            self.mop_lift_status = WorkingStatus(int(state[6:7]))
            self.brush_lift_status = WorkingStatus(int(state[7:8]))
        info['suction_state'] = self.suction_status
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
        self.wash_end(r)
        self.status = MoveStatus.FAILED


class CleanRobot:
    def __init__(self, module_obj: Module):
        self.chanel = 2
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
    
    def ctrl_suction(self, r: SimModule, power=0):
        cmd = Cmd.SUCTION
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
        r.sendCanFrame(self.chanel, self.can_id, self.dlc, self.extend, cmd)
        data = r.getCanFrame()
        b64_str = data.get('Data', '')
        can_id = data.get('ID', 0)
        hex_str = base64.b64decode(b64_str).hex().upper()
        if can_id + 128 == self.can_id:
            return hex_str
        return self.default_data


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

class MachineState(IntEnum):
    STANDBY = 0
    WASHING = 1
    DUSTING = 2
    MAINTAINING = 3
    SUSPEND = 4
    FINISHING = 5


class Cmd:
    """
    电机控制指令格式   "2B 80 30 " + "addr" + "power" + " 00 00 00"
    电机查询指令格式   "40 80 30 " + "addr" + " 00 00 00 00"
    """
    SUCTION = "2B 80 30 01 00 00 00 00"  # 吸风电机
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
    
    QUERY_SUCTION = "40 80 30 01 00 00 00 00"  # 查询吸风电机信息
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


if __name__ == '__main__':
    m = Module(SimModule(), {})
    m.run(SimModule(), {})
    m.periodRun(SimModule())
    pass
