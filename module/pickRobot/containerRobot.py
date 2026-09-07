# -*- coding: utf-8 -*-
# @Date: 2026/9/7
# @Author: zhong,zhaopengfei
# @Version: 5.0
# @Project: 智千料箱车
# @Update: fix: 修复goods_check_di 传-1 临时屏蔽不生效
# @RBK Version: V3.4.8
SCRIPT_VERSION = "V348-20251116"
import json
import math
import random
import sys
import time
import os



sys.path.append(os.path.dirname(__file__) + "/syspy")
sys.path.append("../syspy")
from syspy import goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.robot import ModuleTool, Motor, MotorType, Robot, GoodsManger

"""
####BEGIN DEFAULT ARGS####
{
    "lift": {
        "value": 0,
        "tips": "货叉识别时的高度",
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
        "tips": "伸缩机构长度",
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
        "default_value":["load","unload","rec_box_barcode", "take_photo", "rec_qrcode", "zero", "zero_with_lift", "calib", "in_take","in_put", "ex_take","ex_put"],
        "tips": "机构动作选项",
        "type": "complex"
    },
    "container":{
        "value": "",
        "tips": "机器人自身库位编号",
        "type": "string"
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
    },
    "pre_finger":{
        "value": 1,
        "type": "int"
    },
    "skip_safe_height":{
        "value": 1,
        "type": "int"
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
        self.zeroing = None
        self.cur_c = None
        self.script_version = SCRIPT_VERSION
        p = ParamServer(__file__)
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                                   group="script", comment="运行超时时间")
        self.low = dict()
        self.high = dict()
        self.low[0] = p.loadParam("low0", type="float", default=0.4, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第0号背篓取料箱高度, 最低层, 从0号计数")
        self.high[0] = p.loadParam("high0", type="float", default=0.41, maxValue=10000.0, minValue=0.0, unit="m",
                                   group="trays", comment="第0号背篓放料箱高度, 最低层, 从0号计数")
        self.low[1] = p.loadParam("low1", type="float", default=0.82, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第1号背篓取料箱高度")
        self.high[1] = p.loadParam("high1", type="float", default=0.83, maxValue=10000.0, minValue=0.0, unit="m",
                                   group="trays", comment="第1号背篓放料箱高度")
        self.low[2] = p.loadParam("low2", type="float", default=1.25, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第2号背篓取料箱高度")
        self.high[2] = p.loadParam("high2", type="float", default=1.26, maxValue=10000.0, minValue=0.0, unit="m",
                                   group="trays", comment="第2号背篓放料箱高度")
        self.low[3] = p.loadParam("low3", type="float", default=1.675, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第3号背篓取料箱高度")
        self.high[3] = p.loadParam("high3", type="float", default=1.68, maxValue=10000.0, minValue=0.0, unit="m",
                                   comment="第3号背篓放料箱高度")
        self.low[4] = p.loadParam("low4", type="float", default=2.095, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第4号背篓取料箱高度")
        self.high[4] = p.loadParam("high4", type="float", default=2.10, maxValue=10000.0, minValue=0.0, unit="m",
                                   group="trays", comment="第4号背篓放料箱高度")
        self.low[5] = p.loadParam("low5", type="float", default=2.515, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第5号背篓取料箱高度")
        self.high[5] = p.loadParam("high5", type="float", default=2.525, maxValue=10000.0, minValue=0.0, unit="m",
                                   group="trays", comment="第5号背篓放料箱高度")
        self.low[6] = p.loadParam("low6", type="float", default=2.945, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第6号背篓取料箱高度")
        self.high[6] = p.loadParam("high6", type="float", default=2.955, maxValue=10000.0, minValue=0.0, unit="m",
                                   group="trays", comment="第6号背篓放料箱高度")
        self.low[7] = p.loadParam("low7", type="float", default=3.375, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第7号背篓取料箱高度")
        self.high[7] = p.loadParam("high7", type="float", default=3.385, maxValue=10000.0, minValue=0.0, unit="m",
                                   group="trays", comment="第7号背篓放料箱高度")
        self.low[8] = p.loadParam("low8", type="float", default=3.825, maxValue=10000.0, minValue=0.0, unit="m",
                                  group="trays", comment="第8号背篓取料箱高度")
        self.high[8] = p.loadParam("high8", type="float", default=3.835, maxValue=10000.0, minValue=0.0, unit="m",
                                   group="trays", comment="第8号背篓放料箱高度")
        self.stretch_self_length = p.loadParam("stretch_self_length", type="float", default=0.73, maxValue=10000.0,
                                               group="stretch", minValue=0.0, unit="m",
                                               comment="取放自身背篓货物时伸出长度")
        self.rec_offz_box = p.loadParam("rec_offz_box", type="float", default=-0.08, maxValue=1000.0, minValue=-1000.0,
                                        group="recognize", unit="m", comment="识别料箱码后抓取料箱时调整高度")
        self.rec_offz_shelf = p.loadParam("rec_offz_shelf", type="float", default=0.02, maxValue=1000.0,
                                          minValue=-1000.0, group="recognize", unit="m",
                                          comment="识别货架码后放置料箱时调整高度")
        self.fork_up_limit = p.loadParam("fork_up_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                         group="lift", comment="货叉上限位DI")
        self.fork_down_limit = p.loadParam("fork_down_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                           group="lift", comment="货叉下限位DI")
        self.fork_limit = p.loadParam("fork_limit", type="int", default=3, maxValue=100, minValue=-1, unit="",
                                      group="lift", comment="货叉升降机械限位限位DI")
        self.min_lift_height = p.loadParam("min_fork_height", type="float", default=0.38, maxValue=10000.0,
                                           minValue=0.0, unit="m", comment="货叉最低高度")
        self.max_lift_height = p.loadParam("max_fork_height", type="float", default=4.5, maxValue=10000.0,
                                           group="lift", minValue=0.0, unit="m", comment="货叉最大高度")
        self.max_rotate_angle = p.loadParam("max_rotate_angle", type="float", default=100,
                                            group="rotate", comment="货叉最大旋转角度值")
        self.max_stretch_length = p.loadParam("max_stretch_length", type="float", default=0.90, unit="m",
                                              group="stretch", comment="货叉最大伸出长度")
        self.safe_stretch_length = p.loadParam("safe_stretch_length", type="float", default=0.05, maxValue=10000.0,
                                               group="stretch", minValue=0.0, unit="m",
                                               comment="货叉升降、旋转操作时伸缩臂安全长度")
        self.safe_lift_height = p.loadParam("safe_lift_height", type="float", default=1.0, maxValue=10000.0,
                                            group="lift", minValue=0.0, unit="m",
                                            comment="货叉安全高度, 货叉导航过程中的最高高度")
        self.door_lift_height = p.loadParam("door_lift_height", type="float", default=1.7, maxValue=10000.0,
                                            group="lift", minValue=0.0, unit="m", comment="门架固定升降高度")
        self.has_fork_sensor = p.loadParam("has_fork_sensor", type="int", default=0,
                                           group="DI", comment="货叉是否有货物检测传感器，1为有，0为无")
        self.has_tray_sensor = p.loadParam("has_tray_sensor", type="int", default=0,
                                           group="DI", comment="背篓是否有货物检测传感器，1为有，0为无")
        self.fork_sensor_di = p.loadParam("fork_sensor_di", type="int", default=9, maxValue=100, minValue=-1, unit="",
                                          group="DI", comment="货叉检测DI")
        self.overlimit_detect_di = p.loadParam("overlimit_detect_di", type="int", default=-1,
                                               group="DI", comment="检测货叉伸出是否超过料箱的DI")
        self.box_code_file = p.loadParam("box_code_file", type="str", default="code/c0001.code",
                                         group="recognize", comment="料箱二维码识别文件")
        self.shelf_code_file = p.loadParam("shelf_code_file", type="str", default="code/c0002.code",
                                           group="recognize", comment="货架二维码识别文件")
        self.barcode_file = p.loadParam("barcode_file", type="str", default="tag/t0003.tag",
                                        group="recognize", comment="条形码识别文件")
        self.lift_motor_speed = p.loadParam("lift_motor_speed", type="float", default=1.5,
                                            group="lift", comment="升降电机运转速度")
        self.stretch_motor_speed = p.loadParam("stretch_motor_speed", type="float", default=1.0,
                                               group="stretch", comment="伸缩电机运转速度")
        self.rotate_motor_speed = p.loadParam("rotate_motor_speed", type="float", default=1.0,
                                              group="rotate", comment="旋转电机运转速度")
        self.lift_motor_name = p.loadParam("lift_motor_name", type="str", default="lift",
                                           group="lift", comment="升降电机名称")
        self.stretch_motor_name = p.loadParam("stretch_motor_name", type="str", default="stretch",
                                              group="stretch", comment="伸缩电机名称")
        self.rotate_motor_name = p.loadParam("rotate_motor_name", type="str", default="rotate",
                                             group="rotate", comment="旋转电机名称")
        # 以下是自动计算取放货伸手的长度
        self.auto_stretch_box_len = p.loadParam("auto_stretch_box_len", type="float", default=0.6, maxValue=100,
                                                group="stretch", minValue=-1, unit="", comment="箱子长度")
        self.auto_load_stretch_dist = p.loadParam("auto_load_stretch_dist", type="float", default=0.01,
                                                  group="stretch", unit="m", comment="自动计算取货伸出长度时的补偿值")
        self.auto_unload_stretch_dist = p.loadParam("auto_unload_stretch_dist", type="float", default=0.01,
                                                    group="stretch", unit="m", comment="自动计算放货伸出长度时的补偿值")
        self.auto_stretch_odo_len = p.loadParam("auto_stretch_odo_len", type="float", default=0.38, maxValue=100,
                                                group="stretch", minValue=20, unit="",
                                                comment="手指机构到货叉旋转中心的距离")
        self.auto_adjust_rotate = p.loadParam("auto_adjust_rotate", type="int", default=1,
                                              group="rotate", comment="识别时是否需要自动调整货叉角度，1：需要 0：不需要")
        self.offset_x = p.loadParam("offset_x", type="float", default=0.,
                                    group="recognize", comment="针对识别结果误差在x方向的补偿值")
        self.light_delay_time = p.loadParam("light_delay_time", type="float", default=0.3,
                                            group="recognize", comment="补光灯延时拍照时间")
        self.motor_settle_delay = p.loadParam("motor_settle_delay", type="float", default=0.5,
                                              group="recognize",
                                              comment="识别前等待机构机械停稳的延时(秒), 防止抖动污染识别")
        self.load_rec_lift_diff = p.loadParam("load_rec_lift_diff", type="float", default=0.05,
                                              group="recognize", comment="取货识别料箱高度与货架上表面的高度差")
        self.rec_box_extra_height = p.loadParam("rec_box_extra_height", type="float", default=0.0,
                                                comment="放货识别货架上是否有货物时，在放货高度上需要额外抬升的高度，该值可设置为货架码到料箱码的高度差")
        self.check_goods_code_enable = p.loadParam("check_goods_code_enable", type="int", default=0,
                                                   group="recognize",
                                                   comment="是否校验识别编码与任务货物编码一致，1：校验 0：不校验")
        self.max_code_check_fail = p.loadParam("max_code_check_fail", type="int", default=3, group="recognize",
                                               comment="识别编码与任务货物编码比较失败的最大次数，超过则报错")
        # 手指控制DO
        self.left_finger_up_do = p.loadParam("left_finger_up_do", type="int", default=8, group="finger",
                                             comment="左手指打开DO")
        self.left_finger_down_do = p.loadParam("left_finger_down_do", type="int", default=9, group="finger",
                                               comment="左手指关闭DO")
        self.right_finger_up_do = p.loadParam("right_finger_up_do", type="int", default=7, group="finger",
                                              comment="右手指打开DO")
        self.right_finger_down_do = p.loadParam("right_finger_down_do", type="int", default=6, group="finger",
                                                comment="右手指关闭DO")
        # 手指到位DI
        self.left_finger_up_di = p.loadParam("left_finger_up_di", type="int", default=1, group="finger",
                                             comment="左手指打开到位DI")
        self.left_finger_down_di = p.loadParam("left_finger_down_di", type="int", default=4, group="finger",
                                               comment="左手指关闭到位DI")
        self.right_finger_up_di = p.loadParam("right_finger_up_di", type="int", default=6, group="finger",
                                              comment="右手指打开到位DI")
        self.right_finger_down_di = p.loadParam("right_finger_down_di", type="int", default=5, group="finger",
                                                comment="右手指关闭到位DI")
        self.goods_check_di = p.loadParam("goods_check_di", type="int", default=8, group="goods",
                                          comment="货叉中部货物检测光电DI")
        self.ok_x = p.loadParam("ok_x", type="float", default=0.01, comment="x方向行走调整完成阈值")
        self.ok_yaw = p.loadParam("ok_yaw", type="float", default=0.015, comment="调整完成弧度阈值")
        self.max_yaw_bias = p.loadParam("max_yaw_bias", type="float", default=0.13,
                                        comment="货叉与料箱角度最大偏差, 弧度值")
        self.args_init = False
        self.script_args = args
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.goods_id = ""
        self.lift_height = None
        self.door_height = None
        self.stretch_length = None
        self.is_auto_stretch = None
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
        self.load_height = 0
        self.unload_height = 0
        self.rec_height_diff = 0
        self.fill_light_do = p.loadParam("fill_light_do", type="int", default=4, maxValue=100, minValue=-1, unit="",
                                          group="light", comment="补光灯DO")
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
        self.load_step = [False] * 16
        self.unload_step = [False] * 16
        self.change_step = [False] * 10
        # 识别前等待机构停稳: 进入识别触发点时记录起点, ≥motor_settle_delay 且 stop 标志为真才放行
        self.motor_settle_start = None
        self.overlimit_alarm = False  # 超限光电报错标志，用于障碍物消除后自动清错
        # 带料箱识别及异常恢复状态
        self.unload_rec_box_lifted = False   # unload 是否已升到 recBoxLift 高度
        self.unload_rec_box_checked = False  # unload 带箱识别是否完成
        self.unload_rec_box_light = False    # unload 带箱识别补光灯是否已开
        self.unload_rec_adjust_done = False  # unload 放货前识别料架是否完成
        self.unload_shelf_occupied = False   # unload 货架是否检测到已有货物
        self.unload_recovery_step = [False] * 8  # unload 异常恢复步骤
        self.unload_recovery_c = None        # unload 异常恢复目标背篓
        self.ex_put_rec_box_lifted = False   # ex_put 是否已升到 recBoxLift 高度
        self.ex_put_rec_box_checked = False  # ex_put 带箱识别是否完成
        self.ex_put_rec_box_light = False    # ex_put 带箱识别补光灯是否已开
        self.ex_put_rec_adjust_done = False  # ex_put 放货前识别料架是否完成
        self.ex_put_shelf_occupied = False   # ex_put 货架是否检测到已有货物
        self.ex_put_recovery_c = None        # ex_put 异常恢复目标背篓
        self.zero_step = [False] * 4
        self.calib_step = [False] * 3
        self.opt_step = [False] * 10
        self.yaw_adjust = 0
        self.rec_res = None
        self.rec_id = None
        self.barcode_rec_times = 0       # 一维码连续识别失败计数
        self.max_barcode_rec_times = 10  # 一维码连续识别失败上限, 超过则报错
        self.rec_box_lift = None
        self.finger_open_start = False
        self.pre_finger = None

        self.in_take_step = [False] * 20
        self.ex_take_step = [False] * 20
        self.in_put_step = [False] * 20
        self.ex_put_step = [False] * 20

        self.lift_motor_calib = None
        self.stretch_motor_calib = None
        self.rotate_motor_calib = None

        self.set_lift_motor_calib = False
        self.set_stretch_motor_calib = False
        self.set_rotate_motor_calib = False
        self.motor_calib_state = False
        self.motor_calib_info = {}
        self.enable_motor = False
        self.send_enable_motor_count = 0
        self.enable_motor_time = time.time()
        self.set_force_calib = False

        self.lift_ok = False
        self.rotate_ok = False
        self.stretch_ok = False

        # 记录当前正在执行的目标位置
        self.lift_executing = None
        self.stretch_executing = None
        self.rotate_executing = None

        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.script_args = args
        self.status = MoveStatus.RUNNING
        self.update_report_info(r)
        self.report_info["getCount_run"] = r.getCount()
        self.check_motor_emc(r)  # 检测控制器及驱动器急停状态
        if self.enable_motor and not self.motor_calib_state:  # 使能成功, 且未标零, 则标零
            self.motor_calib(r)
        if not self.args_init:
            self.args_init = True
            self.init_script_args(r)

        if time.time() - self.start_time > self.timeout:
            r.setError(f"脚本任务运行超时，请重新执行任务！")
            self.status = MoveStatus.FAILED

        if self.motor_calib_state:
            if self.operation is not None:
                if self.operation == "zero":
                    if self.zero(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "calib":
                    self.force_calib(r)
                elif self.operation == "zero_with_lift":
                    self.lift_height = min(self.lift_real_pos, self.lift_height)
                    if self.zero(r, self.lift_height):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "load":
                    if self.load(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "unload":
                    if self.unload(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "rec_box_barcode":
                    self.rec_box_barcode(r)
                elif self.operation == "rec_qrcode":
                    self.rec_qrcode(r)
                elif self.operation == "take_photo":
                    self.take_photo(r)
                elif self.operation == "in_take":
                    if self.in_take(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "in_put":
                    if self.in_put(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "ex_take":
                    if self.ex_take(r):
                        self.status = MoveStatus.FINISHED
                elif self.operation == "ex_put":
                    if self.ex_put(r):
                        self.status = MoveStatus.FINISHED
                else:
                    r.setError(f"脚本输入参数错误，请检查任务参数！{args}")
                    self.status = MoveStatus.FAILED
            else:
                if "finger" in args:
                    if self.finger(r, self.finger_pos):
                        self.update_finger_info(r)
                        self.status = MoveStatus.FINISHED
                elif "lift" in args or "rotate" in args:
                    if "lift" in args and not self.lift_ok:
                        self.lift_ok = self.lift(r, self.lift_height)
                    else:
                        self.lift_ok = True
                    if "rotate" in args and not self.rotate_ok:
                        self.rotate_ok = self.rotate(r, self.rotate_pos)
                    else:
                        self.rotate_ok = True
                    if self.lift_ok and self.rotate_ok:
                        self.status = MoveStatus.FINISHED
                elif "stretch" in args:
                    if self.stretch(r, self.stretch_length):
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
        self.report_info['script_args'] = self.script_args
        self.report_info['script_start_time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time))
        self.report_info['script_running_time'] = time.time() - self.start_time
        self.motor_calib_info['all_motor_enable'] = self.enable_motor
        self.motor_calib_info['lift_motor_calib'] = self.lift_motor_calib
        self.motor_calib_info['stretch_motor_calib'] = self.stretch_motor_calib
        self.motor_calib_info['rotate_motor_calib'] = self.rotate_motor_calib
        self.motor_calib_info['all_motor_calib'] = self.motor_calib_state
        self.report_info['motor_calib_info'] = self.motor_calib_info
        self.report_info['task_status'] = self.status
        self.report_info['goods_id'] = self.goods_id
        self.report_info['self_position'] = self.self_position
        self.report_info['containers'] = self.containers
        self.report_info['motor_info'] = self.container_robot.state or -1
        if self.status == MoveStatus.FAILED or self.status == MoveStatus.FINISHED:
            # r.disableMotor(self.lift_motor_name)
            r.release()
            r.setDO(self.fill_light_do, False)
            r.logInfo(f"script finished: {json.dumps(self.report_info)}")
        r.setInfo(json.dumps(self.report_info))
        r.logDebug(json.dumps(self.report_info))
        return self.status

    def init_script_args(self, r):
        # 重置识别前停稳计时 & 带料箱识别/异常恢复状态
        self.motor_settle_start = None
        self.unload_rec_box_lifted = False
        self.unload_rec_box_checked = False
        self.unload_rec_box_light = False
        self.unload_rec_adjust_done = False
        self.unload_shelf_occupied = False
        self.unload_recovery_step = [False] * 8
        self.unload_recovery_c = None
        self.ex_put_rec_box_lifted = False
        self.ex_put_rec_box_checked = False
        self.ex_put_rec_box_light = False
        self.ex_put_rec_adjust_done = False
        self.ex_put_shelf_occupied = False
        self.ex_put_recovery_c = None
        self.goods_id = self.script_args.get("goodsId", "")
        self.self_position = self.script_args.get("container", self.self_position)
        self.self_position = str(self.self_position) if self.self_position is not None else self.self_position
        self.update_move_task_params(r)
        self.finger_pos = self.script_args.get("finger", 0)
        self.lift_height = self.script_args.get("lift", 0)
        self.door_height = self.script_args.get("lift-door", 0)
        self.stretch_length = self.script_args.get("stretch", 0)
        self.is_auto_stretch = bool("stretch" not in self.script_args)  # 输入参数无"stretch"，则自动计算识别长度
        self.rotate_pos = self.script_args.get("rotate", 0)
        self.offset_x = self.script_args.get("offset_x", self.offset_x)
        self.pre_finger = self.script_args.get("pre_finger", self.pre_finger)
        if self.rec_box_extra_height == 0:
            self.rec_box_lift = 0
        else:
            self.rec_box_lift = self.lift_height + self.rec_box_extra_height
        self.rec_box_lift = self.script_args.get("recBoxLift", self.rec_box_lift)
        if self.rec_box_lift:
            self.rec_box = Rec(self.box_code_file, max_rec_times=1)
        self.code_type = self.script_args.get("visionBinType", "code")
        self.target_type = self.script_args.get("visionType", None)
        self.barcode_height = self.script_args.get("barcodeHeight", None)
        self.operation = self.script_args.get("operation", None)
        self.load_height = self.script_args.get("loadHeight", self.rec_offz_box)
        self.unload_height = self.script_args.get("unloadHeight", self.rec_offz_shelf)
        self.containers = r.getContainers()
        self.goods_manger = GoodsManger(r)
        self.rec_id = ModuleTool.get_uuid()
        self.box_code_file = self.script_args.get("code_file", self.box_code_file)
        self.shelf_code_file = self.script_args.get("shelf_code_file", self.shelf_code_file)
        r.clearError(53000)  # 清除过期的脚本 error
        r.clearWarning(55300)  # 清除过期的脚本 warning
        r.clearNotice(57300)  # 清除过期的脚本 notice
        if "recAdjust" in self.script_args:
            if self.target_type is None:
                if self.operation == "load" or self.operation == "ex_take":
                    self.rec_adjust = RecAdjust(r, self.box_code_file)
                elif self.operation == "unload" or self.operation == "ex_put":
                    self.rec_adjust = RecAdjust(r, self.shelf_code_file)
            elif self.target_type == "box":
                self.rec_adjust = RecAdjust(r, self.box_code_file)
            elif self.target_type == "shelf":
                self.rec_adjust = RecAdjust(r, self.shelf_code_file)
        if self.target_type == "box" and self.code_type == "code":
            self.rec = Rec(self.box_code_file)
        elif self.target_type == "shelf" and self.code_type == "code":
            self.rec = Rec(self.shelf_code_file)
        # 根据货叉货物检测光电更新货叉有无货信息
        # goods_check_di <= 0 时关闭货叉光电检货功能(-1 为关), 不校验也不清空
        if self.goods_check_di > 0:
            if self.stretch_real_pos < 0.05:  # 手臂未伸出状态下检测有效
                if ModuleTool.check_DI(r, self.goods_check_di) and not self.goods_manger.has_goods("999"):
                    r.setError(f"货叉光电检测到货叉中有货，但数据显示无货，需要人工核查处理")
                    self.status = MoveStatus.FAILED
                elif not ModuleTool.check_DI(r, self.goods_check_di):
                    r.clearContainer("999")
                    self.goods_manger = GoodsManger(r)

    @staticmethod
    def get_motor_info(r: SimModule, motor_name: str):
        motor_data = r.odo().get("motor_info", [])
        for _motor in motor_data:
            if _motor['motor_name'] == motor_name:
                return _motor
        return {}

    def check_motor_emc(self, r: SimModule):
        """
        检测急停状态, 驱动器上使能
        :param r:
        :return:
        """
        controller_emc = r.controller().get("emc", False)
        lift_motor_info = self.get_motor_info(r, self.lift_motor_name)  # 能查询到电机数据,说明驱动器已供电
        stretch_motor_info = self.get_motor_info(r, self.stretch_motor_name)
        rotate_motor_info = self.get_motor_info(r, self.rotate_motor_name)
        lift_motor_emc = lift_motor_info.get("emc", False)
        stretch_motor_emc = stretch_motor_info.get("emc", False)
        rotate_motor_emc = rotate_motor_info.get("emc", False)
        self.motor_calib_info["lift_motor_emc"] = lift_motor_emc
        self.motor_calib_info["stretch_motor_emc"] = stretch_motor_emc
        self.motor_calib_info["rotate_motor_emc"] = rotate_motor_emc
        self.motor_calib_info["controller_emc"] = controller_emc
        self.enable_motor = not lift_motor_emc and not rotate_motor_emc and not stretch_motor_emc  # 驱动器使能状态
        if not controller_emc and time.time() - self.enable_motor_time > 0.5:  # 控制器未急停
            self.enable_motor_time = time.time()
            if not r.isAnyErrorExists():
                if lift_motor_info and lift_motor_emc:  # 控制器未急停但是驱动器急停，给电机上使能
                    r.enableMotor(self.lift_motor_name)
                    self.report_info['lift_motor_info'] = lift_motor_info
                if stretch_motor_info and stretch_motor_emc:
                    r.enableMotor(self.stretch_motor_name)
                    self.report_info['stretch_motor_info'] = stretch_motor_info
                if rotate_motor_info and rotate_motor_emc:
                    r.enableMotor(self.rotate_motor_name)
                    self.report_info['rotate_motor_info'] = rotate_motor_info

    def motor_calib(self, r: SimModule):
        self.get_motor_calib_state(r)
        if not self.motor_calib_state:
            if not self.calib_step[0]:
                if not self.set_stretch_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    r.setMotorCalib(self.stretch_motor_name)
                    self.set_stretch_motor_calib = True

            elif self.calib_step[0] and not self.calib_step[1]:
                if not self.set_lift_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    r.setMotorCalib(self.lift_motor_name)
                    self.set_lift_motor_calib = True

            elif self.calib_step[1] and not self.calib_step[2]:
                if not self.set_rotate_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    r.setMotorCalib(self.rotate_motor_name)
                    self.set_rotate_motor_calib = True

            if r.warningExits(54305):
                # 检测由车体抖动引起的标零失败，重置标志位，重新下发标零指令
                self.set_lift_motor_calib = False
                self.set_rotate_motor_calib = False
                self.set_stretch_motor_calib = False
                r.clearWarning(54305)

            self.calib_step[0] = self.stretch_motor_calib
            self.calib_step[1] = self.lift_motor_calib
            self.calib_step[2] = self.rotate_motor_calib

    def get_motor_calib_state(self, r: SimModule):
        odo_data = r.odo()
        if odo_data.get("motor_info", None):
            motor_info = odo_data["motor_info"]
            self.report_info["motor_info"] = motor_info
            for m_f in motor_info:
                if m_f["motor_name"] == self.lift_motor_name:
                    self.lift_motor_calib = m_f["calib"]
                    self.lift_motor_stop = m_f["stop"]
                if m_f["motor_name"] == self.stretch_motor_name:
                    self.stretch_motor_calib = m_f["calib"]
                    self.stretch_motor_stop = m_f["stop"]
                if m_f["motor_name"] == self.rotate_motor_name:
                    self.rotate_motor_calib = m_f["calib"]
                    self.rotate_motor_stop = m_f["stop"]
        self.motor_calib_state = self.lift_motor_calib and self.stretch_motor_calib and self.rotate_motor_calib

    def force_calib(self, r: SimModule):
        if ModuleTool.delay(3):
            if not self.set_force_calib:
                self.set_force_calib = True
                r.setMotorCalib(self.lift_motor_name)
                r.setMotorCalib(self.stretch_motor_name)
                r.setMotorCalib(self.rotate_motor_name)
                self.motor_calib_state = False
        if self.set_force_calib and self.motor_calib_state:
            self.status = MoveStatus.FINISHED

    def cancel(self, r: SimModule):
        r.resetRec()
        self.close_finger(r)
        r.setDO(self.fill_light_do, False)
        self.status = MoveStatus.NONE

    def update_move_task_params(self, r):
        move_task = r.moveTask()
        bin_task = ""
        for p in move_task['params']:
            if p['key'] == 'goodsId':
                self.goods_id = p['string_value']
            if p['key'] == '#containerName' and p['string_value'] != "":
                self.self_position = p['string_value']
            if p['key'] == 'binTask':
                bin_task = p['string_value']
        if bin_task == "ex_put":
            self.self_position = "999"

    def zero(self, r: SimModule, zero_height=0.5):
        """
        支持指定高度执行标零复位
        :param r:
        :param zero_height:
        :return:
        """
        r.logInfo(f"----- running zero ------")
        if not self.zero_step[0]:
            self.zero_step[0] = self.goods_manger.has_goods("999") or self.finger(r, 1)
        elif self.zero_step[0] and not self.zero_step[1]:
            self.zero_step[1] = self.stretch(r, 0)
        elif self.zero_step[1] and not self.zero_step[2]:
            self.zero_step[2] = self.rotate(r, 0)
        elif self.zero_step[2] and not self.zero_step[3]:
            self.zero_step[3] = self.lift(r, zero_height)
        r.logDebug(f"zero_step:{self.zero_step}")
        if all(self.zero_step):
            # r.release()
            return True
        return False

    def lift(self, r, height):
        r.logInfo(f"----- running lift ------")
        if height < self.min_lift_height:
            height = self.min_lift_height
        if height > self.max_lift_height:
            r.setError(f"下发升降高度超上限，最大值：{self.max_lift_height}，下发值：{height}")
            self.status = MoveStatus.FAILED
            return False
        if self.stretch_real_pos > self.safe_stretch_length:
            r.setError(f"检测到伸缩机构未回零，无法执行升降，请先执行标零复位！")
            self.status = MoveStatus.FAILED
            return False
        # 只在目标改变或首次调用时发送命令
        if self.lift_executing != height:
            r.resetMotor(self.lift_motor_name)
            r.setMotorPosition(self.lift_motor_name, height, self.lift_motor_speed, -1)
            self.lift_executing = height  # 标记正在执行此目标

        if r.isMotorReached(self.lift_motor_name):
            r.resetMotor(self.lift_motor_name)
            self.lift_executing = None  # 完成后清除，允许重新发送
            return True
        return False

    def finger(self, r, pos):
        r.logInfo(f"----- running finger {pos}------")
        if not self.finger_open_start:
            self.finger_open_start = time.time()
        else:
            if time.time() - self.finger_open_start > 3:  # 防止手指机构卡死时电机过流烧毁
                r.setError(f"拨指控制超时，请检查拨指是否卡住、检查拨指到位光电是否能正常触发！")
                r.setDO(self.left_finger_up_do, False)
                r.setDO(self.right_finger_up_do, False)
                r.setDO(self.left_finger_down_do, False)
                r.setDO(self.right_finger_down_do, False)
                self.status = MoveStatus.FAILED
                return False
        if pos == 1:
            r.setDO(self.left_finger_up_do, True)
            r.setDO(self.right_finger_up_do, True)
            if ModuleTool.check_DI(r, self.left_finger_up_di):
                self.left_finger_real_pos = 1
                r.setDO(self.left_finger_up_do, False)
            if ModuleTool.check_DI(r, self.right_finger_up_di):
                self.right_finger_real_pos = 1
                r.setDO(self.right_finger_up_do, False)
            if ModuleTool.check_DI(r, self.left_finger_up_di) and ModuleTool.check_DI(r, self.right_finger_up_di):
                self.finger_open_start = False
                return True
        elif pos == 0:
            if ModuleTool.check_DI(r, self.overlimit_detect_di):
                # 超限光电检测到障碍物：报错并等待清障（人工推箱 或 障碍物自行移除）
                # setUserError 签名为 (code: int, msg: str)，第一个参数必须是 int 告警码
                r.setUserError(53901, "伸出长度不够，货叉超限光电检测到障碍物！请手动推箱消除超限，或上调取货伸出补偿参数值！")
                self.overlimit_alarm = True
                # 等待清障期间持续刷新防卡死计时，避免清障耗时超过 3s 被顶部超时守卫误判为 FAILED
                self.finger_open_start = time.time()
                return False
            # 超限光电已无遮挡：若此前报过超限错误，自动清错并进入异常恢复（继续合指抓取）
            if self.overlimit_alarm:
                r.clearError(53901)
                self.overlimit_alarm = False
                r.logInfo("超限光电障碍物已消除，自动清除 53901 错误，继续合指抓取")
            r.setDO(self.left_finger_down_do, True)
            r.setDO(self.right_finger_down_do, True)
            if ModuleTool.check_DI(r, self.left_finger_down_di):
                r.setDO(self.left_finger_down_do, False)
                self.left_finger_real_pos = 0
            if ModuleTool.check_DI(r, self.right_finger_down_di):
                r.setDO(self.right_finger_down_do, False)
                self.right_finger_real_pos = 0
            if ModuleTool.check_DI(r, self.left_finger_down_di) and ModuleTool.check_DI(r, self.right_finger_down_di):
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

    def stretch(self, r, length):
        r.logInfo(f"----- running stretch ------")
        temp_motor_speed = self.stretch_motor_speed
        if self.max_stretch_length < length < self.max_stretch_length + 0.1:
            r.setWarning(
                f"下发伸出长度值略微超上限，下发值：{length}，上限值：{self.max_stretch_length}。请检查货物是否离车体太远了！")
            length = self.max_stretch_length
        elif length > self.max_stretch_length + 0.1:
            r.setError(
                f"下发伸出长度值远超上限，下发值：{length}，上限值：{self.max_stretch_length}。请检查货物是否离车体太远了！！！")
            self.status = MoveStatus.FAILED
            return False
        # 手臂伸出且目标位置大于0.1m, 后半段速度减半
        if length > 0.1 and self.stretch_real_pos > length * 0.6:
            temp_motor_speed = self.stretch_motor_speed * 0.5
        # 只在目标改变或首次调用时发送命令
        if self.stretch_executing != length:
            r.resetMotor(self.stretch_motor_name)
            r.setMotorPosition(self.stretch_motor_name, length, temp_motor_speed, -1)
            self.stretch_executing = length  # 标记正在执行此目标

        if r.isMotorReached(self.stretch_motor_name):
            r.resetMotor(self.stretch_motor_name)
            self.stretch_executing = None  # 完成后清除
            return True
        return False

    def rotate(self, r, pos, max_speed=None):
        r.logInfo(f"----- running rotate ------")
        if abs(pos) > abs(self.max_rotate_angle / 180 * math.pi):
            r.setError(
                f"下发角度值超上限，下发值：{pos / math.pi * 180}，上限值：{self.max_rotate_angle}，请检查箱子是否摆歪，二维码是否破损！")
            self.status = MoveStatus.FAILED
            return False

        if self.stretch_real_pos > self.safe_stretch_length:
            r.setError(f"检测到伸缩机构未回零，无法执行旋转动作，请先执行标零复位！")
            self.status = MoveStatus.FAILED
            return False

        if max_speed is not None:
            speed = max_speed
        else:
            speed = self.rotate_motor_speed
        # 只在目标改变或首次调用时发送命令
        if self.rotate_executing != pos:
            r.resetMotor(self.rotate_motor_name)
            r.setMotorPosition(self.rotate_motor_name, pos, speed, -1)
            self.rotate_executing = pos  # 标记正在执行此目标

        if r.isMotorReached(self.rotate_motor_name):
            r.resetMotor(self.rotate_motor_name)
            self.rotate_executing = None  # 完成后清除
            return True
        return False

    def rec_barcode(self, r):
        """
        识别一维码。RecognizeBarCode 返回 status: 0 成功 / 1 识别中 / 2 识别失败。
        - 成功: 校验货物编码并返回一维码;
        - 识别中: 继续轮询, 不计数;
        - 识别失败: 连续重试下发识别, 超过 max_barcode_rec_times 次报错。
        @param r:
        @return: 识别成功返回一维码字符串, 否则返回 None
        """
        if not self.change_step[0]:
            r.setDO(self.fill_light_do, True)
            if ModuleTool.check_DO(r, self.fill_light_do):
                if ModuleTool.delay(self.light_delay_time):
                    self.change_step[0] = True
            return None

        status = self.rec_res.get("status", 1) if self.rec_res else None
        if status == 0:  # 识别成功
            r.setDO(self.fill_light_do, False)
            bar_code = self.rec_res.get("barCode", "")
            if bar_code != self.goods_id:
                r.setError(
                    f"货物编码不匹配, 任务下发的货物编码: {self.goods_id}, 识别的货物编码: {bar_code}")
                self.status = MoveStatus.FAILED
            self.report_info["barcode"] = bar_code
            return bar_code

        # 首次(None)/识别中(1)/识别失败(2): 按节拍下发识别, 仅识别失败计数
        if ModuleTool.delay(0.05):
            if status == 2:  # 识别失败, 计数并判断是否超限
                self.barcode_rec_times += 1
                if self.barcode_rec_times > self.max_barcode_rec_times:
                    r.setDO(self.fill_light_do, False)
                    r.setError(
                        f"连续识别{self.max_barcode_rec_times}次失败，请检查一维码是否破损、相机是否对准、识别文件({self.barcode_file})是否正确！")
                    self.status = MoveStatus.FAILED
                    self.report_info["barcode"] = "None"
                    return None
            self.rec_res = r.RecognizeBarCode(self.barcode_file, self.rec_id)
        self.report_info["barcode"] = "None"
        self.report_info["rec_id"] = self.rec_id
        return None

    def rec_box_barcode(self, r: SimModule):
        """
        指定货叉高度和角度位置识别一维码
        """
        if time.time() - self.start_time > 20:
            r.setError(f"未识别到一维码！请检查相机是否对准了一维码！")
            self.status = MoveStatus.FAILED
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(r, self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(r, self.rotate_pos)
        if self.opt_step[0] and self.opt_step[1] and not self.opt_step[2]:
            self.rec_barcode(r)
            if self.rec_res and self.rec_res.get("status", 1) == 0:
                self.report_info["barcode"] = self.rec_res['barCode']
                self.opt_step[2] = True
        if all(self.opt_step[0:3]):
            self.status = MoveStatus.FINISHED

    def rec_qrcode(self, r: SimModule):
        """
        指定货叉高度和角度位置识别二维码
        """
        if time.time() - self.start_time > 20:
            r.setError(f"未识别到二维码！请检查相机是否对准了二维码！")
            self.status = MoveStatus.FAILED
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(r, self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(r, self.rotate_pos)
        if all(self.opt_step[0:2]) and not self.opt_step[2]:
            r.setDO(self.fill_light_do, True)
            if ModuleTool.delay(self.light_delay_time):
                self.opt_step[2] = True
        if all(self.opt_step[0:3]) and not self.opt_step[3]:
            if self.rec.status == MoveStatus.FINISHED:
                data = {
                    "containerRobot": {
                        "locName": self.script_args.get("locName", ""),
                        "taskId": self.script_args.get("taskId", ""),
                        "load": {
                            "lift": self.lift_real_pos + self.rec.result['z'] + self.load_rec_lift_diff
                        },
                        "unload": {
                            "lift": self.lift_real_pos + self.rec.result['z']
                        }
                    }
                }
                r.tcpUploadString(json.dumps(data))  # 将数据传递给 Roboshop
                self.report_info["rec_qrcode_data"] = data
                self.rec.reset(r)
                r.setDO(self.fill_light_do, False)
                self.opt_step[3] = True
            else:
                self.rec.run(r, self)

        if all(self.opt_step[0:4]):
            self.status = MoveStatus.FINISHED

    def take_photo(self, r):
        """
        指定货叉高度和角度拍照
        @param r:
        @return:
        """
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(r, self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(r, self.rotate_pos)

        if all(self.opt_step[0:2]) and not self.opt_step[2]:
            r.setDO(self.fill_light_do, True)
            r.resetRec()  # 重置识别模块
            if ModuleTool.check_DO(r, self.fill_light_do):
                if ModuleTool.delay(self.light_delay_time):
                    self.opt_step[2] = True
        else:
            r.doRec(self.box_code_file)  # 下发拍照指令
            if ModuleTool.delay(0.5):
                r.setDO(self.fill_light_do, False)
                self.status = MoveStatus.FINISHED

    def load(self, r):
        r.logInfo(f"----- running load  {self.goods_id}------")
        load_info = dict()
        if not self.cur_c:
            if (self.goods_id and self.goods_manger.goods_id_exist(self.goods_id) and
                    self.goods_manger.get_container_by_goodsId(self.goods_id) != "999"):
                r.setError(f"货物{self.goods_id}已存在，请检查是否重复下发任务！")
                self.status = MoveStatus.FAILED
            if self.self_position:
                if self.goods_manger.has_goods(self.self_position):
                    if self.self_position == "999":
                        r.setError(f"货叉（999号）背篓已有货物，无法继续取货！请核对任务数据和背篓数据！")
                    else:
                        r.setError(f"第{int(self.self_position) + 1}层({self.self_position}号)背篓已有货物，无法继续取货！请核对任务数据和背篓数据！")
                    self.status = MoveStatus.FAILED
                self.cur_c = self.self_position
            else:
                self.cur_c = self.search_operable_container(r, 'load')
            r.logInfo(f"load begin: {json.dumps(self.containers)}")
            if self.cur_c is None:  # 车体满载了
                r.setError(f"车体所有背篓已满，无法继续取货！")
                self.status = MoveStatus.FAILED
                return

            if self.goods_manger.has_goods("999") and self.goods_manger.get_goodsId_by_container(
                    "999") == self.goods_id:
                self.load_step[:9] = [True] * 9
            elif self.goods_manger.has_goods("999"):  # 货叉已载货,但不是目标货物
                r.setError(f"货叉（999号）已载货，无法执行取货任务！请核对任务数据和背篓数据！")
                self.status = MoveStatus.FAILED
                return
        else:
            if not self.load_step[0]:
                self.load_step[0] = self.finger(r, 1)
            if not self.load_step[1]:
                self.load_step[1] = self.rotate(r, self.rotate_pos)
            if not self.load_step[2]:
                self.load_step[2] = self.lift(r, self.lift_height)
            elif (self.load_step[0] and self.load_step[1] and self.load_step[2] and
                  not self.load_step[3]):
                if self.barcode_height is not None:
                    # 必须等升降到识别高度、旋转到位后才下发一维码识别
                    lift_ok = self.lift(r, self.barcode_height)
                    rotate_ok = self.rotate(r, self.rotate_pos)
                    if lift_ok and rotate_ok:
                        self.load_step[3] = self.goods_id == self.rec_barcode(r)
                else:
                    self.load_step[3] = True
            elif self.load_step[3] and not self.load_step[4]:
                if self.rec_adjust is not None:
                    if self.light_st_time is None:
                        # 识别前先等机构停稳, 再开补光灯
                        if not self.wait_motors_settled(r):
                            pass
                        else:
                            self.reset_motor_settle()
                            r.setDO(self.fill_light_do, True)
                            self.light_st_time = time.time()
                    if self.light_st_time is not None and time.time() - self.light_st_time > self.light_delay_time:
                        if self.rec_adjust.status is MoveStatus.FINISHED:
                            r.setDO(self.fill_light_do, False)
                            self.light_st_time = None
                            self.load_step[4] = True
                        elif self.rec_adjust.status is MoveStatus.FAILED:
                            self.status = MoveStatus.FAILED
                        else:
                            self.rec_adjust.run(r, self)
                else:
                    self.load_height = 0
                    self.load_step[4] = True
            elif self.load_step[4] and not self.load_step[5]:
                self.load_step[5] = self.lift(r, self.lift_height + self.load_height)
            elif self.load_step[5] and not self.load_step[6]:
                if ModuleTool.check_DI(r, self.left_finger_up_di) and ModuleTool.check_DI(r, self.right_finger_up_di):
                    self.load_step[6] = self.stretch(r, self.stretch_length)
                else:
                    r.setError(f"检测到拨指未打开，取消执行伸出动作！请检查拨指及其到位光电是否正常！")
                    self.status = MoveStatus.FAILED
            elif self.load_step[6] and not self.load_step[7]:
                self.load_step[7] = self.finger(r, 0)
            elif self.load_step[7] and not self.load_step[8]:
                # 缩回前先校验拨指到位光电, 未到位不执行缩回
                if (not ModuleTool.check_DI(r, self.left_finger_down_di)) or (
                        not ModuleTool.check_DI(r, self.right_finger_down_di)):
                    r.setError(f"检测到手指张开，取消执行收回动作！请检查拨指及其到位光电是否正常！")
                    self.status = MoveStatus.FAILED
                    return
                self.load_step[8] = self.stretch(r, 0)
                if self.load_step[8]:
                    if self.goods_check_di <= 0 or ModuleTool.check_DI(r, self.goods_check_di):
                        # 手臂收回且光电检测成功(或未启用检货光电)时，增加货叉货物数据
                        r.setContainer("999", self.goods_id, "")
                    else:
                        r.setError(f"货叉已收回但货物检测光电未触发，货物{self.goods_id}可能未取到！请人工核查处理！")
                        self.status = MoveStatus.FAILED
                        return
            elif self.load_step[8] and (not self.load_step[9] or not self.load_step[10]):
                if not self.load_step[9]:
                    self.load_step[9] = self.rotate(r, 0)
                if self.cur_c == "999":
                    self.load_step[:15] = [True] * 15
                else:
                    if not self.load_step[10]:
                        self.load_step[10] = self.lift(r, self.high[int(self.cur_c)])
            elif self.load_step[9] and self.load_step[10] and not self.load_step[11]:
                self.load_step[11] = self.stretch(r, self.stretch_self_length)
            elif self.load_step[11] and not self.load_step[12]:
                self.load_step[12] = self.finger(r, 1)
            elif self.load_step[12] and not self.load_step[13]:
                self.load_step[13] = self.stretch(r, 0)
            elif self.load_step[13] and not self.load_step[14]:
                self.load_step[14] = self.finger(r, 0)
            elif self.load_step[14] and not self.load_step[15]:
                if "skip_safe_height" in self.script_args:
                    self.load_step[15] = True
                else:
                    self.load_step[15] = self.lift_safe_height(r)

            load_info['cur_container'] = self.cur_c
            load_info['goodsId'] = self.goods_id
            load_info['load_step'] = self.load_step
            load_info['lift-height'] = self.lift_height
            load_info['load-height'] = self.load_height
            load_info['lift-real-height'] = self.lift_real_pos
            self.report_info["load_info"] = load_info
            if all(self.load_step):
                # 在完成取货的所有动作后，增加背篓货物数据
                r.clearContainer("999")
                r.setContainer(self.cur_c, self.goods_id, "")
                return True

    def in_take(self, r: SimModule):
        """
        内部取货： 从背篓取货到货叉
        :param r:
        :return:
        """
        in_take_info = dict()
        if not self.cur_c:
            self.check_take(r)
        else:
            if self.cur_c == "999":
                self.status = MoveStatus.FINISHED
            else:
                if not self.in_take_step[0]:
                    self.in_take_step[0] = self.finger(r, 1)
                if not self.in_take_step[1]:
                    self.in_take_step[1] = self.lift(r, self.low[int(self.cur_c)])
                if not self.in_take_step[2]:
                    self.in_take_step[2] = self.rotate(r, 0)
                if all(self.in_take_step[0:3]) and not self.in_take_step[3]:
                    self.in_take_step[3] = self.stretch(r, self.stretch_self_length)
                elif self.in_take_step[3] and not self.in_take_step[4]:
                    self.in_take_step[4] = self.finger(r, 0)
                elif self.in_take_step[4] and not self.in_take_step[5]:
                    self.in_take_step[5] = self.stretch(r, 0)
                elif self.in_take_step[5] and not self.in_take_step[6]:
                    self.in_take_step[6] = self.rotate(r, self.rotate_pos)
                if self.in_take_step[5] and not self.in_take_step[7]:
                    self.in_take_step[7] = self.lift(r, self.lift_height)

        in_take_info["in_take_step"] = self.in_take_step[:8]
        in_take_info["cur_container"] = self.cur_c
        in_take_info["goodsId"] = self.goods_id
        self.report_info["in_take_info"] = in_take_info
        if all(self.in_take_step[:8]):
            r.clearContainer(self.cur_c)
            goods_id = self.goods_manger.get_goodsId_by_container(self.cur_c)
            r.setContainer("999", goods_id, "")
            return True

    def in_put(self, r: SimModule):
        """
        内部放货： 从货叉放货到背篓
        :param r:
        :return:
        """
        if not self.cur_c:
            self.check_put(r)
        else:
            if not self.in_put_step[0]:
                self.in_put_step[0] = self.lift(r, self.high[int(self.cur_c)])
            if not self.in_put_step[1]:
                self.in_put_step[1] = self.rotate(r, 0)
            if not self.in_put_step[2]:
                self.in_put_step[2] = True
            if all(self.in_put_step[0:3]) and not self.in_put_step[3]:
                self.in_put_step[3] = self.stretch(r, self.stretch_self_length)
            if all(self.in_put_step[0:4]) and not self.in_put_step[4]:
                self.in_put_step[4] = self.finger(r, 1)
            if all(self.in_put_step[0:5]) and not self.in_put_step[5]:
                self.in_put_step[5] = self.stretch(r, 0)
            if all(self.in_put_step[0:6]) and not self.in_put_step[6]:
                self.in_put_step[6] = self.finger(r, 0)
            if all(self.in_put_step[0:7]) and not self.in_put_step[7]:
                if "skip_safe_height" in self.script_args:
                    self.in_put_step[7] = True
                else:
                    self.in_put_step[7] = self.lift_safe_height(r)
        r.logInfo(f"----- running in_put ------")
        in_put_info = dict()
        in_put_info["goodsId"] = self.goods_id
        in_put_info["in_put_step"] = self.in_put_step[:7]
        self.report_info["in_put_info"] = in_put_info
        if all(self.in_put_step[0:8]):
            goods_id = self.goods_manger.get_goodsId_by_container("999")
            r.setContainer(self.cur_c, goods_id, "")
            r.clearContainer("999")
            return True

    def ex_take(self, r: SimModule):
        """
        外部取货： 从货架取货到货叉
        :param r:
        :return:
        """
        if self.goods_manger.has_goods("999"):  # 抓斗有货
            r.setError(f"检测到货叉（999号）已载货，无法执行外部取货动作！请核对任务数据和背篓数据！")
            self.status = MoveStatus.FAILED
            return
        r.logInfo(f"----- running ex_take ------")
        ex_take_info = dict()
        if self.barcode_height is not None:
            if not self.ex_take_step[0]:
                self.ex_take_step[0] = self.lift(r, self.barcode_height)
            if not self.ex_take_step[1]:
                self.ex_take_step[1] = self.rotate(r, self.rotate_pos)
            if all(self.ex_take_step[0:2]) and not self.ex_take_step[2]:
                self.ex_take_step[2] = self.goods_id == self.rec_barcode(r)
        else:
            self.ex_take_step[0:3] = [True] * 3

        if self.rec_adjust is not None:
            if not self.change_step[0]:
                self.change_step[0] = self.lift(r, self.lift_height)
            if not self.change_step[1]:
                self.change_step[1] = self.rotate(r, self.rotate_pos)
            if all(self.change_step[0:2]) and not self.change_step[2]:
                # 识别前先等机构停稳, 再开补光灯
                if not self.wait_motors_settled(r):
                    pass
                else:
                    self.reset_motor_settle()
                    r.setDO(self.fill_light_do, True)
                    self.rec_adjust.status = MoveStatus.RUNNING
                    if ModuleTool.check_DO(r, self.fill_light_do):
                        if ModuleTool.delay(self.light_delay_time):
                            self.change_step[2] = True
            if self.change_step[2] and not self.ex_take_step[3]:
                if self.rec_adjust.status is MoveStatus.FINISHED:
                    r.setDO(self.fill_light_do, False)
                    self.ex_take_step[3] = True
                elif self.rec_adjust.status is MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
                else:
                    self.rec_adjust.run(r, self)
        else:
            self.ex_take_step[3] = True

        if all(self.ex_take_step[0:4]) and not self.ex_take_step[4]:
            self.ex_take_step[4] = self.lift(r, self.lift_height + self.load_height)
            self.ex_take_step[5] = True
        if all(self.ex_take_step[0:6]) and not self.ex_take_step[6]:
            self.ex_take_step[6] = self.finger(r, 1)
        if all(self.ex_take_step[0:7]) and not self.ex_take_step[7]:
            self.ex_take_step[7] = self.stretch(r, self.stretch_length)
        if all(self.ex_take_step[0:8]) and not self.ex_take_step[8]:
            self.ex_take_step[8] = self.finger(r, 0)
        if all(self.ex_take_step[0:9]) and not self.ex_take_step[9]:
            self.ex_take_step[9] = self.stretch(r, 0)
        # if all(self.ex_take_step[0:10]) and not self.ex_take_step[10]:
        #     self.ex_take_step[10] = self.rotate(r, 0)

        ex_take_info['goodsId'] = self.goods_id
        ex_take_info['cur_container'] = self.cur_c
        ex_take_info['ex_take_step'] = self.ex_take_step[:10]
        self.report_info["ex_take_info"] = ex_take_info
        if all(self.ex_take_step[:10]):
            r.setContainer("999", self.goods_id, "")
            return True

    def ex_put(self, r: SimModule):
        """
        外部放货： 从货叉放货到货架
        带料箱识别防呆前置：到达放货高度后先识别货架是否有货，有货则触发异常恢复(把料箱放回背篓)，
        确认可放货后再识别料架调整(rec_adjust)、放货
        :param r:
        :return:
        """
        r.logInfo(f"----- running ex_put ------")
        if not self.goods_manger.has_goods("999"):  # 抓斗没货
            return self.unload(r)

        ex_put_info = dict()

        # ===== 正常放货流程 =====
        # Step 0: 升到放货高度
        if not self.ex_put_step[0]:
            self.ex_put_step[0] = self.lift(r, self.lift_height)

        # Step 1: 旋转到放货角度
        if not self.ex_put_step[1]:
            self.ex_put_step[1] = self.rotate(r, self.rotate_pos)

        # Step 2: 带料箱识别防呆前置 (升到 recBoxLift 识别货架是否有货), 有货则直接异常恢复,
        # 省去多余的识别料架动作; 识别料架(rec_adjust)后移到 Step 3
        # rec_box_lift 为用户指定的箱码识别高度, 既作开关也作高度; 数值为 0 时跳过识别
        if all(self.ex_put_step[0:2]) and not self.ex_put_step[2]:
            if self.rec_box_lift and not self.ex_put_rec_box_checked:
                # Step 2.a: 升到 recBoxLift
                if not self.ex_put_rec_box_lifted:
                    self.ex_put_rec_box_lifted = self.lift(r, self.rec_box_lift)
                # Step 2.b: 开补光灯并触发识别
                elif not self.ex_put_rec_box_light:
                    # 识别前先等机构停稳, 再开补光灯
                    if not self.wait_motors_settled(r):
                        pass
                    else:
                        self.reset_motor_settle()
                        r.setDO(self.fill_light_do, True)
                        self.rec_box.status = MoveStatus.RUNNING
                        self.rec_box.is_error = True
                        if ModuleTool.check_DO(r, self.fill_light_do):
                            if ModuleTool.delay(self.light_delay_time):
                                self.ex_put_rec_box_light = True
                # Step 2.c: 等识别结果
                else:
                    if self.rec_box.status is MoveStatus.FINISHED:
                        self.rec_box.reset(r)
                        self.rec_box.is_error = None
                        r.setDO(self.fill_light_do, False)
                        if self.rec_box.has_goods and not self.rec_box.goods_out_dist:
                            # 货架有货，触发异常恢复 (不再识别料架, 由下面异常恢复块接管)
                            self.ex_put_shelf_occupied = True
                            r.logInfo("ex_put rec_box_lift: 检测到货架已有货物，触发异常恢复")
                        self.ex_put_rec_box_checked = True
                    elif self.rec_box.status is MoveStatus.FAILED:
                        r.setDO(self.fill_light_do, False)
                        self.ex_put_rec_box_checked = True
                    else:
                        self.rec_box.run(r, self)
            elif self.rec_box_lift and not self.ex_put_shelf_occupied and self.rec_adjust is not None:
                # 货架空且配置了识别料架: 先降回放货高度再识别
                self.ex_put_step[2] = self.lift(r, self.lift_height)
            else:
                self.ex_put_step[2] = True

        # Step 3: 确认放货后识别料架调整 (如有配置) + 升放货补偿高度
        if all(self.ex_put_step[0:3]) and not self.ex_put_step[3]:
            if self.ex_put_shelf_occupied:
                # 识别到货架有货: 标记 step 3 完成但不升放货补偿高度, 让异常恢复块接管
                self.ex_put_step[3] = True
            elif self.rec_adjust is not None and not self.ex_put_rec_adjust_done:
                if not self.change_step[0]:
                    # 识别前先等机构停稳, 再开补光灯
                    if not self.wait_motors_settled(r):
                        pass
                    else:
                        self.reset_motor_settle()
                        r.setDO(self.fill_light_do, True)
                        self.rec_adjust.status = MoveStatus.RUNNING
                        if ModuleTool.check_DO(r, self.fill_light_do):
                            if ModuleTool.delay(self.light_delay_time):
                                self.change_step[0] = True
                else:
                    if self.rec_adjust.status is MoveStatus.FINISHED:
                        r.setDO(self.fill_light_do, False)
                        self.ex_put_rec_adjust_done = True
                    elif self.rec_adjust.status is MoveStatus.FAILED:
                        self.status = MoveStatus.FAILED
                    else:
                        self.rec_adjust.run(r, self)
            else:
                # 识别料架完成(或未配置): 升到放货补偿高度
                self.ex_put_step[3] = self.lift(r, self.lift_height + self.unload_height)

        # Step 4-5: 占位 (历史保留, 识别已合并进 step 3)
        if all(self.ex_put_step[0:4]) and not self.ex_put_step[4]:
            self.ex_put_step[4] = True
        if all(self.ex_put_step[0:5]) and not self.ex_put_step[5]:
            self.ex_put_step[5] = True

        # ===== 异常恢复分支：货架有货，把料箱放回背篓 =====
        if self.ex_put_shelf_occupied:
            # Step 12: 旋转归零 (货叉未伸出，无需缩回)
            if not self.ex_put_step[12]:
                self.ex_put_step[12] = self.rotate(r, 0)
            # Step 13: 查找空背篓
            elif not self.ex_put_step[13]:
                if self.ex_put_recovery_c is None:
                    self.ex_put_recovery_c = self.search_operable_container(r, 'load')
                    if self.ex_put_recovery_c is None:
                        r.setError("检测到货架上已经有货，且车体无空背篓可放回料箱！请人工处理！")
                        self.status = MoveStatus.FAILED
                        return
                    r.logInfo(f"ex_put 异常恢复: 将料箱放回{int(self.ex_put_recovery_c)+1}号背篓")
                self.ex_put_step[13] = True
            # Step 14: 升到目标背篓放货高度
            elif not self.ex_put_step[14]:
                self.ex_put_step[14] = self.lift(r, self.high[int(self.ex_put_recovery_c)])
            # Step 15: 伸到背篓位置
            elif not self.ex_put_step[15]:
                self.ex_put_step[15] = self.stretch(r, self.stretch_self_length)
            # Step 16: 松开手指，放回背篓
            elif not self.ex_put_step[16]:
                self.ex_put_step[16] = self.finger(r, 1)
            # Step 17: 缩回手臂
            elif not self.ex_put_step[17]:
                self.ex_put_step[17] = self.stretch(r, 0)
            # Step 18: 恢复背篓数据 & 报错
            elif not self.ex_put_step[18]:
                goods_id = self.get_fork_goods_id(r)
                r.clearContainer("999")
                r.setContainer(self.ex_put_recovery_c, goods_id, "")
                r.setError(f"检测到货架上已经有货，已将料箱放回{int(self.ex_put_recovery_c)+1}号背篓！请人工核查货架和任务数据！")
                self.status = MoveStatus.FAILED
                self.ex_put_step[18] = True

            ex_put_info["ex_put_step"] = self.ex_put_step[:19]
            ex_put_info["ex_put_shelf_occupied"] = True
            ex_put_info["ex_put_recovery_c"] = self.ex_put_recovery_c
            ex_put_info["goodsId"] = self.goods_id
            self.report_info["ex_put_info"] = ex_put_info
            return  # status 已设为 FAILED，等待 run() 回收

        # ===== 正常放货继续 =====
        # Step 6: 伸到放货长度
        if all(self.ex_put_step[0:6]) and not self.ex_put_step[6]:
            self.ex_put_step[6] = self.stretch(r, self.stretch_length)

        # Step 7: 松开手指 (放货)
        if all(self.ex_put_step[0:7]) and not self.ex_put_step[7]:
            self.ex_put_step[7] = self.finger(r, 1)

        # Step 8: 缩回手臂
        if all(self.ex_put_step[0:8]) and not self.ex_put_step[8]:
            self.ex_put_step[8] = self.stretch(r, 0)

        # Step 9: 旋转归零
        if all(self.ex_put_step[0:9]) and not self.ex_put_step[9]:
            self.ex_put_step[9] = self.rotate(r, 0)

        # Step 10: 合手指 (保持 5.0 行为: 放货后关闭手指复位)
        if all(self.ex_put_step[0:10]) and not self.ex_put_step[10]:
            self.ex_put_step[10] = self.finger(r, 0)

        # Step 11: 升到安全高度
        if all(self.ex_put_step[0:11]) and not self.ex_put_step[11]:
            if "skip_safe_height" in self.script_args:
                self.ex_put_step[11] = True
            else:
                self.ex_put_step[11] = self.lift_safe_height(r)

        ex_put_info["ex_put_step"] = self.ex_put_step[:12]
        ex_put_info["goodsId"] = self.goods_id
        self.report_info["ex_put_info"] = ex_put_info

        if all(self.ex_put_step[:12]):
            r.clearContainer("999")
            return True

    def unload(self, r):
        r.logInfo(f"----- running unload ------")
        unload_info = dict()
        if not self.cur_c:
            # 优先检查货叉中是否有货物
            if self.goods_manger.has_goods("999"):
                # 如果货叉有货，优先处理货叉中的货物
                self.cur_c = "999"
                if self.goods_manger.get_goodsId_by_container("999") != self.goods_id:
                    r.setError(
                        f"货叉中的货物ID与任务中的货物ID不一致，货叉货物ID：{self.goods_manger.get_goodsId_by_container('999')}，任务货物ID：{self.goods_id}")
                    self.status = MoveStatus.FAILED
                    return
            elif self.self_position:
                # 货叉无货时，才检查指定的背篓
                if self.goods_manger.get_goodsId_by_container(self.self_position) != self.goods_id:
                    r.setError(
                        f"{self.self_position}号背篓中的货物Id与任务的货物ID({self.goods_id})不匹配！请核对任务数据和背篓数据！")
                    self.status = MoveStatus.FAILED
                if not self.goods_manger.has_goods(self.self_position):
                    r.setError(f"{self.self_position}号背篓是空的，无法执行放货任务！请核对任务数据和背篓数据！")
                    self.status = MoveStatus.FAILED
                self.cur_c = self.self_position
            else:
                # 查找包含指定货物的容器
                self.cur_c = self.goods_manger.get_container_by_goodsId(self.goods_id)

            if not self.cur_c:
                r.setError(f"背篓中不存在货物: {self.goods_id}，无法执行放货任务！请核对任务数据和背篓数据！")
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
                        self.unload_step[1] = self.finger(r, 1)
                    if not self.unload_step[2]:
                        self.unload_step[2] = self.rotate(r, 0)
                elif self.unload_step[1] and self.unload_step[2] and not self.unload_step[3]:
                    self.unload_step[3] = self.stretch(r, self.stretch_self_length)
                elif self.unload_step[3] and not self.unload_step[4]:
                    self.unload_step[4] = self.finger(r, 0)
                elif self.unload_step[4] and not self.unload_step[5]:
                    if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                        if not self.unload_step[6]:
                            self.unload_step[6] = self.lift(r, self.lift_height)
                        if not self.unload_step[7]:
                            self.unload_step[7] = self.rotate(r, self.rotate_pos)
                    self.unload_step[5] = self.stretch(r, 0)
                    if self.unload_step[5] and (self.goods_check_di <= 0 or ModuleTool.check_DI(r, self.goods_check_di)):
                        goods_id = self.goods_manger.get_goodsId_by_container(self.cur_c)
                        r.setContainer("999", goods_id, "")
                        r.clearContainer(self.cur_c)

            if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                if not self.unload_step[6]:
                    self.unload_step[6] = self.lift(r, self.lift_height)
                if not self.unload_step[7]:
                    self.unload_step[7] = self.rotate(r, self.rotate_pos)
            elif self.unload_step[7] and not self.unload_step[8]:
                # 带料箱识别防呆前置：升到用户指定 recBoxLift 高度识别货架是否有货, 有货则直接异常恢复,
                # 省去多余的识别料架动作; 识别料架(rec_adjust)后移到确认放货之后
                # 注意: rec_box_lift 既作开关也作高度, 数值为 0 时跳过识别
                if self.rec_box_lift and not self.unload_rec_box_checked:
                    if not self.unload_rec_box_lifted:
                        self.unload_rec_box_lifted = self.lift(r, self.rec_box_lift)
                    elif not self.unload_rec_box_light:
                        # 识别前先等机构停稳, 再开补光灯
                        if not self.wait_motors_settled(r):
                            pass
                        else:
                            self.reset_motor_settle()
                            r.setDO(self.fill_light_do, True)
                            self.rec_box.status = MoveStatus.RUNNING
                            self.rec_box.is_error = True
                            if ModuleTool.check_DO(r, self.fill_light_do):
                                if ModuleTool.delay(self.light_delay_time):
                                    self.unload_rec_box_light = True
                    else:
                        if self.rec_box.status is MoveStatus.FINISHED:
                            self.rec_box.reset(r)
                            self.rec_box.is_error = None
                            r.setDO(self.fill_light_do, False)
                            self.unload_rec_box_checked = True
                            if self.rec_box.has_goods and not self.rec_box.goods_out_dist:
                                self.unload_shelf_occupied = True
                                r.logInfo("unload rec_box_lift: 检测到货架已有货物，触发异常恢复")
                        elif self.rec_box.status is MoveStatus.FAILED:
                            r.setDO(self.fill_light_do, False)
                            self.unload_rec_box_checked = True
                        else:
                            self.rec_box.run(r, self)
                elif self.rec_box_lift and not self.unload_shelf_occupied and self.rec_adjust is not None:
                    # 货架空且配置了识别料架: 先降回放货高度再识别
                    self.unload_step[8] = self.lift(r, self.lift_height)
                else:
                    self.unload_step[8] = True
            elif self.unload_step[8] and not self.unload_step[9]:
                if self.unload_shelf_occupied:
                    # 货架已检测到有货: 跳过识别料架和后续放货动作, 由异常恢复块兜底
                    self.unload_step[9] = True
                elif self.rec_adjust is not None and not self.unload_rec_adjust_done:
                    # 确认放货后识别料架调整
                    if not self.change_step[0]:
                        # 识别前先等机构停稳, 再开补光灯
                        if not self.wait_motors_settled(r):
                            pass
                        else:
                            self.reset_motor_settle()
                            r.setDO(self.fill_light_do, True)
                            self.rec_adjust.status = MoveStatus.RUNNING
                            if ModuleTool.check_DO(r, self.fill_light_do):
                                if ModuleTool.delay(self.light_delay_time):
                                    self.change_step[0] = True
                    else:
                        if self.rec_adjust.status is MoveStatus.FINISHED:
                            r.setDO(self.fill_light_do, False)
                            self.unload_rec_adjust_done = True
                        elif self.rec_adjust.status is MoveStatus.FAILED:
                            self.status = MoveStatus.FAILED
                        else:
                            self.rec_adjust.run(r, self)
                else:
                    # 识别料架完成(或未配置): 升到放货补偿高度准备伸出
                    self.unload_step[9] = self.lift(r, self.lift_height + self.unload_height)
            elif self.unload_step[9] and not self.unload_step[10]:
                if self.unload_shelf_occupied:
                    pass  # 货架有货时不伸出，等待异常恢复
                else:
                    if self.pre_finger is not None:
                        self.finger(r, self.pre_finger)
                    self.unload_step[10] = self.stretch(r, self.stretch_length)
            elif self.unload_step[10] and not self.unload_step[11]:
                self.unload_step[11] = self.finger(r, 1)
            elif self.unload_step[11] and not self.unload_step[12]:
                self.unload_step[12] = self.stretch(r, 0)
            elif self.unload_step[12] and (not self.unload_step[13]
                                           or not self.unload_step[14]
                                           or not self.unload_step[15]):
                if not self.unload_step[13]:
                    self.unload_step[13] = self.finger(r, 0)
                if not self.unload_step[14]:
                    self.unload_step[14] = self.rotate(r, 0)
                if not self.unload_step[15]:
                    if "skip_safe_height" in self.script_args:
                        self.unload_step[15] = True
                    else:
                        self.unload_step[15] = self.lift_safe_height(r)

            # ===== 异常恢复：货架有货，把料箱放回原背篓 (货叉未伸出，无需缩回) =====
            if self.unload_shelf_occupied:
                if not self.unload_recovery_step[0]:
                    self.unload_recovery_step[0] = self.rotate(r, 0)
                elif not self.unload_recovery_step[1]:
                    # 确定放回目标背篓
                    if self.unload_recovery_c is None:
                        if self.cur_c == "999":
                            # 货物原本就在叉上(如 ex_take 后直接 unload)，找空背篓
                            self.unload_recovery_c = self.search_operable_container(r, 'load')
                            if self.unload_recovery_c is None:
                                r.setError("检测到货架上已经有货，且车体无空背篓可放回料箱！请人工处理！")
                                self.status = MoveStatus.FAILED
                                return
                        else:
                            # 货物从背篓取出，放回原背篓
                            self.unload_recovery_c = self.cur_c
                    self.unload_recovery_step[1] = self.lift(r, self.high[int(self.unload_recovery_c)])
                elif not self.unload_recovery_step[2]:
                    self.unload_recovery_step[2] = self.stretch(r, self.stretch_self_length)
                elif not self.unload_recovery_step[3]:
                    self.unload_recovery_step[3] = self.finger(r, 1)  # 松开手指，放回背篓
                elif not self.unload_recovery_step[4]:
                    self.unload_recovery_step[4] = self.stretch(r, 0)
                elif not self.unload_recovery_step[5]:
                    # 恢复背篓数据：999→原背篓，与取货时(原背篓→999)对称
                    goods_id = self.get_fork_goods_id(r)
                    r.clearContainer("999")
                    r.setContainer(self.unload_recovery_c, goods_id, "")
                    r.setError(f"检测到货架上已经有货，已将料箱放回{int(self.unload_recovery_c)+1}号背篓！请人工核查货架和任务数据！")
                    self.status = MoveStatus.FAILED
                    self.unload_recovery_step[5] = True

                unload_info['unload_step'] = self.unload_step
                unload_info['unload_shelf_occupied'] = True
                unload_info['unload_recovery_step'] = self.unload_recovery_step
                unload_info['unload_recovery_c'] = self.unload_recovery_c
                unload_info['cur_container'] = self.cur_c
                unload_info['goodsId'] = self.goods_id
                self.report_info["unload_info"] = unload_info
                return  # status 已设为 FAILED，等待 run() 回收

            unload_info['unload_step'] = self.unload_step
            unload_info['cur_container'] = self.cur_c
            unload_info['goodsId'] = self.goods_id
            self.report_info["unload_info"] = unload_info

        if all(self.unload_step):
            # 在所有的动作完成后，将自身背篓的获取清除
            r.clearContainer("999")
            return True

    def lift_safe_height(self, r):
        if self.lift_real_pos > self.safe_lift_height:
            return self.lift(r, self.safe_lift_height)
        return True

    def wait_motors_settled(self, r):
        """
        识别前等待机构机械停稳: 升降/旋转/伸缩三轴 stop 标志为真, 且累计经过 motor_settle_delay 秒。
        首次调用记录起点, 调用方在到达识别触发点后每帧调用直到返回 True, 再开补光灯/触发识别。
        注意: self.lift_motor_stop 等字段只在 motor_calib 流程里写, 标零完成后不再更新, 因此这里
        直接从 r.odo() 实时读取, 不依赖外部状态。
        @return: True 表示已停稳满 motor_settle_delay 秒, False 表示尚需等待
        """
        lift_info = self.get_motor_info(r, self.lift_motor_name)
        rotate_info = self.get_motor_info(r, self.rotate_motor_name)
        stretch_info = self.get_motor_info(r, self.stretch_motor_name)
        all_stop = bool(lift_info.get("stop", False)
                        and rotate_info.get("stop", False)
                        and stretch_info.get("stop", False))
        if not all_stop:
            # 任一轴还在动, 复位计时, 等下次稳定后重新计时
            self.motor_settle_start = None
            return False
        if self.motor_settle_start is None:
            self.motor_settle_start = time.time()
            return False
        return time.time() - self.motor_settle_start >= self.motor_settle_delay

    def reset_motor_settle(self):
        """识别完成/失败后重置停稳计时, 供下一次识别使用"""
        self.motor_settle_start = None

    def get_fork_goods_id(self, r: SimModule):
        """从 r.getContainers() 实时读取货叉(999)上的货号，避免 GoodsManger 快照过期"""
        for c in r.getContainers():
            if c.get("container_name") == "999":
                return c.get("goods_id", "")
        return ""

    def update_report_info(self, r):
        module_pos = dict()
        self.lift_real_pos = ModuleTool.get_motor_pos(r, self.lift_motor_name)
        self.stretch_real_pos = ModuleTool.get_motor_pos(r, self.stretch_motor_name)
        self.rotate_real_pos = ModuleTool.get_motor_pos(r, self.rotate_motor_name)
        self.update_finger_info(r)
        module_pos['lift'] = round(self.lift_real_pos, 3)
        module_pos['stretch'] = round(self.stretch_real_pos, 3)
        module_pos['rotate'] = round(self.rotate_real_pos * 180 / math.pi, 3)
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
        ct = None
        if opt == 'load':
            for c in self.containers:
                if not c['has_goods']:
                    ct = c['container_name']
                    break
        elif opt == 'unload':
            for c in self.containers:
                if c['has_goods'] and self.goods_id == c['goods_id']:
                    ct = c['container_name']
        return ct

    def check_put(self, r: SimModule):
        """
        放货到背篓前，检查背篓有空位且货叉有货
        :param r:
        :return:
        """
        self.goods_manger = GoodsManger(r)
        if not self.goods_manger.has_goods("999"):  # 货叉无货
            r.setNotice(f"货叉（999号）没有货物，无需内部放货！")
            self.status = MoveStatus.FINISHED
            return

        # 货物在背篓里
        if (self.goods_id and self.goods_manger.goods_id_exist(self.goods_id) and
                self.goods_manger.get_container_by_goodsId(self.goods_id) != "999"):
            r.setNotice(f"货物已在背篓中")
            self.status = MoveStatus.FINISHED
            return

        if self.self_position:
            if self.goods_manger.has_goods(self.self_position):
                r.setError(f"第{self.self_position + 1}({self.self_position}号)已有货物，无法继续存放货物！")
                self.status = MoveStatus.FAILED
                return
            self.cur_c = self.self_position
        else:
            self.cur_c = self.search_operable_container(r, 'load')  # 查找空位

        if self.cur_c is None:  # 车体满载了
            r.setNotice(f"车体所有背篓已满，货叉（999号）载货中")
            self.status = MoveStatus.FINISHED
            return

    def check_take(self, r: SimModule):
        """
        从背篓取货前检测背篓货物信息，检查货叉为空
        :param r:
        :return:
        """
        self.goods_manger = GoodsManger(r)
        if self.self_position:
            if not self.goods_manger.has_goods(self.self_position):
                r.setError(f"第{int(self.self_position) + 1}层({self.self_position}号)背篓是空的，无法执行内部取货动作！")
                self.status = MoveStatus.FAILED
            self.cur_c = self.self_position
        else:
            self.cur_c = self.goods_manger.get_container_by_goodsId(self.goods_id)

        if self.goods_manger.has_goods("999"):  # 抓斗有货
            self.cur_c = "999"

        if not self.cur_c:
            r.setError(f"货物{self.goods_id}不存在，请核对货物编号和背篓数据！")
            self.status = MoveStatus.FAILED
            return


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
            if ModuleTool.delay(0.05):
                self.rec_times = self.rec_times + 1
                if self.rec_times > self.max_rec_times:
                    if not self.is_error:
                        r.setError(
                            f"连续识别{self.max_rec_times}次失败，请检查二维码是否损坏，请手动识别并查看照片是否清晰！")
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
        self.lift_step = None
        self.status = MoveStatus.NONE
        self.rec = Rec(filename)
        self.result = []
        self.max_rec_fail_times = 10
        self.max_adjust_time = 30
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.code_check_fail = 0  # objectMessage 与 goodsId 比较失败次数
        self.go_args = dict()
        self.ok = False

        self.next_rotate_pos = 1.5708  # 默认值
        self.diff_height = 0  # 识别高度差
        self.last_yaw_adjust = 1.5708
        self.plan_status = MoveStatus.NONE
        self.goPath = goPath.Module(r, dict())
        self.code2robot = -1

    @staticmethod
    def move_x(dx, dy, yaw, rotate_pos, offset_x=0):
        """
        计算车体在x方向上移动的距离
        rotate_pos 是货叉旋转方向
        (dx, dy, yaw)是识别结果
        """
        if rotate_pos > 0:
            if yaw > 0:
                return -dy - dx * math.tan(math.pi - yaw) - offset_x
            elif yaw < 0:
                return -dy + dx * math.tan(math.pi + yaw) - offset_x
        else:
            if yaw > 0:
                return dy + dx * math.tan(math.pi - yaw) + offset_x
            elif yaw < 0:
                return dy - dx * math.tan(math.pi + yaw) + offset_x

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
                random_dist = random.choice([1, -1]) * (1 / 180 * math.pi)
                agv.rotate(r, agv.rotate_real_pos + random_dist, max_speed=0.3)  # 识别失败时，货叉随机左右扭动 1° 继续识别
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.rec.reset(r)
                    self.rec.run(r, agv)
                else:
                    self.status = MoveStatus.FAILED
                r.logInfo("rec fail!!! {}".format(self.rec_fail_time))
            elif self.rec.status is MoveStatus.FINISHED:
                r.logInfo(f"------------------ move to adjust -----------------")
                self.rec_fail_time = 0
                # 通过参数配置，使识别结果为二维码在料斗坐标系下的坐标位置, (右手坐标系)x轴向前，y轴向左, z轴向上

                """获取结果"""
                # 计算手臂伸出长度
                if agv.is_auto_stretch:
                    if agv.operation == "load":
                        agv.stretch_length = (abs(self.rec.result['x']) - agv.auto_stretch_odo_len +
                                              agv.auto_load_stretch_dist + agv.auto_stretch_box_len)
                    elif agv.operation == "unload":
                        agv.stretch_length = (abs(self.rec.result['x']) - agv.auto_stretch_odo_len +
                                              agv.auto_unload_stretch_dist + agv.auto_stretch_box_len)

                code2fork = [self.rec.result['x'], self.rec.result['y'], self.rec.result['z'],
                             self.rec.result['yaw']]
                # code2fork = [self.rec.result['x'], self.rec.result['y'], self.rec.result['yaw']]
                # fork2robot = [-0, 0, agv.rotate_real_pos]
                # self.code2robot = Pos2World(code2fork, fork2robot)

                self.diff_height = self.rec.result['z']
                agv.rec_height_diff = self.rec.result['z']
                # 根据反馈的yaw来判断rotate调整方向
                agv.yaw_adjust = math.pi - abs(code2fork[3])  # 角度偏差
                if code2fork[3] > 0:  # 识别结果为正值
                    self.next_rotate_pos = agv.rotate_real_pos - agv.yaw_adjust
                else:  # 识别结果为负值
                    self.next_rotate_pos = agv.rotate_real_pos + agv.yaw_adjust

                # 计算移动距离
                if bool(agv.auto_adjust_rotate):
                    rec_yaw = self.rec.result['yaw']
                else:
                    rec_yaw = math.pi
                x_dist = self.move_x(self.rec.result['x'], self.rec.result['y'], rec_yaw, agv.rotate_real_pos,
                                     agv.offset_x)
                self.go_args["x"] = x_dist
                self.go_args["coordinate"] = "robot"
                self.go_args["y"] = 0
                self.go_args["theta"] = 0
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["maxSpeed"] = 0.3  # 设置二次调整时底盘移动最大速度, m/s
                self.go_args["maxAcc"] = 0.3
                self.go_args["maxDec"] = 0.3
                self.go_args["reachDist"] = 0.003
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                else:
                    self.go_args["backMode"] = 0

                if abs(agv.yaw_adjust) > agv.max_yaw_bias:
                    self.status = MoveStatus.FAILED
                    r.setError(
                        f"识别到角度偏差{agv.yaw_adjust}超出上限值{agv.max_yaw_bias}，请检查料箱是否摆正，二维码是否损坏！")
                else:
                    if self.adjust_count >= (self.max_adjust_time - 3):
                        agv.ok_x = 0.01
                        agv.ok_yaw = 0.02
                    # 精度满足, 识别调整任务完成
                    if not bool(agv.auto_adjust_rotate) and abs(self.rec.result['y']) < agv.ok_x:
                        r.logInfo(f"adjust finished, adjust count: {self.adjust_count}")
                        if self.check_goods_code(r, agv):
                            self.status = MoveStatus.FINISHED
                    elif bool(agv.auto_adjust_rotate) and abs(self.rec.result['y']) < agv.ok_x and abs(
                            agv.yaw_adjust) <= agv.ok_yaw:
                        r.logInfo(f"adjust finished, adjust count: {self.adjust_count}")
                        if self.check_goods_code(r, agv):
                            self.status = MoveStatus.FINISHED
                    else:
                        if self.adjust_count >= self.max_adjust_time:
                            self.status = MoveStatus.FAILED
                            r.setError(
                                f"识别调整{self.adjust_count}次未达到精度要求，请检查二维码是否损坏，相机画面是否清晰，精度参数是否设置合理！")
                self.plan_status = MoveStatus.FINISHED
                self.rec.reset(r)
        elif self.status is not MoveStatus.FINISHED and self.status is not MoveStatus.FAILED:
            if self.goPath.status != MoveStatus.FINISHED and self.goPath.status != MoveStatus.FAILED:
                if abs(self.go_args['x']) < 0.003:  # 调整值小于底盘移动精度
                    self.goPath.status = MoveStatus.FINISHED
                else:
                    if self.goPath.status != MoveStatus.FINISHED and self.goPath.status != MoveStatus.FAILED:
                        self.goPath.run(r, self.go_args)
            elif not self.rotate_step and self.goPath.status == MoveStatus.FINISHED:
                if abs(agv.yaw_adjust) <= 0.01:  # 调整值小于货叉旋转精度
                    self.rotate_step = True
                if not self.rotate_step and bool(agv.auto_adjust_rotate):
                    self.rotate_step = agv.rotate(r, self.next_rotate_pos, max_speed=0.3)  # 货叉角度偏移修正
                else:
                    self.rotate_step = True
            elif self.goPath.status == MoveStatus.FAILED:
                self.status = MoveStatus.FAILED
            elif self.goPath.status == MoveStatus.FINISHED and self.rotate_step:
                self.reset(r)
                self.adjust_count += 1
                self.last_yaw_adjust = agv.yaw_adjust
                self.plan_status = MoveStatus.NONE
                self.rotate_step = False
        cur_state["auto_stretch_length"] = agv.stretch_length
        cur_state["go_path_status"] = self.goPath.status
        cur_state["go_args"] = self.go_args
        cur_state["rec_result"] = self.rec.result
        cur_state["rec_fail_time"] = self.rec_fail_time
        cur_state["adjust_count"] = self.adjust_count
        cur_state["cur_rotate"] = agv.rotate_real_pos / math.pi * 180
        cur_state["cur_lift"] = agv.lift_real_pos
        cur_state["cur_stretch"] = agv.stretch_real_pos
        cur_state["status"] = self.status
        cur_state["agv_yaw_adjust"] = agv.yaw_adjust / math.pi * 180
        cur_state["last_yaw_adjust"] = self.last_yaw_adjust / math.pi * 180
        cur_state["next_rotate_pos"] = self.next_rotate_pos / math.pi * 180
        agv.report_info["rec_adjust"] = cur_state
        r.logDebug(f"[ContainerRobot][{agv.lift_real_pos}|{agv.stretch_real_pos}|{agv.rotate_real_pos / math.pi * 180}|"
                   f"{self.rec.result.get('x', 0)}|{self.rec.result.get('y', 0)}|{self.rec.result.get('z', 0)}|{self.rec.result.get('yaw', 0)}|"
                   f"{agv.yaw_adjust / math.pi * 180}|{self.last_yaw_adjust / math.pi * 180}|{self.next_rotate_pos / math.pi * 180}|"
                   f"{self.rec_fail_time}|{self.adjust_count}|{self.rec.rec_times}|{self.go_args.get('x', 0)}|")

    def check_goods_code(self, r: SimModule, agv: Module):
        """
        比较识别结果上报的 objectMessage 与任务下发的 goodsId。
        一致才放行(返回 True)；不一致时重试识别，多次比较失败则报错。
        仅取货(load)动作校验：识别的是料箱货物编码，需与下发 goodsId 一致。
        放货(unload)时 goodsId 用于指定背篓取对应料箱，识别的是货架码放货位，无需校验，直接放行。
        开关关闭(check_goods_code_enable=0)或 goodsId 为空时也不校验，直接放行。
        @return: bool 是否放行通过
        """
        rec_code = self.rec.result.get("objectMessage", "")
        agv.report_info["rec_code"] = rec_code
        # 仅取货动作校验货物编码；卸货识别货架货位, 不校验
        if agv.operation != "load":
            return True
        # 未开启校验或无下发编码(手动调试等场景)时直接放行
        if not bool(agv.check_goods_code_enable) or not agv.goods_id:
            return True
        if rec_code == agv.goods_id:
            self.code_check_fail = 0
            return True
        # 编码不匹配
        self.code_check_fail += 1
        r.logInfo(
            f"货物编码不匹配({self.code_check_fail}/{agv.max_code_check_fail}), "
            f"任务下发: {agv.goods_id}, 识别: {rec_code}")
        if self.code_check_fail >= agv.max_code_check_fail:
            r.setError(
                f"货物编码不匹配, 任务下发的货物编码: {agv.goods_id}, 识别的货物编码: {rec_code}")
            self.status = MoveStatus.FAILED
        # 未达上限时不放行, 外层调整流程会重新识别再比较
        return False

    def reset(self, r):
        self.rec.reset(r)
        self.status = MoveStatus.RUNNING
        self.rec_fail_time = 0
        self.goPath.reset()


if __name__ == '__main__':
    sim = SimModule()
    args1 = {}
    m = Module(sim, args1)
    rec = RecAdjust(sim, '')
    counter = 0
    while m.status is not MoveStatus.FAILED and m.status is not MoveStatus.FINISHED:
        m.run(sim, args1)
        counter += 1
        if counter > 1:
            break
