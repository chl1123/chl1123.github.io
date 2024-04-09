# -*- coding: utf-8 -*-
# @Date : 2023/01/16
# @Author : CXN
# @File :containerRobot_14.py
# @Version : 2.1
# @Project : 牧星料箱车
# @Update : 重构料箱车控制逻辑
import json
import math
import struct
import sys,platform
import time


sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/battery/')
if platform.machine() == 'aarch64':
    import can

sys.path.append("../syspy")
from syspy import goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.robot import ModuleTool, Motor, MotorType, Robot, GoodsManger
try:
    import modbus_tk.defines as cst
    from modbus_tk import modbus_tcp, modbus_rtu
except ImportError:
    import os

    os.system("pip install modbus_tk")
    SimModule.setError(SimModule(), f"modbus_tk needs to be installed")
    os.system("pip install modbus_tk -i https://pypi.tuna.tsinghua.edu.cn/simple")
    import modbus_tk.defines as cst
    from modbus_tk import modbus_tcp
"""
####BEGIN DEFAULT ARGS####
{
    "lift": {
        "value": 0,
        "tips": "货叉抬升高度",
        "type": "float",
        "unit": "m"
    },
    "recBoxLift":{
        "value": 0,
        "tips": "卸货时识别料箱的高度",
        "type": "float",
        "unit": "m"        
    },
    "rotate": {
        "value": 0,
        "tips": "旋转角度",
        "type": "double",
        "unit": "rad"
    },    
    "stretch": {
        "value": 0,
        "tips": "伸缩臂长度",
        "type": "float",
        "unit": "m"
    }, 
    "finger": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "int"
    },
    "finger_can": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "int"
    }, 
    "visionType": {
        "value": "shelf",
        "default_value": ["shelf","box"],
        "tips":"识别对象",
        "type": "complex"
    },
    "visionBinType":{
        "value": "code",
        "default_value":["code", "barcode"],
        "tips":"识别码类型",
        "type": "complex"
    },
    "recAdjust":{
        "value":1,
        "tips":"",
        "type":"int"
    },
    "writeModbus":{
        "value":1,
        "tips":"",
        "type":"int"
    },
    "waitModbus":{
        "value":1,
        "tips":"",
        "type":"int"
    },
    "isNeedComm":{
        "value":1,
        "tips":"",
        "type":"int"
    },
    "operation":{
        "value": "zero",
        "default_value":["load","unload","change","zero","take","put","getContainerPos",
        "prePickUp","pickUp",
        "putOnSelfAndPrePickUp",
        "putOnSelfAndPrePickOff",
        "prePickOff","pickOff","adjust"],
        "tips": "机构动作选项",
        "type": "complex"        
    },
    "selfPosition":{
        "value": 0,
        "tips": "机器人自身库位编号",
        "type": "int"
    },
    "changePosition0":{
        "value": 0,
        "tips": "换层初始库位",
        "type": "int"
    },
    "changePosition1":{
        "value": 0,
        "tips": "换层目标库位",
        "type": "int"
    },
    "putPosition":{
        "value": 0,
        "tips": "put操作目标库位",
        "type": "int"
    },    
    "takePosition":{
        "value": 0,
        "tips": "take操作目标库位",
        "type": "int"
    },   
    "unloadHeight":{
        "value": 0,
        "tips": "rec_offz_shelf",
        "type": "double",
        "unit": "m"
    },
    "loadHeight":{
        "value": 0,
        "tips": "rec_offz_box",
        "type": "double",
        "unit": "m"
    },
    "barcodeHeight":{
        "value": 0,
        "tips": "识别一维码高度",
        "type": "double"
    },
    "goodsId": {
        "value": "",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.writeModbus_value = None
        self.waitModbus_value = None
        self.isNeedComm = 0
        self.finger_can_pos = None
        self.recBoxLift = None
        self.recAdjust = False
        self.cur_c = None
        self.result = None
        self.task_list = []
        self.task_id = 0
        self.operation_status = MoveStatus.NONE
        self.low = dict()
        self.high = dict()
        p = ParamServer(__file__)
        self.rec_type = False if platform.machine() != 'aarch64' else True
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                                   comment=" 运行超时时间")
        self.low[0] = p.loadParam("low0", type="float", default=0.4, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第0层背篓取料箱高度")
        self.high[0] = p.loadParam("high0", type="float", default=0.41, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第0层背篓放料箱高度")
        self.low[1] = p.loadParam("low1", type="float", default=0.82, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第1层背篓取料箱高度")
        self.high[1] = p.loadParam("high1", type="float", default=0.83, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第1层背篓放料箱高度")
        self.low[2] = p.loadParam("low2", type="float", default=1.25, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第2层背篓取料箱高度")
        self.high[2] = p.loadParam("high2", type="float", default=1.26, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第2层背篓放料箱高度")
        self.low[3] = p.loadParam("low3", type="float", default=1.675, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第3层背篓取料箱高度")
        self.high[3] = p.loadParam("high3", type="float", default=1.68, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第3层背篓放料箱高度")
        self.low[4] = p.loadParam("low4", type="float", default=2.095, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第4层背篓取料箱高度")
        self.high[4] = p.loadParam("high4", type="float", default=2.10, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第4层背篓放料箱高度")
        self.stretch_self_length = p.loadParam("stretch_self_length", type="float", default=0.73, maxValue=10000.0,
                                               minValue=0.0, unit="m", comment="取放自身背篓货物时伸出长度")
        self.rec_offz_box = p.loadParam("rec_offz_box", type="float", default=-0.05, maxValue=1000.0, minValue=-1000.0,
                                        unit="m", comment="识别料箱码后抓取料箱时调整高度")
        self.rec_offz_shelf = p.loadParam("rec_offz_shelf", type="float", default=0.02, maxValue=1000.0,
                                          minValue=-1000.0, unit="m", comment="识别货架码后放置料箱时调整高度")
        self.fork_up_limit = p.loadParam("fork_up_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                         comment="货叉上限位DI")
        self.fork_down_limit = p.loadParam("fork_down_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                           comment="货叉下限位DI")
        self.fork_limit = p.loadParam("fork_limit", type="int", default=3, maxValue=100, minValue=-1, unit="",
                                      comment="货叉机械限位限位DI")
        self.min_lift_height = p.loadParam("min_fork_height", type="float", default=0.38, maxValue=10000.0,
                                           minValue=0.0, unit="m", comment="货叉最低高度")
        self.max_lift_height = p.loadParam("max_fork_height", type="float", default=4.5, maxValue=10000.0,
                                           minValue=0.0, unit="m", comment="货叉最大高度")

        self.min_rotate_angle = p.loadParam("min_rotate_angle", type="float", default=80, maxValue=90,
                                            minValue=60, unit="m", comment="货叉最小旋转范围")
        self.max_rotate_angle = p.loadParam("max_rotate_angle", type="float", default=100, maxValue=110,
                                            minValue=90, unit="m", comment="货叉最大旋转范围")

        self.max_stretch_length = p.loadParam("max_stretch_length", type="float", default=0.90, maxValue=10000.0,
                                              minValue=0.0, unit="m", comment="货叉最大伸出长度")
        self.safe_stretch_length = p.loadParam("safe_stretch_length", type="float", default=0.05, maxValue=10000.0,
                                               minValue=0.0, unit="m", comment="货叉升降、旋转操作时伸缩臂安全长度")
        self.safe_lift_height = p.loadParam("safe_lift_height", type="float", default=1.0, maxValue=10000.0,
                                            minValue=0.0, unit="m", comment="货叉安全高度, 货叉导航过程中的最高高度")
        self.level2_height = p.loadParam("level2_height", type="float", default=3.2, maxValue=10000.0,
                                         minValue=0.0, unit="m", comment="门架升降临界高度值")
        self.door_lift_height = p.loadParam("door_lift_height", type="float", default=1.7, maxValue=10000.0,
                                            minValue=0.0, unit="m", comment="门架固定升降高度")
        self.has_fork_sensor = p.loadParam("has_fork_sensor", type="int", default=0,
                                           comment="货叉是否有货物检测传感器，1为有，0为无")
        self.has_tray_sensor = p.loadParam("has_tray_sensor", type="int", default=0,
                                           comment="背篓是否有货物检测传感器，1为有，0为无")
        self.fork_sensor_di = p.loadParam("fork_sensor_di", type="int", default=9, maxValue=100, minValue=-1, unit="",
                                          comment="货叉检测DI")
        self.lift_motor_speed = p.loadParam("lift_motor_speed", type="float", default=1.5, comment="升降电机运转速度")
        self.stretch_motor_speed = p.loadParam("stretch_motor_speed", type="float", default=1.5,
                                               comment="伸缩电机运转速度")
        self.rotate_motor_speed = p.loadParam("rotate_motor_speed", type="float", default=1.5,
                                              comment="旋转电机运转速度")
        self.lift_motor_name = p.loadParam("lift_motor_name", type="str", default="lift", comment="lift_motor_name")
        self.stretch_motor_name = p.loadParam("stretch_motor_name", type="str", default="stretch",
                                              comment="stretch_motor_name")
        self.rotate_motor_name = p.loadParam("rotate_motor_name", type="str", default="rotate",
                                             comment="rotate_motor_name")
        # 以下是自动计算取放货伸手的长度
        self.auto_stretch_box_len = p.loadParam("auto_stretch_box_len", type="float", default=0.6, maxValue=100,
                                                minValue=-1, unit="", comment="箱子长度")
        self.auto_stretch_dist = p.loadParam("auto_stretch_dist", type="float", default=0.01, maxValue=10, minValue=0,
                                             unit="", comment="多伸出的距离")
        self.auto_stretch_odo_len = p.loadParam("auto_stretch_odo_len", type="float", default=0.38, maxValue=100,
                                                minValue=20, unit="", comment="手臂到里程中心的距离")
        # modbus 参数
        self.modbus_IP = p.loadParam("modbus_IP", type="str", default="127.0.0.1",
                                              comment="PLC设备IP")
        self.modbus_port = p.loadParam("modbus_port", type="int", default=502,
                                           comment="PLC设备端口")
        self.modbus_slaveId = p.loadParam("modbus_slaveId", type="int", default=1,
                                       comment="PLC设备ID")
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.goods_id = ""
        # self.logger = ScriptLog("containerRobot", when='H', interval=1, backupCount=48).logger
        self.lift_height = None
        self.door_height = None
        self.stretch_length = None
        self.rotate_pos = None
        self.finger_pos = None
        self.self_position = None
        self.lift_status = None
        self.left_finger_real_pos = -1
        self.right_finger_real_pos = -1
        self.finger_info = dict()
        self.stretch_status = None
        self.stretch_real_pos = 0
        self.lift_real_pos = 0
        self.rotate_real_pos = 0
        self.load_height = None
        self.unload_height = None
        self.collision_di = 0  # 碰撞条DI

        self.lift_zero_di = 8
        self.stretch_limit = 10
        self.rotate_limit = 7
        self.target_type = None
        self.code_type = None
        self.barcode_height = None
        self.rec = None
        self.rec_adjust = None
        self.rotate_status = None
        self.operation = None
        self.container_robot = Robot(r)
        self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name, -1)
        self.stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, self.stretch_motor_name, -1)
        self.rotate_motor = Motor(r, MotorType.LINEAR_MOTOR, self.rotate_motor_name, -1)

        self.yaw_adjust = 0
        self.rec_res = None
        self.rec_id = None

        self.lift_motor_calib = None
        self.stretch_motor_calib = None
        self.rotate_motor_calib = None

        self.operations= self.init_operations()
        self.handle = None

        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init_args(r,args)
            if not self.handle:
                self.handle = self.get_handle(r, args)
                if not self.handle:
                    r.setError(f"找不到输入的操作:{self.operation}，检检查脚本输入参数。")
                    self.status = MoveStatus.FAILED
                    return self.status
            self.init = False
            self.get_move_task_params(r)  # 获取任务的货物 goodsId
        if not self.init and self.status != MoveStatus.FINISHED:
            self.handle_robot(r)
        self.status = self.operation_status
        self.report_data(r)
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def get_motor_calib_state(self, r: SimModule):
        odo_data = r.odo()
        if odo_data.get("motor_info", None):
            motor_info = odo_data["motor_info"]
            for m_f in motor_info:
                if m_f.get("motor_name", None):
                    if m_f["motor_name"] == self.lift_motor_name:
                        self.lift_motor_calib = m_f["calib"]
                    if m_f["motor_name"] == self.stretch_motor_name:
                        self.stretch_motor_calib = m_f["calib"]
                    if m_f["motor_name"] == self.rotate_motor_name:
                        self.rotate_motor_calib = m_f["calib"]
        if self.lift_motor_calib and self.stretch_motor_calib and self.rotate_motor_calib:
            self.report_info["motor_calib"] = True
            return True
    def handle_robot(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
        else:
            self.run_tak_list(r)

    def run_tak_list(self, r):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(r,self)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED

    def get_handle(self, r: SimModule, args: dict):
        # Initialize calibration only if motors are not calibrated.
        if not self.get_motor_calib_state(r):
            self.task_list.extend([MotorCalib(self.stretch_motor_name),MotorCalib(self.rotate_motor_name),MotorCalib(self.lift_motor_name)])
        # Simplify operation retrieval process by checking 'self.operation' first.
        # Retrieve and execute the handler function if it exists.
        handler = self.operations.get(self.operation or next((op for op in args if op in self.operations), None))
        if handler:
            handler(r)
        return handler

    def check_timeout(self,r:SimModule):
        if time.time() - self.start_time > self.timeout:
            r.setError(f"running time out")
            self.status = MoveStatus.FAILED

    def init_operations(self):
        return {
            "prePickUp": self.prePickUp,  #货叉升降、旋转到某个位置准备取货
            "pickUp": self.pickUp,  #从货架抓货到货叉
            "putOnSelf":self.putOnSelf,  # 将料箱放到背篓，升降到某个位置准备下一次抓货
            "putOnSelfAndPrePickUp":self.putOnSelfAndPrePickUp,  # 将料箱放到背篓，升降到某个位置准备下一次抓货
            "putOnSelfAndPrePickOff":self.putOnSelfAndPrePickOff,  # 将料箱放到背篓，从背篓抓取目标料箱并升降到某个位置准备放货
            "prePickOff": self.prePickOff,  # 从背篓抓取目标料箱并升降到某个位置准备放货
            "pickOff": self.pickOff,  # 从货叉放货到货架
            "finger":self.finger_handel,
            "lift":self.lift_handel,
            "rotate": self.rotate_handel,
            "stretch": self.stretch_handel,
            "load": self.load,  # 完整取货
            "unload": self.unload, # 完整放货
            "zero": self.zero,  # 回零位（标零）
            "getContainerPos": self.getContainerPos,  # 获取背篓位置
            "adjust": self.adjust,  # 获取背篓位置
            "can":self.can,
            "waitModbus": self.waitModbus,
            "writeModbus": self.writeModbus
        }

    def can(self, r: SimModule):
        self.task_list = [RecCan3000(r, self.rec_type)]
        self.task_list.append(ModbusWait(self.modbus_IP, self.modbus_port, 4, 1, 3, self.modbus_slaveId))

    def waitModbus(self, r: SimModule):
        self.task_list.append(
            ModbusWait(self.modbus_IP, self.modbus_port, self.waitModbus_value, 0, 3, self.modbus_slaveId))

    def writeModbus(self, r: SimModule):
        self.task_list.append(
            self.task_list.append(ModbusWrite(self.modbus_IP,self.modbus_port,self.writeModbus_value,0,6,self.modbus_slaveId)))


    def zero(self,r:SimModule):
        self.task_list.extend([FingerCan(r,0),StretchZero(0),Rotate(0),Lift(0)])

    def adjust(self,r:SimModule):
        if self.lift_height:
            self.task_list.append(Lift(self.lift_height))
        if self.rotate_pos:
            self.task_list.append(Rotate(self.rotate_pos))
        if self.target_type == "box":
            if self.code_type == "code":
                self.task_list.append(RecHandel(r, True, 10,"box"))
        elif self.target_type == "shelf":
            if self.code_type == "code":
                self.task_list.append(RecHandel(r, True, 10,"shelf"))
        if self.recAdjust and self.code_type == "code":
            self.task_list.append(Adjust(r))
        if self.recAdjust and self.target_type == "box":
            self.task_list.append(Lift(self.lift_height,"box"))
        if self.recAdjust and self.target_type == "shelf":
            self.task_list.append(Lift(self.lift_height,"shelf"))

    def getContainerPos(self,r:SimModule):
        self.task_list.extend([GetContainerPos(r, "load", self.goods_id, self.self_position)])
    def prePickUp(self,r:SimModule):
        """货叉升降、旋转到某个位置准备取货"""
        self.task_list.extend([RotateAndLift(self.lift_height,self.rotate_pos),FingerCan(r,1)])

    def prePickOff(self,r:SimModule):
        """# 从背篓抓取目标料箱并升降到某个位置准备放货"""
        self.task_list.extend([
            GetContainerPos(r, "unload", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("unload",0),
            FingerCan(r,1),  # 打开手指
            Stretch(self.stretch_self_length), # 伸手臂抓箱子
            FingerCan(r,0),  # 关闭手指
            Stretch(0),  # 抓到了收回来
            RotateAndLift(self.lift_height, self.rotate_pos),  # 升降并旋转到指定高度
            FingerCan(r,1),  # 打开手指
            SetAndClearContainer("clear")
            ])

    def pickOff(self,r:SimModule):
        """# 从货叉放货到货架"""
        self.task_list.extend([
            FingerCan(r,1),  # 打开手指
            Stretch(self.stretch_length), # 伸手臂抓箱子
            Stretch(0) , # 伸手臂抓箱子
            FingerCan(r,0),  # 关闭手指
            ])

    def putOnSelfAndPrePickOff(self,r:SimModule):
        """# 将料箱放到背篓，从背篓抓取目标料箱并升降到某个位置准备放货"""
        self.task_list.extend([
            GetContainerPos(r, "load", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("load", 0),  # 下降并旋转到背篓位置
            Stretch(self.stretch_self_length),  # 伸手臂
            FingerCan(r,1),  # 开手指
            Stretch(0),  # 收手臂
            SetAndClearContainer("set",self.goods_id),
            GetContainerPos(r, "unload", self.goods_id, self.self_position),  # 获取背篓位置
            Lift("unload"),  # 升降到背篓位置
            FingerCan(r,1),  # 打开手指
            Stretch(self.stretch_self_length),  # 伸手臂抓箱子
            FingerCan(r,0),  # 关闭手指
            Stretch(0),  # 抓到了收回来
            RotateAndLift(self.lift_height, self.rotate_pos),  # 升降并旋转到指定高度
            FingerCan(r,1),  # 打开手指
            SetAndClearContainer("clear", self.goods_id),
        ])

    def pickUp(self,r:SimModule):
        """从货架抓货到货叉"""
        if self.target_type == "box" and self.code_type == "code":
            self.task_list.extend([
                RecHandel(r, True, 10,"box"),
                Adjust(r),
            ])
        self.task_list.extend([
            FingerCan(r,1),
            Stretch(),
            FingerCan(r,0),
            Stretch(0),
        ])
    def putOnSelfAndPrePickUp(self,r:SimModule):
        """将料箱放到背篓，升降到某个位置准备下一次抓货"""
        self.task_list.extend([
            GetContainerPos(r, "load", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("load", 0),  # 下降并旋转到背篓位置
            Stretch(self.stretch_self_length),  # 伸手臂
            FingerCan(r,1),  # 开手指
            Stretch(0),  # 收手臂
            RotateAndLift(self.lift_height, self.rotate_pos),  # 升降并旋转到背篓位置
            SetAndClearContainer("set",self.goods_id)
        ])

    def putOnSelf(self,r:SimModule):
        # 将料箱放到背篓
        self.task_list.extend([
            GetContainerPos(r, "load", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("load", 0),  # 下降并旋转到背篓位置
            Stretch(self.stretch_self_length),  # 伸手臂
            FingerCan(r,1),  # 开手指
            Stretch(0),  # 收手臂
            FingerCan(r,0),  # 开手指
            SetAndClearContainer("set", self.goods_id)
        ])

    def load(self,r:SimModule):
        # 升降旋转到指定高度
        self.task_list.append(RotateAndLift(self.lift_height,self.rotate_pos))
        # 如果有识别
        if self.target_type == "box" and self.code_type == "code":
            self.task_list.extend( [
                RecHandel(r, True, 10,"box"),
                Adjust(r),
            ])
        # 取货到抓斗
        self.task_list.extend([
            GetContainerPos(r, "load", self.goods_id, self.self_position),  # 获取背篓位置
            Lift(self.lift_height + self.load_height),
            FingerCan(r,1),
            Stretch(),
            FingerCan(r,0),
            Stretch(0)
        ])
        # 返货完成，发送信号给PLC，并等待返回
        if self.isNeedComm:
            self.task_list.append(ModbusWrite(self.modbus_IP,self.modbus_port,2,1,6,self.modbus_slaveId))
            self.task_list.append(ModbusWait(self.modbus_IP,self.modbus_port,3,1,3,self.modbus_slaveId))

        # 将抓斗的料箱放到背篓
        self.task_list.extend([
            RotateAndLift("load", 0),  # 下降并旋转到背篓位置
            #FingerCan(r, 1),  # 开手指
            Stretch(self.stretch_self_length),  # 伸手臂
            FingerCan(r, 1),    #开手指
            Stretch(0),  # 收手臂
            FingerCan(r,0),  # 关手指
            SetAndClearContainer("set", self.goods_id),
            ReportToRds("load")
        ])

    def unload(self,r):
        self.task_list.extend([
            GetContainerPos(r, "unload", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("unload", 0),
            FingerCan(r,1),  # 打开手指
            Stretch(self.stretch_self_length),
            FingerCan(r,0),
            Stretch(0)])
        # 检查有没有箱子
        if self.recBoxLift:
            self.task_list.extend([
                RotateAndLift(self.recBoxLift, self.rotate_pos),
                RecHandel(r, True, 10,"box"),
            ])
        self.task_list.extend([
            RotateAndLift(self.lift_height,self.rotate_pos),
            # FingerCan(r,1),  # 打开手指
            SetAndClearContainer("clear")
            ])
        # 识别放货
        if self.target_type == "shelf" and self.code_type == "code":
            self.task_list.extend( [
                RecHandel(r, True, 10,"shelf"),
                Adjust(r),
            ])
        if self.recAdjust:
            self.task_list.append(Adjust(r))
        self.task_list.extend([
            Lift(self.lift_height + self.unload_height),
            Stretch(),
            FingerCan(r, 1),  # 打开手指
            Stretch(0),
            FingerCan(r,0),
            Rotate(0)
            ])
        if self.isNeedComm:
            self.task_list.append(ModbusWrite(self.modbus_IP,self.modbus_port,5,1,6,self.modbus_slaveId))
            self.task_list.append(ModbusWait(self.modbus_IP,self.modbus_port,6,1,3,self.modbus_slaveId))


    def cancel(self, r: SimModule):
        r.resetRec()
        self.status = MoveStatus.NONE

    def get_move_task_params(self, r):
        """
        获取moveTask参数 goods_id
        """
        move_task = r.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsId':
                self.goods_id = p['string_value']

    def finger_handel(self,r:SimModule):
        """手指控制"""
        self.task_list.append(FingerCan(r,self.finger_pos))

    def lift_handel(self,r:SimModule):
        """升降控制"""
        self.task_list.append(Lift(self.lift_height))

    def rotate_handel(self,r:SimModule):
        """旋转控制"""
        self.task_list.append(Rotate(self.rotate_pos))

    def stretch_handel(self,r:SimModule):
        """手臂伸缩控制"""
        self.task_list.append(Stretch())

    def init_args(self,r:SimModule,args:dict):
        self.goods_id = args.get("goodsId", "")
        self.get_move_task_params(r)
        self.finger_pos = args.get("finger", 0)
        self.finger_can_pos = args.get("finger_can", 0)
        self.lift_height = args.get("lift", 0)
        self.door_height = args.get("lift-door", 0)
        self.stretch_length = args.get("stretch", 0)
        self.rotate_pos = args.get("rotate", 0)
        self.code_type = args.get("visionBinType", "code")
        self.target_type = args.get("visionType", None)
        self.barcode_height = args.get("barcodeHeight", None)
        self.operation = args.get("operation", None)
        self.load_height = args.get("loadHeight", self.rec_offz_box)
        self.unload_height = args.get("unloadHeight", self.rec_offz_shelf)
        self.recBoxLift = args.get("recBoxLift",None)
        self.self_position = args.get("selfPosition", None)
        self.isNeedComm = args.get("isNeedComm", 0)

        self.waitModbus_value = args.get("waitModbus", 0)
        self.writeModbus_value = args.get("writeModbus", 0)

        self.report_info["args"] = args
        self.report_info["load_status"] = 0
        self.report_info["unload_status"] = 0
        if "recAdjust" in args:
            self.recAdjust = True
        if not self.rec_type:
            pass

    def report_data(self, r):
        self.report_info["container_robot"] = self.container_robot.state
        self.report_info['getCount'] = r.getCount()
        self.report_info['task_len'] = len(self.task_list)
        self.report_info['task_id'] = self.task_id

class TpModule:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.start_time = time.time()

    def reset(self, r: SimModule,m:Module):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()

class MotorCalib(TpModule):
    def __init__(self,motor_name):
        super().__init__()
        self.motor_name = motor_name
        self.is_calib = None
        self.is_stop = []
        self.is_setMotorCalib = False
        self.state = {}

    def run(self, r: SimModule,m:Module):
        odo_data = r.odo()
        if odo_data.get("motor_info", None):
            motor_info = odo_data["motor_info"]
            self.is_stop = []
            for m_f in motor_info:
                if m_f.get("motor_name", None):
                    if m_f["motor_name"] == self.motor_name:
                        self.is_calib = m_f.get("calib", None)
                self.is_stop.append(m_f.get("stop", None))
        if self.is_calib:
            self.status = MoveStatus.FINISHED
        else:
            if all(self.is_stop) and not self.is_setMotorCalib:
                r.setMotorCalib(self.motor_name)
                self.is_setMotorCalib = True
        self.state["is_calib"] = self.is_calib
        self.state["is_stop"] = self.is_stop
        self.state["is_setMotorCalib"] = self.is_setMotorCalib
        self.state["status"] = self.status
        self.state["taskid"] = m.task_id

        m.report_info[f"MotorCalib_{self.motor_name}"] = self.state

class GetContainerPos(TpModule):
    def __init__(self, r:SimModule,operation,goods_id,self_position=None):
        super().__init__()
        self.goods_id = goods_id
        self.operation = operation
        self.containers = r.getContainers()
        self.self_position = self_position
        self.goods_manger = GoodsManger(r)
        self.cur_c = None

    def run(self,r: SimModule, m:Module):
        try:
            if self.operation == "load":
                if self.goods_id and self.goods_manger.goods_id_exist(self.goods_id):
                    r.setPickRobotError(53819, f"This good already exists: {self.goods_id}")
                    self.status = MoveStatus.FAILED
                if self.self_position:
                    if self.goods_manger.has_goods(self.self_position):
                        r.setPickRobotError(53820, f"Container {self.self_position} has goods, can not load")
                        self.status = MoveStatus.FAILED
                    self.cur_c = self.self_position
                else:
                    self.cur_c = self.search_operable_container(r, 'load')
                if self.cur_c is None:  # 抓斗取货
                    r.setPickRobotError(53821, f"All containers are full, can not load")
                    self.status = MoveStatus.FAILED
                if self.goods_manger.has_goods("999"):
                    r.setPickRobotError(53820, f"Container 999 has goods, can not load")
                    self.status = MoveStatus.FAILED

            elif self.operation == "unload":
                if self.self_position:
                    if not self.goods_manger.has_goods(self.self_position):
                        r.setPickRobotError(53824, f"Container {self.self_position} is empty, can not unload!")
                        self.status = MoveStatus.FAILED
                    if self.self_position != "999" and self.goods_manger.has_goods("999"):
                        r.setPickRobotError(53820, f"Container 999 has goods, can not unload")
                        self.status = MoveStatus.FAILED
                    self.cur_c = self.self_position
                else:
                    if self.goods_manger.has_goods("999"):
                        self.cur_c = "999"
                    else:
                        self.cur_c = self.goods_manger.get_container_by_goodsId(self.goods_id)
                if self.goods_manger.has_goods("999"):  # 抓斗有货
                    if self.cur_c != "999":
                        r.setPickRobotError(53820, f"Container 999 has goods,but goodsId error, can not unload")
                        self.status = MoveStatus.FAILED
                if not self.cur_c:
                    r.setPickRobotError(53825, f"Goods {self.goods_id} not found, can not unload!")
                    self.status = MoveStatus.FAILED
        except Exception as e:
            r.setNotice(f"{e}")

        m.cur_c = self.cur_c
        if m.cur_c:
            self.status = MoveStatus.FINISHED
        state = {
            "cur_c": self.cur_c,
            "status": self.status,
            "self_position": self.self_position,
            "operation": self.operation,
            "taskid": m.task_id,
            # "height": m.low[int(m.cur_c)]
        }
        m.report_info[f"GetContainerPos_{self.operation}"] = state

    def search_operable_container(self, r, opt):
        if opt == 'load':
            for c in self.containers:
                if not c['has_goods'] and (c['container_name'] != "999"):
                    return c['container_name']
        elif opt == 'unload':
            for c in self.containers:
                if c['has_goods'] and self.goods_id == c['goods_id']:
                    return c['container_name']
        r.setWarning(f"Not found operable container ")
        return None

class RecHandel:

    def __init__(self,r,is_must_ok:bool=True,rec_times_max = 10,rec_type = "box"):
        self.status = MoveStatus.NONE
        self.is_must_ok = is_must_ok
        self.rec_times_max = rec_times_max
        self.rec_times_cur = 0
        self.rec = RecCan3000(r,rec_type)
        self.init = False
        self.rec_type = rec_type

    def reset(self, r,agv):
        self.status = MoveStatus.RUNNING

    def run(self,r: SimModule, m:Module):
        if self.status != MoveStatus.FINISHED:
            if self.rec_times_cur >= self.rec_times_max:
                if self.is_must_ok:
                    self.status = MoveStatus.FAILED
                else:
                    self.status = MoveStatus.FINISHED
            if self.rec.status is MoveStatus.RUNNING or self.rec.status is MoveStatus.NONE:
                self.rec.run(r, m)
            elif self.rec.status is MoveStatus.FINISHED:
                if "qr" in self.rec.result:
                    m.result = self.rec.result
                    self.status = MoveStatus.FINISHED
                    if not self.is_must_ok:
                        r.setError(f"放货时已经有货")
                        self.status = MoveStatus.FAILED
                else:
                    self.rec.reset(r,m)
                    self.rec_times_cur += 1

        task_state = {"status": self.status, "rec_times_cur": self.rec_times_cur, "taskid": m.task_id}
        m.report_info['RecHandel'] = task_state


class ReportToRds:

    def __init__(self,operation = ""):
        self.status = MoveStatus.NONE
        self.operation = operation
        self.init = False

    def reset(self, r,agv):
        self.status = MoveStatus.RUNNING

    def run(self,r: SimModule, m:Module):
        if self.operation == "load":
            m.report_info['load_status'] = 1
        if self.operation == "unload":
            m.report_info['unload_status'] = 1
        self.status = MoveStatus.FINISHED
        task_state = {"status": self.status, "operation": self.operation, "taskid": m.task_id}
        m.report_info['ReportToRds'] = task_state
class Adjust:
    def __init__(self, r:SimModule):
        self.rotate = Rotate(0)
        self.status = MoveStatus.NONE
        self.adjust_count = 0
        self.go_args = dict()
        self.goPath = goPath.Module(r, dict())
        self.init = False
    def run(self, r: SimModule, m:Module):
        task_state = dict()
        self.status = MoveStatus.RUNNING
        if not self.init:
            if m.result:
                code2camera = [m.result['x'], m.result['y'],m.result['yaw']]  # 目标点在相机坐标系的位置
                task_state["code2camera"] = code2camera
                # 取放货高度补偿

                self.go_args["coordinate"] = "robot"
                # 根据下发货叉的角度，判断行走方向
                if m.rotate_pos > 0:
                    self.go_args["x"] = -code2camera[0]
                else:
                    self.go_args["x"] = code2camera[0]
                self.go_args["y"] = 0
                self.go_args["theta"] = 0
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["reachDist"] = 0.002
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                if abs(self.go_args['x']) < 0.002:   # 调整完成
                    self.status = MoveStatus.FINISHED
                    return
            else:
                r.setError(f"识别调整时，没有识别结果")
                self.status = MoveStatus.FAILED
                return
            self.init = True
        if self.status not in [MoveStatus.FINISHED, MoveStatus.FAILED] and self.init:
            if self.goPath.status == MoveStatus.FINISHED:
                self.status = MoveStatus.FINISHED
            if self.goPath.status not in [MoveStatus.FINISHED, MoveStatus.FAILED]:
                self.goPath.run(r, self.go_args)
            elif self.goPath.status == MoveStatus.FINISHED:
                self.status = MoveStatus.FINISHED

        task_state["go_path_status"] = self.goPath.status
        task_state["go_args"] = self.go_args
        task_state["status"] = self.status
        task_state["taskid"] = m.task_id
        m.report_info["Adjust"] = task_state

    def reset(self, r,agv):
        self.status = MoveStatus.RUNNING
        self.goPath.reset()


class Lift(TpModule):
    """
    控制手指
    """
    def __init__(self, height,shape = ''):
        super().__init__()
        self.height = height
        self.shape = shape
        self.init = True

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            if self.height is None:
                r.setError(f"请输入升降目标的位置")
                self.status = MoveStatus.FAILED

            # if self.height < m.min_lift_height:
            #     r.setWarning(f"lower than the min lift height: {self.height}")
            #     self.height = m.min_lift_height
            # if self.height > m.max_lift_height:
            #     r.setWarning(f"Out of the max lift height: {self.height}")
            #     self.height = m.min_lift_height
            # if m.stretch_real_pos > m.safe_stretch_length:
            #     r.setError(f"stretch need to be zero, cannot lift")
            #     self.status = MoveStatus.FAILED
            if self.height == "load":
                self.height = m.high[int(m.cur_c)]
            if self.height == "unload":
                self.height= m.low[int(m.cur_c)]
            if self.shape == "box":
                self.height += m.load_height
            if self.shape == "shelf":
                self.height += m.unload_height
            self.init = False
        if not self.init:
            if self.status != MoveStatus.FINISHED:
                if self.height < m.level2_height:
                    r.setWarning(f"height:{self.height}")
                    if m.container_robot.lift(m.lift_motor, self.height, m.lift_motor_speed):
                        self.status = MoveStatus.FINISHED
                else:
                    r.setWarning(f"Out of the level2_height: {self.height}")
                    self.status = MoveStatus.FINISHED
        r.publishSpeed()
        task_state["status"] = self.status
        task_state["height"] = self.height
        task_state["taskid"] = m.task_id

        m.report_info[f"Lift_{self.height}"] = task_state

class RotateAndLift(TpModule):
    """
    一边旋转一边升降
    """
    def __init__(self, lift_pos,rotate_pos):
        super().__init__()
        self.lift = Lift(lift_pos)
        self.lift_pos = lift_pos
        self.rotate = Rotate(rotate_pos)
        self.init = True
    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
            if self.lift_pos == "load":
                self.lift.height = m.high[int(m.cur_c)]
            if self.lift_pos == "unload":
                self.lift.height = m.low[int(m.cur_c)]
        else:
            if self.lift.status != MoveStatus.FINISHED:
                self.lift.run(r,m)
            if self.rotate.status != MoveStatus.FINISHED:
                self.rotate.run(r,m)
        if self.rotate.status == MoveStatus.FINISHED and self.lift.status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED
        if self.rotate.status == MoveStatus.FAILED or self.lift.status == MoveStatus.FAILED:
            self.status = MoveStatus.FAILED
        task_state["lift_status"] = self.lift.status
        task_state["rotate_status"] = self.rotate.status
        task_state["status"] = self.status
        task_state["taskid"] = m.task_id

        m.report_info["RotateAndLift"] = task_state



class Rotate(TpModule):
    """
    控制手指
    """
    def __init__(self, position):
        super().__init__()
        self.position = position
        self.init = True

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
            if self.position is None:
                r.setError(f"请输入旋转目标的位置")
                self.status = MoveStatus.FAILED
            if self.position < (-m.max_rotate_angle / 180 * math.pi) or self.position > (m.max_rotate_angle / 180 * math.pi):
                r.setError(f"Out of max rotate angle: {self.position}")
                self.status = MoveStatus.FAILED
        if self.status != MoveStatus.FINISHED:
                if m.stretch_real_pos > m.safe_stretch_length:
                    r.setError(f"stretch need to be zero, cannot rotate")
                    self.status = MoveStatus.FAILED
                if m.container_robot.rotate(m.rotate_motor, self.position, m.rotate_motor_speed):
                    self.status = MoveStatus.FINISHED
        r.publishSpeed()
        task_state["status"] = self.status
        task_state["position"] = self.position
        task_state["taskid"] = m.task_id
        m.report_info[f"Rotate_{self.position}"] = task_state


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

    def recvCan(self, r):
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


class FingerCan(TpModule):
    def __init__(self,r:SimModule,position):
        super().__init__()
        self.finger_status = None
        self.position = position
        self.cp = None
        self.send_channel = "can1"
        self.can_id = 0x609
        self.dlc = 8
        self.extend = False
        self.status = MoveStatus.NONE
        self.result = dict()
        self.close_finger = [0x23,0x02,0x20,0x01,0x03,0x20,0xFF,0xFF]

        self.open_finger = [0x23,0x02,0x20,0x02,0x03,0x20,0x00,0x00]
        self.finger_status_sensor = [0x40,0x00,0x20,0x01,0x00,0x00,0x00,0x00]
        self.finger_status_code = [0x40,0x00,0x20,0x02,0x00,0x00,0x00,0x00]
        self.init = True

    def run(self, r: SimModule, m:Module):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()

        res ={}
        if self.init:
            self.init = False
            self.cp = CanPassAarch64()
            self.cp.createCanBus(r, self.send_channel, 500)
            self.cp.attachCanID(0x589)
        if not self.init:
            self.get_finger_status(r)
            if self.finger_status:
                error = self.finger_status.get("finger_error_status")
                # if error != 0:
                #     self.status = MoveStatus.FAILED
                #     if error == 1:
                #         r.setError(f"伸缩限位传感器异常(伸缩前后限位传感器同时触发):{error}")
                #         return
                #     elif error == 2:
                #         r.setError(f"货叉货位传感器异常(往料仓放货，但是传感器没有触发):{error}")
                #         return
                #     elif error == 3:
                #         r.setError(f"旋转零位传感器异常(旋转左、中、右限位传感器右两个以上同时触发):{error}")
                #     elif error == 4:
                #         r.setError(f"挡杆动作超时异常（挡杆被卡住，动作没有执行到位）:{error}")
                #         return
                #     else:
                #         r.setError(f"finger_error_status:{error}")
                #         return
                finger_left_code = self.finger_status.get("finger_left_code")
                finger_right_code = self.finger_status.get("finger_right_code")
                if not finger_right_code and not finger_left_code :
                    return
                if self.position == 1:
                    self.cp.sendCanframe(r, self.send_channel, self.can_id, self.dlc, self.extend,
                                         self.open_finger)
                    if finger_left_code <= 1100 and finger_right_code >= 1900:
                        self.status = MoveStatus.FINISHED
                        self.cp.close()
                    else:
                        self.cp.sendCanframe(r, self.send_channel, self.can_id, self.dlc, self.extend,
                                             self.open_finger)
                        open_res = self.cp.recvCan(r)
                        res["open_res"] = str(open_res)

                else:
                    self.cp.sendCanframe(r, self.send_channel, self.can_id, self.dlc, self.extend,
                                         self.close_finger)
                    if finger_left_code >= 1900 and finger_right_code <= 1100:
                        self.status = MoveStatus.FINISHED
                        self.cp.close()
                    else:
                        self.cp.sendCanframe(r, self.send_channel, self.can_id, self.dlc, self.extend,
                                             self.close_finger)
                        close_res = self.cp.recvCan(r)
                        res["close_res"] = str(close_res)

        state = {
            "res":res,
            "finger_status":self.finger_status,
            "status":self.status,
            "position":self.position,
            "task_id":m.task_id
        }

        m.report_info[f"FingerCan_{self.position}"] = state

    def get_finger_status(self,r:SimModule):
        """
        故障ID:
            1：伸缩限位传感器异常(伸缩前后限位传感器同时触发)
            2：货叉货位传感器异常(往料仓放货，但是传感器没有触发)
            3：旋转零位传感器异常(旋转左、中、右限位传感器右两个以上同时触发)
            4：挡杆动作超时异常（挡杆被卡住，动作没有执行到位）
        传感器状态:
            bit0:伸缩机构远端限位传感器:1-触发，0-不触发
            bit1:伸缩机构近端限位传感器:1-触发，0-不触发
            bit2:货叉货位传感器:        1-触发，0-不触发
            bit3:挡杆电机位置:          1-落下，0-立起来
            bit4:旋转左侧限位传感器:    1-触发，0-不触发
            bit5:旋转中心限位传感器:    1-触发，0-不触发
            bit6:旋转右侧限位传感器:    1-触发，0-不触发
            bit7:上视摄像头状态位:      1-失联，0-正常连接
            挡杆电机传感器值范围：0~10，根据位置输出相应值
            挡杆电机编码器值范围:0~4096,根据位置输出相应值

        :param r:
        :return:
        """
        self.finger_status = {}
        time_start_finger = time.time()
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.finger_status_sensor)
        finger_status_sensor_res = self.cp.recvCan(r)

        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.finger_status_code)
        finger_status_code_res = self.cp.recvCan(r)
        if finger_status_sensor_res:
            finger_error_status= struct.unpack('<B', finger_status_sensor_res[4:5])[0]
            finger_sensor_status= struct.unpack('<B', finger_status_sensor_res[5:6])[0]
            finger_sensor_left= struct.unpack('<B', finger_status_sensor_res[6:7])[0]
            finger_sensor_right= struct.unpack('<B', finger_status_sensor_res[7:8])[0]
            self.finger_status["finger_error_status"] = finger_error_status
            self.finger_status["finger_sensor_status"] = finger_sensor_status
            self.finger_status["finger_sensor_left"] = finger_sensor_left
            self.finger_status["finger_sensor_right"] = finger_sensor_right
        if finger_status_code_res:
            finger_left_code= struct.unpack('<H', finger_status_code_res[4:6])[0]
            finger_right_code= struct.unpack('<H', finger_status_code_res[6:8])[0]
            self.finger_status["finger_left_code"] = finger_left_code
            self.finger_status["finger_right_code"] = finger_right_code
        self.finger_status["time"] = time.time() - time_start_finger



class FingerCanOpen(TpModule):
    def __init__(self,r:SimModule,position):
        super().__init__()
        self.finger_status = None
        self.position = position
        self.cp = CanPassAarch64()
        self.send_channel = "can1"
        self.cp.createCanBus(r,self.send_channel, 500)
        self.cp.attachCanID(0x589)
        self.can_id = 0x609
        self.dlc = 8
        self.extend = False
        self.status = MoveStatus.NONE
        self.result = dict()
        self.close_finger = [0x23,0x02,0x20,0x01,0x03,0x20,0xFF,0xFF]
        self.open_finger = [0x23,0x02,0x20,0x02,0x03,0x20,0x00,0x00]
        self.finger_status_sensor = [0x40,0x00,0x20,0x01,0x00,0x00,0x00,0x00]
        self.finger_status_code = [0x40,0x00,0x20,0x02,0x00,0x00,0x00,0x00]

    def run(self, r: SimModule, m:Module):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()
        self.get_finger_status(r)
        res ={}
        if self.finger_status:
            error = self.finger_status.get("finger_error_status")
            finger_left_code = self.finger_status.get("finger_left_code")
            finger_right_code = self.finger_status.get("finger_right_code")
            self.cp.sendCanframe(r, self.send_channel, self.can_id, self.dlc, self.extend,
                                 self.open_finger)
            if finger_left_code <= 1100 and finger_right_code >= 1900:
                self.status = MoveStatus.FINISHED
            else:
                self.cp.sendCanframe(r, self.send_channel, self.can_id, self.dlc, self.extend,
                                     self.open_finger)
                open_res = self.cp.recvCan(r)
                res["open_res"] = str(open_res)
        state = {
            "res":res,
            "finger_status":self.finger_status,
            "status":self.status,
            "position":self.position,
            "task_id":m.task_id
        }

        m.report_info[f"FingerCanOpen"] = state

    def get_finger_status(self,r:SimModule):
        self.finger_status = {}
        time_start_finger = time.time()
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.finger_status_sensor)
        finger_status_sensor_res = self.cp.recvCan(r)

        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.finger_status_code)
        finger_status_code_res = self.cp.recvCan(r)
        if finger_status_sensor_res and finger_status_sensor_res:
            finger_error_status= struct.unpack('<B', finger_status_sensor_res[4:5])[0]
            finger_sensor_status= struct.unpack('<B', finger_status_sensor_res[5:6])[0]
            finger_sensor_left= struct.unpack('<B', finger_status_sensor_res[6:7])[0]
            finger_sensor_right= struct.unpack('<B', finger_status_sensor_res[7:8])[0]
            finger_left_code= struct.unpack('<H', finger_status_code_res[4:6])[0]
            finger_right_code= struct.unpack('<H', finger_status_code_res[6:8])[0]
            self.finger_status = {
                "finger_error_status":finger_error_status,
                "finger_sensor_status":finger_sensor_status,
                "finger_sensor_left":finger_sensor_left,
                "finger_sensor_right":finger_sensor_right,
                "finger_left_code":finger_left_code,
                "finger_right_code":finger_right_code,
                "times":time.time()- time_start_finger
            }



class FingerCanClose(TpModule):
    def __init__(self,r:SimModule,position):
        super().__init__()
        self.finger_status = None
        self.position = position
        self.cp = CanPassAarch64()
        self.send_channel = "can1"
        self.cp.createCanBus(r,self.send_channel, 500)
        self.cp.attachCanID(0x589)
        self.can_id = 0x609
        self.dlc = 8
        self.extend = False
        self.status = MoveStatus.NONE
        self.result = dict()
        self.close_finger = [0x23,0x02,0x20,0x01,0x03,0x20,0xFF,0xFF]
        self.open_finger = [0x23,0x02,0x20,0x02,0x03,0x20,0x00,0x00]
        self.finger_status_sensor = [0x40,0x00,0x20,0x01,0x00,0x00,0x00,0x00]
        self.finger_status_code = [0x40,0x00,0x20,0x02,0x00,0x00,0x00,0x00]

    def run(self, r: SimModule, m:Module):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()
        self.get_finger_status(r)
        res ={}
        if self.finger_status:
            error = self.finger_status.get("finger_error_status")
            finger_left_code = self.finger_status.get("finger_left_code")
            finger_right_code = self.finger_status.get("finger_right_code")
            self.cp.sendCanframe(r, self.send_channel, self.can_id, self.dlc, self.extend,
                                 self.close_finger)
            if finger_left_code >= 1900 and finger_right_code <= 1100:
                self.status = MoveStatus.FINISHED
            else:
                self.cp.sendCanframe(r, self.send_channel, self.can_id, self.dlc, self.extend,
                                     self.close_finger)
                close_res = self.cp.recvCan(r)
                res["close_res"] = str(close_res)
        state = {
            "res":res,
            "finger_status":self.finger_status,
            "status":self.status,
            "position":self.position,
            "task_id":m.task_id
        }

        m.report_info[f"FingerCanClose"] = state

    def get_finger_status(self,r:SimModule):
        self.finger_status = {}
        time_start_finger = time.time()
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.finger_status_sensor)
        finger_status_sensor_res = self.cp.recvCan(r)

        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.finger_status_code)
        finger_status_code_res = self.cp.recvCan(r)
        finger_error_status= struct.unpack('<B', finger_status_sensor_res[4:5])[0]
        finger_sensor_status= struct.unpack('<B', finger_status_sensor_res[5:6])[0]
        finger_sensor_left= struct.unpack('<B', finger_status_sensor_res[6:7])[0]
        finger_sensor_right= struct.unpack('<B', finger_status_sensor_res[7:8])[0]
        finger_left_code= struct.unpack('<H', finger_status_code_res[4:6])[0]
        finger_right_code= struct.unpack('<H', finger_status_code_res[6:8])[0]
        self.finger_status = {
            "finger_error_status":finger_error_status,
            "finger_sensor_status":finger_sensor_status,
            "finger_sensor_left":finger_sensor_left,
            "finger_sensor_right":finger_sensor_right,
            "finger_left_code":finger_left_code,
            "finger_right_code":finger_right_code,
            "times":time.time()- time_start_finger
        }
