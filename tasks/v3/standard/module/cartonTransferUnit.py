# -*- coding: utf-8 -*-
# @Date: 2026/9/16
# @Author: zhaopengfei
# @Version: v1.2
# @Project: SPK-MJ50-HL
# @Update: fix: 修复inPut和inTake背篓绑定错误问题
# @RBK Version: V3.5+
import enum
import uuid
import math
SCRIPT_VERSION = "20260615"
import json
import random
import time
from typing import List

from syspy.utils.time import Timer
from syspy import Module, Logger, Di, Do, Motor, Navigation, ScriptStatus, Controller, Odometer, Recognize, \
    RobotParam, Trace, AutoPreInterface, AutoPreSequenceAction, is_simulation, _TR
from syspy.lib.net_protocol import parseModbus, NetProtocol
from syspy.bin import Container
from syspy.lib.module import SafeMoveStatus, ModuleBase
from syspy.lib.action_task import ActionBase, ActionStatus, ActionTask
from syspy.utils.param_server import ParamBuilder, ParamType, ScriptParam, BindType
from standard.goPath import GoPath

log = Logger("ContainerRobot")
script_param = ScriptParam(__file__)

# 业务通道名前缀（日志规范 <MOD>[.xxx]）
MOD = "ctu"

# AutoPre 本地预算。位置动作按距离/配置速度估算，并增加到位稳定余量；
# 手指动作沿用 FingerAction 的 3 秒超时作为保守预算。
AUTO_PRE_ADVANCE_TIME = 1.0
AUTO_PRE_POSITION_SETTLE_TIME = 1.0
AUTO_PRE_FINGER_BUDGET = 3.0
AUTO_PRE_DI_BUDGET = 0.1

# 取货结束后货物保留在 999；这里只跨任务保存重建延迟入背篓动作所需的最小数据。
_pending_fork_store = None


def _remember_pending_fork_store(goods_id, preferred_container, skip_safe_height=False):
    global _pending_fork_store
    _pending_fork_store = {
        "goodsName": goods_id,
        "preferredContainer": preferred_container,
        "skipSafeHeight": bool(skip_safe_height),
    }


def _clear_pending_fork_store():
    global _pending_fork_store
    _pending_fork_store = None


def _get_pending_fork_store():
    global _pending_fork_store
    if not Container.hasGoods("999"):
        _pending_fork_store = None
        return None
    goods_id = Container.getGoodsByContainer("999")
    if not _pending_fork_store or _pending_fork_store.get("goodsName") != goods_id:
        _pending_fork_store = {
            "goodsName": goods_id,
            "preferredContainer": None,
            "skipSafeHeight": False,
        }
    return dict(_pending_fork_store)

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
    # DM14 三联码校验（识别 objectMessage 与任务 goodsId 比对）
    check_goods_code_enable = False
    max_code_check_fail = 3
    # 识别前等待机构机械停稳的延时(秒), 防止抖动污染识别
    motor_settle_delay = 0

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
        # .id 是背篓个数（id=2 表示背篓0和1，共2个），初始化时另减去货叉999。
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
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.App.RECOGNITION)
                        builder.DEFAULTVALUE("recognition/default.srec")
                    with builder.CHILD(key="shelfCodeFile", name=_TR("Shelf Code File"),
                                       desc=_TR("Shelf Code Recognition Config")):
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.App.RECOGNITION)
                        builder.DEFAULTVALUE("recognition/default1.srec")
                    with builder.CHILD(key="barcodeFile", name=_TR("Barcode File"), desc=_TR("Barcode Recognition Config")):
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.App.RECOGNITION)
                        builder.DEFAULTVALUE("recognition/default2.srec")
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
                    with builder.CHILD(key="checkGoodsCodeEnable", name=_TR("Check Goods Code Enable"),
                                       desc=_TR("Verify that the recognized goods code (objectMessage) matches the task goods ID when loading (DM14 triple code)")):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="maxCodeCheckFail", name=_TR("Max Code Check Fail"),
                                       desc=_TR("Max goods code comparison failures before raising an error")):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(3, min_value=1, max_value=100)

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
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.Device.DI)
                        builder.DEFAULTVALUE("DI-008")
                        builder.REQUIRED(True)
                    with builder.CHILD(key="overlimitDetectDi", name=_TR("Overlimit Detect Di"),
                                       desc=_TR("Fork Safe Travel Limit")):
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.Device.DI)
                        builder.DEFAULTVALUE("DI-009")
                        builder.REQUIRED(True)
                    with builder.CHILD(key="lightDelayTime", name=_TR("Light Delay Time"), desc=_TR("time for light")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3, min_value=0, max_value=100)
                        builder.REQUIRED(True)
                    with builder.CHILD(key="motorSettleDelay", name=_TR("Motor Settle Delay"),
                                       desc=_TR("Wait for lift/rotate/stretch to mechanically settle before recognition, avoids vibration polluting recognition")):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0, min_value=0, max_value=100)
                        builder.REQUIRED(True)

        builder.save(merge=True)
        cls.load_config()

    @staticmethod
    def _strip_rec_prefix(value):
        _rec_prefix = "recognition/"
        if isinstance(value, str) and value.startswith(_rec_prefix):
            return value[len(_rec_prefix):]
        return value

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
        cls.box_code_file = cls._strip_rec_prefix(cls.config.get("boxCodeFile"))
        cls.shelf_code_file = cls._strip_rec_prefix(cls.config.get("shelfCodeFile"))
        cls.barcode_file = cls._strip_rec_prefix(cls.config.get("barcodeFile"))
        cls.offset_x = cls.config.get("offsetX")
        cls.load_rec_lift_diff = cls.config.get("loadRecLiftDiff")
        cls.rec_box_extra_height = cls.config.get("recBoxExtraHeight")
        cls.ok_x = cls.config.get("okX")
        cls.ok_yaw = cls.config.get("okYaw")
        cls.max_yaw_bias = cls.config.get("maxYawBias")
        cls.check_goods_code_enable = cls.config.get("checkGoodsCodeEnable", False)
        cls.max_code_check_fail = cls.config.get("maxCodeCheckFail", 3)

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
        cls.motor_settle_delay = cls.config.get("motorSettleDelay", 0)


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

# 恢复类操作(归零/标定):不做“货叉有货但数据为空”的一致性拦截。
# 这些操作用于异常后把机构收回原点,必须始终可执行,否则货叉卡货时会与拦截互相死锁,无法归零。
RECOVERY_OPERATIONS = {"zero", "zeroWithLift", "calib"}


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


def create_skip_safe_height_param(builder: ParamBuilder,
                                  desc: str = _TR("Skip lowering fork to safe height after the action completes")):
    with builder.CHILD(key="skipSafeHeight", name=_TR("Skip Safe Height"), desc=desc):
        builder.TYPE(ParamType.BOOL)
        builder.DEFAULTVALUE(False)


'''参数创建必须在全局作用域中'''


class InputParams:
    """脚本任务输入参数定义（参数创建必须放到全局作用域中）"""
    builder = script_param.builderInput()

    with builder.GROUPS():
        with builder.GROUP(key="operation", name=_TR("Operation"), desc=_TR("Mechanism action options")):
            builder.TYPE(ParamType.COMBO_BOX)
            with builder.CHILDREN():
                with builder.CHILD(key="zero", name=_TR("Zero"), desc=_TR("Mechanism homing")):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="load", name=_TR("Load"), desc=_TR("Pick up goods")):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="recfile", name=_TR("Recognition File"), desc=_TR("Recognition file for loading")):
                            builder.TYPE(ParamType.BIND_TYPE)
                            builder.BINDTYPE(BindType.App.RECOGNITION)
                            builder.REQUIRED(False)
                        create_vision_type_param(builder, _TR("Vision type: 'box' or 'shelf', optional"))
                        create_lift_param(builder, _TR("Fork height for recognition before picking"))
                        create_rotate_param(builder, _TR("Fork angle before picking"))
                        create_rec_adjust_param(builder, _TR("Adjust robot position when recognition is enabled"))
                        create_stretch_param(builder, _TR("Fork extension length when picking; auto-calculated from the recognition result if omitted"))
                        create_container_param(builder, _TR("Vehicle basket number; specifies the basket for internal put; if omitted, put in order from bottom to top"))
                        create_goods_id_param(builder, _TR("Set the goods number; empty string if omitted"))
                        create_skip_safe_height_param(builder)
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
                        create_skip_safe_height_param(builder)

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
                            create_skip_safe_height_param(builder)

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
                            create_skip_safe_height_param(builder)

    # 保存脚本任务输入参数
    builder.save()


# ============================================================================
# 脚本内置动作模板定义
# ============================================================================
script_param.addAction(
    action_name="liftAndRotate",
    policy=None,
    args={
        "lift": 0.0,
        "rotate": 0,
    },
    config={}
)

script_param.addAction(
    action_name="finger",
    policy=None,
    args={
        "finger": 0,
    },
    config={}
)

script_param.addAction(
    action_name="stretch",
    policy=None,
    args={
        "stretch": 0.0,
    },
    config={}
)

