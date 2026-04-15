# -*- coding: utf-8 -*-
# Author: zzm
# version: 2.0
# Time: 2025/12/25
# description:
# update:
#   2025/08/29 屏蔽激光，支持原地载货卸货
#   2025/09/04 适配识别文件识别面，不同坐标系，modbus
#   2025/12/25 增加取放货的 TCP，适配 DoMotor 的变轴距


import json
import math
import time
import struct
from enum import IntEnum
from typing import Optional, List, Dict, Any
from syspy import Module, Di, Do, Motor, Navigation, Loc, Recognize, ScriptStatus, \
    Odometer, Laser, NetProtocol, Trace, NavSpeed, Controller, NavStatus, ModuleBase, Container
from syspy.utils import Coordinate
from syspy.utils.time import Timer
from syspy.script_data import ScriptData
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, BindType, ScriptParam
from syspy.lib.module import pos2Base, pos2World, ModuleBase, SafeMoveStatus
from syspy.lib.net_protocol import parseModbus
from syspy.lib.robot_param import RobotParam
import standard.goBezier as GoBezier
from syspy import LevelDB
from syspy.core.rbk_rpc import Service

db = LevelDB("run")

# db.add("forkMileage", "float", False)
# db.add("forkMileageUp", "float", False)
# db.add("forkMileageDown", "float", False)
# db.add("forkMileageToday", "float", False)
# db.add("forkMileageUpToday", "float", False)
# db.add("forkMileageDownToday", "float", False)

param_loader = ScriptParam(__file__)


def clamp(val, lo, hi):
    return max(lo, min(val, hi))


EPS = 1e-6  # 浮点比较公差


def get_r_loc():
    r_loc = Loc.getPose()
    return [r_loc["x"], r_loc["y"], math.radians(r_loc["yaw"])]


def cal_dist(first_loc, second_loc):
    cur_dist = math.sqrt(
        (first_loc[0] - second_loc[0]) ** 2 + (first_loc[1] - second_loc[1]) ** 2)
    return cur_dist


def _robot_device_change_callback(device_change_set: List[str]):
    """机器人设备参数改变回调"""
    """设备参数变化回调"""
    if "Model" in device_change_set:
        ConfigParams.get_device_model_param()
    if "Motor" in device_change_set or "DOMotor" in device_change_set:
        ConfigParams.get_device_motor_param()
    # InputParams.init()


def _robot_config_change_callback(diff_map: Dict[str, Any]):
    """机器人配置参数变化回调"""
    pass
    # for key, value in diff_map.items():
    #     if key == "manualControl.manualBlock.on.manualSlowDownDist":
    #         robot_param["manualSlowDownDist"] = value
    #     elif key == "manualControl.manualBlock.on.manualStopAngle":
    #         robot_param["manualStopAngle"] = value
    #     elif key == "localizationType.2D.localizationLaser":
    #         robot_param["localizationLaser"] = value
    #     elif key == "basic.unload.maxSpeed":
    #         robot_param["unloadMaxSpeed"] = value
    #     elif key == "recognitionObject.pallet.carrierParameter.carrierHeight":
    #         robot_param["carrierHeight"] = value


def _script_config_callback():
    ConfigParams.reload_config()