class RecCan3000(TpModule):
    def __init__(self,r:SimModule,rec_type):
        super().__init__()
        self.cp = CanPassAarch64()
        self.rec_type = rec_type
        self.send_channel = "can1"
        # self.cp.setCallBack(self.handle_data)
        self.cp.createCanBus(r,self.send_channel, 500)
        self.cp.attachCanID(0x589)
        self.can_id = 0x609
        self.dlc = 8
        self.extend = False
        self.status = MoveStatus.NONE
        self.result = dict()
        self.send_angel_shelf = [0x40,0x01,0x20,0x01,0x00,0x00,0x00,0x00]
        self.send_x_y_shelf =   [0x40,0x01,0x20,0x02,0x00,0x00,0x00,0x00]
        self.send_qr_code1_shelf =   [0x40,0x01,0x20,0x03,0x00,0x00,0x00,0x00]
        self.send_qr_code2_shelf =   [0x40,0x01,0x20,0x04,0x00,0x00,0x00,0x00]
        self.send_qr_code3_shelf =   [0x40,0x01,0x20,0x05,0x00,0x00,0x00,0x00]
        self.send_qr_code4_shelf =   [0x40,0x01,0x20,0x06,0x00,0x00,0x00,0x00]

        self.send_angel_box = [0x40,0x01,0x20,0x07,0x00,0x00,0x00,0x00]
        self.send_x_y_box =   [0x40,0x01,0x20,0x08,0x00,0x00,0x00,0x00]
        self.send_qr_code1_box =   [0x40,0x01,0x20,0x09,0x00,0x00,0x00,0x00]
        self.send_qr_code2_box =   [0x40,0x01,0x20,0x0A,0x00,0x00,0x00,0x00]
        self.send_qr_code3_box =   [0x40,0x01,0x20,0x0B,0x00,0x00,0x00,0x00]
        self.send_qr_code4_box =   [0x40,0x01,0x20,0x0C,0x00,0x00,0x00,0x00]
    def send_recv_can_frame(self, r, channel, can_id, dlc, extend, send_data):
        self.cp.sendCanframe(r, channel, can_id, dlc, extend, send_data)
        res = self.cp.recvCan(r)
        return res
    def run(self, r: SimModule, m:Module):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()
        # 发送和接收数据帧并解析数据
        if self.rec_type == "shelf":
            send_angel_res = self.send_recv_can_frame(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_angel_shelf)
            send_x_y_res = self.send_recv_can_frame(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_x_y_shelf)
            send_qr_code1_res = self.send_recv_can_frame(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_qr_code1_shelf)
            send_qr_code2_res = self.send_recv_can_frame(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_qr_code2_shelf)
            send_qr_code3_res = self.send_recv_can_frame(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_qr_code3_shelf)
            send_qr_code4_res = self.send_recv_can_frame(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_qr_code4_shelf)


        else:
            send_angel_res = self.send_recv_can_frame(r, self.send_channel, self.can_id, self.dlc, self.extend,self.send_angel_box)
            send_x_y_res = self.send_recv_can_frame(r, self.send_channel, self.can_id, self.dlc, self.extend,self.send_x_y_box)
            send_qr_code1_res = self.send_recv_can_frame(r, self.send_channel, self.can_id, self.dlc, self.extend,self.send_qr_code1_box)
            send_qr_code2_res = self.send_recv_can_frame(r, self.send_channel, self.can_id, self.dlc, self.extend,self.send_qr_code2_box)
            send_qr_code3_res = self.send_recv_can_frame(r, self.send_channel, self.can_id, self.dlc, self.extend,self.send_qr_code3_box)
            send_qr_code4_res = self.send_recv_can_frame(r, self.send_channel, self.can_id, self.dlc, self.extend,self.send_qr_code4_box)


        res = {
            "send_angel_res":str(send_angel_res),
            "send_x_y_res":str(send_x_y_res),
            "send_qr_code1_res":str(send_qr_code1_res),
            "send_qr_code2_res":str(send_qr_code2_res),
            "send_qr_code3_res":str(send_qr_code3_res),
            "send_qr_code4_res":str(send_qr_code4_res),
            "times":time.time()-self.start_time
        }
        try:
            if send_angel_res and send_x_y_res and send_qr_code1_res and send_qr_code2_res and send_qr_code2_res and send_qr_code3_res and send_qr_code4_res:
                angel_r = struct.unpack('<f', send_angel_res[4:8])[0]
                x_r = struct.unpack('<hh', send_x_y_res[4:8])[0]
                y_r = struct.unpack('<hh', send_x_y_res[4:8])[1]
                qr1_r = send_qr_code1_res[4:8].decode()
                qr2_r = send_qr_code2_res[4:8].decode()
                qr3_r = send_qr_code3_res[4:8].decode()
                qr4_r = send_qr_code4_res[4:8].decode()
                if angel_r:

                    if self.rec_type == "shelf":
                        m.unload_height += y_r*0.25*0.001
                    if self.rec_type == "box":
                        m.load_height += y_r*0.25*0.001
                    self.result = {
                        "unload_height":m.unload_height,
                        "load_height":m.load_height,
                        "yaw":angel_r,
                        "x":x_r*0.25*0.001,
                        "y":y_r*0.25*0.001,
                        "qr":qr1_r+qr2_r+qr3_r+qr4_r,
                    }
        except Exception as e:
            r.setNotice(f"RecCan3000 error:{e}")
        state = {
                "res":res,
                "result":self.result,
                "status":self.status,
                "taskid":m.task_id
            }
        self.status = MoveStatus.FINISHED
        r.setWarning(f"{state}")
        m.report_info["RecCan3000"] = state

    def reset(self, r,s):
        self.status = MoveStatus.RUNNING


