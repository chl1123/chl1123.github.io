# -*- coding: utf-8 -*-
# @Date: 2026/6/8
# @Author: zhaopengfei
# @Version: v1.1
# @Project: SPK-MJ50-HL
# @Update:  add：脚本参数翻译补充  feat：1. 适配3.5日志统一记录格式  2. 手指电机控制部分重构
# @RBK Version: V3.5+
import enum
import uuid

SCRIPT_VERSION = "20260525"
import json
import math
import random
import time
from typing import List

from syspy.utils.time import Timer
from syspy import Module, Logger, Di, Do, Motor, Navigation, ScriptStatus, Controller, Odometer, Recognize, \
    RobotParam, Trace, _TR
from syspy.lib.net_protocol import parseModbus, NetProtocol
from syspy.bin import Container
from syspy.lib.module import SafeMoveStatus, ModuleBase
from syspy.lib.action_task import ActionBase, ActionStatus, ActionTask
from syspy.utils.param_server import ParamBuilder, ParamType, ScriptParam
from standard.goPath import GoPath

log = Logger("ContainerRobot")
script_param = ScriptParam(__file__)

# 业务通道名前缀（日志规范 <MOD>[.xxx]）
MOD = "ctu"

# ============================================================================
# Debug 日志辅助
# ============================================================================
from datetime import datetime


