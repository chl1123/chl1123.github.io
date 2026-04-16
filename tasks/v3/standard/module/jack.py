# -*- coding: utf-8 -*-
# @Date : 2026/4/16
# @Author : zhaopengfei
# @Coding : 顶升车
# @Update : fix: 去除atsite字段用于到点动作 add:增加 FirstRec 后"太近→后退→SecondRec"功能 feat:重构jackload部分场景输入参数


import json
import math
import time
from enum import IntEnum
from syspy.utils.time import Timer

from datetime import datetime

from syspy import (Module, Logger, Motor, Navigation, Loc, Recognize,
                   CodeScanner, ScriptStatus, Trace, NavSpeed, Controller, LevelDB, Di, Container, Odometer)
from syspy.lib.module import pos2Base, pos2World, ModuleBase, SafeMoveStatus
from standard import goPath, goBezier
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ScriptParam, BindType, BindItem

param_loader = ScriptParam(__file__)
from syspy.lib.robot_param import RobotParam
from syspy.utils import Coordinate

log = Logger("jack")


# ============================================================================
# Debug 日志辅助
# ============================================================================
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
        # Prepend timestamp to the first argument
        if args:
            first_arg = f"{timestamp} {args[0]}"
            Trace.log(first_arg, *args[1:], **kwargs)
        else:
            Trace.log(timestamp, **kwargs)

class _SingletonDBManager:
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_db()

    def _init_db(self):
        raise NotImplementedError

# ============================================================================
# 顶升次数统计管理类
# ============================================================================
class JackCountManager(_SingletonDBManager):
    KEY_TOTAL_COUNT = "jackTotalCount"
    KEY_TODAY_COUNT = "jackTodayCount"
    KEY_LAST_DATE = "jackLastDate"

    def _init_db(self):
        try:
            self._db = LevelDB("run")
            if self._db.get(self.KEY_TOTAL_COUNT, "int") is None:
                self._db.add(self.KEY_TOTAL_COUNT, 0, False)
                self._db.add(self.KEY_TODAY_COUNT, 0, False)
                self._db.add(self.KEY_LAST_DATE, "", False)
                debug_trace("JackCountManager: 数据库初始化完成")
        except Exception as e:
            Trace.log(f"JackCountManager: 数据库初始化失败: {e}")
            self._db = None

    def _get_today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _check_and_reset_daily(self):
        if self._db is None:
            return
        try:
            today = self._get_today_str()
            last_date = self._db.get(self.KEY_LAST_DATE, "str") or ""
            if last_date != today:
                self._db.put(self.KEY_TODAY_COUNT, 0)
                self._db.put(self.KEY_LAST_DATE, today)
        except Exception as e:
            Trace.log(f"JackCountManager: 检查日期失败: {e}")

    def increment_count(self):
        if self._db is None:
            return
        try:
            self._check_and_reset_daily()
            total_count = self._db.get(self.KEY_TOTAL_COUNT, "int") or 0
            today_count = self._db.get(self.KEY_TODAY_COUNT, "int") or 0
            self._db.put(self.KEY_TOTAL_COUNT, total_count + 1)
            self._db.put(self.KEY_TODAY_COUNT, today_count + 1)
            self._db.put(self.KEY_LAST_DATE, self._get_today_str())
            debug_trace(f"[STATS] Jack count: Total={total_count + 1}, Today's count={today_count + 1}")
        except Exception as e:
            Trace.log(f"JackCountManager: Update jack count failed: {e}")


# 创建全局实例
jack_count_manager = JackCountManager()

# ============================================================================
# 顶升电机标零状态管理类
# ============================================================================
class JackCalibManager(_SingletonDBManager):
    KEY_CALIB_DONE = "jackCalibDone"

    def _init_db(self):
        try:
            self._db = LevelDB("run")
            if self._db.get(self.KEY_CALIB_DONE, "int") is None:
                self._db.add(self.KEY_CALIB_DONE, 0, False)
                Trace.log("JackCalibManager: DB 初始化完成，jackCalibDone=0")
        except Exception as e:
            Trace.log(f"JackCalibManager: DB 初始化失败: {e}")
            self._db = None

    def is_calib_done(self) -> bool:
        """返回 DB 中记录的标零完成状态（int: 0=未完成, 1=已完成）"""
        if self._db is None:
            return False
        try:
            return self._db.get(self.KEY_CALIB_DONE, "int") == 1
        except Exception as e:
            Trace.log(f"JackCalibManager: 读取 calib 状态失败: {e}")
            return False

    def set_calib_done(self, done: bool):
        """更新 DB 中的标零完成状态（bool → int: True=1, False=0）"""
        if self._db is None:
            return
        try:
            val = int(done)
            self._db.put(self.KEY_CALIB_DONE, val)
            Trace.log(f"JackCalibManager: jackCalibDone 已更新为 {val}")
        except Exception as e:
            Trace.log(f"JackCalibManager: 写入 calib 状态失败: {e}")


# 创建全局实例
jack_calib_manager = JackCalibManager()


