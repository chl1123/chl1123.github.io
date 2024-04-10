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

sys.path.append("../syspy")
import json
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "",
        "default_value":["WashStart", "WashEnd", "DustStart", "DustEnd", "AddWater", "CloseBallValve", "CheckInfo"],
        "tips": "操作选项",
        "type": "complex"
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
        self.min_clean_water_level = p.loadParam("min_clean_water_level", type="float", default=1.0,
                                                 comment="清水液位最小值")
        self.max_clean_water_level = p.loadParam("max_clean_water_level", type="float", default=99.0,
                                                 comment="清水液位最大值")
        self.min_waste_water_level = p.loadParam("min_waste_water_level", type="float", default=1.0,
                                                 comment="污水液位最小值")
        self.max_waste_water_level = p.loadParam("max_waste_water_level", type="float", default=90.0,
                                                 comment="污水液位最大值")
        self.add_water_do = p.loadParam("add_water_do", type="int", default=4, comment="加水DO")
        self.brush_power = p.loadParam("brush_power", type="int", default=67, comment="刷盘电机默认功率")
        self.suck_power = p.loadParam("suck_power", type="int", default=50, comment="吸风电机默认功率")
        self.jet_power = p.loadParam("jet_power", type="int", default=20, comment="喷水泵电机默认功率")
        
        self.add_water_delay_time = p.loadParam("add_water_delay_time", type="float", default=5.0, comment="加水延时关闭时间")
        
        self.ip = "127.0.0.1"  # 机器人上报数据 ip
        self.port = 502
        self.tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_client.setblocking(False)
        self.is_connected = False
        self.rbk_addr1 = 110  # rbk寄存器清水液位数据地址
        self.rbk_addr2 = 111  # rbk寄存器污水液位数据地址
        
        # 清洁机构工作状态, 1: 运行中  0: 未运行
        self.brush_status = 0
        self.jet_status = 0
        self.suck_status = 0
        self.brush_lift_status = 0
        self.mop_lift_status = 0
        self.clean_valve_status = 0
        self.waste_valve_status = 0
        
        self.period_run_start = time.time()
        self.period_run_counter = 0
        self.report_info = {}
        self.status = MoveStatus.NONE
        self.operation = None
        self.init = False
        self.period_init = False
        self.wash_start_time = None
        self.add_water_time_start = None
        
        self.clean_robot = CleanRobot(self)
        self.clean_water_level = 50
        self.waste_water_level = 50
        self.clean_filter = MeanValue(100)  # 清水液位滤波
        self.waste_filter = MeanValue(100)  # 污水液位滤波
        r.logInfo(f"init args: {args}")
    
    def periodRun(self, r: SimModule) -> bool:
        self.period_run_counter += 1
        if not self.period_init:
            self.period_init = True
            # self.update_water_level(r)  # 初始化水位值
            
        if not self.is_connected:
            self.connect(r)
        
        clean_robot = dict()
        clean_robot["cleanWaterLevel"] = self.clean_water_level
        clean_robot["wasteWaterLevel"] = self.waste_water_level
        agv_speed = dict()
        agv_speed['x'] = r.getNextSpeed()['x']
        agv_speed['y'] = r.getNextSpeed()['y']
        agv_speed['rotate'] = r.getNextSpeed()['rotate']
        self.report_info["cleanRobot"] = clean_robot
        self.report_info["connected"] = self.is_connected
        self.report_info["scriptStatus"] = self.status
        self.report_info["agvSpeed"] = agv_speed
        self.report_info["operation"] = self.operation
        self.report_info["periodRunCounter"] = self.period_run_counter
        self.report_info["taskStatus"] = r.getCurrentTaskStatus()
        self.report_info["time"] = time.strftime('%Y-%m-%d %H:%M:%S')
        if time.time() - self.period_run_start > 0.5:
            self.period_run_start = time.time()
            # 同步清洁机器人各机构的工作状态
            self.update_all_info(r)
            # 查询液位并同步到RBK
            # self.save_to_rbk(r)
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
            self.operation = args.get("operation", None)
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
        elif self.operation == "CloseBallValve":
            self.close_ball_valve(r)
        elif self.operation == "CheckInfo":
            self.update_all_info(r)
        else:
            r.setUserError(53910, f"args error: {self.operation}")
            self.status = MoveStatus.FAILED
        
        self.report_info['args'] = args
        self.report_info['clean_water'] = self.clean_water_level
        self.report_info['waste_water'] = self.waste_water_level
        self.report_info['operation'] = self.operation
        r.logInfo(f"clean robot info: {json.dumps(self.report_info)}")
        return self.status
    
    def update_by_task_status(self, r: SimModule):
        task_status = r.getCurrentTaskStatus()
        agv_speed = r.getNextSpeed()
        if task_status == 2:  # Running
            # TODO 根据AGV速度处理业务逻辑
            if self.operation == "WashStart":
                if (agv_speed['x'] < 0.1 or agv_speed['rotate'] > agv_speed['x']) \
                        and (self.jet_status == WorkingStatus.RUNNING):
                    self.clean_robot.ctrl_jet_pump(r, 0)
                elif self.jet_status != WorkingStatus.RUNNING:
                    self.clean_robot.ctrl_jet_pump(r, self.jet_power)
        # TODO 根据任务状态处理业务逻辑
        elif task_status == 3:  # Suspended
            self.wash_end(r)
        elif task_status == 4:  # Completed
            self.wash_end(r)
        elif task_status == 5:  # Failed
            self.wash_end(r)
        elif task_status == 6:  # Canceled
            self.wash_end(r)
    
    def connect(self, r: SimModule):
        try:
            self.tcp_client.connect((self.ip, self.port))
        except Exception as e:
            r.logInfo(f"connect error: {e}")
        else:
            self.is_connected = True
    
    @staticmethod
    def pack(addr, value):
        def crc16(data):
            """
            计算 Modbus CRC16 校验码
            """
            crc = 0xFFFF
            for b in data:
                crc ^= b
                for _ in range(8):
                    if crc & 0x0001:
                        crc >>= 1
                        crc ^= 0xA001
                    else:
                        crc >>= 1
            return crc
        
        # 构造 Modbus TCP 协议中的 PDU
        unit_id = 1  # Modbus device 的 unit id
        func_code = 6  # 写单个寄存器的功能码
        register_addr = addr  # 寄存器地址，假设为 4x0001
        register_value1 = value  # 待写入的值，假设为 0xFFFF
        
        pdu = bytearray()
        pdu += unit_id.to_bytes(1, byteorder='big')
        pdu += func_code.to_bytes(1, byteorder='big')
        pdu += register_addr.to_bytes(2, byteorder='big')
        pdu += register_value1.to_bytes(2, byteorder='big')
        
        # 构造 Modbus TCP 的 ADU
        transaction_id = 1  # Modbus' transaction id，此处设为 1
        protocol_id = 0  # Modbus protocol id，此处设为 0
        length = len(pdu) + 1  # ADU 长度为 PDU 长度加 1（unit id 的长度）
        adu = bytearray()
        adu += transaction_id.to_bytes(2, byteorder='big')
        adu += protocol_id.to_bytes(2, byteorder='big')
        adu += length.to_bytes(2, byteorder='big')
        adu += pdu
        # 计算 CRC-16 校验码
        crc16 = crc16(pdu)
        adu += crc16.to_bytes(2, byteorder='big')
        return adu
    
    def save_to_rbk(self, r: SimModule):
        try:
            self.tcp_client.sendall(self.pack(self.rbk_addr1, round(self.clean_water_level)))
            self.tcp_client.recv(1024)
            self.tcp_client.sendall(self.pack(self.rbk_addr2, round(self.waste_water_level)))
            self.tcp_client.recv(1024)
        except Exception as e:
            self.is_connected = False
            r.setUserWarning(55910, f"save_to_rbk error: {e}")
    
    def wash_start(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        if self.brush_lift_status != 1:
            self.clean_robot.ctrl_brush_lift(r, WorkState.OPEN)
        elif self.mop_lift_status != 1:
            self.clean_robot.ctrl_mop_lift(r, WorkState.OPEN)
        elif self.clean_valve_status != 1:
            self.clean_robot.ctrl_water_valve(r, WorkState.OPEN)
        elif self.suck_status != 1:
            self.clean_robot.ctrl_suck(r, self.suck_power)
        elif self.brush_status != 1:
            self.clean_robot.ctrl_brush(r, self.brush_power)
        elif self.jet_status != 1:
            self.clean_robot.ctrl_jet_pump(r, self.jet_power)
        else:
            self.status = MoveStatus.FINISHED
    
    def wash_end(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        if self.suck_status != 0:
            self.clean_robot.ctrl_suck(r, 0)
        elif self.jet_status != 0:
            self.clean_robot.ctrl_jet_pump(r, 0)
        elif self.brush_status != 0:
            self.clean_robot.ctrl_brush(r, 0)
        elif self.brush_lift_status != 0:
            self.clean_robot.ctrl_brush_lift(r, WorkState.CLOSE)
        elif self.mop_lift_status != 0:
            self.clean_robot.ctrl_mop_lift(r, WorkState.CLOSE)
        elif self.clean_valve_status != 0:
            self.clean_robot.ctrl_water_valve(r, WorkState.CLOSE)
        else:
            self.status = MoveStatus.FINISHED
    
    def dust_start(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        if self.mop_lift_status != 1:
            self.clean_robot.ctrl_mop_lift(r, WorkState.OPEN)
        else:
            self.status = MoveStatus.FINISHED
    
    def dust_end(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        if self.mop_lift_status != WorkingStatus.INIT:
            self.clean_robot.ctrl_mop_lift(r, WorkState.CLOSE)
        else:
            self.status = MoveStatus.FINISHED
    
    def add_water(self, r: SimModule):
        # 加清水
        if self.clean_water_level > self.max_clean_water_level:
            r.setDO(self.add_water_do, False)
        elif self.clean_water_level < self.min_clean_water_level:
            r.setDO(self.add_water_do, True)
        
        # 排污水
        if self.waste_water_level < self.min_waste_water_level:
            self.clean_robot.ctrl_ball_valve(r, WorkState.CLOSE)
        else:
            self.clean_robot.ctrl_ball_valve(r, WorkState.OPEN)
        
        if self.waste_water_level < self.min_waste_water_level and self.clean_water_level > self.max_clean_water_level:
            if not self.add_water_time_start:
                self.add_water_time_start = time.time()
            if time.time() - self.add_water_time_start > self.add_water_delay_time:
                self.add_water_time_start = None
                self.status = MoveStatus.FINISHED
    
    def close_ball_valve(self, r: SimModule):
        if self.waste_valve_status == 1:
            self.clean_robot.ctrl_ball_valve(r, WorkState.CLOSE)
        else:
            self.status = MoveStatus.FINISHED
    
    def get_clean_water_level(self, r):
        data = self.clean_robot.query_clean_water(r)
        if self.clean_robot.query_clean_water_cmd_status is WorkingStatus.FINISHED:
            self.clean_robot.query_clean_water_cmd_status = WorkingStatus.INIT
            self.clean_filter.add_value((int(data[10:12] + data[8:10], 16) / 4095 * 1000) / 950 * 100)
            return self.clean_filter.get_mean_value()
        return self.clean_water_level
    
    def get_waste_water_level(self, r):
        data = self.clean_robot.query_waste_water(r)
        if self.clean_robot.query_waste_water_cmd_status is WorkingStatus.FINISHED:
            self.clean_robot.query_waste_water_cmd_status = WorkingStatus.INIT
            self.waste_filter.add_value((int(data[10:12] + data[8:10], 16) / 4095 * 1000) / 950 * 100)
            return self.waste_filter.get_mean_value()
        return self.waste_water_level
    
    def update_water_level(self, r):
        self.clean_water_level = self.get_clean_water_level(r)
        self.waste_water_level = self.get_waste_water_level(r)
        
    def update_status_by_data(self, data):
        if data != self.clean_robot.default_data:
            if data[8:10] != '00':
                return WorkingStatus.RUNNING
            else:
                return WorkingStatus.FINISHED
        else:
            return WorkingStatus.INIT
    
    def update_module_info(self, r: SimModule):
        info = {}
        if self.clean_robot.query_brush_cmd_status is not WorkingStatus.FINISHED:
            self.brush_status = self.update_status_by_data(self.clean_robot.query_brush(r))
        elif self.clean_robot.query_suck_cmd_status is not WorkingStatus.FINISHED:
            self.suck_status = self.update_status_by_data(self.clean_robot.query_suck(r))
        elif self.clean_robot.query_jet_cmd_status is not WorkingStatus.FINISHED:
            self.jet_status = self.update_status_by_data(self.clean_robot.query_jet_pump(r))
        elif self.clean_robot.query_mop_lift_cmd_status is not WorkingStatus.FINISHED:
            data = self.clean_robot.query_mop_lift(r)
            if data == self.clean_robot.default_data:
                self.mop_lift_status = WorkingStatus.INIT
            elif data[8:10] == "FF":
                self.mop_lift_status = WorkingStatus.FINISHED
            elif data[8:10] == "64":
                self.mop_lift_status = WorkingStatus.RUNNING
        elif self.clean_robot.query_brush_lift_cmd_status is not WorkingStatus.FINISHED:
            data = self.clean_robot.query_brush_lift(r)
            if data == self.clean_robot.default_data:
                self.brush_lift_status = WorkingStatus.INIT
            elif data[8:10] == "64":
                self.brush_lift_status = WorkingStatus.FINISHED
            elif data[8:10] == "FF":
                self.brush_lift_status = WorkingStatus.RUNNING
        elif self.clean_robot.query_ball_valve_cmd_status is not WorkingStatus.FINISHED:
            self.waste_valve_status = self.update_status_by_data(self.clean_robot.query_ball_valve(r))
        elif self.clean_robot.query_water_valve_cmd_status is not WorkingStatus.FINISHED:
            self.clean_valve_status = self.update_status_by_data(self.clean_robot.query_water_valve(r))
        elif self.clean_robot.query_clean_water_cmd_status is not WorkingStatus.FINISHED:
            self.clean_water_level = self.get_clean_water_level(r)
        elif self.clean_robot.query_waste_water_cmd_status is not WorkingStatus.FINISHED:
            self.waste_water_level = self.get_waste_water_level(r)
        else:
            pass
        info['suck_state'] = self.suck_status
        info['brush_state'] = self.brush_status
        info['jet_pump_state'] = self.jet_status
        info['mop_lift_state'] = self.mop_lift_status
        info['brush_lift_state'] = self.brush_lift_status
        info['ball_valve_state'] = self.waste_valve_status
        info['water_valve_state'] = self.waste_water_level
        self.report_info["work_status"] = info

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
        if self.clean_robot.query_all_cmd_status is WorkingStatus.FINISHED:
            self.clean_robot.query_all_cmd_status = WorkingStatus.INIT
            if recv_data != self.clean_robot.default_data:
                state = bin(int(recv_data[12:14], 16))[2:].zfill(8)
                self.clean_water_level = int(recv_data[8:10], 16)
                self.waste_water_level = int(recv_data[10:12], 16)
                self.jet_status = int(state[6:7])
                self.brush_status = int(state[5:6])
                self.suck_status = int(state[4:5])
                self.waste_valve_status = int(state[3:4])
                self.clean_valve_status = int(state[2:3])
                self.mop_lift_status = int(state[1:2])
                self.brush_lift_status = int(state[0:1])
        info['suck_state'] = self.suck_status
        info['brush_state'] = self.brush_status
        info['jet_pump_state'] = self.jet_status
        info['mop_lift_state'] = self.mop_lift_status
        info['brush_lift_state'] = self.brush_lift_status
        info['ball_valve_state'] = self.waste_valve_status
        info['water_valve_state'] = self.waste_water_level
        self.report_info["work_status"] = info

    def suspend(self, r: SimModule):
        r.setWarning(f"script suspend")
        self.status = MoveStatus.SUSPENDED
    
    def cancel(self, r: SimModule):
        r.setWarning(f"script cancel")
        r.setDO(self.add_water_do, False)
        self.clean_robot.ctrl_ball_valve(r, WorkState.CLOSE)
        self.status = MoveStatus.NONE


class CleanRobot:
    def __init__(self, module_obj: Module):
        self.chanel = 2
        self.can_id = 0x605
        self.dlc = 8
        self.extend = False
        self.agv = module_obj
        self.brush_start_time = None
        self.default_data = '0'*16
        self.has_send = False
        self.send_start = None
        self.send_wait_time = 0.008
        
        self.query_brush_cmd_status = WorkingStatus.INIT
        self.query_jet_cmd_status = WorkingStatus.INIT
        self.query_suck_cmd_status = WorkingStatus.INIT
        self.query_brush_lift_cmd_status = WorkingStatus.INIT
        self.query_mop_lift_cmd_status = WorkingStatus.INIT
        self.query_water_valve_cmd_status = WorkingStatus.INIT
        self.query_ball_valve_cmd_status = WorkingStatus.INIT
        self.query_clean_water_cmd_status = WorkingStatus.INIT
        self.query_waste_water_cmd_status = WorkingStatus.INIT
        self.query_all_cmd_status = WorkingStatus.INIT
    
    def ctrl_suck(self, r: SimModule, power=0):
        cmd = Cmd.SUCK
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        recv_data = self.send_cmd(r, cmd)
        if recv_data[0:2] == RecvCmdType.CTRL and recv_data[6:8] == Mechanism.SUCK:
            return recv_data
        return self.default_data
    
    def ctrl_brush(self, r: SimModule, power=0):
        cmd = Cmd.BRUSH
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        recv_data = self.send_cmd(r, cmd)
        if recv_data[0:2] == RecvCmdType.CTRL and recv_data[6:8] == Mechanism.BRUSH:
            return recv_data
        return self.default_data
    
    def ctrl_jet_pump(self, r: SimModule, power=0):
        cmd = Cmd.JET_PUMP
        cmd = cmd[:12] + hex(power)[2:].zfill(2) + cmd[14:]
        recv_data = self.send_cmd(r, cmd)
        if recv_data[0:2] == RecvCmdType.CTRL and recv_data[6:8] == Mechanism.JET_PUMP:
            return recv_data
        return self.default_data
    
    def ctrl_brush_lift(self, r: SimModule, state):
        if state is WorkState.CLOSE:
            cmd = Cmd.BRUSH_LIFT_DOWN
        else:
            cmd = Cmd.BRUSH_LIFT_UP
        recv_data = self.send_cmd(r, cmd)
        if recv_data[0:2] == RecvCmdType.CTRL and recv_data[6:8] == Mechanism.BRUSH_LIFT:
            return recv_data
        return self.default_data
    
    def ctrl_mop_lift(self, r: SimModule, state):
        if state is WorkState.CLOSE:
            cmd = Cmd.MOP_LIFT_DOWN
        else:
            cmd = Cmd.MOP_LIFT_UP
        recv_data = self.send_cmd(r, cmd)
        if recv_data[0:2] == RecvCmdType.CTRL and recv_data[6:8] == Mechanism.MOP_LIFT:
            return recv_data
        return self.default_data
    
    def ctrl_water_valve(self, r: SimModule, state):
        if state is WorkState.OPEN:
            cmd = Cmd.WATER_VALVE_OPEN
        else:
            cmd = Cmd.WATER_VALVE_CLOSE
        recv_data = self.send_cmd(r, cmd)
        if recv_data[0:2] == RecvCmdType.CTRL and recv_data[6:8] == Mechanism.WATER_VALVE:
            return recv_data
        return self.default_data
    
    def ctrl_ball_valve(self, r: SimModule, state):
        if state is WorkState.OPEN:
            cmd = Cmd.BRAIN_BALL_VALVE_OPEN
        else:
            cmd = Cmd.BRAIN_BALL_VALVE_CLOSE
        recv_data = self.send_cmd(r, cmd)
        if recv_data[0:2] == RecvCmdType.CTRL and recv_data[6:8] == Mechanism.BALL_VALVE:
            return recv_data
        return self.default_data
    
    def ctrl_all(self, r: SimModule):
        
        pass
    
    def query_brush(self, r: SimModule):
        self.query_brush_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_BRUSH)
        if recv_data[0:2] == RecvCmdType.QUERY and recv_data[6:8] == Mechanism.BRUSH:
            self.query_brush_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_jet_pump(self, r: SimModule):
        self.query_jet_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_JET_PUMP)
        if recv_data[0:2] == RecvCmdType.QUERY and recv_data[6:8] == Mechanism.JET_PUMP:
            self.query_jet_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_suck(self, r: SimModule):
        self.query_suck_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_SUCK)
        if recv_data[0:2] == RecvCmdType.QUERY and recv_data[6:8] == Mechanism.SUCK:
            self.query_suck_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_brush_lift(self, r: SimModule):
        self.query_brush_lift_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_BRUSH_LIFT)
        if recv_data[0:2] == RecvCmdType.QUERY and recv_data[6:8] == Mechanism.BRUSH_LIFT:
            self.query_brush_lift_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_mop_lift(self, r: SimModule):
        self.query_mop_lift_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_MOP_LIFT)
        if recv_data[0:2] == RecvCmdType.QUERY and recv_data[6:8] == Mechanism.MOP_LIFT:
            self.query_mop_lift_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_water_valve(self, r: SimModule):
        self.query_water_valve_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_WATER_VALVE)
        if recv_data[0:2] == RecvCmdType.QUERY and recv_data[6:8] == Mechanism.WATER_VALVE:
            self.query_water_valve_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_ball_valve(self, r: SimModule):
        self.query_ball_valve_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_BALL_VALVE)
        if recv_data[0:2] == RecvCmdType.QUERY and recv_data[6:8] == Mechanism.BALL_VALVE:
            self.query_ball_valve_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_clean_water(self, r: SimModule):
        self.query_clean_water_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_CLEAN_WATER_LEVEL)
        if recv_data[0:2] == RecvCmdType.METER and recv_data[6:8] == Meter.CLEAN_WATER_METER:
            self.query_clean_water_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_waste_water(self, r: SimModule):
        self.query_waste_water_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_WASTE_WATER_LEVEL)
        if recv_data[0:2] == RecvCmdType.METER and recv_data[6:8] == Meter.WASTE_WATER_METER:
            self.query_waste_water_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def query_all_info(self, r: SimModule):
        self.query_all_cmd_status = WorkingStatus.RUNNING
        recv_data = self.send_cmd(r, Cmd.QUERY_ALL_INFO)
        if recv_data[0:2] == RecvCmdType.ALL and recv_data[6:8] == Mechanism.ALL:
            self.query_all_cmd_status = WorkingStatus.FINISHED
            return recv_data
        return self.default_data
    
    def send_cmd(self, r: SimModule, cmd):
        b64_str, can_id = '', 0
        if not self.has_send:
            r.sendCanFrame(self.chanel, self.can_id, self.dlc, self.extend, cmd)
            data = r.getCanFrame()
            self.has_send = True
            b64_str = data.get('Data', '')
            can_id = data.get('ID', 0)
            self.send_start = time.time()
        if self.has_send and time.time() - self.send_start > self.send_wait_time:
            self.has_send = False
        hex_str = base64.b64decode(b64_str).hex().upper()
        addr = hex_str[2:8]
        self.agv.report_info[cmd] = hex_str
        if can_id + 128 == self.can_id and (cmd[3:5] + cmd[6:8] + cmd[9:11]) == addr:
            return hex_str
        return self.default_data
    
    def init_query_status(self):
        self.query_brush_cmd_status = WorkingStatus.INIT
        self.query_jet_cmd_status = WorkingStatus.INIT
        self.query_suck_cmd_status = WorkingStatus.INIT
        self.query_brush_lift_cmd_status = WorkingStatus.INIT
        self.query_mop_lift_cmd_status = WorkingStatus.INIT
        self.query_water_valve_cmd_status = WorkingStatus.INIT
        self.query_ball_valve_cmd_status = WorkingStatus.INIT
        self.query_clean_water_cmd_status = WorkingStatus.INIT
        self.query_waste_water_cmd_status = WorkingStatus.INIT