script_param.addAction(
    action_name="zero",
    policy=None,
    args={"operation": "zero"},
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
        self.suspend_start_time = None
        self.action_state = {}
        self.auto_pre_timing_enabled = False
        self.auto_pre_timing = None

    def run(self, m):
        self.action_state["action_runtime"] = time.time() - self.start_time
        self.action_state["action_name"] = self.action_name

    def reset(self):
        super().reset()
        self.start_time = time.time()
        self.suspend_start_time = None
        self.auto_pre_timing = None
        if self.auto_pre_timing_enabled:
            self._prepare_auto_pre_timing()

    def suspend(self):
        if self.action_status != ActionStatus.RUNNING:
            return
        self.suspend_start_time = time.time()
        self._suspend_hardware()
        super().suspend()

    def resume(self):
        if self.action_status != ActionStatus.SUSPENDED:
            return
        if self.suspend_start_time is not None:
            self.start_time += time.time() - self.suspend_start_time
            self.suspend_start_time = None
        super().resume()

    def _suspend_hardware(self):
        """机构 Action 按需覆写，暂停时撤销正在执行的硬件指令。"""

    def _prepare_auto_pre_timing(self):
        """仅由机构 Action 覆写；正式动作不会启用该计时标记。"""

    def _set_auto_pre_timing(
            self, mechanism, estimated_seconds, start_position, target_position, unit):
        self.auto_pre_timing = {
            "action": self.action_name,
            "mechanism": mechanism,
            "estimatedSeconds": estimated_seconds,
            "startPosition": start_position,
            "targetPosition": target_position,
            "unit": unit,
        }


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

    def suspend(self):
        if self.action_status != ActionStatus.RUNNING:
            return
        for action in self.actions:
            if action.action_status == ActionStatus.RUNNING:
                action.suspend()
        super().suspend()

    def resume(self):
        if self.action_status != ActionStatus.SUSPENDED:
            return
        for action in self.actions:
            if action.action_status == ActionStatus.SUSPENDED:
                action.resume()
        super().resume()


class CtuAutoPreSequenceAction(AutoPreSequenceAction):
    """在预动作真正启动时开启 CTU 业务超时计时。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nav_start_time = None
        self.nav_end_time = None
        self.nav_estimated_time = None
        self.timing_printed = False
        self.timed_pre_actions = []
        self._mark_timed_pre_actions(self.pre_actions)

    def _mark_timed_pre_actions(self, actions):
        for action in actions:
            children = getattr(action, "actions", None)
            if children is not None:
                self._mark_timed_pre_actions(children)
                continue
            if isinstance(action, BaseAction):
                action.auto_pre_timing_enabled = True
                self.timed_pre_actions.append(action)

    def reset(self):
        super().reset()
        self.nav_start_time = None
        self.nav_end_time = None
        self.nav_estimated_time = None
        self.timing_printed = False
        for action in self.timed_pre_actions:
            action.auto_pre_timing = None

    def _capture_action_timings(self):
        for action in self.timed_pre_actions:
            timing = action.auto_pre_timing
            if timing is None or "actualSeconds" in timing:
                continue
            if action.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
                timing["actualSeconds"] = max(0.0, time.time() - action.start_time)
                timing["status"] = action.action_status.name.lower()

    @staticmethod
    def _rounded_timing(timing):
        result = dict(timing)
        for key in ("estimatedSeconds", "actualSeconds", "startPosition", "targetPosition"):
            value = result.get(key)
            if isinstance(value, (int, float)) and math.isfinite(value):
                result[key] = round(value, 3)
        return result

    def _log_timings(self):
        nav_actual_time = None
        if self.nav_start_time is not None:
            nav_actual_time = (self.nav_end_time or time.time()) - self.nav_start_time
        navigation = {
            "estimatedSeconds": self.nav_estimated_time,
            "actualSeconds": nav_actual_time,
            "station": self.station,
            "includeRotation": self.include_rotation,
        }
        Trace.log(
            {
                "event": "autoPreTiming",
                "navigation": self._rounded_timing(navigation),
                "mechanisms": [
                    self._rounded_timing(action.auto_pre_timing)
                    for action in self.timed_pre_actions
                    if action.auto_pre_timing is not None
                ],
            },
            output_time=True,
            name=f"{MOD}.autoPreTiming",
        )
        self.timing_printed = True

    def run(self, ctx):
        remaining_time = AutoPreInterface.remainingTime(
            self.station, self.include_rotation
        )
        if remaining_time is not None:
            if self.nav_start_time is None:
                self.nav_start_time = time.time()
                self.nav_estimated_time = remaining_time
            if remaining_time <= 0.0 and self.nav_end_time is None:
                self.nav_end_time = time.time()

        was_started = self.started
        super().run(ctx)
        if not was_started and self.started:
            ctx.start_business_timeout()
        self._capture_action_timings()

        if (self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED)
                and not self.timing_printed):
            self._log_timings()


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
        Motor.resetMotor(self.motor_name)
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
            Navigation.setTaskError("LiftHeightExceeded", _TR(f"Lift height exceeds upper limit, max: {ConfigParams.max_lift_height}, commanded: {self.height}"))
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.stretch_real_pos > ConfigParams.safe_stretch_length:
            Navigation.setTaskError("StretchNotZeroed", _TR(f"Stretch mechanism not zeroed, cannot perform lift/rotate. Please zero first"))
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.container_robot.lift(self.agv.lift_motor, self.height, ConfigParams.lift_motor_speed):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        self.agv.lift_motor.reset()

    def _suspend_hardware(self):
        self.agv.lift_motor.stop()

    def _prepare_auto_pre_timing(self):
        start = self.agv.lift_real_pos
        target = self.agv._effective_lift_target(self.height)
        estimated = self.agv._estimate_auto_pre_position_time(
            start, target, ConfigParams.lift_motor_speed, ConfigParams.lift_motor_name
        )
        self._set_auto_pre_timing("lift", estimated, start, target, "m")


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

    def _suspend_hardware(self):
        self.agv.lift_motor.stop()

    def _prepare_auto_pre_timing(self):
        start = self.agv.lift_real_pos
        target = ConfigParams.safe_lift_height
        estimated = self.agv._estimate_auto_pre_position_time(
            start, target, ConfigParams.lift_motor_speed, ConfigParams.lift_motor_name
        )
        self._set_auto_pre_timing("lift", estimated, start, target, "m")


class RotateAction(BaseAction):
    def __init__(self, agv, pos, max_speed=None, action_name="Rotate"):
        super().__init__(action_name)
        self.agv = agv
        self.pos = pos
        self.max_speed = max_speed

    def run(self, m):
        super().run(m)
        if abs(self.pos) > abs(ConfigParams.max_rotate_angle / 180 * math.pi):
            Navigation.setTaskError("RotateAngleExceeded", _TR(f"Rotate angle {self.pos / math.pi * 180} exceeds upper limit {ConfigParams.max_rotate_angle}. Check if box is tilted or QR code is damaged"))
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.stretch_real_pos > ConfigParams.safe_stretch_length:
            Navigation.setTaskError("StretchNotZeroed",_TR(f"Stretch mechanism not zeroed, cannot perform lift/rotate. Please zero first"))
            self.action_status = ActionStatus.FAILED
            return
        speed = self.max_speed if self.max_speed is not None else ConfigParams.rotate_motor_speed
        if self.agv.container_robot.rotate(self.agv.rotate_motor, self.pos, speed):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        self.agv.rotate_motor.reset()

    def _suspend_hardware(self):
        self.agv.rotate_motor.stop()

    def _prepare_auto_pre_timing(self):
        start = self.agv.rotate_real_pos
        speed = self.max_speed if self.max_speed is not None else ConfigParams.rotate_motor_speed
        estimated = self.agv._estimate_auto_pre_position_time(
            start, self.pos, speed, ConfigParams.rotate_motor_name
        )
        self._set_auto_pre_timing("rotate", estimated, start, self.pos, "rad")


class StretchAction(BaseAction):
    def __init__(self, agv, length, action_name="Stretch", dynamic=False):
        super().__init__(action_name)
        self.agv = agv
        self.length = length
        # dynamic=True: 运行时(而非构建时)从 agv.stretch_length 取长度。
        # 取/放货伸出长度由 RecAdjust 在运行时算出并写到 agv.stretch_length，
        # 而整个 action 队列是提前构建的，构建时该值还是 0，必须延迟到运行时再读。
        self.dynamic = dynamic

    def run(self, m):
        super().run(m)
        if self.dynamic:
            self.length = self.agv.stretch_length
        temp_motor_speed = ConfigParams.stretch_motor_speed
        if ConfigParams.max_stretch_length < self.length < ConfigParams.max_stretch_length + 0.1:
            Navigation.setTaskError("StretchLengthExceeded", _TR(f"Stretch length {self.length} exceeds upper limit{ConfigParams.max_stretch_length}. Check if goods are too far from robot！"))
            self.length = ConfigParams.max_stretch_length
        elif self.length > ConfigParams.max_stretch_length + 0.1:
            Navigation.setTaskError("StretchLengthExceeded", _TR(f"Stretch length {self.length} exceeds upper limit{ConfigParams.max_stretch_length}. Check if goods are too far from robot！！！"))
            self.action_status = ActionStatus.FAILED
            return
        if self.length > 0.1 and self.agv.stretch_real_pos > self.length * 0.6:
            temp_motor_speed = ConfigParams.stretch_motor_speed * 0.6
        if self.agv.container_robot.stretch(self.agv.stretch_motor, self.length, temp_motor_speed):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()
        self.agv.stretch_motor.reset()

    def _suspend_hardware(self):
        self.agv.stretch_motor.stop()

    def _prepare_auto_pre_timing(self):
        start = self.agv.stretch_real_pos
        target = self.agv.stretch_length if self.dynamic else self.length
        estimated = self.agv._estimate_auto_pre_position_time(
            start, target, ConfigParams.stretch_motor_speed, ConfigParams.stretch_motor_name
        )
        self._set_auto_pre_timing("stretch", estimated, start, target, "m")


class FingerAction(BaseAction):
    def __init__(self, agv, pos, action_name="Finger"):
        super().__init__(action_name)
        self.agv = agv
        self.pos = pos
        self._motor_started = False
        self.overlimit_alarm = False  # 超限光电报错标志，用于障碍物消除后自动清错

    def run(self, m):
        super().run(m)
        if is_simulation():
            self.agv.left_finger_real_pos = self.pos
            self.agv.right_finger_real_pos = self.pos
            self.action_status = ActionStatus.FINISHED
            return
        if not ConfigParams.has_finger_motor:
            Navigation.setDeviceError("FingerMotorNotConfig",
                _TR(f"fingerMotor not configured in device model. "
                f"Please add two fingerMotor entries under Model-000.moduleType.cartonTransferUnit.fingerMotor"))
            self.action_status = ActionStatus.FAILED
            return
        # 关闭手指(pos==0)前：超限光电防呆——可恢复告警而非直接失败。
        # 障碍物在位时持续告警并刷新防卡死计时，障碍消除后自动清错继续合指抓取。
        if self.pos == 0 and not self._motor_started:
            if Di.getDi(ConfigParams.overlimit_detect_di):
                Navigation.setTaskError("StretchObstacle", _TR(
                    f"Fork overlimit photoelectric sensor detected obstacle. Push the box manually to clear the overlimit, or increase stretch compensation"))
                self.overlimit_alarm = True
                # 刷新防卡死计时, 避免清障耗时超过 3s 被下方超时守卫误判为失败
                self.start_time = time.time()
                return
            if self.overlimit_alarm:
                Navigation.clearTaskError("StretchObstacle")
                self.overlimit_alarm = False
                Trace.log("超限光电障碍物已消除，自动清除告警，继续合指抓取", name=f"{MOD}.motor")
        if time.time() - self.start_time > 3:
            Navigation.setTaskError("FingerTimeout", _TR(f"Finger control timeout. Check if finger is stuck or photoelectric sensor works"))
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
                # 关闭手指：反转，到 downReachDI 停止 (超限防呆已在上方处理)
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

    def _suspend_hardware(self):
        if is_simulation() or not ConfigParams.has_finger_motor:
            return
        self._stop_finger()
        self._motor_started = False

    def reset(self):
        super().reset()
        self._motor_started = False
        self.overlimit_alarm = False

    def _prepare_auto_pre_timing(self):
        start = [self.agv.left_finger_real_pos, self.agv.right_finger_real_pos]
        self._set_auto_pre_timing(
            "finger", AUTO_PRE_FINGER_BUDGET, start, self.pos, "position"
        )


class CheckFingerOpenAction(BaseAction):
    """检查拨指是否已打开，未打开则报错"""
    def __init__(self, agv, action_name="CheckFingerOpen"):
        super().__init__(action_name)
        self.agv = agv

    def run(self, m):
        super().run(m)
        if is_simulation():
            finger_open = (
                self.agv.left_finger_real_pos == 1
                and self.agv.right_finger_real_pos == 1
            )
        else:
            finger_open = (
                Di.getDi(ConfigParams.left_finger_up_di)
                and Di.getDi(ConfigParams.right_finger_up_di)
            )
        if finger_open:
            self.action_status = ActionStatus.FINISHED
        else:
            Navigation.setTaskError("FingerNotOpen", _TR(f"Finger not open, stretch cancelled. Check finger and photoelectric sensor"))
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
        if is_simulation():
            simulation_result = {
                "x": 0.5,
                "y": 0.0,
                "z": 0.0,
                "yaw": math.pi,
                "objectMessage": self.agv.goods_id,
            }
            self.agv.rec_adjust.rec.result = simulation_result
            self.agv.rec_adjust.rec.action_status = ActionStatus.FINISHED
            self.agv.rec_adjust.run(self.agv)
            if self.agv.rec_adjust.action_status is ActionStatus.FINISHED:
                self.action_status = ActionStatus.FINISHED
                Trace.log(
                    f"Simulation RecAdjust finished with result={simulation_result}, "
                    f"stretchLength={self.agv.stretch_length}",
                    name=f"{MOD}.rec",
                )
            elif self.agv.rec_adjust.action_status is ActionStatus.FAILED:
                self.action_status = ActionStatus.FAILED
            return
        retry_target = getattr(self.agv.rec_adjust, "retry_rotate_target", None)
        if retry_target is not None:
            if not self.agv.rotate(retry_target, max_speed=0.3):
                return
            self.agv.rec_adjust.retry_rotate_target = None
            self.agv.rec_adjust.action_status = ActionStatus.RUNNING
            self.agv.reset_motor_settle()
        if getattr(self.agv.rec_adjust, "prepare_recognition", False):
            # 每次识别前确认机构停稳；补光灯只在本次动作首次识别前开启。
            if not self.agv.wait_motors_settled(tag=f"rec_adjust round {self.agv.rec_adjust.adjust_count}"):
                return
            if not self.light_started:
                self.agv.reset_motor_settle()
                Do.setDo(self.agv.fill_light_do, True)
                self.light_started = True
                self.start_time = time.time()  # 首次开灯时起算补光延时
                self.agv.rec_adjust.prepare_recognition = False
                return
            self.agv.rec_adjust.prepare_recognition = False
        if (self.light_started
                and time.time() - self.start_time < ConfigParams.light_delay_time):
            return
        if self.agv.rec_adjust.action_status is ActionStatus.FINISHED:
            Do.setDo(self.agv.fill_light_do, False)
            self.action_status = ActionStatus.FINISHED
        elif self.agv.rec_adjust.action_status is ActionStatus.FAILED:
            self.action_status = ActionStatus.FAILED
        else:
            self.agv.rec_adjust.run(self.agv)

    def reset(self):
        super().reset()
        self.light_started = False


class RecBarcodeAction(BaseAction):
    """识别一维码并验证。识别中不计数, 连续识别失败超上限报错"""
    def __init__(self, agv, action_name="RecBarcode"):
        super().__init__(action_name)
        self.agv = agv
        self.light_on = False
        self.rec_started = False
        self.rec_fail_times = 0       # 一维码连续识别失败计数
        self.max_rec_fail_times = 10  # 一维码连续识别失败上限, 超过则报错

    @staticmethod
    def _extract_barcode(reco):
        """从识别结果中提取一维码内容（字段名做兜底链）"""
        bar_code = reco.get("barCode", "") or reco.get("objectMessage", "")
        if not bar_code:
            bar_code = reco.get("robotResult", {}).get("objectMessage", "")
        return bar_code

    def run(self, m):
        super().run(m)
        if is_simulation():
            self.agv.report_info["barCode"] = self.agv.goods_id
            self.action_status = ActionStatus.FINISHED
            Trace.log(
                f"Simulation barcode recognition finished: {self.agv.goods_id}",
                name=f"{MOD}.rec",
            )
            return
        if not self.light_on:
            Do.setDo(self.agv.fill_light_do, True)
            if Do.getDo(self.agv.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.light_on = True
            return
        if not self.rec_started:
            Recognize.resetRec()
            Recognize.doRec(ConfigParams.barcode_file, "", "")
            self.rec_started = True
            return

        rec_status = Recognize.getRecStatus()
        if rec_status == 2:  # 识别成功
            bar_code = ""
            rec_results = Recognize.getRecResults()
            reco_list = rec_results.get("recoList", [])
            if reco_list:
                bar_code = self._extract_barcode(reco_list[0])
            Recognize.resetRec()
            Do.setDo(self.agv.fill_light_do, False)
            if bar_code != self.agv.goods_id:
                Navigation.setTaskError("GoodsIdMismatch", _TR(f"Goods ID mismatch between task command  {self.agv.goods_id} and recognition result {bar_code}"))
                self.action_status = ActionStatus.FAILED
            else:
                self.agv.report_info["barCode"] = bar_code
                self.action_status = ActionStatus.FINISHED
        elif rec_status == 3 or rec_status == -1:  # 识别失败, 计数并判断是否超限
            if Timer.delay(0.05):
                self.rec_fail_times += 1
                if self.rec_fail_times > self.max_rec_fail_times:
                    Do.setDo(self.agv.fill_light_do, False)
                    Navigation.setTaskError("RecBarcodeFailed", _TR(
                        f"Barcode recognition failed {self.max_rec_fail_times} times in a row. Check if barcode is damaged, camera is aligned and recognition file ({ConfigParams.barcode_file}) is correct"))
                    self.action_status = ActionStatus.FAILED
                    self.agv.report_info["barCode"] = "None"
                    return
                Recognize.resetRec()
                Recognize.doRec(ConfigParams.barcode_file, "", "")
            self.agv.report_info["barCode"] = "None"
        else:  # 识别中: 继续轮询, 不计数
            self.agv.report_info["barCode"] = "None"

    def reset(self):
        super().reset()
        self.light_on = False
        self.rec_started = False
        self.rec_fail_times = 0



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
        if self.container_id == "999":
            _clear_pending_fork_store()
        self.action_status = ActionStatus.FINISHED

    def reset(self):
        super().reset()


class ShelfOccupiedFailAction(BaseAction):
    """货架有货异常恢复的末步：料箱已放回背篓后报错并置 FAILED，提示人工核查。
    与取货对称(原背篓→999→原背篓)，数据已由前置 Unbind/Bind 动作恢复。"""
    def __init__(self, agv, recovery_c, action_name="ShelfOccupiedFail"):
        super().__init__(action_name)
        self.agv = agv
        self.recovery_c = recovery_c

    def run(self, m):
        super().run(m)
        Navigation.setTaskError("ShelfHasGoods", _TR(
            f"Goods detected on shelf, box has been returned to backpack slot {int(self.recovery_c) + 1}. Verify shelf and task data manually"))
        self.action_status = ActionStatus.FAILED

    def reset(self):
        super().reset()


class CheckGoodsDiAction(BaseAction):
    """检查货叉光电并绑定容器；光电未触发说明取货为空，报错"""
    def __init__(self, agv, action_name="CheckGoodsDi"):
        super().__init__(action_name)
        self.agv = agv

    def run(self, m):
        super().run(m)
        if is_simulation():
            Container.bindContainer("999", self.agv.goods_id, "")
            Trace.log(
                f"Simulation goods detection: bind goods {self.agv.goods_id} to fork 999",
                name=f"{MOD}.action",
            )
        elif Di.getDi(ConfigParams.goods_check_di):
            Container.bindContainer("999", self.agv.goods_id, "")
        else:
            Navigation.setTaskError("LoadPickFailed", _TR(
                f"Fork retracted but goods photoelectric not triggered, goods {self.agv.goods_id} may not be picked. Manual check required"))
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.operation == "load":
            _remember_pending_fork_store(
                self.agv.goods_id, self.agv.cur_c, self.agv.skip_safe_height
            )
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
        if is_simulation():
            goods_id = Container.getGoodsByContainer(self.agv.cur_c)
            Container.bindContainer("999", goods_id, "")
            Container.unbindContainer(self.agv.cur_c)
            Trace.log(
                f"Simulation backpack pick: move goods {goods_id} from {self.agv.cur_c} to fork 999",
                name=f"{MOD}.action",
            )
        elif Di.getDi(ConfigParams.goods_check_di):
            goods_id = Container.getGoodsByContainer(self.agv.cur_c)
            Container.bindContainer("999", goods_id, "")
            Container.unbindContainer(self.agv.cur_c)
        else:
            Navigation.setTaskError("BackpackPickFailed", _TR("Failed to pick from backpack, fork photoelectric did not detect goods"))
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
        if is_simulation():
            self.agv.shelf_occupied = False
            self.agv.report_info["recBoxSimulation"] = {"hasGoods": False}
            self.action_status = ActionStatus.FINISHED
            Trace.log("Simulation shelf check: target shelf is empty", name=f"{MOD}.rec")
            return
        if not self.light_started:
            # 识别前先等机构停稳, 再开补光灯, 防止抖动污染识别
            if not self.agv.wait_motors_settled(tag="rec_box_check"):
                return
            self.agv.reset_motor_settle()
            self.agv.rec_box.action_status = ActionStatus.RUNNING
            self.agv.rec_box.is_error = True
            Do.setDo(self.agv.fill_light_do, True)
            self.light_started = True
        if not self.light_ready:
            if Do.getDo(self.agv.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.light_ready = True
            return
        if self.agv.rec_box.action_status is ActionStatus.FINISHED:
            self.agv.rec_box.reset()
            self.agv.rec_box.is_error = None
            Do.setDo(self.agv.fill_light_do, False)
            if self.agv.rec_box.hasGoods and not self.agv.rec_box.goods_out_dist:
                # 货架已有货: 触发异常恢复(把料箱放回背篓), 此处不直接报错,
                # 由主流程 run() 检测 shelf_occupied 后构建恢复队列接管
                self.agv.shelf_occupied = True
                self.fail_reason = "shelf occupied"
                Trace.log("rec_box check: 检测到货架已有货物，触发异常恢复", name=f"{MOD}.action")
                self.action_status = ActionStatus.FAILED
            else:
                self.action_status = ActionStatus.FINISHED
        elif self.agv.rec_box.action_status is ActionStatus.FAILED:
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
            Navigation.setTaskError("RecFailed",_TR(f"Recognition failed after max retries{self.max_rec_times}. Check if QR code is damaged or camera is clear"))
            self.action_status = ActionStatus.FAILED
            return
        if self.agv.rec.action_status == ActionStatus.FINISHED:
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
        self.suspend_start_time = None
        self._last_safe_move_log = None
        self.business_timeout_started = False
        self.auto_pre_enabled = False
        self.auto_pre_stage = 2
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
        self.skip_safe_height = False  # 动作完成后跳过下降到安全高度

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
        self.calib_step = [False] * 3
        self.yaw_adjust = 0
        self.rec_res = None
        self.rec_id = None
        self.rec_box_lift = None
        self.finger_open_start = False
        self.pre_finger = None
        # 识别前等机构停稳的计时起点(None=未开始/被打断)
        self.motor_settle_start = None
        # 停稳判断的上次打印状态(避免每帧刷屏)
        self._settle_print_state = None
        # 货架有货异常恢复状态
        self.shelf_occupied = False   # rec_box 识别到货架已有货物
        self.recovery_built = False   # 恢复队列是否已构建, 防止重复构建
        self.recovery_c = None        # 恢复时把料箱放回的目标背篓

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
        # safeMoveCheck 专用归零队列(与任务 action_task 隔离, 复用同一组归零动作定义)
        self.safe_zero_task = ActionTask(mod=MOD)

    def init_args(self, args):
        """初始化任务参数"""
        self.script_args = args or Module.getTaskArgs()
        if args:
            self.operation = self.script_args.get("operation", None)
            self.auto_pre_enabled = Module.getAutoPre()
            self.auto_pre_stage = Module.getTaskParams("stage", 2)
            if self.auto_pre_enabled and self.operation not in ("load", "unload"):
                Navigation.setTaskError(
                    "AutoPreUnsupported",
                    _TR(f"AutoPre only supports load/unload, operation: {self.operation}"),
                )
                self.status = ScriptStatus.FAILED
                return
            if self.auto_pre_enabled and self.auto_pre_stage != 2:
                Navigation.setTaskError(
                    "AutoPreStageUnsupported",
                    _TR(f"CTU AutoPre only supports script stage 2, stage: {self.auto_pre_stage}"),
                )
                self.status = ScriptStatus.FAILED
                return
            self.goods_id = self.script_args.get("goodsName", "")
            self.self_position = self.script_args.get("container", self.self_position)
            self.self_position = str(self.self_position) if self.self_position is not None else self.self_position
            # AutoPre TASK 已由 MF 提前下发，参数以 Module 当前 TASK 为准；此时没有可查询的导航 moveTask。
            if not self.auto_pre_enabled:
                self.update_move_task_params()
            # 重置识别前停稳计时 & 货架有货异常恢复状态
            self.motor_settle_start = None
            self.shelf_occupied = False
            self.recovery_built = False
            self.recovery_c = None
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
            self.load_height = self.script_args.get("loadHeight", ConfigParams.rec_offz_box)
            self.unload_height = self.script_args.get("unloadHeight", ConfigParams.rec_offz_shelf)
            self.skip_safe_height = "skipSafeHeight" in self.script_args and self.script_args.get("skipSafeHeight")
            container_num = ConfigParams.get_container_count()
            if isinstance(container_num, int) and container_num > 0:
                Container.initContainer(container_num - 1, "999")
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

            if is_simulation():
                # 仿真货物状态由取/放货 Action 维护，不使用物理 DI 校正。
                pass
            elif ConfigParams.goods_check_di != "":
                if self.stretch_real_pos < 0.05:
                    if (Di.getDi(ConfigParams.goods_check_di) and not Container.hasGoods("999")
                            and self.operation not in RECOVERY_OPERATIONS):
                        Navigation.setTaskError("ForkHasGoods", _TR(f"Fork (slot 999) already has goods, cannot execute current task. Verify data"))
                        self.status = ScriptStatus.FAILED
                    elif not Di.getDi(ConfigParams.goods_check_di):
                        Container.unbindContainer("999")
                        _clear_pending_fork_store()
            else:
                Navigation.setTaskError("GoodsCheckDiError", _TR(f"goodsCheckDi not configured properly in script parameters！"))
                Trace.log(f"请在脚本参数中正确配置 goodsCheckDi 参数！", name=f"{MOD}.err")
                self.status = ScriptStatus.FINISHED

            self.start_time = time.time()
            self.business_timeout_started = not self.auto_pre_enabled
            self.status = ScriptStatus.RUNNING

    def start_business_timeout(self):
        if self.business_timeout_started:
            return
        self.start_time = time.time()
        self.business_timeout_started = True
        Trace.log("AutoPre physical actions started; business timeout started", name=f"{MOD}.autoPre")

    def run(self):
        """分发、执行任务"""
        self.status = ScriptStatus.RUNNING
        self.counter += 1
        self.update_report_info()
        self.report_info["getCountRun"] = self.counter

        # 根据货叉货物检测光电更新货叉有无货信息；仿真由 Action 维护货物数据。
        if is_simulation():
            pass
        elif ConfigParams.goods_check_di != "":
            if self.stretch_real_pos < 0.05:  # 手臂未伸出状态下检测有效
                # 队列执行途中(取/放货)999 的绑定由动作队列负责,此时“有货但数据为空”是
                # 收叉与绑定之间的正常瞬态,不应拦截;仅在空闲/任务起始态才判为数据异常。
                queue_running = self.action_task.status in (ActionStatus.RUNNING, ActionStatus.SUSPENDED)
                if (Di.getDi(ConfigParams.goods_check_di) and not Container.hasGoods("999")
                        and self.operation not in RECOVERY_OPERATIONS and not queue_running):
                    Navigation.setTaskError("ForkHasGoods",
                        _TR(f"Fork photoelectric detected goods on fork, but data shows no goods, manual verification required"))
                    self.status = ScriptStatus.FAILED
                elif not Di.getDi(ConfigParams.goods_check_di):
                    Container.unbindContainer("999")
                    _clear_pending_fork_store()
                    self.containers = Container.getContainers()
        else:
            Navigation.setTaskError("GoodsCheckDiError",
                _TR(f"Please configure goods_check_di parameter properly in script parameters!"))
            self.status = ScriptStatus.FINISHED

        self.check_motor_emc()
        if self.enable_motor and not self.motor_calib_state:
            self.motor_calib()

        if self.business_timeout_started and time.time() - self.start_time > ConfigParams.timeout:
            Navigation.setTaskError("ScriptTimeout", _TR(f"Script task execution timeout. Please re-issue the task！"))
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
                    Navigation.setTaskError("InputParamError", _TR(f"Invalid script input parameters"))
                    self.status = ScriptStatus.FAILED

                self._drive_queue()
                if self.action_status == ActionStatus.FINISHED:
                    self.status = ScriptStatus.FINISHED
                elif self.action_status == ActionStatus.FAILED:
                    if self.shelf_occupied and not self.recovery_built:
                        # 货架有货: 不直接失败, 构建"把料箱放回背篓"恢复队列接管
                        self._build_recovery_actions()
                    else:
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
            Trace.log(
                {
                    "event": "scriptFinished",
                    "taskId": Module.getTaskId(),
                    "status": self.status.name.lower(),
                    "operation": self.operation,
                    "goodsName": self.goods_id,
                    "action": self.current_action.action_type if self.current_action else "",
                    "runningSeconds": round(time.time() - self.start_time, 3),
                    "position": self.report_info.get("currentPos", {}),
                },
                output_time=True,
                name=MOD,
            )
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
    def _make_zero_actions(self, zero_height=0.5):
        """归零动作定义（唯一来源）：手指张开→伸缩归0→旋转归0→升降到位。
        仅返回动作列表，不触碰 action_list/operation_init，供任务 zero 与 safeMoveCheck 共用。"""
        actions = []
        if not Container.hasGoods("999"):
            actions.append(FingerAction(self, 1, "zero_finger_open"))
        actions.append(StretchAction(self, 0, "zero_stretch"))
        actions.append(RotateAction(self, 0, action_name="zero_rotate"))
        actions.append(LiftAction(self, zero_height, "zero_lift"))
        return actions

    def _build_zero_actions(self, zero_height=0.5):
        if self.operation_init:
            return
        self.operation_init = True
        self.action_list = self._make_zero_actions(zero_height)

    @staticmethod
    def _estimate_auto_pre_position_time(start_pos, target_pos, speed, motor_name=None):
        values = (start_pos, target_pos, speed)
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
            return None
        if speed <= 0:
            return None
        estimator = getattr(Motor, "estimatePositionMoveDuration", None)
        if callable(estimator) and motor_name:
            try:
                duration = estimator(
                    motor_name,
                    target_pos,
                    startPos=start_pos,
                    maxSpeed=speed,
                )
                if duration is not None and math.isfinite(duration) and duration >= 0:
                    return duration
            except Exception as error:
                Trace.log(
                    f"Motor duration estimate failed for {motor_name}: {error}; use CTU estimate",
                    name=f"{MOD}.autoPre",
                )
        return abs(target_pos - start_pos) / speed + AUTO_PRE_POSITION_SETTLE_TIME

    @staticmethod
    def _max_auto_pre_times(*durations):
        if not durations or any(
                duration is None or not math.isfinite(duration) for duration in durations):
            return None
        return max(durations)

    @staticmethod
    def _effective_lift_target(target):
        return max(float(target), ConfigParams.min_lift_height)

    def _validate_auto_pre_lift_targets(self, targets):
        for action_name, target in targets:
            try:
                effective_target = self._effective_lift_target(target)
            except (TypeError, ValueError):
                effective_target = float("nan")
            if not math.isfinite(effective_target):
                Navigation.setTaskError(
                    "AutoPreLiftHeightInvalid",
                    _TR(f"AutoPre lift target is invalid: {action_name}={target}"),
                )
                self.status = ScriptStatus.FAILED
                return False
            if effective_target > ConfigParams.safe_lift_height:
                Navigation.setTaskError(
                    "AutoPreLiftHeightUnsafe",
                    _TR(
                        f"AutoPre lift target {action_name}={effective_target} exceeds "
                        f"safeLiftHeight={ConfigParams.safe_lift_height}"
                    ),
                )
                self.status = ScriptStatus.FAILED
                return False
        return True

    def _make_auto_pre_sequence(self, pre_actions, required_time):
        if required_time is None or not math.isfinite(required_time):
            Navigation.setTaskError(
                "AutoPreTimeEstimateFailed",
                _TR("Unable to estimate CTU AutoPre action duration. Check motor speed configuration"),
            )
            self.status = ScriptStatus.FAILED
            return None
        Trace.log(
            f"AutoPre build operation={self.operation}, requiredTime={required_time:.3f}s, "
            f"preActions={len(pre_actions)}",
            name=f"{MOD}.autoPre",
        )
        return CtuAutoPreSequenceAction(
            pre_actions=pre_actions,
            required_time=required_time,
            advance_time=AUTO_PRE_ADVANCE_TIME,
            station="targetStation",
            include_rotation=True,
            must_stop_at_pre_station=False,
        )

    def _select_pending_store_container(self, pending_store, excluded=()):
        excluded = {str(container_id) for container_id in excluded if container_id is not None}
        self.containers = Container.getContainers()
        empty_containers = [
            str(container["containerId"])
            for container in self.containers
            if str(container["containerId"]) != "999"
            and str(container["containerId"]) not in excluded
            and not container["hasGoods"]
        ]
        preferred = pending_store.get("preferredContainer")
        preferred = str(preferred) if preferred is not None else None
        if preferred in empty_containers:
            return preferred
        return empty_containers[0] if empty_containers else None

    def _make_pending_store_actions(self, pending_store, container_id):
        goods_id = pending_store["goodsName"]
        actions = [
            ParallelAction([
                RotateAction(self, 0, action_name="deferred_store_rotate_zero"),
                LiftAction(self, ConfigParams.high[int(container_id)], "deferred_store_lift_container"),
            ], "deferred_store_parallel_to_container"),
            StretchAction(self, ConfigParams.stretch_self_length, "deferred_store_stretch_self"),
            FingerAction(self, 1, "deferred_store_finger_open"),
            StretchAction(self, 0, "deferred_store_stretch_retract"),
            FingerAction(self, 0, "deferred_store_finger_close"),
        ]
        if not pending_store.get("skipSafeHeight", False):
            actions.append(LiftSafeAction(self, "deferred_store_lift_safe"))
        actions.extend([
            UnbindContainerAction("999", "deferred_store_unbind_999"),
            BindContainerAction(container_id, goods_id, "", "deferred_store_bind_container"),
        ])
        Trace.log(
            f"deferred store goods {goods_id} from fork 999 to container {container_id}",
            name=f"{MOD}.autoPre",
        )
        return actions

    def _estimate_pending_store_time(
            self, pending_store, container_id, lift_start, rotate_start, stretch_start):
        container_lift = self._effective_lift_target(ConfigParams.high[int(container_id)])
        initial_budget = self._max_auto_pre_times(
            self._estimate_auto_pre_position_time(
                lift_start, container_lift, ConfigParams.lift_motor_speed,
                ConfigParams.lift_motor_name,
            ),
            self._estimate_auto_pre_position_time(
                rotate_start, 0.0, ConfigParams.rotate_motor_speed,
                ConfigParams.rotate_motor_name,
            ),
        )
        stretch_out_budget = self._estimate_auto_pre_position_time(
            stretch_start, ConfigParams.stretch_self_length,
            ConfigParams.stretch_motor_speed, ConfigParams.stretch_motor_name,
        )
        stretch_back_budget = self._estimate_auto_pre_position_time(
            ConfigParams.stretch_self_length, 0.0,
            ConfigParams.stretch_motor_speed, ConfigParams.stretch_motor_name,
        )
        safe_budget = 0.0
        end_lift = container_lift
        if (not pending_store.get("skipSafeHeight", False)
                and container_lift > ConfigParams.safe_lift_height):
            end_lift = ConfigParams.safe_lift_height
            safe_budget = self._estimate_auto_pre_position_time(
                container_lift, end_lift, ConfigParams.lift_motor_speed,
                ConfigParams.lift_motor_name,
            )
        budgets = (initial_budget, stretch_out_budget, stretch_back_budget, safe_budget)
        if any(budget is None for budget in budgets):
            return None, end_lift
        required_time = (
            initial_budget + stretch_out_budget + AUTO_PRE_FINGER_BUDGET
            + stretch_back_budget + AUTO_PRE_FINGER_BUDGET + safe_budget
        )
        return required_time, end_lift

    def _build_load_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        Trace.log(f"----- building load actions {self.goods_id} ------", name=f"{MOD}.action")

        pending_store = _get_pending_fork_store()
        if self.goods_id and pending_store and pending_store["goodsName"] == self.goods_id:
            if self.self_position is not None:
                _remember_pending_fork_store(
                    self.goods_id, self.self_position, self.skip_safe_height
                )
            Trace.log(
                f"load goods {self.goods_id} already carried on fork 999; keep direct-carry state",
                name=f"{MOD}.autoPre",
            )
            if self.auto_pre_enabled:
                auto_pre_action = self._make_auto_pre_sequence([], 0.0)
                if auto_pre_action is not None:
                    self.action_list = [auto_pre_action]
            else:
                self.action_status = ActionStatus.FINISHED
            return

        if (self.goods_id and Container.goodsExist(self.goods_id) and
                Container.getContainerByGoods(self.goods_id) != "999"):
            Navigation.setTaskError("GoodsAlreadyExists", _TR(f"Goods {self.goods_id} already exist. Check for duplicate task"))
            self.status = ScriptStatus.FAILED
            return

        pending_actions = []
        pending_budget = 0.0
        pending_container = None
        pre_lift_start = self.lift_real_pos
        pre_rotate_start = self.rotate_real_pos
        if pending_store:
            excluded = [self.self_position] if self.self_position is not None else []
            pending_container = self._select_pending_store_container(
                pending_store, excluded
            )
            if pending_container is None:
                Navigation.setTaskError(
                    "PendingStoreNoSlot",
                    _TR(f"Fork carries goods {pending_store['goodsName']} and no empty backpack slot is available"),
                )
                self.status = ScriptStatus.FAILED
                return
            if self.auto_pre_enabled and not self._validate_auto_pre_lift_targets([
                ("deferred_store_lift_container", ConfigParams.high[int(pending_container)])
            ]):
                return
            pending_actions = self._make_pending_store_actions(
                pending_store, pending_container
            )
            if self.auto_pre_enabled:
                pending_budget, pre_lift_start = self._estimate_pending_store_time(
                    pending_store, pending_container, self.lift_real_pos,
                    self.rotate_real_pos, self.stretch_real_pos,
                )
                pre_rotate_start = 0.0

        if not self.cur_c:
            if self.self_position:
                occupied_by_pending = self.self_position == "999" and pending_store
                if Container.hasGoods(self.self_position) and not occupied_by_pending:
                    Navigation.setTaskError("BackpackSlotFull", _TR(f"Backpack slot {int(self.self_position) + 1} (No.{self.self_position}) already has goods, cannot continue loading. Please verify task data and backpack data！"))
                    self.status = ScriptStatus.FAILED
                    return
                self.cur_c = self.self_position
            else:
                self.cur_c = self.search_operable_container(
                    'load', excluded=[pending_container] if pending_container else []
                )
            Trace.log(f"load begin: {json.dumps(self.containers)}", name=f"{MOD}.action")
            if self.cur_c is None:
                Navigation.setTaskError("AllBackpackFull", _TR(f"All backpack slots are full, cannot load more goods！"))
                self.status = ScriptStatus.FAILED
                return

        pre_actions = list(pending_actions) if self.auto_pre_enabled else []
        formal_actions = [] if self.auto_pre_enabled else list(pending_actions)
        initial_action = ParallelAction([
            FingerAction(self, 1, "load_finger_open"),
            RotateAction(self, self.rotate_pos, action_name="load_rotate"),
            LiftAction(self, self.lift_height, "load_lift"),
        ], "load_parallel_init")
        if self.auto_pre_enabled:
            lift_targets = [("load_lift", self.lift_height)]
            if self.barcode_height is not None:
                lift_targets.append(("load_lift_barcode", self.barcode_height))
            if not self._validate_auto_pre_lift_targets(lift_targets):
                return
            pre_actions.append(initial_action)
        else:
            formal_actions.append(initial_action)

        if self.barcode_height is not None:
            barcode_lift = LiftAction(self, self.barcode_height, "load_lift_barcode")
            if self.auto_pre_enabled:
                pre_actions.append(barcode_lift)
            else:
                formal_actions.append(barcode_lift)
            formal_actions.append(RecBarcodeAction(self, "load_rec_barcode"))
        if self.rec_adjust is not None:
            formal_actions.append(RecAdjustAction(self, "load_rec_adjust"))
        formal_actions.append(LiftAction(self, self.lift_height + self.load_height, "load_lift_pick"))
        formal_actions.append(CheckFingerOpenAction(self, "load_check_finger"))
        formal_actions.append(StretchAction(self, self.stretch_length, "load_stretch_out", dynamic=self.is_auto_stretch))
        formal_actions.append(FingerAction(self, 0, "load_finger_close"))
        formal_actions.append(StretchAction(self, 0, "load_stretch_retract"))
        formal_actions.append(CheckGoodsDiAction(self, "load_check_goods"))
        transport_actions = [
            RotateAction(self, 0, action_name="load_transport_rotate_zero")
        ]
        if not self.skip_safe_height:
            transport_actions.append(LiftSafeAction(self, "load_transport_lift_safe"))
        formal_actions.append(ParallelAction(
            transport_actions, "load_parallel_transport_safe"
        ))

        if not self.auto_pre_enabled:
            self.action_list = formal_actions
            return

        lift_target = self._effective_lift_target(self.lift_height)
        initial_budget = self._max_auto_pre_times(
            AUTO_PRE_FINGER_BUDGET,
            self._estimate_auto_pre_position_time(
                pre_rotate_start, self.rotate_pos, ConfigParams.rotate_motor_speed,
                ConfigParams.rotate_motor_name,
            ),
            self._estimate_auto_pre_position_time(
                pre_lift_start, lift_target, ConfigParams.lift_motor_speed,
                ConfigParams.lift_motor_name,
            ),
        )
        if pending_budget is None or initial_budget is None:
            required_time = None
        else:
            required_time = pending_budget + initial_budget
        if self.barcode_height is not None and required_time is not None:
            barcode_budget = self._estimate_auto_pre_position_time(
                lift_target,
                self._effective_lift_target(self.barcode_height),
                ConfigParams.lift_motor_speed,
                ConfigParams.lift_motor_name,
            )
            required_time = None if barcode_budget is None else required_time + barcode_budget
        auto_pre_action = self._make_auto_pre_sequence(pre_actions, required_time)
        if auto_pre_action is not None:
            self.action_list = [auto_pre_action] + formal_actions

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
        goods_id = Container.getGoodsByContainer(self.cur_c) or self.goods_id
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
        actions.append(BindContainerAction("999", goods_id, "", "in_take_bind_999"))
        self.action_list = actions

    def _build_in_put_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        if not self.cur_c:
            self.check_put()
            if self.status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
                return
        goods_id = Container.getGoodsByContainer("999") or self.goods_id
        actions = []
        actions.append(ParallelAction([
            LiftAction(self, ConfigParams.high[int(self.cur_c)], "in_put_lift"),
            RotateAction(self, 0, action_name="in_put_rotate_zero"),
        ], "in_put_parallel_init"))
        actions.append(StretchAction(self, ConfigParams.stretch_self_length, "in_put_stretch_out"))
        actions.append(FingerAction(self, 1, "in_put_finger_open"))
        actions.append(StretchAction(self, 0, "in_put_stretch_retract"))
        actions.append(FingerAction(self, 0, "in_put_finger_close"))
        if not self.skip_safe_height:
            actions.append(LiftSafeAction(self, "in_put_lift_safe"))
        actions.append(UnbindContainerAction("999", "in_put_unbind_999"))
        actions.append(BindContainerAction(self.cur_c, goods_id, "", "in_put_bind_container"))
        self.action_list = actions

    def _build_ex_take_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        if Container.hasGoods("999"):
            Navigation.setTaskError("ForkHasGoods", _TR(f"Fork (slot 999) already has goods, cannot execute current task. Verify data"))
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
        actions.append(StretchAction(self, self.stretch_length, "ex_take_stretch_out", dynamic=self.is_auto_stretch))
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
        actions.append(StretchAction(self, self.stretch_length, "ex_put_stretch_out", dynamic=self.is_auto_stretch))
        actions.append(FingerAction(self, 1, "ex_put_finger_open"))
        actions.append(StretchAction(self, 0, "ex_put_stretch_retract"))
        actions.append(ParallelAction([
            RotateAction(self, 0, action_name="ex_put_rotate_zero"),
            FingerAction(self, 0, "ex_put_finger_close"),
        ], "ex_put_parallel_final"))
        if not self.skip_safe_height:
            actions.append(LiftSafeAction(self, "ex_put_lift_safe"))
        actions.append(UnbindContainerAction("999", "ex_put_unbind"))
        self.action_list = actions

    def _build_unload_actions(self):
        if self.operation_init:
            return
        self.operation_init = True
        Trace.log(f"----- building unload actions ------", name=f"{MOD}.action")

        pending_store = _get_pending_fork_store()
        if not self.cur_c:
            if pending_store and pending_store["goodsName"] == self.goods_id:
                self.cur_c = "999"
                Trace.log(
                    f"unload goods {self.goods_id} directly from fork 999; skip backpack transfer",
                    name=f"{MOD}.autoPre",
                )
            elif self.self_position:
                if Container.getGoodsByContainer(self.self_position) != self.goods_id:
                    Navigation.setTaskError("GoodsIdMismatch", _TR(f"Goods ID in backpack slot {int(self.self_position) + 1} ({self.self_position}) doesn't match task goods ID ({self.goods_id})! Verify task and backpack data!"))
                    self.status = ScriptStatus.FAILED
                    return
                if not Container.hasGoods(self.self_position):
                    Navigation.setTaskError("BackpackSlotEmpty", _TR(f"Backpack slot {int(self.self_position) + 1} ({self.self_position}) is empty, cannot unload! Verify task and backpack data!"))
                    self.status = ScriptStatus.FAILED
                    return
                self.cur_c = self.self_position
            else:
                self.cur_c = Container.getContainerByGoods(self.goods_id)
            if not self.cur_c:
                Navigation.setTaskError("GoodsNotFound", _TR(f"Goods {self.goods_id} not found in backpack, cannot unload! Verify task and backpack data!"))
                self.status = ScriptStatus.FAILED
                return
            Trace.log(f"unload begin: {json.dumps(self.containers)}", name=f"{MOD}.action")

        pending_actions = []
        pending_budget = 0.0
        pending_container = None
        pre_lift_start = self.lift_real_pos
        pre_rotate_start = self.rotate_real_pos
        pre_stretch_start = self.stretch_real_pos
        if pending_store and self.cur_c != "999":
            pending_container = self._select_pending_store_container(pending_store)
            if pending_container is None:
                Navigation.setTaskError(
                    "PendingStoreNoSlot",
                    _TR(f"Fork carries goods {pending_store['goodsName']} and no empty backpack slot is available"),
                )
                self.status = ScriptStatus.FAILED
                return
            pending_actions = self._make_pending_store_actions(
                pending_store, pending_container
            )
            if self.auto_pre_enabled:
                pending_budget, pre_lift_start = self._estimate_pending_store_time(
                    pending_store, pending_container, self.lift_real_pos,
                    self.rotate_real_pos, self.stretch_real_pos,
                )
                pre_rotate_start = 0.0
                pre_stretch_start = 0.0

        take_actions = []
        if self.cur_c != "999":
            take_actions.append(ParallelAction([
                LiftAction(self, ConfigParams.low[int(self.cur_c)], "unload_lift_container"),
                FingerAction(self, 1, "unload_finger_open_take"),
                RotateAction(self, 0, action_name="unload_rotate_zero_take"),
            ], "unload_parallel_take_init"))
            take_actions.append(StretchAction(self, ConfigParams.stretch_self_length, "unload_stretch_self"))
            take_actions.append(FingerAction(self, 0, "unload_finger_close_take"))
            take_actions.append(StretchAction(self, 0, "unload_stretch_retract_take"))
            take_actions.append(CheckGoodsDiUnloadTakeAction(self, "unload_check_goods_take"))

        target_pose_actions = []
        formal_actions = []
        if self.rec_box_lift:
            target_pose_actions.append(ParallelAction([
                RotateAction(self, self.rotate_pos, action_name="unload_rotate_rec"),
                LiftAction(self, self.rec_box_lift, "unload_lift_rec_box"),
            ], "unload_parallel_rec_box_pos"))
            if self.rec_box is not None:
                formal_actions.append(RecBoxCheckAction(self, "unload_rec_box_check"))
            formal_actions.append(LiftAction(self, self.lift_height, "unload_lift_after_rec"))
        else:
            target_pose_actions.append(ParallelAction([
                LiftAction(self, self.lift_height, "unload_lift_target"),
                RotateAction(self, self.rotate_pos, action_name="unload_rotate_target"),
            ], "unload_parallel_target"))

        if self.rec_adjust is not None:
            formal_actions.append(RecAdjustAction(self, "unload_rec_adjust"))
        formal_actions.append(LiftAction(self, self.lift_height + self.unload_height, "unload_lift_place"))
        if self.pre_finger is not None:
            formal_actions.append(ParallelAction([
                FingerAction(self, self.pre_finger, "unload_pre_finger"),
                StretchAction(self, self.stretch_length, "unload_stretch_out", dynamic=self.is_auto_stretch),
            ], "unload_parallel_stretch_finger"))
        else:
            formal_actions.append(StretchAction(self, self.stretch_length, "unload_stretch_out", dynamic=self.is_auto_stretch))
        formal_actions.append(FingerAction(self, 1, "unload_finger_open"))
        formal_actions.append(StretchAction(self, 0, "unload_stretch_retract"))
        final_actions = [
            FingerAction(self, 0, "unload_finger_close"),
            RotateAction(self, 0, action_name="unload_rotate_zero"),
        ]
        if not self.skip_safe_height:
            final_actions.append(LiftSafeAction(self, "unload_lift_safe"))
        formal_actions.append(ParallelAction(final_actions, "unload_parallel_final"))
        formal_actions.append(UnbindContainerAction("999", "unload_unbind_999"))

        if not self.auto_pre_enabled:
            self.action_list = pending_actions + take_actions + target_pose_actions + formal_actions
            return

        target_lift = self.rec_box_lift if self.rec_box_lift else self.lift_height
        lift_targets = [("unload_lift_target", target_lift)]
        if pending_container is not None:
            lift_targets.insert(0, (
                "deferred_store_lift_container",
                ConfigParams.high[int(pending_container)],
            ))
        if self.cur_c != "999":
            lift_targets.append(("unload_lift_container", ConfigParams.low[int(self.cur_c)]))
        if not self._validate_auto_pre_lift_targets(lift_targets):
            return

        required_time = pending_budget
        lift_start = pre_lift_start
        rotate_start = pre_rotate_start
        if self.cur_c != "999":
            container_lift = self._effective_lift_target(ConfigParams.low[int(self.cur_c)])
            initial_budget = self._max_auto_pre_times(
                self._estimate_auto_pre_position_time(
                    lift_start, container_lift, ConfigParams.lift_motor_speed,
                    ConfigParams.lift_motor_name,
                ),
                AUTO_PRE_FINGER_BUDGET,
                self._estimate_auto_pre_position_time(
                    rotate_start, 0.0, ConfigParams.rotate_motor_speed,
                    ConfigParams.rotate_motor_name,
                ),
            )
            stretch_out_budget = self._estimate_auto_pre_position_time(
                pre_stretch_start,
                ConfigParams.stretch_self_length,
                ConfigParams.stretch_motor_speed,
                ConfigParams.stretch_motor_name,
            )
            stretch_back_budget = self._estimate_auto_pre_position_time(
                ConfigParams.stretch_self_length, 0.0, ConfigParams.stretch_motor_speed,
                ConfigParams.stretch_motor_name,
            )
            budgets = (initial_budget, stretch_out_budget, stretch_back_budget)
            if required_time is None or any(budget is None for budget in budgets):
                required_time = None
            else:
                required_time += (
                    initial_budget + stretch_out_budget + AUTO_PRE_FINGER_BUDGET
                    + stretch_back_budget + AUTO_PRE_DI_BUDGET
                )
            lift_start = container_lift
            rotate_start = 0.0

        pose_budget = self._max_auto_pre_times(
            self._estimate_auto_pre_position_time(
                lift_start,
                self._effective_lift_target(target_lift),
                ConfigParams.lift_motor_speed,
                ConfigParams.lift_motor_name,
            ),
            self._estimate_auto_pre_position_time(
                rotate_start, self.rotate_pos, ConfigParams.rotate_motor_speed,
                ConfigParams.rotate_motor_name,
            ),
        )
        if required_time is None or pose_budget is None:
            required_time = None
        else:
            required_time += pose_budget

        auto_pre_action = self._make_auto_pre_sequence(
            pending_actions + take_actions + target_pose_actions, required_time
        )
        if auto_pre_action is not None:
            self.action_list = [auto_pre_action] + formal_actions

    def _build_recovery_actions(self):
        """货架有货异常恢复: 把货叉(999)上的料箱放回背篓, 恢复数据后报错(FAILED)。
        触发时机: unload/ex_put 放货前 rec_box 识别到货架已有货物。此时料箱一定在货叉上
        (unload 已从背篓取到叉、ex_put 本就带箱)。放回目标: 原背篓(unload 从背篓取的)或空背篓。
        通过 action_task.reset()+重建队列实现分支(引擎不支持队列中途改道)。"""
        self.recovery_built = True
        self.action_task.reset()
        self.action_status = ActionStatus.RUNNING  # 清掉上条队列的 FAILED, 让恢复队列推进
        # 放回目标背篓: unload 从背篓取的放回原背篓; 货物本就在叉上(cur_c 空/999)则找空背篓
        if self.cur_c and self.cur_c != "999":
            self.recovery_c = self.cur_c
        else:
            self.recovery_c = self.search_operable_container('load')
        goods_id = Container.getGoodsByContainer("999")
        if self.recovery_c is None:
            Navigation.setTaskError("ShelfHasGoodsNoSlot", _TR(
                "Goods detected on shelf and no empty backpack slot to return the box. Manual handling required"))
            self.status = ScriptStatus.FAILED
            self.action_list = []
            return
        Trace.log(f"shelf occupied recovery: return box to slot {int(self.recovery_c) + 1}", name=f"{MOD}.action")
        # 放回背篓沿用本车"入背篓"约定(与 load/in_put 一致): 升到 high[c] → 伸出 → 松指放入 → 缩回
        actions = [
            ParallelAction([
                RotateAction(self, 0, action_name="recovery_rotate_zero"),
                LiftAction(self, ConfigParams.high[int(self.recovery_c)], "recovery_lift_container"),
            ], "recovery_parallel_to_container"),
            StretchAction(self, ConfigParams.stretch_self_length, "recovery_stretch_self"),
            FingerAction(self, 1, "recovery_finger_open"),
            StretchAction(self, 0, "recovery_stretch_retract"),
            UnbindContainerAction("999", "recovery_unbind_999"),
            BindContainerAction(self.recovery_c, goods_id, "", "recovery_bind_container"),
            ShelfOccupiedFailAction(self, self.recovery_c, "recovery_fail"),
        ]
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
            if _motor.get('key') == motor_name:
                return _motor
        return {}

    def wait_motors_settled(self, tag=""):
        """识别前等待机构机械停稳: 升降/旋转/伸缩三轴 stop 标志为真, 且累计经过
        motor_settle_delay 秒。调用方在到达识别触发点后每帧调用直到返回 True, 再开补光灯。
        @param tag: 识别来源说明(如 "load_rec_adjust round N"), 仅用于日志便于定位重识别轮次
        @return: True 表示已停稳满 motor_settle_delay 秒, False 表示尚需等待"""
        lift_info = self.get_motor_info(ConfigParams.lift_motor_name)
        rotate_info = self.get_motor_info(ConfigParams.rotate_motor_name)
        stretch_info = self.get_motor_info(ConfigParams.stretch_motor_name)
        all_stop = bool(lift_info.get("stop", False)
                        and rotate_info.get("stop", False)
                        and stretch_info.get("stop", False))
        tag = tag or ""
        # 只在跳变时打印, 避免每帧刷屏
        if self._settle_print_state != all_stop:
            self._settle_print_state = all_stop
            print(f"[DIAG][{tag}] motors all_stop={all_stop} "
                  f"(lift={lift_info.get('stop')} rotate={rotate_info.get('stop')} stretch={stretch_info.get('stop')})")
        if not all_stop:
            # 任一轴还在动, 复位计时, 等下次稳定后重新计时
            self.motor_settle_start = None
            return False
        if self.motor_settle_start is None:
            self.motor_settle_start = time.time()
            print(f"[DIAG][{tag}] motors stopped, start settle timer @ {time.time():.3f}")
            return False
        elapsed = time.time() - self.motor_settle_start
        if elapsed >= ConfigParams.motor_settle_delay:
            print(f"[DIAG][{tag}] settled after {elapsed:.3f}s (>= {ConfigParams.motor_settle_delay}s) -> proceed to recognize")
        return elapsed >= ConfigParams.motor_settle_delay

    def reset_motor_settle(self):
        """识别完成/失败后重置停稳计时, 供下一次识别使用"""
        self.motor_settle_start = None

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

    def _stop_mechanisms_for_suspend(self):
        for motor in (self.lift_motor, self.stretch_motor, self.rotate_motor):
            motor.stop()
        if ConfigParams.has_finger_motor:
            Motor.resetMotor(ConfigParams.left_finger_motor_name)
            Motor.resetMotor(ConfigParams.right_finger_motor_name)

    def _log_task_control(self, command, paused_seconds=None):
        current = self.action_task.current
        event = {
            "event": "taskControl",
            "command": command,
            "taskId": Module.getTaskId(),
            "operation": self.operation,
            "scriptStatus": self.status.name.lower(),
            "queueStatus": self.action_task.status.name.lower(),
            "action": current.action_type if current else "",
            "actionStatus": current.action_status.name.lower() if current else "",
            "lift": round(self.lift_real_pos, 3),
            "stretch": round(self.stretch_real_pos, 3),
            "rotateDeg": round(self.rotate_real_pos * 180 / math.pi, 3),
        }
        if paused_seconds is not None:
            event["pausedSeconds"] = round(paused_seconds, 3)
        Trace.log(event, output_time=True, name=f"{MOD}.control")

    def suspend(self):
        """暂停任务方法（必须）"""
        if (Module.getStatus() == ScriptStatus.RUNNING
                and self.status == ScriptStatus.RUNNING):
            self.suspend_start_time = time.time()
            self.action_task.suspend()
            self._stop_mechanisms_for_suspend()
            self.status = ScriptStatus.SUSPENDED
            self._log_task_control("suspend")

    def resume(self):
        """恢复任务方法（必须）"""
        if (Module.getStatus() == ScriptStatus.SUSPENDED
                and self.status == ScriptStatus.SUSPENDED):
            paused_seconds = 0.0
            if self.suspend_start_time is not None:
                paused_seconds = time.time() - self.suspend_start_time
                self.start_time += paused_seconds
                self.suspend_start_time = None
            self.action_task.resume()
            self.status = ScriptStatus.RUNNING
            self._log_task_control("resume", paused_seconds)

    def cancel(self):
        self._log_task_control("cancel")
        Recognize.resetRec()
        motor_names = [self.lift_motor.motor_name, self.stretch_motor.motor_name,
                       self.rotate_motor.motor_name]
        if ConfigParams.has_finger_motor:
            motor_names += [ConfigParams.left_finger_motor_name,
                            ConfigParams.right_finger_motor_name]
        for name in motor_names:
            Motor.isMotorStop(name)
            Motor.resetMotor(name)
        Do.setDo(self.fill_light_do, False)
        self.action_task.cancel()
        self.status = ScriptStatus.FAILED

    def update_move_task_params(self):
        move_task = Navigation.moveTask()
        bin_task = ""
        for p in move_task['params']:
            if p['key'] == 'goodsName' or p['key'] == '#goodsName':
                self.goods_id = p['stringValue']
            if p['key'] == '#containerId' and p['stringValue'] != "":
                self.self_position = p['stringValue']
            if p['key'] == 'binTask':
                bin_task = p['stringValue']
        # 库位任务为外部放货时，货物必然在货叉上，强制从999号取
        if bin_task in ("ex_put", "exPut"):
            self.self_position = "999"

    def close_finger(self):
        Motor.resetMotor(ConfigParams.left_finger_motor_name)
        Motor.resetMotor(ConfigParams.right_finger_motor_name)

    def update_finger_info(self):
        if not is_simulation():
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
        if abs(pos) > abs(ConfigParams.max_rotate_angle / 180 * math.pi):
            Navigation.setTaskError("RotateAngleExceeded",_TR(f"Rotate angle {self.pos / math.pi * 180} exceeds upper limit {ConfigParams.max_rotate_angle}. Check if box is tilted or QR code is damaged"))
            self.status = ScriptStatus.FAILED
            return False
        if self.stretch_real_pos > ConfigParams.safe_stretch_length:
            Navigation.setTaskError("StretchNotZeroed", _TR(f"Stretch mechanism not zeroed, cannot perform lift/rotate. Please zero first"))
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
            "action": cur.action_type if cur else "",
            "actionId": cur.action_id if cur else "",
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

    def search_operable_container(self, opt, excluded=()):
        excluded = {str(container_id) for container_id in excluded}
        ct = None
        if opt == 'load':
            for c in self.containers:
                if str(c['containerId']) not in excluded and not c['hasGoods']:
                    ct = c['containerId']
                    break
        elif opt == 'unload':
            for c in self.containers:
                if c['hasGoods'] and self.goods_id == c['containerId']:
                    ct = c['containerId']
        return ct

    def check_put(self):
        if not Container.hasGoods("999"):
            Navigation.setTaskError("ForkNoGoods", _TR(f"Fork (slot 999) has no goods, internal put not needed！"))
            self.status = ScriptStatus.FINISHED
            return
        # 排除999号货叉：货在货叉上属于待放入，不算已在背篓
        if (self.goods_id and Container.goodsExist(self.goods_id) and
                Container.getContainerByGoods(self.goods_id) != "999"):
            Navigation.setTaskError("GoodsAlreadyExists", _TR(f"Goods {self.goods_id} already exist. Check for duplicate task"))
            self.status = ScriptStatus.FINISHED
            return
        if self.self_position:
            if Container.hasGoods(self.self_position):
                Navigation.setTaskError("GoodsInBackpack", _TR(f"Goods already in backpack"))
                self.status = ScriptStatus.FAILED
                return
            self.cur_c = self.self_position
        else:
            self.cur_c = self.search_operable_container('load')
        if self.cur_c is None:
            Navigation.setTaskError("AllBackpackFull", _TR(f"All backpack slots are full, cannot load more goods"))
            self.status = ScriptStatus.FINISHED
            return

    def check_take(self):
        if self.self_position:
            if not Container.hasGoods(self.self_position):
                Navigation.setTaskError("BackpackSlotEmpty", _TR(f"Backpack slot {int(self.self_position) + 1} ({self.self_position}) is empty, cannot execute internal pick!"))
                self.status = ScriptStatus.FAILED
            self.cur_c = self.self_position
        else:
            self.cur_c = Container.getContainerByGoods(self.goods_id)
        if Container.hasGoods("999"):
            self.cur_c = "999"
        if not self.cur_c:
            Navigation.setTaskError("GoodsNotFound", _TR(f"Specified goods {self.goods_id} not found in backpack. Verify goods ID and container data！"))
            self.status = ScriptStatus.FAILED
            return

    def safeMoveCheck(self):
        """底盘移动前安全检查（可选）"""
        if is_simulation():
            self.safe_zero_task.reset()
            Navigation.clearTaskError("FingerTimeout")
            Navigation.clearTaskError("StretchObstacle")
            self.setSafeMoveStatus(SafeMoveStatus.FINISHED)
            self.event_safe_move_check = False
            Trace.log("safe_move_check finished without mechanism actions in simulation", name=MOD)
            return

        if _get_pending_fork_store() is not None:
            self.safe_zero_task.reset()
            self.setSafeMoveStatus(SafeMoveStatus.FINISHED)
            self.event_safe_move_check = False
            Trace.log("safe_move_check kept carried goods on fork 999", name=f"{MOD}.autoPre")
            return

        if self.auto_pre_enabled and self.operation in ("load", "unload"):
            print("DEBUG:  存在autopre，跳过")
            self.safe_zero_task.reset()
            self.setSafeMoveStatus(SafeMoveStatus.FINISHED)
            self.event_safe_move_check = False
            Trace.log("safe_move_check skipped while AutoPre owns CTU motors", name=f"{MOD}.autoPre")
            return
        status = SafeMoveStatus.RUNNING
        self.setSafeMoveStatus(status)
        self.check_motor_emc()
        if self.enable_motor and not self.motor_calib_state:
            self.motor_calib()

        status = SafeMoveStatus.RUNNING
        if self.motor_calib_state:
            if self.safe_zero_task.status == ActionStatus.INIT:
                self.safe_zero_task.build(self._make_zero_actions(0.5))
            self.safe_zero_task.step(self)
            if self.safe_zero_task.status == ActionStatus.FINISHED:
                self.safe_zero_task.reset()  # 复位以便下次移动重新归零
                status = SafeMoveStatus.FINISHED
            elif self.safe_zero_task.status == ActionStatus.FAILED:
                self.safe_zero_task.reset()
                status = SafeMoveStatus.FAILED

        self.setSafeMoveStatus(status)
        safe_move_status = Module.getSafeMoveCheck()
        snapshot = (
            str(safe_move_status),
            int(status),
            bool(self.motor_calib_state),
            int(self.safe_zero_task.status),
        )
        if snapshot != self._last_safe_move_log:
            Trace.log(
                {
                    "event": "safeMoveCheck",
                    "status": status.name.lower(),
                    "motorCalibrated": bool(self.motor_calib_state),
                    "zeroQueueStatus": self.safe_zero_task.status.name.lower(),
                    "rbkStatus": safe_move_status,
                },
                output_time=True,
                name=f"{MOD}.safeMove",
            )
            self._last_safe_move_log = snapshot
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
class Rec(BaseAction):
    def __init__(self, filename, is_error=None, max_rec_times=10, action_name="Rec"):
        super().__init__(action_name)
        self.is_error = is_error
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = max_rec_times
        self.result = dict()
        self.hasGoods = None
        self.goods_out_dist = None
        self.max_goods_dist = 0.8
        # 构造时只清残留识别请求, 不发起识别。识别请求由 run() 在识别器空闲(status==0)时触发,
        # 与 jackWithSpin.RecShelf 一致: 1) Rec 在任务 init 时就被构造, 此时机构未到位/灯未开,
        # 构造即 doRec 会拍到过期图像被当作有效结果; 2) resetRec 与 doRec 不在同一 tick, 避免时序竞争
        Recognize.resetRec()

    def run(self, m):
        super().run(m)
        agv = m
        self.action_status = ActionStatus.RUNNING
        rec_status = Recognize.getRecStatus()
        if rec_status == 0:  # 识别器空闲: 发起识别, 下一 tick 再查询结果
            Recognize.doRec(self.filename, "", "")
        elif rec_status == 3 or rec_status == -1:
            if Timer.delay(0.05):
                self.rec_times = self.rec_times + 1
                Trace.log(
                    {
                        "event": "recognitionRetry",
                        "attempt": self.rec_times,
                        "maxRetries": self.max_rec_times,
                        "recognitionStatus": rec_status,
                        "file": self.filename,
                    },
                    output_time=True,
                    name=f"{MOD}.rec",
                )
                if self.rec_times > self.max_rec_times:
                    if not self.is_error:
                        Navigation.setTaskError("RecFailed", _TR(f"Recognition failed after max retries{self.max_rec_times}. Check if QR code is damaged or camera is clear"))
                        self.action_status = ActionStatus.FAILED
                    else:
                        self.action_status = ActionStatus.FINISHED
                else:
                    Recognize.resetRec()  # 只清状态, 下一 tick status==0 时重新 doRec
        elif rec_status == 2:
            rec_results = Recognize.getRecResults()
            if "recoList" in rec_results:
                if len(rec_results["recoList"]) == 1:
                    reco = rec_results["recoList"][0]
                    if not reco.get('valid', False):
                        Trace.log(
                            {
                                "event": "recognitionRetry",
                                "reason": "invalidResult",
                                "file": self.filename,
                            },
                            output_time=True,
                            name=f"{MOD}.rec",
                        )
                        Recognize.resetRec()  # 只清状态, 下一 tick status==0 时重新 doRec
                        return
                    self.result = reco.get('robotResult', {})
            Recognize.resetRec()
            self.hasGoods = True
            if self.result.get("x", 0) > self.max_goods_dist:
                self.goods_out_dist = True
            self.action_status = ActionStatus.FINISHED
            Trace.log(
                {
                    "event": "recognitionFinished",
                    "file": self.filename,
                    "result": self.result,
                },
                output_time=True,
                name=f"{MOD}.rec",
            )

        cur_state = dict()
        cur_state['recResult'] = self.result
        cur_state['recCount'] = self.rec_times
        cur_state['recTaskStatus'] = self.action_status
        cur_state['recStatus'] = rec_status
        cur_state['file'] = self.filename
        agv.report_info['recInfo'] = cur_state

    def reset(self):
        super().reset()
        # 只清残留请求；下一次 run() tick 发现识别器空闲(status==0)时再触发识别
        Recognize.resetRec()


class RecAdjust(BaseAction):
    def __init__(self, filename, action_name="RecAdjust"):
        super().__init__(action_name)
        self.rotate_step = None
        self.lift_step = None
        self.rec = Rec(filename)
        self.result = []
        self.max_rec_fail_times = 10
        self.max_adjust_time = 30
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.code_check_fail = 0  # DM14 三联码比对失败计数（跨识别轮累计）
        self.go_args = dict()
        self.ok = False

        self.next_rotate_pos = 1.5708
        self.diff_height = 0
        self.last_yaw_adjust = 1.5708
        self.plan_status = ScriptStatus.NONE
        self.goPath = GoPath()
        self.code2robot = -1
        self.prepare_recognition = True
        self.retry_rotate_target = None

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
        super().run(agv)
        cur_state = dict()
        self.action_status = ActionStatus.RUNNING
        if self.plan_status is not ScriptStatus.FINISHED:
            self.plan_status = ScriptStatus.RUNNING
            if self.rec.action_status is ActionStatus.RUNNING or self.rec.action_status is ActionStatus.INIT:
                self.rec.run(agv)
            elif self.rec.action_status is ActionStatus.FAILED:
                self.rec_fail_time = self.rec_fail_time + 1
                random_dist = random.choice([1, -1]) * (1 / 180 * math.pi)
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.retry_rotate_target = agv.rotate_real_pos + random_dist
                    self.prepare_recognition = True
                    self.rec.reset()
                else:
                    self.action_status = ActionStatus.FAILED
                Trace.log(
                    {
                        "event": "recognitionRoundFailed",
                        "round": self.rec_fail_time,
                        "maxRounds": self.max_rec_fail_times,
                        "recoveryRotateDeg": round(random_dist * 180 / math.pi, 3),
                    },
                    output_time=True,
                    name=f"{MOD}.rec",
                )
            elif self.rec.action_status is ActionStatus.FINISHED:
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
                    self.action_status = ActionStatus.FAILED
                    Navigation.setTaskError("RecYawExceeded", _TR(f"Recognition yaw deviation{agv.yaw_adjust / math.pi * 180:.2f}° exceeds limit{ConfigParams.max_yaw_bias}°. Check if box is aligned and QR code intact"))
                else:
                    if self.adjust_count >= (self.max_adjust_time - 3):
                        agv.ok_x = 0.01
                        agv.ok_yaw = 1.15 / 180 * math.pi
                    if not ConfigParams.auto_adjust_rotate and abs(self.rec.result['y']) < agv.ok_x:
                        Trace.log(f"adjust finished, adjust count: {self.adjust_count}", name=f"{MOD}.rec")
                        if self.check_goods_code(agv):
                            self.action_status = ActionStatus.FINISHED
                    elif ConfigParams.auto_adjust_rotate and abs(self.rec.result['y']) < agv.ok_x and abs(
                            agv.yaw_adjust) <= agv.ok_yaw:
                        Trace.log(f"adjust finished, adjust count: {self.adjust_count}", name=f"{MOD}.rec")
                        if self.check_goods_code(agv):
                            self.action_status = ActionStatus.FINISHED
                    else:
                        if self.adjust_count >= self.max_adjust_time:
                            self.action_status = ActionStatus.FAILED
                            Navigation.setTaskError("RecAdjustExceeded", _TR(f"Recognition adjustment {self.adjust_count} retries exceeded. Check QR code, camera, accuracy parameters"))
                self.plan_status = ScriptStatus.FINISHED
                self.rec.reset()
        elif self.action_status is not ActionStatus.FINISHED and self.action_status is not ActionStatus.FAILED:
            if self.goPath.action_status is not ActionStatus.FINISHED and self.goPath.action_status is not ActionStatus.FAILED:
                if abs(self.go_args['x']) < 0.003:
                    self.goPath.action_status = ActionStatus.FINISHED
                else:
                    if self.goPath.action_status is not ActionStatus.FINISHED and self.goPath.action_status is not ActionStatus.FAILED:
                        self.goPath.run(self.go_args)
            elif not self.rotate_step and self.goPath.action_status is ActionStatus.FINISHED:
                if abs(agv.yaw_adjust) <= 0.01:
                    self.rotate_step = True
                if not self.rotate_step and ConfigParams.auto_adjust_rotate:
                    self.rotate_step = agv.rotate(self.next_rotate_pos, max_speed=0.3)
                else:
                    self.rotate_step = True
            elif self.goPath.action_status is ActionStatus.FAILED:
                self.action_status = ActionStatus.FAILED
            elif self.goPath.action_status is ActionStatus.FINISHED and self.rotate_step:
                self.reset()
                self.adjust_count += 1
                self.last_yaw_adjust = agv.yaw_adjust
                self.plan_status = ScriptStatus.NONE
                self.rotate_step = False
        cur_state["autoStretchLength"] = agv.stretch_length
        cur_state["goPathStatus"] = int(self.goPath.action_status)
        cur_state["goArgs"] = self.go_args
        cur_state["recResult"] = self.rec.result
        cur_state["recFailTime"] = self.rec_fail_time
        cur_state["adjustCount"] = self.adjust_count
        cur_state["curRotate"] = agv.rotate_real_pos / math.pi * 180
        cur_state["curLift"] = agv.lift_real_pos
        cur_state["curStretch"] = agv.stretch_real_pos
        cur_state["status"] = self.action_status
        cur_state["agvYawAdjust"] = agv.yaw_adjust / math.pi * 180
        cur_state["lastYawAdjust"] = self.last_yaw_adjust / math.pi * 180
        cur_state["nextRotatePos"] = self.next_rotate_pos / math.pi * 180
        agv.report_info["recAdjust"] = cur_state

    def check_goods_code(self, agv):
        """
        比较识别结果上报的 objectMessage 与任务下发的 goodsId（DM14 三联码校验）。
        一致才放行(返回 True)；不一致时重试识别，多次比较失败则报错。
        仅取货(load)动作校验：识别的是料箱货物编码，需与下发 goodsId 一致。
        放货(unload)时 goodsId 用于指定背篓取对应料箱，识别的是货架码放货位，无需校验，直接放行。
        开关关闭(checkGoodsCodeEnable=False)或 goodsId 为空时也不校验，直接放行。
        @return: bool 是否放行通过
        """
        rec_code = self.rec.result.get("objectMessage", "")
        agv.report_info["recCode"] = rec_code
        # 仅取货动作校验货物编码；卸货识别货架货位, 不校验
        if agv.operation != "load":
            return True
        # 未开启校验或无下发编码(手动调试等场景)时直接放行
        if not ConfigParams.check_goods_code_enable or not agv.goods_id:
            return True
        if rec_code == agv.goods_id:
            self.code_check_fail = 0
            return True
        # 编码不匹配
        self.code_check_fail += 1
        Trace.log(
            f"货物编码不匹配({self.code_check_fail}/{ConfigParams.max_code_check_fail}), "
            f"任务下发: {agv.goods_id}, 识别: {rec_code}", name=f"{MOD}.rec")
        if self.code_check_fail >= ConfigParams.max_code_check_fail:
            Navigation.setTaskError("GoodsCodeMismatch", _TR(
                f"Goods code mismatch between task command {agv.goods_id} and recognized code {rec_code}"))
            self.action_status = ActionStatus.FAILED
        # 未达上限时不放行, 外层调整流程会重新识别再比较
        return False

    def reset(self):
        super().reset()
        self.rec.reset()
        self.rec_fail_time = 0
        self.goPath.reset()
        self.prepare_recognition = True
        self.retry_rotate_target = None


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
        Container.initContainer(container_num - 1, "999")

    while True:
        # 脚本任务状态管理
        status = robot.status
        # 上报脚本任务状态
        Module.setStatus(status)

        # 每 tick 集中上报(reportInfo 含 containers + ctu.task/ctu.motor 数值时序)
        robot.tick_report()

        # 触发安全检查事件
        if robot.event_safe_move_check:
            print(f"DEBUG:检查")
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
            robot.auto_pre_enabled = False

        """需要增加sleep，如果时间太短控制器增加CPU占用"""
        time.sleep(0.1)


if __name__ == '__main__':
    main()