# --- ConfigParams 类（放在前面） ---
class ConfigParams:
    """配置管理器，用于管理动态配置参数"""
    config = {}
    timeout = None
    jack_motor_speed = None
    jack_min_height = None
    jack_max_height = None

    # Debug开关
    debug_mode = False
    auto_calib_enable = False  # 开机自动标零开关（默认关闭）

    # 导航配置参数（bezier）
    bezier_back_dist = 0.0
    bezier_adjust_dist = 2.0
    bezier_min_ahead_dist = 0.0
    bezier_is_backwards = False
    bezier_is_hold_dir = False
    bezier_max_speed = 0.5
    bezier_max_accele = 0.3
    bezier_max_decele = 0.2
    bezier_decele_dist = 1.0
    bezier_curvature_limit = 1.3
    bezier_path_dist_accuracy = 0.01
    bezier_path_angle_accuracy = 0.05

    # 导航配置参数（polyline）
    polyline_back_dist = 0.0
    polyline_ahead_dist = 2.0
    polyline_min_ahead_dist = 0.0
    polyline_is_backwards = False
    polyline_is_hold_dir = False
    polyline_max_speed = 0.5
    polyline_max_accele = 0.3
    polyline_max_decele = 0.2
    polyline_decele_dist = 1.0
    polyline_max_angle = 1.3
    polyline_path_dist_accuracy = 0.01
    polyline_path_angle_accuracy = 0.05

    # PGV二次调整配置参数（policy 结构）
    pgv_code_adjust_type = "singleCode"  # "singleCode" | "codeNumber"
    pgv_scan_device = ""  # 绑定的扫码设备名称
    pgv_angle_adjust_type = "parallelToCode"  # 角度调整模式
    pgv_position_adjust_type = "frontAndBack"  # 位置调整模式（singleCode 专用）
    pgv_code_number = ""  # 指定二维码编号（singleCode 可选）
    pgv_line_angle_threshold = 10.0  # multiLine 模式最大旋转角范围（deg）
    pgv_adjust_region = ""  # multiLine 模式调整区域 JSON 字符串
    pgv_spin = True  # 随动状态下货叉朝向不动
    pgv_reach_dist = 0.02  # 到点距离精度（m）
    pgv_reach_angle = 1.0  # 到点角度精度（deg）

    # 报错保护配置参数
    load_again_error = True  # 是否启用重复取货保护

    module_type = RobotParam.getDevice("Model-000", "moduleType")
    jack_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.jackMotor")
    motor_func = RobotParam.getDevice(f"{jack_motor_name}", "func")
    reset_by_speed = RobotParam.getDevice(f"{jack_motor_name}", "resetMode")
    jack_up_di = RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.upLimitDI")
    jack_zero_di = RobotParam.getDevice(f"{jack_motor_name}", f"resetMode.{reset_by_speed}.zeroDI")

    def __init__(self):
        self._build_and_load_config()

    @classmethod
    def _build_and_load_config(cls):
        """构建并加载配置参数"""
        module_type = RobotParam.getDevice("Model-000", "moduleType")
        jack_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.jackMotor")
        motor_func = RobotParam.getDevice(f"{jack_motor_name}", "func")
        reset_by_speed = RobotParam.getDevice(f"{jack_motor_name}", "resetMode")

        builder = param_loader.builderConfig()

        with builder.GROUPS():
            # ============================================
            # 通用配置组（Debug + 标零 + 报错保护）
            # ============================================
            with builder.GROUP(key="generalConfig", name="General Configuration",
                               desc="General, calibration and error protection parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="debugMode", name="Debug Mode",
                                       desc="Enable debug mode to show debug tasks and low-frequency parameters"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="autoCalibEnable", name="Auto Calib On Startup",
                                       desc="Enable automatic motor calibration (zero) on script startup"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="loadAgainError", name="Load Again Error Protection",
                                       desc="Enable protection to prevent loading when goods already on robot "):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)

            # ============================================
            # 电机与IO配置组（电机速度 + DI + DO + 延迟）
            # ============================================
            with builder.GROUP(key="motorIoConfig", name="Motor & IO Configuration",
                               desc="Motor speed, DI/DO and delay parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="jackMotorSpeed", name="Jack Motor Speed",
                                       desc="Speed of the jack motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.015, min_value=0.001, max_value=0.1)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.001)
                    with builder.CHILD(key="jackMinHeight", name="Jack Min Height",
                                       desc="The min height of jack motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.minLength"))
                        builder.UNIT("m")
                        builder.SINGLESTEP(0.001)
                    with builder.CHILD(key="jackMaxHeight", name="Jack Max Height",
                                       desc="The max height of jack motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.maxLength"))
                        builder.UNIT("m")
                        builder.SINGLESTEP(0.001)

            # ============================================
            # 导航配置组（Bezier + Polyline）
            # ============================================
            with builder.GROUP(key="navigationConfig", name="Navigation Config",
                               desc="Bezier and Polyline navigation parameters (site-specific, rarely changed)"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    # --- Bezier ---
                    with builder.CHILD(key="bezierBackDist", name="[Bezier] Back Distance",
                                       desc="Back distance before starting bezier"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierAdjustDist", name="[Bezier] Adjust Distance",
                                       desc="Adjust distance for decreasing curvature limit"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(2.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierMinAheadDist", name="[Bezier] Min Ahead Distance",
                                       desc="Minimum ahead distance"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierIsBackwards", name="[Bezier] Is Backwards",
                                       desc="Enable backward mode"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="bezierIsHoldDir", name="[Bezier] Hold Direction",
                                       desc="Whether to hold direction during navigation"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="bezierMaxSpeed", name="[Bezier] Max Speed",
                                       desc="Maximum speed for bezier navigation"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5)
                        builder.UNIT("m/s")
                    with builder.CHILD(key="bezierMaxAccele", name="[Bezier] Max Acceleration",
                                       desc="Maximum acceleration"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3)
                        builder.UNIT("m/s²")
                    with builder.CHILD(key="bezierMaxDecele", name="[Bezier] Max Deceleration",
                                       desc="Maximum deceleration"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.2)
                        builder.UNIT("m/s²")
                    with builder.CHILD(key="bezierDeceleDist", name="[Bezier] Deceleration Distance",
                                       desc="Distance to start deceleration before target"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierCurvatureLimit", name="[Bezier] Curvature Limit",
                                       desc="Curvature limit for bezier path"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.3)
                    with builder.CHILD(key="bezierPathDistAccuracy", name="[Bezier] Path Dist Accuracy",
                                       desc="Position accuracy for path following"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.01)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierPathAngleAccuracy", name="[Bezier] Path Angle Accuracy",
                                       desc="Angle accuracy for path following"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05)
                        builder.UNIT("rad")
                    # --- Polyline ---
                    with builder.CHILD(key="polylineBackDist", name="[Polyline] Back Distance",
                                       desc="Back distance before starting polyline"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylineAheadDist", name="[Polyline] Ahead Distance",
                                       desc="Ahead distance for line angle adjustment"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(2.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylineMinAheadDist", name="[Polyline] Min Ahead Distance",
                                       desc="Minimum ahead distance"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylineIsBackwards", name="[Polyline] Is Backwards",
                                       desc="Enable backward mode"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="polylineIsHoldDir", name="[Polyline] Hold Direction",
                                       desc="Whether to hold direction during navigation"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="polylineMaxSpeed", name="[Polyline] Max Speed",
                                       desc="Maximum speed for polyline navigation"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5)
                        builder.UNIT("m/s")
                    with builder.CHILD(key="polylineMaxAccele", name="[Polyline] Max Acceleration",
                                       desc="Maximum acceleration"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3)
                        builder.UNIT("m/s²")
                    with builder.CHILD(key="polylineMaxDecele", name="[Polyline] Max Deceleration",
                                       desc="Maximum deceleration"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.2)
                        builder.UNIT("m/s²")
                    with builder.CHILD(key="polylineDeceleDist", name="[Polyline] Deceleration Distance",
                                       desc="Distance to start deceleration before target"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylineMaxAngle", name="[Polyline] Max Angle",
                                       desc="Maximum angle between two lines"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.3)
                        builder.UNIT("rad")
                    with builder.CHILD(key="polylinePathDistAccuracy", name="[Polyline] Path Dist Accuracy",
                                       desc="Position accuracy for path following"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.01)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylinePathAngleAccuracy", name="[Polyline] Path Angle Accuracy",
                                       desc="Angle accuracy for path following"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05)
                        builder.UNIT("rad")

            # ============================================
            # PGV二次调整配置组（不变）
            # ============================================
            with builder.GROUP(key="pgvConfig", name="PGV Secondary Adjust Config",
                               desc="PGV secondary adjustment parameters (site-specific, rarely changed)"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="codeAdjustType", name="Code Adjust Type",
                                       desc="PGV adjustment working mode"):
                        builder.TYPE(ParamType.COMBO_BOX)
                        builder.DEFAULTVALUE("singleCode")
                        with builder.CHILDREN():
                            with builder.CHILD(key="singleCode", name="Single Code",
                                               desc="Adjust to a single QR code"):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="scanDevice", name="Scan Device",
                                                       desc="Select the PGV code scanner device"):
                                        builder.TYPE(ParamType.BIND_TYPE)
                                        builder.BINDTYPE(BindType.Device.CODE_SCANNER)
                                    with builder.CHILD(key="codeNumber", name="Code Number",
                                                       desc="Target QR code number (pure digits, optional)"):
                                        builder.TYPE(ParamType.STRING)
                                        builder.REQUIRED(False)
                                        builder.DEFAULTVALUE("")
                                    with builder.CHILD(key="positionAdjustType", name="Position Adjust Type",
                                                       desc="Position adjustment strategy"):
                                        builder.TYPE(ParamType.COMBO_BOX)
                                        builder.DEFAULTVALUE("frontAndBack")
                                        with builder.CHILDREN():
                                            with builder.CHILD(key="frontAndBack", name="Front And Back",
                                                               desc="Forward/backward adjustment along X axis"):
                                                builder.TYPE(ParamType.ARRAY)
                                            with builder.CHILD(key="multiLine", name="Multi Line",
                                                               desc="Back-and-forth sweep adjustment in a region"):
                                                builder.TYPE(ParamType.ARRAY)
                                                with builder.CHILDREN():
                                                    with builder.CHILD(key="adjustRegion",
                                                                       name="Adjust Region",
                                                                       desc="Rectangular adjustment region"):
                                                        builder.TYPE(ParamType.BIND_TYPE)
                                                        builder.BINDTYPE(
                                                            BindItem(BindType.Shape.RECTANGLE, no_rotate=True))
                                                    with builder.CHILD(key="lineAngleThreshold",
                                                                       name="Line Angle Threshold",
                                                                       desc="Max rotation angle during sweep (deg)"):
                                                        builder.TYPE(ParamType.FLOAT)
                                                        builder.DEFAULTVALUE(10.0)
                                                        builder.UNIT("deg")
                                                        builder.SINGLESTEP(1.0)
                                    with builder.CHILD(key="angleAdjustType", name="Angle Adjust Type",
                                                       desc="Robot orientation relative to QR code"):
                                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                                        builder.DEFAULTVALUE("parallelToCode")
                                        with builder.CHILDREN():
                                            with builder.CHILD("parallelToCode", "Parallel To Code",
                                                               "Robot parallel to code → pgvAdjust180"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("verticalToCode", "Vertical To Code",
                                                               "Robot perpendicular to code → pgvAdjust90"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("verticalOrParallelToCode",
                                                               "Vertical Or Parallel To Code",
                                                               "90° or 0° whichever is smaller → pgvAdjust90"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("ignoreAngle", "Ignore Angle",
                                                               "XY adjust, ignore angle → pgvAdjustXY"):
                                                builder.TYPE(ParamType.STRING)
                            with builder.CHILD(key="codeNumber", name="Code Number Strip",
                                               desc="Adjust along a QR code strip → auto sets pgvCodeStrip=True"):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="scanDevice", name="Scan Device",
                                                       desc="Select the PGV code scanner device"):
                                        builder.TYPE(ParamType.BIND_TYPE)
                                        builder.BINDTYPE(BindType.Device.CODE_SCANNER)
                                    with builder.CHILD(key="angleAdjustType", name="Angle Adjust Type",
                                                       desc="Robot orientation relative to code strip"):
                                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                                        builder.DEFAULTVALUE("parallelToCode")
                                        with builder.CHILDREN():
                                            with builder.CHILD("parallelToCode", "Parallel To Code",
                                                               "pgvXAngleAdjust + pgvAdjust180"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("verticalToCode", "Vertical To Code",
                                                               "pgvXAngleAdjust + pgvAdjust90"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("verticalOrParallelToCode",
                                                               "Vertical Or Parallel To Code",
                                                               "pgvXAngleAdjust + pgvAdjust90"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("ignoreAngle", "Ignore Angle",
                                                               "pgvXAdjust only"):
                                                builder.TYPE(ParamType.STRING)
                    with builder.CHILD(key="pgvSpin", name="Spin Hold During Adjust",
                                       desc="Hold fork direction during PGV secondary adjustment (spin vehicles)"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="pgvReachDist", name="Reach Distance Accuracy",
                                       desc="PGV secondary adjustment distance accuracy"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.02)
                        builder.UNIT("m")
                        builder.SINGLESTEP(0.001)
                    with builder.CHILD(key="pgvReachAngle", name="Reach Angle Accuracy",
                                       desc="PGV secondary adjustment angle accuracy"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("deg")
                        builder.SINGLESTEP(0.1)

        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        cls.config = param_loader.loadConfig()

        # 通用配置 - 先加载 debug_mode
        cls.debug_mode = cls.config.get("debugMode", False)
        cls.auto_calib_enable = cls.config.get("autoCalibEnable", False)
        # 电机配置
        cls.jack_motor_speed = cls.config.get("jackMotorSpeed")
        cls.jack_min_height = cls.config.get("jackMinHeight")
        cls.jack_max_height = cls.config.get("jackMaxHeight")

        # DI配置（从设备绑定读取）
        cls.jack_up_di = RobotParam.getDevice(f"{cls.jack_motor_name}", f"func.{cls.motor_func}.upLimitDI")
        cls.jack_zero_di = RobotParam.getDevice(f"{cls.jack_motor_name}", f"resetMode.{cls.reset_by_speed}.zeroDI")

        # Bezier导航配置
        cls.bezier_back_dist = cls.config.get("bezierBackDist", 0.0)
        cls.bezier_adjust_dist = cls.config.get("bezierAdjustDist", 2.0)
        cls.bezier_min_ahead_dist = cls.config.get("bezierMinAheadDist", 0)
        cls.bezier_is_backwards = cls.config.get("bezierIsBackwards", False)
        cls.bezier_is_hold_dir = cls.config.get("bezierIsHoldDir", False)
        cls.bezier_max_speed = cls.config.get("bezierMaxSpeed", 0.5)
        cls.bezier_max_accele = cls.config.get("bezierMaxAccele", 0.3)
        cls.bezier_max_decele = cls.config.get("bezierMaxDecele", 0.2)
        cls.bezier_decele_dist = cls.config.get("bezierDeceleDist", 1)
        cls.bezier_curvature_limit = cls.config.get("bezierCurvatureLimit", 1.3)
        cls.bezier_path_dist_accuracy = cls.config.get("bezierPathDistAccuracy", 0.01)
        cls.bezier_path_angle_accuracy = cls.config.get("bezierPathAngleAccuracy", 0.05)

        # Polyline导航配置
        cls.polyline_back_dist = cls.config.get("polylineBackDist", 0.55)
        cls.polyline_ahead_dist = cls.config.get("polylineAheadDist", 2.0)
        cls.polyline_min_ahead_dist = cls.config.get("polylineMinAheadDist", 0.0)
        cls.polyline_is_backwards = cls.config.get("polylineIsBackwards", False)
        cls.polyline_is_hold_dir = cls.config.get("polylineIsHoldDir", False)
        cls.polyline_max_speed = cls.config.get("polylineMaxSpeed", 0.5)
        cls.polyline_max_accele = cls.config.get("polylineMaxAccele", 0.3)
        cls.polyline_max_decele = cls.config.get("polylineMaxDecele", 0.2)
        cls.polyline_decele_dist = cls.config.get("polylineDeceleDist", 1.0)
        cls.polyline_max_angle = cls.config.get("polylineMaxAngle", 1.3)
        cls.polyline_path_dist_accuracy = cls.config.get("polylinePathDistAccuracy", 0.01)
        cls.polyline_path_angle_accuracy = cls.config.get("polylinePathAngleAccuracy", 0.05)

        # PGV配置（policy 结构）
        cls.pgv_code_adjust_type = cls.config.get("codeAdjustType", "singleCode")

        # 读取 singleCode 子参数
        cls.pgv_scan_device = cls.config.get("scanDevice", "")
        cls.pgv_code_number = cls.config.get("codeNumber", "")
        cls.pgv_angle_adjust_type = cls.config.get("angleAdjustType", "parallelToCode")
        cls.pgv_position_adjust_type = cls.config.get("positionAdjustType", "frontAndBack")
        cls.pgv_line_angle_threshold = cls.config.get("lineAngleThreshold", 10.0)
        cls.pgv_adjust_region = cls.config.get("adjustRegion", "")

        # 通用精度参数
        cls.pgv_spin = cls.config.get("pgvSpin", True)
        cls.pgv_reach_dist = cls.config.get("pgvReachDist", 0.02)
        cls.pgv_reach_angle = cls.config.get("pgvReachAngle", 1.0)

        debug_trace(f"Updated config: debug_mode={cls.debug_mode}")


# 创建全局配置管理器实例
config_params = ConfigParams()

# ============================================================================
# 调试任务列表（需要开启 debugMode 才能执行）
# ============================================================================
DEBUG_ONLY_TASKS = [
    "calib",  # 强制标零（外部指令触发）
    "jackHeight",  # 指定高度顶升
    "goBezier",  # 贝塞尔导航
    "PGVSecondaryAdjust",  # PGV二次调整
    "pressIoButton", # I/O控制顶升
    "getLM",  # 获取地标位置
    "laserAreaDeduction",  # 激光区域扣除
    "createOrDeleteDeductedArea",  # 创建/删除扣除区域
    "jackBezierReturn",  # 贝塞尔取货并返回
    "goPolyline",  # 折线导航
    "goDist",  # 直行指定距离
    "goPath",  # 直行到目标位置
    "recShelf",  # 识别货架
    "getRecfile",  # 获取识别文件
    "recTargetObs",  # 识别目标障碍
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
                f"[ERROR] Task '{operation}' is a debug-only task. Please enable 'debugMode' in script config first.")
            return False
    return True


def script_config_callback():
    debug_trace("Reloading script config parameters")
    config_params.reload_config()


def create_start_height(builder: ParamBuilder):
    with builder.CHILD(key="startHeight", name="Start Height",
                       desc="The start height for operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.MIN_VALUE(config_params.jack_min_height)
        builder.MAX_VALUE(config_params.jack_max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(config_params.jack_min_height)


def create_end_height(builder: ParamBuilder):
    """创建顶可被引用参数"""
    with builder.CHILD(key="endHeight", name="End Height",
                       desc="The end height for operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.06)


def create_recfile(builder: ParamBuilder):
    with builder.CHILD(key="insertShelfDir", name="Insert Shelf Direction", desc="direction to go under the shelf"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE("A")


def create_jack_load(builder: ParamBuilder):
    create_start_height(builder)
    create_end_height(builder)

    with builder.CHILD(key="recognize", name="recognize",
                       desc="Enable recognition"):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE("off")
        with builder.CHILDREN():
            # OFF 选项，不需要填识别文件
            with builder.CHILD(key="off", name="OFF",
                               desc="Load Without Recognition"):
                builder.TYPE(ParamType.ARRAY)
            # ON 也就是勾选需要识别后才会需要填写识别文件
            with builder.CHILD(key="on", name="ON",
                               desc="Load With Recognition"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    create_recfile(builder)

    with builder.CHILD(key="recFile", name="RecFile", desc="file for recognizing"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE("default.srec")

    with builder.CHILD(key="howGoSite", name="howGoSite", desc="choose the way to the landmark"):
        builder.TYPE(ParamType.COMBO_BOX)
        builder.DEFAULTVALUE("bezier")
        builder.REQUIRED(False)
        with builder.CHILDREN():
            with builder.CHILD(key="bezier", name="bezier", desc="bezier"):
                builder.TYPE(ParamType.ARRAY)

            with builder.CHILD(key="straight", name="straight", desc="straight"):
                builder.TYPE(ParamType.ARRAY)

            with builder.CHILD(key="polyline", name="polyline", desc="polyline"):
                builder.TYPE(ParamType.ARRAY)

    with builder.CHILD(key="isSecondaryAdjust", name="isSecondaryAdjust",
                       desc="Enable secondary adjust"):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE("off")
        with builder.CHILDREN():
            # OFF 选项，不需要填二次调整内容
            with builder.CHILD(key="off", name="OFF",
                               desc="Load Without secondary_adjust"):
                builder.TYPE(ParamType.ARRAY)
            # ON 也就是勾选需要二次调整后才会出现二次调整相关内容
            with builder.CHILD(key="on", name="ON",
                               desc="Load With secondary_adjust"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    # codeAdjustType 顶层模式（与 pgvConfig 保持一致，此处可按任务覆盖）
                    with builder.CHILD(key="codeAdjustType", name="Code Adjust Type",
                                       desc="Override PGV adjustment mode for this task"):
                        builder.TYPE(ParamType.COMBO_BOX)
                        builder.DEFAULTVALUE("singleCode")
                        with builder.CHILDREN():
                            # singleCode 模式
                            with builder.CHILD(key="singleCode", name="Single Code",
                                               desc="Adjust to a single QR code"):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="scanDevice", name="Scan Device",
                                                       desc="Select the PGV code scanner device"):
                                        builder.TYPE(ParamType.BIND_TYPE)
                                        builder.BINDTYPE(BindType.Device.CODE_SCANNER)

                                    with builder.CHILD(key="codeNumber", name="Code Number",
                                                       desc="Target QR code number (optional, pure digits)"):
                                        builder.TYPE(ParamType.STRING)
                                        builder.REQUIRED(False)
                                        builder.DEFAULTVALUE("")

                                    with builder.CHILD(key="positionAdjustType", name="Position Adjust Type",
                                                       desc="Position adjustment strategy"):
                                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                                        builder.DEFAULTVALUE("frontAndBack")
                                        with builder.CHILDREN():
                                            with builder.CHILD(key="frontAndBack", name="Front And Back",
                                                               desc="Forward/backward adjustment along X axis"):
                                                builder.TYPE(ParamType.ARRAY)
                                            with builder.CHILD(key="multiLine", name="Multi Line",
                                                               desc="Back-and-forth sweep adjustment in a region"):
                                                builder.TYPE(ParamType.ARRAY)
                                                with builder.CHILDREN():
                                                    with builder.CHILD(key="adjustRegion",
                                                                       name="Adjust Region",
                                                                       desc="Rectangular adjustment region"):
                                                        builder.TYPE(ParamType.BIND_TYPE)
                                                        builder.BINDTYPE(
                                                            BindItem(BindType.Shape.RECTANGLE, no_rotate=True))
                                                    with builder.CHILD(key="lineAngleThreshold",
                                                                       name="Line Angle Threshold",
                                                                       desc="Max rotation angle during sweep (deg)"):
                                                        builder.TYPE(ParamType.FLOAT)
                                                        builder.DEFAULTVALUE(10.0)
                                                        builder.UNIT("deg")
                                                        builder.SINGLESTEP(1.0)

                                    with builder.CHILD(key="angleAdjustType", name="Angle Adjust Type",
                                                       desc="Robot orientation relative to QR code"):
                                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                                        builder.DEFAULTVALUE("parallelToCode")
                                        with builder.CHILDREN():
                                            with builder.CHILD("parallelToCode", "Parallel To Code",
                                                               "pgvAdjust180"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("verticalToCode", "Vertical To Code",
                                                               "pgvAdjust90"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("verticalOrParallelToCode",
                                                               "Vertical Or Parallel",
                                                               "pgvAdjust90"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("ignoreAngle", "Ignore Angle",
                                                               "pgvAdjustXY"):
                                                builder.TYPE(ParamType.STRING)

                            # codeNumber 码带模式
                            with builder.CHILD(key="codeNumber", name="Code Number Strip",
                                               desc="Code strip adjustment → pgvCodeStrip=True"):
                                builder.TYPE(ParamType.ARRAY)
                                with builder.CHILDREN():
                                    with builder.CHILD(key="scanDevice", name="Scan Device",
                                                       desc="Select the PGV code scanner device"):
                                        builder.TYPE(ParamType.BIND_TYPE)
                                        builder.BINDTYPE(BindType.Device.CODE_SCANNER)

                                    with builder.CHILD(key="angleAdjustType", name="Angle Adjust Type",
                                                       desc="Robot orientation relative to code strip"):
                                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                                        builder.DEFAULTVALUE("parallelToCode")
                                        with builder.CHILDREN():
                                            with builder.CHILD("parallelToCode", "Parallel To Code",
                                                               "pgvXAngleAdjust + pgvAdjust180"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("verticalToCode", "Vertical To Code",
                                                               "pgvXAngleAdjust + pgvAdjust90"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("verticalOrParallelToCode",
                                                               "Vertical Or Parallel",
                                                               "pgvXAngleAdjust + pgvAdjust90"):
                                                builder.TYPE(ParamType.STRING)
                                            with builder.CHILD("ignoreAngle", "Ignore Angle",
                                                               "pgvXAdjust only"):
                                                builder.TYPE(ParamType.STRING)


class InputParams:
    """
    任务输入参数

    参数分类原则：
    1. 输入参数：每次任务可能不同的参数（如targetName, recFile, recognize）
    2. 配置参数：现场实施后基本不变的参数（已移到ConfigParams）
    3. 调试任务：开启debugMode后才显示的低频任务

    任务分类：
    - 常用任务（始终显示）：jackLoad, jackUnload, jackUp, jackDown
    - 调试任务（debugMode=true时显示）：jackHeight, goBezier等
    """
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        # 操作组合参数
        with builder.GROUP(key="operation", name="Task Operation", desc="Choose an operation for task"):
            builder.TYPE(ParamType.COMBO_BOX)

            with builder.CHILDREN():
                # ============================================
                # 常用任务（始终显示）
                # ============================================

                # 取货
                with builder.CHILD(key="jackLoad", name="Jack Load", desc="recognize and load the shelf"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_jack_load(builder)

                # 放货
                with builder.CHILD(key="jackUnload", name="Jack Unload", desc="recognize and unload the shelf"):
                    builder.TYPE(ParamType.ARRAY)

                # ============================================
                # 调试/低频任务（需要开启debugMode才显示）
                # ===========================================
                if config_params.debug_mode:
                    # [DEBUG] 强制标零（外部指令触发，需开启 debugMode）
                    with builder.CHILD(key="calib", name="[Debug] Calib",
                                       desc="Force recalibrate jack motor zero position (debug only)"):
                        builder.TYPE(ParamType.ARRAY)
                    # [DEBUG] 指定高度顶升
                    with builder.CHILD(key="jackHeight", name="[Debug] Jack Height",
                                       desc="lift to specified height (debug only)"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_end_height(builder)
                            with builder.CHILD(key="recFile", name="RecFile", desc="file for recognizing"):
                                builder.TYPE(ParamType.STRING)
                                builder.REQUIRED(False)
                                builder.DEFAULTVALUE("default.srec")

                    # [DEBUG] 贝塞尔导航
                    with builder.CHILD(key="goBezier", name="[Debug] goBezier",
                                       desc="go bezier line to target (debug only)"):
                        builder.TYPE(ParamType.ARRAY)
                    with builder.CHILD(key="PGVSecondaryAdjust", name="[Debug] PGV Secondary Adjust",
                                       desc="Perform PGV secondary adjustment"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            with builder.CHILD(key="codeAdjustType", name="Code Adjust Type",
                                               desc="PGV adjustment working mode"):
                                builder.TYPE(ParamType.COMBO_BOX)
                                builder.DEFAULTVALUE("singleCode")
                                with builder.CHILDREN():
                                    with builder.CHILD(key="singleCode", name="Single Code",
                                                       desc="Adjust to a single QR code"):
                                        builder.TYPE(ParamType.ARRAY)
                                        with builder.CHILDREN():
                                            with builder.CHILD(key="scanDevice", name="Scan Device",
                                                               desc="Select the PGV code scanner device"):
                                                builder.TYPE(ParamType.BIND_TYPE)
                                                builder.BINDTYPE(BindType.Device.CODE_SCANNER)

                                            with builder.CHILD(key="codeNumber", name="Code Number",
                                                               desc="Target QR code number (optional)"):
                                                builder.TYPE(ParamType.STRING)
                                                builder.REQUIRED(False)
                                                builder.DEFAULTVALUE("")

                                            with builder.CHILD(key="positionAdjustType",
                                                               name="Position Adjust Type",
                                                               desc="Position adjustment strategy"):
                                                builder.TYPE(ParamType.STRING_COMBO_LIST)
                                                builder.DEFAULTVALUE(config_params.pgv_position_adjust_type)
                                                with builder.CHILDREN():
                                                    with builder.CHILD(key="frontAndBack",
                                                                       name="Front And Back",
                                                                       desc="Forward/backward adjustment along X axis"):
                                                        builder.TYPE(ParamType.ARRAY)
                                                    with builder.CHILD(key="multiLine",
                                                                       name="Multi Line",
                                                                       desc="Back-and-forth sweep adjustment in a region"):
                                                        builder.TYPE(ParamType.ARRAY)
                                                        with builder.CHILDREN():
                                                            with builder.CHILD(key="adjustRegion",
                                                                               name="Adjust Region",
                                                                               desc="Rectangular adjustment region"):
                                                                builder.TYPE(ParamType.BIND_TYPE)
                                                                builder.BINDTYPE(
                                                                    BindItem(BindType.Shape.RECTANGLE,
                                                                             no_rotate=True))
                                                            with builder.CHILD(key="lineAngleThreshold",
                                                                               name="Line Angle Threshold",
                                                                               desc="Max rotation during sweep (deg)"):
                                                                builder.TYPE(ParamType.FLOAT)
                                                                builder.DEFAULTVALUE(
                                                                    config_params.pgv_line_angle_threshold)
                                                                builder.UNIT("deg")
                                                                builder.SINGLESTEP(1.0)

                                            with builder.CHILD(key="angleAdjustType",
                                                               name="Angle Adjust Type",
                                                               desc="Robot orientation vs QR code"):
                                                builder.TYPE(ParamType.STRING_COMBO_LIST)
                                                builder.DEFAULTVALUE(config_params.pgv_angle_adjust_type)
                                                with builder.CHILDREN():
                                                    with builder.CHILD("parallelToCode", "Parallel To Code",
                                                                       "pgvAdjust180"):
                                                        builder.TYPE(ParamType.STRING)
                                                    with builder.CHILD("verticalToCode", "Vertical To Code",
                                                                       "pgvAdjust90"):
                                                        builder.TYPE(ParamType.STRING)
                                                    with builder.CHILD("verticalOrParallelToCode",
                                                                       "Vertical Or Parallel",
                                                                       "pgvAdjust90"):
                                                        builder.TYPE(ParamType.STRING)
                                                    with builder.CHILD("ignoreAngle", "Ignore Angle",
                                                                       "pgvAdjustXY"):
                                                        builder.TYPE(ParamType.STRING)

                                    with builder.CHILD(key="codeNumber", name="Code Number Strip",
                                                       desc="Code strip mode → pgvCodeStrip=True"):
                                        builder.TYPE(ParamType.ARRAY)
                                        with builder.CHILDREN():
                                            with builder.CHILD(key="scanDevice", name="Scan Device",
                                                               desc="Select the PGV code scanner device"):
                                                builder.TYPE(ParamType.BIND_TYPE)
                                                builder.BINDTYPE(BindType.Device.CODE_SCANNER)

                                            with builder.CHILD(key="angleAdjustType",
                                                               name="Angle Adjust Type",
                                                               desc="Robot orientation vs code strip"):
                                                builder.TYPE(ParamType.STRING_COMBO_LIST)
                                                builder.DEFAULTVALUE(config_params.pgv_angle_adjust_type)
                                                with builder.CHILDREN():
                                                    with builder.CHILD("parallelToCode", "Parallel",
                                                                       "pgvXAngleAdjust + pgvAdjust180"):
                                                        builder.TYPE(ParamType.STRING)
                                                    with builder.CHILD("verticalToCode", "Vertical",
                                                                       "pgvXAngleAdjust + pgvAdjust90"):
                                                        builder.TYPE(ParamType.STRING)
                                                    with builder.CHILD("verticalOrParallelToCode",
                                                                       "Vertical Or Parallel",
                                                                       "pgvXAngleAdjust + pgvAdjust90"):
                                                        builder.TYPE(ParamType.STRING)
                                                    with builder.CHILD("ignoreAngle", "Ignore Angle",
                                                                       "pgvXAdjust only"):
                                                        builder.TYPE(ParamType.STRING)

                            with builder.CHILD(key="pgvSpin", name="Spin Hold During Adjust",
                                               desc="Hold fork direction during PGV adjustment"):
                                builder.TYPE(ParamType.BOOL)
                                builder.DEFAULTVALUE(config_params.pgv_spin)
                            with builder.CHILD(key="pgvReachDist", name="Reach Distance Accuracy",
                                               desc="PGV secondary adjustment distance accuracy"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(config_params.pgv_reach_dist)
                                builder.UNIT("m")
                                builder.SINGLESTEP(0.001)
                            with builder.CHILD(key="pgvReachAngle", name="Reach Angle Accuracy",
                                               desc="PGV secondary adjustment angle accuracy"):
                                builder.TYPE(ParamType.FLOAT)
                                builder.DEFAULTVALUE(config_params.pgv_reach_angle)
                                builder.UNIT("deg")
                                builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="getLM", name="[Debug] getLM",
                                       desc="get the position of landmark"):
                        builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="pressIoButton", name="[Debug] pressIoButton",
                                       desc="use the io button to control"):
                        builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="laserAreaDeduction", name="[Debug] laserAreaDeduction",
                                       desc="laser area deduction"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILD(key="coordinate", name="coordinate", desc="Spin coordinate"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE("robot")
                            builder.REQUIRED(True)
                            with builder.CHILDREN():
                                with builder.CHILD("robot", "robot", "robot"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("world", "world", "world"):
                                    builder.TYPE(ParamType.STRING)

                    with builder.CHILD(key="createOrDeleteDeductedArea", name="[Debug] create Or Delete Deducted Area",
                                       desc="create_or_delete_deducted_area"):
                        builder.TYPE(ParamType.COMBO_BOX)
                        # builder.DEFAULTVALUE("create")
                        builder.REQUIRED(False)
                        with builder.CHILDREN():
                            with builder.CHILD(key="create", name="create", desc="create"):
                                builder.TYPE(ParamType.ARRAY)

                                with builder.CHILD(key="recFile", name="recfile", desc="file for recognize"):
                                    builder.TYPE(ParamType.STRING)
                                    builder.REQUIRED(False)
                                    builder.DEFAULTVALUE("default.srec")

                            with builder.CHILD(key="delete", name="delete", desc="delete"):
                                builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="jackBezierReturn", name="[Debug] jackBezierReturn",
                                       desc="recognize and go bezier to get the shelf and return"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILDREN():
                            create_start_height(builder)
                            create_end_height(builder)
                            create_recfile(builder)

                    with builder.CHILD(key="goPolyline", name="[Debug] goPolyline",
                                       desc="go polyline line to target position"):
                        builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="goDist", name="[Debug] goDist", desc="go straight distance"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILD(key="goPathX", name="goPath_x",
                                           desc="The dist of the target point to which robot will go in a straight line"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("m")
                            builder.DEFAULTVALUE(0)

                    with builder.CHILD(key="goPath", name="[Debug] goPath", desc="go straight to target position"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILD(key="goPathX", name="goPath_x",
                                           desc="The coordinate x of the target point to which robot will go in a straight line"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("m")
                            builder.DEFAULTVALUE(0)
                        with builder.CHILD(key="goPathY", name="goPath_y",
                                           desc="The coordinate y of the target point to which robot will go in a straight line"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("m")
                            builder.DEFAULTVALUE(0)
                        with builder.CHILD(key="goPathTheta", name="goPath_theta",
                                           desc="The theta of the target point to which robot will go in a straight line"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("rad")
                            builder.DEFAULTVALUE(0)
                        with builder.CHILD(key="coordinate", name="coordinate", desc="Spin coordinate"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE("robot")

                            with builder.CHILDREN():
                                with builder.CHILD("robot", "robot", "robot"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("world", "world", "world"):
                                    builder.TYPE(ParamType.STRING)

                    with builder.CHILD(key="recShelf", name="[Debug] recShelf", desc="recognize the shelf"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILD(key="recFile", name="recfile",
                                           desc="the file for recognize"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE("default.srec")

                    with builder.CHILD(key="getRecfile", name="[Debug] getRecfile", desc="get Recfile"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILD(key="recFile", name="recfile",
                                           desc="the file for recognize"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE("default.srec")

                    with builder.CHILD(key="recTargetObs", name="[Debug] recTargetObs", desc="recTargetObs"):
                        builder.TYPE(ParamType.ARRAY)

    builder.save_to_file()


class Jack(ModuleBase):
    def __init__(self):
        super().__init__()

        # ============================================
        # Error53301: 检查顶升电机配置
        # ============================================
        if not config_params.jack_motor_name:
            Navigation.setDeviceError("53301", "模型文件顶升设备配置有误，找不到顶升电机")
        # 脚本任务管理
        # set_info数据打印
        self._last_logged_action_id = None
        self.info_count = 0
        self.jack_height = None
        self.jack_emc = None
        self.jack_isFull = None
        self.jack_speed = None
        self.jack_motors = None
        self.count = 0
        # 脚本运行相关变量
        self.task_args = None
        self.init_args = False
        self.action_id = 0
        self.action_list = []
        self.operation_init = False
        # 识别文件
        self.laser_area_deduct_info = None
        # 定义动作相关的变量
        self.opt = None
        self.shelf_back_distance = None  # 识别文件的参数 # {'enableBackDistance': True, 'backDistance': 0.55}
        self.back_dist = None
        self.ap_world_pos = None  # 定义ap点在世界坐标系的位置
        self.ap_robot_pos = None  # 定义ap点在机器人坐标系的位置
        self.ap_id = None
        self.coordinate = None  # 定义坐标系
        self.action_parameters = None  # vda
        self.recfile = None
        self.how_go_site = None

        # 货架识别
        self.rec_result = []
        # 二维码识别
        self.code_info = dict()

        # 数据打印
        self.report_info = {}

        # robotParam
        self.lift_motor = None
        debug_trace(
            f"Jack init: motor={config_params.jack_motor_name}, height=[{config_params.jack_min_height}~{config_params.jack_max_height}]m, DI=[up:{config_params.jack_up_di}, zero:{config_params.jack_zero_di}]")

        self.status = ScriptStatus.NONE

        self.cur_action_list = []

        # 初始化容器（单容器，id=0）
        Container.initContainer(0)

        # ========== 边走边动相关状态 ==========
        self.pre_action_mode = False  # 是否处于预动作模式（边走边动）
        self.pre_action_completed = False  # 预动作是否完成
        self.pre_action_step = [False] * 5  # 预动作步骤
        self.pre_action_args = {}  # 预动作参数（从finalBinTask解析）
        self.full_action_args = {}  # 完整动作参数（到达终点后执行）
        self.at_final_loc = False  # 是否到达终点
        self.final_bin_task = None  # finalBinTask 参数
        self.final_loc = None  # finalLoc 参数
        self.result = None  # 边走边动结果参数
        self.jack_calib_step = [False, False]  # [0]=motorCalib指令已下发  [1]=标零已确认完成

    def _get_motor_calib_state(self, motor_name):
        """从 Odometer 读取指定电机的 calib 字段（2=标零完成）"""
        try:
            for m in Odometer.getData().get("motorInfo", []):
                if m.get("key") == motor_name:
                    return m.get("calib", None)
        except Exception as e:
            Trace.log(f"[CALIB] 读取电机 {motor_name} calib 状态失败: {e}")
        return None

    def _run_calib_steps(self, label: str) -> bool:
        """
        顶升电机标零状态机（内部复用）。
        返回 True 表示全部标零完成，False 表示仍在进行中。
        """
        # ---- 顶升电机标零 ----
        if not self.jack_calib_step[0]:
            if not Motor.isMotorStop(config_params.jack_motor_name):
                debug_trace(f"[CALIB] {label}：等待顶升电机停止...")
                return False
            Motor.motorCalib(config_params.jack_motor_name)
            self.jack_calib_step[0] = True
            Trace.log(f"[CALIB] {label}：顶升电机已静止，motorCalib 指令已下发")
            return False

        if not self.jack_calib_step[1]:
            if self._get_motor_calib_state(config_params.jack_motor_name) == 2:
                self.jack_calib_step[1] = True
                jack_calib_manager.set_calib_done(True)
                Trace.log(f"[CALIB] {label}：顶升电机标零完成")
                return True
            return False

        return False

    def run_startup_calib(self):
        """脚本启动自动标零（由 main 循环在 DB=False 时周期调用）"""
        self._run_calib_steps("自动标零")

    def do_force_calib(self):
        """外部 'calib' 指令触发的强制标零"""
        if not self.operation_init:
            self.operation_init = True
            jack_calib_manager.set_calib_done(False)
            self.jack_calib_step = [False, False]
            Trace.log("[CALIB] 强制标零：jackCalibDone 已置 False")
        if self._run_calib_steps("强制标零"):
            self.status = ScriptStatus.FINISHED

    def bindContainer(self, container_id: str, goods_name: str, desc: str, insert_dir: str = "D") -> bool:
        """
        重写 bindContainer：绑定容器并设置货物多边形形状。
        """
        # 1. 绑定容器
        Container.bindContainer(container_id, goods_name, desc)

        # 2. 从识别配置中读取货物多边形形状
        recognition_goodsParameter_path = f"recognitionObject.shelf.goodsParameter"
        goods_shape = RobotParam.getConfig(
            "recognition",
            f"{recognition_goodsParameter_path}.goodsShape",
            self.recfile or "default.srec"
        )
        if not goods_shape:
            Trace.log(f"[bindContainer] 未找到货物形状配置，recfile={self.recfile}")
            return False

        shapes = json.loads(goods_shape)
        shape = shapes[0]["points"]

        # 3. 根据插入方向旋转货物模型
        # A: 0°不旋转  B: 顺时针90°  C: 180°  D: 逆时针90°（原默认）
        def _rotate_pt(pt, dir_):
            if dir_ == "A":  # 0°: (x, y) -> (x, y)
                if isinstance(pt, dict):  return {"x": pt["y"], "y":-pt["x"] }
                return [pt[0], pt[1]]
            elif dir_ == "B":  # 顺时针90°: (x, y) -> (y, -x)
                if isinstance(pt, dict):  return {"x":pt["x"] , "y": pt["y"]}
                return [pt[1], -pt[0]]
            elif dir_ == "C":  # 180°: (x, y) -> (-x, -y)
                if isinstance(pt, dict):  return {"x": -pt["y"], "y": pt["x"] }
                return [-pt[0], -pt[1]]
            else:  # D: 逆时针90°: (x, y) -> (-y, x)
                if isinstance(pt, dict):  return {"x":-pt["x"] , "y":-pt["y"]}
                return [-pt[1], pt[0]]

        shape = [_rotate_pt(pt, insert_dir) if isinstance(pt, (dict, list, tuple)) else pt for pt in shape]

        Navigation.setGoodsPolyShape(shape, goods_name)
        Trace.log(f"[bindContainer] 绑定成功(方向={insert_dir}): container={container_id}, goods={goods_name}, "
                  f"shape points={len(shape)}, recfile={self.recfile}")
        return True

    def _init_args(self, args):
        self.task_args = args
        # 获取任务参数
        self.opt = self.task_args.get("operation", None)
        self.ap_id = None  # targetName 从 Navigation.moveTask() 获取
        # 顶升高度相关
        self.start_height = self.task_args.get("startHeight", 0)
        self.end_height = self.task_args.get("endHeight", 0.05)
        # 识别相关
        self.is_recognize = self.task_args.get("recognize", False)
        self.recfile = self.task_args.get("recFile", None)
        self.insert_shelf_dir = self.task_args.get("insertShelfDir", "A")
        # 到点动作：scriptStage==2 时跳过旋转/识别/导航，直接二次调整+顶升
        self.at_site = self._get_script_stage() == 2
        # jackLoad/jackUnload
        self.how_go_site = self.task_args.get("howGoSite", "bezier")

        # ============================================
        # 导航参数：从脚本配置读取（现场实施后基本不变）
        # ============================================
        # Bezier导航参数
        self.back_dist = config_params.bezier_back_dist
        self.adjust_dist_for_curvature_limit = int(config_params.bezier_adjust_dist)  # API要求int类型
        self.min_ahead_dist = config_params.bezier_min_ahead_dist
        self.is_backwards = config_params.bezier_is_backwards
        self.is_hold_dir = config_params.bezier_is_hold_dir
        self.max_speed = config_params.bezier_max_speed
        self.max_rot = None  # 暂不使用
        self.max_accele = config_params.bezier_max_accele
        self.max_decele = config_params.bezier_max_decele
        self.decele_dist = config_params.bezier_decele_dist
        self.curvature_limit = config_params.bezier_curvature_limit
        self.path_dist_accuracy = config_params.bezier_path_dist_accuracy
        self.path_angle_accuracy = config_params.bezier_path_angle_accuracy

        # 如果选择的是polyline，则使用polyline配置
        if self.how_go_site == "polyline":
            self.back_dist = config_params.polyline_back_dist
            self.adjust_dist_for_curvature_limit = int(config_params.polyline_ahead_dist)  # API要求int类型
            self.min_ahead_dist = config_params.polyline_min_ahead_dist
            self.is_backwards = config_params.polyline_is_backwards
            self.is_hold_dir = config_params.polyline_is_hold_dir
            self.max_speed = config_params.polyline_max_speed
            self.max_accele = config_params.polyline_max_accele
            self.max_decele = config_params.polyline_max_decele
            self.decele_dist = config_params.polyline_decele_dist
            self.curvature_limit = config_params.polyline_max_angle
            self.path_dist_accuracy = config_params.polyline_path_dist_accuracy
            self.path_angle_accuracy = config_params.polyline_path_angle_accuracy

        # goPath相关
        self.goPath_x = self.task_args.get("goPathX", None)
        self.goPath_y = self.task_args.get("goPathY", None)
        self.goPath_theta = self.task_args.get("goPathTheta", None)

        # ============================================
        # PGV二次调整参数：从任务参数或脚本配置读取
        # ============================================
        self.is_secondary_adjust = self.task_args.get("isSecondaryAdjust", False)

        # 顶层 codeAdjustType（任务参数可覆盖配置参数）
        self.pgv_code_adjust_type = self.task_args.get(
            "codeAdjustType", config_params.pgv_code_adjust_type)

        # scanDevice、angleAdjustType、positionAdjustType 从任务参数或配置读取
        self.pgv_scan_device = self.task_args.get(
            "scanDevice", config_params.pgv_scan_device)
        self.pgv_angle_adjust_type = self.task_args.get(
            "angleAdjustType", config_params.pgv_angle_adjust_type)
        self.pgv_position_adjust_type = self.task_args.get(
            "positionAdjustType", config_params.pgv_position_adjust_type)

        # singleCode 可选参数
        self.pgv_code_number = self.task_args.get(
            "codeNumber", config_params.pgv_code_number)

        # multiLine 子参数
        self.pgv_line_angle_threshold = self.task_args.get(
            "lineAngleThreshold", config_params.pgv_line_angle_threshold)
        self.pgv_adjust_region = self.task_args.get(
            "adjustRegion", config_params.pgv_adjust_region)

        # 通用精度参数
        self.pgv_spin = self.task_args.get("pgvSpin", config_params.pgv_spin)
        self.pgv_reach_dist = self.task_args.get("pgvReachDist", config_params.pgv_reach_dist)
        self.pgv_reach_angle = self.task_args.get("pgvReachAngle", config_params.pgv_reach_angle)

        # laser area deduction
        self.create_or_delete_deducted_area = self.task_args.get("createOrDeleteDeductedArea", None)
        self.status = ScriptStatus.RUNNING

    def run(self):
        self.set_vda_param()
        # 选择执行动作
        if self.opt == "jackLoad":  # 识别/非识别取货
            self.jack_load()
        elif self.opt == "jackUnload":  # 识别/非识别放货
            self.jack_unload()
        elif self.opt == "getLM":
            self.get_lm()
        elif self.opt == "laserAreaDeduction":
            self.laser_area_deduction()
        elif self.opt == "goAPSite":  # 前往ap点，直线，bezier，两段线
            self.go_ap_site()
        elif self.opt == "goBezier":
            self.go_bezier()
        elif self.opt == "goPolyline":
            self.go_polyline()
        elif self.opt == "jackHeight":  # 控制托盘抬升高度
            self.jack_target_height()
        elif self.opt == "goMapPath":  # 前进一段距离
            self.go_map_path()
        elif self.opt == "goDist":  # 直线前进一段距离
            self.go_dist()
        elif self.opt == "goPath":  # 直线到达目标点（世界/机器人坐标系）
            self.go_path()
        elif self.opt == "recShelf":  # 识别货架
            self.rec_shelf()
        elif self.opt == "PGVSecondaryAdjust":  # 通过pgv单码调整
            self.pgv_adjust()
        # elif self.opt == "PGVCodeStripAdjust":  # 通过pgv码带调整
        #     self.pgv_code_strip_adjust()
        elif self.opt == "recTargetObs":
            self.rec_target_obs()
        elif self.opt == "getRecfile":
            self.get_rec_file()
        elif self.opt == "stopMotor":
            self.stop_motor()
        elif self.opt == "PGVSecondaryAndJackUp":
            self.pgv_second_and_jack_up()
        elif self.opt == "jackBezierReturn":
            self.jack_bezier_return()
        elif self.opt == "pressIoButton":
            self.press_button()
        elif self.opt == "calib":  # 外部指令强制标零（需 debugMode）
            self.do_force_calib()

        else:
            # Error53301: 不支持的任务指令
            Navigation.setTaskError("53350", f"不支持的任务指令: {self.opt}")
            self.status = ScriptStatus.FAILED

        # Trace.log(f"self.action_list: {self.action_list}")

        self.cur_action_list = []
        for task in self.action_list:
            self.cur_action_list.append(task.opt_info)

        # 只在 action_id 变化时输出日志（避免循环内重复输出）
        if not hasattr(self, '_last_logged_action_id') or self._last_logged_action_id != self.action_id:
            self._last_logged_action_id = self.action_id
            if self.action_id < len(self.action_list):
                current_action = self.action_list[self.action_id]
                debug_trace(f'[ACTION] #{self.action_id + 1}/{len(self.action_list)} {current_action.action_name}')
        # Trace.log(f'{current_action.action_name=}, {current_action.action_status=}')

        self._execute_actions()

    def press_button(self):
        if not self.operation_init:
            self.operation_init = True
            jack_height = Motor.getMotorPos(config_params.jack_motor_name)
            print(f"jack_height:{jack_height}")
            print(f"0.5 * (config_params.jack_min_height + config_params.jack_max_height):{0.5 * (config_params.jack_min_height + config_params.jack_max_height)}")
            if jack_height > 0.5 * (config_params.jack_min_height + config_params.jack_max_height):
                self.action_list.append(JackHeight(config_params.jack_motor_name, config_params.jack_min_height, config_params.jack_motor_speed))
            else:
                self.action_list.append(JackHeight(config_params.jack_motor_name, config_params.jack_max_height, config_params.jack_motor_speed))

    def pgv_second_and_jack_up(self):
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(GetPGVData(self.pgv_scan_device))
            self.action_list.append(PGVSecondaryAdjust(
                code_adjust_type=self.pgv_code_adjust_type,
                scan_device=self.pgv_scan_device,
                angle_adjust_type=self.pgv_angle_adjust_type,
                position_adjust_type=self.pgv_position_adjust_type,
                code_number=self.pgv_code_number,
                line_angle_threshold=self.pgv_line_angle_threshold,
                adjust_region=self.pgv_adjust_region,
                pgv_spin=self.pgv_spin,
                pgv_reach_dist=self.pgv_reach_dist,
                pgv_reach_angle=self.pgv_reach_angle
            ))
            self.action_list.append(JackHeight(config_params.jack_motor_name, self.end_height,
                                               config_params.jack_motor_speed))
            # 顶升完成后绑定容器，设置货物模型
            self.action_list.append(BindContainer("0", "shelf", self.recfile, self.insert_shelf_dir))

    def laser_area_deduction(self):
        if not self.operation_init:
            self.operation_init = True

            if self.create_or_delete_deducted_area == "create":

                self.laser_area_deduct_info = self.laser_area_deduct(self.recfile, "shelf")
                robot_loc = [Loc.getPose()["x"], Loc.getPose()["y"], math.radians(Loc.getPose()["yaw"])]
                debug_trace(f"robot_loc = {robot_loc}")
                area_device = {
                    "deduct_device": self.laser_area_deduct_info["deduct_device"],
                    "area": []
                }
                for idx, area in enumerate(self.laser_area_deduct_info["area"], start=1):
                    x_list_deduct_area = []
                    y_list_deduct_area = []
                    for j in range(len(area["x_list"])):
                        x = area["x_list"][j]
                        y = area["y_list"][j]
                        if self.coordinate == "robot":
                            x_list_deduct_area.append(x)
                            y_list_deduct_area.append(y)
                        else:
                            # 调用坐标变换
                            wx, wy, wz = pos2World([x, y, 0], robot_loc)
                            x_list_deduct_area.append(wx)
                            y_list_deduct_area.append(wy)
                    area_device["area"].append({
                        "x_list": x_list_deduct_area,
                        "y_list": y_list_deduct_area
                    })
                    # 对每个area执行操作
                    Navigation.setClearRegion(f"ForbiddenArea{idx}", x_list_deduct_area, y_list_deduct_area,
                                              self.laser_area_deduct_info["deduct_device"], Coordinate.ROBOT)

            elif self.create_or_delete_deducted_area == "delete":

                if self.coordinate == "robot":
                    clear_region_robot = Navigation.getClearRegion(Coordinate.ROBOT)
                    for region in clear_region_robot:
                        Navigation.deleteClearRegion(region, Coordinate.ROBOT)
                    self.report_info["test"] = {
                        "clearRegion": clear_region_robot
                    }
                elif self.coordinate == "world":
                    clear_region_world = Navigation.getClearRegion(Coordinate.WORLD)
                    for region in clear_region_world:
                        Navigation.deleteClearRegion(region, Coordinate.WORLD)
                    self.report_info["test"] = {
                        "clearRegion": clear_region_world
                    }
                    Module.reportInfo(self.report_info)

    def laser_area_deduct(self, recfile, object_key: str = "shelf"):
        """
        解析识别文件中的激光扣除区域配置

        返回格式:
        {
            "deductDevice": ["Laser-000"],
            "area": [
                {"xList": [...], "yList": [...]},
                ...
            ]
        }
        如果没有配置或解析失败，返回 None
        """
        if not recfile:
            return None

        try:
            recognition_obstacle_deduction_path = f"recognitionObject.{object_key}.obstacleDeduction"

            # 1) 获取数组大小
            size = RobotParam.getConfigCloneSize("recognition", recognition_obstacle_deduction_path, recfile)

            if size is None or size == 0:
                return None

            # 合并所有设备和区域
            all_devices = []
            all_areas = []

            # 2) 遍历数组 (._0, ._1, ...)
            for i in range(size):
                # 获取设备ID
                device_str = RobotParam.getConfig(
                    "recognition",
                    f"{recognition_obstacle_deduction_path}._{i}.deductDevice",
                    recfile
                )

                if not device_str:
                    continue

                devices = [d.strip() for d in device_str.split(",") if d.strip()]

                # 获取形状信息
                shape_str = RobotParam.getConfig(
                    "recognition",
                    f"{recognition_obstacle_deduction_path}._{i}.deductShape",
                    recfile
                )

                if not shape_str:
                    continue

                shapes = json.loads(shape_str)

                # 解析每个形状
                for idx, shape in enumerate(shapes):
                    pts = shape.get("points", [])
                    if len(pts) < 3:
                        continue
                    x_list = [p["x"] for p in pts]
                    y_list = [p["y"] for p in pts]
                    all_areas.append({"xList": x_list, "yList": y_list})

                # 合并设备列表
                for d in devices:
                    if d not in all_devices:
                        all_devices.append(d)

            if not all_areas:
                return None

            info = {
                "deductDevice": all_devices,
                "area": all_areas
            }

            # 只输出一条汇总日志
            debug_trace(f"[LASER] Deduct areas parsed: devices={all_devices}, count={len(all_areas)}")
            return info

        except json.JSONDecodeError as e:
            Trace.log(f"[ERROR] laser_area_deduct JSON解析失败: {e}")  # 错误日志始终输出
            return None
        except Exception as e:
            Trace.log(f"[ERROR] laser_area_deduct 异常: {e}")  # 错误日志始终输出
            import traceback
            if ConfigParams.debug_mode:
                traceback.print_exc()
            Trace.log(f"laser_area_deduct: Error - {e}")  # 错误日志始终输出
            return None

    """
    {
    'deduct_device': 'Laser-000',
    'area': [
        {'x_list': [0.437025, 0.691281, 0.691281, 0.437025],
        'y_list': [0.36353, 0.36353, 0.652118, 0.652118]},
        {'x_list': [0.437025, 0.69012, 0.69012, 0.437025],
        'y_list': [-0.595992, -0.595992, -0.355722, -0.355722]},
        {'x_list': [-0.412432, -0.412432, -0.619763, -0.619763],
        'y_list': [0.35816, 0.622824, 0.622824, 0.35816]},
        {'x_list': [-0.412432, -0.642432, -0.642432, -0.412432],
        'y_list': [-0.595992, -0.595992, -0.365992, -0.365992]}
            ]
    }
    """

    def get_rec_file(self):
        if not self.operation_init:
            self.operation_init = True
            # 如果钻入深度为None,即未传入back_dist,此时用识别文件中的钻入深度
            self.shelf_back_distance = self.get_back_distance_info(self.recfile, "shelf", self.insert_shelf_dir)
            debug_print(f"self.shelf_back_distance={self.shelf_back_distance}")
            self.laser_area_deduct_info = self.laser_area_deduct(self.recfile, "shelf")
            debug_print(f"self.laser_area_deduct_info={self.laser_area_deduct_info}")

    def get_back_distance_info(self, recfile, object_key: str = "shelf", side_name: str = "A"):
        """
        返回指定识别对象(object_key)下某个side(side_name)的后退距离开关与数值：
        {
            "side": "A",
            "enableBackDistance": True/False,
            "backDistance": 0.12  # 仅当 enableBackDistance 为 True 时存在
        }
        """
        # 路径前缀：recognitionObject.{object_key}.recognitionSide
        recognition_side_key = f"recognitionObject.{object_key}.recognitionSide"

        # 1) 获取 clone 数量，遍历查到指定 side
        side_count = RobotParam.getConfigCloneSize("recognition", recognition_side_key, recfile)
        target_idx = None
        for i in range(side_count):
            cur_side = RobotParam.getConfig("recognition", f"{recognition_side_key}._{i}", recfile)
            if cur_side == side_name:
                target_idx = i
                break

        if target_idx is None:
            Navigation.setTaskError("53353", f"识别文件中找不到方向 '{side_name}'，object={object_key}")
            self.status = ScriptStatus.FAILED

        # 2) 命中后读取 enableBackDistance / backDistance
        base = f"{recognition_side_key}._{target_idx}.{side_name}"
        enable_back = RobotParam.getConfig("recognition", f"{base}.enableBackDistance", recfile)
        back_dist = RobotParam.getConfig("recognition", f"{base}.enableBackDistance.on.backDistance", recfile)
        info = {
            "side": side_name,
            "enableBackDistance": enable_back,
            "backDistance": back_dist
        }

        # 3) 基本校验
        if any(v is None or v == "none" for v in info.values()):
            Navigation.setTaskError("53354", f"backDistance配置无效: {info}")
            self.status = ScriptStatus.FAILED

        debug_trace(f"backDistanceInfo = {info}")
        return info

    def rec_target_obs(self):
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(RecTargetObs("laser1"))

    def set_vda_param(self):
        # VDA下发的参数
        self.action_parameters = self.task_args.get("action_parameters", None)

    def get_lm(self):
        debug_trace("getLM ==============================================")
        result = Navigation.getLM(self.ap_id, True)
        self.report_info["getLM"] = {
            "LM": result
        }
        Module.reportInfo(self.report_info)
        debug_trace(f"getLM={result}")
        self.status = ScriptStatus.FINISHED
        return self.status

    def get_ap(self):
        """
        获取moveTask参数
        """
        move_task = Navigation.moveTask()
        return move_task.get("targetName", None)

    def _get_script_stage(self):
        """从moveTask的params中获取scriptStage，默认返回2"""
        move_task = Navigation.moveTask()
        for p in move_task.get("params", []):
            if p.get("key") == "scriptStage":
                return p.get("int32Value", 2)
        return 2

    def _append_load_actions(self, target_pos):
        """将导航、二次调整、旋转、顶升、绑定容器等动作添加到 action_list"""
        # 导航方式（无AP点原地执行时 target_pos 为 None，跳过导航）
        if target_pos is not None:
            if self.how_go_site == "straight":
                self.action_list.append(
                    GoPath(self.ap_world_pos, "world", self.is_backwards, self.is_hold_dir,
                           self.max_speed, self.max_rot, self.path_dist_accuracy, self.path_angle_accuracy))
            elif self.how_go_site == "bezier":
                recfile_back_dist = self.get_back_distance_info(self.recfile, "shelf", self.insert_shelf_dir)
                if not self.back_dist:
                    if recfile_back_dist.get("enableBackDistance") == "on":
                        self.back_dist = recfile_back_dist.get("backDistance", 0.24)
                    else:
                        self.back_dist = 0.24
                self.action_list.append(
                    GoBezier(target_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                             self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                             self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                             self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))
            elif self.how_go_site == "polyline":
                self.action_list.append(
                    GoPolyline(self.ap_world_pos, self.min_ahead_dist, self.adjust_dist_for_curvature_limit,
                               self.back_dist, self.max_speed, self.max_rot, self.decele_dist))

        # 二次调整
        if self.is_secondary_adjust:
            self.action_list.append(GetPGVData(self.pgv_scan_device))
            self.action_list.append(PGVSecondaryAdjust(
                code_adjust_type=self.pgv_code_adjust_type,
                scan_device=self.pgv_scan_device,
                angle_adjust_type=self.pgv_angle_adjust_type,
                position_adjust_type=self.pgv_position_adjust_type,
                code_number=self.pgv_code_number,
                line_angle_threshold=self.pgv_line_angle_threshold,
                adjust_region=self.pgv_adjust_region,
                pgv_spin=self.pgv_spin,
                pgv_reach_dist=self.pgv_reach_dist,
                pgv_reach_angle=self.pgv_reach_angle,
            ))

        # 顶升
        self.action_list.append(
            JackHeight(config_params.jack_motor_name, self.end_height, config_params.jack_motor_speed,
                       self.recfile))

        # 顶升完成后设置激光扣除区域
        self.action_list.append(SetLaserDeductArea(self.laser_area_deduct_info))

        # 顶升完成后绑定容器，设置货物模型（识别开启或有recfile时才加载）
        if self.is_recognize or self.recfile:
            self.action_list.append(BindContainer("0", "shelf", self.recfile, self.insert_shelf_dir))

    def jack_load(self):
        """
        完整取货流程：旋转车体对准 → 识别货架 → 导航 → 二次调整 → 顶升 → 设置激光扣除区域
        """
        if not self.operation_init:
            self.operation_init = True
            debug_trace("jackLoad: Starting sequence")

            # ============================================
            # Error53351: 重复取货保护 - 检查车上是否已有货物
            # ============================================
            if config_params.load_again_error and Navigation.hasGoods():
                Navigation.setTaskError("53351", "车上已有货物，不可重复取货。如需重复取货请关闭 LoadAgainError，或先执行 JackUnload")
                self.status = ScriptStatus.FAILED
                return

            # === 初始化时解析并设置扣除区域配置 ===
            if self.recfile:
                self.laser_area_deduct_info = self.laser_area_deduct(self.recfile, "shelf")
                debug_trace(f"jack_load: Parsed laser deduct info: {self.laser_area_deduct_info}")

            # 下降到起始高度
            if self.start_height:
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, self.start_height, config_params.jack_motor_speed))

            # atSite=True: 已到点，跳过旋转/识别/导航，直接二次调整+顶升
            if self.at_site:
                debug_trace("jack_load: atSite=True, 跳过旋转/识别/导航，直接二次调整+顶升")
                self._append_load_actions(None)
            else:
                # 获取AP点
                self.ap_id = self.ap_id or self.get_ap()
                if not self.ap_id:
                    # 原地动作：无AP点，跳过导航，直接执行取货
                    debug_trace("jack_load: no ap_id, 原地执行")
                else:
                    debug_trace(f"jack_load: ap_id={self.ap_id}")
                    self.ap_world_pos = Navigation.getLM(self.ap_id, True)
                    debug_trace(f"jack_load: AP_pos={self.ap_world_pos}")

                    self.report_info["jack_load"] = {"apWorldPos": self.ap_world_pos}
                    robot_loc = [Loc.getPose()["x"], Loc.getPose()["y"], math.radians(Loc.getPose()["yaw"])]

                    ap_to_robot_angle = math.atan2(self.ap_world_pos[1] - robot_loc[1], self.ap_world_pos[0] - robot_loc[0])

                    # 正车：车头朝向AP；倒车：车尾朝向AP（偏转180°）
                    if self.is_backwards:
                        target_angle = ap_to_robot_angle + math.pi
                    else:
                        target_angle = ap_to_robot_angle
                    self.action_list.append(RobotRotate(target_angle, Coordinate.WORLD, False))

                # 启用识别
                if self.is_recognize:
                    if not self.recfile:
                        Navigation.setTaskError("53352", "开启识别但未配置识别文件，请在任务参数中配置 recFile")
                        self.status = ScriptStatus.FAILED
                        return
                    self.action_list.append(
                        RecShelf(self.recfile, "FirstRec", side=self.insert_shelf_dir, is_backwards=self.is_backwards))
                else:
                    # 不识别时，直接在初始化阶段添加导航、二次调整、顶升等动作
                    self._append_load_actions(self.ap_world_pos)

        # 动态添加 action_list（识别完成后）
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]

            if current_action.action_name == "FirstRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                robot_pos = [Loc.getPose()["x"], Loc.getPose()["y"], math.radians(Loc.getPose()["yaw"])]
                result_robot = pos2Base(result_world, robot_pos)

                # 识别结果在机器人坐标系下 x < 1m → 太近，先后退再二次识别
                if result_robot[0] < 1:
                    self.action_list.append(GoPath([-0.3, 0, 0], "robot", True))
                    self.action_list.append(RecShelf(..., "SecondRec", side=self.insert_shelf_dir, is_backwards=self.is_backwards))
                else:
                    self._append_load_actions(result_world)

            if current_action.action_name == "SecondRec" and ...:
                result_world = self.rec_result
                self._append_load_actions(result_world)

    def jack_unload(self):
        """
        完整放货流程：下降托盘 → 删除激光扣除区域
        支持边走边动：如果预动作已经完成顶升下降，则跳过下降步骤
        """
        if not self.operation_init:
            self.operation_init = True
            debug_trace("jackUnload: Starting sequence")

            # 检查是否是边走边动模式下已经完成了顶升下降
            current_height = Motor.getMotorPos(config_params.jack_motor_name)
            if self.pre_action_completed and current_height <= 0.005:
                # 边走边动模式下顶升已经下降完成，跳过下降步骤，但仍需清除货物模型
                debug_trace(f"jackUnload: 边走边动模式，顶升已下降 (height={current_height:.4f}m)，跳过下降步骤")
                self.action_list.append(UnbindContainer("0"))
            else:
                # 正常模式或边走边动未完成，执行下降托盘
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, 0, config_params.jack_motor_speed))
                # 下降完成后解绑容器，清除货物模型
                self.action_list.append(UnbindContainer("0"))

            # === 放货完成后删除激光扣除区域 ===
            self.action_list.append(DeleteLaserDeductArea())

    def go_ap_site(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("targetName", None)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            debug_trace(f'go_ap_site AP_pos: {self.ap_world_pos}')
            if self.how_go_site == "straight":
                self.action_list.append(GoPath(self.ap_world_pos, "world"))
            elif self.how_go_site == "bezier":
                self.action_list.append(GoBezier(self.ap_world_pos))
            elif self.how_go_site == "polyline":
                self.action_list.append(GoPolyline(self.ap_world_pos))

    def go_bezier(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("targetName", None)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            debug_trace(f'go_bezier AP_pos: {self.ap_world_pos}')
            self.action_list.append(
                GoBezier(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                         self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                         self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                         self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))

    def go_polyline(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("targetName", None)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)
            debug_trace(f'go_polyline AP_pos: {self.ap_world_pos}')
            self.action_list.append(GoMapPath())

    def jack_bezier_return(self):
        """
        调试用：bezier导航到AP点 → 识别货架 → 顶升 → bezier退回原始位置
        参数：startHeight, endHeight, recFile, insertShelfDir
        """
        if not self.operation_init:
            self.operation_init = True
            debug_trace("jackBezierReturn: Starting sequence")

            # 记录起始位置（用于返回）
            robot_loc = Loc.getPose()
            self.return_pos = [robot_loc["x"], robot_loc["y"], math.radians(robot_loc["yaw"])]
            debug_trace(f"jackBezierReturn: return_pos={self.return_pos}")

            # 下降到起始高度
            if self.start_height:
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, self.start_height, config_params.jack_motor_speed))

            # 获取AP点
            self.ap_id = self.ap_id or self.get_ap()
            if not self.ap_id:
                # 原地动作：无AP点，跳过导航
                debug_trace("jackBezierReturn: no ap_id, 原地执行")
            else:
                self.ap_world_pos = Navigation.getLM(self.ap_id, True)
                debug_trace(f"jackBezierReturn: ap_id={self.ap_id}, AP_pos={self.ap_world_pos}")

                # 对准AP方向
                robot_loc2 = [Loc.getPose()["x"], Loc.getPose()["y"], math.radians(Loc.getPose()["yaw"])]
                ap_to_robot_angle = math.atan2(
                    self.ap_world_pos[1] - robot_loc2[1],
                    self.ap_world_pos[0] - robot_loc2[0]
                )

                # 正车：车头朝向AP；倒车：车尾朝向AP（偏转180°）
                if self.is_backwards:
                    target_angle = ap_to_robot_angle + math.pi
                else:
                    target_angle = ap_to_robot_angle
                self.action_list.append(RobotRotate(target_angle, Coordinate.WORLD, False))

            # 识别货架
            if self.recfile:
                self.action_list.append(RecShelf(self.recfile, "BezierReturnRec", side=self.insert_shelf_dir, is_backwards=self.is_backwards))

        # 识别完成后动态追加后续动作
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]

            if current_action.action_name == "BezierReturnRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result

                # bezier 进入货架
                recfile_back_dist = self.get_back_distance_info(self.recfile, "shelf", self.insert_shelf_dir)
                if not self.back_dist:
                    if recfile_back_dist.get("enableBackDistance") == "on":
                        self.back_dist = recfile_back_dist.get("backDistance", 0.24)
                    else:
                        self.back_dist = 0.24
                self.action_list.append(
                    GoBezier(result_world, self.back_dist, self.adjust_dist_for_curvature_limit,
                             self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                             self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                             self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))

                # 顶升
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, self.end_height, config_params.jack_motor_speed))
                self.action_list.append(BindContainer("0", "shelf", self.recfile, self.insert_shelf_dir))

                # bezier 退回起始位置
                self.action_list.append(
                    GoBezier(self.return_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                             self.min_ahead_dist,not self.is_backwards, self.is_hold_dir,
                             self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                             self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))

    def go_map_path(self):
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(GoMapPath())

    def jack_target_height(self):
        """抬升托盘到指定高度"""
        if not self.operation_init:
            self.operation_init = True
            debug_trace("jack_height: Starting sequence")
            self.action_list.append(JackHeight(config_params.jack_motor_name, self.end_height,
                                               config_params.jack_motor_speed))

    def go_dist(self):
        """前进一段距离"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(GoStraightDist(self.goPath_x))  # 导航到终点

    def go_path(self):
        """前进一段距离"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(
                GoPath([self.goPath_x, self.goPath_y, self.goPath_theta], self.coordinate, self.is_backwards,
                       self.is_hold_dir, self.max_speed, self.max_rot, self.path_dist_accuracy,
                       self.path_angle_accuracy))

    def rec_shelf(self):
        """识别货架"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(RecShelf(self.recfile, side=self.insert_shelf_dir, is_backwards=self.is_backwards))

    def pgv_adjust(self):
        """二次调整"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(GetPGVData(self.pgv_scan_device))
            self.action_list.append(PGVSecondaryAdjust(
                code_adjust_type=self.pgv_code_adjust_type,
                scan_device=self.pgv_scan_device,
                angle_adjust_type=self.pgv_angle_adjust_type,
                position_adjust_type=self.pgv_position_adjust_type,
                code_number=self.pgv_code_number,
                line_angle_threshold=self.pgv_line_angle_threshold,
                adjust_region=self.pgv_adjust_region,
                pgv_spin=self.pgv_spin,
                pgv_reach_dist=self.pgv_reach_dist,
                pgv_reach_angle=self.pgv_reach_angle
            ))

    # def pgv_code_strip_adjust(self):
    #     """码带调整（codeNumber模式）"""
    #     if not self.operation_init:
    #         self.operation_init = True
    #         # 使用下视PGV读取码带
    #         self.action_list.append(GetPGVData(config_params.pgv_use_which))
    #         # 码带调整
    #         self.action_list.append(PGVCodeStripAdjust(
    #             angle_adjust_type=self.angle_adjust_type,
    #             pgv_reach_dist=self.pgv_reach_dist or config_params.pgv_reach_dist,
    #             pgv_reach_angle=self.pgv_reach_angle or config_params.pgv_reach_angle,
    #             use_target_position=self.use_target_position,
    #             r2ad_x=self.r2ad_x,
    #             r2ad_y=self.r2ad_y,
    #             r2ad_theta=self.r2ad_theta
    #         ))

    def stop_motor(self):
        if not self.operation_init:
            self.operation_init = True
            Motor.stopMotor()
            Motor.resetMotor(config_params.jack_motor_name)

    def _execute_actions(self):
        if self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_status == ActionStatus.FINISHED:
                self.action_id += 1
            elif current_action.action_status == ActionStatus.FAILED:
                Navigation.setTaskError("53355", f"动作执行失败: {current_action}")
                self.status = ScriptStatus.FAILED
            else:
                current_action.run(self)
        else:
            self.status = ScriptStatus.FINISHED
            self.action_list = []

    def suspend(self):
        self.status = ScriptStatus.SUSPENDED
        debug_trace("suspend")

    def resume(self):
        if self.status == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        debug_trace("resume")

    def cancel(self):
        Motor.stopMotor()
        Navigation.resetGoMapPath()
        Navigation.resetGoPGV()
        self.action_list = []
        self.action_id = 0
        self.status = ScriptStatus.FAILED
        Module.setStatus(ScriptStatus.FAILED)
        debug_trace("cancel")

    def safe_move_check(self):
        self.count += 1
        status = SafeMoveStatus.RUNNING
        if self.count == 100:
            self.count = 0
            status = SafeMoveStatus.FINISHED
        self.setSafeMoveStatus(status)
        debug_trace(f"safe_move_check {Module.getSafeMoveCheck()}")
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False

    def set_info(self):
        self.jack_motors = NavSpeed.getMotorCmd()
        self.jack_speed = Motor.getMotorSpeed(config_params.jack_motor_name)
        self.jack_isFull = Navigation.hasGoods()
        self.jack_emc = Controller.getEmc()
        self.jack_height = Motor.getMotorPos(config_params.jack_motor_name)
        self.report_info.update({
            "jackMode": True,
            "jackEnable": True,
            "jackSpeed": self.jack_speed,
            "jackEmc": self.jack_emc,
            "jackIsFull": self.jack_isFull,
            "jackHeight": self.jack_height,
            "containers": Container.getContainers()
        })

        Module.reportInfo(self.report_info)
        self.info_count = self.info_count + 1

    def update_move_task_params(self):
        """
        获取moveTask参数，支持边走边动模式
        监听#finalBinTask和#finalLoc参数，当检测到jackUnload任务时进入预动作模式

        支持两种格式：
        1. realTimeMoveTask().params[] 格式 (key/stringValue)
        2. moveTaskList[] 格式 (直接属性 #finalBinTask/#finalLoc)
        """
        new_final_loc = None
        new_final_bin_task = None

        try:
            # 尝试方式1: realTimeMoveTask的params格式
            move_task = Navigation.realTimeMoveTask()
            if move_task and 'params' in move_task:
                for p in move_task.get('params', []):
                    if p.get('key') == '#finalBinTask' and p.get('stringValue', '') != "":
                        new_final_bin_task = p['stringValue']
                    if p.get('key') == '#finalLoc' and p.get('stringValue', '') != "":
                        new_final_loc = p['stringValue']

            # 尝试方式2: 直接从move_task对象获取（兼容不同格式）
            if not new_final_bin_task:
                new_final_bin_task = move_task.get('#finalBinTask', '')
            if not new_final_loc:
                new_final_loc = move_task.get('#finalLoc', '')

        except Exception as e:
            debug_trace(f"[边走边动] 获取realTimeMoveTask异常: {e}")

        # 尝试方式3: 从moveTask获取（你的实际格式）
        try:
            if not new_final_bin_task or not new_final_loc:
                move_task_info = Navigation.moveTask()
                if move_task_info:
                    if not new_final_bin_task:
                        new_final_bin_task = move_task_info.get('#finalBinTask', '')
                    if not new_final_loc:
                        new_final_loc = move_task_info.get('#finalLoc', '')
        except Exception as e:
            debug_trace(f"[边走边动] 获取moveTask异常: {e}")

        # 调试输出
        if new_final_loc or new_final_bin_task:
            debug_trace(f"[边走边动] 检测到参数: finalLoc={new_final_loc}, finalBinTask={new_final_bin_task}")

        # 只有新任务且与上次不同时才更新
        if new_final_loc and new_final_bin_task:
            if new_final_loc != getattr(self, 'final_loc', None) or new_final_bin_task != getattr(self,
                                                                                                  'final_bin_task',
                                                                                                  None):
                self.final_loc = new_final_loc
                self.final_bin_task = new_final_bin_task

                debug_trace(f"[边走边动] 新任务: finalLoc={new_final_loc}, finalBinTask={new_final_bin_task}")

                # 尝试获取binTask的脚本参数
                result = None
                try:
                    result = Navigation.getBinTask(self.final_loc, self.final_bin_task)
                    debug_trace(f"[边走边动] getBinTask结果: {result}")
                except Exception as e:
                    debug_trace(f"[边走边动] getBinTask异常: {e}")

                if result:
                    full_args = result.get('scriptArgs', {})
                    self.full_action_args = full_args
                    operation = full_args.get('operation', '')
                else:
                    # 如果getBinTask没有返回结果，直接使用finalBinTask作为operation判断
                    # unload -> jackUnload
                    self.full_action_args = {'operation': 'jackUnload'}
                    operation = 'jackUnload' if new_final_bin_task == 'unload' else new_final_bin_task
                    debug_trace(f"[边走边动] 使用finalBinTask推断operation: {operation}")

                # jackUnload时启用边走边动：在导航过程中慢慢降下顶升
                if operation == 'jackUnload' or new_final_bin_task == 'unload':
                    self.pre_action_mode = True
                    self.pre_action_completed = False
                    self.pre_action_step = [False] * 5

                    self.pre_action_args = {
                        'operation': 'jackUnload',
                        'target_height': 0,  # jackUnload目标高度为0（下降到底）
                    }
                    debug_trace(f"[边走边动] 进入预动作模式, operation={operation}, 开始在导航过程中下降顶升")
                else:
                    # 其他操作不使用边走边动
                    self.result = self.full_action_args
                    self.pre_action_mode = False

        # 检查是否到达终点
        self._check_at_final_loc()

    def _check_at_final_loc(self):
        """
        检查是否已到达终点：当#finalBinTask消失或binTask出现时表示已到达
        """
        if not self.pre_action_mode:
            self.at_final_loc = False
            return

        try:
            has_final_bin_task = False
            has_bin_task = False

            # 方式1: 检查realTimeMoveTask
            try:
                move_task = Navigation.realTimeMoveTask()
                if move_task:
                    # 检查params格式
                    for p in move_task.get('params', []):
                        if p.get('key') == '#finalBinTask' and p.get('stringValue', '') != "":
                            has_final_bin_task = True
                        if p.get('key') == 'binTask' and p.get('stringValue', '') != "":
                            has_bin_task = True
                    # 检查直接属性格式
                    if move_task.get('#finalBinTask', ''):
                        has_final_bin_task = True
                    if move_task.get('binTask', ''):
                        has_bin_task = True
            except:
                pass

            # 方式2: 检查moveTask
            try:
                move_task_info = Navigation.moveTask()
                if move_task_info:
                    if move_task_info.get('#finalBinTask', ''):
                        has_final_bin_task = True
                    if move_task_info.get('binTask', ''):
                        has_bin_task = True
            except:
                pass

            # 判断是否到达终点：
            # 1. #finalBinTask消失 表示已经到达最终点
            # 2. binTask出现 表示当前就是执行点
            if (not has_final_bin_task or has_bin_task) and self.pre_action_mode:
                if not self.at_final_loc:  # 首次检测到
                    debug_trace(
                        f"[边走边动] 判断已到达终点 (has_final_bin_task={has_final_bin_task}, has_bin_task={has_bin_task})")
                    time.sleep(0.3)  # 等待系统稳定
                self.at_final_loc = True
            else:
                self.at_final_loc = False

        except Exception as e:
            debug_trace(f"[边走边动] 检查终点状态异常: {e}")
            self.at_final_loc = False

    def pre_unload_action(self):
        """
        jackUnload预动作：在导航过程中慢慢把顶升电机降下来
        """
        debug_trace(f"----- running pre_unload_action (边走边动下降顶升) ------")

        target_height = self.pre_action_args.get('target_height', 0)

        # 获取当前顶升高度
        current_height = Motor.getMotorPos(config_params.jack_motor_name)

        # 如果已经到达目标高度，标记完成
        if current_height <= target_height + 0.005:  # 允许5mm误差
            self.pre_action_step[0] = True
            debug_trace(f"[边走边动] 顶升已下降到位: {current_height:.4f}m")
        else:
            # 持续下降顶升
            if not self.pre_action_step[0]:
                # 使用较慢的速度下降，边走边动
                slow_speed = config_params.jack_motor_speed * 0.5  # 使用一半速度，更平稳
                if config_params.jack_zero_di:
                    Motor.setMotorPosition(config_params.jack_motor_name, target_height, slow_speed,
                                           config_params.jack_zero_di)
                else:
                    Motor.setMotorPosition(config_params.jack_motor_name, target_height, slow_speed)

                # 检查是否到达
                if Motor.isMotorReached(config_params.jack_motor_name) or (config_params.jack_zero_di and Di.getDi(config_params.jack_zero_di)):
                    self.pre_action_step[0] = True
                    Motor.resetMotor(config_params.jack_motor_name)
                    debug_trace(f"[边走边动] 顶升下降完成: {current_height:.4f}m -> {target_height}m")

        self.report_info["preActionInfo"] = {
            'preActionStep': self.pre_action_step,
            'targetHeight': target_height,
            'currentHeight': current_height,
            'atFinalLoc': self.at_final_loc
        }

        if self.pre_action_step[0]:
            self.pre_action_completed = True
            debug_trace(f"[边走边动] jackUnload预动作完成（顶升已下降）")
            return True
        return False

    def execute_pre_action(self):
        """根据操作类型执行预动作"""
        operation = self.pre_action_args.get('operation', '')
        if operation == 'jackUnload':
            return self.pre_unload_action()
        return True

    def run_pre_action(self):
        """
        边走边动：在status==NONE时执行预动作，由main循环调用
        在导航过程中慢慢把顶升电机降下来
        """

        self.set_info()  # 更新状态信息

        self.report_info['preActionMode'] = True
        self.report_info['preActionCompleted'] = self.pre_action_completed
        self.report_info['atFinalLoc'] = self.at_final_loc

        if not self.pre_action_completed:
            self.execute_pre_action()
            debug_trace(f"[边走边动] 执行预动作中（下降顶升）... step={self.pre_action_step}")
        elif self.at_final_loc:
            self.switch_to_full_action()
            debug_trace(f"[边走边动] 已到达终点，切换到完整动作模式")
        else:
            debug_trace(f"[边走边动] 预动作已完成（顶升已下降），等待到达终点...")

        Module.reportInfo(self.report_info)

    def switch_to_full_action(self):
        """切换到完整动作模式"""
        if self.full_action_args:
            operation = self.full_action_args.get('operation', '')

            if operation == 'jackUnload':
                # 顶升已经在预动作中下降完成，直接标记完成或执行剩余动作
                debug_trace(f"[边走边动] jackUnload切换到完整动作，顶升已预先下降")

            self.pre_action_mode = False
            self.status = ScriptStatus.NONE
            Module.setStatus(self.status)

            # 设置result，让main循环中的常规流程继续执行剩余动作
            self.result = self.full_action_args

            debug_trace(f"[边走边动] 预动作模式结束，等待binTask下发完成剩余动作")
            return True
        return False


# --- 以下为各个基础动作类（内容保持不变） ---
class BaseAction:
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        self.action_name = action_name or self.__class__.__name__
        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.action_state = {}

    def run(self, m):
        self.action_state["action_runtime"] = time.time() - self.start_time
        pass

    def reset(self):
        pass

    def __str__(self):
        return json.dumps({
            "class_name": self.__class__.__name__
        })


class SetLaserDeductArea(BaseAction):
    """设置激光扣除区域（取货完成后调用）"""

    def __init__(self, deduct_info, prefix: str = "ShelfDeductArea", coordinate=Coordinate.ROBOT):
        super().__init__("SetLaserDeductArea")
        self.deduct_info = deduct_info
        self.prefix = prefix
        self.coordinate = coordinate
        self.init = True
        self.opt_info = f"{self.__class__.__name__}{{prefix={prefix}}}"

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

            if not self.deduct_info:
                debug_trace("SetLaserDeductArea: No deduct info, skipping")
                self.action_status = ActionStatus.FINISHED
                return

            try:
                devices = self.deduct_info.get("deductDevice", [])
                areas = self.deduct_info.get("area", [])

                debug_trace(f"SetLaserDeductArea: Setting {len(areas)} areas, devices={devices}")

                for idx, area in enumerate(areas, start=1):
                    x_list = area.get("xList", area.get("x_list", []))
                    y_list = area.get("yList", area.get("y_list", []))

                    if len(x_list) < 3 or len(x_list) != len(y_list):
                        debug_trace(f"SetLaserDeductArea: Skip invalid area idx={idx}")
                        continue

                    region_name = f"{self.prefix}{idx}"
                    Navigation.setClearRegion(region_name, x_list, y_list, devices, self.coordinate)
                    debug_trace(f"SetLaserDeductArea: Created {region_name}")

                self.action_status = ActionStatus.FINISHED

            except Exception as e:
                Trace.log(f"SetLaserDeductArea error: {e}")
                self.action_status = ActionStatus.FINISHED

        j.report_info["SetLaserDeductArea"] = {"actionStatus": self.action_status, "prefix": self.prefix}
        Module.reportInfo(j.report_info)


class DeleteLaserDeductArea(BaseAction):
    """删除激光扣除区域（放货完成后调用）"""

    def __init__(self, prefix: str = "ShelfDeductArea", coordinate=Coordinate.ROBOT):
        super().__init__("DeleteLaserDeductArea")
        self.prefix = prefix
        self.coordinate = coordinate
        self.init = True
        self.opt_info = f"{self.__class__.__name__}{{prefix={prefix}}}"

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

            try:
                clear_regions = Navigation.getClearRegion(self.coordinate)
                deleted_count = 0

                if clear_regions:
                    for region in clear_regions:
                        if region.startswith(self.prefix):
                            Navigation.deleteClearRegion(region, self.coordinate)
                            debug_trace(f"DeleteLaserDeductArea: Deleted {region}")
                            deleted_count += 1

                debug_trace(f"DeleteLaserDeductArea: Deleted {deleted_count} regions")
                self.action_status = ActionStatus.FINISHED

            except Exception as e:
                Trace.log(f"DeleteLaserDeductArea error: {e}")
                self.action_status = ActionStatus.FINISHED

        j.report_info["DeleteLaserDeductArea"] = {"actionStatus": self.action_status, "prefix": self.prefix}
        Module.reportInfo(j.report_info)

class RobotRotate(BaseAction):
    """只转车不转托盘"""

    def __init__(self, angle, coordinate, spin=True, direction=None, unit="rad"):
        super().__init__("RobotRotate")

        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.action_status = ActionStatus.INIT
        self.init = True

        self.angle = angle  # 角度或弧度
        self.coordinate = coordinate
        self.spin = spin
        self.direction = direction  # 0 shortest; -1 cw; 1 ccw
        self.speed = 0.7
        self.move_args = dict()
        self.robot_ang = []
        if unit == "deg":
            self.angle = math.radians(angle)  # 统一转成弧度存储
        else:
            self.angle = angle  # 已经是弧度，直接存

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetOdoMove()
            self.move_args['spin'] = self.spin  # 是否随动
            self.move_args['speedW'] = self.speed
            if self.coordinate == Coordinate.ROBOT:
                self.move_args['locMode'] = 0  # 基于里程定位
                self.move_args['moveAngle'] = self.angle
                if self.angle < 0:
                    self.move_args['moveAngle'] = -self.angle
                    self.move_args['speedW'] = -self.speed
            elif self.coordinate == Coordinate.WORLD:
                cur_angle_rad = self.normalize(math.radians(Loc.getPose()["yaw"]))

                # self.angle 此时一定是弧度，不再需要猜测
                target_rad = self.normalize(self.angle)

                self.move_args["locMode"] = 1  # 激光定位

                # # 1. 当前朝向：Loc 返回的是度 - 立即转弧度 - 归一化
                # cur_angle_rad = self.normalize(math.radians(Loc.getPose()["yaw"]))

                # # 2. 目标朝向：外部传进来是“度” - 先转弧度，再归一化
                # target_rad = self.normalize(math.radians(self.angle) if abs(self.angle) > math.pi else self.angle)

                # 3. 差值也要再归一化一次，确保 (-π, π]
                rotate_dist = self.normalize(target_rad - cur_angle_rad)  # 就近方向的符号差

                # 默认“就近”   —— 速度正负=方向，幅值必为正
                speed_w = self.speed if rotate_dist >= 0 else -self.speed
                move_ang = abs(rotate_dist)

                # 用户强制指定方向时覆写
                if self.direction == 0:  # 逆时针
                    speed_w = self.speed
                    move_ang = abs(rotate_dist) if rotate_dist >= 0 else 2 * math.pi - abs(rotate_dist)
                elif self.direction == 1:  # 顺时针
                    speed_w = -self.speed
                    move_ang = abs(rotate_dist) if rotate_dist <= 0 else 2 * math.pi - abs(rotate_dist)

                # 4. 最终写回 move_args（注意 move_angle 一律为正幅值）
                self.move_args.update({
                    "spin": self.spin,
                    "speedW": speed_w,
                    "moveAngle": move_ang
                })

        status = Navigation.runOdoMove(self.move_args)
        debug_trace(f"{status=}")
        if status == ActionStatus.FINISHED:
            self.action_status = ActionStatus.FINISHED

        j.report_info["RobotRotate"] = {
            "actionStatus": self.action_status,
            "isSpinHeld": self.move_args['spin'],
            "angle": self.angle,
            "coordinate": self.coordinate,
            "direction": self.direction
        }
        Module.reportInfo(j.report_info)

    def reset(self):
        Navigation.resetOdoMove()
        debug_trace("reset RobotRotate")
        self.action_status = ActionStatus.RUNNING

    def normalize(self, rad: float) -> float:
        """把任意弧度角归一化到 (-π, π] 区间"""
        return (rad + math.pi) % (2 * math.pi) - math.pi


class JackHeight(BaseAction):
    """顶升动作，通过设置电机位置实现顶升"""

    def __init__(self, motor_name, target_height, jack_motor_speed, recfile=None, object_key="shelf"):
        super().__init__("JackHeight")

        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.motor_name = motor_name
        self.target_height = target_height
        self.jackMotorSpeed = jack_motor_speed
        self.recfile = recfile
        self.object_key = object_key
        self.init = False
        self.jack_start_height = None
        self._count_recorded = False  # 防止重复计数
        self._last_progress = -1  # 用于进度日志去重
        self._up_di_triggered_time = None # 上到位 DI/isReached 触发时间戳（用于延迟）
        self._motor_moved = False  # 电机是否已开始运动
        Motor.resetMotor(self.motor_name)

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            self.jack_start_height = Motor.getMotorPos(config_params.jack_motor_name)
            self._motor_moved = False
            self._init_time = time.time()

            # 只在初始化时输出一次关键信息
            direction = "↑Jack up" if self.target_height > self.jack_start_height else "↓Jack down"
            debug_trace(
                f"[JACK] {direction} {self.jack_start_height:.3f}m → {self.target_height:.3f}m (speed={self.jackMotorSpeed})")

            # 目标高度等于当前高度，无需动作
            if abs(self.target_height - self.jack_start_height) < 0.001:
                Trace.log(f"[JACK] 目标高度与当前高度相同({self.jack_start_height:.3f}m)，跳过")
                self.action_status = ActionStatus.FINISHED
                return

            if self.target_height > self.jack_start_height:
                # 初始化前检查：上到位 DI 不应该已经触发
                if config_params.jack_up_di and Di.getDi(config_params.jack_up_di):
                    Trace.log(f"[JACK] 警告: 上到位DI({config_params.jack_up_di})在顶升前已触发，请检查DI配置")
                    Navigation.setDeviceError("53304", f"顶升前上到位DI({config_params.jack_up_di})已触发，DI配置错误或机械卡住")
                    self.action_status = ActionStatus.FAILED
                    return
                if config_params.jack_up_di:
                    Motor.setMotorPosition(self.motor_name, self.target_height, self.jackMotorSpeed,
                                           config_params.jack_up_di)
                else:
                    Motor.setMotorPosition(self.motor_name, self.target_height, self.jackMotorSpeed)
            else:
                # 初始化前检查：下到位 DI 不应该已经触发
                if config_params.jack_zero_di and Di.getDi(config_params.jack_zero_di):
                    Trace.log(f"[JACK] 警告: 下到位DI({config_params.jack_zero_di})在下降前已触发，请检查DI配置")
                    Navigation.setDeviceError("53305", f"下降前下到位DI({config_params.jack_zero_di})已触发，DI配置错误或机械卡住")
                    self.action_status = ActionStatus.FAILED
                    return
                if config_params.jack_zero_di:
                    Motor.setMotorPosition(self.motor_name, self.target_height, self.jackMotorSpeed,
                                           config_params.jack_zero_di)
                else:
                    Motor.setMotorPosition(self.motor_name, self.target_height, self.jackMotorSpeed)

        # 获取当前电机位置
        current_pos = Motor.getMotorPos(self.motor_name)

        # 检测电机是否已开始运动
        if not self._motor_moved and abs(current_pos - self.jack_start_height) > 0.001:
            self._motor_moved = True

        # 计算并输出进度（每10%输出一次，避免刷屏）
        if self.jack_start_height != self.target_height:
            progress = int(
                abs(current_pos - self.jack_start_height) / abs(self.target_height - self.jack_start_height) * 100)
            progress = min(progress, 100)
            progress_10 = progress // 10 * 10  # 取整到10%
            if self._last_progress < progress_10 < 100:
                self._last_progress = progress_10
                debug_trace(f"[JACK] progress: {progress_10}% (pos={current_pos:.4f}m)")

        if self.target_height > self.jack_start_height:
            # 顶升动作：触发上到位 DI 后结束
            if Motor.isMotorReached(self.motor_name) or (config_params.jack_up_di and Di.getDi(config_params.jack_up_di)):
                if not self._motor_moved:
                    Trace.log(f"[JACK] 警告: 电机未运动就触发到位信号，pos={current_pos:.4f}m，请检查DI配置")
                if self._up_di_triggered_time is None:
                    self._up_di_triggered_time = time.time()
                    debug_trace(f"[JACK] 上到位触发 pos={current_pos:.4f}m")
                elif time.time() - self._up_di_triggered_time >= 0.2:
                    self.action_status = ActionStatus.FINISHED
                    Motor.resetMotor(self.motor_name)
                    debug_trace(f"[JACK] 顶升完成 pos={current_pos:.4f}m")

                    if not self._count_recorded:
                        self._count_recorded = True
                        jack_count_manager.increment_count()
        else:
            # 下降动作
            if Motor.isMotorReached(self.motor_name) or (config_params.jack_zero_di and Di.getDi(config_params.jack_zero_di)):
                if not self._motor_moved:
                    Trace.log(f"[JACK] 警告: 电机未运动就触发到位信号，pos={current_pos:.4f}m，请检查DI配置")
                self.action_status = ActionStatus.FINISHED
                Motor.resetMotor(self.motor_name)
                debug_trace(f"[JACK] Jack down done pos={current_pos:.4f}m")


        j.report_info["JackHeight"] = {
            "actionStatus": self.action_status,
            "motorName": self.motor_name,
            "targetHeight": self.target_height,
            "jackMotorSpeed": self.jackMotorSpeed,
        }
        Module.reportInfo(j.report_info)

class BindContainer(BaseAction):
    """顶升完成后绑定容器并设置货物模型"""

    def __init__(self, container_id: str, goods_name: str, recfile: str, insert_dir: str = "D"):
        super().__init__("BindContainer")
        self.opt_info = f"BindContainer{{container_id={container_id}, goods_name={goods_name}, recfile={recfile}}}"
        self.container_id = container_id
        self.goods_name = goods_name
        self.recfile = recfile
        self.insert_dir = insert_dir

    def run(self, j: Jack):
        ok = j.bindContainer(self.container_id, self.goods_name, self.recfile or "default.srec", self.insert_dir)
        if not ok:
            Trace.log(f"[BindContainer] 绑定失败，recfile={self.recfile}")
        self.action_status = ActionStatus.FINISHED


class UnbindContainer(BaseAction):
    """下降完成后解绑容器并清除货物模型"""

    def __init__(self, container_id: str):
        super().__init__("UnbindContainer")
        self.opt_info = f"UnbindContainer{{container_id={container_id}}}"
        self.container_id = container_id

    def run(self, j: Jack):
        j.unbindContainer(self.container_id)
        Trace.log(f"[UnbindContainer] 解绑成功: container={self.container_id}")
        self.action_status = ActionStatus.FINISHED


class GoMapPath(BaseAction):
    """前进指定距离"""

    def __init__(self):
        super().__init__("GoMapPath")
        self.opt_info = f"{self.__class__.__name__}{{}}"
        self.init = True
        self.action_status = ActionStatus.INIT
        self.task = Navigation.moveTask()

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetGoMapPath()
        finished = Navigation.goMapPath()
        if finished:
            self.action_status = ActionStatus.FINISHED

        self.action_state['status'] = self.action_status


class GoStraightDist(BaseAction):
    """前进/后退指定距离"""

    def __init__(self, go_dist):
        super().__init__("GoStraightDist")
        self.opt_info = f"{self.__class__.__name__}{{go_dist={go_dist}}}"
        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_dist = go_dist

    def run(self, j: Jack):
        if self.init:
            if self.go_dist < 0.0:
                Navigation.setPathBackMode(False)
            else:
                Navigation.setPathBackMode(True)
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            Navigation.setPathOnRobot([0, self.go_dist], [0, 0], 0)
        Navigation.goPath()
        finished = Navigation.isPathReached()
        if finished:
            self.action_status = ActionStatus.FINISHED

        Module.reportInfo({"GoStraightDist": {"status": self.action_status}})
        Module.reportInfo({"GoStraightDist": {"goDist": self.go_dist}})


class GoPath(BaseAction):
    """直线走到指定点"""

    def __init__(self, go_pos, coordinate='robot', back_mode=False, is_hold_dir=None, max_speed=0.5, max_rot=0.3,
                 path_dist_accuracy=0.01, path_angle_accuracy=0.05):
        super().__init__("GoPath")

        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_pos = go_pos
        self.coordinate = coordinate
        self.back_mode = back_mode
        self.is_hold_dir = is_hold_dir
        self.max_speed = max_speed
        self.max_rot = max_rot
        self.path_dist_accuracy = path_dist_accuracy
        self.path_angle_accuracy = path_angle_accuracy
        self.go_path = goPath.GoPath()

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

        args = {
            "x": self.go_pos[0],
            "y": self.go_pos[1],
            "theta": self.go_pos[2],
            "backMode": self.back_mode,
            "hold_dir": self.is_hold_dir,
            "coordinate": getattr(self.coordinate, 'name', self.coordinate),
            "maxSpeed": self.max_speed,
            # "maxRot": self.max_rot,
            "reachDist": self.path_dist_accuracy,
            "reachAngle": self.path_angle_accuracy
        }
        self.action_status = self.go_path.run(args)

        j.report_info["GoPath"] = {
            "actionStatus": self.action_status,
            "goPos": self.go_pos,
            "backMode": self.back_mode,
            "holdDir": self.is_hold_dir,
            "coordinate": getattr(self.coordinate, 'name', self.coordinate),
            "maxSpeed": self.max_speed,
            # "maxRot": self.max_rot,
            "reachDist": self.path_dist_accuracy,
            "reachAngle": self.path_angle_accuracy
        }
        Module.reportInfo(j.report_info)


class GoBezierCombined(BaseAction):
    """执行行走贝塞尔曲线到达取货点"""

    def __init__(self, target_world, back_dist=0, adjust_dist_for_curvature_limit=2, min_ahead_dist=0,
                 is_backwards=False, is_hold_dir=None,
                 max_speed=0.3, max_accele=0.3, max_decele=0.2, decele_dist=1, curvature_limit=1.3,
                 path_dist_accuracy=0.01,
                 path_angle_accuracy=0.05):
        super().__init__()
        self.opt_info = f"{self.__class__.__name__}{{target_world={target_world}, back_dist={back_dist}}}"
        self.init = True
        self.action_status = ActionStatus.INIT
        self.bezier_status = ActionStatus.INIT
        self.bezier_return_status = ActionStatus.INIT

        self.go_bezier = goBezier.GoBezierWorld(target_world, back_dist, adjust_dist_for_curvature_limit,
                                                min_ahead_dist, is_backwards, is_hold_dir, max_speed, max_accele,
                                                max_decele, decele_dist,
                                                curvature_limit, path_dist_accuracy, path_angle_accuracy)
        self.go_bezier_return = goBezier.GoBezierWorldReturn(not is_backwards)

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

        if self.bezier_status in (ActionStatus.INIT, ActionStatus.RUNNING):
            self.bezier_status = self.go_bezier.run()
            debug_trace(f"bezier_status={self.bezier_status}")
        elif self.bezier_status == ActionStatus.FAILED:
            self.action_status = ActionStatus.FAILED
        elif self.bezier_status == ActionStatus.FINISHED:
            if self.bezier_return_status in (ActionStatus.INIT, ActionStatus.RUNNING):
                self.bezier_return_status = self.go_bezier_return.run()
                debug_trace(f"bezier_return_status={self.bezier_return_status}")
            elif self.bezier_return_status == ActionStatus.FAILED:
                self.action_status = ActionStatus.FAILED
            elif self.bezier_return_status == ActionStatus.FINISHED:
                self.action_status = ActionStatus.FINISHED
        time.sleep(0.1)


class GoBezier(BaseAction):
    """执行行走贝塞尔曲线到达取货点"""

    def __init__(self, target_world, back_dist=0.0, adjust_dist_for_curvature_limit=2, min_ahead_dist=0.0,
                 is_backwards=False, is_hold_dir=None,
                 max_speed=0.3, max_accele=0.3, max_decele=0.2, decele_dist=0.1, curvature_limit=1.3,
                 path_dist_accuracy=0.01, path_angle_accuracy=0.05):
        super().__init__()

        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.init = True
        self.action_status = ActionStatus.INIT
        self._last_status = None
        self.target_world = target_world
        self.go_bezier = goBezier.GoBezierWorld(target_world, back_dist, adjust_dist_for_curvature_limit,
                                                min_ahead_dist,
                                                is_backwards, is_hold_dir, max_speed, max_accele, max_decele,
                                                decele_dist,
                                                curvature_limit, path_dist_accuracy, path_angle_accuracy)

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            debug_trace(f"[NAV] Bezier nav start target=({self.target_world[0]:.2f}, {self.target_world[1]:.2f})")

        if self.action_status in (ActionStatus.INIT, ActionStatus.RUNNING):
            self.action_status = self.go_bezier.run()

        # 只在状态变化时输出
        if self.action_status != self._last_status:
            self._last_status = self.action_status
            if self.action_status == ActionStatus.FINISHED:
                debug_trace(f"[NAV] Bezier nav done")
            elif self.action_status == ActionStatus.FAILED:
                debug_trace(f"[NAV] Bezier nav failed")

        time.sleep(0.1)

        j.report_info["GoBezier"] = {
            "actionStatus": self.action_status,
            "targetWorld": self.go_bezier.target_world,
            "backDist": self.go_bezier.back_dist,
            "adjustDistForCurvatureLimit": self.go_bezier.adjust_dist_for_curvature_limit,
            "minAheadDist": self.go_bezier.min_ahead_dist,
            "isBackwards": self.go_bezier.is_backwards,
            "isHoldDir": self.go_bezier.is_hold_dir,
            "maxSpeed": self.go_bezier.max_speed,
            "maxAccele": self.go_bezier.max_accele,
            "maxDecele": self.go_bezier.max_decele,
            "deceleDist": self.go_bezier.decele_dist,
            "curvatureLimit": self.go_bezier.curvature_limit,
            "pathDistAccuracy": self.go_bezier.path_dist_accuracy,
            "pathAngleAccuracy": self.go_bezier.path_angle_accuracy,
        }
        Module.reportInfo(j.report_info)


class GoBezierReturn(BaseAction):
    """执行行走贝塞尔曲线到达取货点"""

    def __init__(self, is_backwards=True, is_hold_dir=None, max_speed=0.3, max_accele=0.3, max_decele=0.7,
                 decele_dist=0.1):
        super().__init__()

        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_bezier_return = goBezier.GoBezierWorldReturn(is_backwards, is_hold_dir, max_speed, max_accele,
                                                             max_decele, decele_dist)

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

        if self.action_status in (ActionStatus.INIT, ActionStatus.RUNNING):
            self.action_status = self.go_bezier_return.run()
        debug_trace(f"bezier_return_status={self.action_status}")
        time.sleep(0.1)


class RecShelf(BaseAction):
    """识别货架"""

    def __init__(self, shelf_file, action_name="RecShelf", recognition_region=None, side="A", is_backwards=False):
        super().__init__(action_name)

        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.action_status = ActionStatus.INIT
        self.recfile = shelf_file
        self.attempts = 0
        self.max_attempts = 10
        self.do_rec = False
        self.side = side
        self.is_backwards = is_backwards
        Recognize.resetRec()
        # 识别区域：优先使用传入参数，否则根据车头/车尾选择默认值
        default_region_front = {
            "points": [{"x": 0.5, "y": -1.74}, {"x": 2.86, "y": -1.74},
                       {"x": 2.86, "y": 1.59}, {"x": 0.5, "y": 1.59}],
            "shape": "rectangle"
        }
        default_region_rear = {
            "points": [{"x": 0.12, "y": 1.33}, {"x": -2.09, "y": 1.33},
                       {"x": -2.09, "y": -1.76}, {"x": 0.12, "y": -1.76}],
            "shape": "rectangle"
        }
        default_region = default_region_rear if self.is_backwards else default_region_front
        self.recognitionRegion = recognition_region if recognition_region is not None else default_region
        self.report_info = {}

    def run(self, j: Jack):
        self.action_status = ActionStatus.RUNNING
        Trace.log("recognizing the shelf")
        rec_status = Recognize.getRecStatus()
        Trace.log(f"{rec_status=}")
        # ===== 3.5.4.x识别 =====
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            Trace.log(f"{rec_result=}")
            Recognize.resetRec()
            Trace.log(f"rec_result={rec_result}")
            reco_list = rec_result.get('recoList', [])
            if not reco_list:
                Trace.log("RecShelf: recoList is empty, retrying")
                self.do_rec = False
            else:
                reco = reco_list[0]
                if not reco.get('valid', False):
                    Trace.log("RecShelf: recognition result is invalid (valid=False), retrying")
                    self.do_rec = False
                else:
                    world_result = reco.get('worldResult', {})
                    rec_x = world_result['x']
                    rec_y = world_result['y']
                    rec_yaw = world_result['yaw']
                    rec_yaw = (rec_yaw + math.pi) % (2 * math.pi) - math.pi
                    rec_x_y_yaw = [rec_x, rec_y, rec_yaw]
                    Trace.log(f"{rec_x_y_yaw=}")
                    j.rec_result = rec_x_y_yaw
                    self.action_status = ActionStatus.FINISHED
        elif rec_status in (3, -1):
            if Timer.delay(0.05):
                self.attempts += 1

                if self.attempts > self.max_attempts:
                    self.action_status = ActionStatus.FAILED
                    Navigation.setTaskError("53357", "识别重试次数超限，请检查识别距离或识别传感器是否正常")
                else:
                    Recognize.resetRec()
                    self.do_rec = False
        elif rec_status == 0:
            self.do_rec = True
            Recognize.doRec(self.recfile, json.dumps(self.recognitionRegion), self.side)
        j.report_info["RecShelf"] = {
            "actionStatus": self.action_status,
            "recResult": j.rec_result,
            "recFile": self.recfile,
            "recStatus": rec_status,
            "recTimes": self.attempts
        }
        Module.reportInfo(j.report_info)


class RecTargetObs(BaseAction):
    """识别货架"""

    def __init__(self, device_name):
        super().__init__()
        self.opt_info = f"{self.__class__.__name__}{{device_name={device_name}}}"
        self.action_status = ActionStatus.INIT
        self.device_name = device_name

    def run(self, j: Jack):
        self.action_status = ActionStatus.RUNNING
        Recognize.resetRec()
        Recognize.recTargetObs(self.device_name, 0, 0, 0, 0, 0, 0, 0)

        j.report_info["RecTargetObs"] = {
            "actionStatus": self.action_status
        }
        Module.reportInfo(j.report_info)


class GetApPosAdjustedViaPgv(BaseAction):
    # 路径导航  导航到站点
    def __init__(self, ap_id=None, dist=0, back_dist=0, ahead_dist=0.7):
        super().__init__("GetApPosAdjustedViaPgv")
        self.opt_info = f"{self.__class__.__name__}{{ap_id={ap_id}, dist={dist}}}"
        self.pgv_info = []
        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_args = dict()
        self.dist = dist  # 终点前的补偿距离
        self.ap_id = ap_id
        self.target_world_pos = []
        self.back_dist = back_dist
        self.ahead_dist = ahead_dist

    def run(self, j: Jack):

        self.action_status = ActionStatus.RUNNING
        if self.init:
            self.init = False
            # 获取AP点坐标
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
            self.target_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置

            # 获取qrcode的偏移数值，并补偿到终点坐标中
            self.pgv_info[0] = j.code_info["tag_diff_x"]  # 上视pgv读到的货架在车体坐标系偏移,用于补偿货架机械偏差
            self.pgv_info[1] = j.code_info["tag_diff_y"]
            self.pgv_info[2] = j.code_info["tag_diff_angle"]
            if abs(self.pgv_info[0]) > 0.02 and abs(self.pgv_info[1]) > 0.02:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError("53359", "PGV偏差超限(>0.02m)，请检查货物二维码偏移或调整AP点位置")

            else:
                # 将车体终点位置，加入二维码的偏差补偿
                self.target_world_pos = pos2World(self.pgv_info, [self.target_world_pos[0], self.target_world_pos[1],
                                                                  self.target_world_pos[2]])
                j.ap_world_pos = self.target_world_pos
                self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class GetPGVData(BaseAction):
    """获取二维码资料"""

    def __init__(self, scan_device: str):
        super().__init__("GetPGVData")
        self.opt_info = f"{self.__class__.__name__}{{scan_device={scan_device}}}"
        self.action_status = ActionStatus.INIT
        self.init = True
        self.count = 0
        self.max_rec_num = 15
        self.scan_device = scan_device  # 设备名称字符串（来自 BIND_TYPE）
        self.is_DMT_detected = False
        self.tag_value = ""
        self.tag_diff_x = 0
        self.tag_diff_y = 0
        self.tag_diff_angle = 0
        self.codeScannerInfo = None

    def run(self, j: Jack):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = False

        pgv_data = CodeScanner.getCodeScanners()

        chosen_pgv = None

        # 按设备 key 精确匹配；若设备名为空则回退到原有 isUpside 逻辑
        for pgv in pgv_data:
            if self.scan_device:
                device_key = getattr(pgv.codeScannerInfo, "key", None) or getattr(pgv, "key", None)
                if device_key == self.scan_device:
                    chosen_pgv = pgv
                    break
            else:
                # 兼容旧逻辑：scan_device 未设置时默认选下视 PGV
                if hasattr(pgv.codeScannerInfo, "isUpside") and not pgv.codeScannerInfo.isUpside:
                    chosen_pgv = pgv
                    break

        # 如果没找到对应的PGV，打印可用设备详细信息辅助排查（仅首次）
        if chosen_pgv is None:
            if self.count == 0:
                for i, pgv in enumerate(pgv_data):
                    pgv_attrs = {k: v for k, v in vars(pgv).items() if not k.startswith('_')} if hasattr(pgv,
                                                                                                         '__dict__') else str(
                        pgv)
                    info_attrs = {}
                    if hasattr(pgv, 'codeScannerInfo') and pgv.codeScannerInfo is not None:
                        info_attrs = {k: v for k, v in vars(pgv.codeScannerInfo).items() if
                                      not k.startswith('_')} if hasattr(pgv.codeScannerInfo, '__dict__') else str(
                            pgv.codeScannerInfo)
                    Trace.log(f"GetPGVData: pgv[{i}] attrs={pgv_attrs}, codeScannerInfo attrs={info_attrs}")
                Trace.log(f"GetPGVData: scan_device='{self.scan_device}' not found in above devices!")
        else:
            self.tag_value = chosen_pgv.tagValue
            self.tag_diff_x = chosen_pgv.tagDiffX
            self.tag_diff_y = chosen_pgv.tagDiffY
            self.tag_diff_angle = chosen_pgv.tagDiffAngle
            self.is_DMT_detected = chosen_pgv.isDMTDetected
            self.codeScannerInfo = chosen_pgv.codeScannerInfo

        # 输出结构
        is_upside = False
        if self.codeScannerInfo is not None:
            is_upside = getattr(self.codeScannerInfo, "isUpside", False)
        j.code_info = {
            "tag_value": self.tag_value,
            "is_DMT_detected": self.is_DMT_detected,
            "tag_diff_x": self.tag_diff_x,
            "tag_diff_y": self.tag_diff_y,
            "tag_diff_angle": self.tag_diff_angle,
            "scanDevice": self.scan_device,
            "isUpside": is_upside
        }

        # 判断二维码识别逻辑
        if self.is_DMT_detected and self.tag_value != "":
            debug_trace(
                f"read code success: {self.tag_value} (scan_device={self.scan_device})"
            )
            self.action_status = ActionStatus.FINISHED
        else:
            self.count += 1
            if self.count >= self.max_rec_num:
                Navigation.setTaskError("53358", f"PGV二次调整识别超限({self.count}次)，请检查PGV相机或二维码位置")

        # 上报
        j.report_info["GetPGVData"] = {
            "actionStatus": self.action_status,
            "codeInfo": j.code_info
        }
        Module.reportInfo(j.report_info)


class GoPolyline(BaseAction):
    """折线导航 """

    def __init__(self, world_target, min_ahead_dist=0, ahead_dist=0, back_dist=0, max_speed=0.5, max_angle=0.5,
                 dec_dist=1):
        super().__init__()
        self.action_status = ActionStatus.INIT
        self.goal = world_target
        self.back_dist = back_dist
        self.ahead_dist = ahead_dist
        self.min_ahead_dist = min_ahead_dist
        self.init = False
        self._log_counter = 0
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

    def run(self, f):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            pos = Loc.getData()
            Trace.log(f"[GoPolyline] start pos: x={pos['x']:.4f}, y={pos['y']:.4f}, angle={pos['angle']:.4f}")
            Trace.log(f"[GoPolyline] goal: x={self.goal[0]:.4f}, y={self.goal[1]:.4f}, yaw={self.goal[2]:.4f}")
            Trace.log(f"[GoPolyline] back_dist={self.back_dist}, min_ahead_dist={self.min_ahead_dist}, ahead_dist={self.ahead_dist}")
            Navigation.resetGoForkPath(self.goal[0], self.goal[1], self.goal[2],
                                       self.back_dist, self.min_ahead_dist, self.ahead_dist)
            Navigation.goForkUseStraightLine()  # 走折线
            Trace.log("[GoPolyline] resetGoForkPath + goForkUseStraightLine done")
        self.action_status = Navigation.goForkPath()
        self._log_counter += 1
        # 每10个周期打印一次实时位置和状态
        if self._log_counter % 10 == 0:
            pos = Loc.getData()
            speed = NavSpeed.getSpeeds()
            Trace.log(f"[GoPolyline] running: x={pos['x']:.4f}, y={pos['y']:.4f}, angle={pos['angle']:.4f}, "
                      f"status={self.action_status}, speed={speed}")
        if self.action_status == ActionStatus.FINISHED:
            pos = Loc.getData()
            Trace.log(f"[GoPolyline] finished at: x={pos['x']:.4f}, y={pos['y']:.4f}, angle={pos['angle']:.4f}")
        elif self.action_status == ActionStatus.FAILED:
            Trace.log("[GoPolyline] FAILED")

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.init = False

class PGVSecondaryAdjust(BaseAction):
    """
    PGV二次调整（singleCode / codeNumber 模式）。

    根据文档 §3.5 policy 参数结构，将上层配置翻译成 goPGVRun 底层参数。

    singleCode 模式参数映射（文档附录）：
      angleAdjustType:
        "parallelToCode"          → pgvAdjust180 = True
        "verticalToCode"          → pgvAdjust90  = True
        "verticalOrParallelToCode"→ pgvAdjust90  = True
        "ignoreAngle"             → pgvAdjustXY  = True
      positionAdjustType:
        "frontAndBack" + ignoreAngle  → pgvXAdjust      = True
        "frontAndBack" + other        → pgvXAngleAdjust  = True
        "multiLine"                   → pgvAdjustCx/pgvAdjustDist/pgvAdjustCy
                                        （从 adjustRegion 计算）
                                        + lineAngleThreshold 传入 policy

    codeNumber 模式参数映射（文档附录）：
      自动设置 pgvCodeStrip = True
      angleAdjustType:
        "parallelToCode"           → pgvXAngleAdjust + pgvAdjust180
        "verticalToCode"           → pgvXAngleAdjust + pgvAdjust90
        "verticalOrParallelToCode" → pgvXAngleAdjust + pgvAdjust90
        "ignoreAngle"              → pgvXAdjust
    """

    def __init__(self,
                 code_adjust_type: str = "singleCode",
                 scan_device: str = "",
                 angle_adjust_type: str = "parallelToCode",
                 position_adjust_type: str = "frontAndBack",
                 code_number: str = "",
                 line_angle_threshold: float = 0.1,
                 adjust_region: str = "",
                 pgv_spin: bool = True,
                 pgv_reach_dist: float = 0.02,
                 pgv_reach_angle: float = 1.0,
                 useTCP: bool = False):
        super().__init__("PGVSecondaryAdjust")
        self.opt_info = (f"{self.__class__.__name__}{{"
                         f"code_adjust_type={code_adjust_type}, "
                         f"scan_device={scan_device}, "
                         f"angle_adjust_type={angle_adjust_type}, "
                         f"position_adjust_type={position_adjust_type}}}")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.adjust_param = dict()

        self.code_adjust_type = code_adjust_type
        self.scan_device = scan_device
        self.angle_adjust_type = angle_adjust_type
        self.position_adjust_type = position_adjust_type
        self.code_number = code_number
        self.line_angle_threshold = line_angle_threshold
        self.adjust_region = adjust_region
        self.pgv_spin = pgv_spin
        self.pgv_reach_dist = pgv_reach_dist
        self.pgv_reach_angle = pgv_reach_angle
        self.useTCP = useTCP

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.reset()
            self._build_static_params(j)

        # multiLine 模式：每帧刷新圆心偏移（来自当前读码偏差）
        if (self.code_adjust_type == "singleCode"
                and self.position_adjust_type == "multiLine"):
            self._refresh_multiline_cx(j.code_info.get("tag_diff_x", 0.0))

        self.action_status = Navigation.goPGVRun(self.adjust_param)

        j.report_info["PGVSecondaryAdjust"] = {
            "actionStatus": self.action_status,
            "adjustParam": self.adjust_param,
            "codeInfo": j.code_info
        }
        Module.reportInfo(j.report_info)

    # ------------------------------------------------------------------
    # 内部：一次性构建静态参数（init 阶段调用）
    # ------------------------------------------------------------------
    def _build_static_params(self, j: Jack):
        """将上层 policy 翻译成 goPGVRun 底层 JSON 参数（不含每帧刷新量）。"""
        p = self.adjust_param

        # ---- 随动锁叉 ----
        p['spin'] = self.pgv_spin

        # ---- 是否使用TCP ----
        p['useTCP'] = self.useTCP

        # ---- 精度 ----
        p['pgvReachDist'] = self.pgv_reach_dist
        p['pgvReachAngle'] = self.pgv_reach_angle  # 单位 deg

        # ---- 扫码设备 → R2ADP / R2AUP ----
        # 根据 GetPGVData 阶段获取的 codeScannerInfo.isUpside 判断上视/下视
        # 文档：R2AUP = 上视PGV，R2ADP = 下视PGV
        is_upside = j.code_info.get("isUpside", False)
        if is_upside:
            p['R2AUP'] = True
            p['R2ADP'] = False
        else:
            p['R2AUP'] = False
            p['R2ADP'] = True
        Trace.log(f"PGVSecondaryAdjust: scan_device='{self.scan_device}', "
                  f"isUpside={is_upside} -> R2AUP={p['R2AUP']}, R2ADP={p['R2ADP']}")

        if self.code_adjust_type == "singleCode":
            self._build_singlecode_params()
        elif self.code_adjust_type == "codeNumber":
            self._build_codestrip_params()
        else:
            Trace.log(f"PGVSecondaryAdjust: unknown codeAdjustType='{self.code_adjust_type}', "
                      f"falling back to singleCode")
            self._build_singlecode_params()

        Trace.log(f"PGVSecondaryAdjust: built params: {json.dumps(self.adjust_param, indent=2)}")

    def _build_singlecode_params(self):
        """singleCode 模式参数构建（文档 §2 singleCode）。"""
        p = self.adjust_param

        # codeNumber（可选）：纯数字字符串才生效 → pgvDownCode
        if self.code_number and self.code_number.isdigit():
            p['pgvDownCode'] = int(self.code_number)

        # ---- angleAdjustType ----
        angle = self.angle_adjust_type
        if angle == "parallelToCode":
            p['pgvAdjust180'] = True
        elif angle in ("verticalToCode", "verticalOrParallelToCode"):
            p['pgvAdjust90'] = True
        elif angle == "ignoreAngle":
            p['pgvAdjustXY'] = True

        # ---- positionAdjustType ----
        pos = self.position_adjust_type
        if pos == "frontAndBack":
            # ignoreAngle → pgvXAdjust；其他 → pgvXAngleAdjust
            if angle == "ignoreAngle":
                p['pgvXAdjust'] = True
            else:
                p['pgvXAngleAdjust'] = True

        elif pos == "multiLine":
            # adjustRegion 解析：取第一个元素 points 数组，计算 X 最大/最小值
            cx, dist = self._parse_adjust_region(self.adjust_region)
            p['pgvAdjustCx'] = cx
            p['pgvAdjustDist'] = dist
            p['pgvAdjustCy'] = 0.0
            # lineAngleThreshold: 控制来回运动时的最大旋转角度范围
            # UI 单位为 deg，底层接口需要 rad
            p['lineAngleThreshold'] = math.radians(self.line_angle_threshold)

    def _build_codestrip_params(self):
        """codeNumber（码带）模式参数构建（文档 §3 codeNumber）。"""
        p = self.adjust_param

        # 码带模式核心标识
        p['pgvCodeStrip'] = True

        angle = self.angle_adjust_type
        if angle == "parallelToCode":
            p['pgvXAngleAdjust'] = True
            p['pgvAdjust180'] = True
        elif angle in ("verticalToCode", "verticalOrParallelToCode"):
            p['pgvXAngleAdjust'] = True
            p['pgvAdjust90'] = True
        elif angle == "ignoreAngle":
            p['pgvXAdjust'] = True

    # ------------------------------------------------------------------
    # 内部：multiLine 每帧刷新圆心 X
    # ------------------------------------------------------------------
    def _refresh_multiline_cx(self, tag_diff_x: float):
        """multiLine 模式下每帧用当前读码 X 偏差更新 pgvAdjustCx。"""
        self.adjust_param['pgvAdjustCx'] = tag_diff_x

    # ------------------------------------------------------------------
    # 内部：解析 adjustRegion JSON 字符串 → (cx, dist)
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_adjust_region(region_str: str):
        """
        解析 adjustRegion JSON 字符串，返回 (pgvAdjustCx, pgvAdjustDist)。

        文档逻辑：
          max_x = max(points[*].x)
          min_x = min(points[*].x)
          pgvAdjustCx   = (max_x + min_x) / 2
          pgvAdjustDist = |max_x - min_x| / 2
        """
        if not region_str:
            Trace.log("PGVSecondaryAdjust: adjustRegion is empty, using (cx=0, dist=0.2)")
            return 0.0, 0.2

        try:
            region_data = json.loads(region_str)
            points = region_data[0].get("points", [])
            x_values = [pt["x"] for pt in points]
            max_x = max(x_values)
            min_x = min(x_values)
            cx = (max_x + min_x) / 2.0
            dist = abs(max_x - min_x) / 2.0
            Trace.log(f"PGVSecondaryAdjust: adjustRegion parsed → cx={cx:.4f}, dist={dist:.4f}")
            return cx, dist
        except Exception as e:
            Trace.log(f"PGVSecondaryAdjust: adjustRegion parse error: {e}, using (cx=0, dist=0.2)")
            return 0.0, 0.2

    def reset(self):
        debug_trace("reset PGV secondary adjustment")
        self.action_status = ActionStatus.RUNNING
        Navigation.resetGoPGV()


class PGVCodeStripAdjust(BaseAction):
    """
    PGV码带调整（codeNumber模式）

    """

    def __init__(self, angle_adjust_type: str = "parallelToCode",
                 pgv_reach_dist: float = 0.02, pgv_reach_angle: float = 1.0,
                 use_target_position: bool = False,
                 r2ad_x: float = 0.0, r2ad_y: float = 0.0, r2ad_theta: float = 0.0):
        super().__init__("PGVCodeStripAdjust")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.adjust_param = dict()

        # 角度调整类型
        self.angle_adjust_type = angle_adjust_type
        # 精度参数
        self.pgv_reach_dist = pgv_reach_dist
        self.pgv_reach_angle = pgv_reach_angle
        # 目标位置参数
        self.use_target_position = use_target_position
        self.r2ad_x = r2ad_x
        self.r2ad_y = r2ad_y
        self.r2ad_theta = r2ad_theta

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.reset()
            self._parse_angle_adjust_type()

        # 获取当前偏差值（从PGV读码获取）
        current_diff_x = j.code_info.get("tag_diff_x", 0)
        current_diff_y = j.code_info.get("tag_diff_y", 0)
        current_diff_angle = j.code_info.get("tag_diff_angle", 0)

        # 始终传入当前偏差值
        self.adjust_param['pgvAdjustCx'] = current_diff_x
        self.adjust_param['pgvAdjustCy'] = current_diff_y

        # 设置精度参数
        self.adjust_param['pgvReachDist'] = self.pgv_reach_dist
        self.adjust_param['pgvReachAngle'] = self.pgv_reach_angle

        # 如果启用目标位置，添加R2AD参数
        if self.use_target_position:
            self.adjust_param['R2ADx'] = self.r2ad_x
            self.adjust_param['R2ADy'] = self.r2ad_y
            self.adjust_param['R2ADtheta'] = self.r2ad_theta
            Trace.log(
                f"PGVCodeStripAdjust: Target position enabled: x={self.r2ad_x}, y={self.r2ad_y}, theta={self.r2ad_theta}")

        Trace.log(
            f"PGVCodeStripAdjust: Current offset x={current_diff_x}, y={current_diff_y}, angle={current_diff_angle}")
        Trace.log(f"PGVCodeStripAdjust: Running with params: {json.dumps(self.adjust_param, indent=2)}")

        # 调用底层接口
        self.action_status = Navigation.goPGVRun(self.adjust_param)

        # 上报信息
        j.report_info["PGVCodeStripAdjust"] = {
            "actionStatus": self.action_status,
            "codeInfo": j.code_info,
            "angleAdjustType": self.angle_adjust_type,
            "useTargetPosition": self.use_target_position,
            "targetPosition": {
                "R2ADx": self.r2ad_x,
                "R2ADy": self.r2ad_y,
                "R2ADtheta": self.r2ad_theta
            } if self.use_target_position else None
        }
        Module.reportInfo(j.report_info)

    def _parse_angle_adjust_type(self):
        """根据 angleAdjustType 设置底层参数"""
        # 码带模式核心参数
        self.adjust_param['pgvCodeStrip'] = True

        # 使用下视PGV（码带在地面）
        self.adjust_param['R2ADP'] = True
        self.adjust_param['R2AUP'] = False

        # 根据 angleAdjustType 设置角度参数
        if self.angle_adjust_type == "parallelToCode":
            # 机器人平行于码带方向
            self.adjust_param['pgvXAngleAdjust'] = True
            self.adjust_param['pgvAdjust180'] = True
            Trace.log("PGVCodeStripAdjust: parallelToCode -> pgvXAngleAdjust + pgvAdjust180")
        elif self.angle_adjust_type == "verticalToCode":
            # 机器人垂直于码带方向
            self.adjust_param['pgvXAngleAdjust'] = True
            self.adjust_param['pgvAdjust90'] = True
            Trace.log("PGVCodeStripAdjust: verticalToCode -> pgvXAngleAdjust + pgvAdjust90")
        elif self.angle_adjust_type == "ignoreAngle":
            # 忽略角度，仅调整位置
            self.adjust_param['pgvXAdjust'] = True
            Trace.log("PGVCodeStripAdjust: ignoreAngle -> pgvXAdjust only")

    def reset(self):
        Trace.log("Reset PGV code strip adjustment")
        self.action_status = ActionStatus.RUNNING
        Navigation.resetGoPGV()


class ActionStatus(IntEnum):
    """ 动作运行状态枚举，对标 ActionStatus """
    INIT = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


# ============================================================================
# 脚本内置动作模板定义
# ============================================================================

# 添加 "jackLoad" 动作模板
param_loader.addAction(
    action_name="jackLoad",
    policy = None,
    args={
        "operation": "jackLoad",
        "operation.jackLoad.endHeight": 0.06,
        "operation.jackLoad.recFile": "",
        "operation.jackLoad.recognize": "on",
        "operation.jackLoad.recognize.on.insertShelfDir": "A",
        "operation.jackLoad.howGoSite": "bezier",
        "operation.jackLoad.isSecondaryAdjust": "on",
        "operation.jackLoad.atSite": False,
    },
    config={}
)

# 添加 "jackUnload" 动作模板
param_loader.addAction(
    action_name="jackUnload",
    policy = None,
    args={
        "operation": "jackUnload",
    },
    config={}
)

# 添加 "jackHeight" 动作模板
param_loader.addAction(
    action_name="jackHeight",
    policy={},
    args={
        "operation": "jackHeight",
        "operation.jackHeight.endHeight": 0.06,
    },
    config={}
)

# 添加 "PGVSecondaryAdjust" 动作模板
param_loader.addAction(
    action_name="PGVSecondaryAdjust",
    policy=None,
    args={
        "operation": "PGVSecondaryAdjust",
    },
    config={}
)

# 保存动作模板到文件
param_loader.saveAction()


def main():
    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    validator = ParamValidator(InputParams.builder.toDict())
    j = Jack()
    # 每次脚本启动都重置标零状态，确保开机标零一次
    if config_params.auto_calib_enable:
        jack_calib_manager.set_calib_done(False)

    while True:
        # ========== 边走边动：更新moveTask参数 ==========
        j.update_move_task_params()

        status = j.status
        Module.setStatus(status)
        # 打印数据
        j.set_info()

        # 脚本任务状态管理
        if j.event_safe_move_check:
            j.safe_move_check()

        # 启动自动标零（DB=False 时每周期轮询，完成后自动停止）
        if config_params.auto_calib_enable and not jack_calib_manager.is_calib_done():
            j.run_startup_calib()

        if status == ScriptStatus.NONE:
            # ========== 边走边动：预动作执行（保持NONE状态） ==========
            if j.pre_action_mode:
                j.run_pre_action()
                # 预动作模式下不处理其他任务，但保持NONE状态让导航继续
            # ========== 常规流程 ==========
            else:
                # 优先使用边走边动结果参数，否则使用Module.getTaskArgs()
                input_params = j.result or Module.getTaskArgs()
                if input_params:
                    try:
                        if "script" in input_params and "args" in input_params["script"]:
                            input_params = input_params["script"]["args"]

                        # 精简的任务参数输出
                        operation = input_params.get("operation", "unknown")
                        debug_trace(f"[TASK] {operation} Mission Start")
                        debug_print(f"  Input Params: {json.dumps(input_params, indent=2, ensure_ascii=False)}")

                        # 验证参数
                        validated_params = validator.validate(input_params)
                        debug_trace(f"[TASK] Input params check ok")

                        j._init_args(validated_params)
                    except ValueError as e:
                        Trace.log(f"[ERROR] Input params check fail: {e}")
                        Navigation.setTaskError("53356", f"输入参数校验失败: {e}")

        elif status == ScriptStatus.RUNNING:
            j.run()
            # 确保状态同步
            Module.setStatus(j.status)
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            j.action_id = 0
            j.action_list = []
            j.operation_init = False
            j.result = None  # 清空 result 防止完成后重复触发
            # 重置边走边动状态
            j.pre_action_mode = False
            j.pre_action_completed = False
            j.pre_action_step = [False] * 5
            j.at_final_loc = False
            j.final_loc = None
            j.final_bin_task = None
            j.status = ScriptStatus.NONE

        time.sleep(0.1)


if __name__ == '__main__':
    main()