class ConfigParams:
    """生成和定义配置参数的示例"""
    recCenterX: float = -1.0
    recCenterY: float = 0.0
    recRadius: float = 0.7
    chassis_type = ""
    module_type: str = ""
    shape: str = ""
    head: float = 0.0
    tail: float = 0.0
    width: float = 0.0
    module_x: float = 0.0
    fork_tip_width: float = 0.0
    center_distance_between_forks: float = 0.0
    fork_motor_name: str = ""
    shiftMotor = ""
    motor_func: str = ""
    min_height: float = 0.0
    max_height: float = 0.0
    up_di: str = ""
    down_di: str = ""
    fork_max_speed: float = 0.0
    base_shift: bool = False
    base_shift_length: float = 0.0
    fork_root_3D_camera: str = ""
    fork_root_2D_lasers: str = ""
    fork_tip_3D_cameras: list = []
    fork_tip_2D_lasers: list = []
    fork_tip_di_sensors: list = []
    fork_tip_distance_sensors: list = []
    contact_ids: list = []
    reach_up_dist: float = 0.001
    reach_down_dist: float = 0.001
    DOMotor: bool = False

    # 参数配置文件的参数
    config = {}

    # —— 脚本相关
    timeout: float = 120.0
    scriptDebug: bool = False
    # —— fork 相关
    upMaxSpeedWithGoods: float = 0.06
    downMaxSpeedWithGoods: float = 0.06
    backLaserEnableHeight: float = 0.3
    checkGoodsWhileLoad: bool = True
    checkAllContactDis: bool = False
    upDo: str = ""
    upDoStatus: bool = True
    downDo: str = ""
    downDoStatus: bool = True
    loadTime: float = 20.0
    unloadTime: float = 20.0
    # —— DO 控 fork
    downDelayTime: float = 10.0
    upDelayTime: float = 10.0
    downDiDoFork: str = ""
    upDiDoFork: str = ""
    leakDo: str = ""
    pumpDo: str = ""
    # —— 取放货
    laserDetectionWidth: float = 0.05
    loadUnloadCheck: bool = False
    aheadDist: float = 0.8
    minAheadDist: float = 1.0
    forkDiEnableAtLoad: bool = False
    forkDiEnableAtUnload: bool = False
    diTriggerMeasureUnload: str = ""
    pathAdjustMode: str = ""
    maxCurve: float = 3.0
    maxAngle: float = 10.0

    loadAdjustMaxSpeed: float = 0.5
    returnOnSamePath: bool = True
    forkDiDist: float = 0.1
    enableContactDiNoRec: bool = True
    enableTcp: bool = True
    loadObsStopDist: float = 0.05
    useForPalletFallProtection: bool = False
    setRoiX: float = 2
    setRoiMaxY: float = 1
    setRoiMinY: float = 1
    setRoiZ: float = 2

    # —— 线性堆栈
    laserWidth: float = 0.1
    obsDist: float = 0.5
    loadObsDist: float = 0.1
    # —— 识别区域
    obsAreaMinHeight: float = 0.0
    obsAreaMaxHeight: float = 0.0
    obsAreaLength: float = 0.0
    obsAreaWidth: float = 0.0
    deviceName: str = ""
    errorRecY: float = 0.1
    errorRecAngle: float = 15.0
    zMax: bool = True

    @classmethod
    def init(cls):
        """初始化所有设备参数"""
        cls.get_device_model_param()
        cls.get_device_motor_param()
        cls._build_and_load_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        Trace.log("Reloading config parameters")
        cfg = param_loader.loadConfig()
        cls.config = cfg

        # --- script
        cls.timeout = cfg.get("timeout", 120.0)
        cls.scriptDebug = cfg.get("scriptDebug", False)
        if cls.scriptDebug:
            Trace.log(f"Loaded config: {cls.config}")

        # --- fork
        cls.upMaxSpeedWithGoods = cfg.get("upMaxSpeedWithGoods")
        cls.downMaxSpeedWithGoods = cfg.get("downMaxSpeedWithGoods")
        cls.backLaserEnableHeight = cfg.get("backLaserEnableHeight")
        cls.checkGoodsWhileLoad = cfg.get("checkGoodsWhileLoad")
        cls.checkAllContactDis = cfg.get("checkAllContactDi")
        cls.loadTime = cfg.get("loadTime", 20.0)
        cls.unloadTime = cfg.get("unloadTime", 20.0)

        # --- forkByDO
        cls.downDelayTime = cfg.get("downDelayTime")
        cls.upDelayTime = cfg.get("upDelayTime")
        cls.downDiDoFork = cfg.get("downDiDoFork")
        cls.upDiDoFork = cfg.get("upDiDoFork")
        cls.leakDo = cfg.get("leakDo")
        cls.pumpDo = cfg.get("pumpDo")

        # --- loadUnload
        cls.laserDetectionWidth = cfg.get("laserDetectionWidth")
        cls.aheadDist = cfg.get("aheadDist")
        cls.minAheadDist = cfg.get("minAheadDist")
        cls.loadAdjustMaxSpeed = cfg.get("loadAdjustMaxSpeed")
        cls.returnOnSamePath = cfg.get("returnOnSamePath")
        cls.forkDiDist = cfg.get("forkDiDist")
        cls.enableContactDiNoRec = cfg.get("enableContactDiNoRec")
        cls.enableTcp = cfg.get("enableTcp")
        cls.loadObsStopDist = cfg.get("loadObsStopDist")
        cls.errorRecY = cfg.get("errorRecY")
        cls.errorRecAngle = cfg.get("errorRecAngle")
        cls.zMax = cfg.get("zMax")
        cls.recCenterX = cfg.get("recCenterX", 0.0)
        cls.recCenterY = cfg.get("recCenterY", 0.0)
        cls.recRadius = cfg.get("recRadius", 0.7)
        cls.pathAdjustMode = cfg.get("pathAdjustMode", "bezier")
        cls.maxCurve = cfg.get("maxCurve", 3.0)
        cls.maxAngle = cfg.get("maxAngle", 3.0)
        print(cls.pathAdjustMode, cls.maxCurve, cls.maxAngle)

        # --- linearUnload
        cls.laserWidth = cfg.get("laserWidth")
        cls.obsDist = cfg.get("obsDist")
        cls.loadObsDist = cfg.get("loadObsDist")

        # --- recognition
        cls.obsAreaMinHeight = cfg.get("obsAreaMinHeight")
        cls.obsAreaMaxHeight = cfg.get("obsAreaMaxHeight")
        cls.obsAreaLength = cfg.get("obsAreaLength")
        cls.obsAreaWidth = cfg.get("obsAreaWidth")
        cls.deviceName = cfg.get("deviceName")

        if cls.scriptDebug:
            Trace.log(f"Updated config: {cls.config}")

    # 从设备模型文件中获取的参数
    @classmethod
    def get_device_model_param(cls):
        cls.chassis_type = RobotParam.getDevice("Model-000", "chassisType")
        cls.module_type = RobotParam.getDevice("Model-000", "moduleType") or ""
        cls.fork_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.liftMotor") or ""
        cls.shiftMotor = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.shiftMotor")
        cls.shape = RobotParam.getDevice("Model-000", "shape") or ""
        cls.head = float(RobotParam.getDevice("Model-000", f"shape.{cls.shape}.head") or 0)
        cls.tail = float(RobotParam.getDevice("Model-000", f"shape.{cls.shape}.tail") or 0)
        cls.width = float(RobotParam.getDevice("Model-000", f"shape.{cls.shape}.width") or 0)
        cls.module_x = float(RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.installPosition.x") or 0)
        cls.fork_tip_width = float(RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkWidth") or 0)
        cls.center_distance_between_forks = float(
            RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.centerDistanceBetweenForks") or 0
        )

        cls.fork_root_3D_camera = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkRoot3DCamera")
        cls.fork_root_2D_lasers = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkRoot2DLasers")
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkTip3DCameras")
        cls.fork_tip_3D_cameras = _tmp_val.split(',') if _tmp_val else []
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkTip2DLasers")
        cls.fork_tip_2D_lasers = _tmp_val.split(',') if _tmp_val else []
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.diSensor")
        cls.fork_tip_di_sensors = _tmp_val.split(',') if _tmp_val else []
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.forkTipDistanceSensors")
        cls.fork_tip_distance_sensors = _tmp_val.split(',') if _tmp_val else []
        _tmp_val = RobotParam.getDevice("Model-000", f"moduleType.{cls.module_type}.id")
        cls.contact_ids = _tmp_val.split(',') if _tmp_val else []

        # 如果是搬运车，需要判断一下是否是变轴距的车
        if cls.module_type == "liftFork":
            Trace.log(f"chassis_type:{cls.chassis_type}")
            if cls.chassis_type in ("variableWheelbaseSingleStandardSteer", "variableWheelbaseSingleDifferentialSteer"):
                cls.base_shift = True
                ConfigParams.base_shift_length = float(
                    RobotParam.getDevice("Model-000", f"chassisType.{cls.chassis_type}.wheelBaseShiftLength") or 0
                )

    # 从设备模型文件中获取的参数
    @classmethod
    def get_device_motor_param(cls):
        """读取电机相关参数（线性电机）"""
        if cls.fork_motor_name.startswith("DOMotor"):
            ConfigParams.DOMotor = True
            cls.min_height = float(RobotParam.getDevice(f"{cls.fork_motor_name}", f"basic.minLength") or 0)
            cls.max_height = float(RobotParam.getDevice(f"{cls.fork_motor_name}", f"basic.maxLength") or 0)
        else:
            cls.motor_func = RobotParam.getDevice(f"{cls.fork_motor_name}", "func") or ""
            cls.min_height = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.minLength") or 0)
            cls.max_height = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.maxLength") or 0)
            cls.up_di = RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.upLimitDI")
            cls.down_di = RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.DownLimitDI")
            cls.fork_max_speed = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.maxSpeed") or 0)
            cls.reach_up_dist = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.reachUpDist") or 0)
            cls.reach_down_dist = float(
                RobotParam.getDevice(f"{cls.fork_motor_name}", f"func.{cls.motor_func}.reachDownDist") or 0)

    def get_app_rec_param(cls):
        pass

    # 设置脚本配置参数
    @classmethod
    def _build_and_load_config(cls):
        builder = param_loader.builderConfig()

        with builder.GROUPS():
            # ===== 脚本相关 =====
            with builder.GROUP(key="script", name="Script Settings", desc="脚本相关配置"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="timeout", name="Timeout", desc="脚本超时时间"):
                    builder.TYPE(ParamType.FLOAT)
                    builder.DEFAULTVALUE(200)
                    builder.UNIT("s")

                with builder.CHILD(key="scriptDebug", name="Script Debug", desc="是否打印调试信息"):
                    builder.TYPE(ParamType.BOOL)
                    builder.DEFAULTVALUE(False)

            # ===== fork 相关 =====
            with builder.GROUP(key="fork", name="Fork Settings", desc="货叉相关配置"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="loadAndUnloadCheck", name="Load And Unload Check",
                                       desc="取放货是否根据载货状态报错"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="upMaxSpeedWithGoods", name="Up Max Speed With Goods",
                                       desc="载货时的货叉上升最大速度"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.06, min_value=0, max_value=0.5)
                        builder.UNIT("m/s")
                    with builder.CHILD(key="downMaxSpeedWithGoods", name="Down Max Speed With Goods",
                                       desc="载货时的货叉下降最大速度"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.06, min_value=0, max_value=0.5)
                        builder.UNIT("m/s")
                    with builder.CHILD(key="backLaserEnableHeight", name="Back Laser Enable Height",
                                       desc="后置激光避障生效时的货叉高度"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3, min_value=0, max_value=2)
                        builder.UNIT("m")
                    with builder.CHILD(key="checkGoodsWhileLoad", name="Check Goods While Load",
                                       desc="载货时检测到位 di"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="loadTime", name="Load Time",
                                       desc="货叉上升超时时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(20.0, min_value=1, max_value=300)
                        builder.UNIT("s")
                    with builder.CHILD(key="unloadTime", name="Unload Time",
                                       desc="货叉下降超时时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(20.0, min_value=1, max_value=300)
                        builder.UNIT("s")
                    with builder.CHILD(key="upDo", name="UP DO", desc="升货叉时的 do"):
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.Device.DO)
                    with builder.CHILD(key="upDoStatus", name="Up Do Status", desc="升货叉时的 do 状态"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="downDo", name="Down DO", desc="降货叉时的 do"):
                        builder.TYPE(ParamType.BIND_TYPE)
                        builder.BINDTYPE(BindType.Device.DO)
                    with builder.CHILD(key="downDoStatus", name="Down Do Status", desc="降货叉时的 do 状态"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

            # ===== 取放货 =====
            with builder.GROUP(key="loadUnload", name="Load & Unload", desc="取放货相关配置"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="pathAdjustMode", name="Path Adjust Mode", desc="调整是否走直线曲线"):
                        builder.TYPE(ParamType.COMBO_BOX)
                        builder.DEFAULTVALUE("bezier")

                        with builder.CHILDREN():
                            with builder.CHILD(key="bezier", name="Bezier", desc="贝塞尔曲线"):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="maxCurve", name="Max Curve",
                                                       desc="贝塞尔曲线的最大曲率"):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(3)
                                        builder.UNIT("m")

                            with builder.CHILD(key="straightLine", name="Straight Line", desc="直线调整"):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="maxAngle", name="Max Angle",
                                                       desc="两段线调整的最大夹角"):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.DEFAULTVALUE(10)
                                        builder.UNIT("deg")

                    with builder.CHILD(key="returnOnSamePath", name="Return On Same Path",
                                       desc="识别调整后退出是否按原路返回"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)

                    with builder.CHILD(key="forkDiDist", name="Fork DI Dist", desc="盲插到位后后退距离"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.1, min_value=-2, max_value=2)
                        builder.UNIT("m")
                    if ConfigParams.fork_tip_2D_lasers:
                        with builder.CHILD(key="laserDetectionWidth", name="Load Laser Detection Width",
                                           desc="进叉时的激光宽度"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.DEFAULTVALUE(0.05, min_value=0, max_value=2)
                            builder.UNIT("m")
                    with builder.CHILD(key="loadObsStopDist", name="Load Obstacle Stop Distance",
                                       desc="取货时后退的避障距离"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05, min_value=0, max_value=2)
                        builder.UNIT("m")
                    with builder.CHILD(key="checkAllContactDi", name="Check All Contact DI",
                                       desc="需要先启用 di 检测，检测所有到位di"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

                    if ConfigParams.fork_tip_di_sensors:
                        with builder.CHILD(key="forkDiEnableAtLoad", name="Fork Di Enable At Load",
                                           desc="取货时是否启用叉尖 di sensor，false 为屏蔽防止阻挡"):
                            builder.TYPE(ParamType.BOOL)
                            builder.DEFAULTVALUE(False)

                        with builder.CHILD(key="forkDiEnableAtUnload", name="Fork Di Enable At Unload",
                                           desc="放货时是否启用叉尖 di sensor"):
                            builder.TYPE(ParamType.COMBO_BOX_BOOL)
                            builder.DEFAULTVALUE("on")
                            with builder.CHILDREN():
                                # on选项
                                with builder.CHILD(key="on", name="Fork Di Enable At Unload",
                                                   desc="forkDiEnableAtUnload"):
                                    builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILD(key="diTriggerMeasureUnload", name="Di Trigger Measure Unload",
                                                       desc="放货时di触发时的机器人的方式"):
                                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                                        builder.DEFAULTVALUE("collision")
                                        with builder.CHILDREN():
                                            with builder.CHILD("collision", "Collision", "报阻挡"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("autoClearError", "Auto Clear Error",
                                                               "触发时报错有货，不触发时继续任务"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("failTask", "Fail Task", "触发结束任务"):
                                                builder.TYPE(ParamType.STRING)

                                # off选项
                                with builder.CHILD(key="off", name="Fork Di Disable At Unload",
                                                   desc="fork Di Disable At Unload"):
                                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="recLoad", name="Recognition Load",
                                       desc="识别取货"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            # 需要移到 bintask
                            with builder.CHILD(key="zMax", name="sort the rec results by height",
                                               desc="根据识别结果的高度由大到小进行排序"):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(False)
                            with builder.CHILD(key="errorRecY", name="Error Rec Y",
                                               desc="识别结果相对AP点报错的y偏移，-1不启用"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.1)
                                builder.UNIT("m")
                            with builder.CHILD(key="errorRecAngle", name="Error Rec Angle",
                                               desc="识别结果相对AP点报错的yaw偏移，-1不启用"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(15)
                                builder.UNIT("°")
                            with builder.CHILD(key="enableTcp", name="Enable TCP", desc="识别取货是否启用 tcp"):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(False)
                            with builder.CHILD(key="aheadDist", name="Ahead Dist", desc="识别取货的前置距离"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.8, min_value=0, max_value=2)
                                builder.UNIT("m")
                            with builder.CHILD(key="minAheadDist", name="Min Ahead Dist",
                                               desc="识别取货的最小直线距离"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(ConfigParams.tail + 0.1, min_value=-2, max_value=2)
                                builder.UNIT("m")
                            with builder.CHILD(key="recCenterX", name="Rec Center X",
                                               desc="不指定AP点时，机器人坐标系下识别区域中心X坐标"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(-(ConfigParams.tail + 0.3), min_value=-5, max_value=5)
                                builder.UNIT("m")
                            with builder.CHILD(key="recCenterY", name="Rec Center Y",
                                               desc="不指定AP点时，机器人坐标系下识别区域中心Y坐标"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.0, min_value=-5, max_value=5)
                                builder.UNIT("m")
                            with builder.CHILD(key="recRadius", name="Rec Radius",
                                               desc="识别半径"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(0.7, min_value=0.1, max_value=5)
                                builder.UNIT("m")
                    with builder.CHILD(key="noRecLoad", name="Load By Landmark",
                                       desc="根据站点位置取货"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            with builder.CHILD(key="enableContactDiNoRec", name="Enable Contact DI (No Rec)",
                                               desc="盲叉取货是否启用到位di"):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="useForPalletFallProtection", name="Use For Pallet Fall Protection",
                                       desc="取放货时是否启用货物脱离检测"):
                        builder.TYPE(ParamType.COMBO_BOX_BOOL)
                        builder.DEFAULTVALUE("off")
                        with builder.CHILDREN():
                            # off选项
                            with builder.CHILD(key="off", name="Disable Pallet Fall Protection",
                                               desc="Disable Pallet Fall Protection"):
                                builder.TYPE(ParamType.ARRAY)

                            # on选项
                            with builder.CHILD(key="on", name="Enable Pallet Fall Protection",
                                               desc="using extern IMU"):
                                builder.TYPE(ParamType.ARRAY)

                                with builder.CHILDREN():
                                    with builder.CHILD(key="setRoiX", name="Set Roi X",
                                                       desc=""):
                                        builder.TYPE(ParamType.FLOAT)
                                        builder.REQUIRED(True)
                                        builder.DEFAULTVALUE(2.0)
                                with builder.CHILD(key="setRoiMaxY", name="Set Roi Max Y",
                                                   desc=""):
                                    builder.TYPE(ParamType.FLOAT)
                                    builder.REQUIRED(True)
                                    builder.DEFAULTVALUE(2.0)
                                with builder.CHILD(key="setRoiMinY", name="Set Roi Min Y",
                                                   desc=""):
                                    builder.TYPE(ParamType.FLOAT)
                                    builder.REQUIRED(True)
                                    builder.DEFAULTVALUE(2.0)
                                with builder.CHILD(key="setRoiZ", name="Set Roi Z",
                                                   desc=""):
                                    builder.TYPE(ParamType.FLOAT)
                                    builder.REQUIRED(True)
                                    builder.DEFAULTVALUE(2.0)

            # ===== 线性堆栈 =====
            with builder.GROUP(key="linearUnload", name="Linear Unload", desc="线性堆栈相关配置"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="laserWidth", name="Laser Width", desc="线性堆栈激光宽度"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.1, min_value=0, max_value=1)
                        builder.UNIT("m")
                    with builder.CHILD(key="obsDist", name="Obs Dist", desc="线性堆栈的避障距离"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5, min_value=0, max_value=1)
                        builder.UNIT("m")
                    with builder.CHILD(key="loadObsDist", name="Load Obs Dist", desc="取货进叉时的避障距离"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.1, min_value=0, max_value=11)
                        builder.UNIT("m")

            # # ===== 识别 =====
            # with builder.GROUP(key="recognition", name="Recognition", desc="检测货物有无相关"):
            #     builder.TYPE(ParamType.ARRAY)
            #     with builder.CHILDREN():
            #         with builder.CHILD(key="zMax", name="sort the rec results by height",
            #                            desc="根据识别结果的高度由大到小进行排序"):
            #             builder.TYPE(ParamType.BOOL)
            #             builder.DEFAULTVALUE(True)
            #         with builder.CHILD(key="obsAreaMinHeight", name="Obs Area Min Height", desc="检测区域最低高度"):
            #             builder.TYPE(ParamType.FLOAT)
            #             builder.DEFAULTVALUE(0.0)
            #             builder.UNIT("m")
            #         with builder.CHILD(key="obsAreaMaxHeight", name="Obs Area Max Height", desc="检测区域最高高度"):
            #             builder.TYPE(ParamType.FLOAT)
            #             builder.DEFAULTVALUE(0.0)
            #             builder.UNIT("m")
            #         with builder.CHILD(key="obsAreaLength", name="Obs Area Length", desc="检测区域长度"):
            #             builder.TYPE(ParamType.FLOAT)
            #             builder.DEFAULTVALUE(0.0)
            #             builder.UNIT("m")
            #         with builder.CHILD(key="obsAreaWidth", name="Obs Area Width", desc="检测区域宽度"):
            #             builder.TYPE(ParamType.FLOAT)
            #             builder.DEFAULTVALUE(0.0)
            #             builder.UNIT("m")
            #         with builder.CHILD(key="deviceName", name="Device Name", desc="检测设备名称"):
            #             builder.TYPE(ParamType.STRING)
            #             builder.DEFAULTVALUE("")

        builder.save(merge=True)
        cls.reload_config()


ConfigParams.init()


def create_fork_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    """创建顶升高度参数（可复用）"""
    with builder.CHILD(key="height", name="Fork Height",
                       desc="The height for lift operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        # builder.MIN_VALUE(min_height)
        # builder.MAX_VALUE(max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_end_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="endHeight", name="End Height",
                       desc="The fork height after load"):
        builder.TYPE(ParamType.FLOAT)
        # builder.REQUIRED(True)
        # builder.MIN_VALUE(min_height)
        # builder.MAX_VALUE(max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_start_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="startHeight", name="Start Height",
                       desc="The fork height before load"):
        builder.TYPE(ParamType.FLOAT)
        # builder.REQUIRED(True)
        # builder.MIN_VALUE(min_height)
        # builder.MAX_VALUE(max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_rec_param(builder: ParamBuilder):
    # 识别参数
    with builder.CHILD(key="recognize", name="Recognition",
                       desc="Enable pallet recognition"):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE("off")

        with builder.CHILDREN():
            # off 选项，不需要填识别文件
            with builder.CHILD(key="off", name="Recognize",
                               desc="Load Without Recognition"):
                builder.TYPE(ParamType.ARRAY)

            # on 也就是勾选需要识别后才会需要填写识别文件
            with builder.CHILD(key="on", name="Recognize",
                               desc="Load With Recognition"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="recfile", name="Recfile",
                                   desc="Recognition file name"):
                    builder.TYPE(ParamType.STRING)
                    builder.DEFAULTVALUE("default.srec")

                with builder.CHILD(key="recSide", name="Rec Side",
                                   desc="Rec Side"):
                    builder.TYPE(ParamType.STRING)
                    builder.DEFAULTVALUE("A")

                with builder.CHILD(key="recHeight", name="Rec Height",
                                   desc="The fork height before load after rec"):
                    builder.TYPE(ParamType.FLOAT)
                    # builder.REQUIRED(True)
                    # builder.MIN_VALUE(min_height)
                    # builder.MAX_VALUE(max_height)
                    builder.UNIT("m")
                    builder.SINGLESTEP(0.01)
                    builder.DEFAULTVALUE(0.1)


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    @classmethod
    def init(cls):
        min_height = ConfigParams.min_height
        max_height = ConfigParams.max_height

        with cls.builder.GROUPS():
            # 公共参数:
            # 使用PGV参数
            # with builder.CHILD(key="use_pgv", name="Use PGV", desc="Use PGV for position adjustment"):
            #     builder.TYPE(ParamType.BOOL)
            #     builder.DEFAULTVALUE(False)

            # 操作组合框
            with cls.builder.GROUP(key="operation", name="Operations", desc="Task script input parameters"):
                cls.builder.TYPE(ParamType.COMBO_BOX)

                with cls.builder.CHILDREN():
                    # 取货操作
                    with cls.builder.CHILD(key="load", name="Fork Load", desc="load the pallet"):
                        cls.builder.TYPE(ParamType.ARRAY)

                        with cls.builder.CHILDREN():
                            # 取货路径导航前的货叉高度
                            create_start_height_param(cls.builder, min_height, max_height)

                            # 取完后的货叉高度
                            create_end_height_param(cls.builder, min_height, max_height)

                            # 识别参数
                            create_rec_param(cls.builder)

                            # 如果需要脱离库位，则多一个参数
                            with cls.builder.CHILD(key="leaveLocHeight", name="Leave Loc Height",
                                                   desc="The fork height after leave loc"):
                                cls.builder.TYPE(ParamType.FLOAT)
                                # builder.REQUIRED(True)
                                # builder.MIN_VALUE(min_height)
                                # builder.MAX_VALUE(max_height)
                                cls.builder.UNIT("m")
                                cls.builder.SINGLESTEP(0.01)
                                cls.builder.DEFAULTVALUE(-1)

                    # 放货操作
                    with cls.builder.CHILD(key="unload", name="Fork Unload",
                                           desc="unload the pallet"):
                        cls.builder.TYPE(ParamType.ARRAY)

                        with cls.builder.CHILDREN():
                            # 取货路径导航前的货叉高度
                            create_start_height_param(cls.builder, min_height, max_height)

                            # 取完后的货叉高度
                            create_end_height_param(cls.builder, min_height, max_height)

                            # 如果需要脱离库位，则多一个参数
                            with cls.builder.CHILD(key="leaveLocHeight", name="Leave Loc Height",
                                                   desc="The fork height after leave loc"):
                                cls.builder.TYPE(ParamType.FLOAT)
                                # builder.REQUIRED(True)
                                # builder.MIN_VALUE(min_height)
                                # builder.MAX_VALUE(max_height)
                                cls.builder.UNIT("m")
                                cls.builder.SINGLESTEP(0.01)
                                cls.builder.DEFAULTVALUE(-1)

                    # ForkHeight 操作
                    with cls.builder.CHILD(key="forkHeight", name="Fork Height",
                                           desc="Lift the fork"):
                        cls.builder.TYPE(ParamType.ARRAY)
                        create_fork_height_param(cls.builder, min_height, max_height)

                        with cls.builder.CHILD(key="forkSpeed", name="Fork Speed", desc="fork lift speed"):
                            cls.builder.TYPE(ParamType.FLOAT)
                            cls.builder.SINGLESTEP(0.01)
                            # builder.REQUIRED(True)
                            cls.builder.DEFAULTVALUE(ConfigParams.fork_max_speed)

                    # 脱离库位操作
                    with cls.builder.CHILD(key="leaveLoc", name="Leave Loc",
                                           desc="Leave loc after load"):
                        cls.builder.TYPE(ParamType.ARRAY)

                        with cls.builder.CHILDREN():
                            create_end_height_param(cls.builder, min_height, max_height)

                    with cls.builder.CHILDREN():
                        # 料笼堆叠
                        with cls.builder.CHILD(key="cageStack", name="Cage Stack", desc="stack the cage"):
                            cls.builder.TYPE(ParamType.ARRAY)

                            with cls.builder.CHILDREN():
                                # 取货路径导航前的货叉高度
                                create_start_height_param(cls.builder, min_height, max_height)

                                # 取完后的货叉高度
                                create_end_height_param(cls.builder, min_height, max_height)

                                # 识别参数
                                create_rec_param(cls.builder)

                    if ConfigParams.scriptDebug:
                        with cls.builder.CHILD(key="rec", name="Rec", desc="Rec the pallet"):
                            cls.builder.TYPE(ParamType.ARRAY)

                            with cls.builder.CHILD(key="recfile", name="Recognition File Name",
                                                   desc="Recognition file name"):
                                cls.builder.TYPE(ParamType.STRING)
                                cls.builder.DEFAULTVALUE("default.srec")

                        with cls.builder.CHILD(key="deleteClearRegion", name="Delete Clear Region",
                                               desc="Delete Clear Region"):
                            cls.builder.TYPE(ParamType.ARRAY)

                        with cls.builder.CHILD(key="test", name="Test",
                                               desc="test"):
                            cls.builder.TYPE(ParamType.ARRAY)

                            cls.builder.TYPE(ParamType.ARRAY)

                            with cls.builder.CHILDREN():
                                # 取货路径导航前的货叉高度
                                create_start_height_param(cls.builder, min_height, max_height)

                                # 取完后的货叉高度
                                create_end_height_param(cls.builder, min_height, max_height)

                                # 识别参数
                                create_rec_param(cls.builder)

            if ConfigParams.scriptDebug:
                with cls.builder.CHILD(key="targetName", name="Target Name", desc="Target ID Name"):
                    cls.builder.TYPE(ParamType.STRING)
                    cls.builder.DEFAULTVALUE("AP1")

        cls.builder.save_to_file()


InputParams.init()

param_loader.addAction(
    action_name="Fork Load",
    policy={},
    args={
        "operation": "load",
        "operation.load.startHeight": 0.1,
        "operation.load.endHeight": 0.1,
        "operation.load.recognize": 0,
        "operation.load.leaveLocHeight": -1,
    },
    config={}
)

param_loader.addAction(
    action_name="Fork UnLoad",
    policy={},
    args={
        "operation": "unload",
        "operation.unload.startHeight": 0.1,
        "operation.unload.endHeight": 0.1,
        "operation.unload.leaveLocHeight": -1,
    },
    config={}
)

param_loader.addAction(
    action_name="Fork Height",
    policy={},
    args={
        "operation": "forkHeight",
        "operation.forkHeight.height": 0.1,
        "operation.forkHeight.forkSpeed": ConfigParams.fork_max_speed,
    },
    config={}
)

param_loader.addAction(
    action_name="Leave Loc",
    policy={},
    args={
        "operation": "leaveLoc",
        "operation.leaveLoc.endHeight": 0.1,
    },
    config={}
)

param_loader.addAction(
    action_name="Cage Stack",
    policy={},
    args={
        "operation": "cageStack",
        "operation.cageStack.startHeight": 0.1,
        "operation.cageStack.endHeight": 0.1,
        "operation.cageStack.recognize": 0,
    },
    config={}
)

param_loader.saveAction()


def float32_to_regs(value: float):
    """float32 转成两个寄存器（小端：低位在前）"""
    raw = struct.pack("!f", value)  # 转成 4 字节
    word1 = int.from_bytes(raw[2:], "big")  # 低地址寄存器 = 低 16 位
    word2 = int.from_bytes(raw[:2], "big")  # 高地址寄存器 = 高 16 位
    return [word1, word2]


def float_to_modbus_poll_regs(value: float):
    """
    将 float 数值转换为两个 uint16 的 Modbus Poll 寄存器值，符合小端序（B0 B1 B2 B3 → reg1 = B3B2, reg2 = B1B0）
    """
    # 强制 float32 精度（模拟 numpy.float32）
    value = struct.unpack('<f', struct.pack('<f', value))[0]

    # 打包为小端 float32，结果是字节数组 [B0, B1, B2, B3]
    packed = struct.pack('<f', value)
    b0, b1, b2, b3 = packed

    # 拼成两个 uint16 寄存器，顺序为：reg1 = B3B2，reg2 = B1B0
    reg1 = (b1 << 8) + b0
    reg2 = (b3 << 8) + b2

    return [reg1, reg2]


def delete_deduct_area(names, coordinate):
    if not names:  # names 为空 → 删除全部
        deduct_area_list = Navigation.getClearRegion(coordinate)
    else:
        if isinstance(names, str):
            names = [names]
        deduct_area_list = [
            s for s in Navigation.getClearRegion(coordinate)
            if s.startswith(tuple(names))
        ]

    for region in deduct_area_list:
        Navigation.deleteClearRegion(region, coordinate)


def set_deduct_area(area_infos, base_pos, prefix: str, coordinate):
    """
    扣除栈板相关的内容，区域名称以PalletRobotDeductArea[idx]命名
    """
    for info_idx, info in enumerate(area_infos):
        devices = info["deduct_device"]
        for area_idx, area in enumerate(info["areas"], start=1):
            x_coords, y_coords = [], []

            for x, y in zip(area["x"], area["y"]):
                wx, wy, wz = pos2World([x, y, 0], base_pos)
                x_coords.append(wx)
                y_coords.append(wy)

            # 区域合法性检查
            if len(x_coords) < 3 or len(x_coords) != len(y_coords):
                Trace.log(f"skip invalid area idx={area_idx}, device={devices}")
                continue

            region_name = f"{prefix}{info_idx + 1}_{area_idx}"
            Navigation.setClearRegion(
                region_name,
                x_coords,
                y_coords,
                devices,  # 支持一个或多个 device
                coordinate,
            )

            Trace.log(f"set clear region: {region_name}, devices={devices}")


def get_deduct_area(recfile):
    """
    解析 pallet 障碍物扣除区域配置。
    返回格式:
    [
        {
            "deduct_device": ["Laser-003"],
            "areas": [
                {"x": [...], "y": [...]},
                {"x": [...], "y": [...]}
            ]
        },
        ...
    ]
    """
    recognition_obstacle_deduction_path = "recognitionObject.pallet.obstacleDeduction"
    size = RobotParam.getConfigCloneSize("recognition", recognition_obstacle_deduction_path, recfile)

    result = []

    if size is None:
        Navigation.setTaskError("NoDeductShape", f"no deductShape in recfile")
        return []

    for i in range(size):
        # 获取设备ID
        device_str = RobotParam.getConfig(
            "recognition",
            f"{recognition_obstacle_deduction_path}._{i}.deductDevice",
            recfile,
        )
        if not device_str:
            continue
        devices = [d for d in device_str.split(",") if d.strip()]

        # 获取形状信息
        shape_str = RobotParam.getConfig(
            "recognition",
            f"{recognition_obstacle_deduction_path}._{i}.deductShape",
            recfile,
        )
        if not shape_str:
            continue
        shapes = json.loads(shape_str)

        areas = []
        for shape in shapes:
            pts = shape.get("points", [])
            if len(pts) < 3:  # 至少3个点才构成区域
                continue
            x_list = [p["x"] for p in pts]
            y_list = [p["y"] for p in pts]
            areas.append({"x": x_list, "y": y_list})

        if devices and areas:
            result.append({"deduct_device": devices, "areas": areas})

    Trace.log(f"pallet_deduct_infos: {result}")
    return result


def get_rec_side_info(recfile, rec_side):
    recognitionSide_key = "recognitionObject.pallet.recognitionSide"
    recognitionSide_size = RobotParam.getConfigCloneSize("recognition", recognitionSide_key, recfile)
    rec_sides = []

    for i in range(recognitionSide_size):
        side_value = RobotParam.getConfig("recognition", f"{recognitionSide_key}._{i}", recfile)
        # coordinateSystem = RobotParam.getConfig(
        #     "recognition",
        #     f"{recognitionSide_key}._{i}.{side_value}.coordinateSystem",
        #     recfile
        # )
        enableCargoContactDI = RobotParam.getConfig(
            "recognition",
            f"{recognitionSide_key}._{i}.{side_value}.enableCargoContactDI",
            recfile
        )
        enableBackDistance = RobotParam.getConfig(
            "recognition",
            f"{recognitionSide_key}._{i}.{side_value}.enableBackDistance",
            recfile
        )

        side_info = {
            "side_value": side_value,
            # "coordinateSystem": coordinateSystem,  # 3.5.4 proto变更取消字段
            "enableCargoContactDI": enableCargoContactDI,
            "enableBackDistance": enableBackDistance
        }

        if enableBackDistance == "on":
            backDistance = RobotParam.getConfig(
                "recognition",
                f"{recognitionSide_key}._{i}.{side_value}.enableBackDistance.{enableBackDistance}.backDistance",
                recfile
            )
            side_info["backDistance"] = backDistance

        rec_sides.append(side_info)

    if rec_side:
        rec_info = next((s for s in rec_sides if s["side_value"] == rec_side), None)
        if rec_info is None:
            Navigation.setTaskError("RecSideError", f"Recognition side {rec_side} is not match in {recfile}, script failed")
            Trace.log(f"input rec_side:{rec_side}, rec_info: None, rec_sides:{rec_sides}")
            return None
    else:
        if len(rec_sides) == 0:
            Navigation.setTaskError("RecSideError", f"RecSide is not config in {recfile}, script failed")
            Trace.log(f"no rec side in {recfile}", True, True)
            return None
        rec_info = rec_sides[0]

    Trace.log(f"input rec_side:{rec_side}, rec_info:{rec_info}, rec_sides:{rec_sides}")
    return rec_info


def parse_shapes(json_str):
    """
       输入: JSon 字符串（来自 RobotParam.getConfig）
       输出: [
                [{"x":..,"y":..}, {"x":..,"y":..}, ...],
                [{"x":..,"y":..}, {"x":..,"y":..}, ...]
             ]
       """
    if not json_str:
        return []
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
    except json.JSonDecodeError:
        return []

    points = []
    for obj in data:
        for p in obj.get("points", []):
            points.append({"x": p["x"], "y": p["y"]})
    return points


def convex_hull(points1, points2=None, points3=None):
    """输入三组 [{'x':..,'y':..},...] 点，输出凸包 [{'x':..,'y':..},...]"""

    # 合并三组点
    all_points = []
    for group in (points1, points2, points3):
        if group:  # 可能为空
            for p in group:
                all_points.append((float(p["x"]), float(p["y"])))

    # 去重 & 排序
    pts = sorted(set(all_points))
    if len(pts) <= 1:
        return [{"x": x, "y": y} for x, y in pts]

    # 叉积
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    # 下凸壳
    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    # 上凸壳
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    return [{"x": x, "y": y} for x, y in hull]


def _flat_attrs(action, idx1: int):
    """把 action 展平为 {1.Class.attr: value, ...}"""
    snap = {}
    cls = action.__class__.__name__
    for name in dir(action):
        if name.startswith("_"):
            continue
        try:
            val = getattr(action, name)
            if not callable(val):
                # 尝试序列化，不行就转成 str
                try:
                    # 尝试序列化
                    json.dumps(val)
                    safe_val = val
                except TypeError:
                    # 序列化失败就转字符串
                    safe_val = str(val)
                snap[f"action.{idx1}.{cls}.{name}"] = safe_val
        except Exception:
            pass
    return snap


class Fork(ModuleBase):
    def __init__(self):
        super().__init__()

        # 栈板扣除区域 还是以前表面为中心点
        self.leave_loc_height = -1
        self.rec_height = -1
        self.cage_count = 0

        self.start_loc = []
        self.recognize = False
        self.fork_height = 0.
        self.carrier_length = 0
        self.carrier_width = 0
        self.pallet_deduct_infos = None
        self.obstacle_polygon_by_rec = []
        self.no_rec_deduct_pallet_area = [{"x": 0, "y": 0.6},
                                          {"x": -1.2, "y": 0.6},
                                          {"x": -1.2, "y": -0.6},
                                          {"x": 0, "y": -0.6}]

        self.clear_fork_region_by_height = False
        self.set_fork_region_by_height = False
        self.name_left = "back_laser_clear_left"
        self.name_right = "back_laser_clear_right"
        self.back_laser_clear_region_name = "back_laser_clear_region"

        self.outer = (ConfigParams.center_distance_between_forks + ConfigParams.fork_tip_width) / 2
        self.inner = (ConfigParams.center_distance_between_forks - ConfigParams.fork_tip_width) / 2
        self.points_left = [{"x": ConfigParams.module_x, "y": -self.outer},
                            {"x": -ConfigParams.tail, "y": -self.outer},
                            {"x": -ConfigParams.tail, "y": -self.inner},
                            {"x": ConfigParams.module_x, "y": -self.inner}]
        self.points_right = [{"x": ConfigParams.module_x, "y": self.outer},
                             {"x": -ConfigParams.tail, "y": self.outer},
                             {"x": -ConfigParams.tail, "y": self.inner},
                             {"x": ConfigParams.module_x, "y": self.inner}]
        # 叉车车头后面那块区域
        self.fork_points = [{"x": ConfigParams.module_x + 0.05, "y": ConfigParams.width / 2},
                            {"x": -ConfigParams.tail, "y": ConfigParams.width / 2},
                            {"x": -ConfigParams.tail, "y": -ConfigParams.width / 2},
                            {"x": ConfigParams.module_x + 0.05, "y": -ConfigParams.width / 2}]
        self.carrier_shape = []

        self.check_di = False
        self.back_dist = 0
        self.task_args = {}
        self.forkSpeed = 0.
        self.endHeight = 0.
        self.recfile = ""

        self.target_pos = [0, 0, 0, -1]
        self.rec_params = dict()
        self.start_time = None
        self.init_args = False
        self.action_id = 0
        self.action_list = list()
        self.operation_init = False
        self.script_status = ScriptStatus.NONE
        self.action_status = ActionStatus.INIT
        # 识别相关
        self.rec_result = dict()
        # 定义脚本运行相关的成员变量
        self.opt = ""
        self.min_safe_height = 0.0  # 最小安全高度，fork 高于此高度时跳过后激光碰撞检测；0 表示禁用
        self.hasReachDi = None
        self.fork_cur_height = None
        self.motor_infos = dict()
        self.nav_speed = dict()
        self.is_goods_detected = None
        self.goPathArgs = None  # 堆栈的终点坐标点
        self.move_task = dict()
        self.first_point = None
        self.second_path = None
        self.first_point_return = None
        self.second_path_return = None
        self.pallet_width = 0
        self.cur_state = {}
        self.rec_sides = []
        self.move_info = {}
        self.trace_chart = {}
        self.rec_info = {}
        self.pallet_deduct_info = {}
        self.fork_height_in_place = True
        self.current_action = None

        # 处理货叉里程数据

        self.mileage_total_key = "forkMileage"
        self.mileage_up_key = "forkMileageUp"
        self.mileage_down_key = "forkMileageDown"
        self.key_today_total_mileage = "forkMileageToday"
        self.key_today_up_mileage = "forkMileageUpToday"
        self.key_today_down_mileage = "forkMileageDownToday"
        self.key_today_date = "fork_mileage_today_date"

        self.total_dist = db.get(self.mileage_total_key, "float")
        self.up_dist = db.get(self.mileage_up_key, "float")
        self.down_dist = db.get(self.mileage_down_key, "float")
        self.today_total = db.get(self.key_today_total_mileage, "float")
        self.today_up = db.get(self.key_today_up_mileage, "float")
        self.today_down = db.get(self.key_today_down_mileage, "float")

        self.last_saved_total = self.total_dist  # ← 记录上次保存值
        self.last_pos = None
        self.last_save_ts = time.time()
        self.save_interval = 5  # 写数据库时间
        Container.initContainer(0)

    def run(self, args):

        if not self.init_args:
            self.script_status = ScriptStatus.RUNNING
            self.action_status = ActionStatus.INIT
            self.current_action = None
            self.init_args = True
            self.operation_init = False
            self.task_args = args
            self.action_id = 0
            self.action_list = []
            self.min_safe_height = 0.0  # 每次新任务复位，_init_args 会重新解析
            Trace.log(f"script args:{self.task_args}")
            self._init_args()

        self._check_timeout()

        if self.opt == "load":
            self.load()
        elif self.opt == "unload":
            self.unload()
        elif self.opt == "forkHeight":
            self.fork_move()
        elif self.opt == "rec":
            self.rec()
        elif self.opt == "leaveLoc":
            self.leave_loc()
        elif self.opt == "test":
            self.test()
        elif self.opt == "deleteClearRegion":
            self.delete_clear_region()
        elif self.opt == "cageStack":
            self.cage_stack()
        else:
            Navigation.setTaskError("WrongOperation", f"wrong operation:{self.opt}, script failed")
            self.script_status = ScriptStatus.FAILED
            return
        self._execute_actions()
        if self.action_status == ActionStatus.FAILED:
            self.script_status = ScriptStatus.FAILED

    def suspend(self):
        self.script_status = ScriptStatus.SUSPENDED
        Trace.log("suspend")

    def resume(self):
        if self.script_status == ScriptStatus.SUSPENDED:
            self.script_status = ScriptStatus.RUNNING
        Trace.log("resume")

    def cancel(self):
        self.script_status = ScriptStatus.FAILED
        self.action_list[self.action_id].cancel()
        self.reset()
        Trace.log("cancel")
        return

    def reset(self):
        self.start_time = time.time()
        # Motor.resetMotor(ConfigParams.fork_motor_name)
        # Navigation.clearGoodsShape()

    def bindContainer(self, container_id: str, goods_name: str, desc: str) -> bool:
        # 1. 绑定容器
        Container.bindContainer(container_id, goods_name, desc)
        # 2. 设置货物形状
        goods_shape = [{"x": 1.2 / 2, "y": 1.0 / 2},
                       {"x": 1.2 / 2, "y": -1.0 / 2},
                       {"x": -1.2 / 2, "y": -1.0 / 2},
                       {"x": -1.2 / 2, "y": 1.0 / 2}]
        if not goods_shape:
            return False
        goods_point2robot = []

        for point in goods_shape:
            point2ap = pos2World([point["x"], point["y"], 0],
                                 [ConfigParams.module_x - 1.2 / 2, 0, 0])
            goods_point2robot.append({"x": point2ap[0], "y": point2ap[1]})
        Navigation.setGoodsPolyShape(goods_point2robot, goods_name)
        return True

    def delete_clear_region(self):
        delete_deduct_area("PalletRobotDeductArea", Coordinate.WORLD)
        delete_deduct_area("noRecDeduct2World", Coordinate.WORLD)
        Navigation.deleteClearRegion(self.back_laser_clear_region_name, Coordinate.ROBOT)
        Navigation.deleteClearRegion(self.name_right, Coordinate.ROBOT)

    def modbus(self):
        # modbus解析器
        # 读取数据
        if NetProtocol.getModbusData("4x", 200, 1):
            modbus_data = NetProtocol.getModbusData("4x", 201, 2)
            data = parseModbus(modbus_data, "float")
            args = {"operation": "forkHeight", "height": data}
            self.event_modbus = False
            return args

    def safe_move_check(self):
        status = SafeMoveStatus.FINISHED
        self.setSafeMoveStatus(status)
        if ConfigParams.scriptDebug:
            Trace.log(f"safe_move_check {Module.getSafeMoveCheck()}")
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False

    def get_station_pos(self, station_type):
        pos = [0, 0, 0, -1]
        tcp_name = ""
        station_id = self.move_task.get(station_type, "")  # int, 可能是 LM，可能是 AP
        Trace.log(f"target id:{station_id}")
        if station_id == "" and station_type == "targetName":
            # task_args 里已经是带前缀的字符串
            target_id_str = self.task_args.get("targetName", "")
            pos = Navigation.getLM(target_id_str, True)
            tcp_name = Navigation.getLmTcpName(target_id_str)
            Trace.log(f"pos:{pos}, tcp name:{tcp_name}")
        elif station_id != "":
            # 尝试 AP 和 LM 两个前缀

            pos = Navigation.getLM(station_id, True)
            tcp_name = Navigation.getLmTcpName(station_id)
            if pos[3] != -1:  # 找到有效结果
                Trace.log(f"id_str:{station_id}, id:{station_id}, pos:{pos} tcp name:{tcp_name}")
                return pos, tcp_name  # 优先返回成功的结果

            # 如果走到这里，说明 AP 和 LM 都失败了
            Trace.log(f"{station_id} not found, return {pos}")
        return pos, tcp_name

    def test(self):
        pass

    # 识别取货和非识别取货
    def load(self):
        if not self.operation_init:
            self.operation_init = True
            r_loc = get_r_loc()
            source_pos = self.get_station_pos("sourceName")[0]
            Trace.log(f"source_pos:{source_pos},recfile:{self.recfile}")
            self.start_loc = r_loc if source_pos[3] == -1 else source_pos
            if (self.recognize and self.check_di) or (not self.recognize and ConfigParams.enableContactDiNoRec):
                ConfigParams.checkGoodsWhileLoad = False
            # 解析识别文件
            if self.recfile:
                # 处理扣除区域
                self.pallet_deduct_infos = get_deduct_area(self.recfile)

                # 处理载具和货物形状
                recognition_pallet_path = f"recognitionObject.pallet"
                self.carrier_width = RobotParam.getConfig("recognition", f"{recognition_pallet_path}.carrierParameter"
                                                                         f".carrierWidth", self.recfile)
                self.carrier_length = RobotParam.getConfig("recognition", f"{recognition_pallet_path}.carrierParameter"
                                                                          f".carrierLength", self.recfile)
                self.carrier_shape = [{"x": self.carrier_length / 2, "y": self.carrier_width / 2},
                                      {"x": self.carrier_length / 2, "y": -self.carrier_width / 2},
                                      {"x": -self.carrier_length / 2, "y": -self.carrier_width / 2},
                                      {"x": -self.carrier_length / 2, "y": self.carrier_width / 2}]
                goods_shape = RobotParam.getConfig("recognition",
                                                   f"{recognition_pallet_path}.goodsParameter.goodsShape",
                                                   self.recfile)
                self.goods_shape = parse_shapes(goods_shape)

                # 处理识别面
                self.rec_info = get_rec_side_info(self.recfile, self.recSide)
                if self.rec_info is None:
                    self.script_status = ScriptStatus.FAILED
                    return

                if any(v is None or v == "none" for v in self.rec_info.values()):
                    Navigation.setTaskError("InvalidRecInfo", f"Invalid side info, found None: {self.rec_info},script failed")
                    self.script_status = ScriptStatus.FAILED

            # 从任务参数 或者从 脚本任务参数里获取到AP点及其坐标
            self.target_pos, tcp_name = self.get_station_pos("targetName")

            # 如果有货,脚本无法取货并报错
            if Navigation.hasGoods() and ConfigParams.loadUnloadCheck:
                Navigation.setTaskError("ForkHasGoods", f"fork has goods, cannot load, script failed")
                self.script_status = ScriptStatus.FAILED
                return

            # 不需要根据识别结果通过盲走插货
            if not self.recognize:
                self.check_di = ConfigParams.enableContactDiNoRec

                if not self.target_pos or self.target_pos[3] == -1:
                    self.action_list = [
                        RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height, ConfigParams.fork_max_speed,
                                           "upFork")
                    ]
                else:
                    self.action_list = [
                        RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height)
                    ]
                    target_pos = self.target_pos
                    if tcp_name:
                        ap_world_pos_tcp = Navigation.calTCPTrans(target_pos[0], target_pos[1], target_pos[2],
                                                                  tcp_name)
                        ap_world_pos_tcp_list = [ap_world_pos_tcp["x"], ap_world_pos_tcp["y"],
                                                 ap_world_pos_tcp["theta"]]
                        target_pos = ap_world_pos_tcp_list
                        Trace.log(f"ap world tcp :{ap_world_pos_tcp_list}")

                        # 根据参数配置是否走贝塞尔曲线、直线选择调整办法
                        args = {
                            "back_dist": 0,
                            "min_ahead_dist": ConfigParams.tail + ConfigParams.module_x,
                            "adjust_dist": ConfigParams.aheadDist,
                        }
                        method = ConfigParams.pathAdjustMode
                        if method == "straightLine":
                            method = "twoStraightLine"
                            args["max_angle"] = ConfigParams.maxAngle
                        elif method == "bezier":
                            args["max_curve"] = ConfigParams.maxCurve
                    else:
                        method = "goPath"
                        args = {}

                    self.action_list.append(
                        GoPathWithContactDi(ConfigParams.contact_ids, target_pos, ConfigParams.loadObsStopDist,
                                            method, args, self.check_di, "load"))
                    self.action_list.append(RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height))

                    if self.leave_loc_height >= 0:
                        args = {
                            'x': self.start_loc[0],
                            'y': self.start_loc[1],
                            'theta': self.start_loc[2],
                            'coordinate': 'world',
                            'backMode': 0,
                            'maxRot': 10,
                            'maxSpeed': 0.2,
                            'useOdo': 0,
                            'reachAngle': math.radians(0.5),
                            'reachDist': 0.005
                        }

                        self.action_list.extend([
                            GoPath(args),
                            RunMotorByPosition(ConfigParams.fork_motor_name, self.leave_loc_height)
                        ])

            # 如果需要识别后再取货
            else:
                # 计算圆心
                if self.target_pos[3] == -1:
                    rec_center2robot = [ConfigParams.recCenterX, ConfigParams.recCenterY]
                else:
                    target2robot = pos2Base(self.target_pos, r_loc)
                    rec_center2robot = pos2World([ConfigParams.module_x, 0, 0], target2robot)
                Trace.log(f"rec center to robot :{rec_center2robot}", True, True)

                # 先看识别文件是否有启用 back_dist，如果启用了，用识别文件的值，没启用的话，用设备模型中的值
                if self.rec_info.get("enableBackDistance", 'off') != 'on':
                    self.back_dist = ConfigParams.module_x
                else:
                    self.back_dist = self.rec_info.get("backDistance")

                self.action_list = [RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height)]

                self.action_list.append(
                    Rec(self.recfile, rec_center2robot[0], rec_center2robot[1], ConfigParams.recRadius))

                if self.rec_height >= 0:
                    self.action_list.append(
                        RunMotorByPosition(ConfigParams.fork_motor_name, self.rec_height)
                    )

            Trace.log(f"task:{self.action_list}", True, True)

        if self.action_id < len(self.action_list):
            # 如果有识别，识别结束后动态加调整的类
            if (isinstance(self.action_list[self.action_id], Rec)
                    and self.action_list[self.action_id].action_name == "RecPallet"
                    and self.action_list[self.action_id].action_status == ActionStatus.FINISHED
                    and self.recognize):
                self.check_di = self.rec_info.get("enableCargoContactDI")

                Trace.log(f"add task list {self.action_list[self.action_id]},id {self.action_id}", True, True)

                results = self.action_list[self.action_id].results_list
                self.pallet_width = results[0]["palletWidth"]
                rec_result_dict = results[0]
                self.obstacle_polygon_by_rec = self.action_list[self.action_id].obstacle_polygon

                Trace.log(f"carrier {self.carrier_shape, self.goods_shape, self.obstacle_polygon_by_rec}", True, True)
                # # 拿到 y 最小的值
                # results_in_r = []
                # if self.rec_info.get("coordinateSystem") == Coordinate.WORLD.value:
                #     Trace.log("rec world")
                #     for result in results:
                #         results_in_r.append(pos2Base([result["x"], result["y"], result["yaw"]],
                #                                      r_loc))
                # else:
                #     for result in results:
                #         results_in_r.append([result["x"], result["y"], result["yaw"]])

                # 相对于机器人取 y 最小的
                # min_y_result = min(results_in_r, key=lambda result_in_r: abs(result_in_r[1]))

                worldResult = rec_result_dict.get(f"worldResult", dict())
                rec_world_pos = [worldResult["x"], worldResult["y"], worldResult["yaw"]]

                robotResult = rec_result_dict.get(f"robotResult", dict())
                rec_robot_pos = [robotResult["x"], robotResult["y"], robotResult["yaw"]]
                Trace.log(f"rec_world_pos: {rec_world_pos},robotResult:{rec_robot_pos}", True, True)

                if ConfigParams.enableTcp:
                    rec_world_pos_tcp = Navigation.calTCPTrans(rec_world_pos[0], rec_world_pos[1], rec_world_pos[2],
                                                               "defaultTCP")
                    rec_world_pos_tcp_list = [rec_world_pos_tcp["x"], rec_world_pos_tcp["y"],
                                              rec_world_pos_tcp["theta"]]
                    Trace.log(f"after tcp:{rec_world_pos_tcp_list}", True, True)
                    rec_world_pos = rec_world_pos_tcp_list

                # 根据AP点，异常识别结果报警，如果 AP 点没有角度怎么办
                if self.target_pos and self.target_pos[3] != -1:
                    rec2ap_pos = pos2Base(rec_world_pos, self.target_pos)
                    angle = math.degrees(rec2ap_pos[2])
                    Trace.log(
                        f"rec2ap_pos: {rec2ap_pos},rec_world_pos: {rec_world_pos},target_pos:{self.target_pos},angle2ap:{angle}",
                        True, True)
                    y = rec2ap_pos[1]
                    if abs(angle) > ConfigParams.errorRecAngle != -1:
                        Navigation.setTaskError("RecYError", f"rec result yaw angle too large:{angle}° from action point")
                        self.script_status = ScriptStatus.FAILED
                        return
                    if abs(y) > ConfigParams.errorRecY != -1:
                        Navigation.setTaskError("RecYError", f"rec result y too large :{y}m from action point")
                        self.script_status = ScriptStatus.FAILED
                        return

                # 根据参数配置是否走贝塞尔曲线、直线选择调整办法
                args = {
                    "back_dist": self.back_dist,
                    "min_ahead_dist": ConfigParams.minAheadDist,
                    "adjust_dist": ConfigParams.aheadDist,
                }
                method = ConfigParams.pathAdjustMode
                Trace.log(f"method:{method}")
                if method == "straightLine":
                    args["max_angle"] = ConfigParams.maxAngle
                elif method == "bezier":
                    args["max_curve"] = ConfigParams.maxCurve
                self.action_list.extend([
                    GoPathWithContactDi(ConfigParams.contact_ids, rec_world_pos, ConfigParams.loadObsStopDist, method,
                                        args,
                                        self.check_di, "load"),
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height, ConfigParams.fork_max_speed,
                                       "upFork")
                ])
                Trace.log(f"task after rec:{self.action_list}", True, True)

                if self.leave_loc_height >= 0:
                    args = {
                        'x': self.start_loc[0],
                        'y': self.start_loc[1],
                        'theta': self.start_loc[2],
                        'coordinate': 'world',
                        'backMode': 0,
                        'maxRot': 10,
                        'maxSpeed': 0.2,
                        'useOdo': 0
                    }
                    if ConfigParams.pathAdjustMode == "bezier" and ConfigParams.returnOnSamePath:
                        self.action_list.append(
                            GoBezier.GoBezierWorldReturn(False)
                        )
                    elif ConfigParams.pathAdjustMode == "straightLine" and ConfigParams.returnOnSamePath:
                        self.action_list.append(
                            GoTwoStraightLine(0, 0, 0, 0, 0, 0, 0, True)
                        )
                    else:
                        self.action_list.append(
                            GoPath(args)
                        )

                    self.action_list.append(
                        RunMotorByPosition(ConfigParams.fork_motor_name, self.leave_loc_height)
                    )

                    Trace.log(f"task after leave loc:{self.action_list}", True, True)

            # 取完货后离库位前，抬升货叉就加载货物模型
            if (isinstance(self.action_list[self.action_id], RunMotorByPosition)
                    and self.action_list[self.action_id].action_name == "upFork"
                    and self.action_list[self.action_id].action_status == ActionStatus.FINISHED):
                goods_point2robot = []

                # 取最外面的包络，货物模型、栈板模型、识别出来的外部包络
                # outer_points = convex_hull(self.carrier_shape, self.goods_shape, self.obstacle_polygon_by_rec)
                for point in self.carrier_shape:
                    point2ap = pos2World([point["x"], point["y"], 0],
                                         [ConfigParams.module_x - self.carrier_length / 2, 0, 0])
                    goods_point2robot.append({"x": point2ap[0], "y": point2ap[1]})
                # 设置货物形状
                goods_name = self.recfile
                # 设置扣除区域
                if self.pallet_deduct_infos:
                    set_deduct_area(self.pallet_deduct_infos,
                                    [ConfigParams.module_x - self.carrier_length / 2, 0, 0],
                                    "PalletRobotDeductArea",
                                    Coordinate.ROBOT)

                Navigation.setGoodsPolyShape(goods_point2robot, goods_name)

        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED

    def leave_loc(self):
        if not self.operation_init:
            self.operation_init = True

            target_pos = self.get_station_pos("targetName")[0]
            if target_pos[3] == -1:
                Navigation.setTaskError("NoTargetId", f"cannot find point, script failed")
                self.script_status = ScriptStatus.FAILED
                return
            args = {
                'x': target_pos[0],
                'y': target_pos[1],
                'theta': target_pos[2],
                'coordinate': 'world',
                'backMode': 0,
                'maxRot': 10,
                'maxSpeed': 0.2,
                'useOdo': 0
            }
            if ConfigParams.returnOnSamePath and ConfigParams.pathAdjustMode == "bezier":
                self.action_list = [
                    GoBezier.GoBezierWorldReturn(False)
                ]
            elif ConfigParams.returnOnSamePath and ConfigParams.pathAdjustMode == "straightLine":
                self.action_list = [
                    GoTwoStraightLine(0, 0, 0, 0, 0, 0, 0, True)
                ]
            else:
                self.action_list = [
                    GoPath(args)
                ]

            self.action_list.append(RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height))
            Trace.log(f"task:{self.action_list}")

        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED

    def unload(self):
        if not self.operation_init:
            self.operation_init = True
            r_loc = get_r_loc()
            source_pos = self.get_station_pos("sourceName")[0]
            self.start_loc = r_loc if source_pos[3] == -1 else source_pos

            if not Navigation.hasGoods() and ConfigParams.loadUnloadCheck:
                Navigation.setTaskError("ForkNoGoods", f"fork has no goods, cannot unload, script failed")
                self.script_status = ScriptStatus.FAILED
                return
            target_pos, tcp_name = self.get_station_pos("targetName")
            Trace.log(f"target_pos: {target_pos}")
            if not target_pos or target_pos[3] == -1:
                self.action_list = [
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height,
                                       ConfigParams.downMaxSpeedWithGoods, "downFork")
                ]
            else:

                # AP 点是否绑定了 tcp
                if tcp_name:

                    ap_world_pos_tcp = Navigation.calTCPTrans(target_pos[0], target_pos[1], target_pos[2],
                                                              tcp_name)
                    ap_world_pos_tcp_list = [ap_world_pos_tcp["x"], ap_world_pos_tcp["y"], ap_world_pos_tcp["theta"]]
                    target_pos = ap_world_pos_tcp_list
                    Trace.log(f"ap world tcp :{ap_world_pos_tcp_list}")

                    # 根据参数配置是否走贝塞尔曲线、直线选择调整办法
                    args = {
                        "back_dist": 0,
                        "min_ahead_dist": ConfigParams.tail + ConfigParams.module_x - ConfigParams.base_shift_length,
                        "adjust_dist": ConfigParams.aheadDist,
                    }
                    method = ConfigParams.pathAdjustMode
                    if method == "straightLine":
                        args["max_angle"] = ConfigParams.maxAngle
                    elif method == "bezier":
                        args["max_curve"] = ConfigParams.maxCurve
                else:
                    method = "goPath"
                    args = {}
                if ConfigParams.base_shift:
                    target_pos = pos2World([-ConfigParams.base_shift_length, 0, 0], target_pos)
                self.action_list = [
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height),
                    GoPathWithContactDi(ConfigParams.contact_ids, target_pos, None, method, args,
                                        False, "unload"),
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height,
                                       ConfigParams.downMaxSpeedWithGoods, "downFork")
                ]

                if self.leave_loc_height >= 0:

                    args = {
                        'x': self.start_loc[0],
                        'y': self.start_loc[1],
                        'theta': self.start_loc[2],
                        'coordinate': 'world',
                        'backMode': 0,
                        'maxRot': 10,
                        'maxSpeed': 0.2,
                        'useOdo': 0,
                        "reachAngle": math.radians(0.5),
                        "reachDist": 0.005
                    }
                    if ConfigParams.pathAdjustMode == "bezier" and ConfigParams.returnOnSamePath:
                        self.action_list.extend([
                            GoBezier.GoBezierWorldReturn(False)
                        ])
                    elif ConfigParams.pathAdjustMode == "straightLine" and ConfigParams.returnOnSamePath:
                        self.action_list.extend([
                            GoTwoStraightLine(0, 0, 0, 0, 0, 0, 0, True)
                        ])
                    else:
                        self.action_list.extend([
                            GoPath(args)
                        ])

                    self.action_list.append(
                        RunMotorByPosition(ConfigParams.fork_motor_name, self.leave_loc_height)
                    )

            Trace.log(f"task list: {self.action_list}")

        if self.action_id < len(self.action_list):
            # 放完货就取消货物模型
            if (isinstance(self.action_list[self.action_id], RunMotorByPosition)
                    and self.action_list[self.action_id].action_name == "downFork"
                    and self.action_list[self.action_id].action_status == ActionStatus.FINISHED):
                Navigation.clearGoodsShape()

        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            delete_deduct_area(["no_rec_deduct_pallet_area", "PalletRobotRegionByHeight"], Coordinate.ROBOT)

            self.script_status = ScriptStatus.FINISHED

    def _execute_actions(self):
        if self.action_id < len(self.action_list):
            self.current_action = self.action_list[self.action_id]

            if self.current_action.action_status == ActionStatus.FINISHED:
                Trace.log(f"execute {self.current_action.action_name} finished", True, True)
                self.action_id += 1

            elif self.current_action.action_status == ActionStatus.FAILED:
                Navigation.setTaskError("ExecuteActionError", f"execute action {self.current_action} failed!")
                self.action_status = ActionStatus.FAILED
                return
            elif self.current_action.action_status == ActionStatus.INIT:
                self.current_action.reset()
            else:
                self.current_action.run()
            self.trace_chart.update(
                _flat_attrs(self.current_action, idx1=self.action_id)
            )
        else:
            self.action_status = ActionStatus.FINISHED
        self.trace_chart.update({
            "script.task_len": len(self.action_list),
            "script.action_id": self.action_id,
            "script.all_action_status": self.action_status,
            "script.cur_action": self.current_action.action_name,
            "script.cur_action_status": self.current_action.action_status,
            "script.script_status": self.script_status
        })

    def fork_move(self):
        if not self.operation_init:
            self.fork_height_in_place = False
            self.operation_init = True
            # forkHeight 和 forkSpeed 为任务输入参数
            # if ConfigParams.fork_motor_name:
            self.action_list = [RunMotorByPosition(ConfigParams.fork_motor_name, self.forkHeight, self.forkSpeed)]
        if self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED
            self.fork_height_in_place = True
        # print("action_status:" + json.dumps(cur_status))

    def _init_args(self):

        # 解析任务参数，script_args 里的参数
        self.recfile = self.task_args.get("recfile", "")
        self.opt = self.task_args.get("operation", "")
        self.start_height = self.task_args.get("startHeight", 0.09)
        self.rec_height = self.task_args.get("recHeight", -1)
        self.end_height = self.task_args.get("endHeight", 0.2)
        self.leave_loc_height = self.task_args.get("leaveLocHeight", -1)
        self.forkHeight = self.task_args.get("height")
        self.forkSpeed = self.task_args.get("forkSpeed", ConfigParams.fork_max_speed)
        self.recSide = self.task_args.get("recSide")
        input_recognize = self.task_args.get("recognize", False)

        # 解析任务下发的参数，不含在 script_args 里的参数
        self.move_task = Navigation.moveTask()

        movetask_recognize = next(
            (p.get('boolValue') for p in self.move_task.get('params', [])
             if p.get('key') == 'recognize'),
            False
        )
        self.min_safe_height = next(
            (float(p.get('floatValue', p.get('value', 0.0))) for p in self.move_task.get('params', [])
             if p.get('key') == 'minSafeHeight'),
            0.0
        )
        Trace.log(f"min_safe_height:{self.min_safe_height}")
        Trace.log(f"move task:{self.move_task}")

        self.recognize = any([input_recognize, movetask_recognize])

        self.start_time = time.time()

        self.clear_fork_region_by_height = False
        self.name_left = "back_laser_clear_left"
        self.name_right = "back_laser_clear_right"
        self.back_laser_clear_region_name = "back_laser_clear_region"
        self.outer = (ConfigParams.center_distance_between_forks + ConfigParams.fork_tip_width) / 2
        self.inner = (ConfigParams.center_distance_between_forks - ConfigParams.fork_tip_width) / 2
        self.points_left = [{"x": ConfigParams.module_x, "y": -self.outer},
                            {"x": -ConfigParams.tail, "y": -self.outer},
                            {"x": -ConfigParams.tail, "y": -self.inner},
                            {"x": ConfigParams.module_x, "y": -self.inner}]
        self.points_right = [{"x": ConfigParams.module_x, "y": self.outer},
                             {"x": -ConfigParams.tail, "y": self.outer},
                             {"x": -ConfigParams.tail, "y": self.inner},
                             {"x": ConfigParams.module_x, "y": self.inner}]
        Trace.log(f"init args")
        # self.opt = "rec"
        # Abnormal.setTask(53000, "test", "", "", "")

    def _check_timeout(self):
        self.script_runtime = time.time() - self.start_time
        if self.script_runtime > ConfigParams.timeout:
            Trace.log(f"script timeout:{ConfigParams.timeout}")
            Navigation.setTaskError("ScriptTimeout", f"script timeout:{ConfigParams.timeout}, script failed")
            self.script_status = ScriptStatus.FAILED
            self.action_list[self.action_id].cancel()

    # def _report(self):
    #     cur_status = dict()
    #     if self.action_id < len(self.action_list):
    #         cur_status['action_id'] = self.action_id
    #         cur_status['action_num'] = len(self.action_list)
    #         cur_status['action_list'] = [str(action) for action in self.action_list]
    #         cur_status['action_status'] = self.action_list[self.action_id].action_status
    #         cur_status['script_status'] = self.script_status

    def rec(self):
        if not self.operation_init:
            self.operation_init = True
            self.action_list = [Rec(self.recfile, rec_center_x=ConfigParams.recCenterX,
                                    rec_center_y=ConfigParams.recCenterY, rec_radius=ConfigParams.recRadius)]
        if self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED

    def save_mileage(self):
        db_total = db.get(self.mileage_total_key, "float")
        if db_total == 0:
            self.total_dist = 0.0
            self.up_dist = 0.0
            self.down_dist = 0.0
        if self.total_dist != self.last_saved_total:
            db.put(self.mileage_total_key, self.total_dist)
            self.last_saved_total = self.total_dist

    def period_run(self):
        fork_height = Motor.getMotorPos(ConfigParams.fork_motor_name)
        self.fork_height = fork_height

        self.trace_chart.update({
            "forkHeight": fork_height,  # 货叉高度, 单位 m
            "forkHeightInPlace": self.fork_height_in_place,  # 货叉高度是否到位, true = 到位, false = 未到位
            "forkAutoFlag": not Controller.getIsExternalControl(),
            "forkMileage": self.total_dist,
            "containers": Container.getContainers()
            # 叉车的控制模式(通过叉车上的物理按钮切换), ture = 自动控制(控制器控制), false = 手动控制(方向盘驾驶)
        })
        Module.reportInfo(self.trace_chart)
        Trace.chart(self.trace_chart, False)

        # 根据变动量记录货叉的里程数据
        if self.last_pos is not None:
            delta = fork_height - self.last_pos
            if delta > ConfigParams.reach_up_dist:
                self.up_dist += delta
                self.total_dist += delta
            elif delta < -ConfigParams.reach_down_dist:
                d = -delta
                self.down_dist += d
                self.total_dist += d

        self.last_pos = fork_height

        if time.time() - self.last_save_ts > self.save_interval:
            self.save_mileage()
            self.last_save_ts = time.time()

        # 写modbus寄存器
        modbus_list_fork_height = float_to_modbus_poll_regs(fork_height)
        NetProtocol.setModbusData("3x", 57, modbus_list_fork_height)

        # 如果在低位且是载货状态，需要做卸货处理
        if ConfigParams.module_type == "liftFork" and (
                self.fork_height - ConfigParams.min_height) <= EPS and Navigation.hasGoods():
            Navigation.clearGoodsShape()

        if ConfigParams.module_type in ["straddleLiftFork", "counterBalanceFork"]:
            task_status = NavStatus.getTaskStatus()
            # 有任务时用后激光做碰撞检测，有障碍物时不动。
            # 当 minSafeHeight > 0 且货叉正在升降且高度超过最小安全高度时，跳过后激光碰撞检测，防货叉遮挡误报
            if task_status == 2:
                x_list = [p["x"] for p in self.fork_points]
                y_list = [p["y"] for p in self.fork_points]
                if ConfigParams.fork_root_2D_lasers:
                    collision_device = [ConfigParams.fork_root_2D_lasers]
                    fork_is_moving = (
                            isinstance(self.current_action, RunMotorByPosition)
                            and self.current_action.motor_name == ConfigParams.fork_motor_name
                            and self.current_action.action_status == ActionStatus.RUNNING
                    )
                    if 0 < self.min_safe_height <= fork_height and fork_is_moving:
                        Trace.log(
                            f"fork moving, height:{fork_height} >= min_safe_height:{self.min_safe_height}, skip back laser collision detection")
                    else:
                        Navigation.collisionDetection(collision_device, x_list, y_list)

            # 堆高车处理后激光的屏蔽
            if Loc.getLocState() == 1:
                # if ConfigParams.scriptDebug:
                #     Trace.log(
                #         f"set_fork_region_by_height:{self.set_fork_region_by_height},clear_fork_region_by_height:{self.clear_fork_region_by_height}")
                if fork_height <= ConfigParams.backLaserEnableHeight and not self.set_fork_region_by_height:
                    self.set_fork_region_by_height = True
                    self.clear_fork_region_by_height = False
                    # Navigation.setClearRegion(self.name_left, [p["x"] for p in self.points_left],
                    #                           [p["y"] for p in self.points_left],
                    #                           [ConfigParams.fork_root_2D_lasers], Coordinate.ROBOT)
                    Navigation.setClearRegion(self.back_laser_clear_region_name, [p["x"] for p in self.fork_points],
                                              [p["y"] for p in self.fork_points],
                                              [ConfigParams.fork_root_2D_lasers], Coordinate.ROBOT)
                    Trace.log(f"set clear region:{self.back_laser_clear_region_name},{self.fork_points}")

                elif fork_height > ConfigParams.backLaserEnableHeight and not self.clear_fork_region_by_height:
                    self.clear_fork_region_by_height = True
                    self.set_fork_region_by_height = False
                    Navigation.deleteClearRegion(self.back_laser_clear_region_name, Coordinate.ROBOT)

                    Trace.log(f"delete clear region:{self.back_laser_clear_region_name},{self.fork_points}")

                    # Navigation.deleteClearRegion(self.name_right, Coordinate.ROBOT)

        # 处理载货时di状态监控
        if ConfigParams.checkGoodsWhileLoad:
            # print(f"checkGoodsWhileLoad:{ConfigParams.checkGoodsWhileLoad}")

            # 获取到位 di 的状态
            di_status = []
            contact_ids = ConfigParams.contact_ids
            for di in contact_ids:
                di_status.append(Di.getDi(di))

            # 根据是否检测所有到位di 决定错误状态
            if Navigation.hasGoods():
                if ConfigParams.checkAllContactDis:
                    missing_goods = not all(di_status)
                else:
                    missing_goods = not any(di_status)

                # 做 0.3s 的延时处理
                if missing_goods and Timer.delay(0.3):
                    Navigation.setTaskError("forkMissingGood", "fork missing goods,No Contact Di Trigger")
                else:
                    if Timer.delay(0.3):
                        if Navigation.errorExists("forkMissingGood"):
                            Navigation.clearTaskError("forkMissingGood")

    def cage_stack(self):
        if not self.operation_init:
            self.operation_init = True
            self.cage_count = 0
            self.start_loc = get_r_loc()

            # # 料笼堆叠功能需要底盘是全向车或者平衡重有横移机构，否则报错，结束任务不支持
            # if ConfigParams.chassis_type == "":
            #     Abnormal.setTask(53330,
            #                      f"cage function only support in chassisType.multipleDifferentialSteers or shiftMotor"
            #                      f"", f"check the fork type", f"change the robot", f"{self.opt}")
            #     self.script_status = ScriptStatus.FAILED
            #     return
            #
            # if not Navigation.hasGoods() and ConfigParams.loadUnloadCheck:
            #     Abnormal.setTask(53903, f"fork has no goods, cannot unload, script failed", "", "", "unload")
            #     self.script_status = ScriptStatus.FAILED
            #     return
            self.target_pos, tcp_name = self.get_station_pos("targetName")
            Trace.log(f"target_pos: {self.target_pos}", True, True)
            #
            # self.action_list = [
            #     RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height)
            # ]

            # 如果没指定目标站点，那么没有导航的动作，就直接识别并二次调整
            if not self.target_pos or self.target_pos[3] == -1:
                pass
            else:
                if tcp_name:
                    ap_world_pos_tcp = Navigation.calTCPTrans(self.target_pos[0], self.target_pos[1],
                                                              self.target_pos[2],
                                                              tcp_name)
                    ap_world_pos_tcp_list = [ap_world_pos_tcp["x"], ap_world_pos_tcp["y"], ap_world_pos_tcp["theta"]]
                    self.target_pos = ap_world_pos_tcp_list
                    Trace.log(f"ap world tcp :{ap_world_pos_tcp_list}", True, True)

                    # 根据参数配置是否走贝塞尔曲线、直线选择调整办法
                    args = {
                        "back_dist": 0,
                        "min_ahead_dist": ConfigParams.tail + ConfigParams.module_x - ConfigParams.base_shift_length,
                        "adjust_dist": ConfigParams.aheadDist,
                    }
                    if ConfigParams.pathAdjustMode == "straightLine":
                        method = "twoStraightLine"
                        args["max_angle"] = 10
                    else:
                        method = "goBezier"
                        args["max_curve"] = 3
                else:
                    method = "goPath"
                    args = {}

                self.action_list.append(
                    GoPathWithContactDi(ConfigParams.contact_ids, self.target_pos, None, method, args,
                                        False))
            Trace.log(f"task list: {self.action_list}", True, True)
            self.action_list.append(Rec(self.recfile, -ConfigParams.tail, 0, ConfigParams.recRadius))

        # 识别结束后动态加调整的类
        if (self.action_id < len(self.action_list)
                and isinstance(self.current_action, Rec)
                and self.current_action.action_name == "RecCage"
                and self.current_action.action_status == ActionStatus.FINISHED):
            # 计算出上料笼腿相对于下料笼顶的位置
            robot2pos = self.get_robot2target_pos(self.current_action.results_list)
            Trace.log(f"robot2pos: {robot2pos},yaw: {math.degrees(robot2pos[2])}", True, True)

            if abs(math.degrees(robot2pos[2])) > 8 or abs(robot2pos[0]) > 0.2:
                Navigation.setTaskError("CageTooFar", "cage too far from")
                self.script_status = ScriptStatus.FAILED
                return
            Trace.log(f"cage_count:{self.cage_count}", True, True)

            if (abs(math.degrees(robot2pos[2])) <= 0.5 and abs(robot2pos[0]) <= 0.01 and abs(
                    robot2pos[1]) <= 0.01) or self.cage_count >= 2:
                self.action_list.append(RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height))
            else:

                self.action_list.extend([MoveChassisByY(robot2pos),
                                         Rec(self.recfile, -ConfigParams.tail, 0, ConfigParams.recRadius)])

                self.cage_count += 1
            Trace.log(f"task list: {self.action_list},cage_count:{self.cage_count}", True, True)

        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            delete_deduct_area(["no_rec_deduct_pallet_area", "PalletRobotRegionByHeight"], Coordinate.ROBOT)

            self.script_status = ScriptStatus.FINISHED

    def get_robot2target_pos(self, results_list):
        """
        1. 找到正确的腿和顶，因为后面的料笼可能也会有看到。（过滤条件）
        2. 腿或者顶小于2，需要报错
        3. 计算腿和顶的中心
        4. 把上料笼的坐标转换到下料笼下
        """

        # 筛选 top 和 bottom
        bottom_cages = [obj for obj in results_list if obj.get("class") == "Head"]  # 下面的料笼
        top_cages = [obj for obj in results_list if obj.get("class") == "Bottom"]  # 上面的料笼

        # 数量检查
        if len(bottom_cages) < 2:
            Navigation.setTaskError("UnknownError", "")
            return [999, 999, 999]
        if len(top_cages) < 2:
            Navigation.setTaskError("UnknownError", "")
            return [999, 999, 999]

        # 如果识别结果在世界坐标系，需要改到机器人坐标系后做处理
        recognitionSide_key = "recognitionObject.CageHeadBottom.coordinateSystem"
        coordinate_system = RobotParam.getConfigCloneSize("recognition", recognitionSide_key, "cage.srec")
        if coordinate_system == Coordinate.WORLD.value:
            r_loc = get_r_loc()

            def _to_robot(o):
                rx, ry, ryaw = pos2Base([o["x"], o["y"], o.get("yaw", 0)], r_loc)
                return dict(o, x=rx, y=ry, yaw=ryaw)

            top_cages = [_to_robot(o) for o in top_cages]
            bottom_cages = [_to_robot(o) for o in bottom_cages]

        # 按 x 从大到小排序，取离车体最近的两个值
        tops_sorted = sorted(top_cages, key=lambda o: o["x"], reverse=True)
        bottoms_sorted = sorted(bottom_cages, key=lambda o: o["x"], reverse=True)

        # 取 x 从大到小排序，即取离车体最近的两个值
        top_two = tops_sorted[:2]
        bottom_two = bottoms_sorted[:2]

        # # 计算 x 间距
        # top_x_diff = abs(tops_sorted[0]["x"] - tops_sorted[1]["x"])
        # bottom_x_diff = abs(bottoms_sorted[0]["x"] - bottoms_sorted[1]["x"])

        def normalize_angle_rad(a: float) -> float:
            # 归一化到 [-pi, pi]
            a = (a + math.pi) % (2 * math.pi) - math.pi
            return a

        def calc_yaw_from_two_points(p0: dict, p1: dict) -> float:
            p0, p1 = sorted([p0, p1], key=lambda p: p["y"])
            dx = p1["x"] - p0["x"]
            dy = p1["y"] - p0["y"]

            # 你定义：x 相同 yaw=0
            if abs(dx) < EPS:
                return 0.0

            yaw = math.atan2(-dx, dy)  # x轴为0°，逆时针为正，顺时针为负
            return normalize_angle_rad(yaw)  # [-pi, pi]

        # 计算 top 中点
        top_mid = {
            "x": (top_two[0]["x"] + top_two[1]["x"]) / 2,
            "y": (top_two[0]["y"] + top_two[1]["y"]) / 2,
            "z": (top_two[0]["z"] + top_two[1]["z"]) / 2,
            "yaw": calc_yaw_from_two_points(top_two[0], top_two[1])
        }

        # 计算 bottom 中点
        bottom_mid = {
            "x": (bottom_two[0]["x"] + bottom_two[1]["x"]) / 2,
            "y": (bottom_two[0]["y"] + bottom_two[1]["y"]) / 2,
            "z": (bottom_two[0]["z"] + bottom_two[1]["z"]) / 2,
            "yaw": calc_yaw_from_two_points(bottom_two[0], bottom_two[1])

        }

        # 上料笼比下料笼要宽一些，需要做一下offset的转换，把上料笼中心位置和下料笼对齐
        top_mid_offset = pos2World([-0.08 / 2, 0, 0], [top_mid['x'], top_mid['y'], top_mid['yaw']])
        bottom_mid_offset = pos2World([-0.04 / 2, 0, 0], [bottom_mid['x'], bottom_mid['y'], bottom_mid['yaw']])

        robot2target_pos = pos2Base(top_mid_offset, bottom_mid_offset)
        # bottom2top_pos = pos2Base([top_mid['x'], top_mid['y'], top_mid['yaw']], bottom_mid_offset)

        Trace.log(
            f"top_mid:{top_mid},bottom_mid:{bottom_mid}, bottom_mid_offset:{bottom_mid_offset},bottom2top_pos: {robot2target_pos}")
        return robot2target_pos


