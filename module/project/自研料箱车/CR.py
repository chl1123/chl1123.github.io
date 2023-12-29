# -*- coding: utf-8 -*-
# @Date : 2023/12/19
# @Author : CXN
# @File :containerRobot_14.py
# @Version : 2.0
# @Project : 无敌自研料箱车 https://seer-group.coding.net/p/test_center/bug-tracking/issues/2767/detail
# @Update : 重构料箱车控制逻辑
import base64
import json
import math
import sys,platform
import threading
import time
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/battery/')
if platform.machine() == 'aarch64':
    import can

sys.path.append("../syspy")
import syspy.goPath
from syspy import goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.robot import ModuleTool, Motor, MotorType, Robot, GoodsManger

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
    "operation":{
        "value": "zero",
        "default_value":["load","unload","change","zero","take","put","getContainerPos",
        "prePickUp","pickUp",
        "putOnSelfAndPrePickUp",
        "putOnSelfAndPrePickOff",
        "prePickOff","pickOff","can","adjust"],
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
        self.box_code_file = p.loadParam("box_code_file", type="str", default="tag/t0001.tag",
                                         comment="料箱二维码识别文件")
        self.shelf_code_file = p.loadParam("shelf_code_file", type="str", default="tag/t0002.tag",
                                           comment="货架二维码识别文件")
        self.barcode_file = p.loadParam("barcode_file", type="str", default="tag/t0003.tag", comment="条形码识别文件")
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

        self.fill_light_do = 4  # 补光灯DO
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
            self.task_list.extend([Finger(0),MotorCalib(self.stretch_motor_name),MotorCalib(self.lift_motor_name),MotorCalib(self.rotate_motor_name)])
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
            "can":self.can
        }
    def can(self,r:SimModule):
        self.task_list.extend([RecCan3000(r)])
    def zero(self,r:SimModule):
        self.task_list.extend([Stretch(0),Finger(0),Rotate(0),Lift(0)])

    def adjust(self,r:SimModule):
        if self.lift_height:
            self.task_list.append(Lift(self.lift_height))
        if self.rotate_pos:
            self.task_list.append(Rotate(self.rotate_pos))
        self.task_list.append(OpenDO([self.fill_light_do]))
        if self.target_type == "box":
            if self.code_type == "code":
                self.task_list.append(RecHandel(self.box_code_file, True, 10))
            if self.code_type == "barcode":
                self.task_list.append(RecBarcode(self.barcode_file,ModuleTool.get_uuid()))
        elif self.target_type == "shelf":
            if self.code_type == "code":
                self.task_list.append(RecHandel(self.shelf_code_file, True, 10))
            if self.code_type == "barcode":
                self.task_list.append(RecBarcode(self.barcode_file,ModuleTool.get_uuid()))
        self.task_list.append(CloseDO([self.fill_light_do]))

        if self.recAdjust and self.code_type == "code":
            self.task_list.append(Adjust(r))

    def getContainerPos(self,r:SimModule):
        self.task_list.extend([GetContainerPos(r, "unload", self.goods_id, self.self_position)])
    def prePickUp(self,r:SimModule):
        """货叉升降、旋转到某个位置准备取货"""
        self.task_list.extend([RotateAndLift(self.lift_height,self.rotate_pos),Finger(1)])

    def prePickOff(self,r:SimModule):
        """# 从背篓抓取目标料箱并升降到某个位置准备放货"""
        self.task_list.extend([
            GetContainerPos(r, "unload", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("ContainerPos",0),
            Finger(1),  # 打开手指
            Stretch(self.stretch_self_length), # 伸手臂抓箱子
            Finger(0),  # 关闭手指
            Stretch(0),  # 抓到了收回来
            RotateAndLift(self.lift_height, self.rotate_pos),  # 升降并旋转到指定高度
            Finger(1),  # 打开手指
            SetAndClearContainer("clear")
            ])

    def pickOff(self,r:SimModule):
        """# 从货叉放货到货架"""
        self.task_list.extend([
            Finger(1),  # 打开手指
            Stretch(self.stretch_length), # 伸手臂抓箱子
            Stretch(0), # 伸手臂抓箱子
            Finger(0),  # 关闭手指
            ])

    def pick123(self,r:SimModule):
        """# 从货叉放货到货架"""
        self.task_list.extend([
            Finger(1),  # 打开手指
            Finger(0),  # 关闭手指
            ])

    def putOnSelfAndPrePickOff(self,r:SimModule):
        """# 将料箱放到背篓，从背篓抓取目标料箱并升降到某个位置准备放货"""
        self.task_list.extend([
            GetContainerPos(r, "load", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("ContainerPos", 0),  # 下降并旋转到背篓位置
            Stretch(self.stretch_self_length),  # 伸手臂
            Finger(1),  # 开手指
            Stretch(0),  # 收手臂
            SetAndClearContainer("set",self.goods_id),
            GetContainerPos(r, "unload", self.goods_id, self.self_position),  # 获取背篓位置
            Lift("ContainerPos"),  # 升降到背篓位置
            Finger(1),  # 打开手指
            Stretch(self.stretch_self_length),  # 伸手臂抓箱子
            Finger(0),  # 关闭手指
            Stretch(0),  # 抓到了收回来
            RotateAndLift(self.lift_height, self.rotate_pos),  # 升降并旋转到指定高度
            Finger(1),  # 打开手指
            SetAndClearContainer("clear", self.goods_id),
        ])

    def pickUp(self,r:SimModule):
        """从货架抓货到货叉"""
        if self.target_type == "box" and self.code_type == "code":
            self.task_list.extend([
                OpenDO([self.fill_light_do]),
                RecHandel(self.box_code_file, True, 10),
                CloseDO([self.fill_light_do]),
                Adjust(r),
            ])
        self.task_list.extend([
            Finger(1),
            Stretch(),
            Finger(0),
            Stretch(0),
        ])
    def putOnSelfAndPrePickUp(self,r:SimModule):
        """将料箱放到背篓，升降到某个位置准备下一次抓货"""
        self.task_list.extend([
            GetContainerPos(r, "load", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("ContainerPos", 0),  # 下降并旋转到背篓位置
            Stretch(self.stretch_self_length),  # 伸手臂
            Finger(1),  # 开手指
            Stretch(0),  # 收手臂
            RotateAndLift(self.lift_height, self.rotate_pos),  # 升降并旋转到背篓位置
            SetAndClearContainer("set",self.goods_id)
        ])

    def putOnSelf(self,r:SimModule):
        # 将料箱放到背篓
        self.task_list.extend([
            GetContainerPos(r, "load", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("ContainerPos", 0),  # 下降并旋转到背篓位置
            Stretch(self.stretch_self_length),  # 伸手臂
            Finger(1),  # 开手指
            Stretch(0),  # 收手臂
            Finger(0),  # 开手指
            SetAndClearContainer("set", self.goods_id)
        ])

    def load(self,r:SimModule):
        # 升降旋转到指定高度
        self.task_list.append(RotateAndLift(self.lift_height,self.rotate_pos))
        # 如果有识别
        if self.target_type == "box" and self.code_type == "code":
            self.task_list.extend( [
                OpenDO([self.fill_light_do]),
                RecHandel(self.box_code_file, True, 10),
                CloseDO([self.fill_light_do]),
                Adjust(r),
            ])
        # 取货到抓斗
        self.task_list.extend([
            GetContainerPos(r, "load", self.goods_id, self.self_position),  # 获取背篓位置
            Lift(self.lift_height + self.load_height),
            Finger(1),
            Stretch(),
            Finger(0),
            Stretch(0),
        ])
        # 将抓斗的料箱放到背篓
        self.task_list.extend([
            RotateAndLift("ContainerPos", 0),  # 下降并旋转到背篓位置
            Stretch(self.stretch_self_length),  # 伸手臂
            Finger(1),  # 开手指
            Stretch(0),  # 收手臂
            Finger(0),  # 开手指
            SetAndClearContainer("set", self.goods_id)
        ])

    def unload(self,r):
        self.task_list.extend([
            GetContainerPos(r, "unload", self.goods_id, self.self_position),  # 获取背篓位置
            RotateAndLift("ContainerPos", 0),
            Finger(1),  # 打开手指
            Stretch(self.stretch_self_length),
            Finger(0),
            Stretch(0)])
        # 检查有没有箱子
        if self.recBoxLift:
            self.task_list.extend([
                RotateAndLift(self.recBoxLift, self.rotate_pos),
                OpenDO([self.fill_light_do]),
                RecHandel(self.box_code_file, False, 1),
                CloseDO([self.fill_light_do]),
            ])
        self.task_list.extend([
            RotateAndLift(self.lift_height,self.rotate_pos),
            Finger(1),  # 打开手指
            SetAndClearContainer("clear")
            ])
        # 识别放货
        if self.target_type == "shelf" and self.code_type == "code":
            self.task_list.extend( [
                OpenDO([self.fill_light_do]),
                RecHandel(self.shelf_code_file, True, 10),
                CloseDO([self.fill_light_do]),
                Adjust(r),
            ])
        # if self.recAdjust:
        #     self.task_list.append(Adjust(r))
        self.task_list.extend([
            Lift(self.lift_height + self.unload_height),
            Stretch(),
            Stretch(0),
            Finger(0)
            ])

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
        self.task_list.append(Finger(self.finger_pos))

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
        if "recAdjust" in args:
            self.recAdjust = True

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
            if all(self.is_stop):
                r.setMotorCalib(self.motor_name)
                self.is_setMotorCalib = True
        if self.is_setMotorCalib and all(self.is_stop):
            self.status = MoveStatus.FINISHED
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
        state = {
            "cur_c": self.cur_c,
            "status": self.status,
            "self_position": self.self_position,
            "operation": self.operation
        }
        m.cur_c = self.cur_c
        if m.cur_c:
            self.status = MoveStatus.FINISHED
        state["taskid"] = m.task_id
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

    def __init__(self,filename,is_must_ok:bool=True,rec_times_max = 10):
        self.status = MoveStatus.NONE
        self.is_must_ok = is_must_ok
        self.rec_times_max = rec_times_max
        self.rec_times_cur = 0
        self.rec = Rec(filename)

    def reset(self, r,agv):
        r.resetRec()
        self.status = MoveStatus.RUNNING

    def run(self,r: SimModule, m:Module):
        if self.status != MoveStatus.FINISHED:
            if self.rec_times_cur >= self.rec_times_max:
                if self.is_must_ok:
                    self.status = MoveStatus.FAILED
                else:
                    self.status = MoveStatus.FINISHED
            if self.rec.status is MoveStatus.RUNNING or self.rec.status is MoveStatus.NONE:
                r.setNotice(f"----- rec to adjust {self.rec.status.name}------")
                self.rec.run(r, m)
            elif self.rec.status is MoveStatus.FINISHED:
                if self.rec.result:
                    m.result = self.rec.result
                    self.status = MoveStatus.FINISHED
                else:
                    self.rec.reset(r,m)
                    self.rec_times_cur += 1
                if not self.is_must_ok:
                    r.setError(f"放货时已经有货")
                    self.status = MoveStatus.FAILED
        task_state = {"status": self.status, "rec_times_cur": self.rec_times_cur, "taskid": m.task_id}
        m.report_info['RecHandel'] = task_state


class Rec:
    def __init__(self, filename=""):
        self.status = MoveStatus.NONE
        self.filename = filename
        self.result = dict()
    def reset(self, r,agv):
        r.resetRec()
        self.status = MoveStatus.RUNNING
    def run(self, r: SimModule, m:Module):
        rec_status = r.getRecStatus()  # 获取识别状态 0: 初始化, 1: 识别中, 2: 获得结果, 3：识别出错, -1: 未知错误
        if rec_status == 3 or rec_status == -1:  # 识别失败的状态
            r.setNotice("rec failed:{}".format(self.result))
            r.resetRec()
            self.status = MoveStatus.FINISHED
        elif rec_status == 2:  # 识别成功,获得结果
            self.result = r.getRecResult()
            r.resetRec()
            self.status = MoveStatus.FINISHED
            r.setNotice(f"rec success: {self.status.name} {self.result}")
        else:
            r.doRecWithAngle(self.filename,0.0)
        task_state = dict()
        task_state['rec_result'] = self.result
        task_state['status'] = self.status
        task_state['rec_status'] = rec_status
        task_state['file'] = self.filename
        task_state["taskid"] = m.task_id
        m.report_info[f'Rec_{self.filename}'] = task_state


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
                if not m.stretch_length:
                    m.stretch_length = abs(m.result['x']) - m.auto_stretch_odo_len + m.auto_stretch_dist + m.auto_stretch_box_len
                    if m.max_stretch_length < m.stretch_length:
                        r.setError(f"自动计算手臂伸出长度为{m.stretch_length}，大于最大伸缩长度{m.max_stretch_length }。需要检查箱子距离是否太远了")
                        self.status = MoveStatus.FAILED
                        return
                def move(dx, dy, yaw):
                    if abs(yaw) >= 3.0916:
                        return dy
                    if yaw < 0:
                        return dy - dx * math.tan(math.pi + yaw)
                    else:
                        return dy + dx * math.tan(math.pi - yaw)
                code2camera = [m.result['x'], m.result['y'], m.result['z'], m.result['yaw']]  # 目标点在相机坐标系的位置
                task_state["code2camera"] = code2camera
                # agv.yaw_adjust = math.pi/2 + code2camera[3]   # 角度偏差
                self.go_args["coordinate"] = "robot"
                # 根据反馈的yaw来判断rotate调整方向
                if code2camera[3] > 0:
                        m.yaw_adjust = code2camera[3] - math.pi  # 负角度调整
                else:
                        m.yaw_adjust = math.pi + code2camera[3]  # 正角度调整
                # 根据下发货叉的角度，判断行走方向
                if m.rotate_pos > 0:
                    if m.result['y'] >= 0:
                        self.go_args["x"] = 0-move(m.result['x'], m.result['y'], m.result['yaw'])
                    else:
                        self.go_args["x"]= 0-move(m.result['x'], m.result['y'], m.result['yaw'])
                else:
                    if m.result['y'] >= 0:
                        self.go_args["x"] = move(m.result['x'], m.result['y'], m.result['yaw'])
                    else:
                        self.go_args["x"] = move(m.result['x'], m.result['y'], m.result['yaw'])
                self.go_args["y"] = 0
                self.go_args["theta"] = 0
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["reachDist"] = 0.002
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1

                self.rotate.position = m.rotate_pos + m.yaw_adjust

                ok_x = 0.002   # 调整完成阈值
                ok_yaw = 0.03   # 调整完成阈值
                if abs(m.yaw_adjust) >= 0.1396:
                    self.status = MoveStatus.FAILED
                    r.setError("recAdjust fails!!! reach max yaw_adjust.")
                    return
                if abs(self.go_args['x']) < 0.002 and abs(m.yaw_adjust) <= 0.05:   # 调整完成
                    self.status = MoveStatus.FINISHED
                    return
            else:
                r.setError(f"识别调整时，没有识别结果")
                self.status = MoveStatus.FAILED
                return
            self.init = True
        if self.status not in [MoveStatus.FINISHED, MoveStatus.FAILED] and self.init:
            if self.goPath.status == MoveStatus.FINISHED:
                if abs(m.yaw_adjust) <= 0.05:   # 调整完成
                    self.status = MoveStatus.FINISHED
            if self.goPath.status not in [MoveStatus.FINISHED, MoveStatus.FAILED]:
                self.goPath.run(r, self.go_args)
            elif self.rotate.status not in [MoveStatus.FINISHED, MoveStatus.FAILED]:
                self.rotate.run(r, m)
            elif self.goPath.status == MoveStatus.FINISHED and self.rotate.status == MoveStatus.FINISHED:
                self.status = MoveStatus.FINISHED

        task_state["go_path_status"] = self.goPath.status
        task_state["agv.stretch_length"] = m.stretch_length
        task_state["go_args"] = self.go_args
        task_state["status"] = self.status
        task_state["agv yaw_adjust"] = m.yaw_adjust
        task_state["taskid"] = m.task_id

        m.report_info["Adjust"] = task_state

    def reset(self, r,agv):
        self.status = MoveStatus.RUNNING
        self.goPath.reset()


class Finger(TpModule):

    """
    控制手指
    """
    def __init__(self, position):
        super().__init__()
        self.position = position
        self.init = True
        self.left_finger_up_do = 8  # di1
        self.right_finger_up_do = 7   # di6

        self.right_finger_down_do = 6
        self.left_finger_up_di = 1

        self.left_finger_down_do = 9  # di4
        self.right_finger_up_di = 6  # di5

        self.right_finger_down_di = 5
        self.left_finger_down_di = 4
        self.insert = False

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
            if self.position is None:
                r.setError(f"请输入手指的位置")
                self.status = MoveStatus.FAILED
        if self.status != MoveStatus.FINISHED and not self.init:
            if self.position == 1:
                if not ModuleTool.check_DI(r, self.left_finger_up_di):
                    r.setDO(self.left_finger_up_do, True)
                if not ModuleTool.check_DI(r, self.right_finger_up_di):
                    r.setDO(self.right_finger_up_do, True)
                if ModuleTool.check_DI(r, self.left_finger_up_di) and ModuleTool.check_DI(r,self.right_finger_up_di):
                    r.setDO(self.left_finger_up_do, False)
                    r.setDO(self.right_finger_up_do, False)
                    self.status = MoveStatus.FINISHED
            elif self.position == 0:
                if not ModuleTool.check_DI(r, self.left_finger_down_di):
                    r.setDO(self.left_finger_down_do, True)
                if not ModuleTool.check_DI(r,self.right_finger_down_di):
                    r.setDO(self.right_finger_down_do, True)
                if ModuleTool.check_DI(r, self.left_finger_down_di) and ModuleTool.check_DI(r,self.right_finger_down_di):
                    r.setDO(self.left_finger_down_do, False)
                    r.setDO(self.right_finger_down_do, False)
                    self.status = MoveStatus.FINISHED
        task_state["status"] = self.status
        task_state["position"] = self.position
        task_state["taskid"] = m.task_id

        m.report_info[f"Finger_{self.position}"] = task_state


class Lift(TpModule):
    """
    控制手指
    """
    def __init__(self, height):
        super().__init__()
        self.height = height
        self.init = True

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            if self.height is None:
                r.setError(f"请输入升降目标的位置")
                self.status = MoveStatus.FAILED
            if self.height == "ContainerPos":
                self.height = m.low[int(m.cur_c)]
            if self.height < m.min_lift_height:
                r.setWarning(f"lower than the min lift height: {self.height}")
                self.height = m.min_lift_height
            if self.height > m.max_lift_height:
                r.setWarning(f"Out of the max lift height: {self.height}")
                self.height = m.min_lift_height
            if m.stretch_real_pos > m.safe_stretch_length:
                r.setError(f"stretch need to be zero, cannot lift")
                self.status = MoveStatus.FAILED
            self.init = False
        else:
            if self.status != MoveStatus.FINISHED:
                if self.height < m.level2_height:
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
            if self.lift_pos == "ContainerPos":
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

class RecBarcode(TpModule):
    def __init__(self,barcode_file,rec_id):
        super().__init__()
        self.barcode_file = barcode_file
        self.rec_res = None
        self.rec_id = rec_id

    def run(self, r:SimModule,m:Module):
        if self.rec_res and self.rec_res.get("status", 1) == 0:
            self.status = MoveStatus.FINISHED
        else:
            if ModuleTool.delay(0.5):
                self.rec_res = r.RecognizeBarCode(self.barcode_file, self.rec_id)
        state = {"status": self.status, "rec_res": self.rec_res, "taskid": m.task_id}

        m.report_info["RecBarcode"] = state


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

    def setCallBack(self,handleData):
        if not handleData:
            print("Set callback error.It should be implemented the func 'handleData'")
        else:
            self.__callback = handleData

    def createCanBus(self,r:SimModule, channel, bitrate):
        self.bus = can.interface.Bus(bustype='socketcan', channel=channel, bitrate=bitrate)
        __msg_thread = threading.Thread(target=self.__run, args=(r,),name="run")
        __msg_thread.start()  # FIXME: when to join?

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

    def sendCanframe(self,r:SimModule,channel, can_id, dlc, extend, can_string):
        bus = can.interface.Bus(channel, bustype='socketcan')
        msg = can.Message(arbitration_id=can_id, data=can_string, is_extended_id=extend, dlc=dlc)
        bus.send(msg)
        r.setNotice(f'message send: channel={channel}, can_id={hex(can_id)}, dlc={dlc}, extend={extend}, can_string={can_string}')
        bus.shutdown()

    def recvCan(self,r):
        for msg in self.bus:
            if self.can_filter(msg):
                if not self.__callback is None:
                    self.__callback(msg)

    def __run(self,r):
        try:
            while not self.__should_close:
                self.recvCan(r)
        except Exception as e:
            print("recvCan exception:", e)
        finally:
            pass

    def __del__(self):
        self.bus.shutdown()

class RecCan3000(TpModule):
    def __init__(self,r:SimModule):
        super().__init__()
        self.cp = CanPassAarch64()
        self.send_channel = 2
        self.cp.setCallBack(self.handle_data)
        self.cp.createCanBus(r,self.send_channel, 9600)
        self.cp.attachCanID(self.send_channel,1,0)

        self.can_id = 0x609
        self.dlc = 8
        self.extend = False
        self.status = MoveStatus.NONE
        self.result = dict()
        self.send_angel = "40 01 20 01 00 00 00 00"
        self.send_x_y =   "40 01 20 02 00 00 00 00"
        self.send_qr_code1 =   "40 01 20 03 00 00 00 00"
        self.send_qr_code2 =   "40 01 20 04 00 00 00 00"
        self.send_qr_code3 =   "40 01 20 05 00 00 00 00"
        self.send_qr_code4 =   "40 01 20 06 00 00 00 00"

    def handle_data(self,msg):
        print(f"Received CAN message: ID={hex(msg.arbitration_id)}, Data={msg.data}")

    def run(self, r: SimModule, agv):
        self.status = MoveStatus.RUNNING
        # 发送和接收数据帧并解析数据
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_angel)
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_x_y)
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_qr_code1)
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_qr_code2)
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_qr_code3)
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, self.send_qr_code4)
        self.status = MoveStatus.FINISHED



    def send_receive(self, r: SimModule, msg):
        self.cp.sendCanframe(r,self.send_channel, self.can_id, self.dlc, self.extend, msg)
        data = r.getCanFrame(r)
        b64_str = data["Data"]
        byte_str = base64.b64decode(b64_str)
        hex_str = byte_str.hex().upper()
        data["Data"] = hex_str
        can_frame_id_res = data["ID"]
        if can_frame_id_res + 128 != self.can_id:
            return
        d_data = data["Data"]
        dict_obj = msg[3:5] + msg[6:8] + msg[9:11]
        dict_obj_res = d_data[2:8]
        if dict_obj != dict_obj_res:
            return
        return data

    # 解析角度
    def parse_angle(self,data):
        angle = data[1]
        return angle

    # 解析X轴和Y轴位置
    def parse_position(self,data):
        x_axis = (data[3] << 8) | data[2]
        y_axis = (data[5] << 8) | data[4]
        return x_axis, y_axis

    # 解析二维码数据
    def parse_qr_code(self,data):
        if not data:
            return ''
        qr_code = ''.join([chr(b) for b in data[6:10]])
        return qr_code

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


class OpenDO(TpModule):
    def __init__(self, task: list):
        super().__init__()
        self.task = task
        self.opt = [False] * len(self.task)

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            for i, t in enumerate(self.task):
                r.setDO(t, True)
                self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        task_state["taskid"] = m.task_id


class CloseDO(TpModule):
    def __init__(self, task: list):
        super().__init__()
        self.task = task
        self.opt = [False] * len(self.task)

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            for i, t in enumerate(self.task):
                r.setDO(t, False)
                self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        task_state["taskid"] = m.task_id


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
