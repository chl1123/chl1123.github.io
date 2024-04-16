# -*- coding: utf-8 -*-
# @Date: 2024/04/10
# @Author: zhong
# @Version: 1.1
# @Project: SRC2000 清洁机器人
# @Coding: https://seer-group.coding.net/p/robokit/assignments/issues/2631/detail
# @Update: 更新一键控制协议
import base64
import time
import socket
from enum import IntEnum
import sys,can,threading
sys.path.append("../syspy")
#from canpass_aarch64  import CanPassAarch64 as ca64
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

#宏信息
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
    SET_ALL_CLOSED = "23 02 40 00 00 00 00 00"   # 设定全部机构关闭
    QUERY_ALL_INFO = "40 03 40 00 00 00 00 00"  # 查询所有机构的运行状态

class MeanValue:
    """均值滤波"""
    
    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.data = []
        self.threshold = 10
    
    def add_value(self, v):
        if (not self.data) or (abs(v - self.get_mean_value()) < self.threshold):
            self.data.append(v)
        while len(self.data) > self.window_size:
            self.data.pop(0)
    
    def get_mean_value(self) -> float:
        return round(sum(self.data) / len(self.data), 5)

#can通信报文
class CanPassAarch64:
    def __init__(self):
        print("canPassAarch64 start!")
        self.bus = None
        self.__callback = None
        self.__should_close = False
        self.can_ids = []
        self.send_time = 0
        self.res_timeout = 2

    def setCallBack(self, handleData):
        if not handleData:
            print("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__callback = handleData

    def createCanBus(self, r: SimModule, channel, bitrate):
        self.bus = can.interface.Bus(bustype='socketcan', channel=channel, bitrate=bitrate)
        # __msg_thread = threading.Thread(target=self.__run, args=(r,),name="run")
        # __msg_thread.start()  # FIXME: when to join?

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
        print('Attached CAN IDs:', end=' ')
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

    def recvCan(self, r)->dict:
        try:
            start = time.time()
            msg = self.bus.recv(0.1)

            r.logInfo(f"self.bus start {self.bus},{type(self.bus)}")
            if msg and self.can_filter(msg):
                if not self.__callback is None:
                    self.__callback(r, msg)
                r.logInfo(f"start time end {time.time() - start},has rec")
                return msg.data
            r.logInfo(f"start time end {time.time() - start},nor rec")
            return False
        except Exception as e:
            r.setWarning(f"can 通信接受异常,{e}")
            return False

    def __del__(self):
        self.bus.shutdown()

    def close(self):
        self.bus.shutdown()

#辅助函数，快速添加字典
class SetAid:
    @staticmethod
    def add_to_dict(input_dict, *args):
        for pair in args:
            if len(pair) == 2:
                key, value = pair
                input_dict[key] = value
            else:
                return False
        return True

class Module(BasicModule):
    function_dict = {
        'WashStart': 'wash_start',
        'WashEnd': 'wash_end',
        'DustStart': 'dust_start',
        'DustEnd': 'dust_end',
        'AddWater':'add_water',
        'CloseBallValve':'close_ball_valve',
        'CheckInfo':'update_all_info'
    }#写在前面，每个operation执行的对应动作
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
        
        # 清洁机构工作状态
        self.brush_status = WorkingStatus.INIT
        self.jet_status = WorkingStatus.INIT
        self.suck_status = WorkingStatus.INIT
        self.brush_lift_status = WorkingStatus.INIT
        self.mop_lift_status = WorkingStatus.INIT
        self.clean_valve_status = WorkingStatus.INIT
        self.waste_valve_status = WorkingStatus.INIT
        
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
        self.clean_filter = MeanValue(1000)  # 清水液位滤波
        self.waste_filter = MeanValue(1000)  # 污水液位滤波
        self.can_arch64 = CanPassAarch64()
        self.can_arch64.createCanBus(r,channel="can1", bitrate=250)
        self.can_arch64.attachCanID(0x585)
        r.logInfo(f"init args: {args}")
    
    def periodRun(self, r: SimModule) -> bool:
        self.period_run_counter += 1
        if not self.period_init:
            self.period_init = True
        clean_dict = dict()
        agv_speed = dict()
        #字典添加都是用来做输出的方便用户调试，不影响实际运行,代码里的add_to_dict都是这个道理
        SetAid.add_to_dict(clean_dict,("cleanWaterLevel",self.filter_clean_water_level()),("wasteWaterLevel",self.waste_water_level))
        SetAid.add_to_dict(agv_speed,('x',r.getNextSpeed()['x']),('y',r.getNextSpeed()['y']),('rotate',r.getNextSpeed()['rotate']))
        SetAid.add_to_dict(self.report_info,("cleanRobot",clean_dict),("connected",self.is_connected),("scriptStatus",self.status),("time",time.strftime('%Y-%m-%d %H:%M:%S')),\
                             ("agvSpeed",agv_speed),("operation",self.operation),("periodRunCounter",self.period_run_counter),("taskStatus",r.getCurrentTaskStatus()))
        # 同步清洁机器人各机构的工作状态
        self.update_all_info(r)
        if time.time() - self.period_run_start > 0.5:
            self.period_run_start = time.time()
            # 同步液位数据到RBK
            self.save_to_rbk(r, self.rbk_addr1, self.filter_clean_water_level())
            self.save_to_rbk(r, self.rbk_addr2, self.filter_waste_water_level())
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
        
        if self.operation in self.function_dict:
            func_name = self.function_dict[self.operation]
            # 根据函数名获取函数对象，并调用
            getattr(self, func_name)(r)
        else:
            r.setUserError(53910, f"args error: {self.operation}")
            self.status = MoveStatus.FAILED
        
        SetAid.add_to_dict(self.report_info,('args',args),('clean_water',self.clean_water_level),('waste_water',self.waste_water_level),('operation',self.operation))
        r.logInfo(f"clean robot info: {json.dumps(self.report_info)}")
        return self.status
    
    def update_by_task_status(self, r: SimModule):# 同步清洁机器人各机构的工作状态
        task_status = r.getCurrentTaskStatus()
        agv_speed = r.getNextSpeed()
        if task_status == 2:  # Running
            # TODO 根据AGV速度处理业务逻辑
            if self.operation == "WashStart":
                if (agv_speed['x'] < 0.1 or agv_speed['rotate'] > agv_speed['x']) and (self.jet_status == WorkingStatus.RUNNING):
                    self.clean_robot.ctrl_mechanism(self.can_arch64,r,'jet_pump',WorkState.OPEN,0)
                elif self.jet_status != WorkingStatus.RUNNING:
                    self.clean_robot.ctrl_mechanism(self.can_arch64,r,'jet_pump',WorkState.OPEN,self.jet_power)
        # TODO 根据任务状态处理业务逻辑
        else:  # Suspended or Completed or Failed or Canceled
            self.wash_end(r)
 
    
    def connect(self, r: SimModule):
        try:
            self.tcp_client.connect((self.ip, self.port))
        except Exception as e:
            r.logInfo(f"connect error: {e}")
        else:
            self.is_connected = True
    
    @staticmethod
    def pack(addr, v):
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
        register_value1 = v  # 待写入的值，假设为 0xFFFF
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
    
    def save_to_rbk(self, r: SimModule, addr, value):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_ip = self.ip
        server_port = self.port
        try:
            client_socket.connect((server_ip, server_port))
            client_socket.sendall(self.pack(addr, value))
            response_adu = client_socket.recv(1024)
            r.logDebug(f"response_adu: {response_adu}")
            client_socket.close()
        except Exception as e:
            r.logDebug(f"save_to_rbk error: {e}")
    
    #下面是几个基本动作
    def wash_start(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        controls = [
            ('brush_lift', self.brush_lift_status),
            ('mop_lift', self.mop_lift_status),
            ('water_valve', self.clean_valve_status),
            ('suck', self.suck_status, self.suck_power),
            ('brush', self.brush_status, self.brush_power),
            ('jet_pump', self.jet_status, self.jet_power)
        ]
        for control, status, *args in controls:
            if status != WorkingStatus.RUNNING:
                self.clean_robot.ctrl_mechanism(self.can_arch64, r, control, WorkState.OPEN, *args)
                return  # 停止遍历，只执行第一个未运行的控制函数
        else:
            self.status = MoveStatus.FINISHED
    
    def wash_end(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        controls = [
            ('jet_pump', self.jet_status),
            ('suck', self.suck_status),
            ('brush', self.brush_status),
            ('brush_lift', self.brush_lift_status),
            ('mop_lift', self.mop_lift_status),
            ('water_valve', self.clean_valve_status)
        ]
        for control, status in controls:
            if status != WorkingStatus.INIT:
                self.clean_robot.ctrl_mechanism(self.can_arch64, r, control, WorkState.OPEN, 0) \
                    if control in ['jet_pump', 'suck', 'brush'] else self.clean_robot.ctrl_mechanism(self.can_arch64, r, control, WorkState.CLOSE)
                return  # 停止遍历，只执行第一个未初始化的控制函数
        else:
            self.status = MoveStatus.FINISHED
    
    def dust_start(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        if self.mop_lift_status != WorkingStatus.RUNNING:
            self.clean_robot.ctrl_mechanism(self.can_arch64,r,'mop_lift', WorkState.OPEN)
        else:
            self.status = MoveStatus.FINISHED
    
    def dust_end(self, r: SimModule):
        self.status = MoveStatus.RUNNING
        if self.mop_lift_status != WorkingStatus.INIT:
            self.clean_robot.ctrl_mechanism(self.can_arch64,r,'mop_lift', WorkState.CLOSE)
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
            self.clean_robot.ctrl_mechanism(self.can_arch64,r,'ball_valve', WorkState.CLOSE)
        else:
            self.clean_robot.ctrl_mechanism(self.can_arch64,r,'ball_valve', WorkState.OPEN)
        
        if self.waste_water_level < self.min_waste_water_level and self.clean_water_level > self.max_clean_water_level:
            if not self.add_water_time_start:
                self.add_water_time_start = time.time()
            if time.time() - self.add_water_time_start > self.add_water_delay_time:
                self.add_water_time_start = None
                self.status = MoveStatus.FINISHED
    
    def close_ball_valve(self, r: SimModule): #关阀
        if self.waste_valve_status == 1:
            self.clean_robot.ctrl_mechanism(self.can_arch64,r,'ball_valve', WorkState.CLOSE)
        else:
            self.status = MoveStatus.FINISHED
            
    def filter_clean_water_level(self):#水位计算，调用滤波方法
        self.clean_filter.add_value(self.clean_water_level)
        return self.clean_filter.get_mean_value()
        
    def filter_waste_water_level(self):
        self.waste_filter.add_value(self.waste_water_level)
        return self.waste_filter.get_mean_value()

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
            if recv_data != self.clean_robot.default_data:
                state = bin(int(recv_data[12:14], 16))[2:].zfill(8)  # 状态数据变为8位2进制
                self.clean_water_level = int(recv_data[8:10], 16)  # 清水液位
                self.waste_water_level = int(recv_data[10:12], 16)  # 污水液位
                self.jet_status = int(state[6:7])
                self.brush_status = int(state[5:6])
                self.suck_status = int(state[4:5])
                self.waste_valve_status = int(state[3:4])
                self.clean_valve_status = int(state[2:3])
                self.mop_lift_status = int(state[1:2])
                self.brush_lift_status = int(state[0:1])
 
        SetAid.add_to_dict(info,('suck_state',self.suck_status),('brush_state',self.brush_status),('jet_pump_state',self.jet_status),('water_valve_state',self.waste_water_level),\
                           ('mop_lift_state',self.mop_lift_status),('brush_lift_state',self.brush_lift_status),('ball_valve_state',self.waste_valve_status))
        SetAid.add_to_dict(self.report_info,("work_status",info),("query_all_cmd_status",self.clean_robot.query_all_cmd_status))

class CleanRobot:
    def __init__(self, module_obj: Module):
        self.chanel = "can1"
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

    def ctrl_mechanism(self, can_arch64:CanPassAarch64,r: SimModule, mechanism: str, state,power=0):
        cmd_map = {
            "suck": ((Cmd.SUCK[:12] + hex(power)[2:].zfill(2) + Cmd.SUCK[14:]), Mechanism.SUCK),
            "brush": ((Cmd.BRUSH[:12] + hex(power)[2:].zfill(2) + Cmd.BRUSH[14:]), Mechanism.BRUSH),
            "jet_pump": ((Cmd.JET_PUMP[:12] + hex(power)[2:].zfill(2) + Cmd.JET_PUMP[14:]), Mechanism.JET_PUMP),
            "brush_lift": (Cmd.BRUSH_LIFT_DOWN if state is WorkState.CLOSE else Cmd.BRUSH_LIFT_UP, Mechanism.BRUSH_LIFT),
            "mop_lift": (Cmd.MOP_LIFT_DOWN if state is WorkState.CLOSE else Cmd.MOP_LIFT_UP, Mechanism.MOP_LIFT),
            "water_valve": (Cmd.WATER_VALVE_OPEN if state is WorkState.OPEN else Cmd.WATER_VALVE_CLOSE, Mechanism.WATER_VALVE),
            "ball_valve": (Cmd.BRAIN_BALL_VALVE_OPEN if state is WorkState.OPEN else Cmd.BRAIN_BALL_VALVE_CLOSE, Mechanism.BALL_VALVE),
            "open_all": (Cmd.SET_ALL_STD, None),
            "close_all": (Cmd.SET_ALL_CLOSED, None)
        }
        #上面是发送的can控制报文，每个行为对应一个can报文同时对应不同的设施序号，下面对输入的行为设施进行获取并发送报文,其中suck等因为需要把功率加入报文，要做些微调
        cmd, expected_mechanism = cmd_map.get(mechanism, (None, None))
        if cmd is None:
            raise ValueError("Invalid mechanism")
        recv_data = self.send_cmd(can_arch64,r, cmd)
        if expected_mechanism is not None:
            if recv_data[0:2] == RecvCmdType.CTRL and recv_data[6:8] == expected_mechanism:
                return recv_data
        else:
            return recv_data
        return self.default_data
    
    def query_mechanism(self, can_arch64:CanPassAarch64,r: SimModule, mechanism: str):
        cmd_status_map = {
            "brush": (Cmd.QUERY_BRUSH, "query_brush_cmd_status", Mechanism.BRUSH),
            "jet_pump": (Cmd.QUERY_JET_PUMP, "query_jet_cmd_status", Mechanism.JET_PUMP),
            "suck": (Cmd.QUERY_SUCK, "query_suck_cmd_status", Mechanism.SUCK),
            "brush_lift": (Cmd.QUERY_BRUSH_LIFT, "query_brush_lift_cmd_status", Mechanism.BRUSH_LIFT),
            "mop_lift": (Cmd.QUERY_MOP_LIFT, "query_mop_lift_cmd_status", Mechanism.MOP_LIFT),
            "water_valve": (Cmd.QUERY_WATER_VALVE, "query_water_valve_cmd_status", Mechanism.WATER_VALVE),
            "ball_valve": (Cmd.QUERY_BALL_VALVE, "query_ball_valve_cmd_status", Mechanism.BALL_VALVE),
            "clean_water": (Cmd.QUERY_CLEAN_WATER_LEVEL, "query_clean_water_cmd_status", Meter.CLEAN_WATER_METER),
            "waste_water": (Cmd.QUERY_WASTE_WATER_LEVEL, "query_waste_water_cmd_status", Meter.WASTE_WATER_METER),
            "all_info": (Cmd.QUERY_ALL_INFO, "query_all_cmd_status", Mechanism.ALL)
        }
        
        cmd, status_attr, expected_mechanism = cmd_status_map.get(mechanism)
        if cmd is None:
            raise ValueError("Invalid mechanism")
        setattr(self, status_attr, WorkingStatus.RUNNING)
        recv_data = self.send_cmd(can_arch64,r, cmd)
        #上面是设备状态查询和重设，暂时没用
        if recv_data[0:2] == RecvCmdType.QUERY and recv_data[6:8] == expected_mechanism:
            setattr(self, status_attr, WorkingStatus.FINISHED)
            return recv_data
        
        return self.default_data
    
    def send_cmd(self, can_arch64:CanPassAarch64,r: SimModule, cmd):
        b64_str, can_id = '', 0
        if not self.has_send:
            can_arch64.sendCanframe(r,self.chanel, self.can_id, self.dlc, self.extend, cmd)
            data = can_arch64.recvCan(r)
            self.has_send = True
            b64_str = data.get('Data', '')
            can_id = data.get('ID', 0)
            self.send_start = time.time()
        if self.has_send and time.time() - self.send_start > self.send_wait_time:
            self.has_send = False
        hex_str = base64.b64decode(b64_str).hex().upper()
        self.agv.report_info[cmd] = hex_str
        if can_id + 128 == self.can_id and (cmd[3:5] + cmd[6:8] + cmd[9:11]) == hex_str[2:8]:
            return hex_str
        return self.default_data

if __name__ == '__main__':
    print(0 == WorkingStatus.INIT)
    pass