class BaseAction:
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        self.action_name = action_name or self.__class__.__name__

        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.action_state = {}
        self.init = False

    def run(self):
        self.action_state["action_runtime"] = time.time() - self.start_time
        self.action_state['action_name'] = self.action_name
        pass

    def reset(self):
        pass

    def __str__(self):
        return json.dumps({
            "class_name": self.action_name
        })

    def cancel(self):
        self.action_status = ActionStatus.FAILED


# class GoBezier(BaseAction):
#     def __init__(self, goal, back_dist, ahead_dist, min_ahead_dist):
#         super().__init__()
#         self.action_status = ActionStatus.INIT
#         self.goal = goal
#         self.init = False
#         self.back_dist = back_dist
#         self.ahead_dist = ahead_dist
#         self.min_ahead_dist = min_ahead_dist
#         self.start_time = 0.0
#
#     def run(self):
#         if not self.init:
#             self.init = True
#             self.action_status = ActionStatus.RUNNING
#             Navigation.resetGoForkPath(self.goal[0], self.goal[1], self.goal[2], self.back_dist,
#                                        self.min_ahead_dist, self.ahead_dist)
#             if ConfigParams.pathAdjustMode == "straightLine":
#                 Navigation.goForkUseStraightLine()  # 走折线
#         self.action_status = Navigation.goForkPath()
#
#     def reset(self):
#         self.action_status = ActionStatus.RUNNING
#         self.init = False


