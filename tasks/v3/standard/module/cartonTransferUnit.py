# -*- coding: utf-8 -*-
# @Date: 2026/2/10
# @Author: zhaopengfei
# @Version: v1.1
# @Project: SPK-MJ50-HL
# @Update: 脚本参数规范化第一版
# @RBK Version: V3.5+
import enum
import uuid

SCRIPT_VERSION = "20260204"
import json
import math
import random
import time
from typing import List

from syspy.utils.time import Timer
from syspy import Module, Logger, Di, Do, Motor, Navigation, ScriptStatus, Abnormal, Controller, Odometer, Recognize, \
    RobotParam, Trace
from syspy.lib.net_protocol import parseModbus, NetProtocol
from syspy.bin import Container
from syspy.lib.module import SafeMoveStatus, ModuleBase
from syspy.utils.param_server import ParamBuilder, ParamType, ParamServer, ParamValidator, ScriptParam
from standard.goPath import GoPath

log = Logger("ContainerRobot")
param_loader = ScriptParam(__file__)

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


def debug_trace(*args, **kwargs):
    """Log to Trace only when debug_mode is enabled (with timestamp)"""
    if ConfigParams.debug_mode:
        timestamp = _get_timestamp()
        if args:
            first_arg = f"{timestamp} {args[0]}"
            Trace.log(first_arg, *args[1:], **kwargs)
        else:
            Trace.log(timestamp, **kwargs)