class Stretch(TpModule):
    """
    控制手臂
    """
    def __init__(self, position = None):
        super().__init__()
        self.position = position
        self.init = True

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
            if self.position is None:
                self.position = m.stretch_length
            if self.position > m.max_stretch_length:
                r.setWarning(f"Out of max stretch length: {self.position}")
                self.position = m.max_stretch_length
        if not self.init and self.status != MoveStatus.FINISHED:
            if m.container_robot.stretch(m.stretch_motor, self.position, m.stretch_motor_speed):
                self.status = MoveStatus.FINISHED
        r.publishSpeed()
        task_state["status"] = self.status
        task_state["position"] = self.position
        task_state["taskid"] = m.task_id
        m.report_info[f"Stretch_{self.position}"] = task_state



class ModbusWait(TpModule):
    """
    等待 modbus 的值
    """
    def __init__(self, ip,port,addr,value,functionCode,slave=1):
        super().__init__()
        self.addr = addr
        self.value = value
        self.slave = slave
        self.modbus = None
        self.ip = ip
        self.port = port
        self.functionCode = functionCode
        self.init = True
    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
            self.modbus = modbus_tcp.TcpMaster(self.ip, self.port, 10)
        if not self.init and self.status != MoveStatus.FINISHED:
            if self.modbus:
                if self.functionCode == 1:
                    res = self.modbus.execute(self.slave, cst.READ_COILS, self.addr, 1)
                elif self.functionCode == 2:
                    res = self.modbus.execute(self.slave, cst.READ_DISCRETE_INPUTS, self.addr, 1)
                elif self.functionCode == 3:
                    res = self.modbus.execute(self.slave, cst.READ_HOLDING_REGISTERS, self.addr, 1)
                elif self.functionCode == 4:
                    res = self.modbus.execute(self.slave, cst.READ_INPUT_REGISTERS, self.addr, 1)
                else:
                    r.setError("function core error,need 1,2,3,4")
                    self.status = MoveStatus.FAILED
                    return
                m.report_info["res"] = res
                if res == (self.value,):
                    self.status = MoveStatus.FINISHED
        if self.status in [MoveStatus.FINISHED,MoveStatus.FAILED]:
            if self.modbus:
                self.modbus.close()
        task_state["status"] = self.status
        task_state["taskid"] = m.task_id
        m.report_info[f"ModbusWait_{self.value}"] = task_state