# 用于识别栈板并获取识别的栈板坐标
class Rec(BaseAction):
    def __init__(self, pallet_file, rec_center_x=-1.0, rec_center_y=0.0, rec_radius=0.7, action_name="RecPallet"):
        super().__init__(action_name)
        self.rec_status = None
        self.result = dict()
        self.action_status = ActionStatus.INIT
        self.recfile = pallet_file
        self.attempts = 0
        self.max_attempts = 20
        self.success = False
        self.results_dict = {}
        self.results_list = []
        self.obstacle_polygon = []
        # 识别区域参数
        self.rec_center_x = rec_center_x
        self.rec_center_y = rec_center_y
        self.rec_radius = rec_radius
        self.region = {
            "point": {"x": self.rec_center_x, "y": self.rec_center_y},
            "radius": self.rec_radius,
            "shape": "circle"
        }
        Trace.log(f"region: {self.region}")

    def run(self):
        if not self.init:
            self.init = True
            self.success = False
            time.sleep(1)

        self.action_status = ActionStatus.RUNNING
        if not self.success:
            self.success, self.rec_status, self.results_dict = self.rec(self.recfile)
        else:
            results_list = self.results_dict.get("recoList", [])
            self.obstacle_polygon = self.results_dict.get("obstaclePolygon", [])
            # 处理识别结果，并按降序排序，z值最大的结果在前
            if ConfigParams.zMax:

                results_list.sort(key=lambda x: x["robotResult"]["z"],reverse=True)
                results_list.sort(key=lambda x: x["worldResult"]["z"],reverse=True)
            # z值最小的结果在前
            else:
                results_list.sort(key=lambda x: x["robotResult"]["z"])
                results_list.sort(key=lambda x: x["worldResult"]["z"])

            self.results_list = results_list
            self.result = self.results_list[0]

            Trace.log(f"rec_result_list: {self.results_list}")

            self.action_status = ActionStatus.FINISHED

    def reset(self):
        Recognize.resetRec()
        self.action_status = ActionStatus.RUNNING

    def rec(self, recfile):
        rec_status = Recognize.getRecStatus()
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            Trace.log(f"raw results:{rec_result}")
            return True, rec_status, rec_result
        elif rec_status in (-1, 3):
            if Timer.delay(0.05):
                self.attempts += 1
                if self.attempts > self.max_attempts:
                    results = Recognize.getRecResults()
                    # Trace.log(f"raw results:{results}")
                    error_type = results["error"]
                    error_msg = results["logMsg"]
                    Trace.log(f"error_type: {error_type}")
                    self.action_status = ActionStatus.FAILED
                    Navigation.setTaskError("RecFailed", f"Recognition failed, the maximum number of retries exceeded")
                else:
                    Recognize.resetRec()
        else:
            Trace.log(f"recfile:{recfile}")
            Recognize.doRec(recfile, json.dumps(self.region))

            Timer.delay(0.05)
        return False, rec_status, list


