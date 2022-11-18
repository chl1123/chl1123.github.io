# -*- coding: utf-8 -*-
# @Date : 2022/11/10
# @Author : zhong
# @File :containerRobot.py
# @Version : 1.1
# @Project : 自研料箱车
# @Update :
import json
import math
import sys
import time

sys.path.append("../syspy")
import goPath
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer, Pos2Base
from robot import ModuleTool, Motor, MotorType, Robot, ScriptLog, GoodsManger

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
        "default_value":["code", "barcode", "markerless"],
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
        "default_value":["load","unload","change","zero","take","put"],
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
        p = ParamServer(__file__)
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                                   comment=" 运行超时时间")
        self.low = dict()
        self.high = dict()
        self.low[0] = p.loadParam("low0", type="float", default=0.4, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第0层背篓取料箱高度")
        self.high[0] = p.loadParam("high0", type="float", default=0.45, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第0层背篓放料箱高度")
        self.low[1] = p.loadParam("low1", type="float", default=0.845, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第1层背篓取料箱高度")
        self.high[1] = p.loadParam("high1", type="float", default=0.855, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第1层背篓放料箱高度")
        self.low[2] = p.loadParam("low2", type="float", default=1.295, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第2层背篓取料箱高度")
        self.high[2] = p.loadParam("high2", type="float", default=1.305, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第2层背篓放料箱高度")
        self.low[3] = p.loadParam("low3", type="float", default=1.55, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第3层背篓取料箱高度")
        self.high[3] = p.loadParam("high3", type="float", default=1.6, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第3层背篓放料箱高度")
        self.low[4] = p.loadParam("low4", type="float", default=2.195, maxValue=10000.0, minValue=0.0, unit="m",
                                  comment="第4层背篓取料箱高度")
        self.high[4] = p.loadParam("high4", type="float", default=2.205, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第4层背篓放料箱高度")
        self.stretch_self_length = p.loadParam("stretch_self_length", type="float", default=0.72, maxValue=10000.0,
                                               minValue=0.0, unit="m", comment="取放自身背篓货物时伸出长度")
        self.rec_offz_box = p.loadParam("rec_offz_box", type="float", default=-0.08, maxValue=1000.0, minValue=-1000.0,
                                        unit="m", comment="识别料箱码后抓取料箱时调整高度")
        self.rec_offz_shelf = p.loadParam("rec_offz_shelf", type="float", default=0.05, maxValue=1000.0,
                                          minValue=-1000.0, unit="m", comment="识别货架码后放置料箱时调整高度")
        self.fork_up_limit = p.loadParam("fork_up_limit", type="int", default=4, maxValue=100, minValue=-1, unit="",
                                         comment="货叉上限位DI")
        self.fork_down_limit = p.loadParam("fork_down_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                           comment="货叉下限位DI")
        self.fork_limit = p.loadParam("fork_limit", type="int", default=1, maxValue=100, minValue=-1, unit="",
                                      comment="货叉机械限位限位DI")
        self.min_lift_height = p.loadParam("min_fork_height", type="float", default=0.4, maxValue=10000.0,
                                           minValue=0.0, unit="m", comment="货叉最低高度")
        self.max_lift_height = p.loadParam("max_fork_height", type="float", default=3.0, maxValue=10000.0,
                                           minValue=0.0, unit="m", comment="货叉最大高度")
        self.max_stretch_length = p.loadParam("max_stretch_length", type="float", default=0.72, maxValue=10000.0,
                                              minValue=0.0, unit="m", comment="货叉最大伸出长度")
        self.safe_stretch_length = p.loadParam("safe_stretch_length", type="float", default=0.05, maxValue=10000.0,
                                               minValue=0.0, unit="m", comment="货叉伸缩臂安全操作长度")
        self.safe_lift_height = p.loadParam("safe_lift_height", type="float", default=1.0, maxValue=10000.0,
                                            minValue=0.0, unit="m", comment="货叉安全高度")
        self.has_fork_sensor = p.loadParam("has_fork_sensor", type="int", default=0,
                                           comment="货叉是否有货物检测传感器，1为有，0为无")
        self.has_tray_sensor = p.loadParam("has_tray_sensor", type="int", default=0,
                                           comment="背篓是否有货物检测传感器，1为有，0为无")
        self.fork_sensor_di = p.loadParam("fork_sensor_di", type="int", default=-1, maxValue=100, minValue=-1, unit="",
                                          comment="货叉检测DI")
        self.box_code_file = p.loadParam("box_code_file", type="str", default="tag/t0002.tag",
                                         comment="料箱二维码识别文件")
        self.shelf_code_file = p.loadParam("shelf_code_file", type="str", default="tag/t0001.tag",
                                           comment="货架二维码识别文件")
        self.barcode_file = p.loadParam("barcode_file", type="str", default="tag/t0001.tag", comment="条形码识别文件")
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.goods_id = ""
        self.logger = ScriptLog("containerRobot", when='H', interval=1, backupCount=48).logger
        self.lift_height = None
        self.stretch_length = None
        self.rotate_pos = None
        self.finger_pos = None
        self.self_position = None
        self.lift_status = None
        self.left_finger_real_pos = None
        self.right_finger_real_pos = None
        self.finger_info = dict()
        self.stretch_status = None
        self.stretch_real_pos = 0
        self.lift_real_pos = 0
        self.rotate_real_pos = 0
        self.load_height = None
        self.unload_height = None
        self.left_finger_up_di = 2
        self.left_finger_down_di = 4
        self.left_finger_up_do = 2
        self.left_finger_down_do = 1
        self.right_finger_up_di = 7
        self.right_finger_down_di = 10
        self.right_finger_up_do = 3
        self.right_finger_down_do = 5
        self.fill_light_do = 7
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
        self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, "lift", -1)
        self.stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, "stretch", -1)
        self.rotate_motor = Motor(r, MotorType.LINEAR_MOTOR, "rotate", -1)
        self.load_step = [False] * 15
        self.unload_step = [False] * 16
        self.change_step = [False] * 10
        self.zero_step = [False] * 4

        r.logInfo(f"init args: {args}")
        self.logger.info(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.goods_id = args.get("goodsId", "")
            self.get_move_task_params(r)
            self.finger_pos = args.get("finger", 0)
            self.lift_height = args.get("lift", 0)
            self.stretch_length = args.get("stretch", 0)
            self.rotate_pos = args.get("rotate", 0)
            self.code_type = args.get("visionBinType", "code")
            self.target_type = args.get("visionType", None)
            self.barcode_height = args.get("barcodeHeight", None)
            if "recAdjust" in args:
                self.rec_adjust = RecAdjust(r, self.box_code_file)
            self.load_height = args.get("loadHeight", self.rec_offz_box)
            self.unload_height = args.get("unloadHeight", self.rec_offz_shelf)
            self.containers = r.getContainers()
            self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, "lift", -1)
            self.stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, "stretch", -1)
            self.rotate_motor = Motor(r, MotorType.LINEAR_MOTOR, "rotate", -1)
            self.goods_manger = GoodsManger(r)
            self.self_position = args.get("selfPosition", None)
            self.operation = args.get("operation", None)

        if time.time() - self.start_time > self.timeout:
            r.setError(f"running time out")
            self.status = MoveStatus.FAILED
        self.update_report_info(r)
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
            elif self.operation == "change":
                pass
            elif self.operation == "take":
                pass
            elif self.operation == "put":
                pass
            else:
                r.setError(f"args error: {args}")
                self.status = MoveStatus.FAILED
        else:
            if "finger" in args:
                if self.finger(r, self.finger_pos):
                    self.update_finger_info(r)
                    self.status = MoveStatus.FINISHED
            if "lift" in args:
                if self.lift(r, self.lift_height):
                    self.status = MoveStatus.FINISHED
            if "rotate" in args:
                if self.rotate(r, self.rotate_pos):
                    self.status = MoveStatus.FINISHED
            if "stretch" in args:
                if self.stretch(r, self.stretch_length):
                    self.status = MoveStatus.FINISHED
            if "visionType" in args:
                if self.code_type == "barcode":
                    if self.rec_barcode(r):
                        self.status = MoveStatus.FINISHED
                elif self.code_type == "code":
                    if self.vision(r, self.target_type, self.code_type):
                        self.status = MoveStatus.FINISHED
        r.publishSpeed()
        self.update_report_info(r)
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        self.report_info['finger'] = self.finger_info
        self.report_info['goodsId'] = self.goods_id
        self.report_info['containers'] = self.containers
        self.report_info['motor_info'] = self.container_robot.state or -1

        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        self.logger.info(f"report info: {json.dumps(self.report_info)}")
        return self.status

    def cancel(self, r: SimModule):
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

    def zero(self, r):
        """
        机构复位
        :param r:
        :return:
        """
        r.setNotice(f"----- running zero ------")
        if not self.zero_step[0]:
            self.zero_step[0] = self.stretch(r, 0)
        elif self.zero_step[0] and not all(self.zero_step[1:]):
            self.zero_step[1] = self.finger(r, 0)
            self.zero_step[2] = self.rotate(r, 0)
            self.zero_step[3] = self.lift(r, 0)
        if all(self.zero_step):
            return True
        return False

    def lift(self, r, height):
        r.setNotice(f"----- running lift ------")
        if height < self.min_lift_height:
            r.setWarning(f"lower than the min lift height: {height}")
            height = self.min_lift_height
        if height > self.max_lift_height:
            r.setWarning(f"Out of the max lift height: {height}")
            height = self.max_lift_height
        if self.stretch_real_pos > self.safe_stretch_length:
            r.setError(f"stretch need to be zero, cannot lift")
        if self.container_robot.lift(self.lift_motor, height):
            return True
        return False

    def finger(self, r, pos):
        r.setNotice(f"----- running finger ------")
        if pos == 1:
            r.setDO(self.left_finger_up_do, True)
            r.setDO(self.left_finger_down_do, False)
            r.setDO(self.right_finger_up_do, True)
            r.setDO(self.right_finger_down_do, False)
            if ModuleTool.check_DI(r, self.left_finger_up_di) and ModuleTool.check_DI(r, self.right_finger_up_di):
                self.left_finger_real_pos, self.right_finger_real_pos = 1, 1
                return True
        elif pos == 0:
            r.setDO(self.left_finger_down_do, True)
            r.setDO(self.left_finger_up_do, False)
            r.setDO(self.right_finger_down_do, True)
            r.setDO(self.right_finger_up_do, False)
            if ModuleTool.check_DI(r, self.left_finger_down_di) and ModuleTool.check_DI(r, self.right_finger_down_di):
                self.left_finger_real_pos, self.right_finger_real_pos = 0, 0
                return True
        return False

    def update_finger_info(self, r):
        if ModuleTool.check_DI(r, self.left_finger_down_di):
            self.left_finger_real_pos = 0
        elif ModuleTool.check_DI(r, self.left_finger_up_di):
            self.left_finger_real_pos = 1
        if ModuleTool.check_DI(r, self.right_finger_down_di):
            self.right_finger_real_pos = 0
        elif ModuleTool.check_DI(r, self.right_finger_up_di):
            self.right_finger_real_pos = 1

    def stretch(self, r, length):
        r.setNotice(f"----- running stretch ------")
        if length > self.max_stretch_length:
            r.setWarning(f"Out of max stretch length: {length}")
            length = self.max_stretch_length
        if self.container_robot.stretch(self.stretch_motor, length):
            return True
        return False

    def rotate(self, r, pos):
        r.setNotice(f"----- running rotate ------")
        if pos < (-100 / 180 * math.pi) or pos > (100 / 180 * math.pi):
            r.setError(f"Out of max rotate angle: {pos}")
        if self.stretch_real_pos > self.safe_stretch_length:
            r.setError(f"stretch need to be zero, cannot rotate")
        if self.container_robot.rotate(self.rotate_motor, pos):
            return True
        return False

    def rec_barcode(self, r):
        r.setNotice(f"----- running rec_barcode ------")
        r.setDO(self.fill_light_do, True)
        rec_count = 0
        rec_res = r.RecognizeBarCode(self.barcode_file)
        if rec_res:
            r.setDO(self.fill_light_do, False)
            r.logInfo(f"barcode: {rec_res}")
            self.report_info["barcode"] = rec_res
            return rec_res
        else:
            rec_count += 1
            if rec_count > 10:
                return False

    def vision(self, r, target_type, code_type):  # 识别料箱、货架二维码
        r.setNotice(f"----- running vision ------")
        r.setDO(self.fill_light_do, True)
        if target_type == "box" and code_type == "code":
            self.rec = Rec(self.box_code_file)
        elif target_type == "box" and code_type == "barcode":
            # self.rec = Rec(self.barcode_file)
            pass
        elif target_type == "shelf" and code_type == "code":
            self.rec = Rec(self.shelf_code_file)

        if self.rec.status is MoveStatus.FINISHED:
            self.rec.reset(r)
            r.setDO(self.fill_light_do, False)
            r.logInfo(f"rec result: {self.rec.result}")
            self.logger.info(f"rec result: {self.rec.result}")
            return True
        elif self.rec.status is MoveStatus.FAILED:
            r.setDO(self.fill_light_do, False)
            return False
        else:
            self.rec.run(r, self)
        return False

    def load(self, r):
        r.setNotice(f"----- running load  {self.goods_id}------")
        load_info = dict()
        cur_c = self.search_operable_container(r, 'load')
        if self.goods_id and self.goods_manger.goods_id_exist(self.goods_id):
            r.setPickRobotError(53819, f"This good already exists: {self.goods_id}")
            self.status = MoveStatus.FAILED
        if self.self_position:
            cur_c = self.self_position
            if self.goods_manger.has_goods(cur_c):
                r.setPickRobotError(53820, f"Container {cur_c} has goods, can not load")
                self.status = MoveStatus.FAILED
        r.logInfo(f"load begin: {json.dumps(self.containers)}")
        if cur_c is None:  # 抓斗取货
            for c in self.containers:
                if c['container_name'] == "999" and not c['has_goods']:
                    cur_c = "999"
            if cur_c != "999":
                r.setPickRobotError(53821, f"All containers are full, can not load")
                self.status = MoveStatus.FAILED

        if not self.load_step[0]:
            self.load_step[0] = self.finger(r, 1) and self.lift(r, self.lift_height)
        elif self.load_step[0] and not self.load_step[1]:
            self.load_step[1] = self.rotate(r, self.rotate_pos)
        elif self.load_step[1] and not self.load_step[2]:
            if self.barcode_height is not None:
                self.lift(r, self.barcode_height)
                self.load_step[2] = self.goods_id == self.rec_barcode(r)
            else:
                self.load_step[2] = True
        elif self.load_step[2] and not self.load_step[3]:
            if self.rec_adjust is not None:
                if self.lift(r, self.lift_height):
                    r.setDO(self.fill_light_do, True)
                    if self.rec_adjust.status is MoveStatus.FINISHED:
                        r.setDO(self.fill_light_do, False)
                        self.load_step[3] = True
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
            self.load_step[6] = self.finger(r, 0)
        elif self.load_step[6] and not self.load_step[7]:
            self.load_step[7] = self.stretch(r, 0)
        elif self.load_step[7] and not self.load_step[8]:
            self.load_step[8] = self.rotate(r, 0)
        elif self.load_step[8] and not self.load_step[9]:
            if cur_c == "999":
                # self.load_step = [True] * 14 + [False]
                self.load_step[:14] = [True] * 14
            else:
                self.load_step[9] = self.lift(r, self.high[int(cur_c)])
        elif self.load_step[9] and not self.load_step[10]:
            self.load_step[10] = self.stretch(r, self.stretch_self_length)
        elif self.load_step[10] and not self.load_step[11]:
            self.load_step[11] = self.finger(r, 1)
        elif self.load_step[11] and not self.load_step[12]:
            self.load_step[12] = self.stretch(r, 0)
        elif self.load_step[12] and not self.load_step[13]:
            self.load_step[13] = self.finger(r, 0)
        elif self.load_step[13] and not self.load_step[14]:
            if self.lift_real_pos > self.safe_lift_height:
                self.load_step[14] = self.lift(r, 0)
            else:
                self.load_step[14] = True

        load_info['load_step'] = self.load_step
        load_info['cur_container'] = cur_c
        load_info['goodsId'] = self.goods_id
        load_info['load_step'] = self.load_step
        self.report_info["load_info"] = load_info
        if all(self.load_step):
            r.setContainer(cur_c, self.goods_id, "")
            return True

    def unload(self, r):
        r.setNotice(f"----- running unload ------")
        unload_info = dict()
        cur_c = self.goods_manger.get_container_by_goodsId(self.goods_id)
        if self.self_position:
            cur_c = self.self_position
            if not self.goods_manger.has_goods(cur_c):
                r.setPickRobotError(53824, f"Container {cur_c} is empty, can not unload!")
                self.status = MoveStatus.FAILED
        if self.goods_manger.has_goods("999"):  # 抓斗有货
            cur_c = "999"
        if not cur_c:
            r.setPickRobotError(53825, f"Goods {self.goods_id} not found, can not unload!")
            self.status = MoveStatus.FAILED
        r.logInfo(f"unload begin: {json.dumps(self.containers)}")
        if cur_c == "999":
            self.unload_step[:6] = [True] * 6
        else:
            if not self.unload_step[0]:
                self.unload_step[0] = self.lift(r, self.low[cur_c])
            elif self.unload_step[0] and not self.unload_step[1]:
                self.unload_step[1] = self.finger(r, 1)
            elif self.unload_step[1] and not self.unload_step[2]:
                self.unload_step[2] = self.rotate(r, 0)
            elif self.unload_step[2] and not self.unload_step[3]:
                self.unload_step[3] = self.stretch(r, self.stretch_self_length)
            elif self.unload_step[3] and not self.unload_step[4]:
                self.unload_step[4] = self.finger(r, 0)
            elif self.unload_step[4] and not self.unload_step[5]:
                self.unload_step[5] = self.stretch(r, 0)

        if all(self.unload_step[:6]) and not self.unload_step[6]:
            self.unload_step[6] = self.lift(r, self.lift_height)
        elif self.unload_step[6] and not self.unload_step[7]:
            self.unload_step[7] = self.rotate(r, self.rotate_pos)
        elif self.unload_step[7] and not self.unload_step[8]:
            if self.rec_adjust:
                r.setDO(self.fill_light_do, True)
                if self.rec_adjust.status is MoveStatus.FINISHED:
                    r.setDO(self.fill_light_do, False)
                    self.unload_step[8] = True
                else:
                    self.rec_adjust.run(r, self)
            else:
                self.unload_step[8] = True
        elif self.unload_step[8] and not self.unload_step[9]:
            self.unload_step[9] = self.lift(r, self.lift_height + self.unload_height)
        elif self.unload_step[9] and not self.unload_step[10]:
            self.unload_step[10] = self.finger(r, 1)
        elif self.unload_step[10] and not self.unload_step[11]:
            self.unload_step[11] = self.stretch(r, self.stretch_self_length)
        elif self.unload_step[11] and not self.unload_step[12]:
            self.unload_step[12] = self.stretch(r, 0)
        elif self.unload_step[12] and not self.unload_step[13]:
            self.unload_step[13] = self.finger(r, 0)
        elif self.unload_step[13] and not self.unload_step[14]:
            self.unload_step[14] = self.rotate(r, 0)
        elif self.unload_step[14] and not self.unload_step[15]:
            if self.lift_real_pos > self.safe_lift_height:
                self.unload_step[15] = self.lift(r, 0)
            else:
                self.unload_step[15] = True

        unload_info['unload_step'] = self.unload_step
        unload_info['cur_container'] = cur_c
        unload_info['goodsId'] = self.goods_id
        unload_info['unload_info'] = self.unload_step
        self.report_info["unload_info"] = unload_info

        if all(self.unload_step):
            r.clearContainer(cur_c)
            # r.clearContainerByGoodsId(self.goods_id)
            return True

    def change(self, r):
        pass

    def update_report_info(self, r):
        module_pos = dict()
        self.lift_real_pos = ModuleTool.get_motor_pos(r, "lift")
        self.stretch_real_pos = ModuleTool.get_motor_pos(r, "stretch")
        self.rotate_real_pos = ModuleTool.get_motor_pos(r, "rotate")
        self.update_finger_info(r)
        module_pos['lift'] = round(self.lift_real_pos, 6)
        module_pos['stretch'] = round(self.stretch_real_pos, 6)
        module_pos['rotate'] = round(self.rotate_real_pos, 6)
        module_pos['left_finger'] = self.left_finger_real_pos
        module_pos['right_finger'] = self.right_finger_real_pos
        self.containers = r.getContainers()
        self.report_info["current_pos"] = module_pos

    def has_goods_id(self, r, goods_id: str):
        r.logInfo(f"goodsId: {goods_id}")
        for c in self.containers:
            if goods_id == c['goods_id']:
                return True
        return False

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


class Rec:
    def __init__(self, filename):
        self.status = MoveStatus.NONE
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = 10
        self.result = dict()

    def run(self, r: SimModule, agv):
        self.status = MoveStatus.RUNNING
        rec_status = r.getRecStatus()  # 获取识别状态
        r.logDebug("rec_status: {}".format(rec_status))
        if rec_status == 3:  # 识别失败的状态
            self.rec_times = self.rec_times + 1
            if self.rec_times > self.max_rec_times:
                r.setError("rec fail. reach max times {}".format(self.max_rec_times))
                self.status = MoveStatus.FAILED
            else:
                r.doRec(self.filename)
        elif rec_status == 0 or rec_status == 1:  # 
            r.doRec(self.filename)
        elif rec_status == 2:  # 识别成功
            self.result = r.getRecResult()
            r.logDebug("rec_result:{}".format(self.result))
            self.status = MoveStatus.FINISHED
        cur_state = dict()

        cur_state['rec_result'] = self.result
        cur_state['rec_count'] = self.rec_times
        cur_state['rec_state'] = self.status
        cur_state['rec_status'] = rec_status
        cur_state['file'] = self.filename
        agv.report_info['rec_info'] = cur_state
        r.logDebug(json.dumps(agv.report_info))

    def reset(self, r):
        r.resetRec()
        self.status = MoveStatus.RUNNING


class RecAdjust:
    def __init__(self, r, filename):
        self.status = MoveStatus.NONE
        self.rec = Rec(filename)
        self.result = []
        self.max_rec_fail_times = 10
        self.max_adjust_time = 10
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.go_args = dict()
        self.ok = False
        self.plan_status = MoveStatus.NONE
        self.goPath = goPath.Module(r, dict())

    def run(self, r: SimModule, agv):
        self.status = MoveStatus.RUNNING
        if self.plan_status is not MoveStatus.FINISHED:
            self.plan_status = MoveStatus.RUNNING
            if self.rec.status is MoveStatus.RUNNING or self.rec.status is MoveStatus.NONE:
                self.rec.run(r, agv)
            elif self.rec.status is MoveStatus.FAILED:
                self.rec_fail_time = self.rec_fail_time + 1
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.rec.reset(r)
                    self.rec.run(r, agv)
                else:
                    self.status = MoveStatus.FAILED
                    r.setError("rec fails!!! reach max times. {}".format(self.max_rec_fail_times))
                r.setNotice("rec fail!!! {}".format(self.rec_fail_time))
            elif self.rec.status is MoveStatus.FINISHED:
                self.rec_fail_time = 0
                code2world = [self.rec.result['x'], self.rec.result['y'], self.rec.result['yaw']]  # 目标点在世界坐标系的位置
                loc = r.loc()
                robot2world = [loc['x'], loc['y'], loc['angle']]  # 小车在世界坐标系的位置
                code2robot = Pos2Base(code2world, robot2world)  # 目标点相对小车的位置
                self.go_args["coordinate"] = "robot"
                self.go_args["x"] = code2robot[0]
                self.go_args["y"] = 0
                self.go_args["theta"] = 0
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["reachDist"] = 0.002
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                ok_x = 0.005
                if abs(self.go_args['x']) < ok_x:
                    self.status = MoveStatus.FINISHED
                else:
                    if self.adjust_count >= self.max_adjust_time:
                        self.status = MoveStatus.FAILED
                        r.setError("recAdjust fails!!! reach max times.")
                self.plan_status = MoveStatus.FINISHED
                self.rec.reset(r)
        elif self.status is not MoveStatus.FINISHED and self.status is not MoveStatus.FAILED:
            if self.goPath.status != MoveStatus.FINISHED and self.goPath.status != MoveStatus.FAILED:
                if abs(self.go_args["x"]) < 0.003:
                    self.goPath.status = MoveStatus.FINISHED
                else:
                    self.goPath.run(r, self.go_args)
            elif self.goPath.status == MoveStatus.FAILED:
                self.status = MoveStatus.FAILED
            elif self.goPath.status == MoveStatus.FINISHED:
                self.adjust_count = self.adjust_count + 1
                self.goPath.reset()
                self.status = MoveStatus.RUNNING
                self.go_args = dict()
                self.plan_status = MoveStatus.NONE
        cur_state = dict()
        cur_state["goaPathStatus"] = self.goPath.status
        cur_state["planStatus"] = self.plan_status
        cur_state["go_args"] = self.go_args
        cur_state["rec_fail_time"] = self.rec_fail_time
        cur_state["adjust_time"] = self.adjust_count
        cur_state["status"] = self.status
        agv.report_info["recAdjust_org"] = cur_state

    def reset(self, r):
        self.rec.reset(r)
        self.status = MoveStatus.RUNNING
        self.rec_fail_time = 0
        self.adjust_count = 0
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