class ModbusWrite(TpModule):
    """
    写 modbus 的值
    """
    def __init__(self, ip,port,addr,value,functionCode,slave=1):
        super().__init__()
        self.addr = addr
        self.value = value
        self.slave = slave
        self.modbus = None
        self.ip = ip
        self.port = port
        self.functionCode = functionCode
        self.init = True
    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
            self.modbus = modbus_tcp.TcpMaster(self.ip, self.port, 10)
        if not self.init and self.status != MoveStatus.FINISHED:
            if self.modbus:
                if self.functionCode == 5:
                    res = self.modbus.execute(self.slave, cst.WRITE_SINGLE_COIL, self.addr, output_value=self.value)
                    if res is not None:
                        if res[1] == 1:
                            pass
                        elif self.value == 1:
                            self.value = 65280
                elif self.functionCode == 6:
                    res = self.modbus.execute(self.slave, cst.WRITE_SINGLE_REGISTER, self.addr, output_value=self.value)
                elif self.functionCode == 15:
                    res = self.modbus.execute(self.slave, cst.WRITE_MULTIPLE_COILS, self.addr, output_value=self.value)

                elif self.functionCode == 16:
                    res = self.modbus.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, self.addr, output_value=self.value)
                else:
                    r.setError("function core error")
                    self.status = MoveStatus.FAILED
                    return
                m.report_info["res"] = res
                if res is not None:
                    if res == (self.addr, self.value):
                        self.status = MoveStatus.FINISHED
        if self.status in [MoveStatus.FINISHED, MoveStatus.FAILED]:
            if self.modbus:
                self.modbus.close()
        task_state["status"] = self.status
        task_state["taskid"] = m.task_id
        m.report_info[f"ModbusWrite_{self.value}"] = task_state