class GoPathWithContactDi(BaseAction):
    def __init__(self, contact_dis, world_pos, obs_dist, method, args, check_di=True, operation_type=""):
        super().__init__()
        if args is None:
            args = {}
        self.di_filter_time = 1
        self.check_di = check_di
        self.check_all_contact_di = ConfigParams.checkAllContactDis
        self.operation_type = operation_type  # "load" or "unload"
        self.laser_id = []
        self.laser_width = None
        self.walk_dist = None
        self.action_status = ActionStatus.INIT
        self.di_status = []
        self.contact_di = contact_dis
        self.contact_di = [d for d in contact_dis if d]

        # 获取叉尖 di sensor 绑定的实际 DI 通道 id
        self.fork_tip_di_ids = []
        if ConfigParams.fork_tip_di_sensors:
            for sensor_name in ConfigParams.fork_tip_di_sensors:
                di_id = RobotParam.getDevice(sensor_name, "basic.id")
                if di_id:
                    self.fork_tip_di_ids.append(di_id)
        self.di_triggered_stopped = False  # unload autoClearError 模式：是否因 di 触发而停止等待中
        self.di_trigger_start_time = None  # di 触发开始时间（防抖）
        self.di_clear_start_time = None  # di 清除开始时间（防抖）

        self.target_pos = world_pos
        if self.check_di and not self.contact_di:
            Navigation.setTaskError("ContactDiNone", f"check di is True in recfile, but contact di is none")
            self.action_status = ActionStatus.FAILED
        self.goal = [0, 0, 0]
        self.init = False
        self.obs_dist = obs_dist
        self.start_loc = None
        self.method = method
        self.di_trigger_time = 1
        self.set_policy = False
        self.clear_policy = False
        self.policy = {}
        target2robot = pos2Base(world_pos, get_r_loc())
        Trace.log(f"go path with di target pos:{world_pos},args:{args}")

        if self.check_di:
            back_dist = args.get("back_dist", 0.0) + ConfigParams.forkDiDist
        else:
            back_dist = args.get("back_dist", 0.0)

        if method == "goPath":
            # 如果要触发到位di，那就再往后一个 fork di dist 的距离
            if self.check_di:
                target_pos = pos2World([-ConfigParams.forkDiDist, 0, 0], world_pos)
            else:
                target_pos = world_pos
            self.final_target = target_pos

            Trace.log(f"go path with di target pos:{target_pos}")
            self.back_args = {
                'x': target_pos[0],
                'y': target_pos[1],
                'theta': target_pos[2],
                'coordinate': 'world',
                'backMode': 1,
                'maxRot': 10,
                'maxSpeed': 0.15,
                'useOdo': 0,
                'reachAngle': math.radians(0.5),
                'reachDist': 0.005
            }
            if target2robot[0] > 0:
                self.back_args["backMode"] = 0
            self.back_action = GoPath(self.back_args)
        elif method == "bezier":
            self.back_action = GoBezier.GoBezierWorld(world_pos, back_dist, args["adjust_dist"],
                                                      args["min_ahead_dist"], True,
                                                      None, 0.1, 0.3, 0.2, 0.5, args["max_curve"])
            self.final_target = pos2World([-args["back_dist"], 0, 0], world_pos)
            Trace.log(f"goBezier target pos:{self.final_target}")

        elif method == "straightLine":
            self.back_action = GoTwoStraightLine(world_pos, args["min_ahead_dist"], args["adjust_dist"],
                                                 back_dist, 0.2, args['max_angle'], 1)
            self.final_target = pos2World([-args["back_dist"], 0, 0], world_pos)
            Trace.log(f"twoStraightLine target pos:{self.final_target}")
        else:
            Navigation.setTaskError("WrongGoPathMethod", f"wrong gopath method :{method}, script failed")
            self.action_status = ActionStatus.FAILED
        # self.back_status = self.back_action.action_status

    def run(self):
        if self.action_status in [ActionStatus.FAILED, ActionStatus.FINISHED]:
            return

        self.action_status = ActionStatus.RUNNING
        try:
            if not self.init:
                self.init = True
                self.start_loc = get_r_loc()
                Trace.log(f"fork tip 2d laser:{ConfigParams.fork_tip_2D_lasers}")
                # if cal_dist(self.target_pos, self.start_loc) < 0.05:
                #     self.action_status = ActionStatus.FINISHED
                #     return
                if self.obs_dist is not None and ConfigParams.fork_tip_2D_lasers:
                    for laser in ConfigParams.fork_tip_2D_lasers:
                        Trace.log(f"set2DLaserWidth:{laser}")
                        Laser.set2DLaserWidth(laser, 0.05)

                # 根据操作类型决定是否屏蔽叉尖 di sensor（从碰撞检测设备列表中移除）
                Trace.log(
                    f"fork tip di sensors:{ConfigParams.fork_tip_di_sensors}, fork_tip_di_ids:{self.fork_tip_di_ids}, operation_type:{self.operation_type}")
                should_shield_di = False
                if ConfigParams.fork_tip_di_sensors:
                    if self.operation_type == "load":
                        should_shield_di = not ConfigParams.forkDiEnableAtLoad
                    elif self.operation_type == "unload":
                        should_shield_di = not ConfigParams.forkDiEnableAtUnload
                    else:
                        should_shield_di = True

                if should_shield_di:
                    current_collision_device_str = (RobotParam.getConfig("navigation",
                                                                         "collisionDetection.detectionDevice"))
                    current_collision_device = current_collision_device_str.split(",")
                    Trace.log(f"current_collision_device:{current_collision_device}")
                    for di_sensor in ConfigParams.fork_tip_di_sensors:
                        if di_sensor in current_collision_device:
                            current_collision_device.remove(di_sensor)
                    current_collision_device_str = ",".join(current_collision_device)
                    self.policy["navigation.collisionDetection.detectionDevice"] = current_collision_device_str
                    Trace.log(f"shielded fork tip di, new collision device:{current_collision_device_str}")

                if self.obs_dist is not None:
                    self.policy['navigation.obstacleStop.obsStopUnload.obsStopDist'] = self.obs_dist
                    self.policy['navigation.obstacleStop.obsStopLoad.loadObsStopDist'] = self.obs_dist
                self.policy['navigation.obstacleStop.obsStopUnload.obsExpansion'] = 0.02
                self.policy['navigation.obstacleStop.obsStopLoad.loadObsExpansion'] = 0.01

                # Navigation.setObsStopDist(self.obs_dist)

                Navigation.appendCustomPolicy("policy", self.policy)
                time.sleep(0.5)

                self.set_policy = True
                current_collision_device_change = (RobotParam.getConfig("navigation",
                                                                        "collisionDetection.detectionDevice"))
                unload_stop_dist = (RobotParam.getConfig("navigation", "obstacleStop.obsStopUnload.obsStopDist"))
                Trace.log(
                    f"policy :{self.policy},current_collision_device_change:{current_collision_device_change}, cur_unload_stop_dist:{unload_stop_dist}")

            # 开始后退
            if self.back_action.action_status not in [ScriptStatus.FAILED, ScriptStatus.FINISHED, ActionStatus.FAILED,
                                                      ActionStatus.FINISHED]:
                self.back_action.run()

            if self.back_action.action_status in [ScriptStatus.FAILED, ActionStatus.FAILED]:
                return

            # 前进的时候不要设置避障距离
            vx = NavSpeed.getSpeeds()[0]
            if vx > 0.005 and not self.clear_policy:
                Navigation.clearPolicy()
                self.clear_policy = True
                self.set_policy = False
                Trace.log(f"vx:{vx},clear policy", True, True)
            elif vx <= 0 and not self.set_policy:
                Trace.log(f"vx:{vx},set policy", True, True)
                Navigation.appendCustomPolicy("policy", self.policy)
                time.sleep(0.5)
                Navigation.goPathParam(dict())
                self.clear_policy = False
                self.set_policy = True

            # unload 叉尖 di sensor 触发检测（collision 模式由 rbk 底层处理，脚本无需操作）
            if (self.operation_type == "unload" and ConfigParams.forkDiEnableAtUnload
                    and self.fork_tip_di_ids and ConfigParams.diTriggerMeasureUnload != "collision"):

                # 读取叉尖 di 状态
                fork_tip_di_status = [Di.getDi(di_id) for di_id in self.fork_tip_di_ids]
                di_triggered = any(fork_tip_di_status)

                if ConfigParams.diTriggerMeasureUnload == "autoClearError":
                    # autoClearError 模式：触发时停车报错，恢复时清除异常并继续
                    if di_triggered:
                        # di 触发，开始计时（防抖 0.3s）
                        if self.di_trigger_start_time is None:
                            self.di_trigger_start_time = time.time()
                        elif time.time() - self.di_trigger_start_time > 0.3:
                            # 持续触发超过 0.3s，停车并报错
                            if not self.di_triggered_stopped:
                                Navigation.stopRobotNow()
                                Navigation.setTaskError("ForkTipDiTrigger", f"unload fork tip di triggered, goods detected")
                                self.di_triggered_stopped = True
                                Trace.log(f"autoClearError: fork tip di triggered, stopped robot")
                            # 重置清除计时
                            self.di_clear_start_time = None
                    else:
                        # di 未触发
                        self.di_trigger_start_time = None
                        if self.di_triggered_stopped:
                            # 之前因 di 触发而停止，现在 di 恢复，开始计时（防抖 0.3s）
                            if self.di_clear_start_time is None:
                                self.di_clear_start_time = time.time()
                            elif time.time() - self.di_clear_start_time > 0.3:
                                # 持续恢复超过 0.3s，清除异常并恢复运行
                                if Navigation.errorExists("ForkTipDiTrigger"):
                                    Navigation.clearTaskError("ForkTipDiTrigger")
                                Navigation.goPathParam(dict())  # 恢复路径规划
                                self.di_triggered_stopped = False
                                self.di_clear_start_time = None
                                Trace.log(f"autoClearError: fork tip di cleared, resumed robot")
                        else:
                            # 正常运行中，清除计时
                            self.di_clear_start_time = None

                elif ConfigParams.diTriggerMeasureUnload == "failTask":
                    # failTask 模式：触发时停车并失败任务
                    if di_triggered:
                        if self.di_trigger_start_time is None:
                            self.di_trigger_start_time = time.time()
                        elif time.time() - self.di_trigger_start_time > 0.3:
                            # 持续触发超过 0.3s，停车并失败任务
                            Navigation.stopRobotNow()
                            Navigation.setTaskError("UnloadTipDiFail", f"unload fork tip di triggered, fail task")
                            self.action_status = ActionStatus.FAILED
                            Trace.log(f"failTask: fork tip di triggered, failed task")
                            return
                    else:
                        self.di_trigger_start_time = None

            # 如果没有到位 di
            if not self.check_di:
                self.action_status = ActionStatus(self.back_action.action_status.value)
                return

            # 获取到位 di 的状态
            self.di_status = [Di.getDi(d) for d in self.contact_di]

            r_loc = get_r_loc()

            dist2target = pos2Base(r_loc, self.final_target)
            # Trace.log(f"r_loc:{r_loc},final target :{self.final_target}")

            # 如果不需要检查所有的到位 di，一个到位任务结束
            if not self.check_all_contact_di:

                if dist2target[0] > 0.2 and any(self.di_status):
                    Navigation.setTaskError("NotReachGoal", f"reach di not reach goal, still {dist2target[0]}m left, ")
                    self.action_status = ActionStatus.FAILED
                    return

                # 任务结束超过 1 s，且没有到位 di 触发，则报错结束任务
                if self.back_action.action_status == ActionStatus.FINISHED and not all(self.di_status) and Timer.delay(
                        1):
                    Navigation.setTaskError("NoContactDiTriger", f"not trigger di but robot reach goal")
                    self.action_status = ActionStatus.FAILED
                    return
                # 一个到位任务结束
                if any(self.di_status):
                    if self.stop_robot():
                        self.action_status = ActionStatus.FINISHED
                        return

            # 仅检查所有到位 di 的情况
            else:
                if dist2target[0] > 0.2 and all(self.di_status):
                    Navigation.setTaskError("NotReachGoal", f"reach di not reach goal, still {dist2target[0]:.2f}m left, ")
                    self.action_status = ActionStatus.FAILED
                    return
                # 所有到位 di 没有全部触发，则报错结束任务
                if self.back_action.action_status == ActionStatus.FINISHED and not any(self.di_status) and Timer.delay(
                        1):
                    Navigation.setTaskError("NoContactDiTriger", f"not trigger di but robot reach goal")
                    self.action_status = ActionStatus.FAILED
                    return
                # 到位触发判断，从一个 di 触发后的一段时间内，其他 di 都触发，算任务结束；如果没有全部触发，则报错
                if any(self.di_status):
                    if Timer.delay(self.di_trigger_time):
                        if all(self.di_status):
                            if self.stop_robot():
                                self.action_status = ActionStatus.FINISHED
                        else:
                            Navigation.setTaskError("NoAllContactDiTriger", f"not all di triggered but robot reach goal")
                            self.action_status = ActionStatus.FAILED
                            return

        finally:
            if self.action_status in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                Laser.clear2DLaserWidth(ConfigParams.fork_tip_2D_lasers)
                Navigation.clearPolicy()

        # cur_state = dict()
        # cur_state['status'] = self.action_status
        # cur_state['method'] = self.method
        # cur_state['back status'] = self.back_action.action_status
        # cur_state['check_di'] = self.check_di
        # cur_state['contact_di'] = self.contact_di
        # cur_state['walk_dist'] = self.cal_walk_dist()
        # cur_state['di_status'] = self.di_status
        # cur_state['obs_dist'] = self.obsDist

    def reset(self):
        self.action_status = ScriptStatus.RUNNING

    def stop_robot(self):
        Navigation.stopRobotNow()
        Navigation.resetPath()
        return True

    def cancel(self):
        self.back_action.cancel()
        self.action_status = ActionStatus.FINISHED


