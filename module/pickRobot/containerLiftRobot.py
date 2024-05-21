# -*- coding: utf-8 -*-
# @Date : 2024/05/15
# @Author : zhong
# @Version : 1.3
# @Project : 抱夹式料箱车
# Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/6117/detail
# @Update : 增加 offset_x 补偿值
import json
import math
import sys
import time

sys.path.append("../syspy")
import goPath
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import ModuleTool, Motor, MotorType, Robot, GoodsManger

"""
####BEGIN DEFAULT ARGS####
{
    "lift": {
        "value": 0,
        "tips": "货叉抬升高度",
        "type": "float",
        "unit": "m"
    },
    "lift-door": {
        "value": 0,
        "tips": "门架抬升高度",
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
    "clamp": {
        "value": 0,
        "tips": "抱夹机构位置",
        "type": "float",
        "unit": "m"
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
        "default_value":["load","unload","recBoxBarcode","zero","take","put"],
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
    },
    "code_file": {
        "value": "",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.check_safe_height = 0
        self.rec_box = None
        self.stretch_motor_stop = None
        self.rotate_motor_stop = None
        self.lift_motor_stop = None
        self.clamp_motor_stop = None
        self.zeroing = None
        self.cur_c = None
        p = ParamServer(__file__)
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                                   comment=" 运行超时时间")
        self.low = dict()
        self.high = dict()
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
        self.low[5] = p.loadParam("low5", type="float", default=2.515, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第5层背篓取料箱高度")
        self.high[5] = p.loadParam("high5", type="float", default=2.525, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第5层背篓放料箱高度")
        self.tray_stretch_length = p.loadParam("tray_stretch_length", type="float", default=0.73, maxValue=10000.0,
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
        self.max_clamp_length = p.loadParam("max_clamp_length", type="float", default=0.038, unit="m", comment="抱夹机构最大值")
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
        self.clamp_motor_name = p.loadParam("clamp_motor_name", type="str", default="clamping", comment="clamp_motor_name")
        self.stretch_motor_name = p.loadParam("stretch_motor_name", type="str", default="stretch",
                                              comment="stretch_motor_name")
        self.rotate_motor_name = p.loadParam("rotate_motor_name", type="str", default="rotate",
                                             comment="rotate_motor_name")
        self.lift_height_after_clamp = p.loadParam("lift_height_after_clamp", type="float", default=0.035,
                                                   comment="抱夹抓取物料后上升的高度")
        self.lift_height_before_clamp = p.loadParam("lift_height_before_clamp", type="float", default=0.035,
                                                      comment="抱夹松开物料前下降的高度")
        # 以下是自动计算取放货伸手的长度
        self.auto_stretch_box_len = p.loadParam("auto_stretch_box_len", type="float", default=0.6, maxValue=100,
                                                minValue=-1, unit="", comment="箱子长度")
        self.auto_stretch_dist = p.loadParam("auto_stretch_dist", type="float", default=0.01, maxValue=10, minValue=0,
                                             unit="", comment="多伸出的距离")
        self.auto_stretch_odo_len = p.loadParam("auto_stretch_odo_len", type="float", default=0.38, maxValue=100,
                                                minValue=20, unit="", comment="手臂到里程中心的距离")
        self.offset_x = p.loadParam("offset_x", type="float", default=0, comment="针对识别结果误差在x方向的补偿值")
        
        self.init = True
        
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.goods_id = ""
        self.lift_height = None
        self.door_height = None
        self.stretch_length = None
        self.rotate_pos = None
        self.clamp_pos = None
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
        self.clamp_real_pos = 0
        self.load_height = 0
        self.unload_height = 0
        # 手指控制DO
        self.left_finger_up_do = 8  # di1
        self.right_finger_up_do = 7  # di6
        self.right_finger_down_do = 6  # di5
        self.left_finger_down_do = 9  # di4
        # 手指到位DI
        self.left_finger_up_di = 1
        self.left_finger_down_di = 4
        self.right_finger_up_di = 6
        self.right_finger_down_di = 5
        
        self.fill_light_do = 4  # 补光灯DO
        self.collision_di = 0  # 碰撞条DI
        self.light_st_time = None
        
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
        self.containers = None
        self.container_robot = Robot(r)
        self.goods_manger = GoodsManger(r)
        self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name, -1)
        self.stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, self.stretch_motor_name, -1)
        self.rotate_motor = Motor(r, MotorType.LINEAR_MOTOR, self.rotate_motor_name, -1)
        self.clamp_motor = Motor(r, MotorType.LINEAR_MOTOR, self.clamp_motor_name, -1)
        self.load_step = [False] * 15
        self.unload_step = [False] * 14
        self.change_step = [False] * 10
        self.rec_box_lift_step = [False] * 5
        self.zero_step = [False] * 4
        self.zero_by_rbk_step = [False] * 4
        self.opt_step = [False]*10
        self.yaw_adjust = 0
        self.rec_res = None
        self.rec_id = None
        self.rec_box_lift = None
        self.finger_open_start = False
        
        self.lift_motor_calib = None
        self.stretch_motor_calib = None
        self.rotate_motor_calib = None
        self.clamp_motor_calib = None
        
        self.set_lift_motor_calib = None
        self.set_stretch_motor_calib = None
        self.set_rotate_motor_calib = None
        self.set_clamp_motor_calib = None
        
        r.logInfo(f"init args: {args}")
    
    def periodRun(self, r: SimModule) -> bool:
        self.report_info["odo"] = r.odo()
        r.setInfo(json.dumps(self.report_info))
        r.logDebug(json.dumps(self.report_info))
        return True
    
    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        self.report_info["getCount_run"] = r.getCount()
        if self.init:
            # self.close_finger(r)
            self.motor_calib(r)
            self.goods_id = args.get("goodsId", "")
            self.get_move_task_params(r)
            self.finger_pos = args.get("finger", 0)
            self.lift_height = args.get("lift", 0)
            self.door_height = args.get("lift-door", 0)
            self.stretch_length = args.get("stretch", 0)
            self.rotate_pos = args.get("rotate", 0)
            self.clamp_pos = args.get("clamp", 0)
            self.rec_box_lift = args.get("recBoxLift", 0)
            if self.rec_box_lift:
                self.rec_box = Rec(self.box_code_file, max_rec_times=1)
            self.code_type = args.get("visionBinType", "code")
            self.target_type = args.get("visionType", None)
            self.barcode_height = args.get("barcodeHeight", None)
            self.operation = args.get("operation", None)
            self.load_height = args.get("loadHeight", self.rec_offz_box)
            self.unload_height = args.get("unloadHeight", self.rec_offz_shelf)
            self.containers = r.getContainers()
            self.goods_manger = GoodsManger(r)
            self.self_position = args.get("selfPosition", None)
            self.rec_id = ModuleTool.get_uuid()
            self.box_code_file = args.get("code_file", self.box_code_file)
            if "recAdjust" in args:
                if self.operation == "load":
                    self.rec_adjust = RecAdjust(r, self.box_code_file)
                if self.operation == "unload":
                    self.rec_adjust = RecAdjust(r, self.shelf_code_file)
            if self.target_type == "box" and self.code_type == "code":
                self.rec = Rec(self.box_code_file)
            elif self.target_type == "shelf" and self.code_type == "code":
                self.rec = Rec(self.shelf_code_file)
        
        if time.time() - self.start_time > self.timeout:
            r.setError(f"running time out")
            self.status = MoveStatus.FAILED
        self.update_report_info(r)
        if not self.init:
            if self.operation is not None:
                if self.operation == "zero":
                    if self.zero(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "load":
                    if self.load(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "unload":
                    if self.unload(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "recBoxBarcode":
                    self.rec_box_barcode(r)
                elif self.operation == "take":
                    pass
                elif self.operation == "put":
                    pass
                else:
                    r.setError(f"args error: {args}")
                    self.status = MoveStatus.FAILED
            else:
                if "lift" in args:
                    if self.lift(r, self.lift_height):
                        self.status = MoveStatus.FINISHED
                elif "lift-door" in args:
                    if self.lift_door(r, self.door_height):
                        self.status = MoveStatus.FINISHED
                elif "rotate" in args:
                    if self.rotate(r, self.rotate_pos):
                        self.status = MoveStatus.FINISHED
                elif "stretch" in args:
                    if self.stretch(r, self.stretch_length):
                        self.status = MoveStatus.FINISHED
                elif "clamp" in args:
                    if self.clamp(r, self.clamp_pos):
                        self.status = MoveStatus.FINISHED
                elif "visionType" in args:
                    if self.code_type == "barcode":
                        if self.rec_barcode(r):
                            self.status = MoveStatus.FINISHED
                    elif self.code_type == "code":
                        if self.rec_qrcode(r):
                            self.status = MoveStatus.FINISHED
        r.publishSpeed()
        self.update_report_info(r)
        self.get_motor_calib_state(r)
        self.report_info['args'] = args
        self.report_info['motor_calib'] = [self.lift_motor_calib, self.stretch_motor_calib, self.rotate_motor_calib]
        self.report_info['task_status'] = self.status
        self.report_info['goodsId'] = self.goods_id
        self.report_info['containers'] = self.containers
        self.report_info['zero_step'] = self.zero_step
        self.report_info['motor_info'] = self.container_robot.state or -1
        if self.status == MoveStatus.FAILED or self.status == MoveStatus.FINISHED:
            r.setDO(self.fill_light_do, False)
        if self.status == MoveStatus.FINISHED:
            r.logInfo(json.dumps(self.report_info))
        r.setInfo(json.dumps(self.report_info))
        r.logDebug(json.dumps(self.report_info))
        return self.status
    
    def motor_calib(self, r: SimModule):
        self.get_motor_calib_state(r)
        if self.lift_motor_calib and self.stretch_motor_calib and self.rotate_motor_calib and self.clamp_motor_calib:
            self.init = False
        else:
            if not self.zero_by_rbk_step[0]:
                self.zero_by_rbk_step[0] = True
            elif self.zero_by_rbk_step[0] and not self.zero_by_rbk_step[1]:
                if not self.set_stretch_motor_calib:
                    if self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                        r.setMotorCalib(self.stretch_motor_name)
                        self.set_stretch_motor_calib = True
                if self.stretch_motor_calib:
                    self.zero_by_rbk_step[1] = True
            elif self.zero_by_rbk_step[1] and not self.zero_by_rbk_step[2]:
                if self.lift_motor_stop and self.rotate_motor_stop and self.clamp_motor_stop:
                    r.setMotorCalib(self.rotate_motor_name)
                    r.setMotorCalib(self.lift_motor_name)
                    r.setMotorCalib(self.clamp_motor_name)
                    self.set_rotate_motor_calib = True
                    self.set_lift_motor_calib = True
                    self.set_clamp_motor_calib = True
                if self.lift_motor_calib:
                    self.zero_by_rbk_step[2] = True
                if self.rotate_motor_calib and self.clamp_motor_calib:
                    self.zero_by_rbk_step[3] = True
            if all(self.zero_by_rbk_step):
                self.init = False

    def get_motor_calib_state(self, r: SimModule):
        odo_data = r.odo()
        if odo_data.get("motor_info", None):
            motor_info = odo_data["motor_info"]
            for m_f in motor_info:
                calib = None
                stop = None
                if m_f.get("calib", None):
                    calib = m_f["calib"]
                if m_f.get("stop", None):
                    stop = m_f["stop"]
                if m_f.get("motor_name", None):
                    if m_f["motor_name"] == self.lift_motor_name:
                        self.lift_motor_calib = calib
                        self.lift_motor_stop = stop
                    if m_f["motor_name"] == self.stretch_motor_name:
                        self.stretch_motor_calib = calib
                        self.stretch_motor_stop = stop
                    if m_f["motor_name"] == self.rotate_motor_name:
                        self.rotate_motor_calib = calib
                        self.rotate_motor_stop = stop
                    if m_f["motor_name"] == self.clamp_motor_name:
                        self.clamp_motor_calib = calib
                        self.clamp_motor_stop = stop
        return True

    def cancel(self, r: SimModule):
        r.resetRec()
        # self.close_finger(r)
        r.setDO(self.fill_light_do, False)
        self.status = MoveStatus.NONE

    def get_move_task_params(self, r):
        """
        获取moveTask参数
        """
        move_task = r.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsId':
                self.goods_id = p['string_value']

    def zero(self, r: SimModule):
        """
        机构复位
        :param r:
        :return:
        """
        self.get_motor_calib_state(r)
        self.zeroing = True
        r.logInfo(f"----- running zero ------")
        if not self.zero_step[0]:
            self.zero_step[0] = self.clamp(r, 0)
        elif self.zero_step[0] and not self.zero_step[1]:
            self.zero_step[1] = self.stretch(r, 0)
        elif self.zero_step[1] and not self.zero_step[2]:
            self.zero_step[2] = self.rotate(r, 0)
            self.zero_step[3] = self.lift(r, 0)
        elif self.zero_step[2] and not self.zero_step[3]:
            self.zero_step[3] = self.lift(r, 0)
        r.logDebug(f"zero_step:{self.zero_step}")
        if all(self.zero_step):
            return True

        return False
    
    def lift(self, r, height):
        r.logInfo(f"----- running lift ------")
        if height < self.min_lift_height:
            # r.setWarning(f"lower than the min lift height: {height}")
            height = self.min_lift_height
        if height > self.max_lift_height:
            r.setError(f"Out of the max lift height: {height}")
            return False
        # if self.stretch_real_pos > self.safe_stretch_length:
        #     r.setError(f"stretch need to be zero, cannot lift")
        if height < self.level2_height:
            if self.container_robot.lift(self.lift_motor, height, self.lift_motor_speed):
                return True
        else:
            r.setWarning(f"Out of the level2_height: {height}")
            return True
        return False
    
    def lift_door(self, r, height):
        r.logInfo(f"----- running lift_door ------")
        if height < self.door_lift_height:
            # return self.container_robot.lift_door(self.lift_door_motor, height)
            return True
        else:
            r.setError(f"Out of the max lift-door height: {height}")
        return False
    
    def finger(self, r, pos):
        r.logInfo(f"----- running finger ------")
        if not self.finger_open_start:
            self.finger_open_start = time.time()
        else:
            if time.time() - self.finger_open_start > 3:
                r.setError(f"finger open error")
                r.setDO(self.left_finger_up_do, False)
                r.setDO(self.right_finger_up_do, False)
                r.setDO(self.left_finger_down_do, False)
                r.setDO(self.right_finger_down_do, False)
                self.status = MoveStatus.FAILED
                return
        if pos == 1:
            r.setDO(self.left_finger_up_do, True)
            r.setDO(self.right_finger_up_do, True)
            if ModuleTool.check_DI(r, self.left_finger_up_di) and ModuleTool.check_DI(r, self.right_finger_up_di):
                self.left_finger_real_pos, self.right_finger_real_pos = 1, 1
                r.setDO(self.left_finger_up_do, False)
                r.setDO(self.right_finger_up_do, False)
                self.finger_open_start = False
                return True
        elif pos == 0:
            r.setDO(self.left_finger_down_do, True)
            r.setDO(self.right_finger_down_do, True)
            r.logInfo(f"----- open finger do  ------")
            if ModuleTool.check_DI(r, self.left_finger_down_di) and ModuleTool.check_DI(r, self.right_finger_down_di):
                self.left_finger_real_pos, self.right_finger_real_pos = 0, 0
                r.setDO(self.left_finger_down_do, False)
                r.setDO(self.right_finger_down_do, False)
                self.finger_open_start = False
                return True
        return False
    
    def close_finger(self, r):
        r.setDO(self.left_finger_up_do, False)
        r.setDO(self.right_finger_up_do, False)
        r.setDO(self.left_finger_down_do, False)
        r.setDO(self.right_finger_down_do, False)
    
    def update_finger_info(self, r):
        if ModuleTool.check_DI(r, self.left_finger_down_di):
            self.left_finger_real_pos = 0
        elif ModuleTool.check_DI(r, self.left_finger_up_di):
            self.left_finger_real_pos = 1
        if ModuleTool.check_DI(r, self.right_finger_down_di):
            self.right_finger_real_pos = 0
        elif ModuleTool.check_DI(r, self.right_finger_up_di):
            self.right_finger_real_pos = 1
        self.finger_info["left_finger"] = self.left_finger_real_pos
        self.finger_info["right_finger"] = self.right_finger_real_pos
        
    def clamp(self, r: SimModule, pos):
        r.logInfo(f"----- running clamp ------")
        if pos > self.max_clamp_length:
            r.setWarning(f"Out of max clamp pos: {pos}")
            pos = self.max_clamp_length
        if self.container_robot.stretch(self.clamp_motor, pos):
            return True
        return False
    
    def stretch(self, r, length):
        r.logInfo(f"----- running stretch ------")
        if length > self.max_stretch_length:
            r.setWarning(f"Out of max stretch length: {length}")
            length = self.max_stretch_length
        if self.container_robot.stretch(self.stretch_motor, length, self.stretch_motor_speed):
            return True
        return False
    
    def rotate(self, r, pos):
        r.logInfo(f"----- running rotate ------")
        if pos < (-self.max_rotate_angle / 180 * math.pi) or pos > (self.max_rotate_angle / 180 * math.pi):
            r.setError(f"Out of max rotate angle: {pos}")
            self.status = MoveStatus.FAILED
            return False
        
        if self.stretch_real_pos > self.safe_stretch_length:
            r.setError(f"stretch need to be zero, cannot rotate")
            self.status = MoveStatus.FAILED
            return False
        if self.container_robot.rotate(self.rotate_motor, pos, self.rotate_motor_speed):
            return True
        return False
    
    def rec_barcode(self, r):
        """
        识别一维码
        @param r:
        @return:
        """
        if not self.change_step[0]:
            r.setDO(self.fill_light_do, True)
            if ModuleTool.check_DO(r, self.fill_light_do):
                if ModuleTool.delay(0.1):
                    self.change_step[0] = True
        else:
            if self.rec_res and self.rec_res.get("status", 1) == 0:
                r.setDO(self.fill_light_do, False)
                self.report_info["barcode"] = self.rec_res['barCode']
                return self.rec_res['barCode']
            else:
                if ModuleTool.delay(0.3):
                    self.rec_res = r.RecognizeBarCode(self.barcode_file, self.rec_id)
                self.report_info["barcode"] = "None"
            self.report_info["rec_id"] = self.rec_id
    
    def rec_box_barcode(self, r: SimModule):
        """
        指定货叉高度和角度位置识别一维码
        """
        if time.time() - self.start_time > 20:
            r.setWarning(f"No code recognized!")
            self.status = MoveStatus.FAILED
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(r, self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(r, self.rotate_pos)
        if self.opt_step[0] and self.opt_step[1] and not self.opt_step[2]:
            self.rec_barcode(r)
            if self.rec_res and self.rec_res.get("status", 1) == 0:
                self.opt_step[2] = True
        if all(self.opt_step[0:3]):
            self.status = MoveStatus.FINISHED
    
    def rec_qrcode(self, r):
        """
        识别料箱、货架二维码
        @param r:
        @return:
        """
        if not self.change_step[0]:
            r.setDO(self.fill_light_do, True)
            if ModuleTool.check_DO(r, self.fill_light_do):
                if ModuleTool.delay(0.1):
                    self.change_step[0] = True
        else:
            if self.rec.status is MoveStatus.FINISHED:
                self.rec.reset(r)
                r.setDO(self.fill_light_do, False)
                return True
            elif self.rec.status is MoveStatus.FAILED:
                r.setDO(self.fill_light_do, False)
                return False
            else:
                self.rec.run(r, self)
            return False
    
    def load(self, r):
        r.logInfo(f"----- running load  {self.goods_id}------")
        load_info = dict()
        if not self.cur_c:
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
            r.logInfo(f"load begin: {json.dumps(self.containers)}")
            if self.cur_c is None:  # 车体满载了
                r.setPickRobotError(53821, f"All containers are full, can not load")
                self.status = MoveStatus.FAILED
                return
            if self.goods_manger.has_goods("999"):  # 货叉已载货
                r.setPickRobotError(53820, f"Container 999 has goods, can not load")
                self.status = MoveStatus.FAILED
                return
        else:
            if not self.load_step[0]:
                self.load_step[0] = self.clamp(r, 0) and self.lift(r, self.lift_height)
            if not self.load_step[1]:
                self.load_step[1] = self.rotate(r, self.rotate_pos)
            elif self.load_step[0] and self.load_step[1] and not self.load_step[2]:
                if self.barcode_height is not None:
                    self.lift(r, self.barcode_height)
                    self.load_step[2] = self.goods_id == self.rec_barcode(r)
                else:
                    self.load_step[2] = True
            elif self.load_step[2] and not self.load_step[3]:
                if self.rec_adjust is not None:
                    if self.light_st_time is None:
                        r.setDO(self.fill_light_do, True)
                        self.light_st_time = time.time()
                    if time.time() - self.light_st_time > 0.1:  # 延时0.1秒
                        if self.rec_adjust.status is MoveStatus.FINISHED:
                            r.setDO(self.fill_light_do, False)
                            self.load_step[3] = True
                        elif self.rec_adjust.status is MoveStatus.FAILED:
                            self.status = MoveStatus.FAILED
                        else:
                            self.rec_adjust.run(r, self)
                else:
                    self.load_height = 0
                    self.load_step[3] = True
            elif self.load_step[3] and not self.load_step[4]:
                self.load_step[4] = self.lift(r, self.lift_height + self.load_height)
            elif self.load_step[4] and not self.load_step[5]:
                self.load_step[5] = self.stretch(r, self.stretch_length)
            elif self.load_step[5] and not self.load_step[6]:
                self.load_step[6] = self.clamp(r, self.clamp_pos)
            elif self.load_step[6] and not self.load_step[7]:
                self.load_step[7] = self.lift(r, self.lift_height + self.load_height + self.lift_height_after_clamp)
            elif self.load_step[7] and not self.load_step[8]:
                self.load_step[8] = self.stretch(r, 0)
            elif self.load_step[8] and (not self.load_step[9] or not self.load_step[10]):
                if not self.load_step[9]:
                    self.load_step[9] = self.rotate(r, 0)
                if self.cur_c == "999":
                    self.load_step[:15] = [True] * 14
                else:
                    if not self.load_step[10]:
                        self.load_step[10] = self.lift(r, self.high[int(self.cur_c)])
            elif self.load_step[9] and self.load_step[10] and not self.load_step[11]:
                self.load_step[11] = self.stretch(r, self.tray_stretch_length)
            elif self.load_step[11] and not self.load_step[12]:
                self.load_step[12] = self.lift(r, self.high[int(self.cur_c)] - self.lift_height_before_clamp)
            elif self.load_step[12] and not self.load_step[13]:
                self.load_step[13] = self.clamp(r, 0)
            elif self.load_step[13] and not self.load_step[14]:
                self.load_step[14] = self.stretch(r, 0)
            
            load_info['load_step'] = self.load_step
            load_info['cur_container'] = self.cur_c
            load_info['goodsId'] = self.goods_id
            load_info['load_step'] = self.load_step
            self.report_info["load_info"] = load_info
            if all(self.load_step[:15]):
                # 在完成取货的所有动作后，增加背篓货物数据
                r.setContainer(self.cur_c, self.goods_id, "")
                return True
    
    def unload(self, r):
        r.logInfo(f"----- running unload ------")
        unload_info = dict()
        
        if not self.cur_c:
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
                    return
            if not self.cur_c:
                r.setPickRobotError(53825, f"Goods {self.goods_id} not found, can not unload!")
                self.status = MoveStatus.FAILED
                return
            r.logInfo(f"unload begin: {json.dumps(self.containers)}")
        else:
            if self.cur_c == "999":
                self.unload_step[:6] = [True] * 6
            else:
                if not self.unload_step[0] or not self.unload_step[1] or not self.unload_step[2]:
                    if not self.unload_step[0]:
                        self.unload_step[0] = self.lift(r, self.low[int(self.cur_c)])
                    if not self.unload_step[1]:
                        self.unload_step[1] = self.clamp(r, 0)
                    if not self.unload_step[2]:
                        self.unload_step[2] = self.rotate(r, 0)
                elif self.unload_step[1] and self.unload_step[2] and not self.unload_step[3]:
                    self.unload_step[3] = self.stretch(r, self.tray_stretch_length)
                elif self.unload_step[3] and not self.unload_step[4]:
                    if not self.change_step[0]:
                        self.change_step[0] = self.clamp(r, self.clamp_pos)
                    elif self.change_step[0] and not self.change_step[1]:
                        self.change_step[1] = self.lift(r, self.low[int(self.cur_c)] + self.lift_height_after_clamp)
                    self.unload_step[4] = self.change_step[0] and self.change_step[1]
                elif self.unload_step[4] and not self.unload_step[5]:
                    if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                        if not self.unload_step[6]:
                            self.unload_step[6] = self.lift(r, self.lift_height)
                        if not self.unload_step[7]:
                            self.unload_step[7] = self.rotate(r, self.rotate_pos)
                    self.unload_step[5] = self.stretch(r, 0)
            
            if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                if self.rec_box_lift:
                    if not self.unload_step[6]:
                        if not self.rec_box_lift_step[0]:
                            self.rec_box_lift_step[0] = self.rotate(r, self.rotate_pos)
                        if not self.rec_box_lift_step[1]:
                            self.rec_box_lift_step[1] = self.lift(r, self.rec_box_lift)
                        if self.rec_box_lift_step[0] and self.rec_box_lift_step[1]:
                            self.unload_step[6] = True
                    if not self.unload_step[7] and self.unload_step[6]:
                        if self.rec_box is not None:
                            if not self.rec_box_lift_step[2]:
                                self.rec_box.status = MoveStatus.RUNNING
                                self.rec_box.is_error = True
                                r.setDO(self.fill_light_do, True)
                                if ModuleTool.check_DO(r, self.fill_light_do):
                                    if ModuleTool.delay(0.3):
                                        self.rec_box_lift_step[2] = True
                            if not self.rec_box_lift_step[3] and self.rec_box_lift_step[2]:
                                if self.rec_box.status is MoveStatus.FINISHED:
                                    self.rec_box.reset(r)
                                    self.rec_box.is_error = None
                                    r.setDO(self.fill_light_do, False)
                                    if self.rec_box.has_goods and not self.rec_box.goods_out_dist:
                                        r.setError("shelf had goods!!!")
                                        self.status = MoveStatus.FAILED
                                        return
                                    else:
                                        self.rec_box_lift_step[3] = True
                                elif self.rec_box.status is MoveStatus.FAILED:
                                    r.setDO(self.fill_light_do, False)
                                    self.rec_box_lift_step[3] = True
                                else:
                                    self.rec_box.run(r, self)
                            if not self.rec_box_lift_step[4] and self.rec_box_lift_step[3]:
                                self.rec_box_lift_step[4] = self.lift(r, self.lift_height)
                            if self.rec_box_lift_step[4]:
                                self.unload_step[7] = True
                        else:
                            self.unload_step[7] = True
                else:
                    if not self.unload_step[6]:
                        self.unload_step[6] = self.lift(r, self.lift_height)
                    if not self.unload_step[7]:
                        self.unload_step[7] = self.rotate(r, self.rotate_pos)
            elif self.unload_step[7] and not self.unload_step[8]:
                if self.rec_adjust is not None:
                    if not self.load_step[0]:
                        r.setDO(self.fill_light_do, True)
                        self.rec_adjust.status = MoveStatus.RUNNING
                        if ModuleTool.check_DO(r, self.fill_light_do):
                            if ModuleTool.delay(0.3):
                                self.load_step[0] = True
                    else:
                        if self.rec_adjust.status is MoveStatus.FINISHED:
                            r.setDO(self.fill_light_do, False)
                            self.unload_step[8] = True
                        elif self.rec_adjust.status is MoveStatus.FAILED:
                            self.status = MoveStatus.FAILED
                        else:
                            self.rec_adjust.run(r, self)
                else:
                    self.unload_step[8] = True
            elif self.unload_step[8] and not self.unload_step[9]:
                self.unload_step[9] = self.lift(r, self.lift_height + self.unload_height)
            elif self.unload_step[9] and not self.unload_step[10]:
                self.unload_step[10] = self.stretch(r, self.stretch_length)
            elif self.unload_step[10] and not self.unload_step[11]:
                if not self.change_step[2]:
                    self.change_step[2] = self.lift(r, self.lift_height + self.unload_height - self.lift_height_before_clamp)
                elif self.change_step[2] and not self.change_step[3]:
                    self.change_step[3] = self.clamp(r, 0)
                self.unload_step[11] = self.change_step[2] and self.change_step[3]
            elif self.unload_step[11] and not self.unload_step[12]:
                self.unload_step[12] = self.stretch(r, 0)
            elif self.unload_step[12] and not self.unload_step[13]:
                self.unload_step[13] = self.rotate(r, 0)
            
            unload_info['unload_step'] = self.unload_step
            unload_info['cur_container'] = self.cur_c
            unload_info['goodsId'] = self.goods_id
            self.report_info["unload_info"] = unload_info
        
        if all(self.unload_step[:14]):
            # 在所有的动作完成后，将自身背篓的获取清除
            r.clearContainer(self.cur_c)
            # r.clearContainerByGoodsId(self.goods_id)
            return True
    
    def change(self, r):
        pass
    
    def update_report_info(self, r):
        module_pos = dict()
        self.lift_real_pos = ModuleTool.get_motor_pos(r, self.lift_motor_name)
        self.stretch_real_pos = ModuleTool.get_motor_pos(r, self.stretch_motor_name)
        self.clamp_real_pos = ModuleTool.get_motor_pos(r, self.clamp_motor_name)
        self.rotate_real_pos = ModuleTool.get_motor_pos(r, self.rotate_motor_name)
        self.rotate_real_pos = self.rotate_real_pos * 180 / math.pi
        # self.update_finger_info(r)
        module_pos['lift'] = round(self.lift_real_pos, 3)
        module_pos['stretch'] = round(self.stretch_real_pos, 3)
        module_pos['rotate'] = round(self.rotate_real_pos, 3)
        module_pos['clamp'] = round(self.clamp_real_pos, 3)
        # module_pos['left_finger'] = self.left_finger_real_pos
        # module_pos['right_finger'] = self.right_finger_real_pos
        self.containers = r.getContainers()
        self.report_info["current_pos"] = module_pos
    
    def has_goods_id(self, r, goods_id: str):
        r.logInfo(f"goodsId: {goods_id}")
        for c in self.containers:
            if goods_id == c['goods_id']:
                return True
        return False
    
    def search_operable_container(self, r, opt):
        ct = None
        if opt == 'load':
            for c in self.containers:
                if not c['has_goods'] and (c['container_name'] == "999"):
                    ct = "999"
                if not c['has_goods'] and (c['container_name'] != "999"):
                    ct = c['container_name']
                    break
        elif opt == 'unload':
            for c in self.containers:
                if c['has_goods'] and self.goods_id == c['goods_id']:
                    ct = c['container_name']
        r.logDebug(f"search_operable_container: {ct}")
        return ct


class Rec:
    def __init__(self, filename, is_error=None, max_rec_times=10):
        self.status = MoveStatus.NONE
        self.is_error = is_error
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = max_rec_times
        self.result = dict()
        self.has_goods = None
        self.goods_out_dist = None
        self.max_goods_dist = 0.8  # 料箱距离货叉里程中心最远距离，单位：米
    
    def run(self, r: SimModule, agv):
        self.status = MoveStatus.RUNNING
        rec_status = r.getRecStatus()  # 获取识别状态 0: 初始化, 1: 识别中, 2: 获得结果, 3：识别出错, -1: 未知错误
        if rec_status == 3 or rec_status == -1:  # 识别失败的状态
            r.logInfo("rec failed:{}".format(self.result))
            if ModuleTool.delay(0.5):
                self.rec_times = self.rec_times + 1
                if self.rec_times > self.max_rec_times:
                    if not self.is_error:
                        r.setError("rec fail. reach max times {}".format(self.max_rec_times))
                        self.status = MoveStatus.FAILED
                    else:
                        self.status = MoveStatus.FINISHED
                else:
                    r.resetRec()
        
        elif rec_status == 2:  # 识别成功,获得结果
            self.result = r.getRecResult()
            if "resultImg" in self.result:
                self.result.pop("resultImg")
            r.resetRec()
            self.has_goods = True
            if self.result["x"] > self.max_goods_dist:
                self.goods_out_dist = True
            self.status = MoveStatus.FINISHED
            r.logInfo(f"rec success: {self.status.name} {self.result}")
        else:
            r.logInfo(f"--------------- doRec ----------------")
            r.doRecWithAngle(self.filename, 0.0)
        
        cur_state = dict()
        cur_state['rec_result'] = self.result
        cur_state['rec_count'] = self.rec_times
        cur_state['rec_task_status'] = self.status
        cur_state['rec_status'] = rec_status
        cur_state['file'] = self.filename
        agv.report_info['rec_info'] = cur_state
    
    def reset(self, r):
        r.resetRec()
        
        self.status = MoveStatus.RUNNING


class RecAdjust:
    def __init__(self, r, filename):
        p = ParamServer(__file__)
        self.rotate_step = None
        self.status = MoveStatus.NONE
        self.rec = Rec(filename)
        self.result = []
        self.max_rec_fail_times = 10
        self.max_adjust_time = 10
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.go_args = dict()
        self.ok = False
        # self.ok_x = 0.003  # x方向行走调整完成阈值
        self.ok_x = p.loadParam("ok_x", type="float", default=0.005, comment="x方向行走调整完成阈值")
        # self.ok_yaw = 0.035  # 调整完成弧度阈值, 对应2°
        self.ok_yaw = p.loadParam("ok_yaw", type="float", default=0.04, comment="调整完成弧度阈值")
        # self.max_yaw_bias = 0.13  # 最大偏差弧度
        self.max_yaw_bias = p.loadParam("max_yaw_bias", type="float", default=0.13, comment="货叉与料箱角度最大偏差, 弧度值")
        self.adjust_rotate = 1.5708  # 默认值
        self.plan_status = MoveStatus.NONE
        self.goPath = goPath.Module(r, dict())
    
    @staticmethod
    def move_x(dx, dy, yaw, rotate_pos, offset_x):
        """
        计算车体在x方向上移动的距离
        rotate_pos 是货叉旋转方向
        (dx, dy, yaw)是识别结果
        """
        if rotate_pos > 0:
            if yaw > 0:
                return -dy - dx * math.tan(math.pi - yaw) + offset_x
            elif yaw < 0:
                return -dy + dx * math.tan(math.pi + yaw) + offset_x
        else:
            if yaw > 0:
                return dy + dx * math.tan(math.pi - yaw) - offset_x
            elif yaw < 0:
                return dy - dx * math.tan(math.pi + yaw) - offset_x
    
    def run(self, r: SimModule, agv: Module):
        cur_state = dict()
        self.status = MoveStatus.RUNNING
        if self.plan_status is not MoveStatus.FINISHED:
            self.plan_status = MoveStatus.RUNNING
            if self.rec.status is MoveStatus.RUNNING or self.rec.status is MoveStatus.NONE:
                r.logInfo(f"----- rec to adjust {self.rec.status.name}------")
                self.rec.run(r, agv)
            elif self.rec.status is MoveStatus.FAILED:
                self.rec_fail_time = self.rec_fail_time + 1
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.rec.reset(r)
                    self.rec.run(r, agv)
                else:
                    self.status = MoveStatus.FAILED
                    r.setError("rec fails!!! reach max times. {}".format(self.max_rec_fail_times))
                r.logInfo("rec fail!!! {}".format(self.rec_fail_time))
            elif self.rec.status is MoveStatus.FINISHED:
                r.logInfo(f"------------------ move to adjust -----------------")
                self.rec_fail_time = 0
                # 通过参数配置，使识别结果为二维码在相机坐标系下的坐标位置, (右手坐标系)x轴向前，y轴向左, z轴向上
                
                """获取结果"""
                # 计算手臂伸出长度
                if not agv.stretch_length:
                    agv.stretch_length = abs(self.rec.result[
                                                 'x']) - agv.auto_stretch_odo_len + agv.auto_stretch_dist + agv.auto_stretch_box_len
                    if agv.stretch_length > agv.max_stretch_length:
                        r.setError(
                            f"The box is too far. need stretch: {agv.stretch_length}, max stretch: {agv.max_stretch_length}.")
                        self.status = MoveStatus.FAILED
                        return
                
                code2camera = [self.rec.result['x'], self.rec.result['y'], self.rec.result['z'],
                               self.rec.result['yaw']]
                cur_state["code2camera"] = code2camera
                
                self.go_args["coordinate"] = "robot"
                
                # 根据反馈的yaw来判断rotate调整方向
                if code2camera[3] > 0:
                    agv.yaw_adjust = code2camera[3] - math.pi  # 负角度调整
                    self.adjust_rotate = agv.rotate_pos - (math.pi - code2camera[3])
                else:
                    agv.yaw_adjust = code2camera[3] + math.pi  # 正角度调整
                    self.adjust_rotate = agv.rotate_pos + (math.pi + code2camera[3])
                
                self.go_args["x"] = self.move_x(self.rec.result['x'], self.rec.result['y'], self.rec.result['yaw'],
                                                agv.rotate_pos, agv.offset_x)
                self.go_args["y"] = 0
                self.go_args["theta"] = 0
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["reachDist"] = self.ok_x
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                else:
                    self.go_args["backMode"] = 0
                
                if abs(agv.yaw_adjust) > self.max_yaw_bias:
                    self.status = MoveStatus.FAILED
                    r.setError("recAdjust fails!!! reach max yaw_adjust.")
                else:
                    # 精度满足, 识别调整任务完成
                    if abs(self.go_args['x']) < self.ok_x and abs(agv.yaw_adjust) <= self.ok_yaw:
                        self.status = MoveStatus.FINISHED
                    else:
                        if self.adjust_count >= self.max_adjust_time:
                            self.status = MoveStatus.FAILED
                            r.setError("recAdjust fails!!! recAdjust max times.")
                self.plan_status = MoveStatus.FINISHED
                self.rec.reset(r)
        elif self.status is not MoveStatus.FINISHED and self.status is not MoveStatus.FAILED:
            if self.goPath.status != MoveStatus.FINISHED and self.goPath.status != MoveStatus.FAILED:
                if abs(self.go_args['x']) < self.ok_x:  # 底盘调整完成
                    self.goPath.status = MoveStatus.FINISHED
                else:
                    if self.adjust_count >= self.max_adjust_time:
                        self.status = MoveStatus.FAILED
                        r.setError("recAdjust fails!!! recAdjust max times.")
                    
                    if self.goPath.status != MoveStatus.FINISHED and self.goPath.status != MoveStatus.FAILED:
                        self.goPath.run(r, self.go_args)
            elif not self.rotate_step and self.goPath.status == MoveStatus.FINISHED:
                if abs(agv.yaw_adjust) <= self.ok_yaw:  # 货叉调整完成
                    self.rotate_step = True
                if not self.rotate_step:
                    if agv.operation == "load":
                        self.rotate_step = agv.rotate(r, self.adjust_rotate)  # 货叉角度偏移修正
                    elif agv.operation == "unload":
                        self.rotate_step = True
            elif self.goPath.status == MoveStatus.FAILED:
                self.status = MoveStatus.FAILED
            elif self.goPath.status == MoveStatus.FINISHED and self.rotate_step:
                self.reset(r)
                self.adjust_count += 1
                self.plan_status = MoveStatus.NONE
                self.rotate_step = False
                # self.status = MoveStatus.FINISHED
        cur_state["stretch_length"] = agv.stretch_length
        cur_state["go_path_status"] = self.goPath.status
        cur_state["plan_status"] = self.plan_status
        cur_state["go_args"] = self.go_args
        cur_state["rec_fail_time"] = self.rec_fail_time
        cur_state["adjust_count"] = self.adjust_count
        cur_state["status"] = self.status
        cur_state["agv yaw_adjust"] = agv.yaw_adjust
        agv.report_info["rec_adjust"] = cur_state
    
    def reset(self, r):
        self.rec.reset(r)
        self.status = MoveStatus.RUNNING
        self.rec_fail_time = 0
        self.goPath.reset()


if __name__ == '__main__':
    sim = SimModule()
    args1 = {}
    m = Module(sim, args1)
    counter = 0
    while m.status is not MoveStatus.FAILED and m.status is not MoveStatus.FINISHED:
        m.run(sim, args1)
        counter += 1
        if counter > 1:
            break
