# -*- coding: utf-8 -*-
# @Date: 2025/07/24
# @Author:
# @Version: 3.8
# @Project: 智千、河狸料箱车
# @Update: 适配3.5
# @RBK Version: V3.5+
import enum
import uuid

SCRIPT_VERSION = "V35-20250831"
import json
import math
import random
import time

from syspy.utils.time import Timer
from syspy import Module, Logger, Di, Do, Motor, Navigation, ScriptStatus, Abnormal, Controller, Odometer, Recognize, \
    RobotParam, Trace
from syspy.lib.net_protocol import parse_modbus, NetProtocol
from syspy.bin import Container
from syspy.lib.module import SafeMoveStatus, ModuleBase
from syspy.utils.param_server import ParamBuilder, ParamType, ParamServer, ParamValidator
from tasks.standard.goPath import GoPath

log = Logger("ContainerRobot")


class ConfigParams:
    p = ParamServer(__file__)
    # 超时参数
    timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                          group="script", comment="运行超时时间")
    # 背篓层高参数
    low = dict()
    high = dict()
    low[0] = p.loadParam("low0", type="float", default=0.4, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第0号背篓取料箱高度, 最低层, 从0号计数")
    high[0] = p.loadParam("high0", type="float", default=0.41, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第0号背篓放料箱高度, 最低层, 从0号计数")
    low[1] = p.loadParam("low1", type="float", default=0.82, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第1号背篓取料箱高度")
    high[1] = p.loadParam("high1", type="float", default=0.83, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第1号背篓放料箱高度")
    low[2] = p.loadParam("low2", type="float", default=1.25, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第2号背篓取料箱高度")
    high[2] = p.loadParam("high2", type="float", default=1.26, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第2号背篓放料箱高度")
    low[3] = p.loadParam("low3", type="float", default=1.675, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第3号背篓取料箱高度")
    high[3] = p.loadParam("high3", type="float", default=1.68, maxValue=10000.0, minValue=0.0, unit="m",
                          comment="第3号背篓放料箱高度")
    low[4] = p.loadParam("low4", type="float", default=2.095, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第4号背篓取料箱高度")
    high[4] = p.loadParam("high4", type="float", default=2.10, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第4号背篓放料箱高度")
    low[5] = p.loadParam("low5", type="float", default=2.515, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第5号背篓取料箱高度")
    high[5] = p.loadParam("high5", type="float", default=2.525, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第5号背篓放料箱高度")
    low[6] = p.loadParam("low6", type="float", default=2.945, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第6号背篓取料箱高度")
    high[6] = p.loadParam("high6", type="float", default=2.955, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第6号背篓放料箱高度")
    low[7] = p.loadParam("low7", type="float", default=3.375, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第7号背篓取料箱高度")
    high[7] = p.loadParam("high7", type="float", default=3.385, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第7号背篓放料箱高度")
    low[8] = p.loadParam("low8", type="float", default=3.825, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第8号背篓取料箱高度")
    high[8] = p.loadParam("high8", type="float", default=3.835, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第8号背篓放料箱高度")
    # 伸缩参数
    stretch_self_length = p.loadParam("stretch_self_length", type="float", default=0.73, maxValue=10000.0,
                                      group="stretch", minValue=0.0, unit="m",
                                      comment="取放自身背篓货物时伸出长度")
    # 识别偏移参数
    rec_offz_box = p.loadParam("rec_offz_box", type="float", default=-0.08, maxValue=1000.0, minValue=-1000.0,
                               group="recognize", unit="m", comment="识别料箱码后抓取料箱时调整高度")
    rec_offz_shelf = p.loadParam("rec_offz_shelf", type="float", default=0.02, maxValue=1000.0,
                                 minValue=-1000.0, group="recognize", unit="m",
                                 comment="识别货架码后放置料箱时调整高度")
    # DI参数
    fork_up_limit = p.loadParam("fork_up_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                group="lift", comment="货叉上限位DI")
    fork_down_limit = p.loadParam("fork_down_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                  group="lift", comment="货叉下限位DI")
    fork_limit = p.loadParam("fork_limit", type="int", default=3, maxValue=100, minValue=-1, unit="",
                             group="lift", comment="货叉升降机械限位限位DI")
    # 高度限制参数
    min_lift_height = p.loadParam("min_fork_height", type="float", default=0.38, maxValue=10000.0,
                                  minValue=0.0, unit="m", comment="货叉最低高度")
    max_lift_height = p.loadParam("max_fork_height", type="float", default=4.5, maxValue=10000.0,
                                  group="lift", minValue=0.0, unit="m", comment="货叉最大高度")
    # 角度限制参数
    max_rotate_angle = p.loadParam("max_rotate_angle", type="float", default=100,
                                   group="rotate", comment="货叉最大旋转角度值")
    # 伸缩限制参数
    max_stretch_length = p.loadParam("max_stretch_length", type="float", default=0.90, unit="m",
                                     group="stretch", comment="货叉最大伸出长度")
    safe_stretch_length = p.loadParam("safe_stretch_length", type="float", default=0.05, maxValue=10000.0,
                                      group="stretch", minValue=0.0, unit="m",
                                      comment="货叉升降、旋转操作时伸缩臂安全长度")
    # 安全高度参数
    safe_lift_height = p.loadParam("safe_lift_height", type="float", default=1.0, maxValue=10000.0,
                                   group="lift", minValue=0.0, unit="m",
                                   comment="货叉安全高度, 货叉导航过程中的最高高度")
    # 传感器参数
    has_fork_sensor = p.loadParam("has_fork_sensor", type="int", default=0,
                                  group="DI", comment="货叉是否有货物检测传感器，1为有，0为无")
    has_tray_sensor = p.loadParam("has_tray_sensor", type="int", default=0,
                                  group="DI", comment="背篓是否有货物检测传感器，1为有，0为无")
    fork_sensor_di = p.loadParam("fork_sensor_di", type="int", default=9, maxValue=100, minValue=-1, unit="",
                                 group="DI", comment="货叉检测DI")
    overlimit_detect_di = p.loadParam("overlimit_detect_di", type="str", default="OVERRIDE",
                                      group="DI", comment="检测货叉伸出是否超过料箱的DI")
    # 识别文件参数
    box_code_file = p.loadParam("box_code_file", type="str", default="default.srec",
                                group="recognize", comment="料箱二维码识别文件")
    shelf_code_file = p.loadParam("shelf_code_file", type="str", default="default.srec",
                                  group="recognize", comment="货架二维码识别文件")
    barcode_file = p.loadParam("barcode_file", type="str", default="default.srec",
                               group="recognize", comment="条形码识别文件")
    # 电机速度参数
    lift_motor_speed = p.loadParam("lift_motor_speed", type="float", default=1.5,
                                   group="lift", comment="升降电机运转速度")
    stretch_motor_speed = p.loadParam("stretch_motor_speed", type="float", default=1.0,
                                      group="stretch", comment="伸缩电机运转速度")
    rotate_motor_speed = p.loadParam("rotate_motor_speed", type="float", default=1.0,
                                     group="rotate", comment="旋转电机运转速度")
    # 电机名称参数
    lift_motor_name = p.loadParam("lift_motor_name", type="str", default="Motor-002",
                                  group="lift", comment="升降电机名称")
    stretch_motor_name = p.loadParam("stretch_motor_name", type="str", default="Motor-004",
                                     group="stretch", comment="伸缩电机名称")
    rotate_motor_name = p.loadParam("rotate_motor_name", type="str", default="Motor-003",
                                    group="rotate", comment="旋转电机名称")

    # 自动计算参数
    auto_stretch_box_len = p.loadParam("auto_stretch_box_len", type="float", default=0.6, maxValue=100,
                                       group="stretch", minValue=-1, unit="", comment="箱子长度")
    auto_load_stretch_dist = p.loadParam("auto_load_stretch_dist", type="float", default=0.01,
                                         group="stretch", unit="m", comment="自动计算取货伸出长度时的补偿值")
    auto_unload_stretch_dist = p.loadParam("auto_unload_stretch_dist", type="float", default=0.01,
                                           group="stretch", unit="m", comment="自动计算放货伸出长度时的补偿值")
    auto_stretch_odo_len = p.loadParam("auto_stretch_odo_len", type="float", default=0.38, maxValue=100,
                                       group="stretch", minValue=20, unit="",
                                       comment="手指机构到货叉旋转中心的距离")
    auto_adjust_rotate = p.loadParam("auto_adjust_rotate", type="int", default=1,
                                     group="rotate", comment="识别时是否需要自动调整货叉角度，1：需要 0：不需要")
    # 识别补偿参数
    offset_x = p.loadParam("offset_x", type="float", default=0.1,
                           group="recognize", comment="针对识别结果误差在x方向的补偿值")
    light_delay_time = p.loadParam("light_delay_time", type="float", default=0.3,
                                   group="recognize", comment="补光灯延时拍照时间")
    load_rec_lift_diff = p.loadParam("load_rec_lift_diff", type="float", default=0.05,
                                     group="recognize", comment="取货识别料箱高度与货架上表面的高度差")
    rec_box_extra_height = p.loadParam("rec_box_extra_height", type="float", default=0.0,
                                       comment="放货识别货架上是否有货物时，在放货高度上需要额外抬升的高度，该值可设置为货架码到料箱码的高度差")
    # 手指控制DO
    finger_up_do = p.loadParam("finger_up_do", type="str", default="DO-015", group="finger",
                               comment="手指打开DO")
    finger_down_do = p.loadParam("finger_down_do", type="str", default="DO-014", group="finger",
                                 comment="手指关闭DO")

    # 手指到位DI
    left_finger_up_di = p.loadParam("left_finger_up_di", type="str", default="DI-019", group="finger",
                                    comment="左手指打开到位DI")
    left_finger_down_di = p.loadParam("left_finger_down_di", type="str", default="DI-022", group="finger",
                                      comment="左手指关闭到位DI")
    right_finger_up_di = p.loadParam("right_finger_up_di", type="str", default="DI-018", group="finger",
                                     comment="右手指打开到位DI")
    right_finger_down_di = p.loadParam("right_finger_down_di", type="str", default="DI-016",
                                       group="finger",
                                       comment="右手指关闭到位DI")

    goods_check_di = p.loadParam("goods_check_di", type="str", default="DI-011", group="goods",
                                 comment="货叉中部货物检测光电DI")
    fill_light_do = p.loadParam("fill_light_do", type="str", default="DO-005", group="light",
                                comment="补光灯DO")

    ok_x = p.loadParam("ok_x", type="float", default=0.01, comment="x方向行走调整完成阈值")
    ok_yaw = p.loadParam("ok_yaw", type="float", default=0.015, comment="调整完成弧度阈值")
    max_yaw_bias = p.loadParam("max_yaw_bias", type="float", default=0.13,
                               comment="货叉与料箱角度最大偏差, 弧度值")


def create_container_param(builder: ParamBuilder, desc: str = "车体背篓号"):
    """创建车体背篓号参数"""
    with builder.CHILD(key="container", name="Container",
                       desc=desc):
        builder.MIN_VALUE(0)
        builder.MAX_VALUE(998)
        builder.TYPE(ParamType.INT)
        builder.DEFAULTVALUE(0)


def create_goods_id_param(builder: ParamBuilder, desc: str = "货物编号"):
    """创建货物编号参数"""
    with builder.CHILD(key="goodsId", name="Goods Id", desc=desc):
        builder.TYPE(ParamType.STRING)
        builder.DEFAULTVALUE("")


def create_lift_param(builder: ParamBuilder, desc: str = "货叉高度"):
    """创建货叉高度参数"""
    with builder.CHILD(key="lift", name="Lift", desc=desc):
        builder.MIN_VALUE(ConfigParams.min_lift_height)
        builder.MAX_VALUE(ConfigParams.max_lift_height)
        builder.TYPE(ParamType.FLOAT)
        builder.UNIT("m")
        builder.DEFAULTVALUE(0)  # 1.1


def create_rotate_param(builder: ParamBuilder, desc: str = "旋转角度"):
    """创建货叉旋转角度参数"""
    with builder.CHILD(key="rotate", name="Rotate", desc=desc):
        builder.MIN_VALUE(-ConfigParams.max_rotate_angle)
        builder.MAX_VALUE(ConfigParams.max_rotate_angle)
        builder.TYPE(ParamType.DOUBLE)
        builder.UNIT("rad")
        builder.DEFAULTVALUE(0)  # -1.57


def create_stretch_param(builder: ParamBuilder, desc: str = "伸缩机构长度"):
    """创建伸缩机构长度参数"""
    with builder.CHILD(key="stretch", name="Stretch", desc=desc):
        builder.MIN_VALUE(0)
        builder.MAX_VALUE(ConfigParams.max_stretch_length)
        builder.TYPE(ParamType.FLOAT)
        builder.UNIT("m")
        builder.DEFAULTVALUE(0)


def create_vision_type_param(builder: ParamBuilder, desc: str = "识别类型"):
    """创建识别类型参数"""
    with builder.CHILD(key="visionType", name="visionType", desc=desc):
        builder.TYPE(ParamType.STRING)
        builder.DEFAULTVALUE("box")


def create_rec_adjust_param(builder: ParamBuilder, desc: str = "开启识别控制机器人位置"):
    """创建识别调整参数"""
    with builder.CHILD(key="recAdjust", name="Rec Adjust", desc=desc):
        builder.TYPE(ParamType.INT)
        builder.DEFAULTVALUE(1)


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        with builder.CHILD(key="finger", name="finger", desc="手指"):
            builder.TYPE(ParamType.INT)
            builder.REQUIRED(False)
            builder.DEFAULTVALUE(0)

        create_lift_param(builder)

        create_rotate_param(builder)

        create_stretch_param(builder)

        with builder.CHILD(key="modbus_ip", name="Modbus IP", desc="Modbus TCP IP"):
            builder.TYPE(ParamType.IP)
            builder.DEFAULTVALUE("192.168.192.6")

        with builder.GROUP(key="operation", name="Operation", desc="机构动作选项"):
            builder.TYPE(ParamType.COMBO_BOX)
            with builder.CHILDREN():
                with builder.CHILD(key="none", name="none", desc="空"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="rec_qrcode", name="Rec_Qrcode", desc="识别二维码"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_vision_type_param(builder, "识别类型: 'box' 或 'shelf'")
                        create_lift_param(builder, "识别时的货叉高度")
                        create_rotate_param(builder, "识别时的货叉角度")
                with builder.CHILD(key="zero", name="Zero", desc="机构回零"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="load", name="Load", desc="取货"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_vision_type_param(builder, "识别类型: 'box'或'shelf'，可缺省")
                        create_lift_param(builder, "取货前识别时的货叉高度")
                        create_rotate_param(builder, "取货前的货叉角度")
                        create_rec_adjust_param(builder, "开启识别时调整机器人位置")
                        create_stretch_param(builder, "取货时货叉伸出长度，缺省时根据识别结果自动计算")
                        create_container_param(builder, "车体背篓号，指定内部放货的背篓号，缺省时将按照从下往上依次放货")
                        create_goods_id_param(builder, "设置货物编号，缺省时为空字符串")
                with builder.CHILD(key="unload", name="Unload", desc="放货"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_vision_type_param(builder, "识别类型: 'shelf'")
                        create_lift_param(builder, "放货前识别时的货叉高度")
                        create_rec_adjust_param(builder, "开启识别时调整机器人位置")
                        create_rotate_param(builder, "放货前的货叉角度")
                        create_stretch_param(builder, "放货时货叉伸出长度，缺省时根据识别结果自动计算")
                        with builder.CHILD(key="recBoxLift", name="Rec Box Lift",
                                           desc="识别料箱码的高度，用于放货前先识别库位是否已经有货"):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(-1)
                        with builder.CHILD(key="pre_finger", name="Pre Finger",
                                           desc="放货时提前打开手指，解决推箱子后由于箱体表面不规则结构卡手指"):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(1)
                        create_container_param(builder, "车体背篓号，指定内部取货的背篓号，缺省时将按照从下往上依次取货")
                        create_goods_id_param(builder, "货物编号，指定要取货的货物编号，若车体背篓中无此goodsId，会报错")
                with builder.CHILD(key="rec_box_barcode", name="Rec_Box_Barcode", desc="识别料箱一维码"):
                    builder.TYPE(ParamType.ARRAY)
                    create_lift_param(builder, "识别前的货叉高度")
                    create_rotate_param(builder, "识别前的货叉角度")
                with builder.CHILD(key="take_photo", name="Take_Photo", desc="拍照"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_lift_param(builder, "拍照前的货叉高度")
                        create_rotate_param(builder, "拍照前的货叉角度")

                # in_take
                with builder.CHILD(key="in_take", name="In Take", desc="内部取货"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_container_param(builder, "车体背篓号，指定内部取货的背篓号，缺省时将按照从下往上依次取货")
                        create_goods_id_param(builder, "货物编号，指定要取货的货物编号，若车体背篓中无此goodsId，会报错")
                        create_rotate_param(builder,
                                            "内部取货后货叉停止的角度，可设置为下一个动作的目标角度，缺省时默认为0")
                        create_lift_param(builder,
                                          "内部取货后货叉停止的高度，可设置为下一个动作的目标高度，缺省时默认为0")

                with builder.CHILD(key="in_put", name="In_Put", desc="内部放货"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_container_param(builder, "车体背篓号，指定内部放货的背篓号，缺省时将按照从下往上依次放货")
                        create_goods_id_param(builder, "设置货物编号，缺省时为空字符串")

                with builder.CHILD(key="ex_take", name="Ex_Take", desc="外部取货"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_vision_type_param(builder, "识别类型: 'box'或'shelf' ")
                        create_lift_param(builder, "取货前识别时的货叉高度")
                        create_rec_adjust_param(builder, "开启识别时调整机器人位置")
                        create_rotate_param(builder, "取货前的货叉角度")
                        create_stretch_param(builder, "取货时的伸缩机构长度")

                with builder.CHILD(key="ex_put", name="Ex_Put", desc="外部放货"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_vision_type_param(builder, "识别类型: 'shelf'")
                        create_lift_param(builder, "放货前识别时的货叉高度")
                        create_rec_adjust_param(builder, "开启识别时调整机器人位置")
                        create_rotate_param(builder, "放货前的货叉角度")
                        create_stretch_param(builder, "放货时的伸缩机构长度")
    builder.save_to_file()


class MotorType(enum.IntEnum):
    LINEAR_MOTOR = 0
    ROLLER_MOTOR = 1


class MotorRun:
    def __init__(self, motor_type: MotorType, motor_name: str, stop_di: int = -1):
        self.motor_type = motor_type
        self.motor_name = motor_name
        self.stop_di = stop_di
        self.status = ScriptStatus.NONE
        self.state = dict()

    def run(self, vel=0., pos=0., max_vel=0.):
        """
        控制电机运转，辊筒电机需传参 vel，线性电机需传参 pos 和 max_vel
        :param vel: 辊筒电机转速
        :param pos: 线性电机目标位置
        :param max_vel: 线性电机最大转速
        :return:
        """
        self.status = ScriptStatus.RUNNING
        if self.motor_type == MotorType.LINEAR_MOTOR:
            Motor.setMotorPosition(self.motor_name, pos, max_vel, self.stop_di)
        elif self.motor_type == MotorType.ROLLER_MOTOR:
            Motor.setMotorSpeed(self.motor_name, vel, self.stop_di)
        else:
            log.error(f"motor type error {self.motor_type}")
            self.status = ScriptStatus.FAILED
        if Motor.isMotorReached(self.motor_name):
            Motor.resetMotor(self.motor_name)
            self.status = ScriptStatus.FINISHED
        self.state['motor_name'] = self.motor_name
        self.state['motor_type'] = self.motor_type
        self.state['motor_pos'] = Motor.get_motor_pos(self.motor_name)
        self.state['motor_speed'] = Motor.get_motor_speed(self.motor_name)
        self.state['motor_status'] = self.status

    def reset(self):
        log.info(f"motor reset: {self.motor_name}")
        Motor.resetMotor(self.motor_name)
        self.status = ScriptStatus.RUNNING

    def stop(self):
        Motor.isMotorStop(self.motor_name)
        self.status = ScriptStatus.NONE
        self.state['motor_status'] = self.status


class RobotRun:
    """
    实例化一个 AGV 对象，控制 AGV 移动和操作上层机构
    """

    def __init__(self):
        self.reach_angle = 0.01  # 路径导航的到点角度精度
        self.reach_dist = 0.003  # 路径导航的到点精度
        self.state = dict()  # 记录机器人状态
        self.init = True

    def lift(self, motor: MotorRun, height: float, max_vel=0.3) -> bool:
        """
        控制升降电机
        :param motor:
        :param height:
        :param max_vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == ScriptStatus.NONE:
            motor.reset()
        elif motor.status == ScriptStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == ScriptStatus.FAILED:
            return False
        else:
            motor.run(pos=float(height), max_vel=float(max_vel))
        return False

    def lift_door(self, motor: MotorRun, height: float, max_vel=0.3) -> bool:
        """
        料箱车门架电机
        :param motor:
        :param height:
        :param max_vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == ScriptStatus.NONE:
            motor.reset()
        elif motor.status == ScriptStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == ScriptStatus.FAILED:
            return False
        else:
            motor.run(pos=float(height), max_vel=float(max_vel))
        return False

    def stretch(self, motor: MotorRun, length: float, max_vel=0.3) -> bool:
        """
        控制伸缩机构电机
        :param motor:
        :param length:
        :param max_vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == ScriptStatus.NONE:
            motor.reset()
        elif motor.status == ScriptStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == ScriptStatus.FAILED:
            return False
        else:
            motor.run(pos=float(length), max_vel=float(max_vel))
        return False

    def rotate(self, motor: MotorRun, length: float, max_vel=0.3) -> bool:
        """
        控制旋转机构电机
        :param motor:
        :param length:
        :param max_vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == ScriptStatus.NONE:
            motor.reset()
        elif motor.status == ScriptStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == ScriptStatus.FAILED:
            return False
        else:
            motor.run(pos=float(length), max_vel=float(max_vel))
        return False

    def roller(self, motor: MotorRun, vel) -> bool:
        """
        控制辊筒电机
        :param motor:
        :param vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == ScriptStatus.NONE:
            motor.reset()
        elif motor.status == ScriptStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == ScriptStatus.FAILED:
            return False
        else:
            motor.run(vel=vel)
        return False

    def jack(self, motor: MotorRun, height: float, max_vel=0.3):
        """
        控制顶升电机
        :param motor:
        :param height:
        :param max_vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == ScriptStatus.NONE:
            motor.reset()
        elif motor.status == ScriptStatus.FINISHED:
            # motor.reset()   # 适配多电机顶升同步顶升
            return True
        elif motor.status == ScriptStatus.FAILED:
            return False
        else:
            motor.run(pos=height, max_vel=max_vel)
        return False

    def run_motor(self, motor: MotorRun, pos=0, vel=0.3, max_vel=0.3, reach_di=-1):
        """
        @param motor: Motor类实例对象
        @param pos: 位置模式下电机运动的目标位置
        @param vel: 速度模式下电机运动的目标速度
        @param max_vel: 电机运动的最大速度
        @param reach_di: 到位 DI
        @return: 电机运行到位返回True, 否则返回False
        """
        motor.stop_di = reach_di
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == ScriptStatus.NONE:
            motor.reset()
        elif motor.status == ScriptStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == ScriptStatus.FAILED:
            return False
        else:
            motor.run(vel=vel, pos=pos, max_vel=max_vel)
        return False


class ContainerRobot(ModuleBase):
    def __init__(self, args=None):
        super().__init__()
        self.check_safe_height = 0
        self.rec_box = None
        self.stretch_motor_stop = None
        self.rotate_motor_stop = None
        self.lift_motor_stop = None
        self.zeroing = None
        self.cur_c = None
        self.script_version = SCRIPT_VERSION

        self.ok_x = ConfigParams.ok_x
        self.ok_yaw = ConfigParams.ok_yaw

        self.args_init = False
        self.script_args = {}
        self.status = ScriptStatus.NONE
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
        self.count = 0

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
        self.container_robot = RobotRun()
        self.lift_motor = MotorRun(MotorType.LINEAR_MOTOR, ConfigParams.lift_motor_name, -1)
        self.stretch_motor = MotorRun(MotorType.LINEAR_MOTOR, ConfigParams.stretch_motor_name, -1)
        self.rotate_motor = MotorRun(MotorType.LINEAR_MOTOR, ConfigParams.rotate_motor_name, -1)
        self.load_step = [False] * 16
        self.unload_step = [False] * 16
        self.change_step = [False] * 10
        self.rec_box_lift_step = [False] * 5
        self.zero_step = [False] * 4
        self.calib_step = [False] * 3
        self.opt_step = [False] * 10
        self.yaw_adjust = 0
        self.rec_res = None
        self.rec_id = None
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

        self.box_code_file = None
        self.shelf_code_file = None

        self.lift_ok = False
        self.rotate_ok = False
        self.stretch_ok = False

        self.counter = 0
        log.info(f"init args: {args}")

    def init_script_args(self, args):
        self.script_args = args or Module.get_task_args()
        if args:
            self.goods_id = self.script_args.get("goodsId", "")
            self.self_position = self.script_args.get("container", self.self_position)
            self.self_position = str(self.self_position) if self.self_position is not None else self.self_position
            self.update_move_task_params()
            self.finger_pos = self.script_args.get("finger", 0)
            self.lift_height = self.script_args.get("lift", 0)
            self.door_height = self.script_args.get("lift-door", 0)
            self.stretch_length = self.script_args.get("stretch", 0)
            self.is_auto_stretch = bool("stretch" not in self.script_args)  # 输入参数无"stretch"，则自动计算识别长度
            self.rotate_pos = self.script_args.get("rotate", 0)
            self.offset_x = self.script_args.get("offset_x", ConfigParams.offset_x)
            self.pre_finger = self.script_args.get("pre_finger", self.pre_finger)
            if ConfigParams.rec_box_extra_height == 0:
                self.rec_box_lift = 0
            else:
                self.rec_box_lift = self.lift_height + ConfigParams.rec_box_extra_height
            self.rec_box_lift = self.script_args.get("recBoxLift", self.rec_box_lift)
            if self.rec_box_lift:
                self.rec_box = Rec(ConfigParams.box_code_file, max_rec_times=1)
            self.code_type = self.script_args.get("visionBinType", "code")
            self.target_type = self.script_args.get("visionType", None)
            self.barcode_height = self.script_args.get("barcodeHeight", None)
            self.operation = self.script_args.get("operation", None)
            self.load_height = self.script_args.get("loadHeight", ConfigParams.rec_offz_box)
            self.unload_height = self.script_args.get("unloadHeight", ConfigParams.rec_offz_shelf)
            container_num = RobotParam.getDevice("Model-000", "moduleType.cartonTransferUnit.id")
            # 如果container_num为数字且>0
            if isinstance(container_num, int) and container_num > 0:
                Container.init_container(container_num)
            self.containers = Container.getContainers()
            self.rec_id = uuid.uuid4().hex
            self.box_code_file = self.script_args.get("code_file", ConfigParams.box_code_file)
            self.shelf_code_file = self.script_args.get("shelf_code_file", ConfigParams.shelf_code_file)
            Abnormal.clear(53300)
            Abnormal.clear(53310)
            Abnormal.clear(53320)
            if "recAdjust" in self.script_args:
                if self.target_type is None:
                    if self.operation == "load" or self.operation == "ex_take":
                        self.rec_adjust = RecAdjust(self.box_code_file)
                    elif self.operation == "unload" or self.operation == "ex_put":
                        self.rec_adjust = RecAdjust(self.shelf_code_file)
                elif self.target_type == "box":
                    self.rec_adjust = RecAdjust(self.box_code_file)
                elif self.target_type == "shelf":
                    self.rec_adjust = RecAdjust(self.shelf_code_file)
            if self.target_type == "box" and self.code_type == "code":
                self.rec = Rec(self.box_code_file)
            elif self.target_type == "shelf" and self.code_type == "code":
                self.rec = Rec(self.shelf_code_file)

            # 根据货叉货物检测光电更新货叉有无货信息
            # if ConfigParams.goods_check_di != "":
            #     if self.stretch_real_pos < 0.05:  # 手臂未伸出状态下检测有效
            #         if Di.get_di(ConfigParams.goods_check_di) and not Container.has_goods("999"):
            #             Abnormal.setTask(53700, f"货叉光电检测到货叉中有货，但数据显示无货，需要人工核查处理", "", "", "")
            #             self.status = ScriptStatus.FAILED
            #         elif not Di.get_di(ConfigParams.goods_check_di):
            #             Container.clearContainer("999")
            # else:
            #     Abnormal.setTask(53701, f"请在脚本参数中正确配置 goods_check_di 参数！", "", "", "")
            #     log.error(f"请在脚本参数中正确配置 goods_check_di 参数！")
            #     self.status = ScriptStatus.FINISHED
            self.start_time = time.time()
            self.status = ScriptStatus.RUNNING

    def run(self):
        self.status = ScriptStatus.RUNNING
        self.counter += 1
        self.update_report_info()
        self.report_info["getCount_run"] = self.counter
        self.check_motor_emc()  # 检测控制器及驱动器急停状态
        if self.enable_motor and not self.motor_calib_state:  # 使能成功, 且未标零, 则标零
            self.motor_calib()

        if time.time() - self.start_time > ConfigParams.timeout:
            Abnormal.setTask(53702, f"脚本任务运行超时，请重新执行任务！", "", "", "")
            self.status = ScriptStatus.FAILED

        if self.motor_calib_state:
            if self.operation is not None and self.operation != 'none':
                if self.operation == "zero":
                    if self.zero():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "calib":
                    self.force_calib()
                elif self.operation == "zero_with_lift":
                    self.lift_height = min(self.lift_real_pos, self.lift_height)
                    if self.zero(self.lift_height):
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "load":
                    if self.load():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "unload":
                    if self.unload():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "rec_box_barcode":
                    self.rec_box_barcode()
                elif self.operation == "rec_qrcode":
                    self.rec_qrcode()
                elif self.operation == "take_photo":
                    self.take_photo()
                elif self.operation == "in_take":
                    if self.in_take():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "in_put":
                    if self.in_put():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "ex_take":
                    if self.ex_take():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "ex_put":
                    if self.ex_put():
                        self.status = ScriptStatus.FINISHED
                else:
                    Abnormal.setTask(53703, f"脚本输入参数错误!", "'operation'不合法", "检查任务参数'operation'",
                                     self.script_args)
                    self.status = ScriptStatus.FAILED
            else:
                if "finger" in self.script_args:
                    if self.finger(self.finger_pos):
                        self.update_finger_info()
                        self.status = ScriptStatus.FINISHED
                elif "lift" in self.script_args or "rotate" in self.script_args:
                    if "lift" in self.script_args and not self.lift_ok:
                        self.lift_ok = self.lift(self.lift_height)
                    else:
                        self.lift_ok = True
                    if "rotate" in self.script_args and not self.rotate_ok:
                        self.rotate_ok = self.rotate(self.rotate_pos)
                    else:
                        self.rotate_ok = True
                    if self.lift_ok and self.rotate_ok:
                        self.status = ScriptStatus.FINISHED
                elif "stretch" in self.script_args:
                    if self.stretch(self.stretch_length):
                        self.status = ScriptStatus.FINISHED
                elif "visionType" in self.script_args:
                    if self.code_type == "barcode":
                        if self.rec_barcode():
                            self.status = ScriptStatus.FINISHED
                    elif self.code_type == "code":
                        if self.rec_qrcode():
                            self.status = ScriptStatus.FINISHED
        self.update_report_info()
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
        self.report_info['goodsId'] = self.goods_id
        self.report_info['containers'] = self.containers
        self.report_info['motor_info'] = self.container_robot.state or -1
        if self.status == ScriptStatus.FAILED or self.status == ScriptStatus.FINISHED:
            # r.disableMotor(ConfigParams.lift_motor_name)
            NetProtocol.release()
            Do.setDO(ConfigParams.fill_light_do, False)
            log.info(f"script finished: {json.dumps(self.report_info)}")

        log.debug(self.report_info)

        return self.status

    @staticmethod
    def get_motor_info(motor_name: str):
        motor_data = Odometer.get_data().get("motorInfo", [])
        for _motor in motor_data:
            if _motor.get('motorName') == motor_name:
                return _motor
        return {}

    def check_motor_emc(self):
        """
        检测急停状态, 驱动器上使能
        """
        controller_emc = Controller.get_emc()
        lift_motor_info = self.get_motor_info(ConfigParams.lift_motor_name)  # 能查询到电机数据,说明驱动器已供电
        stretch_motor_info = self.get_motor_info(ConfigParams.stretch_motor_name)
        rotate_motor_info = self.get_motor_info(ConfigParams.rotate_motor_name)
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
            if Abnormal.getNum() == 0:
                if lift_motor_info and lift_motor_emc:  # 控制器未急停但是驱动器急停，给电机上使能
                    Motor.enableMotor(ConfigParams.lift_motor_name)
                    self.report_info['lift_motor_info'] = lift_motor_info
                if stretch_motor_info and stretch_motor_emc:
                    Motor.enableMotor(ConfigParams.stretch_motor_name)
                    self.report_info['stretch_motor_info'] = stretch_motor_info
                if rotate_motor_info and rotate_motor_emc:
                    Motor.enableMotor(ConfigParams.rotate_motor_name)
                    self.report_info['rotate_motor_info'] = rotate_motor_info

    def motor_calib(self):
        self.get_motor_calib_state()
        if not self.motor_calib_state:
            if not self.calib_step[0]:
                if not self.set_stretch_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    Motor.motorCalib(ConfigParams.stretch_motor_name)
                    self.set_stretch_motor_calib = True

            elif self.calib_step[0] and not self.calib_step[1]:
                if not self.set_lift_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    Motor.motorCalib(ConfigParams.lift_motor_name)
                    self.set_lift_motor_calib = True

            elif self.calib_step[1] and not self.calib_step[2]:
                if not self.set_rotate_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    Motor.motorCalib(ConfigParams.rotate_motor_name)
                    self.set_rotate_motor_calib = True

            if Abnormal.exists(54305):
                # 检测由车体抖动引起的标零失败，重置标志位，重新下发标零指令
                self.set_lift_motor_calib = False
                self.set_rotate_motor_calib = False
                self.set_stretch_motor_calib = False
                Abnormal.clear(54305)

            self.calib_step[0] = self.stretch_motor_calib
            self.calib_step[1] = self.lift_motor_calib
            self.calib_step[2] = self.rotate_motor_calib

    def get_motor_calib_state(self):
        odo_data = Odometer.get_data()
        if odo_data.get("motorInfo", None):
            motor_info = odo_data["motorInfo"]
            self.report_info["motorInfo"] = motor_info
            for m_f in motor_info:
                if m_f["motorName"] == ConfigParams.lift_motor_name:
                    self.lift_motor_calib = m_f.get("calib", None)
                    self.lift_motor_stop = m_f.get("stop", None)
                if m_f["motorName"] == ConfigParams.stretch_motor_name:
                    self.stretch_motor_calib = m_f.get("calib", None)
                    self.stretch_motor_stop = m_f.get("stop", None)
                if m_f["motorName"] == ConfigParams.rotate_motor_name:
                    self.rotate_motor_calib = m_f.get("calib", None)
                    self.rotate_motor_stop = m_f.get("stop", None)
        # self.motor_calib_state = (self.lift_motor_calib == "CALIBED" and self.stretch_motor_calib == "CALIBED" and self.rotate_motor_calib == "CALIBED")
        # print(self.motor_calib_state)
        self.motor_calib_state = True

    def force_calib(self):
        if Timer.delay(3):
            if not self.set_force_calib:
                self.set_force_calib = True
                Motor.motorCalib(ConfigParams.lift_motor_name)
                Motor.motorCalib(ConfigParams.stretch_motor_name)
                Motor.motorCalib(ConfigParams.rotate_motor_name)
                self.motor_calib_state = False
        if self.set_force_calib and self.motor_calib_state:
            self.status = ScriptStatus.FINISHED

    def suspend(self):
        if Module.get_status() == ScriptStatus.RUNNING:
            self.status = ScriptStatus.SUSPENDED

    def resume(self):
        if Module.get_status() == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING

    def cancel(self):
        Recognize.resetRec()
        self.close_finger()
        Do.setDO(ConfigParams.fill_light_do, False)
        self.status = ScriptStatus.FAILED
        log.info("carton cancel")

    def update_move_task_params(self):
        """
        获取moveTask参数
        """
        move_task = Navigation.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsId':
                self.goods_id = p['string_value']
            if p['key'] == '#containerName' and p['string_value'] != "":
                self.self_position = p['string_value']

    def zero(self, zero_height=0):
        """
        支持指定高度执行标零复位
        :param zero_height:
        :return:
        """
        log.info(f"----- running zero ------")
        if not self.zero_step[0]:
            # print(ConfigParams.left_finger_down_di)
            # print(ConfigParams.left_finger_up_di)
            self.zero_step[0] = Container.has_goods("999") or self.finger(1)
            # abc = Di.get_di(ConfigParams.left_finger_up_di)
            print(f"{self.zero_step[0]=}")
            # print(f"{abc=}")
        elif self.zero_step[0] and not self.zero_step[1]:
            self.zero_step[1] = self.stretch(0)
        elif self.zero_step[1] and not self.zero_step[2]:
            self.zero_step[2] = self.rotate(0)
            self.zero_step[3] = self.lift(zero_height)
        elif self.zero_step[2] and not self.zero_step[3]:
            self.zero_step[3] = self.lift(zero_height)
        log.debug(f"zero_step:{self.zero_step}")
        if all(self.zero_step):
            # r.release()
            Do.setDO(ConfigParams.finger_up_do, False)
            Container.clearContainer("999")
            return True
        return False

    def lift(self, height):
        log.info(f"----- running lift ------")
        if height < ConfigParams.min_lift_height:
            height = ConfigParams.min_lift_height
        if height > ConfigParams.max_lift_height:
            Abnormal.setTask(53704, f"下发升降高度超上限，最大值：{ConfigParams.max_lift_height}，下发值：{height}", "", "",
                             "")
            self.status = ScriptStatus.FAILED
            return False
        if self.stretch_real_pos > ConfigParams.safe_stretch_length:
            Abnormal.setTask(53705, f"检测到伸缩机构未回零，无法执行升降，请先执行标零复位！", "", "", "")
            self.status = ScriptStatus.FAILED
            return False
        if self.container_robot.lift(self.lift_motor, height, ConfigParams.lift_motor_speed):
            return True
        return False

    def finger(self, pos):
        log.info(f"----- running finger ------")
        if not self.finger_open_start:
            self.finger_open_start = time.time()
        else:
            if time.time() - self.finger_open_start > 3:  # 防止手指机构卡死时电机过流烧毁
                Abnormal.setTask(53706, f"拨指控制超时，请检查拨指是否卡住、检查拨指到位光电是否能正常触发！", "", "", "")
                Do.setDO(ConfigParams.finger_up_do, False)
                Do.setDO(ConfigParams.finger_down_do, False)
                self.status = ScriptStatus.FAILED
                return False
        if pos == 1:
            log.info(f"----- pose1 start ------")
            Do.setDO(ConfigParams.finger_up_do, True)

            if Di.get_di(ConfigParams.left_finger_up_di) and not Di.get_di(ConfigParams.left_finger_down_di):
                self.left_finger_real_pos = 1
                print(self.left_finger_real_pos)
            if Di.get_di(ConfigParams.right_finger_up_di) and not Di.get_di(ConfigParams.right_finger_down_di):
                self.right_finger_real_pos = 1
                print(self.right_finger_real_pos)
            log.info(f"----- pose1 end ------")
            if self.left_finger_real_pos == 1 and self.right_finger_real_pos == 1:
                self.finger_open_start = False

                return True

        elif pos == 0:
            if Di.get_di(ConfigParams.overlimit_detect_di):
                Abnormal.setTask(53707, f"伸出长度不够，货叉超限光电检测到障碍物！可上调取货伸出补偿参数值！", "", "", "")
                self.status = ScriptStatus.FAILED
                return False
            Do.setDO(ConfigParams.finger_down_do, True)
            if Di.get_di(ConfigParams.left_finger_down_di) and not Di.get_di(ConfigParams.left_finger_up_di):
                self.left_finger_real_pos = 0
            if Di.get_di(ConfigParams.right_finger_down_di) and not Di.get_di(ConfigParams.right_finger_up_di):
                self.right_finger_real_pos = 0
            if self.left_finger_real_pos == 0 and self.right_finger_real_pos == 0:
                self.finger_open_start = False
                Do.setDO(ConfigParams.finger_down_do, False)
                return True
        return False

    def close_finger(self):
        Do.setDO(ConfigParams.finger_up_do, False)
        Do.setDO(ConfigParams.finger_down_do, False)

    def update_finger_info(self):
        if Di.get_di(ConfigParams.left_finger_down_di) and not Di.get_di(ConfigParams.left_finger_up_di):
            self.left_finger_real_pos = 0
        elif Di.get_di(ConfigParams.left_finger_up_di) and not Di.get_di(ConfigParams.left_finger_down_di):
            self.left_finger_real_pos = 1
        if Di.get_di(ConfigParams.right_finger_down_di) and not Di.get_di(ConfigParams.right_finger_up_di):
            self.right_finger_real_pos = 0
        elif Di.get_di(ConfigParams.right_finger_up_di) and not Di.get_di(ConfigParams.right_finger_down_di):
            self.right_finger_real_pos = 1
        self.finger_info["left_finger"] = self.left_finger_real_pos
        self.finger_info["right_finger"] = self.right_finger_real_pos

    def stretch(self, length):
        log.info(f"----- running stretch ------")
        temp_motor_speed = ConfigParams.stretch_motor_speed
        if ConfigParams.max_stretch_length < length < ConfigParams.max_stretch_length + 0.1:
            Abnormal.setTask(53708,
                             f"下发伸出长度值略微超上限，下发值：{length}，上限值：{ConfigParams.max_stretch_length}。请检查货物是否离车体太远了！",
                             "", "", "")
            length = ConfigParams.max_stretch_length
        elif length > ConfigParams.max_stretch_length + 0.1:
            Abnormal.setTask(53708,
                             f"下发伸出长度值远超上限，下发值：{length}，上限值：{ConfigParams.max_stretch_length}。请检查货物是否离车体太远了！！！",
                             "", "", "")
            self.status = ScriptStatus.FAILED
            return False
        # 手臂伸出且目标位置大于0.1m, 后半段速度减半
        if length > 0.1 and self.stretch_real_pos > length * 0.6:
            temp_motor_speed = ConfigParams.stretch_motor_speed * 0.6
        if self.container_robot.stretch(self.stretch_motor, length, temp_motor_speed):
            return True
        return False

    def rotate(self, pos, max_speed=None):
        log.info(f"----- running rotate ------")
        if abs(pos) > abs(ConfigParams.max_rotate_angle / 180 * math.pi):
            Abnormal.setTask(53709,
                             f"下发角度值超上限，下发值：{pos / math.pi * 180}，上限值：{ConfigParams.max_rotate_angle}，请检查箱子是否摆歪，二维码是否破损！",
                             "", "", "")
            self.status = ScriptStatus.FAILED
            return False

        if self.stretch_real_pos > ConfigParams.safe_stretch_length:
            Abnormal.setTask(53710, f"检测到伸缩机构未回零，无法执行旋转动作，请先执行标零复位！", "", "", "")
            self.status = ScriptStatus.FAILED
            return False

        if max_speed is not None:
            speed = max_speed
        else:
            speed = ConfigParams.rotate_motor_speed

        if self.container_robot.rotate(self.rotate_motor, pos, speed):
            return True
        return False

    def rec_barcode(self):
        """
        识别一维码
        @param r:
        @return:
        """
        if not self.change_step[0]:
            Do.setDO(ConfigParams.fill_light_do, True)
            if Do.get_do(ConfigParams.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.change_step[0] = True
        else:
            if self.rec_res and self.rec_res.get("status", 1) == 0:
                Do.setDO(ConfigParams.fill_light_do, False)
                if self.rec_res['barCode'] != self.goods_id:
                    Abnormal.setTask(53711,
                                     f"货物编码不匹配, 任务下发的货物编码: {self.goods_id}, 识别的货物编码: {self.rec_res['barCode']}",
                                     "", "", "")
                    self.status = ScriptStatus.FAILED
                self.report_info["barcode"] = self.rec_res['barCode']
                return self.rec_res['barCode']
            else:
                if Timer.delay(0.05):
                    Recognize.doRec(ConfigParams.barcode_file, False, 0.0, 0.0, 0.0, 0.0)
                self.report_info["barcode"] = "None"
            self.report_info["rec_id"] = self.rec_id

    def rec_box_barcode(self):
        """
        指定货叉高度和角度位置识别一维码
        """
        if time.time() - self.start_time > 20:
            Abnormal.setTask(53712, f"未识别到一维码！请检查相机是否对准了一维码！", "", "", "")
            self.status = ScriptStatus.FAILED
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(self.rotate_pos)
        if self.opt_step[0] and self.opt_step[1] and not self.opt_step[2]:
            self.rec_barcode()
            if self.rec_res and self.rec_res.get("status", 1) == 0:
                self.report_info["barcode"] = self.rec_res['barCode']
                self.opt_step[2] = True
        if all(self.opt_step[0:3]):
            self.status = ScriptStatus.FINISHED

    def rec_qrcode(self):
        """
        指定货叉高度和角度位置识别二维码
        """
        if time.time() - self.start_time > 20:
            Abnormal.setTask(53713, f"未识别到二维码！请检查相机是否对准了二维码！", "", "", "")
            self.status = ScriptStatus.FAILED
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(self.rotate_pos)
        if all(self.opt_step[0:2]) and not self.opt_step[2]:
            Do.setDO(ConfigParams.fill_light_do, True)
            if Timer.delay(ConfigParams.light_delay_time):
                self.opt_step[2] = True
        if all(self.opt_step[0:3]) and not self.opt_step[3]:
            if self.rec.status == ScriptStatus.FINISHED:
                data = {
                    "containerRobot": {
                        "locName": self.script_args.get("locName", ""),
                        "taskId": self.script_args.get("taskId", ""),
                        "load": {
                            "lift": self.lift_real_pos + self.rec.result['z'] + ConfigParams.load_rec_lift_diff
                        },
                        "unload": {
                            "lift": self.lift_real_pos + self.rec.result['z']
                        }
                    }
                }
                NetProtocol.tcpUploadString(json.dumps(data))  # 将数据传递给 Roboshop
                self.report_info["rec_qrcode_data"] = data
                self.rec.reset()
                Do.setDO(ConfigParams.fill_light_do, False)
                self.opt_step[3] = True
            else:
                self.rec.run(self)

        if all(self.opt_step[0:4]):
            self.status = ScriptStatus.FINISHED

    def take_photo(self):
        """
        指定货叉高度和角度拍照
        @param r:
        @return:
        """
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(self.rotate_pos)

        if all(self.opt_step[0:2]) and not self.opt_step[2]:
            Do.setDO(ConfigParams.fill_light_do, True)
            Recognize.resetRec()  # 重置识别模块
            if Do.get_do(ConfigParams.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.opt_step[2] = True
        else:
            Recognize.doRec(ConfigParams.box_code_file, False, 0.0, 0.0, 0.0, 0.0)  # 下发拍照指令
            if Timer.delay(0.5):
                Do.setDO(ConfigParams.fill_light_do, False)
                self.status = ScriptStatus.FINISHED

    def load(self):
        log.info(f"----- running load  {self.goods_id}------")
        load_info = dict()
        if not self.cur_c:
            if (self.goods_id and Container.goods_id_exist(self.goods_id) and
                    Container.get_container_by_goodsId(self.goods_id) != "999"):
                Abnormal.setTask(53714, f"货物{self.goods_id}已存在，请检查是否重复下发任务！", "", "", "")
                self.status = ScriptStatus.FAILED
            if self.self_position:
                if Container.has_goods(self.self_position):
                    Abnormal.setTask(53715,
                                     f"第{self.self_position + 1}层({self.self_position}号)背篓已有货物，无法继续取货！请核对任务数据和背篓数据！",
                                     "",
                                     "", "")
                    self.status = ScriptStatus.FAILED
                self.cur_c = self.self_position
            else:
                self.cur_c = self.search_operable_container('load')
            log.info(f"load begin: {json.dumps(self.containers)}")
            if self.cur_c is None:  # 车体满载了
                Abnormal.setTask(53716, f"车体所有背篓已满，无法继续取货！", "", "", "")
                self.status = ScriptStatus.FAILED
                return
            if Container.has_goods("999") and Container.get_goodsId_by_container("999") == self.goods_id:
                self.load_step[:9] = [True] * 9
            elif Container.has_goods("999"):  # 货叉已载货,但不是目标货物
                Abnormal.setTask(53717, f"货叉（999号）已载货，无法执行取货任务！请核对任务数据和背篓数据！", "", "", "")
                self.status = ScriptStatus.FAILED
                return
        else:
            if not self.load_step[0]:
                self.load_step[0] = self.finger(1)
            if not self.load_step[1]:
                self.load_step[1] = self.rotate(self.rotate_pos)
            if not self.load_step[2]:
                self.load_step[2] = self.lift(self.lift_height)
            elif (self.load_step[0] and self.load_step[1] and self.load_step[2] and
                  not self.load_step[3]):
                if self.barcode_height is not None:
                    self.lift(self.barcode_height)
                    self.load_step[3] = self.goods_id == self.rec_barcode()
                else:
                    self.load_step[3] = True
            elif self.load_step[3] and not self.load_step[4]:
                if self.rec_adjust is not None:
                    if self.light_st_time is None:
                        Do.setDO(ConfigParams.fill_light_do, True)
                        self.light_st_time = time.time()
                    if time.time() - self.light_st_time > ConfigParams.light_delay_time:
                        if self.rec_adjust.status is ScriptStatus.FINISHED:
                            Do.setDO(ConfigParams.fill_light_do, False)
                            self.light_st_time = None
                            self.load_step[4] = True
                        elif self.rec_adjust.status is ScriptStatus.FAILED:
                            self.status = ScriptStatus.FAILED
                        else:
                            self.rec_adjust.run(self)
                else:
                    self.load_height = 0
                    self.load_step[4] = True
            elif self.load_step[4] and not self.load_step[5]:
                self.load_step[5] = self.lift(self.lift_height + self.load_height)
            elif self.load_step[5] and not self.load_step[6]:
                if Di.get_di(ConfigParams.left_finger_up_di) and Di.get_di(ConfigParams.right_finger_up_di):
                    self.load_step[6] = self.stretch(self.stretch_length)
                else:
                    Abnormal.setTask(53718, f"检测到拨指未打开，取消执行伸出动作！请检查拨指及其到位光电是否正常！", "",
                                     "", "")
                    self.status = ScriptStatus.FAILED
            elif self.load_step[6] and not self.load_step[7]:
                Do.setDO(ConfigParams.finger_up_do, False)
                self.load_step[7] = self.finger(0)
            elif self.load_step[7] and not self.load_step[8]:
                self.load_step[8] = self.stretch(0)
                if self.load_step[8] and Di.get_di(ConfigParams.goods_check_di):
                    # 手臂收回且光电检测成功时，增加货叉货物数据
                    Container.setContainer("999", self.goods_id, "")
            elif self.load_step[8] and (not self.load_step[9] or not self.load_step[10]):
                if not self.load_step[9]:
                    self.load_step[9] = self.rotate(0)
                if self.cur_c == "999":
                    self.load_step[:15] = [True] * 15
                else:
                    if not self.load_step[10]:
                        self.load_step[10] = self.lift(ConfigParams.high[int(self.cur_c)])
            elif self.load_step[9] and self.load_step[10] and not self.load_step[11]:
                self.load_step[11] = self.stretch(ConfigParams.stretch_self_length)
            elif self.load_step[11] and not self.load_step[12]:
                self.load_step[12] = self.finger(1)
            elif self.load_step[12] and not self.load_step[13]:
                self.load_step[13] = self.stretch(0)
            elif self.load_step[13] and not self.load_step[14]:
                Do.setDO(ConfigParams.finger_up_do, False)
                self.load_step[14] = self.finger(0)
            elif self.load_step[14] and not self.load_step[15]:
                self.load_step[15] = self.lift_safe_height()

            load_info['cur_container'] = self.cur_c
            load_info['goodsId'] = self.goods_id
            load_info['load_step'] = self.load_step
            load_info['lift-height'] = self.lift_height
            load_info['load-height'] = self.load_height
            load_info['lift-real-height'] = self.lift_real_pos
            self.report_info["load_info"] = load_info
            if all(self.load_step):
                # 在完成取货的所有动作后，增加背篓货物数据
                Container.clearContainer("999")
                Container.setContainer(self.cur_c, self.goods_id, "")
                return True

    def in_take(self):
        """
        内部取货： 从背篓取货到货叉
        """
        in_take_info = dict()
        if not self.cur_c:
            self.check_take()
        else:
            if self.cur_c == "999":
                self.status = ScriptStatus.FINISHED
            else:
                if not self.in_take_step[0]:
                    self.in_take_step[0] = self.finger(1)
                if not self.in_take_step[1]:
                    self.in_take_step[1] = self.lift(ConfigParams.low[int(self.cur_c)])
                if not self.in_take_step[2]:
                    self.in_take_step[2] = self.rotate(0)
                if all(self.in_take_step[0:3]) and not self.in_take_step[3]:
                    self.in_take_step[3] = self.stretch(ConfigParams.stretch_self_length)
                elif self.in_take_step[3] and not self.in_take_step[4]:
                    Do.setDO(ConfigParams.finger_up_do, False)
                    self.in_take_step[4] = self.finger(0)
                elif self.in_take_step[4] and not self.in_take_step[5]:
                    self.in_take_step[5] = self.stretch(0)
                elif self.in_take_step[5] and not self.in_take_step[6]:
                    self.in_take_step[6] = self.rotate(self.rotate_pos)
                if self.in_take_step[5] and not self.in_take_step[7]:
                    self.in_take_step[7] = self.lift(self.lift_height)

        in_take_info["in_take_step"] = self.in_take_step[:8]
        in_take_info["cur_container"] = self.cur_c
        in_take_info["goodsId"] = self.goods_id
        self.report_info["in_take_info"] = in_take_info
        if all(self.in_take_step[:8]):
            Container.clearContainer(self.cur_c)
            goods_id = Container.get_goodsId_by_container(self.cur_c)
            Container.setContainer("999", goods_id, "")
            return True

    def in_put(self):
        """
        内部放货： 从货叉放货到背篓
        """
        if not self.cur_c:
            self.check_put()
        else:
            if not self.in_put_step[0]:
                self.in_put_step[0] = self.lift(ConfigParams.high[int(self.cur_c)])
            if not self.in_put_step[1]:
                self.in_put_step[1] = self.rotate(0)
            if not self.in_put_step[2]:
                self.in_put_step[2] = True
            if all(self.in_put_step[0:3]) and not self.in_put_step[3]:
                self.in_put_step[3] = self.stretch(ConfigParams.stretch_self_length)
            if all(self.in_put_step[0:4]) and not self.in_put_step[4]:
                self.in_put_step[4] = self.finger(1)
            if all(self.in_put_step[0:5]) and not self.in_put_step[5]:
                self.in_put_step[5] = self.stretch(0)
            if all(self.in_put_step[0:6]) and not self.in_put_step[6]:
                Do.setDO(ConfigParams.finger_up_do, False)
                self.in_put_step[6] = self.finger(0)
            if all(self.in_put_step[0:7]) and not self.in_put_step[7]:
                self.in_put_step[7] = self.lift_safe_height()
        log.info(f"----- running in_put ------")
        in_put_info = dict()
        in_put_info["goodsId"] = self.goods_id
        in_put_info["in_put_step"] = self.in_put_step[:7]
        self.report_info["in_put_info"] = in_put_info
        if all(self.in_put_step[0:8]):
            goods_id = Container.get_goodsId_by_container("999")
            Container.setContainer(self.cur_c, goods_id, "")
            Container.clearContainer("999")
            return True

    def ex_take(self):
        """
        外部取货： 从货架取货到货叉
        """
        if Container.has_goods("999"):  # 抓斗有货
            Abnormal.setTask(53719, f"检测到货叉（999号）已载货，无法执行外部取货动作！请核对任务数据和背篓数据！", "", "",
                             "")
            self.status = ScriptStatus.FAILED
            return
        log.info(f"----- running ex_take ------")
        ex_take_info = dict()
        if self.barcode_height is not None:
            if not self.ex_take_step[0]:
                self.ex_take_step[0] = self.lift(self.barcode_height)
            if not self.ex_take_step[1]:
                self.ex_take_step[1] = self.rotate(self.rotate_pos)
            if all(self.ex_take_step[0:2]) and not self.ex_take_step[2]:
                self.ex_take_step[2] = self.goods_id == self.rec_barcode()
        else:
            self.ex_take_step[0] = True
            if not self.ex_take_step[1]:
                self.ex_take_step[1] = self.rotate(self.rotate_pos)
            self.ex_take_step[2] = True

        if self.rec_adjust is not None:
            if not self.change_step[0]:
                self.change_step[0] = self.lift(self.lift_height)
            if not self.change_step[1]:
                self.change_step[1] = self.rotate(self.rotate_pos)
            if all(self.change_step[0:2]) and not self.change_step[2]:
                Do.setDO(ConfigParams.fill_light_do, True)
                self.rec_adjust.status = ScriptStatus.RUNNING
                if Do.get_do(ConfigParams.fill_light_do):
                    if Timer.delay(ConfigParams.light_delay_time):
                        self.change_step[2] = True
            if self.change_step[2] and not self.ex_take_step[3]:
                if self.rec_adjust.status is ScriptStatus.FINISHED:
                    Do.setDO(ConfigParams.fill_light_do, False)
                    self.ex_take_step[3] = True
                elif self.rec_adjust.status is ScriptStatus.FAILED:
                    self.status = ScriptStatus.FAILED
                else:
                    self.rec_adjust.run(self)
        else:
            self.ex_take_step[3] = True

        if all(self.ex_take_step[0:4]) and not self.ex_take_step[4]:
            self.ex_take_step[4] = self.lift(self.lift_height + self.load_height)
            self.ex_take_step[5] = True
        if all(self.ex_take_step[0:6]) and not self.ex_take_step[6]:
            self.ex_take_step[6] = self.finger(1)
        if all(self.ex_take_step[0:7]) and not self.ex_take_step[7]:
            self.ex_take_step[7] = self.stretch(self.stretch_length)
        if all(self.ex_take_step[0:8]) and not self.ex_take_step[8]:
            Do.setDO(ConfigParams.finger_up_do, False)
            self.ex_take_step[8] = self.finger(0)
        if all(self.ex_take_step[0:9]) and not self.ex_take_step[9]:
            self.ex_take_step[9] = self.stretch(0)
        # if all(self.ex_take_step[0:10]) and not self.ex_take_step[10]:
        #     self.ex_take_step[10] = self.rotate(0)

        ex_take_info['goodsId'] = self.goods_id
        ex_take_info['cur_container'] = self.cur_c
        ex_take_info['ex_take_step'] = self.ex_take_step[:10]
        self.report_info["ex_take_info"] = ex_take_info
        if all(self.ex_take_step[:10]):
            Container.setContainer("999", self.goods_id, "")
            return True

    def ex_put(self):
        """
        外部放货： 从货叉放货到货架
        """
        log.info(f"----- running ex_put ------")
        if not Container.has_goods("999"):  # 抓斗没货
            return self.unload()

        ex_put_info = dict()
        if self.rec_box_lift:  # 识别货架是否有货
            if not self.ex_put_step[0]:
                self.ex_put_step[0] = self.lift(self.rec_box_lift)
            if not self.ex_put_step[1]:
                self.ex_put_step[1] = self.rotate(self.rotate_pos)
            if all(self.ex_put_step[0:2]) and not self.ex_put_step[2]:
                self.rec_box.status = ScriptStatus.RUNNING
                self.rec_box.is_error = True
                Do.setDO(ConfigParams.fill_light_do, True)
                if Do.get_do(ConfigParams.fill_light_do):
                    if Timer.delay(ConfigParams.light_delay_time):
                        self.ex_put_step[2] = True
            if all(self.ex_put_step[0:3]) and not self.ex_put_step[3]:
                if self.rec_box.status is ScriptStatus.FINISHED:
                    self.rec_box.reset()
                    self.rec_box.is_error = None
                    Do.setDO(ConfigParams.fill_light_do, False)
                    if self.rec_box.has_goods and not self.rec_box.goods_out_dist:
                        Abnormal.setTask(53720, "检测到货架上已经有货，取消放货动作！请人工核查货架和任务数据！", "", "",
                                         "")
                        self.status = ScriptStatus.FAILED
                        return
                    else:
                        self.ex_put_step[3] = True
                elif self.rec_box.status is ScriptStatus.FAILED:
                    Do.setDO(ConfigParams.fill_light_do, False)
                    self.ex_put_step[3] = True
                else:
                    self.rec_box.run(self)
        else:
            self.ex_put_step[0:4] = [True] * 4

        if all(self.ex_put_step[0:4]) and not self.ex_put_step[4]:
            self.ex_put_step[4] = self.lift(self.lift_height)
        if all(self.ex_put_step[0:4]) and not self.ex_put_step[5]:
            self.ex_put_step[5] = self.rotate(self.rotate_pos)
        if all(self.ex_put_step[0:6]) and not self.ex_put_step[6]:
            if self.rec_adjust is not None:
                if not self.change_step[0]:
                    Do.setDO(ConfigParams.fill_light_do, True)
                    self.rec_adjust.status = ScriptStatus.RUNNING
                    if Do.get_do(ConfigParams.fill_light_do):
                        if Timer.delay(ConfigParams.light_delay_time):
                            self.change_step[0] = True
                else:
                    if self.rec_adjust.status is ScriptStatus.FINISHED:
                        Do.setDO(ConfigParams.fill_light_do, False)
                        self.ex_put_step[6] = True
                    elif self.rec_adjust.status is ScriptStatus.FAILED:
                        self.status = ScriptStatus.FAILED
                    else:
                        self.rec_adjust.run(self)
            else:
                self.ex_put_step[6] = True
        if all(self.ex_put_step[0:7]) and not self.ex_put_step[7]:
            self.ex_put_step[7] = self.lift(self.lift_height + self.unload_height)
        if all(self.ex_put_step[0:8]) and not self.ex_put_step[8]:
            self.ex_put_step[8] = self.stretch(self.stretch_length)
        if all(self.ex_put_step[0:9]) and not self.ex_put_step[9]:
            self.ex_put_step[9] = self.finger(1)
        if all(self.ex_put_step[0:10]) and not self.ex_put_step[10]:
            self.ex_put_step[10] = self.stretch(0)
        if all(self.ex_put_step[0:11]) and not self.ex_put_step[11]:
            self.ex_put_step[11] = self.rotate(0)
        if all(self.ex_put_step[0:11]) and not self.ex_put_step[12]:
            if Do.setDO(ConfigParams.finger_up_do, False):
                self.ex_put_step[12] = self.finger(0)
        if all(self.ex_put_step[0:12]) and not self.ex_put_step[13]:
            self.ex_put_step[13] = self.lift_safe_height()

        ex_put_info["ex_put_info"] = self.ex_put_step[:13]
        ex_put_info["goodsId"] = self.goods_id
        self.report_info["ex_put_info"] = ex_put_info
        if all(self.ex_put_step[:14]):
            Container.clearContainer("999")
            return True

    def unload(self):
        log.info(f"----- running unload ------")
        unload_info = dict()

        if not self.cur_c:
            if self.self_position:
                if Container.get_goodsId_by_container(self.self_position) != self.goods_id:
                    Abnormal.setTask(53721,
                                     f"{self.self_position + 1}层({self.self_position}号)背篓中的货物Id与任务的货物ID({self.goods_id})不匹配！请核对任务数据和背篓数据！", )
                    self.status = ScriptStatus.FAILED
                if not Container.has_goods(self.self_position):
                    Abnormal.setTask(53722,
                                     f"{self.self_position + 1}层({self.self_position}号)背篓是空的，无法执行放货任务！请核对任务数据和背篓数据！",
                                     "", "", "")
                    self.status = ScriptStatus.FAILED
                if self.self_position != "999" and Container.has_goods("999"):
                    # r.setError(f"料斗已载货，无法执行背篓的放货任务！请核对任务数据和背篓数据！")
                    Abnormal.setTask(53723, f"货叉（999号）已载货，无法执行背篓的放货任务！请核对任务数据和背篓数据！", "",
                                     "", "")
                    self.status = ScriptStatus.FAILED
                self.cur_c = self.self_position
            else:
                if Container.has_goods("999"):  # 抓斗有货
                    self.cur_c = "999"
                    if Container.get_goodsId_by_container("999") != self.goods_id:
                        # r.setError(f"料斗已载货，无法先执行背篓的放货任务，必须优先释放料斗的货物！")
                        Abnormal.setTask(53724, f"货叉（999号）已载货，无法先执行背篓的放货任务，必须优先释放货叉的货物！",
                                         "", "",
                                         "")
                        self.status = ScriptStatus.FAILED
                        return
                else:
                    self.cur_c = Container.get_container_by_goodsId(self.goods_id)

            if not self.cur_c:
                Abnormal.setTask(53725, f"背篓中不存在货物: {self.goods_id}，无法执行放货任务！请核对任务数据和背篓数据！",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
                return
            log.info(f"unload begin: {json.dumps(self.containers)}")
        else:
            if self.cur_c == "999":
                self.unload_step[:6] = [True] * 6
            else:
                if not self.unload_step[0] or not self.unload_step[1] or not self.unload_step[2]:
                    if not self.unload_step[0]:
                        self.unload_step[0] = self.lift(ConfigParams.low[int(self.cur_c)])
                    if not self.unload_step[1]:
                        self.unload_step[1] = self.finger(1)
                    if not self.unload_step[2]:
                        self.unload_step[2] = self.rotate(0)
                elif self.unload_step[1] and self.unload_step[2] and not self.unload_step[3]:
                    self.unload_step[3] = self.stretch(ConfigParams.stretch_self_length)
                elif self.unload_step[3] and not self.unload_step[4]:
                    Do.setDO(ConfigParams.finger_up_do, False)
                    self.unload_step[4] = self.finger(0)
                elif self.unload_step[4] and not self.unload_step[5]:
                    if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                        if not self.unload_step[6]:
                            self.unload_step[6] = self.lift(self.lift_height)
                        if not self.unload_step[7]:
                            self.unload_step[7] = self.rotate(self.rotate_pos)
                    self.unload_step[5] = self.stretch(0)
                    if self.unload_step[5] and Di.get_di(ConfigParams.goods_check_di):
                        goods_id = Container.get_goodsId_by_container(self.cur_c)
                        Container.setContainer("999", goods_id, "")
                        Container.clearContainer(self.cur_c)

            if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                if self.rec_box_lift:
                    if not self.unload_step[6]:
                        if not self.rec_box_lift_step[0]:
                            self.rec_box_lift_step[0] = self.rotate(self.rotate_pos)
                        if not self.rec_box_lift_step[1]:
                            self.rec_box_lift_step[1] = self.lift(self.rec_box_lift)
                        if self.rec_box_lift_step[0] and self.rec_box_lift_step[1]:
                            self.unload_step[6] = True
                    if not self.unload_step[7] and self.unload_step[6]:
                        if self.rec_box is not None:
                            if not self.rec_box_lift_step[2]:
                                self.rec_box.status = ScriptStatus.RUNNING
                                self.rec_box.is_error = True
                                Do.setDO(ConfigParams.fill_light_do, True)
                                if Do.get_do(ConfigParams.fill_light_do):
                                    if Timer.delay(ConfigParams.light_delay_time):
                                        self.rec_box_lift_step[2] = True
                            if not self.rec_box_lift_step[3] and self.rec_box_lift_step[2]:
                                if self.rec_box.status is ScriptStatus.FINISHED:
                                    self.rec_box.reset()
                                    self.rec_box.is_error = None
                                    Do.setDO(ConfigParams.fill_light_do, False)
                                    self.rec_box_lift_step[3] = True
                                    # if self.rec_box.has_goods and not self.rec_box.goods_out_dist:
                                    #     Abnormal.setTask(53726, "检测到货架上有货，取消放货动作！", "", "", "")
                                    #     self.status = ScriptStatus.FAILED
                                    #     return
                                    # else:
                                    #     self.rec_box_lift_step[3] = True
                                elif self.rec_box.status is ScriptStatus.FAILED:
                                    Do.setDO(ConfigParams.fill_light_do, False)
                                    self.rec_box_lift_step[3] = True
                                else:
                                    self.rec_box.run(self)
                            if not self.rec_box_lift_step[4] and self.rec_box_lift_step[3]:
                                self.rec_box_lift_step[4] = self.lift(self.lift_height)
                            if self.rec_box_lift_step[4]:
                                self.unload_step[7] = True
                        else:
                            self.unload_step[7] = True
                else:
                    if not self.unload_step[6]:
                        self.unload_step[6] = self.lift(self.lift_height)
                    if not self.unload_step[7]:
                        self.unload_step[7] = self.rotate(self.rotate_pos)
            elif self.unload_step[7] and not self.unload_step[8]:
                if self.rec_adjust is not None:
                    if not self.change_step[0]:
                        Do.setDO(ConfigParams.fill_light_do, True)
                        self.rec_adjust.status = ScriptStatus.RUNNING
                        if Do.get_do(ConfigParams.fill_light_do):
                            if Timer.delay(ConfigParams.light_delay_time):
                                self.change_step[0] = True
                                print(self.change_step[0])
                    else:
                        if self.rec_adjust.status is ScriptStatus.FINISHED:
                            Do.setDO(ConfigParams.fill_light_do, False)
                            self.unload_step[8] = True
                        elif self.rec_adjust.status is ScriptStatus.FAILED:
                            self.status = ScriptStatus.FAILED
                        else:
                            self.rec_adjust.run(self)
                else:
                    self.unload_step[8] = True
            elif self.unload_step[8] and not self.unload_step[9]:
                self.unload_step[9] = self.lift(self.lift_height + self.unload_height)
            elif self.unload_step[9] and not self.unload_step[10]:
                if self.pre_finger is not None:
                    self.finger(self.pre_finger)
                self.unload_step[10] = self.stretch(self.stretch_length)
            elif self.unload_step[10] and not self.unload_step[11]:
                self.unload_step[11] = self.finger(1)
            elif self.unload_step[11] and not self.unload_step[12]:
                self.unload_step[12] = self.stretch(0)
            elif self.unload_step[12] and (not self.unload_step[13]
                                           or not self.unload_step[14]
                                           or not self.unload_step[15]):
                if not self.unload_step[13]:
                    Do.setDO(ConfigParams.finger_up_do, False)
                    self.unload_step[13] = self.finger(0)
                if not self.unload_step[14]:
                    self.unload_step[14] = self.rotate(0)
                if not self.unload_step[15]:
                    self.unload_step[15] = self.lift_safe_height()

            unload_info['unload_step'] = self.unload_step
            unload_info['cur_container'] = self.cur_c
            unload_info['goodsId'] = self.goods_id
            self.report_info["unload_info"] = unload_info

        if all(self.unload_step):
            # 在所有的动作完成后，将自身背篓的获取清除
            Container.clearContainer("999")
            return True

    def lift_safe_height(self):
        if self.lift_real_pos > ConfigParams.safe_lift_height:
            return self.lift(ConfigParams.safe_lift_height)
        return True

    def update_report_info(self):
        module_pos = dict()
        self.lift_real_pos = Motor.get_motor_pos(ConfigParams.lift_motor_name)
        self.stretch_real_pos = Motor.get_motor_pos(ConfigParams.stretch_motor_name)
        self.rotate_real_pos = Motor.get_motor_pos(ConfigParams.rotate_motor_name)
        self.update_finger_info()
        module_pos['lift'] = round(self.lift_real_pos, 3)
        module_pos['stretch'] = round(self.stretch_real_pos, 3)
        module_pos['rotate'] = round(self.rotate_real_pos * 180 / math.pi, 3)
        module_pos['left_finger'] = self.left_finger_real_pos
        module_pos['right_finger'] = self.right_finger_real_pos
        self.containers = Container.getContainers()
        self.report_info["current_pos"] = module_pos

    def has_goods_id(self, goods_id: str):
        log.info(f"goodsId: {goods_id}")
        for c in self.containers:
            if goods_id == c['goods_id']:
                return True
        return False

    def search_operable_container(self, opt):
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

    def check_put(self):
        """
        放货到背篓前，检查背篓有空位且货叉有货
        """
        if not Container.has_goods("999"):  # 货叉无货
            Abnormal.setTask(53727, f"货叉（999号）没有货物，无需内部放货！", "", "", "")
            self.status = ScriptStatus.FINISHED
            return

        # 货物在背篓里
        if self.goods_id and Container.goods_id_exist(self.goods_id):
            Abnormal.setTask(53728, f"货物已存在", "", "", "")
            self.status = ScriptStatus.FINISHED
            return

        if self.self_position:
            if Container.has_goods(self.self_position):
                Abnormal.setTask(53729, f"货物已在背篓中", "", "", "")
                self.status = ScriptStatus.FAILED
                return
            self.cur_c = self.self_position
        else:
            self.cur_c = self.search_operable_container('load')  # 查找空位

        if self.cur_c is None:  # 车体满载了
            Abnormal.setTask(53730, f"车体所有背篓已满，货叉（999号）载货中", "", "", "")
            self.status = ScriptStatus.FINISHED
            return

    def check_take(self):
        """
        从背篓取货前检测背篓货物信息，检查货叉为空
        """
        if self.self_position:
            if not Container.has_goods(self.self_position):
                Abnormal.setTask(53731,
                                 f"第{self.self_position + 1}层({self.self_position}号)背篓是空的，无法执行内部取货动作！",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
            self.cur_c = self.self_position
        else:
            self.cur_c = Container.get_container_by_goodsId(self.goods_id)

        if Container.has_goods("999"):  # 抓斗有货
            self.cur_c = "999"

        if not self.cur_c:
            Abnormal.setTask(53732, f"货物{self.goods_id}不存在，请核对货物编号和背篓数据！", "", "", "")
            self.status = ScriptStatus.FAILED
            return

    def safe_move_check(self):
        self.count += 1
        status = SafeMoveStatus.RUNNING
        if self.count == 100:
            self.count = 0
            status = SafeMoveStatus.FINISHED
        self.set_safe_move_status(status)
        Trace.log(f"safe_move_check {Module.get_safe_move_check()}")
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False

    def modbus(self):
        """
        从Modbus读取参数并解析
        """
        print("modbus___________ 读取Modbus数据")
        args = {}
        # 1. 读取操作码
        op_data = NetProtocol.getModbusData("4x", 201, 1)
        if op_data:
            operation_code = parse_modbus(op_data, 'uint16')
            print(f"   操作码: {operation_code}")
            # 根据操作码构建参数
            if operation_code == 1:
                args["operation"] = "load"
                # 读取高度参数
                height_data = NetProtocol.getModbusData("4x", 202, 2)
                if len(height_data) >= 2:
                    height = parse_modbus(height_data, 'float')
                    print(f"   读取高度参数寄存器值: [{height_data[0]}, {height_data[1]}]")
                    print(f"   解析后高度值: {height:.4f}m")
                    # 限制在有效范围内
                    args["height"] = max(0.0, min(0.06, height))
                    print(f"   设置高度: {args['height']:.4f}m")
            elif operation_code == 2:
                args["operation"] = "unload"
            elif operation_code == 3:
                args["operation"] = "spin"
                # 3. 读取浮点型参数
                print("读取浮点型参数:")
                # 读取角度参数
                angle_data = NetProtocol.getModbusData("4x", 202, 1)
                if angle_data:
                    angle_raw = parse_modbus(angle_data, 'int16')
                    args["spinAngle"] = angle_raw / 100.0  # 转换为度
                    print(f"   设置角度: {args['spinAngle']:.2f}度")
                else:
                    args["spinAngle"] = 90.0  # 默认角度
                    print("   使用默认角度")

            elif operation_code == 4:
                args["operation"] = "getCurrentPathProperty"
                # 4. 读取字符串参数
                print("读取字符串参数:")
                str_data = NetProtocol.getModbusData("4x", 202, 4)
                if str_data:
                    # 使用parse_modbus函数解析字符串
                    device_name = parse_modbus(str_data, 'string', 0, len(str_data))
                    if device_name:
                        args["device"] = device_name
                        print(f"   设备名称: {device_name}")

            print(f"   操作类型: {args.get('operation', 'unknown')}")
        return args


class Rec:
    def __init__(self, filename, is_error=None, max_rec_times=10):
        self.status = ScriptStatus.NONE
        self.is_error = is_error
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = max_rec_times
        self.result = dict()
        self.has_goods = None
        self.goods_out_dist = None
        self.max_goods_dist = 0.8  # 料箱距离货叉里程中心最远距离，单位：米

    def run(self, agv):
        self.status = ScriptStatus.RUNNING
        rec_status = Recognize.getRecStatus()  # 获取识别状态 0: 初始化, 1: 识别中, 2: 获得结果, 3：识别出错, -1: 未知错误
        if rec_status == 3 or rec_status == -1:  # 识别失败的状态
            log.info("rec failed:{}".format(self.result))
            if Timer.delay(0.05):
                self.rec_times = self.rec_times + 1
                if self.rec_times > self.max_rec_times:
                    if not self.is_error:
                        Abnormal.setTask(53733,
                                         f"连续识别{self.max_rec_times}次失败，请检查二维码是否损坏，请手动识别并查看照片是否清晰！",
                                         "", "", "")
                        self.status = ScriptStatus.FAILED
                    else:
                        self.status = ScriptStatus.FINISHED
                else:
                    Recognize.resetRec()

        elif rec_status == 2:  # 识别成功,获得结果
            rec_results = Recognize.getRecResults()
            if "reco_list" in rec_results:
                if len(rec_results["reco_list"]) == 1:
                    self.result = rec_results["reco_list"][0]
            if "resultImg" in self.result:
                self.result.pop("resultImg")
            Recognize.resetRec()
            self.has_goods = True
            if self.result["x"] > self.max_goods_dist:
                self.goods_out_dist = True
            self.status = ScriptStatus.FINISHED
            log.info(f"rec success: {self.status.name} {self.result}")
        else:
            log.info(f"--------------- doRec ----------------")
            Recognize.doRec(self.filename, False, 0.0, 0.0, 0.0, 0.0)

        cur_state = dict()
        cur_state['rec_result'] = self.result
        cur_state['rec_count'] = self.rec_times
        cur_state['rec_task_status'] = self.status
        cur_state['rec_status'] = rec_status
        cur_state['file'] = self.filename
        agv.report_info['rec_info'] = cur_state

    def reset(self):
        Recognize.resetRec()
        self.status = ScriptStatus.RUNNING


class RecAdjust:
    def __init__(self, filename):
        p = ParamServer(__file__)
        self.rotate_step = None
        self.lift_step = None
        self.status = ScriptStatus.NONE
        self.rec = Rec(filename)
        self.result = []
        self.max_rec_fail_times = 10
        self.max_adjust_time = 30
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.go_args = dict()
        self.ok = False

        self.next_rotate_pos = 1.5708  # 默认值
        self.diff_height = 0  # 识别高度差
        self.last_yaw_adjust = 1.5708
        self.plan_status = ScriptStatus.NONE
        self.goPath = GoPath()
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

    def run(self, agv: ContainerRobot):
        cur_state = dict()
        self.status = ScriptStatus.RUNNING
        if self.plan_status is not ScriptStatus.FINISHED:
            self.plan_status = ScriptStatus.RUNNING
            if self.rec.status is ScriptStatus.RUNNING or self.rec.status is ScriptStatus.NONE:
                log.info(f"----- rec to adjust {self.rec.status.name}------")
                self.rec.run(agv)
            elif self.rec.status is ScriptStatus.FAILED:
                self.rec_fail_time = self.rec_fail_time + 1
                random_dist = random.choice([1, -1]) * (1 / 180 * math.pi)
                agv.rotate(agv.rotate_real_pos + random_dist, max_speed=0.3)  # 识别失败时，货叉随机左右扭动 1° 继续识别
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.rec.reset()
                    self.rec.run(agv)
                else:
                    self.status = ScriptStatus.FAILED
                log.info("rec fail!!! {}".format(self.rec_fail_time))
            elif self.rec.status is ScriptStatus.FINISHED:
                log.info(f"------------------ move to adjust -----------------")
                self.rec_fail_time = 0
                # 通过参数配置，使识别结果为二维码在料斗坐标系下的坐标位置, (右手坐标系)x轴向前，y轴向左, z轴向上

                """获取结果"""
                # 计算手臂伸出长度
                if agv.is_auto_stretch:
                    if agv.operation == "load":
                        agv.stretch_length = (abs(self.rec.result['x']) - ConfigParams.auto_stretch_odo_len +
                                              ConfigParams.auto_load_stretch_dist + ConfigParams.auto_stretch_box_len)
                    elif agv.operation == "unload":
                        agv.stretch_length = (abs(self.rec.result['x']) - ConfigParams.auto_stretch_odo_len +
                                              ConfigParams.auto_unload_stretch_dist + ConfigParams.auto_stretch_box_len)

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
                if bool(ConfigParams.auto_adjust_rotate):
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

                if abs(agv.yaw_adjust) > ConfigParams.max_yaw_bias:
                    self.status = ScriptStatus.FAILED
                    Abnormal.setTask(53734,
                                     f"识别到角度偏差{agv.yaw_adjust}超出上限值{ConfigParams.max_yaw_bias}，请检查料箱是否摆正，二维码是否损坏！",
                                     "", "", "")
                else:
                    if self.adjust_count >= (self.max_adjust_time - 3):
                        agv.ok_x = 0.01
                        agv.ok_yaw = 0.02
                    # 精度满足, 识别调整任务完成
                    if not bool(ConfigParams.auto_adjust_rotate) and abs(self.rec.result['y']) < agv.ok_x:
                        log.info(f"adjust finished, adjust count: {self.adjust_count}")
                        self.status = ScriptStatus.FINISHED
                    elif bool(ConfigParams.auto_adjust_rotate) and abs(self.rec.result['y']) < agv.ok_x and abs(
                            agv.yaw_adjust) <= agv.ok_yaw:
                        log.info(f"adjust finished, adjust count: {self.adjust_count}")
                        self.status = ScriptStatus.FINISHED
                    else:
                        if self.adjust_count >= self.max_adjust_time:
                            self.status = ScriptStatus.FAILED
                            Abnormal.setTask(53735,
                                             f"识别调整{self.adjust_count}次未达到精度要求，请检查二维码是否损坏，相机画面是否清晰，精度参数是否设置合理！",
                                             "", "", "")
                self.plan_status = ScriptStatus.FINISHED
                self.rec.reset()
        elif self.status is not ScriptStatus.FINISHED and self.status is not ScriptStatus.FAILED:
            if self.goPath.status != ScriptStatus.FINISHED and self.goPath.status != ScriptStatus.FAILED:
                if abs(self.go_args['x']) < 0.003:  # 调整值小于底盘移动精度
                    self.goPath.status = ScriptStatus.FINISHED
                else:
                    if self.goPath.status != ScriptStatus.FINISHED and self.goPath.status != ScriptStatus.FAILED:
                        self.goPath.run(self.go_args)
            elif not self.rotate_step and self.goPath.status == ScriptStatus.FINISHED:
                if abs(agv.yaw_adjust) <= 0.01:  # 调整值小于货叉旋转精度
                    self.rotate_step = True
                if not self.rotate_step and bool(ConfigParams.auto_adjust_rotate):
                    self.rotate_step = agv.rotate(self.next_rotate_pos, max_speed=0.3)  # 货叉角度偏移修正
                else:
                    self.rotate_step = True
            elif self.goPath.status == ScriptStatus.FAILED:
                self.status = ScriptStatus.FAILED
            elif self.goPath.status == ScriptStatus.FINISHED and self.rotate_step:
                self.reset()
                self.adjust_count += 1
                self.last_yaw_adjust = agv.yaw_adjust
                self.plan_status = ScriptStatus.NONE
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
        log.debug(f"[ContainerRobot][{agv.lift_real_pos}|{agv.stretch_real_pos}|{agv.rotate_real_pos / math.pi * 180}|"
                  f"{self.rec.result.get('x', 0)}|{self.rec.result.get('y', 0)}|{self.rec.result.get('z', 0)}|{self.rec.result.get('yaw', 0)}|"
                  f"{agv.yaw_adjust / math.pi * 180}|{self.last_yaw_adjust / math.pi * 180}|{self.next_rotate_pos / math.pi * 180}|"
                  f"{self.rec_fail_time}|{self.adjust_count}|{self.rec.rec_times}|{self.go_args.get('x', 0)}|")

    def reset(self):
        self.rec.reset()
        self.status = ScriptStatus.RUNNING
        self.rec_fail_time = 0
        self.goPath.reset()


def main():
    Module.init()
    print("main")
    robot = ContainerRobot()
    validator = ParamValidator(InputParams.builder.to_dict())
    modbus_args = None

    while True:
        # 脚本任务状态管理
        status = robot.status
        Module.set_status(status)
        Module.report_info(robot.report_info)
        robot.report_info["status"] = status
        if robot.event_safe_move_check:
            robot.safe_move_check()
        if robot.event_modbus:
            modbus_args = robot.modbus()
            robot.event_modbus = False
        if status == ScriptStatus.NONE:
            args = modbus_args or Module.get_task_args()
            if args:
                try:
                    # 验证参数
                    args = validator.validate(args)
                    print("check ok, args:", json.dumps(args, indent=2))
                except ValueError as e:
                    print("check error:", e)
                robot.init_script_args(args)
        elif status == ScriptStatus.RUNNING:
            robot.run()
        elif status == ScriptStatus.SUSPENDED:
            robot.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            modbus_args = None
            robot.status = ScriptStatus.NONE

        time.sleep(0.1)


if __name__ == '__main__':
    main()