class LocDetectGoods(BaseAction):
    def __init__(self, loc_name: str, rec_file: str):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_Info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.action_status = ActionStatus.INIT
        self.state = dict()
        self.loc_name = loc_name
        self.rec_file = rec_file
        self.target = [0, 0, 0, -1]
        self.detect_result = None
        self.rec_failed_time = 0
        self.max_rec_time = 10
        self.rec_status = 0

    def run(self):
        self.action_status = ActionStatus.RUNNING
        if self.init:
            self.init = False
            Recognize.resetRec()
            pass
            self.target = Navigation.getLM(self.loc_name, True)
            # self.target = [-5.67, 9.56, 3.14, 1]
        self.rec_status = Recognize.getRecStatus()
        if self.target[3] != -1:
            if self.rec_status == 3:
                self.rec_failed_time = self.rec_failed_time + 1
                if self.rec_failed_time > self.max_rec_time:
                    Navigation.setTaskError("TargetNotFilled", f"{self.loc_name} is not filled")
                    # f.is_goods_detected = False
                    self.action_status = ActionStatus.FAILED
                else:
                    Recognize.recTargetObs(ConfigParams.deviceName, self.target[0], self.target[1], self.target[2],
                                           ConfigParams.obsAreaMinHeight, ConfigParams.obsAreaMaxHeight,
                                           ConfigParams.obsAreaLength, ConfigParams.obsAreaWidth)
            elif self.rec_status == 0 or self.rec_status == 1:
                Recognize.recTargetObs(ConfigParams.deviceName, self.target[0], self.target[1], self.target[2],
                                       ConfigParams.obsAreaMinHeight, ConfigParams.obsAreaMaxHeight,
                                       ConfigParams.obsAreaLength, ConfigParams.obsAreaWidth)
                self.action_status = ActionStatus.RUNNING
            elif self.rec_status == 2:
                self.detect_result = Recognize.getRecResults()
                # r.setError(f"result:{self.detectResult}")
                if self.detect_result:
                    Navigation.setTaskError("TargetFilled", f"{self.loc_name} is filled")
                    # f.is_goods_detected = True
                    self.action_status = ActionStatus.FINISHED
        else:
            Navigation.setTaskError("TargetPointFilled", f"{self.loc_name} does not exist")
            self.action_status = ActionStatus.FAILED

        self.action_state["locName"] = self.loc_name
        self.action_state["target"] = self.target
        self.action_state["recFile"] = self.rec_file
        self.action_state["detectResult"] = self.detect_result
        self.action_state["locDetectMid70Status"] = self.action_status
        self.action_state["recStatus"] = self.rec_status
        self.action_state["recTime"] = self.rec_failed_time

    def reset(self):
        Recognize.resetRec()
        self.action_status = ActionStatus.RUNNING