def _get_timestamp():
    """Get current timestamp in format: 2026-02-02 12:02:42,445"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S,") + f"{now.microsecond // 1000:03d}"


def debug_print(*args, **kwargs):
    """Print only when debug_mode is enabled (with timestamp)"""
    if ConfigParams.debug_mode:
        timestamp = _get_timestamp()
        print(f"{timestamp}", *args, **kwargs)


class ConfigParams:
    config = {}
    high = dict()
    low = dict()
    container_count = 0
    debug_mode = False

    # 手指 DoMotor（从设备模型 fingerMotor 克隆读取，._0=左手指, ._1=右手指）
    has_finger_motor: bool = False
    left_finger_motor_name: str = ""
    right_finger_motor_name: str = ""
    # 手指 DI（直接从 DoMotor 设备模型读取，如 DOMotor-XXX.basic.upReachDI）
    left_finger_up_di: str = ""
    left_finger_down_di: str = ""
    right_finger_up_di: str = ""
    right_finger_down_di: str = ""

    DEFAULT_TRAY_HEIGHTS = [
        (0.400, 0.410),  # 0
        (0.805, 0.815),  # 1
        (1.210, 1.220),  # 2
        (1.620, 1.630),  # 3
        (2.040, 2.045),  # 4
        (2.440, 2.445),  # 5
        (2.945, 2.955),  # 6
        (3.375, 3.385),  # 7
        (3.825, 3.835),  # 8
    ]

    @staticmethod
    def get_container_count():
        module_type = RobotParam.getDevice("Model-000", "moduleType")
        if not module_type:
            raise ValueError("读取设备模型失败: Model-000.moduleType 为空，请检查设备模型配置！")
        container_num = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.id")
        if not isinstance(container_num, int) or container_num <= 0:
            raise ValueError(
                f"读取背篓数量失败: moduleType.{module_type}.id = {container_num}，"
                f"请在设备模型中正确配置 cartonTransferUnit.id！"
            )
        return container_num

    @classmethod
    def read_device_model(cls):
        module_type = RobotParam.getDevice("Model-000", "moduleType")
        if not module_type:
            raise ValueError("读取设备模型失败: Model-000.moduleType 为空，请检查设备模型配置！")
        base = f"moduleType.{module_type}"

        cls.lift_motor_name = RobotParam.getDevice("Model-000", f"{base}.liftMotor")
        cls.rotate_motor_name = RobotParam.getDevice("Model-000", f"{base}.rotateMotor")
        cls.stretch_motor_name = RobotParam.getDevice("Model-000", f"{base}.reachMotor")
        if not cls.lift_motor_name or not cls.rotate_motor_name or not cls.stretch_motor_name:
            raise ValueError(
                f"读取电机名称失败: liftMotor={cls.lift_motor_name}, "
                f"rotateMotor={cls.rotate_motor_name}, stretchMotor={cls.stretch_motor_name}，"
                f"请在设备模型中正确配置！"
            )

        # 读取手指 DoMotor（逗号分隔字符串，第1个=左手指, 第2个=右手指）
        finger_motor = RobotParam.getDevice("Model-000", f"{base}.fingerMotor")
        if finger_motor and isinstance(finger_motor, str):
            motor_list = [x.strip() for x in finger_motor.split(",") if x.strip()]
            if len(motor_list) >= 2:
                cls.left_finger_motor_name = motor_list[0]
                cls.right_finger_motor_name = motor_list[1]
                cls.has_finger_motor = True
                cls.left_finger_up_di = RobotParam.getDevice(
                    f"{cls.left_finger_motor_name}", "basic.upReachDI") or ""
                cls.left_finger_down_di = RobotParam.getDevice(
                    f"{cls.left_finger_motor_name}", "basic.downReachDI") or ""
                cls.right_finger_up_di = RobotParam.getDevice(
                    f"{cls.right_finger_motor_name}", "basic.upReachDI") or ""
                cls.right_finger_down_di = RobotParam.getDevice(
                    f"{cls.right_finger_motor_name}", "basic.downReachDI") or ""
                Trace.log(
                    f"fingerMotor bindings: left={cls.left_finger_motor_name} (upDI={cls.left_finger_up_di}, downDI={cls.left_finger_down_di}), "
                    f"right={cls.right_finger_motor_name} (upDI={cls.right_finger_up_di}, downDI={cls.right_finger_down_di})",
                    name=f"{MOD}.cfg")
            else:
                cls.has_finger_motor = False
                cls.left_finger_motor_name = ""
                cls.right_finger_motor_name = ""
                Trace.log(
                    f"fingerMotor config incomplete: need 2 values, got {len(motor_list)}. "
                    f"Finger control disabled.", name=f"{MOD}.cfg")
        else:
            cls.has_finger_motor = False
            cls.left_finger_motor_name = ""
            cls.right_finger_motor_name = ""
            Trace.log(
                f"fingerMotor NOT configured at Model-000.{base}.fingerMotor. "
                f"Finger control disabled.", name=f"{MOD}.cfg")

    @classmethod
    def init(cls):
        cls.container_count = cls.get_container_count()
        cls.read_device_model()
        Trace.log(f"Container count from device model: {cls.container_count}", name=f"{MOD}.cfg")
        builder = script_param.builderConfig()

        with builder.GROUPS():
            # 通用配置组
            with builder.GROUP(key="generalConfig", name=_TR("General Configuration"),
                               desc=_TR("General configuration parameters")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="debugMode", name=_TR("Debug Mode"),
                                       desc=_TR("Enable debug mode to show debug tasks and low-frequency parameters")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

            # 背篓组
            with builder.GROUP(key="traysConfig", name=_TR("Trays Config"),
                               desc=_TR("Backpack layer height parameters, Counted from No. 0")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    for i in range(cls.container_count):
                        default_low = cls.DEFAULT_TRAY_HEIGHTS[i][0] if i < len(
                            cls.DEFAULT_TRAY_HEIGHTS) else 0.400 + i * 0.410
                        default_high = cls.DEFAULT_TRAY_HEIGHTS[i][1] if i < len(
                            cls.DEFAULT_TRAY_HEIGHTS) else default_low + 0.010
                        with builder.CHILD(key=f"low{i}", name=_TR(f"Low{i}"),
                                           desc=_TR(f"Height of the No. {i} Backboard Retrieval Box")):
                            builder.TYPE(ParamType.FLOAT)
                            builder.UNIT("m")
                            builder.DEFAULTVALUE(default_low)
                        with builder.CHILD(key=f"high{i}", name=_TR(f"High{i}"),
                                           desc=_TR(f"Height of the No. {i} Backbasket Material Box")):
                            builder.TYPE(ParamType.FLOAT)
                            builder.UNIT("m")
                            builder.DEFAULTVALUE(default_high)

            # 识别组
            with builder.GROUP(key="recognizeConfig", name=_TR("Recognize Config"),
                               desc=_TR("Recognition relevant parameters")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="recOffzBox", name=_TR("rec Offz Box"), desc=_TR("Adjust Height Twice for Pick")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(-0.030)
                    with builder.CHILD(key="recOffzShelf", name=_TR("Rec Offz Shelf"), desc=_TR("Adjust Height Twice for Place")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.030)
                    with builder.CHILD(key="boxCodeFile", name=_TR("Box Code File"), desc=_TR("Box Code Recognition Config")):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("default.srec")
                    with builder.CHILD(key="shelfCodeFile", name=_TR("Shelf Code File"),
                                       desc=_TR("Shelf Code Recognition Config")):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("default1.srec")
                    with builder.CHILD(key="barcodeFile", name=_TR("Barcode File"), desc=_TR("Barcode Recognition Config")):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("default2.srec")
                    with builder.CHILD(key="offsetX", name=_TR("Offset X"), desc=_TR("Walking Direction Offset")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.000)
                    with builder.CHILD(key="loadRecLiftDiff", name=_TR("Load Rec Lift Diff"),
                                       desc=_TR("Height difference from bin to shelf")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.050)
                    with builder.CHILD(key="recBoxExtraHeight", name=_TR("Rec Box Extra Height"),
                                       desc=_TR("Lift height for shelf stock detection")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.000)
                    with builder.CHILD(key="okX", name=_TR("Ok X"), desc=_TR("Walking Direction Recognition Threshold")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.01)
                    with builder.CHILD(key="okYaw", name=_TR("Ok Yaw"), desc=_TR("Adjustment Completion Threshold")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("deg")
                        builder.DEFAULTVALUE(0.86)
                    with builder.CHILD(key="maxYawBias", name=_TR("Max Yaw Bias"), desc=_TR("Max Fork Angle Offset (deg)")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("deg")
                        builder.DEFAULTVALUE(7.45)

            # 电机组
            with builder.GROUP(key="motorConfig", name=_TR("Motor Configuration"),
                               desc=_TR("Motor related configuration parameters")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="liftMotorSpeed", name=_TR("Lift Motor Speed"), desc=_TR("Speed of the lift motor")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.500)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)
                    with builder.CHILD(key="maxForkHeight", name=_TR("Max Lift Height"), desc=_TR("Maximum position for lift")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(4.500)
                        builder.UNIT("m")
                    with builder.CHILD(key="minForkHeight", name=_TR("Min Lift Height"), desc=_TR("Zero position for lift")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.380)
                        builder.UNIT("m")
                    with builder.CHILD(key="safeLiftHeight", name=_TR("Safe Lift Height"),
                                       desc=_TR("Safe position for lift, the highest height during forklift navigation")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.000)
                        builder.UNIT("m")
                with builder.CHILDREN():
                    with builder.CHILD(key="rotateMotorSpeed", name=_TR("Rotate Motor Speed"),
                                       desc=_TR("Speed of the rotate motor")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.000)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)
                    with builder.CHILD(key="maxRotateAngle", name=_TR("Max Rotate Angle"), desc=_TR("Maximum angle for rotate")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(100)
                        builder.UNIT("deg")
                    with builder.CHILD(key="autoAdjustRotate", name=_TR("Auto Adjust Rotate"),
                                       desc=_TR("The distance between the finger mechanism and the fork rotation center, Used for automatic calculation of fork extension length")):
                        builder.TYPE(ParamType.BOOL)
                with builder.CHILDREN():
                    with builder.CHILD(key="stretchMotorSpeed", name=_TR("Stretch Motor Speed"),
                                       desc=_TR("Speed of the stretch motor")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.000)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)
                    with builder.CHILD(key="maxStretchLength", name=_TR("Max Stretch Length"),
                                       desc=_TR("Maximum length of fork")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.900)
                        builder.UNIT("m")
                    with builder.CHILD(key="safeStretchLength", name=_TR("Safe Stretch Length"),
                                       desc=_TR("Safe length of telescopic arm during forklift lifting and rotating operations")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.900)
                        builder.UNIT("m")
                    with builder.CHILD(key="stretchSelfLength", name=_TR("Stretch Self Length"),
                                       desc=_TR("The length when picking up and placing goods in one's own backpack")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.760)
                        builder.UNIT("m")
                    with builder.CHILD(key="autoStretchBoxLen", name=_TR("Auto Stretch Box Len"),
                                       desc=_TR("The length of box, Used for automatic calculation of fork extension length")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.600)
                        builder.UNIT("m")
                    with builder.CHILD(key="autoLoadStretchDist", name=_TR("Auto Load Stretch Dist"),
                                       desc=_TR("The compensation value for the extended length of the pickup fork when picking up goods")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.010)
                        builder.UNIT("m")
                    with builder.CHILD(key="autoUnloadStretchDist", name=_TR("Auto Unload Stretch Dist"),
                                       desc=_TR("The compensation value for the extended length of the pickup fork when putting down goods")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.010)
                        builder.UNIT("m")
                    with builder.CHILD(key="autoStretchOdoLen", name=_TR("Auto Stretch Odo Len"),
                                       desc=_TR("The distance between the finger mechanism and the fork rotation center, Used for automatic calculation of fork extension length")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.380)
                        builder.UNIT("m")

            # 其他组
            with builder.GROUP(key="otherConfig", name=_TR("Other Configuration"), desc=_TR("Other configuration parameters")):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="timeout", name=_TR("Timeout"), desc=_TR("Execution Timeout")):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(120, min_value=0, max_value=300)
                    with builder.CHILD(key="goodsCheckDi", name=_TR("Goods Check Di"), desc=_TR("Fork Midpoint Detection DI")):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DI-008")
                        builder.REQUIRED(True)
                    with builder.CHILD(key="overlimitDetectDi", name=_TR("Overlimit Detect Di"),
                                       desc=_TR("Fork Safe Travel Limit")):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DI-009")
                        builder.REQUIRED(True)
                    with builder.CHILD(key="lightDelayTime", name=_TR("Light Delay Time"), desc=_TR("time for light")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3, min_value=0, max_value=100)
                        builder.REQUIRED(True)

        builder.save(merge=True)
        cls.load_config()

    @classmethod
    def load_config(cls):
        """重新加载配置参数"""
        cls.container_count = cls.get_container_count()
        cls.read_device_model()
        cls.config = script_param.loadConfig()
        Trace.log(f"Loaded config: {cls.config}", name=f"{MOD}.cfg")

        cls.debug_mode = cls.config.get("debugMode", False)
        cls.low.clear()
        cls.high.clear()
        for i in range(cls.container_count):
            cls.low[i] = cls.config.get(f"low{i}")
            cls.high[i] = cls.config.get(f"high{i}")

        cls.rec_offz_box = cls.config.get("recOffzBox")
        cls.rec_offz_shelf = cls.config.get("recOffzShelf")
        cls.box_code_file = cls.config.get("boxCodeFile")
        cls.shelf_code_file = cls.config.get("shelfCodeFile")
        cls.barcode_file = cls.config.get("barcodeFile")
        cls.offset_x = cls.config.get("offsetX")
        cls.load_rec_lift_diff = cls.config.get("loadRecLiftDiff")
        cls.rec_box_extra_height = cls.config.get("recBoxExtraHeight")
        cls.ok_x = cls.config.get("okX")
        cls.ok_yaw = cls.config.get("okYaw")
        cls.max_yaw_bias = cls.config.get("maxYawBias")

        cls.lift_motor_speed = cls.config.get("liftMotorSpeed")
        cls.max_lift_height = cls.config.get("maxForkHeight")
        cls.min_lift_height = cls.config.get("minForkHeight")
        cls.safe_lift_height = cls.config.get("safeLiftHeight")
        cls.rotate_motor_speed = cls.config.get("rotateMotorSpeed")
        cls.max_rotate_angle = cls.config.get("maxRotateAngle")
        cls.auto_adjust_rotate = cls.config.get("autoAdjustRotate")
        cls.stretch_motor_speed = cls.config.get("stretchMotorSpeed")
        cls.max_stretch_length = cls.config.get("maxStretchLength")
        cls.safe_stretch_length = cls.config.get("safeStretchLength")
        cls.stretch_self_length = cls.config.get("stretchSelfLength")
        cls.auto_stretch_box_len = cls.config.get("autoStretchBoxLen")
        cls.auto_load_stretch_dist = cls.config.get("autoLoadStretchDist")
        cls.auto_unload_stretch_dist = cls.config.get("autoUnloadStretchDist")
        cls.auto_stretch_odo_len = cls.config.get("autoStretchOdoLen")

        # 手指 DoMotor DI：直接从设备模型读取（如 DOMotor-XXX.basic.upReachDI）
        if cls.has_finger_motor and cls.left_finger_motor_name and cls.right_finger_motor_name:
            cls.left_finger_up_di = RobotParam.getDevice(
                f"{cls.left_finger_motor_name}", "basic.upReachDI") or ""
            cls.left_finger_down_di = RobotParam.getDevice(
                f"{cls.left_finger_motor_name}", "basic.downReachDI") or ""
            cls.right_finger_up_di = RobotParam.getDevice(
                f"{cls.right_finger_motor_name}", "basic.upReachDI") or ""
            cls.right_finger_down_di = RobotParam.getDevice(
                f"{cls.right_finger_motor_name}", "basic.downReachDI") or ""

        cls.timeout = cls.config.get("timeout")
        cls.goods_check_di = cls.config.get("goodsCheckDi")
        cls.overlimit_detect_di = cls.config.get("overlimitDetectDi")
        cls.light_delay_time = cls.config.get("lightDelayTime")


'''参数创建必须在全局作用域中'''
ConfigParams.init()


def script_config_callback():
    """脚本配置参数修改回调，脚本配置修改时会调用"""
    Trace.log("Reloading script config parameters", name=f"{MOD}.cfg")
    ConfigParams.load_config()


def robot_device_callback(change_devices: List[str]):
    """机器人设备参数修改回调，设备参数修改时会调用"""
    Trace.log(f"{change_devices=}", name=f"{MOD}.cfg")
    relevant_devices = {"Model", "Motor", "DOMotor", "CodeScanner"}
    if set(change_devices) & relevant_devices:
        ConfigParams.load_config()


# ============================================================================
# 调试任务列表（需要开启 debugMode 才能执行）
# ============================================================================
DEBUG_ONLY_TASKS = [
    "none",
    "recQrcode",
    "recBoxBarcode",
    "takePhoto",
]


def check_debug_task(operation: str) -> bool:
    if operation in DEBUG_ONLY_TASKS:
        if not ConfigParams.debug_mode:
            Trace.log(
                f"[ERROR] Task '{operation}' is a debug-only task. "
                f"Please enable 'debugMode' in script config first.", name=f"{MOD}.err")
            return False
    return True


# ============================================================================
# 可复用参数创建辅助函数
# ============================================================================
def create_container_param(builder: ParamBuilder, desc: str = _TR("Vehicle basket number")):
    with builder.CHILD(key="container", name=_TR("Container"), desc=desc):
        builder.MIN_VALUE(0)
        builder.MAX_VALUE(999)
        builder.TYPE(ParamType.INT)
        builder.DEFAULTVALUE(0)


def create_goods_id_param(builder: ParamBuilder, desc: str = _TR("Goods number")):
    with builder.CHILD(key="goodsName", name=_TR("Goods Name"), desc=desc):
        builder.TYPE(ParamType.STRING)
        builder.DEFAULTVALUE("")


def create_lift_param(builder: ParamBuilder, desc: str = _TR("Fork height")):
    with builder.CHILD(key="lift", name=_TR("Lift"), desc=desc):
        builder.MIN_VALUE(ConfigParams.min_lift_height)
        builder.MAX_VALUE(ConfigParams.max_lift_height)
        builder.TYPE(ParamType.FLOAT)
        builder.UNIT("m")
        builder.DEFAULTVALUE(0)


def create_rotate_param(builder: ParamBuilder, desc: str = _TR("Rotation angle")):
    with builder.CHILD(key="rotate", name=_TR("Rotate"), desc=desc):
        builder.MIN_VALUE(-ConfigParams.max_rotate_angle)
        builder.MAX_VALUE(ConfigParams.max_rotate_angle)
        builder.TYPE(ParamType.DOUBLE)
        builder.UNIT("deg")
        builder.DEFAULTVALUE(0)


def create_stretch_param(builder: ParamBuilder, desc: str = _TR("Telescopic mechanism length")):
    with builder.CHILD(key="stretch", name=_TR("Stretch"), desc=desc):
        builder.MIN_VALUE(0)
        builder.MAX_VALUE(ConfigParams.max_stretch_length)
        builder.TYPE(ParamType.FLOAT)
        builder.UNIT("m")
        builder.DEFAULTVALUE(0)


def create_vision_type_param(builder: ParamBuilder, desc: str = _TR("Vision type")):
    with builder.CHILD(key="visionType", name=_TR("visionType"), desc=desc):
        builder.TYPE(ParamType.STRING)
        builder.DEFAULTVALUE("box")


def create_rec_adjust_param(builder: ParamBuilder, desc: str = _TR("Enable recognition to control robot position")):
    with builder.CHILD(key="recAdjust", name=_TR("Rec Adjust"), desc=desc):
        builder.TYPE(ParamType.INT)
        builder.DEFAULTVALUE(1)


'''参数创建必须在全局作用域中'''


class InputParams:
    """脚本任务输入参数定义（参数创建必须放到全局作用域中）"""
    builder = script_param.builderInput()

    with builder.GROUPS():
        with builder.CHILD(key="finger", name=_TR("finger"), desc=_TR("Finger")):
            builder.TYPE(ParamType.INT)
            builder.REQUIRED(False)
            builder.DEFAULTVALUE(0)

        create_lift_param(builder)
        create_rotate_param(builder)
        create_stretch_param(builder)

        with builder.CHILD(key="modbusIp", name=_TR("Modbus IP"), desc=_TR("Modbus TCP IP")):
            builder.TYPE(ParamType.IP)
            builder.DEFAULTVALUE("192.168.192.6")

        with builder.GROUP(key="operation", name=_TR("Operation"), desc=_TR("Mechanism action options")):
            builder.TYPE(ParamType.COMBO_BOX)
            with builder.CHILDREN():
                with builder.CHILD(key="zero", name=_TR("Zero"), desc=_TR("Mechanism homing")):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="load", name=_TR("Load"), desc=_TR("Pick up goods")):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_vision_type_param(builder, _TR("Vision type: 'box' or 'shelf', optional"))
                        create_lift_param(builder, _TR("Fork height for recognition before picking"))
                        create_rotate_param(builder, _TR("Fork angle before picking"))
                        create_rec_adjust_param(builder, _TR("Adjust robot position when recognition is enabled"))
                        create_stretch_param(builder, _TR("Fork extension length when picking; auto-calculated from the recognition result if omitted"))
                        create_container_param(builder, _TR("Vehicle basket number; specifies the basket for internal put; if omitted, put in order from bottom to top"))
                        create_goods_id_param(builder, _TR("Set the goods number; empty string if omitted"))
                with builder.CHILD(key="unload", name=_TR("Unload"), desc=_TR("Put down goods")):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_vision_type_param(builder, _TR("Vision type: 'shelf'"))
                        create_lift_param(builder, _TR("Fork height for recognition before putting"))
                        create_rec_adjust_param(builder, _TR("Adjust robot position when recognition is enabled"))
                        create_rotate_param(builder, _TR("Fork angle before putting"))
                        create_stretch_param(builder, _TR("Fork extension length when putting; auto-calculated from the recognition result if omitted"))
                        with builder.CHILD(key="recBoxLift", name=_TR("Rec Box Lift"),
                                           desc=_TR("Lift height for scanning the box code, used to check whether the slot already has goods before unloading")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(-1)
                        with builder.CHILD(key="preFinger", name=_TR("Pre Finger"),
                                           desc=_TR("Open the fingers in advance when unloading, to prevent the fingers from getting stuck on the irregular box surface after pushing the box")):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(1)
                        create_container_param(builder, _TR("Vehicle basket number; specifies the basket for internal pick; if omitted, pick in order from bottom to top"))
                        create_goods_id_param(builder, _TR("Goods number; specifies the goods to pick; an error is raised if no such goodsName exists in the vehicle basket"))

                # 调试/低频任务（需要开启 debugMode 才显示）
                if ConfigParams.debug_mode:
                    with builder.CHILD(key="none", name=_TR("[Debug] none"), desc=_TR("Empty")):
                        builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="recQrcode", name=_TR("[Debug] Rec_Qrcode"), desc=_TR("Recognize QR code")):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_vision_type_param(builder, _TR("Vision type: 'box' or 'shelf'"))
                            create_lift_param(builder, _TR("Fork height during recognition"))
                            create_rotate_param(builder, _TR("Fork angle during recognition"))

                    with builder.CHILD(key="recBoxBarcode", name=_TR("Rec_Box_Barcode"), desc=_TR("Recognize box barcode")):
                        builder.TYPE(ParamType.ARRAY)
                        create_lift_param(builder, _TR("Fork height before recognition"))
                        create_rotate_param(builder, _TR("Fork angle before recognition"))

                    with builder.CHILD(key="takePhoto", name=_TR("Take_Photo"), desc=_TR("Take photo")):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_lift_param(builder, _TR("Fork height before taking photo"))
                            create_rotate_param(builder, _TR("Fork angle before taking photo"))

                    with builder.CHILD(key="inTake", name=_TR("In Take"), desc=_TR("Internal pick")):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_container_param(builder,
                                                   _TR("Vehicle basket number; specifies the basket for internal pick; if omitted, pick in order from bottom to top"))
                            create_goods_id_param(builder,
                                                  _TR("Goods number; specifies the goods to pick; an error is raised if no such goodsName exists in the vehicle basket"))
                            create_rotate_param(builder,
                                                _TR("Fork stop angle after internal pick; can be set to the target angle of the next action; defaults to 0 if omitted"))
                            create_lift_param(builder,
                                              _TR("Fork stop height after internal pick; can be set to the target height of the next action; defaults to 0 if omitted"))

                    with builder.CHILD(key="inPut", name=_TR("In_Put"), desc=_TR("Internal put")):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_container_param(builder,
                                                   _TR("Vehicle basket number; specifies the basket for internal put; if omitted, put in order from bottom to top"))
                            create_goods_id_param(builder, _TR("Set the goods number; empty string if omitted"))

                    with builder.CHILD(key="exTake", name=_TR("Ex_Take"), desc=_TR("External pick")):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_vision_type_param(builder, _TR("Vision type: 'box' or 'shelf'"))
                            create_lift_param(builder, _TR("Fork height for recognition before picking"))
                            create_rec_adjust_param(builder, _TR("Adjust robot position when recognition is enabled"))
                            create_rotate_param(builder, _TR("Fork angle before picking"))
                            create_stretch_param(builder, _TR("Telescopic mechanism length when picking"))

                    with builder.CHILD(key="exPut", name=_TR("Ex_Put"), desc=_TR("External put")):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_vision_type_param(builder, _TR("Vision type: 'shelf'"))
                            create_lift_param(builder, _TR("Fork height for recognition before putting"))
                            create_rec_adjust_param(builder, _TR("Adjust robot position when recognition is enabled"))
                            create_rotate_param(builder, _TR("Fork angle before putting"))
                            create_stretch_param(builder, _TR("Telescopic mechanism length when putting"))

    # 保存脚本任务输入参数
    builder.save()


# ============================================================================
# 脚本内置动作模板定义
# ============================================================================
script_param.addAction(
    action_name="zero",
    policy=None,
    args={"operation": "zero"},
    config={}
)

script_param.addAction(
    action_name="calib",
    policy=None,
    args={"operation": "calib"},
    config={}
)

script_param.addAction(
    action_name="load",
    policy=None,
    args={
        "operation": "load",
        "operation.load.visionType": "box",
        "operation.load.lift": 0.0,
        "operation.load.rotate": 0,
        "operation.load.recAdjust": 1,
        "operation.load.stretch": 0.0,
        "operation.load.container": 0,
        "operation.load.goodsName": "",
    },
    config={}
)

script_param.addAction(
    action_name="unload",
    policy=None,
    args={
        "operation": "unload",
        "operation.unload.visionType": "shelf",
        "operation.unload.lift": 0.0,
        "operation.unload.recAdjust": 1,
        "operation.unload.rotate": 0,
        "operation.unload.stretch": 0.0,
        "operation.unload.recBoxLift": -1,
        "operation.unload.preFinger": 1,
        "operation.unload.container": 0,
        "operation.unload.goodsName": "",
    },
    config={}
)

script_param.saveAction()


# ============================================================================
# Action 状态机基础设施
# ============================================================================
class BaseAction(ActionBase):
    """ctu 桥接基类:继承框架 ActionBase, 保留 ctu 原有 start_time/action_state 约定。
    run(self, m) 的 ctx 参数 m 仅为满足 ActionTask.step(ctx) 调用, 子类用 self.agv。"""

    def __init__(self, action_name: str = None):
        super().__init__(action_name)
        self.start_time = time.time()
        self.action_state = {}

    def run(self, m):
        self.action_state["action_runtime"] = time.time() - self.start_time
        self.action_state["action_name"] = self.action_name

    def reset(self):
        super().reset()
        self.start_time = time.time()


class ParallelAction(BaseAction):
    def __init__(self, actions, action_name="Parallel"):
        super().__init__(action_name)
        self.actions = actions

    def run(self, m):
        super().run(m)
        all_finished = True
        for action in self.actions:
            if action.action_status == ActionStatus.FAILED:
                self.action_status = ActionStatus.FAILED
                return
            elif action.action_status == ActionStatus.INIT:
                action.reset()
                all_finished = False
            elif action.action_status != ActionStatus.FINISHED:
                action.run(m)
                all_finished = False
        if all_finished:
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        for action in self.actions:
            action.action_status = ActionStatus.INIT

    def cancel(self):
        super().cancel()
        for action in self.actions:
            action.cancel()


# ============================================================================
# 电机控制辅助类
# ============================================================================
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
        self.status = ScriptStatus.RUNNING
        if self.motor_type == MotorType.LINEAR_MOTOR:
            Motor.setMotorPosition(self.motor_name, pos, max_vel)
        elif self.motor_type == MotorType.ROLLER_MOTOR:
            Motor.setMotorSpeed(self.motor_name, vel)
        else:
            Trace.log(f"motor type error {self.motor_type}", name=f"{MOD}.err")
            self.status = ScriptStatus.FAILED
        if Motor.isMotorReached(self.motor_name):
            Motor.resetMotor(self.motor_name)
            self.status = ScriptStatus.FINISHED
        self.state['motorName'] = self.motor_name
        self.state['motorType'] = self.motor_type
        self.state['motorPos'] = Motor.getMotorPos(self.motor_name)
        self.state['motorSpeed'] = Motor.getMotorSpeed(self.motor_name)
        self.state['motorStatus'] = self.status

    def reset(self):
        Trace.log(f"motor reset: {self.motor_name}", name=f"{MOD}.motor")
        Motor.resetMotor(self.motor_name)
        self.status = ScriptStatus.RUNNING

    def stop(self):
        Motor.isMotorStop(self.motor_name)
        self.status = ScriptStatus.NONE
        self.state['motorStatus'] = self.status


class RobotRun:
    def __init__(self):
        self.reach_angle = 0.01
        self.reach_dist = 0.003
        self.state = dict()
        self.init = True

    def lift(self, motor: MotorRun, height: float, max_vel=0.3) -> bool:
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


# ============================================================================
# 电机级别 Action 类
# ============================================================================
class LiftAction(BaseAction):
    def __init__(self, agv, height, action_name="Lift"):
        super().__init__(action_name)
        self.agv = agv
        self.height = height

    def run(self, m):
        super().run(m)
        if self.height < ConfigParams.min_lift_height:
            self.height = ConfigParams.min_lift_height
        if self.height > ConfigParams.max_lift_height:
            Navigation.setTaskError("LiftHeightExceeded", f"Lift height exceeds upper limit, max: {ConfigParams.max_lift_height}, commanded: {self.height}")
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.stretch_real_pos > ConfigParams.safe_stretch_length:
            Navigation.setTaskError("StretchNotZeroed", f"Stretch mechanism not zeroed, cannot perform lift/rotate. Please zero first")
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.container_robot.lift(self.agv.lift_motor, self.height, ConfigParams.lift_motor_speed):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        self.agv.lift_motor.reset()


class LiftSafeAction(BaseAction):
    def __init__(self, agv, action_name="LiftSafe"):
        super().__init__(action_name)
        self.agv = agv

    def run(self, m):
        super().run(m)
        if self.agv.lift_real_pos <= ConfigParams.safe_lift_height:
            self.action_status = ActionStatus.FINISHED
            return
        if self.agv.container_robot.lift(self.agv.lift_motor, ConfigParams.safe_lift_height, ConfigParams.lift_motor_speed):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        if self.agv.lift_real_pos <= ConfigParams.safe_lift_height:
            self.action_status = ActionStatus.FINISHED
        else:
            self.agv.lift_motor.reset()


class RotateAction(BaseAction):
    def __init__(self, agv, pos, max_speed=None, action_name="Rotate"):
        super().__init__(action_name)
        self.agv = agv
        self.pos = pos
        self.max_speed = max_speed

    def run(self, m):
        super().run(m)
        if abs(self.pos) > abs(ConfigParams.max_rotate_angle / 180 * math.pi):
            Navigation.setTaskError("RotateAngleExceeded", f"Rotate angle {self.pos / math.pi * 180} exceeds upper limit {ConfigParams.max_rotate_angle}. Check if box is tilted or QR code is damaged")
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.stretch_real_pos > ConfigParams.safe_stretch_length:
            Navigation.setTaskError("StretchNotZeroed",f"Stretch mechanism not zeroed, cannot perform lift/rotate. Please zero first")
            self.action_status = ActionStatus.FAILED
            return
        speed = self.max_speed if self.max_speed is not None else ConfigParams.rotate_motor_speed
        if self.agv.container_robot.rotate(self.agv.rotate_motor, self.pos, speed):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        self.agv.rotate_motor.reset()


class StretchAction(BaseAction):
    def __init__(self, agv, length, action_name="Stretch"):
        super().__init__(action_name)
        self.agv = agv
        self.length = length

    def run(self, m):
        super().run(m)
        temp_motor_speed = ConfigParams.stretch_motor_speed
        if ConfigParams.max_stretch_length < self.length < ConfigParams.max_stretch_length + 0.1:
            Navigation.setTaskError("StretchLengthExceeded", f"Stretch length {self.length} exceeds upper limit{ConfigParams.max_stretch_length}. Check if goods are too far from robot！")
            self.length = ConfigParams.max_stretch_length
        elif self.length > ConfigParams.max_stretch_length + 0.1:
            Navigation.setTaskError("StretchLengthExceeded", f"Stretch length {self.length} exceeds upper limit{ConfigParams.max_stretch_length}. Check if goods are too far from robot！！！")
            self.action_status = ActionStatus.FAILED
            return
        if self.length > 0.1 and self.agv.stretch_real_pos > self.length * 0.6:
            temp_motor_speed = ConfigParams.stretch_motor_speed * 0.6
        if self.agv.container_robot.stretch(self.agv.stretch_motor, self.length, temp_motor_speed):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        self.agv.stretch_motor.reset()


class FingerAction(BaseAction):
    def __init__(self, agv, pos, action_name="Finger"):
        super().__init__(action_name)
        self.agv = agv
        self.pos = pos
        self._motor_started = False

    def run(self, m):
        super().run(m)
        if not ConfigParams.has_finger_motor:
            Navigation.setDeviceError("FingerMotorNotConfig",
                f"fingerMotor not configured in device model. "
                f"Please add two fingerMotor entries under Model-000.moduleType.cartonTransferUnit.fingerMotor")
            self.action_status = ActionStatus.FAILED
            return
        if time.time() - self.start_time > 3:
            Navigation.setDeviceError("FingerTimeout", f"Finger control timeout. Check if finger is stuck or photoelectric sensor works")
            self._stop_finger()
            self.action_status = ActionStatus.FAILED
            return

        if not self._motor_started:
            self._motor_started = True
            Motor.resetMotor(ConfigParams.left_finger_motor_name)
            Motor.resetMotor(ConfigParams.right_finger_motor_name)
            if self.pos == 1:
                # 打开手指：正转，到 upReachDI 停止
                Motor.setMotorSpeed(ConfigParams.left_finger_motor_name, 1.0,
                                    ConfigParams.left_finger_up_di or "")
                Motor.setMotorSpeed(ConfigParams.right_finger_motor_name, 1.0,
                                    ConfigParams.right_finger_up_di or "")
            else:
                # 关闭手指：反转，到 downReachDI 停止
                if Di.getDi(ConfigParams.overlimit_detect_di):
                    Navigation.setTaskError("StretchObstacle", f"Fork overlimit photoelectric sensor detected obstacle. Increase stretch compensation")
                    self.action_status = ActionStatus.FAILED
                    return
                Motor.setMotorSpeed(ConfigParams.left_finger_motor_name, -1.0,
                                    ConfigParams.left_finger_down_di or "")
                Motor.setMotorSpeed(ConfigParams.right_finger_motor_name, -1.0,
                                    ConfigParams.right_finger_down_di or "")

        left_reached = Motor.isMotorReached(ConfigParams.left_finger_motor_name)
        right_reached = Motor.isMotorReached(ConfigParams.right_finger_motor_name)

        if left_reached:
            self.agv.left_finger_real_pos = self.pos
            Motor.resetMotor(ConfigParams.left_finger_motor_name)
        if right_reached:
            self.agv.right_finger_real_pos = self.pos
            Motor.resetMotor(ConfigParams.right_finger_motor_name)
        if left_reached and right_reached:
            Trace.log(f"手指{'打开' if self.pos == 1 else '关闭'}成功", name=f"{MOD}.motor")
            self.action_status = ActionStatus.FINISHED

    def _stop_finger(self):
        """停止手指电机"""
        Motor.resetMotor(ConfigParams.left_finger_motor_name)
        Motor.resetMotor(ConfigParams.right_finger_motor_name)

    def reset(self):
        super().reset()
        self._motor_started = False


class CheckFingerOpenAction(BaseAction):
    """检查拨指是否已打开，未打开则报错"""
    def __init__(self, agv, action_name="CheckFingerOpen"):
        super().__init__(action_name)
        self.agv = agv

    def run(self, m):
        super().run(m)
        if Di.getDi(ConfigParams.left_finger_up_di) and Di.getDi(ConfigParams.right_finger_up_di):
            self.action_status = ActionStatus.FINISHED
        else:
            Navigation.setDeviceError("FingerNotOpen", f"Finger not open, stretch cancelled. Check finger and photoelectric sensor")
            self.action_status = ActionStatus.FAILED

    def reset(self):
        super().reset()


class RecAdjustAction(BaseAction):
    """识别调整动作，内部封装 RecAdjust 循环"""
    def __init__(self, agv, action_name="RecAdjust"):
        super().__init__(action_name)
        self.agv = agv
        self.light_started = False

    def run(self, m):
        super().run(m)
        if not self.light_started:
            Do.setDo(self.agv.fill_light_do, True)
            self.light_started = True
            return
        if time.time() - self.start_time < ConfigParams.light_delay_time:
            return
        if self.agv.rec_adjust.status is ScriptStatus.FINISHED:
            Do.setDo(self.agv.fill_light_do, False)
            self.action_status = ActionStatus.FINISHED
        elif self.agv.rec_adjust.status is ScriptStatus.FAILED:
            self.action_status = ActionStatus.FAILED
        else:
            self.agv.rec_adjust.run(self.agv)

    def reset(self):
        super().reset()
        self.light_started = False


class RecBarcodeAction(BaseAction):
    """识别一维码并验证"""
    def __init__(self, agv, action_name="RecBarcode"):
        super().__init__(action_name)
        self.agv = agv
        self.light_on = False

    def run(self, m):
        super().run(m)
        if not self.light_on:
            Do.setDo(self.agv.fill_light_do, True)
            if Do.getDo(self.agv.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.light_on = True
        else:
            if self.agv.rec_res and self.agv.rec_res.get("status", 1) == 0:
                Do.setDo(self.agv.fill_light_do, False)
                if self.agv.rec_res['barCode'] != self.agv.goods_id:
                    Navigation.setTaskError("GoodsIdMismatch", f"Goods ID mismatch between task command  {self.agv.goods_id} and recognition result {self.agv.rec_res['barCode']}")
                    self.action_status = ActionStatus.FAILED
                else:
                    self.agv.report_info["barCode"] = self.agv.rec_res['barCode']
                    self.action_status = ActionStatus.FINISHED
            else:
                if Timer.delay(0.05):
                    Recognize.doRec(ConfigParams.barcode_file, "", "")
                self.agv.report_info["barCode"] = "None"

    def reset(self):
        super().reset()
        self.light_on = False


class BindContainerAction(BaseAction):
    """绑定容器数据"""
    def __init__(self, container_id, goods_id, desc="", action_name="BindContainer"):
        super().__init__(action_name)
        self.container_id = container_id
        self.goods_id = goods_id
        self.desc = desc

    def run(self, m):
        super().run(m)
        Container.bindContainer(self.container_id, self.goods_id, self.desc)
        self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()


class UnbindContainerAction(BaseAction):
    """解绑容器数据"""
    def __init__(self, container_id, action_name="UnbindContainer"):
        super().__init__(action_name)
        self.container_id = container_id

    def run(self, m):
        super().run(m)
        Container.unbindContainer(self.container_id)
        self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()


class CheckGoodsDiAction(BaseAction):
    """检查货叉光电并绑定容器"""
    def __init__(self, agv, action_name="CheckGoodsDi"):
        super().__init__(action_name)
        self.agv = agv

    def run(self, m):
        super().run(m)
        if Di.getDi(ConfigParams.goods_check_di):
            Container.bindContainer("999", self.agv.goods_id, "")
        self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()


class CheckGoodsDiUnloadTakeAction(BaseAction):
    """放货流程-从背篓取出后检查光电，有货则转绑到999"""
    def __init__(self, agv, action_name="CheckGoodsDiUnloadTake"):
        super().__init__(action_name)
        self.agv = agv

    def run(self, m):
        super().run(m)
        if Di.getDi(ConfigParams.goods_check_di):
            goods_id = Container.getGoodsByContainer(self.agv.cur_c)
            Container.bindContainer("999", goods_id, "")
            Container.unbindContainer(self.agv.cur_c)
        else:
            Navigation.setDeviceError("BackpackPickFailed", "Failed to pick from backpack, fork photoelectric did not detect goods")
            self.action_status = ActionStatus.FAILED
            return
        self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()


class RecBoxCheckAction(BaseAction):
    """放货前识别货架上是否有货"""
    def __init__(self, agv, action_name="RecBoxCheck"):
        super().__init__(action_name)
        self.agv = agv
        self.light_started = False
        self.light_ready = False

    def run(self, m):
        super().run(m)
        if not self.light_started:
            self.agv.rec_box.status = ScriptStatus.RUNNING
            self.agv.rec_box.is_error = True
            Do.setDo(self.agv.fill_light_do, True)
            self.light_started = True
        if not self.light_ready:
            if Do.getDo(self.agv.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.light_ready = True
            return
        if self.agv.rec_box.status is ScriptStatus.FINISHED:
            self.agv.rec_box.reset()
            self.agv.rec_box.is_error = None
            Do.setDo(self.agv.fill_light_do, False)
            if self.agv.rec_box.hasGoods and not self.agv.rec_box.goods_out_dist:
                Navigation.setTaskError("ShelfHasGoods", f"Goods detected on shelf, unload cancelled. Verify shelf and task data manually")
                self.action_status = ActionStatus.FAILED
            else:
                self.action_status = ActionStatus.FINISHED
        elif self.agv.rec_box.status is ScriptStatus.FAILED:
            Do.setDo(self.agv.fill_light_do, False)
            self.action_status = ActionStatus.FINISHED
        else:
            self.agv.rec_box.run(self.agv)

    def reset(self):
        super().reset()
        self.light_started = False
        self.light_ready = False


class FillLightAction(BaseAction):
    """补光灯开启+延时"""
    def __init__(self, agv, action_name="FillLight"):
        super().__init__(action_name)
        self.agv = agv
        self.light_on = False

    def run(self, m):
        super().run(m)
        if not self.light_on:
            Do.setDo(self.agv.fill_light_do, True)
            self.light_on = True
        if time.time() - self.start_time > ConfigParams.light_delay_time:
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        self.light_on = False


class RecQrcodeAction(BaseAction):
    """识别二维码并上报"""
    def __init__(self, agv, action_name="RecQrcode"):
        super().__init__(action_name)
        self.agv = agv

    def run(self, m):
        super().run(m)
        if time.time() - self.start_time > 20:
            Navigation.setTaskError("RecFailed",f"Recognition failed after max retries{self.max_rec_times}. Check if QR code is damaged or camera is clear")
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.rec.status == ScriptStatus.FINISHED:
            data = {
                "containerRobot": {
                    "locName": self.agv.script_args.get("locName", ""),
                    "taskId": self.agv.script_args.get("taskId", ""),
                    "load": {
                        "lift": self.agv.lift_real_pos + self.agv.rec.result['z'] + ConfigParams.load_rec_lift_diff
                    },
                    "unload": {
                        "lift": self.agv.lift_real_pos + self.agv.rec.result['z']
                    }
                }
            }
            NetProtocol.tcpUploadString(json.dumps(data))
            self.agv.report_info["recQrcodeData"] = data
            self.agv.rec.reset()
            Do.setDo(self.agv.fill_light_do, False)
            self.action_status = ActionStatus.FINISHED
        else:
            self.agv.rec.run(self.agv)

    def reset(self):
        super().reset()


class TakePhotoAction(BaseAction):
    """拍照动作"""
    def __init__(self, agv, action_name="TakePhoto"):
        super().__init__(action_name)
        self.agv = agv
        self.light_on = False
        self.light_ready = False

    def run(self, m):
        super().run(m)
        if not self.light_on:
            Do.setDo(self.agv.fill_light_do, True)
            Recognize.resetRec()
            self.light_on = True
        if not self.light_ready:
            if Do.getDo(self.agv.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.light_ready = True
            return
        Recognize.doRec(ConfigParams.box_code_file, "", "")
        if Timer.delay(0.5):
            Do.setDo(self.agv.fill_light_do, False)
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        self.light_on = False
        self.light_ready = False


# ============================================================================
# 任务脚本主类
# ============================================================================
class ContainerRobot(ModuleBase):
    def __init__(self):
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
        self.ok_yaw = ConfigParams.ok_yaw / 180 * math.pi

        self.args_init = False
        self.script_args = {}
        self.status = ScriptStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.goods_id = ""
        self.lift_height = None
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

        self.fill_light_do = "DO-004"
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
        self.zero_step = [False] * 4
        self.calib_step = [False] * 3
        self.yaw_adjust = 0
        self.rec_res = None
        self.rec_id = None
        self.rec_box_lift = None
        self.finger_open_start = False
        self.pre_finger = None

        self.lift_motor_calib = None
        self.stretch_motor_calib = None
        self.rotate_motor_calib = None

        self.set_lift_motor_calib = False
        self.set_stretch_motor_calib = False
        self.set_rotate_motor_calib = False
        self.motor_calib_state = False
        self.motor_calib_info = {}
        self.enable_motor = False
        self.enable_motor_time = time.time()
        self.set_force_calib = False

        self.box_code_file = None
        self.shelf_code_file = None

        self.counter = 0

        # action_list 状态机
        self.action_list = []
        self.action_id = 0
        self.action_status = ActionStatus.INIT
        self.current_action = None
        self.operation_init = False
        # 框架动作队列引擎(action_list 作暂存源, 经 _sync_task 镜像到此队列执行)
        self.action_task = ActionTask(mod=MOD)

    def init_args(self, args):
        """初始化任务参数"""
        self.script_args = args or Module.getTaskArgs()
        if args:
            self.goods_id = self.script_args.get("goodsName", "")
            self.self_position = self.script_args.get("container", self.self_position)
            self.self_position = str(self.self_position) if self.self_position is not None else self.self_position
            self.update_move_task_params()
            self.finger_pos = self.script_args.get("finger", 0)
            self.lift_height = self.script_args.get("lift", 0)
            self.stretch_length = self.script_args.get("stretch", 0)
            self.is_auto_stretch = bool("stretch" not in self.script_args)
            self.rotate_pos = self.script_args.get("rotate", 0) / 180 * math.pi
            self.offset_x = self.script_args.get("offsetX", ConfigParams.offset_x)
            self.pre_finger = self.script_args.get("preFinger", self.pre_finger)
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
            container_num = ConfigParams.get_container_count()
            if isinstance(container_num, int) and container_num > 0:
                Container.initContainer(container_num, "999")
            self.containers = Container.getContainers()
            self.rec_id = uuid.uuid4().hex
            self.box_code_file = self.script_args.get("codeFile", ConfigParams.box_code_file)
            self.shelf_code_file = self.script_args.get("shelfCodeFile", ConfigParams.shelf_code_file)
            if "recAdjust" in self.script_args:
                if self.target_type is None:
                    if self.operation == "load" or self.operation == "exTake":
                        self.rec_adjust = RecAdjust(self.box_code_file)
                    elif self.operation == "unload" or self.operation == "exPut":
                        self.rec_adjust = RecAdjust(self.shelf_code_file)
                elif self.target_type == "box":
                    self.rec_adjust = RecAdjust(self.box_code_file)
                elif self.target_type == "shelf":
                    self.rec_adjust = RecAdjust(self.shelf_code_file)
            if self.target_type == "box" and self.code_type == "code":
                self.rec = Rec(self.box_code_file)
            elif self.target_type == "shelf" and self.code_type == "code":
                self.rec = Rec(self.shelf_code_file)

            if ConfigParams.goods_check_di != "":
                if self.stretch_real_pos < 0.05:
                    if Di.getDi(ConfigParams.goods_check_di) and not Container.hasGoods("999"):
                        Navigation.setTaskError("ForkHasGoods", f"Fork (slot 999) already has goods, cannot execute current task. Verify data")
                        self.status = ScriptStatus.FAILED
                    elif not Di.getDi(ConfigParams.goods_check_di):
                        Container.unbindContainer("999")
            else:
                Navigation.setTaskError("GoodsCheckDiError", f"goodsCheckDi not configured properly in script parameters！")
                Trace.log(f"请在脚本参数中正确配置 goodsCheckDi 参数！", name=f"{MOD}.err")
                self.status = ScriptStatus.FINISHED

            self.start_time = time.time()
            self.status = ScriptStatus.RUNNING

    def run(self):
        """分发、执行任务"""
        self.status = ScriptStatus.RUNNING
        self.counter += 1
        self.update_report_info()
        self.report_info["getCountRun"] = self.counter
        self.check_motor_emc()
        if self.enable_motor and not self.motor_calib_state:
            self.motor_calib()

        if time.time() - self.start_time > ConfigParams.timeout:
            Navigation.setTaskError("ScriptTimeout", f"Script task execution timeout. Please re-issue the task！")
            self.status = ScriptStatus.FAILED

        if self.motor_calib_state:
            if self.operation is not None and self.operation != 'none':
                if not check_debug_task(self.operation):
                    self.status = ScriptStatus.FAILED
                    return self.status
                if self.operation == "zero":
                    self._build_zero_actions()
                elif self.operation == "calib":
                    self.force_calib()
                elif self.operation == "zeroWithLift":
                    self.lift_height = min(self.lift_real_pos, self.lift_height)
                    self._build_zero_actions(self.lift_height)
                elif self.operation == "load":
                    self._build_load_actions()
                elif self.operation == "unload":
                    self._build_unload_actions()
                elif self.operation == "recBoxBarcode":
                    self._build_rec_box_barcode_actions()
                elif self.operation == "recQrcode":
                    self._build_rec_qrcode_actions()
                elif self.operation == "takePhoto":
                    self._build_take_photo_actions()
                elif self.operation == "inTake":
                    self._build_in_take_actions()
                elif self.operation == "inPut":
                    self._build_in_put_actions()
                elif self.operation == "exTake":
                    self._build_ex_take_actions()
                elif self.operation == "exPut":
                    self._build_ex_put_actions()
                else:
                    Navigation.setTaskError("InputParamError", f"Invalid script input parameters")
                    self.status = ScriptStatus.FAILED

                self._drive_queue()
                if self.action_status == ActionStatus.FINISHED:
                    self.status = ScriptStatus.FINISHED
                elif self.action_status == ActionStatus.FAILED:
                    self.status = ScriptStatus.FAILED
            else:
                if "finger" in self.script_args:
                    if not self.operation_init:
                        self.operation_init = True
                        self.action_list = [FingerAction(self, self.finger_pos)]
                    self._drive_queue()
                    if self.action_status == ActionStatus.FINISHED:
                        self.update_finger_info()
                        self.status = ScriptStatus.FINISHED
                    elif self.action_status == ActionStatus.FAILED:
                        self.status = ScriptStatus.FAILED
                elif "lift" in self.script_args or "rotate" in self.script_args:
                    if not self.operation_init:
                        self.operation_init = True
                        actions = []
                        if "lift" in self.script_args:
                            actions.append(LiftAction(self, self.lift_height))
                        if "rotate" in self.script_args:
                            actions.append(RotateAction(self, self.rotate_pos))
                        self.action_list = [ParallelAction(actions)] if len(actions) > 1 else actions
                    self._drive_queue()
                    if self.action_status == ActionStatus.FINISHED:
                        self.status = ScriptStatus.FINISHED
                    elif self.action_status == ActionStatus.FAILED:
                        self.status = ScriptStatus.FAILED
                elif "stretch" in self.script_args:
                    if not self.operation_init:
                        self.operation_init = True
                        self.action_list = [StretchAction(self, self.stretch_length)]
                    self._drive_queue()
                    if self.action_status == ActionStatus.FINISHED:
                        self.status = ScriptStatus.FINISHED
                    elif self.action_status == ActionStatus.FAILED:
                        self.status = ScriptStatus.FAILED
                elif "visionType" in self.script_args:
                    if self.code_type == "barcode":
                        if not self.operation_init:
                            self.operation_init = True
                            self.action_list = [RecBarcodeAction(self)]
                        self._drive_queue()
                        if self.action_status == ActionStatus.FINISHED:
                            self.status = ScriptStatus.FINISHED
                        elif self.action_status == ActionStatus.FAILED:
                            self.status = ScriptStatus.FAILED
                    elif self.code_type == "code":
                        self._build_rec_qrcode_actions()
                        self._drive_queue()
                        if self.action_status == ActionStatus.FINISHED:
                            self.status = ScriptStatus.FINISHED
                        elif self.action_status == ActionStatus.FAILED:
                            self.status = ScriptStatus.FAILED

        self.update_report_info()
        self.report_info['scriptArgs'] = self.script_args
        self.report_info['scriptStartTime'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time))
        self.report_info['scriptRunningTime'] = time.time() - self.start_time
        self.motor_calib_info['allMotorEnable'] = self.enable_motor
        self.motor_calib_info['liftMotorCalib'] = self.lift_motor_calib
        self.motor_calib_info['stretchMotorCalib'] = self.stretch_motor_calib
        self.motor_calib_info['rotateMotorCalib'] = self.rotate_motor_calib
        self.motor_calib_info['allMotorCalib'] = self.motor_calib_state
        self.report_info['motorCalibInfo'] = self.motor_calib_info
        self.report_info['taskStatus'] = self.status
        self.report_info['goodsName'] = self.goods_id
        self.report_info['containers'] = self.containers
        self.report_info['motorInfo'] = self.container_robot.state or -1
        self.report_info['actionId'] = self.action_id
        self.report_info['actionListLen'] = len(self.action_list)
        if self.current_action:
            self.report_info['currentAction'] = self.current_action.action_name
            self.report_info['currentActionStatus'] = self.current_action.action_status
        if self.status == ScriptStatus.FAILED or self.status == ScriptStatus.FINISHED:
            NetProtocol.release()
            Do.setDo(self.fill_light_do, False)
            Trace.log(f"script finished: {json.dumps(self.report_info)}", name=MOD)
        return self.status

    def _sync_task(self):
        """将 action_list 新增的尾部动作镜像进 action_task(build/extend)。
        action_list 是各 operation 装配动作的暂存源; action_task 是框架执行引擎, 共享同一批动作对象。
        ctu 各 operation 一次性 build(无运行中动态追加), 通常仅首次 build。"""
        have = self.action_task.total
        want = len(self.action_list)
        if want <= have:
            return
        new = self.action_list[have:]
        if self.action_task.status in (ActionStatus.RUNNING, ActionStatus.SUSPENDED):
            self.action_task.extend(new)
        else:
            self.action_task.build(new)
            self.action_list = new

    def _drive_queue(self):
        """推进框架队列一步, 并把队列终态同步回 self.action_status(沿用既有 status 判定)。"""
        self._sync_task()
        if self.action_task.total == 0:
            return
        self.action_task.step(self)
        self.current_action = self.action_task.current
        if self.action_task.is_done:
            self.action_status = (ActionStatus.FAILED
                                  if self.action_task.status == ActionStatus.FAILED
                                  else ActionStatus.FINISHED)

    # ================================================================
    # action_list 构建方法
    # ================================================================
    def _build_zero_actions(self, zero_height=0.5):
        if self.operation_init:
            return
        self.operation_init = True
        actions = []
        if not Container.hasGoods("999"):
            actions.append(FingerAction(self, 1, "zero_finger_open"))
        actions.append(StretchAction(self, 0, "zero_stretch"))
        actions.append(RotateAction(self, 0, action_name="zero_rotate"))
        actions.append(LiftAction(self, zero_height, "zero_lift"))
        self.action_list = actions

    def _build_load_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        Trace.log(f"----- building load actions {self.goods_id} ------", name=f"{MOD}.action")

        if not self.cur_c:
            if (self.goods_id and Container.goodsExist(self.goods_id) and
                    Container.getContainerByGoods(self.goods_id) != "999"):
                Navigation.setTaskError("GoodsAlreadyExists", f"Goods {self.goods_id} already exist. Check for duplicate task")
                self.status = ScriptStatus.FAILED
                return
            if self.self_position:
                if Container.hasGoods(self.self_position):
                    Navigation.setTaskError("BackpackSlotFull", f"Backpack slot {int(self.self_position) + 1} (No.{self.self_position}) already has goods, cannot continue loading. Please verify task data and backpack data！")
                    self.status = ScriptStatus.FAILED
                    return
                self.cur_c = self.self_position
            else:
                self.cur_c = self.search_operable_container('load')
            Trace.log(f"load begin: {json.dumps(self.containers)}", name=f"{MOD}.action")
            if self.cur_c is None:
                Navigation.setTaskError("AllBackpackFull", f"All backpack slots are full, cannot load more goods！")
                self.status = ScriptStatus.FAILED
                return
            if Container.hasGoods("999") and Container.getGoodsByContainer("999") == self.goods_id:
                actions = []
                if self.cur_c == "999":
                    self.action_list = []
                    self.action_status = ActionStatus.FINISHED
                    return
                actions.append(ParallelAction([
                    RotateAction(self, 0, action_name="load_rotate_zero"),
                    LiftAction(self, ConfigParams.high[int(self.cur_c)], "load_lift_to_container"),
                ], "load_parallel_to_container"))
                actions.append(StretchAction(self, ConfigParams.stretch_self_length, "load_stretch_self"))
                actions.append(FingerAction(self, 1, "load_finger_open_put"))
                actions.append(StretchAction(self, 0, "load_stretch_retract_put"))
                actions.append(FingerAction(self, 0, "load_finger_close_final"))
                actions.append(LiftSafeAction(self, "load_lift_safe"))
                actions.append(UnbindContainerAction("999", "load_unbind_999"))
                actions.append(BindContainerAction(self.cur_c, self.goods_id, "", "load_bind_container"))
                self.action_list = actions
                return
            elif Container.hasGoods("999"):
                Navigation.setTaskError("ForkHasGoods", f"Fork (slot 999) already has goods, cannot execute current task. Verify data")
                self.status = ScriptStatus.FAILED
                return

        actions = []
        actions.append(ParallelAction([
            FingerAction(self, 1, "load_finger_open"),
            RotateAction(self, self.rotate_pos, action_name="load_rotate"),
            LiftAction(self, self.lift_height, "load_lift"),
        ], "load_parallel_init"))
        if self.barcode_height is not None:
            actions.append(LiftAction(self, self.barcode_height, "load_lift_barcode"))
            actions.append(RecBarcodeAction(self, "load_rec_barcode"))
        if self.rec_adjust is not None:
            actions.append(RecAdjustAction(self, "load_rec_adjust"))
        actions.append(LiftAction(self, self.lift_height + self.load_height, "load_lift_pick"))
        actions.append(CheckFingerOpenAction(self, "load_check_finger"))
        actions.append(StretchAction(self, self.stretch_length, "load_stretch_out"))
        actions.append(FingerAction(self, 0, "load_finger_close"))
        actions.append(StretchAction(self, 0, "load_stretch_retract"))
        actions.append(CheckGoodsDiAction(self, "load_check_goods"))
        if self.cur_c == "999":
            actions.append(UnbindContainerAction("999", "load_unbind_999"))
            actions.append(BindContainerAction(self.cur_c, self.goods_id, "", "load_bind_container"))
        else:
            actions.append(ParallelAction([
                RotateAction(self, 0, action_name="load_rotate_zero"),
                LiftAction(self, ConfigParams.high[int(self.cur_c)], "load_lift_to_container"),
            ], "load_parallel_to_container"))
            actions.append(StretchAction(self, ConfigParams.stretch_self_length, "load_stretch_self"))
            actions.append(FingerAction(self, 1, "load_finger_open_put"))
            actions.append(StretchAction(self, 0, "load_stretch_retract_put"))
            actions.append(FingerAction(self, 0, "load_finger_close_final"))
            actions.append(LiftSafeAction(self, "load_lift_safe"))
            actions.append(UnbindContainerAction("999", "load_unbind_999"))
            actions.append(BindContainerAction(self.cur_c, self.goods_id, "", "load_bind_container"))
        self.action_list = actions

    def _build_in_take_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        if not self.cur_c:
            self.check_take()
            if self.status == ScriptStatus.FAILED:
                return
        if self.cur_c == "999":
            self.action_list = []
            self.action_status = ActionStatus.FINISHED
            return
        actions = []
        actions.append(ParallelAction([
            FingerAction(self, 1, "in_take_finger_open"),
            LiftAction(self, ConfigParams.low[int(self.cur_c)], "in_take_lift"),
            RotateAction(self, 0, action_name="in_take_rotate_zero"),
        ], "in_take_parallel_init"))
        actions.append(StretchAction(self, ConfigParams.stretch_self_length, "in_take_stretch_out"))
        actions.append(FingerAction(self, 0, "in_take_finger_close"))
        actions.append(StretchAction(self, 0, "in_take_stretch_retract"))
        actions.append(ParallelAction([
            RotateAction(self, self.rotate_pos, action_name="in_take_rotate_target"),
            LiftAction(self, self.lift_height, "in_take_lift_target"),
        ], "in_take_parallel_final"))
        actions.append(UnbindContainerAction(self.cur_c, "in_take_unbind"))
        self.action_list = actions

    def _build_in_put_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        if not self.cur_c:
            self.check_put()
            if self.status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
                return
        actions = []
        actions.append(ParallelAction([
            LiftAction(self, ConfigParams.high[int(self.cur_c)], "in_put_lift"),
            RotateAction(self, 0, action_name="in_put_rotate_zero"),
        ], "in_put_parallel_init"))
        actions.append(StretchAction(self, ConfigParams.stretch_self_length, "in_put_stretch_out"))
        actions.append(FingerAction(self, 1, "in_put_finger_open"))
        actions.append(StretchAction(self, 0, "in_put_stretch_retract"))
        actions.append(FingerAction(self, 0, "in_put_finger_close"))
        actions.append(LiftSafeAction(self, "in_put_lift_safe"))
        self.action_list = actions

    def _build_ex_take_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        if Container.hasGoods("999"):
            Navigation.setTaskError("ForkHasGoods", f"Fork (slot 999) already has goods, cannot execute current task. Verify data")
            self.status = ScriptStatus.FAILED
            return
        Trace.log(f"----- building ex_take actions ------", name=f"{MOD}.action")
        actions = []
        if self.barcode_height is not None:
            actions.append(ParallelAction([
                LiftAction(self, self.barcode_height, "ex_take_lift_barcode"),
                RotateAction(self, self.rotate_pos, action_name="ex_take_rotate_barcode"),
            ], "ex_take_parallel_barcode"))
            actions.append(RecBarcodeAction(self, "ex_take_rec_barcode"))
        else:
            actions.append(RotateAction(self, self.rotate_pos, action_name="ex_take_rotate"))
        if self.rec_adjust is not None:
            actions.append(ParallelAction([
                LiftAction(self, self.lift_height, "ex_take_lift_rec"),
                RotateAction(self, self.rotate_pos, action_name="ex_take_rotate_rec"),
            ], "ex_take_parallel_rec"))
            actions.append(RecAdjustAction(self, "ex_take_rec_adjust"))
        actions.append(LiftAction(self, self.lift_height + self.load_height, "ex_take_lift_pick"))
        actions.append(FingerAction(self, 1, "ex_take_finger_open"))
        actions.append(StretchAction(self, self.stretch_length, "ex_take_stretch_out"))
        actions.append(FingerAction(self, 0, "ex_take_finger_close"))
        actions.append(StretchAction(self, 0, "ex_take_stretch_retract"))
        actions.append(BindContainerAction("999", self.goods_id, "", "ex_take_bind"))
        self.action_list = actions

    def _build_ex_put_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        Trace.log(f"----- building ex_put actions ------", name=f"{MOD}.action")
        if not Container.hasGoods("999"):
            self._build_unload_actions()
            return
        actions = []
        if self.rec_box_lift:
            actions.append(ParallelAction([
                LiftAction(self, self.rec_box_lift, "ex_put_lift_rec_box"),
                RotateAction(self, self.rotate_pos, action_name="ex_put_rotate_rec_box"),
            ], "ex_put_parallel_rec_box"))
            actions.append(RecBoxCheckAction(self, "ex_put_rec_box_check"))
        actions.append(ParallelAction([
            LiftAction(self, self.lift_height, "ex_put_lift"),
            RotateAction(self, self.rotate_pos, action_name="ex_put_rotate"),
        ], "ex_put_parallel_position"))
        if self.rec_adjust is not None:
            actions.append(RecAdjustAction(self, "ex_put_rec_adjust"))
        actions.append(LiftAction(self, self.lift_height + self.unload_height, "ex_put_lift_place"))
        actions.append(StretchAction(self, self.stretch_length, "ex_put_stretch_out"))
        actions.append(FingerAction(self, 1, "ex_put_finger_open"))
        actions.append(StretchAction(self, 0, "ex_put_stretch_retract"))
        actions.append(ParallelAction([
            RotateAction(self, 0, action_name="ex_put_rotate_zero"),
            FingerAction(self, 0, "ex_put_finger_close"),
        ], "ex_put_parallel_final"))
        actions.append(LiftSafeAction(self, "ex_put_lift_safe"))
        actions.append(UnbindContainerAction("999", "ex_put_unbind"))
        self.action_list = actions

    def _build_unload_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        Trace.log(f"----- building unload actions ------", name=f"{MOD}.action")

        if not self.cur_c:
            if self.self_position:
                if Container.getGoodsByContainer(self.self_position) != self.goods_id:
                    Navigation.setTaskError("GoodsIdMismatch", f"Goods ID in backpack slot {int(self.self_position) + 1} ({self.self_position}) doesn't match task goods ID ({self.goods_id})! Verify task and backpack data!")
                    self.status = ScriptStatus.FAILED
                    return
                if not Container.hasGoods(self.self_position):
                    Navigation.setTaskError("BackpackSlotEmpty", f"Backpack slot {int(self.self_position) + 1} ({self.self_position}) is empty, cannot unload! Verify task and backpack data!")
                    self.status = ScriptStatus.FAILED
                    return
                if self.self_position != "999" and Container.hasGoods("999"):
                    Navigation.setTaskError("ForkHasGoods", f"Fork (slot 999) already has goods, cannot execute current task. Verify data")
                    self.status = ScriptStatus.FAILED
                    return
                self.cur_c = self.self_position
            else:
                if Container.hasGoods("999"):
                    self.cur_c = "999"
                    if Container.getGoodsByContainer("999") != self.goods_id:
                        Navigation.setTaskError("ForkHasGoods", f"Fork (slot 999) already has goods, cannot execute current task. Verify data")
                        self.status = ScriptStatus.FAILED
                        return
                else:
                    self.cur_c = Container.getContainerByGoods(self.goods_id)
            if not self.cur_c:
                Navigation.setTaskError("GoodsNotFound", f"Goods {self.goods_id} not found in backpack, cannot unload! Verify task and backpack data!")
                self.status = ScriptStatus.FAILED
                return
            Trace.log(f"unload begin: {json.dumps(self.containers)}", name=f"{MOD}.action")

        actions = []
        if self.cur_c != "999":
            actions.append(ParallelAction([
                LiftAction(self, ConfigParams.low[int(self.cur_c)], "unload_lift_container"),
                FingerAction(self, 1, "unload_finger_open_take"),
                RotateAction(self, 0, action_name="unload_rotate_zero_take"),
            ], "unload_parallel_take_init"))
            actions.append(StretchAction(self, ConfigParams.stretch_self_length, "unload_stretch_self"))
            actions.append(FingerAction(self, 0, "unload_finger_close_take"))
            actions.append(StretchAction(self, 0, "unload_stretch_retract_take"))
            actions.append(CheckGoodsDiUnloadTakeAction(self, "unload_check_goods_take"))

        if self.rec_box_lift:
            actions.append(ParallelAction([
                RotateAction(self, self.rotate_pos, action_name="unload_rotate_rec"),
                LiftAction(self, self.rec_box_lift, "unload_lift_rec_box"),
            ], "unload_parallel_rec_box_pos"))
            if self.rec_box is not None:
                actions.append(RecBoxCheckAction(self, "unload_rec_box_check"))
            actions.append(LiftAction(self, self.lift_height, "unload_lift_after_rec"))
        else:
            actions.append(ParallelAction([
                LiftAction(self, self.lift_height, "unload_lift_target"),
                RotateAction(self, self.rotate_pos, action_name="unload_rotate_target"),
            ], "unload_parallel_target"))

        if self.rec_adjust is not None:
            actions.append(RecAdjustAction(self, "unload_rec_adjust"))
        actions.append(LiftAction(self, self.lift_height + self.unload_height, "unload_lift_place"))
        if self.pre_finger is not None:
            actions.append(ParallelAction([
                FingerAction(self, self.pre_finger, "unload_pre_finger"),
                StretchAction(self, self.stretch_length, "unload_stretch_out"),
            ], "unload_parallel_stretch_finger"))
        else:
            actions.append(StretchAction(self, self.stretch_length, "unload_stretch_out"))
        actions.append(FingerAction(self, 1, "unload_finger_open"))
        actions.append(StretchAction(self, 0, "unload_stretch_retract"))
        actions.append(ParallelAction([
            FingerAction(self, 0, "unload_finger_close"),
            RotateAction(self, 0, action_name="unload_rotate_zero"),
            LiftSafeAction(self, "unload_lift_safe"),
        ], "unload_parallel_final"))
        actions.append(UnbindContainerAction("999", "unload_unbind_999"))
        self.action_list = actions

    def _build_rec_box_barcode_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        actions = []
        actions.append(ParallelAction([
            LiftAction(self, self.lift_height, "rec_barcode_lift"),
            RotateAction(self, self.rotate_pos, action_name="rec_barcode_rotate"),
        ], "rec_barcode_parallel_pos"))
        actions.append(RecBarcodeAction(self, "rec_barcode_scan"))
        self.action_list = actions

    def _build_rec_qrcode_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        actions = []
        actions.append(ParallelAction([
            LiftAction(self, self.lift_height, "rec_qrcode_lift"),
            RotateAction(self, self.rotate_pos, action_name="rec_qrcode_rotate"),
        ], "rec_qrcode_parallel_pos"))
        actions.append(FillLightAction(self, "rec_qrcode_light"))
        actions.append(RecQrcodeAction(self, "rec_qrcode_scan"))
        self.action_list = actions

    def _build_take_photo_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        actions = []
        actions.append(ParallelAction([
            LiftAction(self, self.lift_height, "photo_lift"),
            RotateAction(self, self.rotate_pos, action_name="photo_rotate"),
        ], "photo_parallel_pos"))
        actions.append(TakePhotoAction(self, "photo_take"))
        self.action_list = actions

    @staticmethod
    def get_motor_info(motor_name: str):
        motor_data = Odometer.getData().get("motorInfo", [])
        for _motor in motor_data:
            if _motor.get('motorName') == motor_name:
                return _motor
        return {}

    def check_motor_emc(self):
        controller_emc = Controller.getEmc()
        lift_motor_info = self.get_motor_info(ConfigParams.lift_motor_name)
        stretch_motor_info = self.get_motor_info(ConfigParams.stretch_motor_name)
        rotate_motor_info = self.get_motor_info(ConfigParams.rotate_motor_name)
        lift_motor_emc = lift_motor_info.get("emc", False)
        stretch_motor_emc = stretch_motor_info.get("emc", False)
        rotate_motor_emc = rotate_motor_info.get("emc", False)
        self.motor_calib_info["liftMotorEmc"] = lift_motor_emc
        self.motor_calib_info["stretchMotorEmc"] = stretch_motor_emc
        self.motor_calib_info["rotateMotorEmc"] = rotate_motor_emc
        self.motor_calib_info["controllerEmc"] = controller_emc
        self.enable_motor = not lift_motor_emc and not rotate_motor_emc and not stretch_motor_emc
        if not controller_emc and time.time() - self.enable_motor_time > 0.5:
            self.enable_motor_time = time.time()
            if lift_motor_info and lift_motor_emc:
                Motor.enableMotor(ConfigParams.lift_motor_name)
                self.report_info['liftMotorInfo'] = lift_motor_info
            if stretch_motor_info and stretch_motor_emc:
                Motor.enableMotor(ConfigParams.stretch_motor_name)
                self.report_info['stretchMotorInfo'] = stretch_motor_info
            if rotate_motor_info and rotate_motor_emc:
                Motor.enableMotor(ConfigParams.rotate_motor_name)
                self.report_info['rotateMotorInfo'] = rotate_motor_info

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

            calib_retry = (
                (self.set_stretch_motor_calib and self.stretch_motor_stop and self.stretch_motor_calib != 2) or
                (self.set_lift_motor_calib and self.lift_motor_stop and self.lift_motor_calib != 2) or
                (self.set_rotate_motor_calib and self.rotate_motor_stop and self.rotate_motor_calib != 2)
            )
            if calib_retry:
                Trace.log("标零失败检测：电机已停止但calib未完成，重置标志位重新下发", name=f"{MOD}.motor")
                self.set_lift_motor_calib = False
                self.set_rotate_motor_calib = False
                self.set_stretch_motor_calib = False

            if self.stretch_motor_calib == 2:
                self.calib_step[0] = True
            if self.lift_motor_calib == 2:
                self.calib_step[1] = True
            if self.rotate_motor_calib == 2:
                self.calib_step[2] = True

    def get_motor_calib_state(self):
        odo_data = Odometer.getData()
        if odo_data.get("motorInfo", None):
            motor_info = odo_data["motorInfo"]
            self.report_info["motorInfo"] = motor_info
            for m_f in motor_info:
                if m_f["key"] == ConfigParams.lift_motor_name:
                    self.lift_motor_calib = m_f.get("calib", None)
                    self.lift_motor_stop = m_f.get("stop", None)
                if m_f["key"] == ConfigParams.stretch_motor_name:
                    self.stretch_motor_calib = m_f.get("calib", None)
                    self.stretch_motor_stop = m_f.get("stop", None)
                if m_f["key"] == ConfigParams.rotate_motor_name:
                    self.rotate_motor_calib = m_f.get("calib", None)
                    self.rotate_motor_stop = m_f.get("stop", None)
        self.motor_calib_state = (
                self.lift_motor_calib == 2 and self.stretch_motor_calib == 2 and self.rotate_motor_calib == 2)

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
        """暂停任务方法（必须）"""
        if Module.getStatus() == ScriptStatus.RUNNING:
            self.action_task.suspend()
            self.status = ScriptStatus.SUSPENDED

    def resume(self):
        """恢复任务方法（必须）"""
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            self.action_task.resume()
            self.status = ScriptStatus.RUNNING

    def cancel(self):
        """取消任务方法（必须）"""
        Recognize.resetRec()
        self.close_finger()
        Do.setDo(self.fill_light_do, False)
        self.action_task.cancel()
        self.status = ScriptStatus.FAILED
        Trace.log("carton cancel", name=MOD)

    def update_move_task_params(self):
        move_task = Navigation.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsName':
                self.goods_id = p['stringValue']
            if p['key'] == '#containerId' and p['stringValue'] != "":
                self.self_position = p['stringValue']

    def zero(self, zero_height=0):
        Trace.log(f"----- running zero ------", name=f"{MOD}.motor")
        if not self.zero_step[0]:
            self.zero_step[0] = Container.hasGoods("999") or self._finger_open_for_zero()
        elif self.zero_step[0] and not self.zero_step[1]:
            self.zero_step[1] = self.container_robot.stretch(self.stretch_motor, 0)
        elif self.zero_step[1] and not self.zero_step[2]:
            self.zero_step[2] = self.container_robot.rotate(self.rotate_motor, 0)
        elif self.zero_step[2] and not self.zero_step[3]:
            self.zero_step[3] = self.container_robot.lift(self.lift_motor, zero_height, ConfigParams.lift_motor_speed)
        Trace.log(f"zero_step:{self.zero_step}", name=f"{MOD}.motor")
        if all(self.zero_step):
            self.zero_step = [False] * 4
            return True
        return False

    def _finger_open_for_zero(self):
        """ DoMotor 打开手指，每帧推进，超时3秒"""
        if not getattr(self, '_zero_finger_ts', None):
            self._zero_finger_ts = time.time()
        elif time.time() - self._zero_finger_ts > 3:
            Navigation.setDeviceError("FingerTimeout", f"Finger control timeout during zero. Check if finger is stuck or photoelectric sensor works")
            self.close_finger()
            self.status = ScriptStatus.FAILED
            self._zero_finger_ts = None
            return False

        if not getattr(self, '_zero_finger_started', False):
            self._zero_finger_started = True
            Motor.resetMotor(ConfigParams.left_finger_motor_name)
            Motor.resetMotor(ConfigParams.right_finger_motor_name)
            Motor.setMotorSpeed(ConfigParams.left_finger_motor_name, 1.0,
                                ConfigParams.left_finger_up_di or "")
            Motor.setMotorSpeed(ConfigParams.right_finger_motor_name, 1.0,
                                ConfigParams.right_finger_up_di or "")

        left_reached = Motor.isMotorReached(ConfigParams.left_finger_motor_name)
        right_reached = Motor.isMotorReached(ConfigParams.right_finger_motor_name)
        if left_reached:
            self.left_finger_real_pos = 1
            Motor.resetMotor(ConfigParams.left_finger_motor_name)
        if right_reached:
            self.right_finger_real_pos = 1
            Motor.resetMotor(ConfigParams.right_finger_motor_name)
        if left_reached and right_reached:
            Trace.log(f"手指打开成功 (zero)", name=f"{MOD}.motor")
            self._zero_finger_started = False
            self._zero_finger_ts = None
            return True
        return False

    def close_finger(self):
        Motor.resetMotor(ConfigParams.left_finger_motor_name)
        Motor.resetMotor(ConfigParams.right_finger_motor_name)

    def update_finger_info(self):
        if Di.getDi(ConfigParams.left_finger_down_di) and not Di.getDi(ConfigParams.left_finger_up_di):
            self.left_finger_real_pos = 0
        elif Di.getDi(ConfigParams.left_finger_up_di) and not Di.getDi(ConfigParams.left_finger_down_di):
            self.left_finger_real_pos = 1
        if Di.getDi(ConfigParams.right_finger_down_di) and not Di.getDi(ConfigParams.right_finger_up_di):
            self.right_finger_real_pos = 0
        elif Di.getDi(ConfigParams.right_finger_up_di) and not Di.getDi(ConfigParams.right_finger_down_di):
            self.right_finger_real_pos = 1
        self.finger_info["leftFinger"] = self.left_finger_real_pos
        self.finger_info["rightFinger"] = self.right_finger_real_pos

    def rotate(self, pos, max_speed=None):
        Trace.log(f"----- running rotate ------", name=f"{MOD}.motor")
        if abs(pos) > abs(ConfigParams.max_rotate_angle / 180 * math.pi):
            Navigation.setTaskError("RotateAngleExceeded",f"Rotate angle {self.pos / math.pi * 180} exceeds upper limit {ConfigParams.max_rotate_angle}. Check if box is tilted or QR code is damaged")
            self.status = ScriptStatus.FAILED
            return False
        if self.stretch_real_pos > ConfigParams.safe_stretch_length:
            Navigation.setTaskError("StretchNotZeroed", f"Stretch mechanism not zeroed, cannot perform lift/rotate. Please zero first")
            self.status = ScriptStatus.FAILED
            return False
        if max_speed is not None:
            speed = max_speed
        else:
            speed = ConfigParams.rotate_motor_speed
        if self.container_robot.rotate(self.rotate_motor, pos, speed):
            return True
        return False

    def update_report_info(self):
        module_pos = dict()
        self.lift_real_pos = Motor.getMotorPos(ConfigParams.lift_motor_name)
        self.stretch_real_pos = Motor.getMotorPos(ConfigParams.stretch_motor_name)
        self.rotate_real_pos = Motor.getMotorPos(ConfigParams.rotate_motor_name)
        self.update_finger_info()
        module_pos['lift'] = round(self.lift_real_pos, 3)
        module_pos['stretch'] = round(self.stretch_real_pos, 3)
        module_pos['rotate'] = round(self.rotate_real_pos * 180 / math.pi, 3)
        module_pos['leftFinger'] = self.left_finger_real_pos
        module_pos['rightFinger'] = self.right_finger_real_pos
        self.containers = Container.getContainers()
        self.report_info["currentPos"] = module_pos

    def tick_report(self):
        """每 tick 调用一次:合并一次 reportInfo(含 containers)+ 集中数值时序(ctu.task / ctu.motor)。"""
        self.update_report_info()
        cur = self.action_task.current
        counts = self.action_task.status_counts()
        containers = self.containers or []
        container_count = sum(1 for c in containers if c.get("hasGoods"))

        # 调度/Roboshop 上报(合并一次; containers 必带)
        self.report_info.update({
            "status": self.status,
            "action": cur.action_name if cur else "",
            "actionTotal": self.action_task.total,
            "containers": containers,
        })
        Module.reportInfo(self.report_info)

        # ctu.task 数值时序(int 稳定)
        Trace.log(
            {
                "scriptStatus":   int(self.status),
                "total":          int(self.action_task.total),
                "runningCount":   int(counts["running"]),
                "waitingCount":   int(counts["init"]),
                "finishedCount":  int(counts["finished"]),
                "failedCount":    int(counts["failed"]),
                "suspendedCount": int(counts["suspended"]),
            },
            False,
            name=f"{MOD}.task",
        )
        # ctu.motor 数值时序(料箱车机构状态)
        Trace.log(
            {
                "ctuHeight": float(self.lift_real_pos or 0.0),
                "ctuTarget": float(self.lift_height or 0.0),
                "ctuInPlace": bool(cur and cur.action_status == ActionStatus.FINISHED),
                "containerCount": int(container_count),
            },
            False,
            name=f"{MOD}.motor",
        )

    def has_goods_id(self, goods_id: str):
        Trace.log(f"goodsName: {goods_id}", name=MOD)
        for c in self.containers:
            if goods_id == c['containerId']:
                return True
        return False

    def search_operable_container(self, opt):
        ct = None
        if opt == 'load':
            for c in self.containers:
                if not c['hasGoods']:
                    ct = c['containerId']
                    break
        elif opt == 'unload':
            for c in self.containers:
                if c['hasGoods'] and self.goods_id == c['containerId']:
                    ct = c['containerId']
        return ct

    def check_put(self):
        if not Container.hasGoods("999"):
            Navigation.setTaskError("ForkNoGoods", f"Fork (slot 999) has no goods, internal put not needed！")
            self.status = ScriptStatus.FINISHED
            return
        if self.goods_id and Container.goodsExist(self.goods_id):
            Navigation.setTaskError("GoodsAlreadyExists", f"Goods {self.goods_id} already exist. Check for duplicate task")
            self.status = ScriptStatus.FINISHED
            return
        if self.self_position:
            if Container.hasGoods(self.self_position):
                Navigation.setTaskError("GoodsInBackpack", f"Goods already in backpack")
                self.status = ScriptStatus.FAILED
                return
            self.cur_c = self.self_position
        else:
            self.cur_c = self.search_operable_container('load')
        if self.cur_c is None:
            Navigation.setTaskError("AllBackpackFull", f"All backpack slots are full, cannot load more goods")
            self.status = ScriptStatus.FINISHED
            return

    def check_take(self):
        if self.self_position:
            if not Container.hasGoods(self.self_position):
                Navigation.setTaskError("BackpackSlotEmpty", f"Backpack slot {int(self.self_position) + 1} ({self.self_position}) is empty, cannot execute internal pick!")
                self.status = ScriptStatus.FAILED
            self.cur_c = self.self_position
        else:
            self.cur_c = Container.getContainerByGoods(self.goods_id)
        if Container.hasGoods("999"):
            self.cur_c = "999"
        if not self.cur_c:
            Navigation.setTaskError("GoodsNotFound", f"Specified goods {self.goods_id} not found in backpack. Verify goods ID and container data！")
            self.status = ScriptStatus.FAILED
            return

    def safeMoveCheck(self):
        """底盘移动前安全检查（可选）"""
        self.check_motor_emc()
        if self.enable_motor and not self.motor_calib_state:
            self.motor_calib()

        debug_print(f"[safe_move_check] motor_calib 后: motor_calib_state={self.motor_calib_state}")

        status = SafeMoveStatus.RUNNING
        if self.motor_calib_state:
            zero_result = self.zero(0.5)
            if zero_result:
                status = SafeMoveStatus.FINISHED
        else:
            debug_print(f"[safe_move_check] motor 未标零，跳过 zero，等待下一帧")

        self.setSafeMoveStatus(status)
        Trace.log(f"safe_move_check {Module.getSafeMoveCheck()}", name=MOD)
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False

    def modbus(self):
        debug_print("modbus___________ 读取Modbus数据")
        args = {}
        op_data = NetProtocol.getModbusData("4x", 201, 1)
        if op_data:
            operation_code = parseModbus(op_data, 'uint16')
            debug_print(f"   操作码: {operation_code}")
            if operation_code == 1:
                args["operation"] = "load"
                height_data = NetProtocol.getModbusData("4x", 202, 2)
                if len(height_data) >= 2:
                    height = parseModbus(height_data, 'float')
                    debug_print(f"   读取高度参数寄存器值: [{height_data[0]}, {height_data[1]}]")
                    debug_print(f"   解析后高度值: {height:.4f}m")
                    args["height"] = max(0.0, min(0.06, height))
                    debug_print(f"   设置高度: {args['height']:.4f}m")
            elif operation_code == 2:
                args["operation"] = "unload"
            elif operation_code == 3:
                args["operation"] = "spin"
                debug_print("读取浮点型参数:")
                angle_data = NetProtocol.getModbusData("4x", 202, 1)
                if angle_data:
                    angle_raw = parseModbus(angle_data, 'int16')
                    args["spinAngle"] = angle_raw / 100.0
                    debug_print(f"   设置角度: {args['spinAngle']:.2f}度")
                else:
                    args["spinAngle"] = 90.0
                    debug_print("   使用默认角度")
            elif operation_code == 4:
                args["operation"] = "getCurrentPathProperty"
                debug_print("读取字符串参数:")
                str_data = NetProtocol.getModbusData("4x", 202, 4)
                if str_data:
                    device_name = parseModbus(str_data, 'string', 0, len(str_data))
                    if device_name:
                        args["device"] = device_name
                        debug_print(f"   设备名称: {device_name}")
            debug_print(f"   操作类型: {args.get('operation', 'unknown')}")
        return args


# ============================================================================
# 识别辅助类
# ============================================================================
class Rec:
    def __init__(self, filename, is_error=None, max_rec_times=10):
        self.status = ScriptStatus.NONE
        self.is_error = is_error
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = max_rec_times
        self.result = dict()
        self.hasGoods = None
        self.goods_out_dist = None
        self.max_goods_dist = 0.8
        Recognize.resetRec()
        Recognize.doRec(self.filename, "", "")

    def run(self, agv):
        self.status = ScriptStatus.RUNNING
        rec_status = Recognize.getRecStatus()
        if rec_status == 3 or rec_status == -1:
            Trace.log("rec failed:{}".format(self.result), name=f"{MOD}.rec")
            if Timer.delay(0.05):
                self.rec_times = self.rec_times + 1
                if self.rec_times > self.max_rec_times:
                    if not self.is_error:
                        Navigation.setTaskError("RecFailed", f"Recognition failed after max retries{self.max_rec_times}. Check if QR code is damaged or camera is clear")
                        self.status = ScriptStatus.FAILED
                    else:
                        self.status = ScriptStatus.FINISHED
                else:
                    Recognize.resetRec()
                    Recognize.doRec(self.filename, "", "")
        elif rec_status == 2:
            rec_results = Recognize.getRecResults()
            if "recoList" in rec_results:
                if len(rec_results["recoList"]) == 1:
                    reco = rec_results["recoList"][0]
                    if not reco.get('valid', False):
                        Trace.log("Rec: recognition result is invalid (valid=False), retrying", name=f"{MOD}.rec")
                        Recognize.resetRec()
                        Recognize.doRec(self.filename, "", "")
                        return
                    self.result = reco.get('robotResult', {})
            Recognize.resetRec()
            self.hasGoods = True
            if self.result.get("x", 0) > self.max_goods_dist:
                self.goods_out_dist = True
            self.status = ScriptStatus.FINISHED
        Trace.log(f"rec success: {self.status.name} {self.result}", name=f"{MOD}.rec")

        cur_state = dict()
        cur_state['recResult'] = self.result
        cur_state['recCount'] = self.rec_times
        cur_state['recTaskStatus'] = self.status
        cur_state['recStatus'] = rec_status
        cur_state['file'] = self.filename
        agv.report_info['recInfo'] = cur_state

    def reset(self):
        Recognize.resetRec()
        Recognize.doRec(self.filename, "", "")
        self.status = ScriptStatus.RUNNING


class RecAdjust:
    def __init__(self, filename):
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

        self.next_rotate_pos = 1.5708
        self.diff_height = 0
        self.last_yaw_adjust = 1.5708
        self.plan_status = ScriptStatus.NONE
        self.goPath = GoPath()
        self.code2robot = -1

    @staticmethod
    def move_x(dx, dy, yaw, rotate_pos, offset_x=0):
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
                Trace.log(f"----- rec to adjust {self.rec.status.name}------", name=f"{MOD}.rec")
                self.rec.run(agv)
            elif self.rec.status is ScriptStatus.FAILED:
                self.rec_fail_time = self.rec_fail_time + 1
                random_dist = random.choice([1, -1]) * (1 / 180 * math.pi)
                agv.rotate(agv.rotate_real_pos + random_dist, max_speed=0.3)
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.rec.reset()
                    self.rec.run(agv)
                else:
                    self.status = ScriptStatus.FAILED
                Trace.log("rec fail!!! {}".format(self.rec_fail_time), name=f"{MOD}.rec")
            elif self.rec.status is ScriptStatus.FINISHED:
                Trace.log(f"------------------ move to adjust -----------------", name=f"{MOD}.rec")
                self.rec_fail_time = 0

                if agv.is_auto_stretch:
                    if agv.operation == "load":
                        agv.stretch_length = (abs(self.rec.result['x']) - ConfigParams.auto_stretch_odo_len +
                                              ConfigParams.auto_load_stretch_dist + ConfigParams.auto_stretch_box_len)
                    elif agv.operation == "unload":
                        agv.stretch_length = (abs(self.rec.result['x']) - ConfigParams.auto_stretch_odo_len +
                                              ConfigParams.auto_unload_stretch_dist + ConfigParams.auto_stretch_box_len)

                code2fork = [self.rec.result['x'], self.rec.result['y'], self.rec.result['z'],
                             self.rec.result['yaw']]

                self.diff_height = self.rec.result['z']
                agv.rec_height_diff = self.rec.result['z']
                agv.yaw_adjust = math.pi - abs(code2fork[3])
                if code2fork[3] > 0:
                    self.next_rotate_pos = agv.rotate_real_pos - agv.yaw_adjust
                else:
                    self.next_rotate_pos = agv.rotate_real_pos + agv.yaw_adjust

                if ConfigParams.auto_adjust_rotate:
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
                self.go_args["maxSpeed"] = 0.3
                self.go_args["maxAcc"] = 0.3
                self.go_args["maxDec"] = 0.3
                self.go_args["reachDist"] = 0.003
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                else:
                    self.go_args["backMode"] = 0

                if abs(agv.yaw_adjust) > ConfigParams.max_yaw_bias / 180 * math.pi:
                    self.status = ScriptStatus.FAILED
                    Navigation.setTaskError("RecYawExceeded", f"Recognition yaw deviation{agv.yaw_adjust / math.pi * 180:.2f}° exceeds limit{ConfigParams.max_yaw_bias}°. Check if box is aligned and QR code intact")
                else:
                    if self.adjust_count >= (self.max_adjust_time - 3):
                        agv.ok_x = 0.01
                        agv.ok_yaw = 1.15 / 180 * math.pi
                    if not ConfigParams.auto_adjust_rotate and abs(self.rec.result['y']) < agv.ok_x:
                        Trace.log(f"adjust finished, adjust count: {self.adjust_count}", name=f"{MOD}.rec")
                        self.status = ScriptStatus.FINISHED
                    elif ConfigParams.auto_adjust_rotate and abs(self.rec.result['y']) < agv.ok_x and abs(
                            agv.yaw_adjust) <= agv.ok_yaw:
                        Trace.log(f"adjust finished, adjust count: {self.adjust_count}", name=f"{MOD}.rec")
                        self.status = ScriptStatus.FINISHED
                    else:
                        if self.adjust_count >= self.max_adjust_time:
                            self.status = ScriptStatus.FAILED
                            Navigation.setTaskError("RecAdjustExceeded", f"Recognition adjustment {self.adjust_count} retries exceeded. Check QR code, camera, accuracy parameters")
                self.plan_status = ScriptStatus.FINISHED
                self.rec.reset()
        elif self.status is not ScriptStatus.FINISHED and self.status is not ScriptStatus.FAILED:
            if self.goPath.status != ScriptStatus.FINISHED and self.goPath.status != ScriptStatus.FAILED:
                if abs(self.go_args['x']) < 0.003:
                    self.goPath.status = ScriptStatus.FINISHED
                else:
                    if self.goPath.status != ScriptStatus.FINISHED and self.goPath.status != ScriptStatus.FAILED:
                        self.goPath.run(self.go_args)
            elif not self.rotate_step and self.goPath.status == ScriptStatus.FINISHED:
                if abs(agv.yaw_adjust) <= 0.01:
                    self.rotate_step = True
                if not self.rotate_step and ConfigParams.auto_adjust_rotate:
                    self.rotate_step = agv.rotate(self.next_rotate_pos, max_speed=0.3)
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
        cur_state["autoStretchLength"] = agv.stretch_length
        cur_state["goPathStatus"] = self.goPath.status
        cur_state["goArgs"] = self.go_args
        cur_state["recResult"] = self.rec.result
        cur_state["recFailTime"] = self.rec_fail_time
        cur_state["adjustCount"] = self.adjust_count
        cur_state["curRotate"] = agv.rotate_real_pos / math.pi * 180
        cur_state["curLift"] = agv.lift_real_pos
        cur_state["curStretch"] = agv.stretch_real_pos
        cur_state["status"] = self.status
        cur_state["agvYawAdjust"] = agv.yaw_adjust / math.pi * 180
        cur_state["lastYawAdjust"] = self.last_yaw_adjust / math.pi * 180
        cur_state["nextRotatePos"] = self.next_rotate_pos / math.pi * 180
        agv.report_info["recAdjust"] = cur_state
        Trace.log(f"[ContainerRobot][{agv.lift_real_pos}|{agv.stretch_real_pos}|{agv.rotate_real_pos / math.pi * 180}|"
                  f"{self.rec.result.get('x', 0)}|{self.rec.result.get('y', 0)}|{self.rec.result.get('z', 0)}|{self.rec.result.get('yaw', 0)}|"
                  f"{agv.yaw_adjust / math.pi * 180}|{self.last_yaw_adjust / math.pi * 180}|{self.next_rotate_pos / math.pi * 180}|"
                  f"{self.rec_fail_time}|{self.adjust_count}|{self.rec.rec_times}|{self.go_args.get('x', 0)}|", name=f"{MOD}.rec", debug=True)

    def reset(self):
        self.rec.reset()
        self.status = ScriptStatus.RUNNING
        self.rec_fail_time = 0
        self.goPath.reset()


def main():
    Module.init()

    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    # 注册设备参数变更回调
    RobotParam.setDeviceChangeCallBack(robot_device_callback)

    # 实例化脚本任务主类
    robot = ContainerRobot()
    modbus_args = None
    container_num = ConfigParams.get_container_count()
    if isinstance(container_num, int) and container_num > 0:
        Container.initContainer(container_num, "999")

    while True:
        # 脚本任务状态管理
        status = robot.status
        # 上报脚本任务状态
        Module.setStatus(status)

        # 每 tick 集中上报(reportInfo 含 containers + ctu.task/ctu.motor 数值时序)
        robot.tick_report()

        # 触发安全检查事件
        if robot.event_safe_move_check:
            robot.safeMoveCheck()
        if robot.event_modbus:
            modbus_args = robot.modbus()
            robot.event_modbus = False

        if status == ScriptStatus.NONE:
            args = modbus_args or Module.getTaskArgs()
            if args:
                try:
                    debug_print("args", args)
                    # 校验参数, 解析为不带.的参数
                    args = script_param.loadInput(args)
                    debug_print("check ok, args:", json.dumps(args, indent=2))
                    # 初始化参数，成功时设置任务状态为RUNNING
                    robot = ContainerRobot()
                    robot.init_args(args)
                except ValueError as e:
                    Trace.log(f"check error: {e}", name=f"{MOD}.err")
        elif status == ScriptStatus.RUNNING:
            robot.run()
        elif status == ScriptStatus.SUSPENDED:
            robot.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            modbus_args = None
            robot.status = ScriptStatus.NONE

        """需要增加sleep，如果时间太短控制器增加CPU占用"""
        time.sleep(0.1)


if __name__ == '__main__':
    main()