class ConfigParams:
    config = {}
    high = dict()
    low = dict()
    container_count = 0  # 背篓数量，从设备模型读取
    debug_mode = False  # Debug开关
    """配置管理器，用于管理动态配置参数"""

    # 默认背篓高度参数 (low, high)
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

    def __init__(self):
        self._build_and_load_config()

    @staticmethod
    def get_container_count():
        """从设备模型读取背篓数量"""
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
        """从设备模型读取电机名称和拨指 DO/DI 配置
        """
        module_type = RobotParam.getDevice("Model-000", "moduleType")
        if not module_type:
            raise ValueError("读取设备模型失败: Model-000.moduleType 为空，请检查设备模型配置！")
        base = f"moduleType.{module_type}"

        # 电机名称
        cls.lift_motor_name = RobotParam.getDevice("Model-000", f"{base}.liftMotor")
        cls.rotate_motor_name = RobotParam.getDevice("Model-000", f"{base}.rotateMotor")
        cls.stretch_motor_name = RobotParam.getDevice("Model-000", f"{base}.reachMotor")
        if not cls.lift_motor_name or not cls.rotate_motor_name or not cls.stretch_motor_name:
            raise ValueError(
                f"读取电机名称失败: liftMotor={cls.lift_motor_name}, "
                f"rotateMotor={cls.rotate_motor_name}, stretchMotor={cls.stretch_motor_name}，"
                f"请在设备模型中正确配置！"
            )

        # 拨指 DO: "左关,左开,右关,右开"
        finger_do = RobotParam.getDevice("Model-000", f"{base}.fingerDO")
        if not finger_do or not isinstance(finger_do, str):
            raise ValueError(f"读取拨指DO失败: fingerDO={finger_do}，请在设备模型中正确配置！")
        do_list = [x.strip() for x in finger_do.split(",") if x.strip()]
        if len(do_list) < 4:
            raise ValueError(f"拨指DO配置不完整，需要4个值，实际: {do_list}")
        cls.left_finger_down_do = do_list[0]  # 左关
        cls.left_finger_up_do = do_list[1]  # 左开
        cls.right_finger_down_do = do_list[2]  # 右关
        cls.right_finger_up_do = do_list[3]  # 右开

        # # 拨指 DI - 先打印看返回格式
        # finger_di = RobotParam.getDevice("Model-000", f"{base}.fingerDI")
        # print(f"[DEBUG] fingerDI raw value: {finger_di}, type: {type(finger_di)}")

    @classmethod
    def _build_and_load_config(cls):
        """构建并加载配置参数"""
        cls.container_count = cls.get_container_count()
        cls.read_device_model()
        log.info(f"Container count from device model: {cls.container_count}")
        builder = param_loader.builderConfig()

        with builder.GROUPS():
            # ============================================
            # 通用配置组
            # ============================================
            with builder.GROUP(key="generalConfig", name="General Configuration",
                               desc="General configuration parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="debugMode", name="Debug Mode",
                                       desc="Enable debug mode to show debug tasks and low-frequency parameters"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

            # ============================================
            # 背篓组（独立 GROUP，和 generalConfig 同级缩进）
            # ============================================
            with builder.GROUP(key="traysConfig", name="Trays Config",
                               desc="Backpack layer height parameters, Counted from No. 0"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    for i in range(cls.container_count):
                        default_low = cls.DEFAULT_TRAY_HEIGHTS[i][0] if i < len(
                            cls.DEFAULT_TRAY_HEIGHTS) else 0.400 + i * 0.410
                        default_high = cls.DEFAULT_TRAY_HEIGHTS[i][1] if i < len(
                            cls.DEFAULT_TRAY_HEIGHTS) else default_low + 0.010
                        with builder.CHILD(key=f"low{i}", name=f"Low{i}",
                                           desc=f"Height of the No. {i} Backboard Retrieval Box"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.UNIT("m")
                            builder.DEFAULTVALUE(default_low)
                        with builder.CHILD(key=f"high{i}", name=f"High{i}",
                                           desc=f"Height of the No. {i} Backbasket Material Box"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.UNIT("m")
                            builder.DEFAULTVALUE(default_high)

            # 识别组
            with builder.GROUP(key="recognizeConfig", name="Recognize Config",
                               desc="Recognition relevant parameters"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 识别取箱时二次调整高度
                    with builder.CHILD(key="recOffzBox", name="rec Offz Box", desc="Adjust Height Twice for Pick"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(-0.030)
                    # 识别放箱时二次调整高度
                    with builder.CHILD(key="recOffzShelf", name="Rec Offz Shelf", desc="Adjust Height Twice for Place"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.030)
                    # 料箱码识别配置文件
                    with builder.CHILD(key="boxCodeFile", name="Box Code File", desc="Box Code Recognition Config"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("default.srec")
                    # 货架码识别配置文件
                    with builder.CHILD(key="shelfCodeFile", name="Shelf Code File",
                                       desc="Shelf Code Recognition Config"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("default1.srec")
                    # 一维码识别配置文件
                    with builder.CHILD(key="barcodeFile", name="Barcode File", desc="Barcode Recognition Config"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("default2.srec")
                    # 针对识别结果误差在行走方向的补偿值
                    with builder.CHILD(key="offsetX", name="Offset X", desc="Walking Direction Offset"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.000)
                    # 补光灯延时拍照时间
                    with builder.CHILD(key="loadRecLiftDiff", name="Load Rec Lift Diff",
                                       desc="Height difference from bin to shelf"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.050)
                    # 放货识别货架上是否有货物时，在放货高度上需要额外抬升的高度，该值可设置为货架码到料箱码的高度差
                    with builder.CHILD(key="recBoxExtraHeight", name="Rec Box Extra Height",
                                       desc="Lift height for shelf stock detection"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.000)
                    # 行走方向识别调整完成阈值
                    with builder.CHILD(key="okX", name="Ok X", desc="Walking Direction Recognition Threshold"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0.01)
                    # 识别调整完成角度阈值
                    with builder.CHILD(key="okYaw", name="Ok Yaw", desc="Adjustment Completion Threshold"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("deg")
                        builder.DEFAULTVALUE(0.86)
                    # 货叉与料箱角度最大偏差, 角度值
                    with builder.CHILD(key="maxYawBias", name="Max Yaw Bias", desc="Max Fork Angle Offset (deg)"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.UNIT("deg")
                        builder.DEFAULTVALUE(7.45)

            # 电机组
            with builder.GROUP(key="motorConfig", name="Motor Configuration",
                               desc="Motor related configuration parameters"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 升降电机速度
                    with builder.CHILD(key="liftMotorSpeed", name="Lift Motor Speed", desc="Speed of the lift motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.500)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)

                    # 升降最高位
                    with builder.CHILD(key="maxForkHeight", name="Max Lift Height", desc="Maximum position for lift"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(4.500)
                        builder.UNIT("m")

                    # 升降最低位
                    with builder.CHILD(key="minForkHeight", name="Min Lift Height", desc="Zero position for lift"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.380)
                        builder.UNIT("m")

                    # 安全升降高度, 货叉导航过程中的最高高度
                    with builder.CHILD(key="safeLiftHeight", name="Safe Lift Height",
                                       desc="Safe position for lift, the highest height during forklift navigation"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.000)
                        builder.UNIT("m")

                with builder.CHILDREN():
                    # 旋转电机速度
                    with builder.CHILD(key="rotateMotorSpeed", name="Rotate Motor Speed",
                                       desc="Speed of the rotate motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.000)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)

                    # 旋转最大位
                    with builder.CHILD(key="maxRotateAngle", name="Max Rotate Angle", desc="Maximum angle for rotate"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(100)
                        builder.UNIT("deg")

                    # 识别时是否需要自动调整货叉角度
                    with builder.CHILD(key="autoAdjustRotate", name="Auto Adjust Rotate",
                                       desc="The distance between the finger mechanism and the fork rotation center, Used for automatic calculation of fork extension length"):
                        builder.TYPE(ParamType.BOOL)

                with builder.CHILDREN():
                    # 伸缩电机速度
                    with builder.CHILD(key="stretchMotorSpeed", name="Stretch Motor Speed",
                                       desc="Speed of the stretch motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.000)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)

                    # 伸缩最大长度
                    with builder.CHILD(key="maxStretchLength", name="Max Stretch Length",
                                       desc="Maximum length of fork"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.900)
                        builder.UNIT("m")

                    # 伸缩安全长度, 货叉升降、旋转操作时伸缩臂安全长度
                    with builder.CHILD(key="safeStretchLength", name="Safe Stretch Length",
                                       desc="Safe length of telescopic arm during forklift lifting and rotating operations"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.900)
                        builder.UNIT("m")

                    # 取放自身背篓货物时伸出长度
                    with builder.CHILD(key="stretchSelfLength", name="Stretch Self Length",
                                       desc="The length when picking up and placing goods in one's own backpack"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.760)
                        builder.UNIT("m")

                    # 箱子长度, 用于自动计算货叉伸出长度
                    with builder.CHILD(key="autoStretchBoxLen", name="Auto Stretch Box Len",
                                       desc="The length of box, Used for automatic calculation of fork extension length"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.600)
                        builder.UNIT("m")

                    # 自动计算取货伸出长度时的补偿值
                    with builder.CHILD(key="autoLoadStretchDist", name="Auto Load Stretch Dist",
                                       desc="The compensation value for the extended length of the pickup fork when picking up goods"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.010)
                        builder.UNIT("m")

                    # 自动计算放货伸出长度时的补偿值
                    with builder.CHILD(key="autoUnloadStretchDist", name="Auto Unload Stretch Dist",
                                       desc="The compensation value for the extended length of the pickup fork when putting down goods"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.010)
                        builder.UNIT("m")

                    # 手指机构到货叉旋转中心的距离, 用于自动计算货叉伸出长度
                    with builder.CHILD(key="autoStretchOdoLen", name="Auto Stretch Odo Len",
                                       desc="The distance between the finger mechanism and the fork rotation center, Used for automatic calculation of fork extension length"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.380)
                        builder.UNIT("m")

            # 拨指组
            with builder.GROUP(key="fingerConfig", name="Finger Configuration",
                               desc="Finger related configuration parameters"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 左拨指打开DI
                    with builder.CHILD(key="leftFingerUpDi", name="Left Finger Up Di", desc="Open Left Fingers"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DI-003")
                        builder.REQUIRED(True)

                    # 左拨指关闭DI
                    with builder.CHILD(key="left_finger_down_di", name="Left Finger Down Di",
                                       desc="Close Left Fingers"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DI-000")
                        builder.REQUIRED(True)

                    # 右拨指打开DI
                    with builder.CHILD(key="rightFingerUpDi", name="Right Finger Up Di", desc="Open Right Fingers"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DI-004")
                        builder.REQUIRED(True)

                    # 右拨指关闭DI
                    with builder.CHILD(key="rightFingerDownDi", name="Right Finger Down Di",
                                       desc="Close Right Fingers"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DI-005")
                        builder.REQUIRED(True)

            # 其他组
            with builder.GROUP(key="otherConfig", name="Other Configuration", desc="Other configuration parameters"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 超时时间
                    with builder.CHILD(key="timeout", name="Timeout", desc="Execution Timeout"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(120, min_value=0, max_value=300)
                    # 货叉中部货物检测光电DI
                    with builder.CHILD(key="goodsCheckDi", name="Goods Check Di", desc="Fork Midpoint Detection DI"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DI-008")
                        builder.REQUIRED(True)
                    # 货叉安全限位DI
                    with builder.CHILD(key="overlimitDetectDi", name="Overlimit Detect Di",
                                       desc="Fork Safe Travel Limit"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DI-009")
                        builder.REQUIRED(True)
                    # 补光灯时间
                    with builder.CHILD(key="lightDelayTime", name="Light Delay Time", desc="time for light"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3, min_value=0, max_value=100)
                        builder.REQUIRED(True)

        # 保存配置参数到文件
        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        cls.container_count = cls.get_container_count()
        cls.read_device_model()
        cls.config = param_loader.loadConfig()

        # 通用配置 - 先加载 debug_mode
        cls.debug_mode = cls.config.get("debugMode", False)
        # 根据背篓数量动态加载背篓高度参数
        cls.low.clear()
        cls.high.clear()
        for i in range(cls.container_count):
            cls.low[i] = cls.config.get(f"low{i}")
            cls.high[i] = cls.config.get(f"high{i}")

        cls.rec_offz_box = cls.config.get("recOffzBox")
        cls.rec_offz_shelf = cls.config.get("recOffzShelf")
        cls.rec_load_offz_shelf = cls.config.get("recLoadOffzShelf")
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

        cls.left_finger_up_di = cls.config.get("leftFingerUpDi")
        cls.left_finger_down_di = cls.config.get("leftFingerDownDi")
        cls.right_finger_up_di = cls.config.get("rightFingerUpDi")
        cls.right_finger_down_di = cls.config.get("rightFingerDownDi")

        cls.timeout = cls.config.get("timeout")
        cls.goods_check_di = cls.config.get("goodsCheckDi")
        cls.overlimit_detect_di = cls.config.get("overlimitDetectDi")
        cls.light_delay_time = cls.config.get("lightDelayTime")


# 创建全局配置管理器实例
config_params = ConfigParams()

# ============================================================================
# 调试任务列表（需要开启 debugMode 才能执行）
# ============================================================================
DEBUG_ONLY_TASKS = [
    "none",  # 空操作
    "calib",  # 强制标零
    "recQrcode",  # 识别二维码
    "recBoxBarcode",  # 识别料箱一维码
    "takePhoto",  # 拍照
]


def check_debug_task(operation: str) -> bool:
    """
    检查任务是否为调试任务，如果是调试任务且 debugMode=false 则返回 False

    Returns:
        True: 可以执行
        False: 调试任务但 debugMode 未开启，不能执行
    """
    if operation in DEBUG_ONLY_TASKS:
        if not config_params.debug_mode:
            Trace.log(
                f"[ERROR] Task '{operation}' is a debug-only task. "
                f"Please enable 'debugMode' in script config first.")
            return False
    return True


def script_config_callback():
    log.info("Reloading script config parameters")
    config_params.reload_config()


def params_callback(device_change_set: List[str]):
    log.info(f"{device_change_set=}")
    for device in device_change_set:
        if device == "Model":
            config_params.reload_config()


# 创建可复用的参数
def create_container_param(builder: ParamBuilder, desc: str = "车体背篓号"):
    """创建车体背篓号参数"""
    with builder.CHILD(key="container", name="Container",
                       desc=desc):
        builder.MIN_VALUE(0)
        builder.MAX_VALUE(999)
        builder.TYPE(ParamType.INT)
        builder.DEFAULTVALUE(0)


def create_goods_id_param(builder: ParamBuilder, desc: str = "货物编号"):
    """创建货物编号参数"""
    with builder.CHILD(key="goodsName", name="Goods Name", desc=desc):
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
        builder.UNIT("deg")
        builder.DEFAULTVALUE(0)  # 角度值


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

        with builder.CHILD(key="modbusIp", name="Modbus IP", desc="Modbus TCP IP"):
            builder.TYPE(ParamType.IP)
            builder.DEFAULTVALUE("192.168.192.6")

        with builder.GROUP(key="operation", name="Operation", desc="机构动作选项"):
            builder.TYPE(ParamType.COMBO_BOX)
            # ============================================
            # 常用任务（始终显示）
            # ============================================
            with builder.CHILDREN():
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
                        with builder.CHILD(key="preFinger", name="Pre Finger",
                                           desc="放货时提前打开手指，解决推箱子后由于箱体表面不规则结构卡手指"):
                            builder.TYPE(ParamType.INT)
                            builder.DEFAULTVALUE(1)
                        create_container_param(builder, "车体背篓号，指定内部取货的背篓号，缺省时将按照从下往上依次取货")
                        create_goods_id_param(builder, "货物编号，指定要取货的货物编号，若车体背篓中无此goodsName，会报错")

                # ============================================
                # 调试/低频任务（需要开启 debugMode 才显示）
                # ============================================
                if config_params.debug_mode:
                    with builder.CHILD(key="none", name="[Debug] none", desc="空"):
                        builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="recQrcode", name="[Debug] Rec_Qrcode", desc="识别二维码"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_vision_type_param(builder, "识别类型: 'box' 或 'shelf'")
                            create_lift_param(builder, "识别时的货叉高度")
                            create_rotate_param(builder, "识别时的货叉角度")

                    with builder.CHILD(key="recBoxBarcode", name="Rec_Box_Barcode", desc="识别料箱一维码"):
                        builder.TYPE(ParamType.ARRAY)
                        create_lift_param(builder, "识别前的货叉高度")
                        create_rotate_param(builder, "识别前的货叉角度")
                    with builder.CHILD(key="takePhoto", name="Take_Photo", desc="拍照"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_lift_param(builder, "拍照前的货叉高度")
                            create_rotate_param(builder, "拍照前的货叉角度")

                    # in_take
                    with builder.CHILD(key="inTake", name="In Take", desc="内部取货"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_container_param(builder,
                                                   "车体背篓号，指定内部取货的背篓号，缺省时将按照从下往上依次取货")
                            create_goods_id_param(builder,
                                                  "货物编号，指定要取货的货物编号，若车体背篓中无此goodsName，会报错")
                            create_rotate_param(builder,
                                                "内部取货后货叉停止的角度，可设置为下一个动作的目标角度，缺省时默认为0")
                            create_lift_param(builder,
                                              "内部取货后货叉停止的高度，可设置为下一个动作的目标高度，缺省时默认为0")

                    with builder.CHILD(key="inPut", name="In_Put", desc="内部放货"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_container_param(builder,
                                                   "车体背篓号，指定内部放货的背篓号，缺省时将按照从下往上依次放货")
                            create_goods_id_param(builder, "设置货物编号，缺省时为空字符串")

                    with builder.CHILD(key="exTake", name="Ex_Take", desc="外部取货"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_vision_type_param(builder, "识别类型: 'box'或'shelf' ")
                            create_lift_param(builder, "取货前识别时的货叉高度")
                            create_rec_adjust_param(builder, "开启识别时调整机器人位置")
                            create_rotate_param(builder, "取货前的货叉角度")
                            create_stretch_param(builder, "取货时的伸缩机构长度")

                    with builder.CHILD(key="exPut", name="Ex_Put", desc="外部放货"):
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
            Motor.setMotorPosition(self.motor_name, pos, max_vel)
        elif self.motor_type == MotorType.ROLLER_MOTOR:
            Motor.setMotorSpeed(self.motor_name, vel)
        else:
            Trace.log(f"motor type error {self.motor_type}")
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
        Trace.log(f"motor reset: {self.motor_name}")
        Motor.resetMotor(self.motor_name)
        self.status = ScriptStatus.RUNNING

    def stop(self):
        Motor.isMotorStop(self.motor_name)
        self.status = ScriptStatus.NONE
        self.state['motorStatus'] = self.status


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
        self.ok_yaw = ConfigParams.ok_yaw / 180 * math.pi  # 角度转弧度

        self.args_init = False
        self.script_args = args or {}
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

        self.fill_light_do = "DO-004"  # 补光灯DO
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
        self.count = 0
        Trace.log(f"init args: {args}")

    def init_script_args(self, args):
        self.script_args = args or Module.getTaskArgs()
        if args:
            self.goods_id = self.script_args.get("goodsName", "")
            self.self_position = self.script_args.get("container", self.self_position)
            self.self_position = str(self.self_position) if self.self_position is not None else self.self_position
            self.update_move_task_params()
            self.finger_pos = self.script_args.get("finger", 0)
            self.lift_height = self.script_args.get("lift", 0)
            self.door_height = self.script_args.get("lift-door", 0)
            self.stretch_length = self.script_args.get("stretch", 0)
            self.is_auto_stretch = bool("stretch" not in self.script_args)  # 输入参数无"stretch"，则自动计算识别长度
            self.rotate_pos = self.script_args.get("rotate", 0) / 180 * math.pi  # 角度转弧度
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
            # 如果container_num为数字且>0
            if isinstance(container_num, int) and container_num > 0:
                Container.initContainer(container_num)
            self.containers = Container.getContainers()
            self.rec_id = uuid.uuid4().hex
            self.box_code_file = self.script_args.get("codeFile", ConfigParams.box_code_file)
            self.shelf_code_file = self.script_args.get("shelfCodeFile", ConfigParams.shelf_code_file)
            Abnormal.clear(53300)
            Abnormal.clear(53310)
            Abnormal.clear(53320)
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

            # 根据货叉货物检测光电更新货叉有无货信息
            if ConfigParams.goods_check_di != "":
                if self.stretch_real_pos < 0.05:  # 手臂未伸出状态下检测有效
                    if Di.getDi(ConfigParams.goods_check_di) and not Container.hasGoods("999"):
                        Abnormal.setTask(53700, f"货叉光电检测到货叉中有货，但数据显示无货，需要人工核查处理", "", "", "")
                        self.status = ScriptStatus.FAILED
                    elif not Di.getDi(ConfigParams.goods_check_di):
                        Container.clearContainer("999")
            else:
                Abnormal.setTask(53701, f"请在脚本参数中正确配置 goodsCheckDi 参数！", "", "", "")
                Trace.log(f"请在脚本参数中正确配置 goodsCheckDi 参数！")
                self.status = ScriptStatus.FINISHED

            self.start_time = time.time()
            self.status = ScriptStatus.RUNNING

    def run(self):
        self.status = ScriptStatus.RUNNING
        self.counter += 1
        self.update_report_info()
        self.report_info["getCountRun"] = self.counter
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
                elif self.operation == "zeroWithLift":
                    self.lift_height = min(self.lift_real_pos, self.lift_height)
                    if self.zero(self.lift_height):
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "load":
                    if self.load():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "unload":
                    if self.unload():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "recBoxBarcode":
                    self.rec_box_barcode()
                elif self.operation == "recQrcode":
                    self.rec_qrcode()
                elif self.operation == "takePhoto":
                    self.take_photo()
                elif self.operation == "inTake":
                    if self.in_take():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "inPut":
                    if self.in_put():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "exTake":
                    if self.ex_take():
                        self.status = ScriptStatus.FINISHED
                elif self.operation == "exPut":
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
        if self.status == ScriptStatus.FAILED or self.status == ScriptStatus.FINISHED:
            # r.disableMotor(ConfigParams.lift_motor_name)
            NetProtocol.release()
            Do.setDo(self.fill_light_do, False)
            Trace.log(f"script finished: {json.dumps(self.report_info)}")
        Module.reportInfo(self.report_info)
        return self.status

    @staticmethod
    def get_motor_info(motor_name: str):
        motor_data = Odometer.getData().get("motorInfo", [])
        for _motor in motor_data:
            if _motor.get('motorName') == motor_name:
                return _motor
        return {}

    def check_motor_emc(self):
        """
        检测急停状态, 驱动器上使能
        """
        controller_emc = Controller.getEmc()
        lift_motor_info = self.get_motor_info(ConfigParams.lift_motor_name)  # 能查询到电机数据,说明驱动器已供电
        stretch_motor_info = self.get_motor_info(ConfigParams.stretch_motor_name)
        rotate_motor_info = self.get_motor_info(ConfigParams.rotate_motor_name)
        lift_motor_emc = lift_motor_info.get("emc", False)
        stretch_motor_emc = stretch_motor_info.get("emc", False)
        rotate_motor_emc = rotate_motor_info.get("emc", False)
        self.motor_calib_info["liftMotorEmc"] = lift_motor_emc
        self.motor_calib_info["stretchMotorEmc"] = stretch_motor_emc
        self.motor_calib_info["rotateMotorEmc"] = rotate_motor_emc
        self.motor_calib_info["controllerEmc"] = controller_emc
        self.enable_motor = not lift_motor_emc and not rotate_motor_emc and not stretch_motor_emc  # 驱动器使能状态
        if not controller_emc and time.time() - self.enable_motor_time > 0.5:  # 控制器未急停
            self.enable_motor_time = time.time()
            if Abnormal.getNum() == 0:
                if lift_motor_info and lift_motor_emc:  # 控制器未急停但是驱动器急停，给电机上使能
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
        # self.motor_calib_state = (self.lift_motor_calib == 2 and self.stretch_motor_calib == 2 and self.rotate_motor_calib == 2)
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
        if Module.getStatus() == ScriptStatus.RUNNING:
            self.status = ScriptStatus.SUSPENDED

    def resume(self):
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING

    def cancel(self):
        Recognize.resetRec()
        self.close_finger()
        Do.setDo(self.fill_light_do, False)
        self.status = ScriptStatus.FAILED
        Trace.log("carton cancel")

    def update_move_task_params(self):
        """
        获取moveTask参数
        """
        move_task = Navigation.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsName':
                self.goods_id = p['stringValue']
            if p['key'] == '#containerId' and p['stringValue'] != "":
                self.self_position = p['stringValue']

    def zero(self, zero_height=0):
        """
        支持指定高度执行标零复位
        :param zero_height:
        :return:
        """
        Trace.log(f"----- running zero ------")

        if not self.zero_step[0]:
            self.zero_step[0] = Container.hasGoods("999") or self.finger(1)
        elif self.zero_step[0] and not self.zero_step[1]:
            self.zero_step[1] = self.stretch(0)
        elif self.zero_step[1] and not self.zero_step[2]:
            self.zero_step[2] = self.rotate(0)
        elif self.zero_step[2] and not self.zero_step[3]:
            self.zero_step[3] = self.lift(zero_height)
        Trace.log(f"zero_step:{self.zero_step}")
        if all(self.zero_step):
            self.zero_step = [False] * 4
            # r.release()
            return True
        return False

    def lift(self, height):
        Trace.log(f"----- running lift ------")
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
        Trace.log(f"----- running finger ------")
        if not self.finger_open_start:
            self.finger_open_start = time.time()
        else:
            if time.time() - self.finger_open_start > 3:  # 防止手指机构卡死时电机过流烧毁
                Abnormal.setTask(53706, f"拨指控制超时，请检查拨指是否卡住、检查拨指到位光电是否能正常触发！", "", "", "")
                Do.setDo(ConfigParams.left_finger_up_do, False)
                Do.setDo(ConfigParams.right_finger_up_do, False)
                Do.setDo(ConfigParams.left_finger_down_do, False)
                Do.setDo(ConfigParams.right_finger_down_do, False)
                self.status = ScriptStatus.FAILED
                return False
        if pos == 1:
            Do.setDo(ConfigParams.left_finger_up_do, True)
            Do.setDo(ConfigParams.right_finger_up_do, True)
            if Di.getDi(ConfigParams.left_finger_up_di) and not Di.getDi(ConfigParams.left_finger_down_di):
                self.left_finger_real_pos = 1
                Do.setDo(ConfigParams.left_finger_up_do, False)
            if Di.getDi(ConfigParams.right_finger_up_di) and not Di.getDi(ConfigParams.right_finger_down_di):
                self.right_finger_real_pos = 1
                Do.setDo(ConfigParams.right_finger_up_do, False)

            if self.left_finger_real_pos == 1 and self.right_finger_real_pos == 1:
                self.finger_open_start = False
                return True

        elif pos == 0:
            if Di.getDi(ConfigParams.overlimit_detect_di):
                Abnormal.setTask(53707, f"伸出长度不够，货叉超限光电检测到障碍物！可上调取货伸出补偿参数值！", "", "", "")
                self.status = ScriptStatus.FAILED
                return False
            Do.setDo(ConfigParams.left_finger_down_do, True)
            Do.setDo(ConfigParams.right_finger_down_do, True)
            if Di.getDi(ConfigParams.left_finger_down_di) and not Di.getDi(ConfigParams.left_finger_up_di):
                Do.setDo(ConfigParams.left_finger_down_do, False)
                self.left_finger_real_pos = 0
            if Di.getDi(ConfigParams.right_finger_down_di) and not Di.getDi(ConfigParams.right_finger_up_di):
                Do.setDo(ConfigParams.right_finger_down_do, False)
                self.right_finger_real_pos = 0
            if self.left_finger_real_pos == 0 and self.right_finger_real_pos == 0:
                self.finger_open_start = False
                return True
        return False

    def close_finger(self):
        Do.setDo(ConfigParams.left_finger_up_do, False)
        Do.setDo(ConfigParams.right_finger_up_do, False)
        Do.setDo(ConfigParams.left_finger_down_do, False)
        Do.setDo(ConfigParams.right_finger_down_do, False)

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

    def stretch(self, length):
        Trace.log(f"----- running stretch ------")
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
        Trace.log(f"----- running rotate ------")
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
            Do.setDo(self.fill_light_do, True)
            if Do.getDo(self.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.change_step[0] = True
        else:
            if self.rec_res and self.rec_res.get("status", 1) == 0:
                Do.setDo(self.fill_light_do, False)
                if self.rec_res['barCode'] != self.goods_id:
                    Abnormal.setTask(53711,
                                     f"货物编码不匹配, 任务下发的货物编码: {self.goods_id}, 识别的货物编码: {self.rec_res['barCode']}",
                                     "", "", "")
                    self.status = ScriptStatus.FAILED
                self.report_info["barCode"] = self.rec_res['barCode']
                return self.rec_res['barCode']
            else:
                if Timer.delay(0.05):
                    Recognize.doRec(ConfigParams.barcode_file, "", "")
                self.report_info["barCode"] = "None"
            self.report_info["recId"] = self.rec_id

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
            Do.setDo(self.fill_light_do, True)
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
                self.report_info["recQrcodeData"] = data
                self.rec.reset()
                Do.setDo(self.fill_light_do, False)
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
            Do.setDo(self.fill_light_do, True)
            Recognize.resetRec()  # 重置识别模块
            if Do.getDo(self.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.opt_step[2] = True
        else:
            Recognize.doRec(ConfigParams.box_code_file, "", "")  # 下发拍照指令
            if Timer.delay(0.5):
                Do.setDo(self.fill_light_do, False)
                self.status = ScriptStatus.FINISHED

    def load(self):
        Trace.log(f"----- running load  {self.goods_id}------")
        load_info = dict()
        if not self.cur_c:
            if (self.goods_id and Container.goodsExist(self.goods_id) and
                    Container.getContainerByGoods(self.goods_id) != "999"):
                Abnormal.setTask(53714, f"货物{self.goods_id}已存在，请检查是否重复下发任务！", "", "", "")
                self.status = ScriptStatus.FAILED
            if self.self_position:
                if Container.hasGoods(self.self_position):
                    Abnormal.setTask(53715,
                                     f"第{self.self_position + 1}层({self.self_position}号)背篓已有货物，无法继续取货！请核对任务数据和背篓数据！",
                                     "",
                                     "", "")
                    self.status = ScriptStatus.FAILED
                self.cur_c = self.self_position
            else:
                self.cur_c = self.search_operable_container('load')
            Trace.log(f"load begin: {json.dumps(self.containers)}")
            if self.cur_c is None:  # 车体满载了
                Abnormal.setTask(53716, f"车体所有背篓已满，无法继续取货！", "", "", "")
                self.status = ScriptStatus.FAILED
                return
            if Container.hasGoods("999") and Container.getGoodsByContainer("999") == self.goods_id:
                self.load_step[:9] = [True] * 9
            elif Container.hasGoods("999"):  # 货叉已载货,但不是目标货物
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
                        Do.setDo(self.fill_light_do, True)
                        self.light_st_time = time.time()
                    if time.time() - self.light_st_time > ConfigParams.light_delay_time:
                        if self.rec_adjust.status is ScriptStatus.FINISHED:
                            Do.setDo(self.fill_light_do, False)
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
                if Di.getDi(ConfigParams.left_finger_up_di) and Di.getDi(ConfigParams.right_finger_up_di):
                    self.load_step[6] = self.stretch(self.stretch_length)
                else:
                    Abnormal.setTask(53718, f"检测到拨指未打开，取消执行伸出动作！请检查拨指及其到位光电是否正常！", "",
                                     "", "")
                    self.status = ScriptStatus.FAILED
            elif self.load_step[6] and not self.load_step[7]:
                self.load_step[7] = self.finger(0)
            elif self.load_step[7] and not self.load_step[8]:
                self.load_step[8] = self.stretch(0)
                if self.load_step[8] and Di.getDi(ConfigParams.goods_check_di):
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
                self.load_step[14] = self.finger(0)
            elif self.load_step[14] and not self.load_step[15]:
                self.load_step[15] = self.lift_safe_height()

            load_info['curContainer'] = self.cur_c
            load_info['goodsName'] = self.goods_id
            load_info['loadStep'] = self.load_step
            load_info['lift-height'] = self.lift_height
            load_info['load-height'] = self.load_height
            load_info['lift-real-height'] = self.lift_real_pos
            self.report_info["loadInfo"] = load_info
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
                    self.in_take_step[4] = self.finger(0)
                elif self.in_take_step[4] and not self.in_take_step[5]:
                    self.in_take_step[5] = self.stretch(0)
                elif self.in_take_step[5] and not self.in_take_step[6]:
                    self.in_take_step[6] = self.rotate(self.rotate_pos)
                if self.in_take_step[5] and not self.in_take_step[7]:
                    self.in_take_step[7] = self.lift(self.lift_height)

        in_take_info["inTakeStep"] = self.in_take_step[:8]
        in_take_info["curContainer"] = self.cur_c
        in_take_info["goodsName"] = self.goods_id
        self.report_info["inTakeInfo"] = in_take_info
        if all(self.in_take_step[:8]):
            Container.clearContainer(self.cur_c)
            goods_id = Container.getGoodsByContainer(self.cur_c)
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
                self.in_put_step[6] = self.finger(0)
            if all(self.in_put_step[0:7]) and not self.in_put_step[7]:
                self.in_put_step[7] = self.lift_safe_height()
        Trace.log(f"----- running in_put ------")
        in_put_info = dict()
        in_put_info["goodsName"] = self.goods_id
        in_put_info["inPutStep"] = self.in_put_step[:7]
        self.report_info["inPutInfo"] = in_put_info
        if all(self.in_put_step[0:8]):
            goods_id = Container.getGoodsByContainer("999")
            Container.setContainer(self.cur_c, goods_id, "")
            Container.clearContainer("999")
            return True

    def ex_take(self):
        """
        外部取货： 从货架取货到货叉
        """
        if Container.hasGoods("999"):  # 抓斗有货
            Abnormal.setTask(53719, f"检测到货叉（999号）已载货，无法执行外部取货动作！请核对任务数据和背篓数据！", "", "",
                             "")
            self.status = ScriptStatus.FAILED
            return
        Trace.log(f"----- running ex_take ------")
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
                Do.setDo(self.fill_light_do, True)
                self.rec_adjust.status = ScriptStatus.RUNNING
                if Do.getDo(self.fill_light_do):
                    if Timer.delay(ConfigParams.light_delay_time):
                        self.change_step[2] = True
            if self.change_step[2] and not self.ex_take_step[3]:
                if self.rec_adjust.status is ScriptStatus.FINISHED:
                    Do.setDo(self.fill_light_do, False)
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
            self.ex_take_step[8] = self.finger(0)
        if all(self.ex_take_step[0:9]) and not self.ex_take_step[9]:
            self.ex_take_step[9] = self.stretch(0)
        # if all(self.ex_take_step[0:10]) and not self.ex_take_step[10]:
        #     self.ex_take_step[10] = self.rotate(0)

        ex_take_info['goodsName'] = self.goods_id
        ex_take_info['curContainer'] = self.cur_c
        ex_take_info['exTakeStep'] = self.ex_take_step[:10]
        self.report_info["exTakeInfo"] = ex_take_info
        if all(self.ex_take_step[:10]):
            Container.setContainer("999", self.goods_id, "")
            return True

    def ex_put(self):
        """
        外部放货： 从货叉放货到货架
        """
        Trace.log(f"----- running ex_put ------")
        if not Container.hasGoods("999"):  # 抓斗没货
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
                Do.setDo(self.fill_light_do, True)
                if Do.getDo(self.fill_light_do):
                    if Timer.delay(ConfigParams.light_delay_time):
                        self.ex_put_step[2] = True
            if all(self.ex_put_step[0:3]) and not self.ex_put_step[3]:
                if self.rec_box.status is ScriptStatus.FINISHED:
                    self.rec_box.reset()
                    self.rec_box.is_error = None
                    Do.setDo(self.fill_light_do, False)
                    if self.rec_box.hasGoods and not self.rec_box.goods_out_dist:
                        Abnormal.setTask(53720, "检测到货架上已经有货，取消放货动作！请人工核查货架和任务数据！", "", "",
                                         "")
                        self.status = ScriptStatus.FAILED
                        return
                    else:
                        self.ex_put_step[3] = True
                elif self.rec_box.status is ScriptStatus.FAILED:
                    Do.setDo(self.fill_light_do, False)
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
                    Do.setDo(self.fill_light_do, True)
                    self.rec_adjust.status = ScriptStatus.RUNNING
                    if Do.getDo(self.fill_light_do):
                        if Timer.delay(ConfigParams.light_delay_time):
                            self.change_step[0] = True
                else:
                    if self.rec_adjust.status is ScriptStatus.FINISHED:
                        Do.setDo(self.fill_light_do, False)
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
            self.ex_put_step[12] = self.finger(0)
        if all(self.ex_put_step[0:12]) and not self.ex_put_step[13]:
            self.ex_put_step[13] = self.lift_safe_height()

        ex_put_info["exPutStep"] = self.ex_put_step[:13]
        ex_put_info["goodsName"] = self.goods_id
        self.report_info["exPutInfo"] = ex_put_info
        if all(self.ex_put_step[:14]):
            Container.clearContainer("999")
            return True

    def unload(self):
        Trace.log(f"----- running unload ------")
        unload_info = dict()

        if not self.cur_c:
            if self.self_position:
                if Container.getGoodsByContainer(self.self_position) != self.goods_id:
                    Abnormal.setTask(53721,
                                     f"{self.self_position + 1}层({self.self_position}号)背篓中的货物Id与任务的货物ID({self.goods_id})不匹配！请核对任务数据和背篓数据！",
                                     "", "", "")
                    self.status = ScriptStatus.FAILED
                if not Container.hasGoods(self.self_position):
                    Abnormal.setTask(53722,
                                     f"{self.self_position + 1}层({self.self_position}号)背篓是空的，无法执行放货任务！请核对任务数据和背篓数据！",
                                     "", "", "")
                    self.status = ScriptStatus.FAILED
                if self.self_position != "999" and Container.hasGoods("999"):
                    # r.setError(f"料斗已载货，无法执行背篓的放货任务！请核对任务数据和背篓数据！")
                    Abnormal.setTask(53723, f"货叉（999号）已载货，无法执行背篓的放货任务！请核对任务数据和背篓数据！", "",
                                     "", "")
                    self.status = ScriptStatus.FAILED
                self.cur_c = self.self_position
            else:
                if Container.hasGoods("999"):  # 抓斗有货
                    self.cur_c = "999"
                    if Container.getGoodsByContainer("999") != self.goods_id:
                        # r.setError(f"料斗已载货，无法先执行背篓的放货任务，必须优先释放料斗的货物！")
                        Abnormal.setTask(53724, f"货叉（999号）已载货，无法先执行背篓的放货任务，必须优先释放货叉的货物！",
                                         "", "",
                                         "")
                        self.status = ScriptStatus.FAILED
                        return
                else:
                    self.cur_c = Container.getContainerByGoods(self.goods_id)

            if not self.cur_c:
                Abnormal.setTask(53725, f"背篓中不存在货物: {self.goods_id}，无法执行放货任务！请核对任务数据和背篓数据！",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
                return
            Trace.log(f"unload begin: {json.dumps(self.containers)}")
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
                    self.unload_step[4] = self.finger(0)
                elif self.unload_step[4] and not self.unload_step[5]:
                    if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                        if not self.unload_step[6]:
                            self.unload_step[6] = self.lift(self.lift_height)
                        if not self.unload_step[7]:
                            self.unload_step[7] = self.rotate(self.rotate_pos)
                    self.unload_step[5] = self.stretch(0)
                    if self.unload_step[5] and Di.getDi(ConfigParams.goods_check_di):
                        goods_id = Container.getGoodsByContainer(self.cur_c)
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
                                Do.setDo(self.fill_light_do, True)
                                if Do.getDo(self.fill_light_do):
                                    if Timer.delay(ConfigParams.light_delay_time):
                                        self.rec_box_lift_step[2] = True
                            if not self.rec_box_lift_step[3] and self.rec_box_lift_step[2]:
                                if self.rec_box.status is ScriptStatus.FINISHED:
                                    self.rec_box.reset()
                                    self.rec_box.is_error = None
                                    Do.setDo(self.fill_light_do, False)
                                    if self.rec_box.hasGoods and not self.rec_box.goods_out_dist:
                                        Abnormal.setTask(53726, "检测到货架上有货，取消放货动作！", "", "", "")
                                        self.status = ScriptStatus.FAILED
                                        return
                                    else:
                                        self.rec_box_lift_step[3] = True
                                elif self.rec_box.status is ScriptStatus.FAILED:
                                    Do.setDo(self.fill_light_do, False)
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
                        Do.setDo(self.fill_light_do, True)
                        self.rec_adjust.status = ScriptStatus.RUNNING
                        if Do.getDo(self.fill_light_do):
                            if Timer.delay(ConfigParams.light_delay_time):
                                self.change_step[0] = True
                    else:
                        if self.rec_adjust.status is ScriptStatus.FINISHED:
                            Do.setDo(self.fill_light_do, False)
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
                    self.unload_step[13] = self.finger(0)
                if not self.unload_step[14]:
                    self.unload_step[14] = self.rotate(0)
                if not self.unload_step[15]:
                    self.unload_step[15] = self.lift_safe_height()

            unload_info['unloadStep'] = self.unload_step
            unload_info['curContainer'] = self.cur_c
            unload_info['goodsName'] = self.goods_id
            self.report_info["unloadInfo"] = unload_info

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

    def has_goods_id(self, goods_id: str):
        Trace.log(f"goodsName: {goods_id}")
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
        """
        放货到背篓前，检查背篓有空位且货叉有货
        """
        if not Container.hasGoods("999"):  # 货叉无货
            Abnormal.setTask(53727, f"货叉（999号）没有货物，无需内部放货！", "", "", "")
            self.status = ScriptStatus.FINISHED
            return

        # 货物在背篓里
        if self.goods_id and Container.goodsExist(self.goods_id):
            Abnormal.setTask(53728, f"货物已存在", "", "", "")
            self.status = ScriptStatus.FINISHED
            return

        if self.self_position:
            if Container.hasGoods(self.self_position):
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
            if not Container.hasGoods(self.self_position):
                Abnormal.setTask(53731,
                                 f"第{self.self_position + 1}层({self.self_position}号)背篓是空的，无法执行内部取货动作！",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
            self.cur_c = self.self_position
        else:
            self.cur_c = Container.getContainerByGoods(self.goods_id)

        if Container.hasGoods("999"):  # 抓斗有货
            self.cur_c = "999"

        if not self.cur_c:
            Abnormal.setTask(53732, f"货物{self.goods_id}不存在，请核对货物编号和背篓数据！", "", "", "")
            self.status = ScriptStatus.FAILED
            return

    def safe_move_check(self):
        status = SafeMoveStatus.RUNNING
        if self.zero(0):
            status = SafeMoveStatus.FINISHED
        self.setSafeMoveStatus(status)
        Trace.log(f"safe_move_check {Module.getSafeMoveCheck()}")
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
            operation_code = parseModbus(op_data, 'uint16')
            print(f"   操作码: {operation_code}")
            # 根据操作码构建参数
            if operation_code == 1:
                args["operation"] = "load"
                # 读取高度参数
                height_data = NetProtocol.getModbusData("4x", 202, 2)
                if len(height_data) >= 2:
                    height = parseModbus(height_data, 'float')
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
                    angle_raw = parseModbus(angle_data, 'int16')
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
                    device_name = parseModbus(str_data, 'string', 0, len(str_data))
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
        self.hasGoods = None
        self.goods_out_dist = None
        self.max_goods_dist = 0.8  # 料箱距离货叉里程中心最远距离，单位：米
        Recognize.resetRec()
        Recognize.doRec(self.filename, "", "")

    def run(self, agv):
        self.status = ScriptStatus.RUNNING
        rec_status = Recognize.getRecStatus()  # 获取识别状态 0: 初始化, 1: 识别中, 2: 获得结果, 3：识别出错, -1: 未知错误
        if rec_status == 3 or rec_status == -1:  # 识别失败的状态
            Trace.log("rec failed:{}".format(self.result))
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
                    Recognize.doRec(self.filename, "", "")
        elif rec_status == 2:  # 识别成功,获得结果
            rec_results = Recognize.getRecResults()
            if "recoList" in rec_results:
                if len(rec_results["recoList"]) == 1:
                    self.result = rec_results["recoList"][0]
            if "resultImg" in self.result:
                self.result.pop("resultImg")
            Recognize.resetRec()
            self.hasGoods = True
            if self.result["x"] > self.max_goods_dist:
                self.goods_out_dist = True
            self.status = ScriptStatus.FINISHED
            Trace.log(f"rec success: {self.status.name} {self.result}")

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
                Trace.log(f"----- rec to adjust {self.rec.status.name}------")
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
                Trace.log("rec fail!!! {}".format(self.rec_fail_time))
            elif self.rec.status is ScriptStatus.FINISHED:
                Trace.log(f"------------------ move to adjust -----------------")
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
                self.go_args["maxSpeed"] = 0.3  # 设置二次调整时底盘移动最大速度, m/s
                self.go_args["maxAcc"] = 0.3
                self.go_args["maxDec"] = 0.3
                self.go_args["reachDist"] = 0.003
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                else:
                    self.go_args["backMode"] = 0

                if abs(agv.yaw_adjust) > ConfigParams.max_yaw_bias / 180 * math.pi:  # 角度转弧度比较
                    self.status = ScriptStatus.FAILED
                    Abnormal.setTask(53734,
                                     f"识别到角度偏差{agv.yaw_adjust / math.pi * 180:.2f}°超出上限值{ConfigParams.max_yaw_bias}°，请检查料箱是否摆正，二维码是否损坏！",
                                     "", "", "")
                else:
                    if self.adjust_count >= (self.max_adjust_time - 3):
                        agv.ok_x = 0.01
                        agv.ok_yaw = 1.15 / 180 * math.pi  # 约1.15°转弧度
                    # 精度满足, 识别调整任务完成
                    if not ConfigParams.auto_adjust_rotate and abs(self.rec.result['y']) < agv.ok_x:
                        Trace.log(f"adjust finished, adjust count: {self.adjust_count}")
                        self.status = ScriptStatus.FINISHED
                    elif ConfigParams.auto_adjust_rotate and abs(self.rec.result['y']) < agv.ok_x and abs(
                            agv.yaw_adjust) <= agv.ok_yaw:
                        Trace.log(f"adjust finished, adjust count: {self.adjust_count}")
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
                if not self.rotate_step and ConfigParams.auto_adjust_rotate:
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
                  f"{self.rec_fail_time}|{self.adjust_count}|{self.rec.rec_times}|{self.go_args.get('x', 0)}|")

    def reset(self):
        self.rec.reset()
        self.status = ScriptStatus.RUNNING
        self.rec_fail_time = 0
        self.goPath.reset()


def main():
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    RobotParam.setDeviceChangeCallBack(params_callback)
    Module.init()
    robot = ContainerRobot()
    validator = ParamValidator(InputParams.builder.toDict())
    modbus_args = None
    container_num = ConfigParams.get_container_count()
    # 如果container_num为数字且>0
    if isinstance(container_num, int) and container_num > 0:
        Container.initContainer(container_num)

    while True:
        # 脚本任务状态管理
        status = robot.status
        Module.setStatus(status)
        containers = Container.getContainers()
        robot.report_info['containers'] = containers
        Module.reportInfo(robot.report_info)
        robot.report_info["status"] = status
        if robot.event_safe_move_check:
            robot.safe_move_check()
        if robot.event_modbus:
            modbus_args = robot.modbus()
            robot.event_modbus = False
        if status == ScriptStatus.NONE:
            args = modbus_args or Module.getTaskArgs()
            if args:
                try:
                    # 验证参数
                    args = validator.validate(args)
                    debug_print("check ok, args:", json.dumps(args, indent=2))
                except ValueError as e:
                    print("check error:", e)
                # 调试任务拦截
                operation = args.get("operation", "")
                if not check_debug_task(operation):
                    Abnormal.setTask(53740,
                                     f"任务 '{operation}' 为调试任务，请先在脚本配置中开启 debugMode！",
                                     "", "", "")
                    continue
                robot = ContainerRobot()
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