class RunMotorByPosition(BaseAction):
    """功能说明：控制线性电机运动,发送电机运行终点高度，触发stop_di时终止运动"""

    def __init__(self, motor_name, position, max_speed=ConfigParams.fork_max_speed, action_name="RunMotor", stop_di=""):
        """
        Args:
            motor_name(string): 电机名
            position(float): 电机运行目标位置
            max_speed(float): 电机运行速度
            stop_di(string): 如果这个StopDI触发则表示运动到位

        使用示例：
        """
        super().__init__(action_name)
        if not motor_name:
            self.action_status = ActionStatus.FAILED
            Navigation.setTaskError("NoMotorInModel","not motor find in Device.Model, script failed")
            return
        self.motor_name = motor_name
        self.position = position
        self.max_speed = max_speed
        self.is_reach = False
        # self.motor_name = "DOMotor-000"
        # self.position = 0.05
        # self.max_speed = 1
        self.stop_di = stop_di
        self.init = False

        self.positions = []
        self.check_duration = 20
        self.fork_timestamps = []
        self.last_sample_time = None
        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.timeout = None
        self.cur_fork_height_at_init = None

    def _close_fork_dos(self):
        """关闭货叉 DO（仅对 fork_motor_name 生效）"""
        if self.motor_name == ConfigParams.fork_motor_name:
            if ConfigParams.upDo:
                Do.setDo(ConfigParams.upDo, not ConfigParams.upDoStatus)
            if ConfigParams.downDo:
                Do.setDo(ConfigParams.downDo, not ConfigParams.downDoStatus)

    def run(self):
        cur_fork_height = Motor.getMotorPos(self.motor_name)

        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.last_sample_time = time.time()
            self.start_time = time.time()
            self.init = True
            self.cur_fork_height_at_init = cur_fork_height

            # 目标位置比初始位置差得不大就不要执行动作了
            if (abs(self.position - cur_fork_height) <= max(ConfigParams.reach_up_dist, ConfigParams.reach_down_dist,
                                                            0.01)
                    and ConfigParams.module_type in ["straddleLiftFork", "counterBalanceFork"]):
                self.action_status = ActionStatus.FINISHED
                return

            # 把目标位置先夹到最大最小区间
            min_h, max_h = ConfigParams.min_height, ConfigParams.max_height
            self.position = clamp(self.position, min_h, max_h)
            Trace.log(f"position:{self.position}")

            # 仅对fork_motor_name进行超时检查
            if self.motor_name == ConfigParams.fork_motor_name:
                delta = self.position - cur_fork_height
                if delta > EPS:  # 上升
                    self.timeout = ConfigParams.loadTime
                elif delta < -EPS:  # 下降
                    self.timeout = ConfigParams.unloadTime
                else:  # 位置相同
                    self.timeout = None

            if ConfigParams.DOMotor:
                if self.position < (ConfigParams.max_height + ConfigParams.min_height) / 2:
                    vel = -0.01
                elif self.position > (ConfigParams.max_height + ConfigParams.min_height) / 2:
                    vel = 0.01
                else:
                    self.action_status = ActionStatus.FINISHED
                    return
                Motor.setMotorSpeed(self.motor_name, vel, self.stop_di)
            else:
                # 如果是搬运车，做一些最大最小高度的逻辑处理
                if ConfigParams.module_type == "liftFork":
                    if self.position < (ConfigParams.max_height + ConfigParams.min_height) / 2:
                        self.position = ConfigParams.min_height
                    elif self.position > (ConfigParams.max_height + ConfigParams.min_height) / 2:
                        self.position = ConfigParams.max_height

                # 考虑载货时的货叉升降速度
                if ConfigParams.module_type != "liftFork":

                    # 从输入参数和设备配置参数里选出最大速度
                    max_speed = min(ConfigParams.fork_max_speed, self.max_speed)

                    if Navigation.hasGoods():
                        # 通过下发位置判断向下还是向上运动
                        delta = self.position - cur_fork_height
                        if abs(delta) <= EPS:
                            self.action_status = ActionStatus.FINISHED
                            return
                        # 取最大速度
                        if delta > 0:
                            max_speed = min(max_speed, ConfigParams.upMaxSpeedWithGoods)
                        else:
                            max_speed = min(max_speed, ConfigParams.downMaxSpeedWithGoods)

                    self.max_speed = max_speed

                Motor.setMotorPosition(self.motor_name, self.position, self.max_speed, self.stop_di)

            # 货叉运动时打开对应 DO（仅对 fork_motor_name 生效）
            if self.motor_name == ConfigParams.fork_motor_name:
                delta = self.position - cur_fork_height  # DOMotor 分支不走上面的 delta，此处统一计算
                if delta > 0 and ConfigParams.upDo:
                    # 上升运动，打开 upDo
                    Do.setDo(ConfigParams.upDo, ConfigParams.upDoStatus)
                    Trace.log(f"fork moving up, set upDo:{ConfigParams.upDo} to {ConfigParams.upDoStatus}")
                elif delta < 0 and ConfigParams.downDo:
                    # 下降运动，打开 downDo
                    Do.setDo(ConfigParams.downDo, ConfigParams.downDoStatus)
                    Trace.log(f"fork moving down, set downDo:{ConfigParams.downDo} to {ConfigParams.downDoStatus}")

        # 检查超时（仅对fork_motor_name）
        if self.timeout is not None and (time.time() - self.start_time) > self.timeout:
            Navigation.setTaskError("ForkMoveTimeout", f"Fork motor timeout: {self.motor_name} exceeded {self.timeout}s")
            self.action_status = ActionStatus.FAILED
            return

        # pos = Motor.get_motor_pos(self.motor_name)
        self.is_reach = Motor.isMotorReached(self.motor_name)
        if self.is_reach:
            # 货叉运动结束，关闭对应 DO
            self._close_fork_dos()

            Trace.log(f"agv has base shift:{ConfigParams.base_shift}")
            if ConfigParams.base_shift and abs(self.position - ConfigParams.max_height) < EPS:
                Navigation.wheelBaseShift(True)
                # Navigation.setGoodsShape(1, 0.1, 1)
                Trace.log(f"base shift true")
            elif ConfigParams.base_shift and abs(self.position - ConfigParams.min_height) < EPS:
                Navigation.wheelBaseShift(False)
                # Navigation.clearGoodsShape()

                Trace.log(f"base shift false")

            self.action_status = ActionStatus.FINISHED

        # 检测货叉的运动是否卡住了
        now = time.time()
        # 0.5s 采一次数据，50ms过于频繁似乎没有必要
        if now - self.last_sample_time > 0.5:
            self.last_sample_time = now
            self.positions.append(cur_fork_height)
            self.fork_timestamps.append(now)

            if self.fork_timestamps and now - self.fork_timestamps[0] >= self.check_duration:
                min_pos = min(self.positions)
                max_pos = max(self.positions)
                if abs(max_pos - min_pos) <= 0.005:
                    Navigation.setTaskError("ForkNoMove", f"fork height not change between:{min_pos}m-{max_pos}m in {self.check_duration}s")
                    self.action_status = ActionStatus.FAILED
                    return

            while self.fork_timestamps and now - self.fork_timestamps[0] > self.check_duration:
                self.positions.pop(0)
                self.fork_timestamps.pop(0)

        # self.action_state["motor_name"] = self.motor_name
        # self.action_state["motor_speed"] = Motor.get_motor_speed(self.motor_name)
        # self.action_state["motor_position"] = Motor.get_motor_pos(self.motor_name)
        # self.action_state["status"] = self.action_status
        # Trace.log(self.action_state)
        # print(json.dumps(self.action_state))

    def reset(self):
        Motor.resetMotor(self.motor_name)
        self.action_status = ActionStatus.RUNNING
        self.fork_timestamps.clear()
        self.positions.clear()
        self.init = False

    def cancel(self):
        Motor.resetMotor(self.motor_name)
        self.fork_timestamps.clear()
        self.positions.clear()
        self.init = False
        self._close_fork_dos()
        self.action_status = ActionStatus.FAILED


class RunMotorBySpeed(BaseAction):
    def __init__(self, motor_name, max_speed, stop_di=""):
        """
        控制线性电机运动，发送电机运行速度，直到触发stop_di结束运动
        Args:
            motor_name(string): 电机名
            max_speed(float): 电机运行速度
            stop_di(string): 如果这个StopDI触发则表示运动到位

        """
        super().__init__()
        self.motor_name = motor_name
        self.max_speed = max_speed
        self.stop_di = stop_di
        self.init = False
        Motor.resetMotor(self.motor_name)

    def run(self):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            Motor.setMotorSpeed(self.motor_name, self.max_speed, self.stop_di)
        if Motor.isMotorReached(self.motor_name):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.INIT
        Motor.resetMotor(self.motor_name)