class WorkingStatus(IntEnum):
    INIT = 0
    RUNNING = 1
    FINISHED = 2


class WorkState(IntEnum):
    CLOSE = 0
    OPEN = 1
    

class WorkingPower(IntEnum):
    FULL = 100
    HIGH = 80
    MEDIUM = 50
    LOW = 25
    

class Mechanism:
    ALL = '00'
    SUCK = '01'
    BRUSH = '02'
    JET_PUMP = '03'
    BRUSH_LIFT = '04'
    MOP_LIFT = '05'
    WATER_VALVE = '06'
    BALL_VALVE = '07'


class Meter:
    CLEAN_WATER_METER = '03'
    WASTE_WATER_METER = '04'


class RecvCmdType:
    CTRL = '60'
    QUERY = '4B'
    METER = '43'
    ALL = '43'


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
    SET_ALL_STD = "23 02 40 00 32 43 1E 07"   # 以标准功率设定全部机构
    SET_ALL_LOW = "23 02 40 00 28 32 14 07"   # 以低档模式设定全部机构
    SET_ALL_HIGH = "23 02 40 00 46 50 32 07"   # 以高档模式设定全部机构
    QUERY_ALL_INFO = "40 03 40 00 00 00 00 00"  # 查询所有机构的运行状态


class MeanValue:
    """均值滤波"""
    
    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.data = []
        self.threshold = 10
    
    def add_value(self, v):
        if not self.data:
            self.data.append(v)
        elif abs(v - self.get_mean_value()) < self.threshold:
            self.data.append(v)
        while len(self.data) > self.window_size:
            self.data.pop(0)
    
    def get_mean_value(self) -> float:
        return round(sum(self.data) / len(self.data), 5)


if __name__ == '__main__':
    print(0 == WorkingStatus.INIT)
    pass