class StretchZero(TpModule):
    """
    控制手臂
    """
    def __init__(self, position = None):
        super().__init__()
        self.position = position
        self.init = True

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
        if not self.init and self.status != MoveStatus.FINISHED:
            if m.container_robot.stretch(m.stretch_motor, 0, m.stretch_motor_speed):
                self.status = MoveStatus.FINISHED
        r.publishSpeed()
        task_state["status"] = self.status
        task_state["position"] = self.position
        task_state["taskid"] = m.task_id
        m.report_info[f"StretchZero"] = task_state

class SetAndClearContainer(TpModule):
    def __init__(self, operation, goodsId="", msg=""):
        super().__init__()
        self.operation = operation
        self.goodsId = goodsId
        self.msg = msg

    def run(self, r: SimModule, m: Module):
        if self.operation == "set":
            r.setContainer(m.cur_c, self.goodsId, self.msg)
        elif self.operation == "clear":
            r.clearContainer(m.cur_c)
        self.status = MoveStatus.FINISHED
        task_state = {"msg": self.msg, "cur_c": m.cur_c, "goodsId": self.goodsId, "operation": self.operation,
                      "status": self.status, "taskid": m.task_id}
        m.report_info["SetAndClearContainer"] = task_state

class DelayTime(TpModule):
    def __init__(self, time_delay: int):
        super().__init__()
        self.time_delay = time_delay

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if ModuleTool.delay(self.time_delay):
            self.status = MoveStatus.FINISHED
        task_state["time"] = self.time_delay
        task_state["status"] = self.status
        task_state["taskid"] = m.task_id
        r.logDebug(json.dumps(task_state))




if __name__ == '__main__':
    pass