class RunMotorByDOInterlock(BaseAction):
    """
    功能说明：控制DO电机运动，采用interlock方式，up_di/down_di触发时结束运动,超过延时时间自动停止
    """

    def __init__(self, operation, pump_do, leak_do, up_di, down_di, up_delay_time=5.0, down_delay_time=5.0):
        super().__init__()
        """
            Args:
                operation(string): "up" or "down" 选择上升或者下降
                positive_do(int): 泵电机DO,正向DO,不能和negative_do同时打开
                negative_do(int): 泄漏阀DO,负向DO,不能和positive_do同时打开
                up_di(int): 抬升到位 DI。货叉举升过程中，该 DI 触发可以结束货叉举升过程。
                down_di(int): 下降到位 DI。货叉下降过程中，该 DI 触发可以结束货叉下降过程。
                up_delay_time(float): 上升延时时间。货叉举升过程中，此参数用来限制货叉上升的最大时间，若超过此延时时间举升未到位，举升动作也会停止。
                down_delay_time(float): 下降延时时间。货叉下降过程中，此参数用来限制货叉下降的最大时间，若超过此延时时间下降未到位，下降动作也会停止。

        """
        self.operation = operation  # 如果是 up 上升，如果是 down 下降
        self.init = False
        self.pump_do = pump_do
        self.leak_do = leak_do
        self.up_di = up_di
        self.down_di = down_di
        self.up_delay_time = up_delay_time
        self.down_delay_time = down_delay_time
        self.start_time = 0
        self.action_state = dict()

    def run(self):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            self.start_time = time.time()
            self.reset()

        if self.is_reached():
            Do.setDo(self.pump_do, False)
            Do.setDo(self.leak_do, False)
            self.action_status = ActionStatus.FINISHED
            return

        if self.operation == "up":
            Do.setDo(self.pump_do, True)
            Do.setDo(self.leak_do, False)
        elif self.operation == "down":
            Do.setDo(self.pump_do, False)
            Do.setDo(self.leak_do, True)

        #
        # self.action_state['action_name'] = self.__class__.__name__
        # self.action_state["action_runtime"] = time.time() - self.start_time
        # self.action_state["up_or_down_operation"] = self.operation
        # self.action_state["positive_do"] = self.positive_do
        # self.action_state["negative_do"] = self.negative_do
        # self.action_state["up_di"] = self.up_di
        # self.action_state['down_di'] = self.down_di
        # self.action_state['status'] = self.action_status

    def is_reached(self):
        is_reach = False
        if self.operation == "up":
            up_di_status = Di.getDi(self.up_di)
            if up_di_status:
                is_reach = True
            if time.time() - self.start_time > self.up_delay_time:
                is_reach = True
        elif self.operation == "down":
            down_di_status = Di.getDi(self.down_di)
            if down_di_status:
                is_reach = True
            if time.time() - self.start_time > self.down_delay_time:
                is_reach = True
        return is_reach

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        Do.setDo(self.leak_do, False)
        Do.setDo(self.pump_do, False)


# 用于走直线
class GoPath(BaseAction):
    def __init__(self, args: Optional[dict] = None):
        super().__init__("GoPath")
        self.goal = [0, 0, 0]
        self.action_name = self.__class__.__name__
        self.init = False
        self.action_status = ActionStatus.INIT
        self.param = {}
        self.args = args if args else {}
        """ eg.
        args = {"x":0,
                "y":0,
                "coordinate":0,
                "reachAngle":0,
                "reachDist":0
                }
        """
        Trace.log(f"go path init")

    def run(self):
        self.action_status = ActionStatus.RUNNING
        args = self.args
        if args is None:
            args = Module.getTaskArgs()

        if not self.init:
            self.init = True
            Navigation.resetPath()
            if "x" in args and "y" in args and "coordinate" in args:
                if "x" in args:
                    self.goal[0] = float(args["x"])
                if "y" in args:
                    self.goal[1] = float(args["y"])
                if "theta" in args:
                    self.goal[2] = float(args["theta"])
                    if "reachAngle" in args:
                        Navigation.setPathReachAngle(float(args["reachAngle"]))
                else:
                    Navigation.setPathReachAngle(math.pi)
                if "reachAngle" in args:
                    Navigation.setPathReachAngle(float(args["reachAngle"]))
                if "reachDist" in args:
                    Navigation.setPathReachDist(float(args["reachDist"]))
                if "useOdo" in args:
                    Navigation.setPathUseOdo(bool(int(args["useOdo"])))
                if "backMode" in args:
                    Navigation.setPathBackMode(bool(int(args["backMode"])))
                if "maxSpeed" in args:
                    Navigation.setPathMaxSpeed(float(args["maxSpeed"]))
                if "maxRot" in args:
                    Navigation.setPathMaxRot(float(args["maxRot"]))
                if "holdDir" in args:
                    Navigation.setPathHoldDir(float(args["holdDir"]))
                if "maxAcc" in args:
                    self.param["maxAcc"] = float(args["maxAcc"])
                if "maxDec" in args:
                    self.param["maxDec"] = float(args["maxDec"])
                if "maxRotAcc" in args:
                    self.param["maxRotAcc"] = float(args["maxRotAcc"])
                if "maxRotDec" in args:
                    self.param["maxRotDec"] = float(args["maxRotDec"])

                Trace.log(f"goal: {str(self.goal)}")
                if args["coordinate"] == "robot":
                    Navigation.setPathOnRobot([0, self.goal[0]], [0, self.goal[1]], self.goal[2])
                elif args["coordinate"] == "world":
                    x = Loc.getPose()["x"]
                    y = Loc.getPose()["y"]
                    Navigation.setPathOnWorld([x, self.goal[0]], [y, self.goal[1]], self.goal[2])
                else:
                    Navigation.setTaskError("WrongCoordinate", f"coordinate only support robot and world. Input is {args['coordinate']}")
                    self.action_status = ScriptStatus.FAILED

            else:
                Navigation.setTaskError("GoPathArgsWrong", f"args wrong")
                self.action_status = ActionStatus.FAILED
            Navigation.goPathParam(self.param)

        if self.action_status != ActionStatus.FAILED:
            # Trace.log(f"is reach:{Navigation.isPathReached()}")
            if Navigation.isPathReached():
                self.action_status = ActionStatus.FINISHED
            else:
                self.action_status = ActionStatus.RUNNING

    def reset(self):
        Navigation.resetPath()
        Trace.log(f"reset path")
        self.action_status = ActionStatus.RUNNING

    def cancel(self):
        Navigation.resetPath()
        self.action_status = ActionStatus.FAILED


class MoveChassisByY(BaseAction):
    def __init__(self, robot2pos):
        super().__init__("MoveChassisByX")

        self.x = -robot2pos[0]
        self.y = -robot2pos[1]
        self.yaw = -robot2pos[2]
        self.shiftMotor = ConfigParams.shiftMotor
        target_world = pos2World([self.x, self.y, self.yaw], get_r_loc())

        # 有横移货叉调三步，先调yaw，再调x和货叉横移y
        if self.shiftMotor != "":
            chassis_yaw_args = {
                "x": 0,
                "y": 0,
                "theta": self.yaw,
                "backMode": 0,
                "maxSpeed": 0.1,
                "maxRot": math.radians(2),
                "coordinate": Coordinate.ROBOT.value,
                "reachAngle": math.radians(1),
                "reachDist": 0.01
            }
            self.yaw = GoPath(chassis_yaw_args)
            shift_position = Motor.getMotorPos(self.shiftMotor)
            self.shift = RunMotorByPosition(self.shiftMotor, shift_position + self.y, 0.01)
            chassis_x_args = {
                "x": self.x,
                "y": 0,
                "theta": 0,
                "backMode": 0,
                "maxSpeed": 0.1,
                "maxRot": math.radians(2),
                "coordinate": Coordinate.ROBOT.value,
                "reachAngle": math.radians(1),
                "reachDist": 0.01
            }
            if self.x < 0:
                chassis_x_args["backMode"] = 1
            self.x = GoPath(chassis_x_args)
        # 没横移调直接全向车 holddir
        else:
            chassis_args = {
                "x": self.x,
                "y": self.y,
                "theta": self.yaw,
                "holdDir": math.degrees(target_world[2]),
                "backMode": 0,
                "maxSpeed": 0.05,
                "maxRot": math.radians(3),
                "coordinate": Coordinate.ROBOT.value,
                "reachAngle": math.radians(0.5),
                "reachDist": 0.005
            }
            Trace.log(f"chassis args:{chassis_args}")
            if self.x < 0:
                chassis_args["backMode"] = 1
            self.chassis_move = GoPath(chassis_args)

    def run(self):
        if not self.init:
            self.init = True
        if self.chassis_move.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
            self.chassis_move.run()
        elif self.chassis_move.action_status == ActionStatus.FINISHED:
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.init = False

    def cancel(self):
        self.init = False
        self.action_status = ActionStatus.FAILED


class GoTwoStraightLine(BaseAction):
    def __init__(self, world_target, min_ahead_dist, ahead_dist, back_dist, speed, max_angle=20.0, dec_dist=1.0,
                 return_back=False):
        super().__init__("GoTwoStraightLine")
        self.go3 = None
        self.go2 = None
        self.go1 = None
        self.temp_start = []
        self.first_point = None
        self.start_pos = []
        self.world_target = world_target
        self.min_ahead_dist = min_ahead_dist
        self.ahead_dist = ahead_dist
        self.back_dist = back_dist
        self.speed = speed
        self.max_angle = max_angle
        self.dec_dist = dec_dist
        self.step = 20

        self.go_step = [False] * 3
        self.action_status = ActionStatus.INIT
        self.init = False
        self.return_back = return_back
        pos = get_r_loc()
        # 如果执行去目标点
        if not self.return_back:

            # 栈板前的点
            self.second_point = pos2World([self.min_ahead_dist, 0, 0], self.world_target)
            # 终点
            self.third_point = pos2World([-self.back_dist, 0, 0], self.world_target)

            # 记录起始点
            self.start_pos = get_r_loc()
            # 如果从当前点出发区栈板前的点角度不满足要求就开始迭代
            if abs(self.cal_angle(self.start_pos, self.second_point)) > self.max_angle:
                self.start_pos[2] = self.world_target[2]
                angle, self.temp_start = self.search_min_angle_str(self.max_angle, self.step)
            else:
                self.temp_start = self.start_pos
            ScriptData.set('goTwoStraightLine',
                           {'points': [self.start_pos, self.temp_start, self.second_point, self.world_target]})
        # 如果执行原路返回
        else:
            points = ScriptData.get('goTwoStraightLine').get('points', [])
            Trace.log(f"points:{points}")
            if not points:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError("NoRoute", "no route before leave loc, script failed")

            self.temp_start = points[2]  # 退出库位的第一个点，栈板 min_ahead_dist 前置点
            self.second_point = points[1]  # 退出库位第二个点，ahead_dist 点
            self.third_point = points[0]  # 退出库位第三个点，前置点/起始点
            check_point = points[3]
            dist = cal_dist(check_point, pos)
            if dist >= 0.5:
                Navigation.setTaskError("NotAtLastLoadPoint", "cannot leave loc when robot is not at last load point")
                self.action_status = ActionStatus.FAILED
            ScriptData.set('goTwoStraightLine', {})

    def run(self):
        if not self.init:
            self.init = True
            # 如果执行去目标点

            if not self.return_back:
                go1_args = {
                    "x": self.temp_start[0],
                    "y": self.temp_start[1],
                    "theta": self.temp_start[2],
                    "backMode": 0,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(5),
                    "coordinate": Coordinate.WORLD.value,
                    "reachAngle": math.radians(1),
                    "reachDist": 0.01
                }
                go2_args = {
                    "x": self.second_point[0],
                    "y": self.second_point[1],
                    "theta": self.second_point[2],
                    "backMode": 1,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(5),
                    "coordinate": Coordinate.WORLD.value,
                    "reachAngle": math.radians(0.2),
                    "reachDist": 0.005
                }
                go3_args = {
                    "x": self.third_point[0],
                    "y": self.third_point[1],
                    "theta": self.third_point[2],
                    "backMode": 1,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(5),
                    "coordinate": Coordinate.WORLD.value,
                    "reachAngle": math.radians(0.2),
                    "reachDist": 0.005
                }
            # 如果执行原路返回
            else:
                go1_args = {
                    "x": self.temp_start[0],
                    "y": self.temp_start[1],
                    "theta": self.temp_start[2],
                    "backMode": 0,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(5),
                    "coordinate": Coordinate.WORLD.value,
                    "reachAngle": math.radians(1),
                    "reachDist": 0.01
                }
                go2_args = {
                    "x": self.second_point[0],
                    "y": self.second_point[1],
                    "theta": self.second_point[2],
                    "backMode": 0,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(5),
                    "coordinate": Coordinate.WORLD.value,
                    "reachAngle": math.radians(1),
                    "reachDist": 0.01
                }
                go3_args = {
                    "x": self.third_point[0],
                    "y": self.third_point[1],
                    "theta": self.third_point[2],
                    "backMode": 1,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(5),
                    "coordinate": Coordinate.WORLD.value,
                    "reachAngle": math.radians(1),
                    "reachDist": 0.01
                }
            self.go1 = GoPath(go1_args)
            self.go2 = GoPath(go2_args)
            self.go3 = GoPath(go3_args)

        if not self.go_step[0]:
            if self.go1.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go1.run()
            if self.go1.action_status == ActionStatus.FINISHED:
                self.go_step[0] = True
        elif self.go_step[0] and not self.go_step[1]:
            if self.go2.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go2.run()
            if self.go2.action_status == ActionStatus.FINISHED:
                self.go_step[1] = True
        elif self.go_step[1] and not self.go_step[2]:
            if self.go3.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go3.run()
            if self.go3.action_status == ActionStatus.FINISHED:
                self.go_step[2] = True
        if all(self.go_step):
            self.action_status = ActionStatus.FINISHED

    def cal_angle(self, start_pos, end_pos):
        start2end = pos2Base(start_pos, end_pos)
        angle = math.degrees(math.atan2(start2end[1], start2end[0]))
        Trace.log(f"angle:{angle}")
        return angle

    def search_min_angle_str(self, max_angle, step):
        for n in range(1, step + 1):
            adjust_dist = self.ahead_dist / self.step * n
            # 临时构造一个新的起点：在原 start_pos 基础上往前平移
            temp_start = pos2World([adjust_dist, 0, 0], self.start_pos)
            angle = abs(self.cal_angle(temp_start, self.second_point))

            if angle <= max_angle:
                # self.first_point = temp_start
                Trace.log(f"满足角度要求，当前角度：{angle:.2f}°，使用第 {n} 次调整")
                return angle, temp_start  # 成功，返回当前角度

        angle = abs(self.cal_angle(temp_start, self.second_point))
        Trace.log(f"未满足角度要求，当前角度：{angle:.2f}°")
        return angle, temp_start

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        Navigation.resetPath()

    def cancel(self):
        Navigation.resetPath()
        self.action_status = ScriptStatus.FAILED


class ActionStatus(IntEnum):
    """ 动作运行状态枚举，对标 ActionStatus """
    INIT = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


class RotateDirection(IntEnum):
    """ 旋转方向枚举 """
    NEARBY = 0
    COUNTERCLOCKWISE = 1
    CLOCKWISE = -1


def main():
    # 设备 参数 脚本参数的回调
    RobotParam.setConfigChangeCallBack(_robot_config_change_callback)
    RobotParam.setDeviceChangeCallBack(_robot_device_change_callback)
    ScriptParam.setConfigChangeCallBack(_script_config_callback)
    Module.init()

    validated_params = {}
    validator = ParamValidator(InputParams.builder.toDict())
    checked_args = False

    f = Fork()

    while True:
        if f.event_safe_move_check:
            f.safe_move_check()
        if f.event_modbus:
            validated_params = f.modbus()

        f.period_run()

        input_params = validated_params or Module.getTaskArgs()
        status = Module.getStatus()

        if ConfigParams.scriptDebug:
            # Trace.log(f"script status:{status}")
            pass

        if status == ScriptStatus.RUNNING:
            args = {}
            if not checked_args:
                checked_args = True
                f.init_args = False
                Trace.log(f"check before, args:{input_params}")
                if args is None:
                    Navigation.setTaskError("ArgsIsNone", f"args is none,script failed")
                    f.script_status = ScriptStatus.FAILED
                else:
                    try:
                        # 验证参数
                        args = validator.validate(input_params)
                        f.script_status = ScriptStatus.RUNNING
                        Trace.log(f"check ok, args:{json.dumps(args, indent=2)}")
                    except ValueError as e:
                        Trace.log(f"check error:f{e}")

            if f.script_status in [ScriptStatus.FINISHED, ScriptStatus.FAILED] and checked_args:
                keys_to_delete = [k for k in f.trace_chart if k.startswith("action.")]
                for k in keys_to_delete:
                    del f.trace_chart[k]

                f.min_safe_height = 0.0
                f.save_mileage()
                Module.setStatus(f.script_status)
                checked_args = False
                validated_params = {}
                delete_deduct_area("PalletRobotDeductArea", Coordinate.WORLD)
                delete_deduct_area("noRecDeduct2World", Coordinate.WORLD)
                Trace.log(f"script end, script_status: {f.script_status}")
                f.reset()
                continue

            f.run(args)

        time.sleep(0.1)


if __name__ == '__main__':
    main()
