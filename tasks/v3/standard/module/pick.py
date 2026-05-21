# -*- coding: utf-8 -*-
# @Date : 2026/5/21
# @Author : zhaopengfei
# @Coding : none
# @Update : 修复bug

import json
import math
import time
from enum import IntEnum
from syspy.utils.time import Timer

start_time = time.time()
from datetime import datetime
from syspy import (Module, Logger, Motor, Navigation, Loc, Recognize, Di,
                   CodeScanner, ScriptStatus, Trace, NavSpeed, Controller, LevelDB, Container)
from syspy.lib.module import pos2Base, pos2World, ModuleBase, SafeMoveStatus
from standard import goPath, goBezier
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ScriptParam

param_loader = ScriptParam(__file__)
from syspy.lib.robot import RobotParam
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
        if args:
            first_arg = f"{timestamp} {args[0]}"
            Trace.log(first_arg, *args[1:], **kwargs)
        else:
            Trace.log(timestamp, **kwargs)


# ============================================================================
# 顶升次数统计管理类
# ============================================================================
class JackCountManager:
    """
    顶升次数统计管理器
    - jackTotalCount: 顶升累计次数
    - jackTodayCount: 顶升今日累计次数
    - jackLastDate: 上次更新日期（用于今日次数自动重置）
    """

    KEY_TOTAL_COUNT = "jackTotalCount"
    KEY_TODAY_COUNT = "jackTodayCount"
    KEY_LAST_DATE = "jackLastDate"

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
        try:
            self._db = LevelDB("run")
            total_count = self._db.get(self.KEY_TOTAL_COUNT, "int")
            if total_count is None:
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
# 货架尺寸优先级管理器
# ============================================================================
class RackSizeManager:
    """
    P300 货架尺寸优先级管理器

    管理多个货架尺寸识别文件的优先级排序策略：

    - 冷启动阶段（所有尺寸均无 LastUsedAt）：UpdatedAt 倒序 > CreatedAt 倒序
    - 稳定运行阶段（至少一个有 LastUsedAt）：LastUsedAt 倒序 > UpdatedAt 倒序 > CreatedAt 倒序

    规则说明：
    - LastUsedAt 仅在取放货任务**成功完成**后写入（非仅识别成功）
    - 货架尺寸参数修改（实质变更）后，清空对应的 LastUsedAt，更新 UpdatedAt
    - 识别全部失败时，上报 RACK_NOT_MATCHED，不写入任何 LastUsedAt
    - 最多支持 5 个货架尺寸（由 ConfigParams.rack_size_files 控制）
    """

    KEY_RACK_METADATA = "rackSizeMetadata"  # LevelDB 中存储元数据的键

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
        try:
            self._db = LevelDB("run")
            existing = self._db.get(self.KEY_RACK_METADATA, "str")
            if existing is None:
                self._db.add(self.KEY_RACK_METADATA, json.dumps({}), False)
                debug_trace("RackSizeManager: 数据库初始化完成")
        except Exception as e:
            Trace.log(f"RackSizeManager: 数据库初始化失败: {e}")
            self._db = None

    def _load_metadata(self) -> dict:
        """加载所有货架尺寸元数据 {recfile: {createdAt, updatedAt, lastUsedAt}}"""
        if self._db is None:
            return {}
        try:
            data = self._db.get(self.KEY_RACK_METADATA, "str")
            if data:
                return json.loads(data)
        except Exception as e:
            Trace.log(f"RackSizeManager: 加载元数据失败: {e}")
        return {}

    def _save_metadata(self, metadata: dict):
        """保存元数据到 LevelDB"""
        if self._db is None:
            return
        try:
            self._db.put(self.KEY_RACK_METADATA, json.dumps(metadata))
        except Exception as e:
            Trace.log(f"RackSizeManager: 保存元数据失败: {e}")

    def register_recfiles(self, recfiles: list):
        """
        注册/同步识别文件列表（脚本启动或配置变更时调用）。
        新增文件写入 CreatedAt；已有文件保留原有元数据不覆盖。
        """
        now_str = datetime.now().isoformat()
        metadata = self._load_metadata()
        changed = False
        for recfile in recfiles:
            if not recfile:
                continue
            if recfile not in metadata:
                metadata[recfile] = {
                    "createdAt": now_str,
                    "updatedAt": None,
                    "lastUsedAt": None
                }
                changed = True
        if changed:
            self._save_metadata(metadata)
            debug_trace(f"RackSizeManager: 注册 {len(recfiles)} 个识别文件")

    def get_sorted_recfiles(self, recfiles: list) -> list:
        """
        返回按优先级排序后的 rec 文件列表。

        冷启动阶段排序：
          P1（有 UpdatedAt）→ UpdatedAt 倒序
          P2（仅有 CreatedAt）→ CreatedAt 倒序

        稳定运行阶段排序：
          P1（有 LastUsedAt）→ LastUsedAt 倒序
          P2（无 LastUsedAt，有 UpdatedAt）→ UpdatedAt 倒序
          P3（仅有 CreatedAt）→ CreatedAt 倒序
        """
        valid_files = [f for f in recfiles if f]
        if not valid_files:
            return []

        metadata = self._load_metadata()
        file_meta = []
        for f in valid_files:
            meta = metadata.get(f, {"createdAt": None, "updatedAt": None, "lastUsedAt": None})
            file_meta.append((f, meta))

        # 判断阶段：所有文件均无 lastUsedAt → 冷启动
        is_cold_start = all(m.get("lastUsedAt") is None for _, m in file_meta)

        if is_cold_start:
            def cold_key(item):
                _, m = item
                updated = m.get("updatedAt") or ""
                created = m.get("createdAt") or ""
                # (优先级, 时间戳) 均取倒序
                if updated:
                    return (1, updated)
                return (0, created)

            sorted_files = sorted(file_meta, key=cold_key, reverse=True)
            debug_trace(f"RackSizeManager: [冷启动] 排序 {len(sorted_files)} 个文件")
        else:
            def stable_key(item):
                _, m = item
                last_used = m.get("lastUsedAt") or ""
                updated = m.get("updatedAt") or ""
                created = m.get("createdAt") or ""
                if last_used:
                    return (2, last_used)
                elif updated:
                    return (1, updated)
                return (0, created)

            sorted_files = sorted(file_meta, key=stable_key, reverse=True)
            debug_trace(f"RackSizeManager: [稳定运行] 排序 {len(sorted_files)} 个文件")

        result = [f for f, _ in sorted_files]
        debug_trace(f"RackSizeManager: 排序结果: {result}")
        return result

    def on_recognition_success(self, recfile: str):
        """
        取放货任务**成功完成**后调用，写入 LastUsedAt。
        注意：仅识别成功还不够，需等整个任务完成后才调用此方法。
        """
        if not recfile:
            return
        now_str = datetime.now().isoformat()
        metadata = self._load_metadata()
        if recfile not in metadata:
            metadata[recfile] = {"createdAt": now_str, "updatedAt": None, "lastUsedAt": now_str}
        else:
            metadata[recfile]["lastUsedAt"] = now_str
        self._save_metadata(metadata)
        debug_trace(f"RackSizeManager: 写入 LastUsedAt for [{recfile}]: {now_str}")
        Trace.log(f"[RACK] LastUsedAt updated: {recfile}")

    def on_recfile_modified(self, recfile: str):
        """
        货架尺寸参数发生**实质变更**后调用，清空 LastUsedAt 并更新 UpdatedAt。
        注意：单纯"打开-保存"不视为修改，不应调用此方法。
        """
        if not recfile:
            return
        now_str = datetime.now().isoformat()
        metadata = self._load_metadata()
        if recfile in metadata:
            metadata[recfile]["lastUsedAt"] = None
            metadata[recfile]["updatedAt"] = now_str
            self._save_metadata(metadata)
            debug_trace(f"RackSizeManager: 清空 LastUsedAt（参数已修改）for [{recfile}]")


# 创建全局实例
rack_size_manager = RackSizeManager()

# --- ConfigParams 类（放在前面） ---

class ConfigParams:
    config = {}
    """配置管理器，用于管理动态配置参数"""
    timeout = None
    jack_motor_speed = None
    jack_min_height = None
    jack_max_height = None
    jack_up_di = None
    jack_zero_di = None

    # Debug开关
    debug_mode = False
    # 货架尺寸识别文件列表（最多5个，按优先级排序后使用）
    rack_size_files = []

    # 导航配置参数（bezier）
    bezier_back_dist = 0.0
    bezier_adjust_dist = 2.0
    bezier_min_ahead_dist = 0.0
    bezier_is_backwards = True
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

    # PGV二次调整配置参数
    pgv_use_which = "useDownPgv"
    pgv_adjust_way = "pgvAdjust90"
    pgv_x_adjust = True
    pgv_x_angle_adjust = True
    pgv_adjust_dist = 0.2
    pgv_reach_dist = 0.02
    pgv_reach_angle = 0.02

    module_type = RobotParam.getDevice("Model-000", "moduleType")
    jack_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.jackMotor")
    motor_func = RobotParam.getDevice(f"{jack_motor_name}", "func")
    reset_by_speed = RobotParam.getDevice(f"{jack_motor_name}", "resetMode")

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
            # 通用配置组
            # ============================================
            with builder.GROUP(key="generalConfig", name="General Configuration",
                               desc="General configuration parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    # Debug开关
                    with builder.CHILD(key="debugMode", name="Debug Mode",
                                       desc="Enable debug mode to show debug tasks and low-frequency parameters"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

            # ============================================
            # 电机配置组
            # ============================================
            with builder.GROUP(key="motorConfig", name="Motor Configuration",
                               desc="Motor related configuration parameters"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 顶升电机速度
                    with builder.CHILD(key="jackMotorSpeed", name="Jack Motor Speed",
                                       desc="Speed of the jack motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.015, min_value=0.001, max_value=0.1)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="jackMinHeight", name="jack Min Height",
                                       desc="The min height of jack motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.minLength"))
                        builder.UNIT("m")
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="jackMaxHeight", name="jack Max Height",
                                       desc="The max height of jack motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.maxLength"))
                        builder.UNIT("m")
                        builder.SINGLESTEP(0.001)

            # ============================================
            # DI配置组
            # ============================================
            with builder.GROUP(key="diConfig", name="DI Configuration", desc="Digital input configuration parameters"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    # 上极限DI
                    with builder.CHILD(key="jackUpDi", name="Jack Up DI",
                                       desc="Upper limit digital input for jack"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE(RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.upLimitDI"))
                    # 零位DI
                    with builder.CHILD(key="jackZeroDi", name="Jack Zero DI",
                                       desc="Zero position digital input for jack"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE(
                            RobotParam.getDevice(f"{jack_motor_name}", f"resetMode.{reset_by_speed}.zeroDI"),
                            min_value=0, max_value=31)

            # ============================================
            # 贝塞尔导航配置组（现场实施后基本不变）
            # ============================================
            with builder.GROUP(key="bezierConfig", name="Bezier Navigation Config",
                               desc="Bezier curve navigation parameters (site-specific, rarely changed)"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="bezierBackDist", name="Back Distance",
                                       desc="Back distance before starting bezier"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierAdjustDist", name="Adjust Distance for Curvature",
                                       desc="Adjust distance for decreasing curvature limit"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(2.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierMinAheadDist", name="Min Ahead Distance",
                                       desc="Minimum ahead distance"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierIsBackwards", name="Is Backwards",
                                       desc="Enable backward mode"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="bezierIsHoldDir", name="Hold Direction",
                                       desc="Whether to hold direction during navigation"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="bezierMaxSpeed", name="Max Speed",
                                       desc="Maximum speed for bezier navigation"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5)
                        builder.UNIT("m/s")
                    with builder.CHILD(key="bezierMaxAccele", name="Max Acceleration",
                                       desc="Maximum acceleration"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3)
                        builder.UNIT("m/s²")
                    with builder.CHILD(key="bezierMaxDecele", name="Max Deceleration",
                                       desc="Maximum deceleration"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.2)
                        builder.UNIT("m/s²")
                    with builder.CHILD(key="bezierDeceleDist", name="Deceleration Distance",
                                       desc="Distance to start deceleration before target"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierCurvatureLimit", name="Curvature Limit",
                                       desc="Curvature limit for bezier path"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.3)
                    with builder.CHILD(key="bezierPathDistAccuracy", name="Path Distance Accuracy",
                                       desc="Position accuracy for path following"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.01)
                        builder.UNIT("m")
                    with builder.CHILD(key="bezierPathAngleAccuracy", name="Path Angle Accuracy",
                                       desc="Angle accuracy for path following"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05)
                        builder.UNIT("rad")

            # ============================================
            # 折线导航配置组（现场实施后基本不变）
            # ============================================
            with builder.GROUP(key="polylineConfig", name="Polyline Navigation Config",
                               desc="Polyline navigation parameters (site-specific, rarely changed)"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="polylineBackDist", name="Back Distance",
                                       desc="Back distance before starting polyline"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylineAheadDist", name="Ahead Distance",
                                       desc="Ahead distance for line angle adjustment"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(2.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylineMinAheadDist", name="Min Ahead Distance",
                                       desc="Minimum ahead distance"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylineIsBackwards", name="Is Backwards",
                                       desc="Enable backward mode"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="polylineIsHoldDir", name="Hold Direction",
                                       desc="Whether to hold direction during navigation"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="polylineMaxSpeed", name="Max Speed",
                                       desc="Maximum speed for polyline navigation"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5)
                        builder.UNIT("m/s")
                    with builder.CHILD(key="polylineMaxAccele", name="Max Acceleration",
                                       desc="Maximum acceleration"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.3)
                        builder.UNIT("m/s²")
                    with builder.CHILD(key="polylineMaxDecele", name="Max Deceleration",
                                       desc="Maximum deceleration"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.2)
                        builder.UNIT("m/s²")
                    with builder.CHILD(key="polylineDeceleDist", name="Deceleration Distance",
                                       desc="Distance to start deceleration before target"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylineMaxAngle", name="Max Angle",
                                       desc="Maximum angle between two lines"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.3)
                        builder.UNIT("rad")
                    with builder.CHILD(key="polylinePathDistAccuracy", name="Path Distance Accuracy",
                                       desc="Position accuracy for path following"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.01)
                        builder.UNIT("m")
                    with builder.CHILD(key="polylinePathAngleAccuracy", name="Path Angle Accuracy",
                                       desc="Angle accuracy for path following"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05)
                        builder.UNIT("rad")

            # ============================================
            # PGV二次调整配置组（现场实施后基本不变）
            # ============================================
            with builder.GROUP(key="pgvConfig", name="PGV Secondary Adjust Config",
                               desc="PGV secondary adjustment parameters (site-specific, rarely changed)"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="pgvUseWhich", name="Use Which PGV",
                                       desc="Use up or down PGV"):
                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                        builder.DEFAULTVALUE("useDownPgv")
                        with builder.CHILDREN():
                            with builder.CHILD("useDownPgv", "Use Down PGV", "Use down-facing PGV"):
                                builder.TYPE(ParamType.STRING)
                            with builder.CHILD("useUpPgv", "Use Up PGV", "Use up-facing PGV"):
                                builder.TYPE(ParamType.STRING)
                    with builder.CHILD(key="pgvAdjustWay", name="Adjust Way",
                                       desc="PGV adjustment method (90/180/0 degrees)"):
                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                        builder.DEFAULTVALUE("pgvAdjust90")
                        with builder.CHILDREN():
                            with builder.CHILD("pgvAdjust90", "90 Degrees", "Adjust at 90 degrees"):
                                builder.TYPE(ParamType.STRING)
                            with builder.CHILD("pgvAdjust180", "180 Degrees", "Adjust at 180 degrees"):
                                builder.TYPE(ParamType.STRING)
                            with builder.CHILD("pgvAdjust0", "0 Degrees", "Adjust at 0 degrees"):
                                builder.TYPE(ParamType.STRING)
                    with builder.CHILD(key="pgvXAdjust", name="X Direction Adjust",
                                       desc="Enable secondary adjustment in X direction"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="pgvXAngleAdjust", name="X Angle Adjust",
                                       desc="Adjust deviation along car direction and angle at target"):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)
                    with builder.CHILD(key="pgvAdjustDist", name="Adjust Distance",
                                       desc="Maximum adjustment radius with QR code center"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.2)
                        builder.UNIT("m")
                    with builder.CHILD(key="pgvReachDist", name="Reach Distance Accuracy",
                                       desc="PGV secondary adjustment distance accuracy"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.02)
                        builder.UNIT("m")
                    with builder.CHILD(key="pgvReachAngle", name="Reach Angle Accuracy",
                                       desc="PGV secondary adjustment angle accuracy"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.02)
                        builder.UNIT("rad")

            # ============================================
            # 货架尺寸识别文件配置组（最多5个）
            # ============================================
            with builder.GROUP(key="rackSizeConfig", name="Rack Size Config",
                               desc="Multiple rack size recognition files (max 5). "
                                    "Tried in priority order during recognition."):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="recFile1", name="Rack Size 1",
                                       desc="Recognition file for rack size 1"):
                        builder.TYPE(ParamType.STRING)
                        builder.REQUIRED(False)
                        builder.DEFAULTVALUE("")
                    with builder.CHILD(key="recFile2", name="Rack Size 2",
                                       desc="Recognition file for rack size 2"):
                        builder.TYPE(ParamType.STRING)
                        builder.REQUIRED(False)
                        builder.DEFAULTVALUE("")
                    with builder.CHILD(key="recFile3", name="Rack Size 3",
                                       desc="Recognition file for rack size 3"):
                        builder.TYPE(ParamType.STRING)
                        builder.REQUIRED(False)
                        builder.DEFAULTVALUE("")
                    with builder.CHILD(key="recFile4", name="Rack Size 4",
                                       desc="Recognition file for rack size 4"):
                        builder.TYPE(ParamType.STRING)
                        builder.REQUIRED(False)
                        builder.DEFAULTVALUE("")
                    with builder.CHILD(key="recFile5", name="Rack Size 5",
                                       desc="Recognition file for rack size 5"):
                        builder.TYPE(ParamType.STRING)
                        builder.REQUIRED(False)
                        builder.DEFAULTVALUE("")

        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        debug_trace("Reloading config parameters")
        cls.config = param_loader.loadConfig()
        debug_trace(f"Loaded config: {cls.config}")

        # 通用配置
        cls.debug_mode = cls.config.get("debugMode", False)

        # 电机配置
        cls.jack_motor_speed = cls.config.get("jackMotorSpeed")
        cls.jack_min_height = cls.config.get("jackMinHeight")
        cls.jack_max_height = cls.config.get("jackMaxHeight")

        # DI配置
        cls.jack_up_di = cls.config.get("jackUpDi")
        cls.jack_zero_di = cls.config.get("jackZeroDi")

        # Bezier导航配置
        cls.bezier_back_dist = cls.config.get("bezierBackDist", 0.0)
        cls.bezier_adjust_dist = cls.config.get("bezierAdjustDist", 2.0)
        cls.bezier_min_ahead_dist = cls.config.get("bezierMinAheadDist", 0)
        cls.bezier_is_backwards = cls.config.get("bezierIsBackwards", True)
        cls.bezier_is_hold_dir = cls.config.get("bezierIsHoldDir", False)
        cls.bezier_max_speed = cls.config.get("bezierMaxSpeed", 0.5)
        cls.bezier_max_accele = cls.config.get("bezierMaxAccele", 0.3)
        cls.bezier_max_decele = cls.config.get("bezierMaxDecele", 0.2)
        cls.bezier_decele_dist = cls.config.get("bezierDeceleDist", 1)
        cls.bezier_curvature_limit = cls.config.get("bezierCurvatureLimit", 1.3)
        cls.bezier_path_dist_accuracy = cls.config.get("bezierPathDistAccuracy", 0.01)
        cls.bezier_path_angle_accuracy = cls.config.get("bezierPathAngleAccuracy", 0.05)

        # Polyline导航配置
        cls.polyline_back_dist = cls.config.get("polylineBackDist", 0.0)
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

        # PGV配置
        cls.pgv_use_which = cls.config.get("pgvUseWhich", "useDownPgv")
        cls.pgv_adjust_way = cls.config.get("pgvAdjustWay", "pgvAdjust90")
        cls.pgv_x_adjust = cls.config.get("pgvXAdjust", True)
        cls.pgv_x_angle_adjust = cls.config.get("pgvXAngleAdjust", True)
        cls.pgv_adjust_dist = cls.config.get("pgvAdjustDist", 0.2)
        cls.pgv_reach_dist = cls.config.get("pgvReachDist", 0.02)
        cls.pgv_reach_angle = cls.config.get("pgvReachAngle", 0.02)

        # 货架尺寸识别文件列表（最多5个，过滤空值）
        cls.rack_size_files = [
            f for f in [
                cls.config.get("recFile1", ""),
                cls.config.get("recFile2", ""),
                cls.config.get("recFile3", ""),
                cls.config.get("recFile4", ""),
                cls.config.get("recFile5", ""),
            ] if f
        ]
        # 注册到管理器（新文件写入 CreatedAt，已有文件保留元数据）
        if cls.rack_size_files:
            rack_size_manager.register_recfiles(cls.rack_size_files)
            debug_trace(f"RackSizeConfig: 共 {len(cls.rack_size_files)}/5 个文件: {cls.rack_size_files}")

        debug_trace(f"Updated config: debug_mode={cls.debug_mode}")
        Trace.log(f"[DEBUG] config loaded: bezierMinAheadDist={cls.bezier_min_ahead_dist}")


# 创建全局配置管理器实例
config_params = ConfigParams()

# ============================================================================
# 调试任务列表（需要开启 debugMode 才能执行）
# ============================================================================
DEBUG_ONLY_TASKS = [
    "goBezier",  # 贝塞尔导航
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


# ============================================================================
# RS485已移除，改用Motor API控制顶升电机
# ============================================================================


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


def create_ap_id(builder: ParamBuilder):
    with builder.CHILD(key="targetName", name="Target ID",
                       desc="the ap id for operation"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE("AP1")


def create_recfile(builder: ParamBuilder):
    with builder.CHILD(key="recFile", name="RecFile", desc="file for recognizing"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE("default.srec")
    with builder.CHILD(key="insertShelfDir", name="Insert Shelf Direction", desc="direction to go under the shelf"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE("A")


def create_bezier(builder: ParamBuilder):
    """贝塞尔导航参数（详细参数已移到脚本配置中）"""
    pass  # 详细参数从ConfigParams读取


def create_polyline(builder: ParamBuilder):
    """折线导航参数（详细参数已移到脚本配置中）"""
    pass  # 详细参数从ConfigParams读取


def create_gopath(builder: ParamBuilder):
    """直线导航参数"""
    pass  # 详细参数从ConfigParams读取


def create_secondary_adjust_pgv(builder: ParamBuilder):
    """PGV二次调整参数（详细参数已移到脚本配置中）"""
    pass  # 详细参数从ConfigParams读取


def create_jack_load(builder: ParamBuilder):
    create_ap_id(builder)
    create_start_height(builder)
    create_end_height(builder)
    create_recfile(builder)

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

    with builder.CHILD(key="howGoSite", name="howGoSite", desc="choose the way to the landmark"):
        builder.TYPE(ParamType.COMBO_BOX)
        builder.DEFAULTVALUE("bezier")
        builder.REQUIRED(False)
        with builder.CHILDREN():
            with builder.CHILD(key="bezier", name="bezier", desc="bezier"):
                builder.TYPE(ParamType.ARRAY)
                create_bezier(builder)

            with builder.CHILD(key="straight", name="straight", desc="straight"):
                builder.TYPE(ParamType.ARRAY)
                create_gopath(builder)

            with builder.CHILD(key="polyline", name="polyline", desc="polyline"):
                builder.TYPE(ParamType.ARRAY)
                create_polyline(builder)

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
                create_secondary_adjust_pgv(builder)


class InputParams:
    """
    任务输入参数

    参数分类原则：
    1. 输入参数：每次任务可能不同的参数（如targetName, recFile, isRecognize）
    2. 配置参数：现场实施后基本不变的参数（已移到ConfigParams）
    3. 调试任务：开启debugMode后才显示的低频任务

    任务分类：
    - 常用任务（始终显示）：jackLoad, jackUnload, jackUp, jackDown
    - 调试任务（debugMode=true时显示）：goBezier等
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

                # 顶升到顶（推荐）
                with builder.CHILD(key="jackUp", name="Jack Up", desc="lift to top, no height needed (recommended)"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="recFile", name="RecFile", desc="file for recognizing"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE("default.srec")

                # 下降到底（推荐）
                with builder.CHILD(key="jackDown", name="Jack Down",
                                   desc="lower to bottom, no height needed (recommended)"):
                    builder.TYPE(ParamType.ARRAY)

                # 指定高度顶升
                with builder.CHILD(key="jackHeight", name="Jack Height",
                                   desc="lift to specified height"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_end_height(builder)
                        with builder.CHILD(key="recFile", name="RecFile", desc="file for recognizing"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE("default.srec")

                # ============================================
                # 调试/低频任务（需要开启debugMode才显示）
                # ===========================================
                if config_params.debug_mode:
                    # [DEBUG] 贝塞尔导航
                    with builder.CHILD(key="goBezier", name="[Debug] goBezier",
                                       desc="go bezier line to target (debug only)"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            create_ap_id(builder)

                    with builder.CHILD(key="getLM", name="getLM",
                                       desc="get the position of landmark"):
                        builder.TYPE(ParamType.ARRAY)
                        create_ap_id(builder)

                    with builder.CHILD(key="laserAreaDeduction", name="laserAreaDeduction",
                                       desc="laser area deduction"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILD(key="coordinate", name="coordinate", desc="Coordinate system"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE("robot")
                            builder.REQUIRED(True)
                            with builder.CHILDREN():
                                with builder.CHILD("robot", "robot", "robot"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("world", "world", "world"):
                                    builder.TYPE(ParamType.STRING)

                    with builder.CHILD(key="createOrDeleteDeductedArea", name="create_or_delete_deducted_area",
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

                    with builder.CHILD(key="jackBezierReturn", name="jackBezierReturn",
                                       desc="recognize and go bezier to get the shelf and return"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILDREN():
                            create_ap_id(builder)
                            create_start_height(builder)
                            create_end_height(builder)
                            create_bezier(builder)
                            create_recfile(builder)

                    with builder.CHILD(key="goPolyline", name="goPolyline", desc="go polyline line to target position"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILDREN():
                            # 旋转角度参数
                            create_ap_id(builder)
                            create_polyline(builder)

                    with builder.CHILD(key="goDist", name="goDist", desc="go straight distance"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILD(key="goPathX", name="goPath_x",
                                           desc="The dist of the target point to which robot will go in a straight line"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("m")
                            builder.DEFAULTVALUE(0)

                    with builder.CHILD(key="goPath", name="goPath", desc="go straight to target position"):
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
                        with builder.CHILD(key="coordinate", name="coordinate", desc="Coordinate system"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE("robot")

                            with builder.CHILDREN():
                                with builder.CHILD("robot", "robot", "robot"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("world", "world", "world"):
                                    builder.TYPE(ParamType.STRING)

                        create_gopath(builder)

                    with builder.CHILD(key="recShelf", name="recShelf", desc="recognize the shelf"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILD(key="recFile", name="recfile",
                                           desc="the file for recognize"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE("default.srec")

                    with builder.CHILD(key="getRecfile", name="getRecfile", desc="get Recfile"):
                        builder.TYPE(ParamType.ARRAY)

                        with builder.CHILD(key="recFile", name="recfile",
                                           desc="the file for recognize"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE("default.srec")

                    with builder.CHILD(key="recTargetObs", name="recTargetObs", desc="recTargetObs"):
                        builder.TYPE(ParamType.ARRAY)

    builder.save_to_file()


class Jack(ModuleBase):
    def __init__(self):
        super().__init__()
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

        self.recfiles = []  # 多货架尺寸：按优先级排序后的候选文件列表
        self.matched_recfile = None  # 本次识别成功匹配的文件（任务完成后写 LastUsedAt）
        self.how_go_site = None

        # 货架识别
        self.rec_result = []
        # 二维码识别
        self.code_info = dict()

        # 数据打印
        self.report_info = {}

        # robotParam
        self.lift_motor = None
        debug_trace(f"Jack init: motor={config_params.jack_motor_name}, "
                    f"height=[{config_params.jack_min_height}~{config_params.jack_max_height}]m, "
                    f"DI=[up:{config_params.jack_up_di}, zero:{config_params.jack_zero_di}]")

        self.status = ScriptStatus.NONE

        self.cur_action_list = []

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

    def _init_args(self, args):
        self.task_args = args
        # 获取任务参数
        self.opt = self.task_args.get("operation", None)
        self.ap_id = None  # targetName 从 Navigation.moveTask() 获取
        # 顶升高度相关
        self.start_height = self.task_args.get("startHeight", 0)
        self.end_height = self.task_args.get("endHeight", 0.06)
        # 识别相关
        self.is_recognize = self.task_args.get("recognize", None)
        self.recfile = self.task_args.get("recFile", "default.srec")
        self.insert_shelf_dir = self.task_args.get("insertShelfDir", "A")
        self.coordinate = self.task_args.get("coordinate", "world")

        # 多货架尺寸：优先使用 ConfigParams 中的文件列表，降级到单文件
        if config_params.rack_size_files:
            self.recfiles = rack_size_manager.get_sorted_recfiles(config_params.rack_size_files)
            debug_trace(f"[RACK] 按优先级排序后的识别文件: {self.recfiles}")
        else:
            self.recfiles = [self.recfile] if self.recfile else []
            debug_trace(f"[RACK] 未配置多货架尺寸，使用单文件: {self.recfile}")
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
        # PGV二次调整参数：从脚本配置读取（现场实施后基本不变）
        # ============================================
        self.is_secondary_adjust = self.task_args.get("isSecondaryAdjust", None)
        self.use_which_pgv = config_params.pgv_use_which
        self.pgv_adjust_way = config_params.pgv_adjust_way
        self.pgv_x_adjust = config_params.pgv_x_adjust
        self.pgv_x_angle_adjust = config_params.pgv_x_angle_adjust
        self.pgv_adjust_dist = config_params.pgv_adjust_dist
        self.pgv_reach_dist = config_params.pgv_reach_dist
        self.pgv_reach_angle = config_params.pgv_reach_angle

        # laser area deduction
        self.create_or_delete_deducted_area = self.task_args.get("createOrDeleteDeductedArea", None)
        self.status = ScriptStatus.RUNNING

        Trace.log(f"[DEBUG] min_ahead_dist={self.min_ahead_dist}, "
                  f"adjust_dist={self.adjust_dist_for_curvature_limit}, "
                  f"max_decele={self.max_decele}")

    def run(self):
        # ============================================
        # 调试任务检查：如果是调试任务且 debugMode=false，则拒绝执行
        # ============================================
        if not check_debug_task(self.opt):
            Trace.log(
                f"[REJECTED] Debug task '{self.opt}' rejected. Enable 'debugMode' in script config to use this task.")
            self.status = ScriptStatus.FAILED
            return

        self.set_vda_param()
        # 选择执行动作
        if self.opt == "jackLoad":  # 识别/非识别取货
            self.jack_load()
        elif self.opt == "jackUnload":  # 识别/非识别放货
            self.jack_unload()
        elif self.opt == "getLM":
            self.get_lm()
        elif self.opt == "goAPSite":  # 前往ap点，直线，bezier，两段线
            self.go_ap_site()
        elif self.opt == "goBezier":
            self.go_bezier()
        elif self.opt == "goPolyline":
            self.go_polyline()
        elif self.opt == "jackHeight":  # 控制托盘抬升高度
            self.jack_target_height()
        elif self.opt == "jackUp":  # 顶升到顶（推荐）
            self.jack_up()
        elif self.opt == "jackDown":  # 下降到底（推荐）
            self.jack_down()
        elif self.opt == "goMapPath":  # 前进一段距离
            self.go_map_path()
        elif self.opt == "goDist":  # 直线前进一段距离
            self.go_dist()
        elif self.opt == "goPath":  # 直线到达目标点（世界/机器人坐标系）
            self.go_path()
        elif self.opt == "recShelf":  # 识别货架
            self.rec_shelf()
        elif self.opt == "PGVSecondaryAdjust":  # 通过pgv二次调整
            self.pgv_adjust()
        elif self.opt == "recTargetObs":
            self.rec_target_obs()
        elif self.opt == "getRecfile":
            self.get_rec_file()
        elif self.opt == "stopMotor":
            self.stop_motor()
        elif self.opt == "PGVSecondaryAndJackUp":
            self.pgv_second_and_jack_up()
        else:
            self.status = ScriptStatus.FAILED

        # Trace.log(f"self.action_list: {self.action_list}")

        self.cur_action_list = []
        for task in self.action_list:
            self.cur_action_list.append(task.opt_info)

        # 只在 action_id 变化时输出日志（避免循环内重复输出）
        if self._last_logged_action_id != self.action_id:
            self._last_logged_action_id = self.action_id
            if self.action_id < len(self.action_list):
                current_action = self.action_list[self.action_id]
                debug_trace(f'[ACTION] #{self.action_id + 1}/{len(self.action_list)} {current_action.action_name}')

        self._execute_actions()

    def pgv_second_and_jack_up(self):
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(GetPGVData(self.use_which_pgv))
            self.action_list.append(PGVSecondaryAdjust(self.use_which_pgv, self.pgv_x_adjust, self.pgv_x_angle_adjust,
                                                       self.pgv_adjust_dist, self.pgv_reach_dist, self.pgv_reach_angle,
                                                       self.pgv_adjust_way))
            self.action_list.append(JackHeight(config_params.jack_motor_name, self.end_height,
                                               config_params.jack_motor_speed, self.recfile))

    def laser_area_deduct(self, recfile, object_key: str = "shelf", index: int = None):
        if not recfile:
            return None
        try:
            recognition_obstacle_deduction_path = f"recognitionObject.{object_key}.obstacleDeduction"
            size = RobotParam.getConfigCloneSize("recognition", recognition_obstacle_deduction_path, recfile)
            if size is None or size == 0:
                return None

            all_devices = []
            all_areas = []

            # 如果指定了 index，只读那一个；否则读全部
            indices_to_read = [index] if index is not None else range(size)

            for i in indices_to_read:
                if i >= size:
                    Trace.log(f"[LASER] index={i} 超出范围 size={size}，跳过")
                    continue

                device_str = RobotParam.getConfig(
                    "recognition",
                    f"{recognition_obstacle_deduction_path}._{i}.deductDevice",
                    recfile
                )
                if not device_str:
                    continue
                devices = [d.strip() for d in device_str.split(",") if d.strip()]

                shape_str = RobotParam.getConfig(
                    "recognition",
                    f"{recognition_obstacle_deduction_path}._{i}.deductShape",
                    recfile
                )
                if not shape_str:
                    continue
                shapes = json.loads(shape_str)
                for shape in shapes:
                    pts = shape.get("points", [])
                    if len(pts) < 3:
                        continue
                    all_areas.append({"xList": [p["x"] for p in pts], "yList": [p["y"] for p in pts]})
                for d in devices:
                    if d not in all_devices:
                        all_devices.append(d)

            if not all_areas:
                return None

            info = {"deductDevice": all_devices, "area": all_areas}
            debug_trace(f"[LASER] index={index} Deduct areas: devices={all_devices}, count={len(all_areas)}")
            return info

        except json.JSONDecodeError as e:
            Trace.log(f"[ERROR] laser_area_deduct JSON解析失败: {e}")
            return None
        except Exception as e:
            Trace.log(f"[ERROR] laser_area_deduct 异常: {e}")
            return None

    def get_rec_file(self):
        if not self.operation_init:
            self.operation_init = True
            # 如果钻入深度为None,即未传入back_dist,此时用识别文件中的钻入深度
            self.shelf_back_distance = self.get_back_distance_info(self.recfile, "shelf", "A")
            print(f"self.shelf_back_distance={self.shelf_back_distance}")
            self.laser_area_deduct_info = self.laser_area_deduct(self.recfile, "shelf")
            print(f"self.laser_area_deduct_info={self.laser_area_deduct_info}")

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
        self.report_info["containers"] = Container.getContainers()
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

    def jack_load(self):
        """
        完整取货流程：旋转车体对准 → 识别货架 → 导航 → 二次调整 → 顶升 → 设置激光扣除区域
        """
        if not self.operation_init:
            self.operation_init = True

            # === 初始化时用优先级最高的文件预读激光扣除区域配置 ===
            primary_recfile = self.recfiles[0] if self.recfiles else self.recfile
            # ① jackLoad 之前：只用 _1 扣除区（导航钻入阶段）
            if primary_recfile:
                deduct_info_pre = self.laser_area_deduct(primary_recfile, "shelf", index=1)
                debug_trace(f"jack_load: Pre-load deduct info (_3): {deduct_info_pre}")
                self.action_list.append(SetLaserDeductArea(deduct_info_pre, prefix="ShelfDeductPre"))

            # 下降到起始高度
            if self.start_height:
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, self.start_height, config_params.jack_motor_speed))

            # 获取AP点
            self.ap_id = self.ap_id or self.get_ap()
            if not self.ap_id:
                Navigation.setTaskError("53379", "丢失AP点ID")
                return

            debug_trace(f"jack_load: ap_id={self.ap_id}")
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)
            debug_trace(f"jack_load: AP_pos={self.ap_world_pos}")

            self.report_info["jack_load"] = {"apWorldPos": self.ap_world_pos}

            # 转到与AP点方向一致
            self.action_list.append(RobotRotate(self.ap_world_pos[2], Coordinate.WORLD, False))

            # 启用识别：传入按优先级排序后的文件列表
            if self.is_recognize:
                rec_files_to_use = self.recfiles if self.recfiles else [self.recfile]
                debug_trace(f"jack_load: 多货架尺寸候选文件: {rec_files_to_use}")
                self.action_list.append(RecShelf(rec_files_to_use, "FirstRec"))

            # 关闭绕行策略
            Navigation.appendCustomPolicy("policy_jack_load", {"navigation.freeBypass": "off"})

        # 动态添加 action_list（识别完成后）
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]

            if current_action.action_name == "FirstRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result

                # 导航方式
                if self.how_go_site == "straight":
                    self.action_list.append(
                        GoPath(self.ap_world_pos, "world", self.is_backwards, self.is_hold_dir,
                               self.max_speed, self.max_rot, self.path_dist_accuracy, self.path_angle_accuracy))
                elif self.how_go_site == "bezier":
                    recfile_back_dist = self.get_back_distance_info(self.recfile, "shelf", "A")
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

                elif self.how_go_site == "polyline":
                    self.action_list.append(
                        GoPolyline(self.ap_world_pos, self.min_ahead_dist, self.adjust_dist_for_curvature_limit,
                                   self.back_dist, self.max_speed, self.max_rot, self.decele_dist))

                # 二次调整
                if self.is_secondary_adjust:
                    self.action_list.append(GetPGVData(self.use_which_pgv))
                    self.action_list.append(
                        PGVSecondaryAdjust(self.use_which_pgv, self.pgv_x_adjust, self.pgv_x_angle_adjust,
                                           self.pgv_adjust_dist, self.pgv_reach_dist, self.pgv_reach_angle,
                                           self.pgv_adjust_way))

                # ② JackHeight 之前：删 _1 扣除区，换上 _0 扣除区
                self.action_list.append(DeleteLaserDeductArea(prefix="ShelfDeductPre"))
                deduct_info_lift = self.laser_area_deduct(self.recfile, "shelf", index=0)

                # 顶升
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, self.end_height, config_params.jack_motor_speed,
                               self.recfile, deduct_info=deduct_info_lift))

                # 顶升完成后绑定容器，设置货物模型
                self.action_list.append(BindContainer("0", "shelf", self.recfile, self.insert_shelf_dir))

                # 取货完成后清除策略
                self.action_list.append(ClearPolicy())

                # 取货任务成功完成后更新货架尺寸 LastUsedAt
                self.action_list.append(UpdateRackLastUsed())

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
                # 边走边动模式下顶升已经下降完成，跳过下降步骤
                debug_trace(f"jackUnload: 边走边动模式，顶升已下降 (height={current_height:.4f}m)，跳过下降步骤")
                self.action_list.append(UnbindContainer("0"))
            else:
                # 正常模式或边走边动未完成，执行下降托盘
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, 0, config_params.jack_motor_speed, self.recfile))
                # 下降完成后解绑容器，清除货物模型
                self.action_list.append(UnbindContainer("0"))
            # === 放货完成后删除激光扣除区域 ===
            self.action_list.append(DeleteLaserDeductArea())

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

    def go_ap_site(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            debug_trace(f'AP_pos: {self.ap_world_pos}')
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
                self.ap_id = Navigation.moveTask().get("target_name", None)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            debug_trace(f'AP_pos: {self.ap_world_pos}')
            self.action_list.append(
                GoBezier(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                         self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                         self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                         self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))

    def go_polyline(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在机器人坐标系下的位置
            debug_trace(f'AP_pos: {self.ap_world_pos}')
            self.action_list.append(GoPolyline(self.ap_world_pos))

    def go_map_path(self):
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(GoMapPath())

    def jack_target_height(self):
        """抬升托盘到指定高度"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(JackHeight(config_params.jack_motor_name, self.end_height,
                                               config_params.jack_motor_speed, self.recfile))

    def jack_up(self):
        """顶升到顶（推荐，不需要指定高度）"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(JackUpDown("up", self.recfile))

    def jack_down(self):
        """下降到底（推荐，不需要指定高度）"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(JackUpDown("down"))

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
            self.action_list.append(RecShelf(self.recfile))  # 导航到终点

    def pgv_adjust(self):
        """二次调整"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(GetPGVData(self.use_which_pgv))
            self.action_list.append(PGVSecondaryAdjust(self.use_which_pgv, self.pgv_x_adjust, self.pgv_x_angle_adjust,
                                                       self.pgv_adjust_dist, self.pgv_reach_dist, self.pgv_reach_angle,
                                                       self.pgv_adjust_way))

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
            "containers": Container.getContainers(),
        })

        Module.reportInfo(self.report_info)
        self.info_count = self.info_count + 1

    # ========== 边走边动 (Move-While-Act) ==========
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

        # 尝试方式3: 从moveTask获取
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
                    for p in move_task.get('params', []):
                        if p.get('key') == '#finalBinTask' and p.get('stringValue', '') != "":
                            has_final_bin_task = True
                        if p.get('key') == 'binTask' and p.get('stringValue', '') != "":
                            has_bin_task = True
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

            # 判断是否到达终点
            if (not has_final_bin_task or has_bin_task) and self.pre_action_mode:
                if not self.at_final_loc:
                    debug_trace(
                        f"[边走边动] 判断已到达终点 (has_final_bin_task={has_final_bin_task}, has_bin_task={has_bin_task})")
                    time.sleep(0.3)
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
        current_height = Motor.getMotorPos(config_params.jack_motor_name)

        if current_height <= target_height + 0.005:
            self.pre_action_step[0] = True
            debug_trace(f"[边走边动] 顶升已下降到位: {current_height:.4f}m")
        else:
            if not self.pre_action_step[0]:
                slow_speed = config_params.jack_motor_speed * 0.5
                Motor.setMotorPosition(config_params.jack_motor_name, target_height, slow_speed,
                                       config_params.jack_zero_di)

                if Motor.isMotorReached(config_params.jack_motor_name) or Di.getDi(config_params.jack_zero_di):
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
        self.set_info()

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
                debug_trace(f"[边走边动] jackUnload切换到完整动作，顶升已预先下降")

            self.pre_action_mode = False
            self.status = ScriptStatus.NONE
            Module.setStatus(self.status)

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


class ClearPolicy(BaseAction):
    """清除导航策略 """

    def __init__(self):
        super().__init__("ClearPolicy")
        self.action_status = ActionStatus.INIT
        self.init = True
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.clearPolicy()
            debug_trace("ClearPolicy: 已清除导航策略，恢复绕行设置")
            self.action_status = ActionStatus.FINISHED


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

    def __init__(self, motor_name, target_height, jack_motor_speed, recfile=None, object_key="shelf", deduct_info=None):
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
        self.deduct_info = deduct_info  # 激光扣除区数据，顶升完成后设置，下降完成后删除
        self.init = False
        self.jack_start_height = None
        self._count_recorded = False  # 防止重复计数
        self._last_progress = -1  # 用于进度日志去重
        self._up_di_triggered_time = None # 上到位 DI/isReached 触发时间戳（用于延迟）
        Motor.resetMotor(self.motor_name)

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            self.jack_start_height = Motor.getMotorPos(config_params.jack_motor_name)

            # 只在初始化时输出一次关键信息
            direction = "↑Jack up" if self.target_height > self.jack_start_height else "↓Jack down"
            debug_trace(
                f"[JACK] {direction} {self.jack_start_height:.3f}m → {self.target_height:.3f}m (speed={self.jackMotorSpeed})")

            if self.target_height > self.jack_start_height:
                Motor.setMotorPosition(self.motor_name, self.target_height, self.jackMotorSpeed,
                                       config_params.jack_up_di)
            else:
                Motor.setMotorPosition(self.motor_name, self.target_height, self.jackMotorSpeed,
                                       config_params.jack_zero_di)

        # 获取当前电机位置（精简版，不输出完整 motor_info）
        current_pos = Motor.getMotorPos(self.motor_name)

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
            if Motor.isMotorReached(self.motor_name) or Di.getDi(config_params.jack_up_di):
                if self._up_di_triggered_time is None:
                    self._up_di_triggered_time = time.time()
                    debug_trace(f"[JACK] 上到位触发 pos={current_pos:.4f}m")
                elif time.time() - self._up_di_triggered_time >= 0.2:
                    self.action_status = ActionStatus.FINISHED
                    Motor.resetMotor(self.motor_name)
                    debug_trace(f"[JACK] 顶升完成 pos={current_pos:.4f}m")
                    # 顶升完成，记录顶升次数（仅在顶升时计数，下降不计数）
                    if not self._count_recorded:
                        self._count_recorded = True
                        jack_count_manager.increment_count()
                    # 顶升完成后设置激光扣除区（车已到达货架正下方，坐标准确）
                    if self.deduct_info:
                        self._set_deduct_area()
        else:
            # 下降动作
            if Motor.isMotorReached(self.motor_name) or Di.getDi(config_params.jack_zero_di):
                self.action_status = ActionStatus.FINISHED
                Motor.resetMotor(self.motor_name)
                debug_trace(f"[JACK] Jack down done pos={current_pos:.4f}m")
                # 下降完成后删除激光扣除区
                self._delete_deduct_area()

        j.report_info["JackHeight"] = {
            "actionStatus": self.action_status,
            "motorName": self.motor_name,
            "targetHeight": self.target_height,
            "jackMotorSpeed": self.jackMotorSpeed,
        }
        Module.reportInfo(j.report_info)

    def _set_deduct_area(self):
        """顶升完成后设置激光扣除区域（机器人坐标系，车已在货架正下方）"""
        try:
            devices = self.deduct_info.get("deductDevice", [])
            areas = self.deduct_info.get("area", [])
            debug_trace(f"[LASER] Setting deduct area: {len(areas)} areas, devices={devices}")
            for idx, area in enumerate(areas, start=1):
                x_list = area.get("xList", area.get("x_list", []))
                y_list = area.get("yList", area.get("y_list", []))
                if len(x_list) < 3 or len(x_list) != len(y_list):
                    debug_trace(f"[LASER] Skip invalid area idx={idx}")
                    continue
                region_name = f"ShelfDeductArea{idx}"
                Navigation.setClearRegion(region_name, x_list, y_list, devices, Coordinate.ROBOT)
                debug_trace(f"[LASER] Created {region_name}")
        except Exception as e:
            Trace.log(f"[LASER] _set_deduct_area error: {e}")

    def _delete_deduct_area(self):
        """下降完成后删除激光扣除区域"""
        try:
            clear_regions = Navigation.getClearRegion(Coordinate.ROBOT)
            deleted_count = 0
            if clear_regions:
                for region in clear_regions:
                    if region.startswith("ShelfDeductArea"):
                        Navigation.deleteClearRegion(region, Coordinate.ROBOT)
                        deleted_count += 1
            debug_trace(f"[LASER] Deleted {deleted_count} deduct regions")
        except Exception as e:
            Trace.log(f"[LASER] _delete_deduct_area error: {e}")

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

class JackUpDown(BaseAction):
    """
    顶升/下降动作（推荐使用，不需要指定高度）
    - direction="up": 顶升到顶，使用Motor.setMotorPosition + jack_up_di
    - direction="down": 下降到底，使用Motor.setMotorPosition + jack_zero_di
    """

    def __init__(self, direction: str, recfile=None, object_key="shelf"):
        super().__init__("JackUpDown")

        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.direction = direction
        self.recfile = recfile
        self.object_key = object_key
        self.init = False
        self._count_recorded = False
        Motor.resetMotor(config_params.jack_motor_name)

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING

            # 发送电机指令
            if self.direction == "up":
                target_height = config_params.jack_max_height or 0.06
                debug_trace(f"[JACK] ↑JackUpDown UP -> target={target_height}, "
                            f"speed={config_params.jack_motor_speed}")
                Motor.setMotorPosition(config_params.jack_motor_name, target_height,
                                       config_params.jack_motor_speed, config_params.jack_up_di)

                # 设置货物形状（在init时）
                shape = None
                if self.recfile:
                    recognition_goodsParameter_path = f"recognitionObject.{self.object_key}.goodsParameter"
                    goods_shape = RobotParam.getConfig("recognition",
                                                       f"{recognition_goodsParameter_path}.goodsShape",
                                                       self.recfile)
                    shapes = json.loads(goods_shape)
                    debug_trace(f"[JACK] goodsShape loaded: {len(shapes[0]['points'])} points")
                    shape = shapes[0]["points"]
                Navigation.setGoodsPolyShape(shape, "shelf")
            else:
                target_height = config_params.jack_min_height or 0.0
                debug_trace(f"[JACK] ↓JackUpDown DOWN -> target={target_height}")
                Motor.setMotorPosition(config_params.jack_motor_name, target_height,
                                       config_params.jack_motor_speed, config_params.jack_zero_di)
                Navigation.clearGoodsShape()

        # 检查是否完成
        if self.direction == "up":
            if Motor.isMotorReached(config_params.jack_motor_name) or Di.getDi(config_params.jack_up_di):
                self.action_status = ActionStatus.FINISHED
                Motor.resetMotor(config_params.jack_motor_name)
                debug_trace(f"[JACK] JackUpDown UP done")
                # 顶升完成，记录次数
                if not self._count_recorded:
                    self._count_recorded = True
                    jack_count_manager.increment_count()
        else:
            if Motor.isMotorReached(config_params.jack_motor_name) or Di.getDi(config_params.jack_zero_di):
                self.action_status = ActionStatus.FINISHED
                Motor.resetMotor(config_params.jack_motor_name)
                debug_trace(f"[JACK] JackUpDown DOWN done")

        j.report_info["JackUpDown"] = {
            "actionStatus": self.action_status,
            "direction": self.direction,
        }
        Module.reportInfo(j.report_info)


class GoMapPath(BaseAction):
    """前进指定距离"""

    def __init__(self):
        super().__init__("GoMapPath")

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
            "coordinate": self.coordinate,
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
            "coordinate": self.coordinate,
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
        print(f"targetWorld = {target_world}")
        self.go_bezier = goBezier.GoBezierWorld(target_world, back_dist, adjust_dist_for_curvature_limit,
                                                min_ahead_dist,
                                                is_backwards, is_hold_dir, max_speed, max_accele, max_decele,
                                                decele_dist,
                                                curvature_limit, path_dist_accuracy, path_angle_accuracy)

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

        if self.action_status in (ActionStatus.INIT, ActionStatus.RUNNING):
            self.action_status = self.go_bezier.run()
            # 路径计算完成后打印一次起点、终点和轨迹
            if not self.go_bezier.init and not hasattr(self, '_bezier_printed'):
                self._bezier_printed = True
                print(f"[GoBezier] 起点(robot_loc): {self.go_bezier.robot_loc}")
                print(f"[GoBezier] 终点(end_position): {self.go_bezier.end_position_world}")
                print(f"[GoBezier] 轨迹点数: {len(self.go_bezier.xs)}")
                print(f"[GoBezier] 轨迹xs: {self.go_bezier.xs}")
                print(f"[GoBezier] 轨迹ys: {self.go_bezier.ys}")
        debug_trace(f"bezier_status={self.action_status}")
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

    def __init__(self, is_backwards=True, is_hold_dir=None, max_speed=0.3, max_accele=1, max_decele=0.7,
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


# class RecShelf(BaseAction):
#     """识别货架"""
#
#     def __init__(self, shelf_file, action_name="RecShelf"):
#         super().__init__(action_name)
#
#         kwargs = locals()
#         del kwargs['self']
#         del kwargs['__class__']
#         self.opt_info = f"{__class__.__name__}{kwargs}"
#
#         self.action_status = ActionStatus.INIT
#         self.recfile = shelf_file
#         self.attempts = 0
#         self.max_attempts = 10
#         self.do_rec = False
#         Recognize.resetRec()
#
#         self.recognitionRegion = {
#             "points": [{"x": -2.56, "y": -1.035}, {"x": -0.63, "y": -1.035}, {"x": -0.63, "y": 1.035},
#                        {"x": -2.56, "y": 1.035}], "shape": "rectangle"}
#
#         self.report_info = {}
#
#     def run(self, j: Jack):
#         self.action_status = ActionStatus.RUNNING
#         debug_trace("recognizing the shelf")
#         rec_status = Recognize.getRecStatus()
#         debug_trace(f"{rec_status=}")
#         if rec_status == 2:
#             rec_result = Recognize.getRecResults()
#             debug_trace(f"{rec_result=}")
#             Recognize.resetRec()
#             debug_trace(f"rec_result={rec_result}")
#             rec_x = rec_result['recoList'][0]['x']
#             rec_y = rec_result['recoList'][0]['y']
#             rec_yaw = rec_result['recoList'][0]['yaw']
#             rec_yaw = (rec_yaw + math.pi) % (2 * math.pi) - math.pi
#             rec_x_y_yaw = [rec_x, rec_y, rec_yaw]
#             debug_trace(f"{rec_x_y_yaw=}")
#             j.rec_result = rec_x_y_yaw
#             self.action_status = ActionStatus.FINISHED
#         elif rec_status in (3, -1):
#             if Timer.delay(0.05):
#                 self.attempts += 1
#
#                 if self.attempts > self.max_attempts:
#                     self.action_status = ActionStatus.FAILED
#                     Navigation.setTaskError("53357", "识别重试次数超限，请检查识别距离或识别传感器是否正常")
#                 else:
#                     Recognize.resetRec()
#                     self.do_rec = False
#         elif rec_status == 0:
#             self.do_rec = True
#             Recognize.doRec(self.recfile, json.dumps(self.recognitionRegion), "A")
#         j.report_info["RecShelf"] = {
#             "actionStatus": self.action_status,
#             "recResult": j.rec_result,
#             "recFile": self.recfile,
#             "recStatus": rec_status,
#             "recTimes": self.attempts
#         }
#         Module.reportInfo(j.report_info)
class RecShelf(BaseAction):
    """
    识别货架，支持多个识别文件按优先级顺序依次尝试。

    - 当前文件成功 → 记录 j.matched_recfile，动作完成
    - 当前文件超限 → 切换下一个文件继续尝试
    - 所有文件均失败 → 上报 RACK_NOT_MATCHED，动作失败，不写入任何 LastUsedAt
    """

    def __init__(self, shelf_files, action_name="RecShelf"):
        super().__init__(action_name)

        if isinstance(shelf_files, str):
            shelf_files = [shelf_files]
        self.shelf_files = [f for f in shelf_files if f]

        self.current_file_idx = 0
        self.recfile = self.shelf_files[0] if self.shelf_files else None
        self.opt_info = f"{self.__class__.__name__}{{shelf_files={self.shelf_files}}}"

        self.action_status = ActionStatus.INIT
        self.attempts = 0
        self.max_attempts = 10
        self.do_rec = False
        Recognize.resetRec()

        self.recognitionRegion = {
            "points": [{"x": -2.56, "y": -1.035}, {"x": -0.63, "y": -1.035}, {"x": -0.63, "y": 1.035},
                       {"x": -2.56, "y": 1.035}], "shape": "rectangle"}

        self.report_info = {}

    def _try_next_file(self) -> bool:
        """切换到下一个候选文件，返回 True 表示还有文件可尝试"""
        self.current_file_idx += 1
        if self.current_file_idx < len(self.shelf_files):
            self.recfile = self.shelf_files[self.current_file_idx]
            self.attempts = 0
            self.do_rec = False
            Recognize.resetRec()
            debug_trace(f"RecShelf: 切换文件 [{self.current_file_idx + 1}/{len(self.shelf_files)}]: {self.recfile}")
            Trace.log(f"[RACK] 切换识别文件 [{self.current_file_idx + 1}/{len(self.shelf_files)}]: {self.recfile}")
            return True
        return False

    def run(self, j: Jack):
        self.action_status = ActionStatus.RUNNING
        debug_trace(f"RecShelf: [{self.current_file_idx + 1}/{len(self.shelf_files)}] file={self.recfile}")
        rec_status = Recognize.getRecStatus()
        debug_trace(f"{rec_status=}")

        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            Recognize.resetRec()
            reco_list = rec_result.get('recoList', [])
            if not reco_list:
                debug_trace("RecShelf: recoList empty, retrying")
                self.do_rec = False
                return
            reco = reco_list[0]
            if not reco.get('valid', False):
                debug_trace("RecShelf: result invalid, retrying")
                self.do_rec = False
                return
            world_result = reco.get('worldResult', {})
            rec_x = world_result['x']
            rec_y = world_result['y']
            rec_yaw = world_result['yaw']
            rec_yaw = (rec_yaw + math.pi) % (2 * math.pi) - math.pi
            j.rec_result = [rec_x, rec_y, rec_yaw]
            j.matched_recfile = self.recfile
            debug_trace(f"RecShelf: 识别成功，匹配文件: {self.recfile}, 结果: {j.rec_result}")
            Trace.log(f"[RACK] 识别成功，匹配文件: {self.recfile}")
            self.action_status = ActionStatus.FINISHED

        elif rec_status in (3, -1):
            if Timer.delay(0.05):
                self.attempts += 1
                debug_trace(f"RecShelf: {self.recfile} 失败 ({self.attempts}/{self.max_attempts})")
                if self.attempts > self.max_attempts:
                    if not self._try_next_file():
                        # 所有文件均失败
                        self.action_status = ActionStatus.FAILED
                        Trace.log(f"[RACK] RACK_NOT_MATCHED: 所有 {len(self.shelf_files)} 个文件均未匹配")
                        Navigation.setTaskError("53357", f"识别失败: 所有{len(self.shelf_files)}个货架尺寸文件均不匹配，请检查识别距离、传感器及货架配置")
                else:
                    Recognize.resetRec()
                    self.do_rec = False

        elif rec_status == 0:
            self.do_rec = True
            Recognize.doRec(self.recfile, json.dumps(self.recognitionRegion), "A")

        j.report_info["RecShelf"] = {
            "actionStatus": self.action_status,
            "currentRecFile": self.recfile,
            "fileIndex": f"{self.current_file_idx + 1}/{len(self.shelf_files)}",
            "recStatus": rec_status,
            "recAttempts": self.attempts,
            "recResult": j.rec_result,
        }
        Module.reportInfo(j.report_info)

class RecTargetObs(BaseAction):
    """识别货架"""

    def __init__(self, device_name):
        super().__init__()
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


class UpdateRackLastUsed(BaseAction):
    """
    取放货任务成功完成后写入 LastUsedAt。
    追加在 jackLoad 动作列表末尾（ClearPolicy 之后）。
    若 j.matched_recfile 为空（未启用识别），则跳过。
    """

    def __init__(self):
        super().__init__("UpdateRackLastUsed")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.opt_info = f"{self.__class__.__name__}{{}}"

    def run(self, j: Jack):
        if self.init:
            self.init = False
            matched_file = getattr(j, 'matched_recfile', None)
            if matched_file:
                rack_size_manager.on_recognition_success(matched_file)
                debug_trace(f"UpdateRackLastUsed: LastUsedAt 已写入 [{matched_file}]")
            else:
                debug_trace("UpdateRackLastUsed: matched_recfile 为空，跳过写入")
            self.action_status = ActionStatus.FINISHED

        j.report_info["UpdateRackLastUsed"] = {
            "actionStatus": self.action_status,
            "matchedRecFile": getattr(j, 'matched_recfile', None)
        }
        Module.reportInfo(j.report_info)

class GetPGVData(BaseAction):
    """获取二维码资料"""

    def __init__(self, use_which_pgv):
        super().__init__("GetPGVData")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.count = 0
        self.max_rec_num = 15
        if use_which_pgv == "useUpPgv":
            self.use_upside = True  # True = 上视, False = 下视
        else:
            self.use_upside = False
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

        # 根据输入参数选择对应 PGV（不再自动判断）
        for pgv in pgv_data:
            if not hasattr(pgv.codeScannerInfo, "isUpside"):
                continue

            if pgv.codeScannerInfo.isUpside == self.use_upside:
                chosen_pgv = pgv
                break

        # 如果没找到对应的PGV，直接报异常
        if chosen_pgv:
            self.tag_value = chosen_pgv.tagValue
            self.tag_diff_x = chosen_pgv.tagDiffX
            self.tag_diff_y = chosen_pgv.tagDiffY
            self.tag_diff_angle = chosen_pgv.tagDiffAngle
            self.is_DMT_detected = chosen_pgv.isDMTDetected
            self.codeScannerInfo = chosen_pgv.codeScannerInfo

        # 输出结构保持不变，新增 isUpside 字段
        j.code_info = {
            "tag_value": self.tag_value,
            "is_DMT_detected": self.is_DMT_detected,
            "tag_diff_x": self.tag_diff_x,
            "tag_diff_y": self.tag_diff_y,
            "tag_diff_angle": self.tag_diff_angle,
            "isUpside": self.use_upside
        }

        # 判断二维码识别逻辑
        if self.is_DMT_detected and self.tag_value != "":
            debug_trace(
                f"read code success: {self.tag_value} (use_upside={self.use_upside})"
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
    def __init__(self, world_target, min_ahead_dist=0, ahead_dist=0, back_dist=0, max_speed=0.5, max_angle=0.5,
                 dec_dist=1):
        """
        target_world, back_dist = 0.0, adjust_dist_for_curvature_limit = 2, min_ahead_dist = 0, is_backwards = False,
        max_speed = 0.5, max_accele = 0.3, max_decele = 0.2, decele_dist = 1, curvature_limit = 1.3
        """
        super().__init__()
        self.go3 = goPath.GoPath()
        self.go2 = goPath.GoPath()
        self.go1 = goPath.GoPath()
        self.go3_args = None
        self.go2_args = None
        self.go1_args = None
        self.temp_start = []
        self.first_point = None
        self.start_pos = []
        self.world_target = world_target
        self.min_ahead_dist = min_ahead_dist
        self.ahead_dist = ahead_dist
        self.back_dist = back_dist
        self.max_speed = max_speed
        self.max_angle = max_angle
        self.dec_dist = dec_dist
        self.step = 20
        self.second_point = pos2World([self.min_ahead_dist, 0, 0], self.world_target)
        self.third_point = pos2World([-self.back_dist, 0, 0], self.world_target)
        self.go_step = [False] * 3
        self.action_status = ActionStatus.INIT
        self.init = False
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

    def run(self, f):
        if not self.init:
            self.init = True
            pos = Loc.getData()
            self.start_pos = [pos['x'], pos['y'], pos['angle']]
            if abs(self.cal_angle(self.start_pos, self.second_point)) > self.max_angle:
                self.start_pos[2] = self.world_target[2]
                angle, self.temp_start = self.search_min_angle_str(self.max_angle, self.step)
            else:
                self.temp_start = self.start_pos
            self.go1_args = {
                "x": self.temp_start[0],
                "y": self.temp_start[1],
                "theta": self.temp_start[2],
                "backMode": 1,
                "maxSpeed": 0.2,
                "maxRot": math.radians(10),
                "coordinate": Coordinate.WORLD
            }
            self.go2_args = {
                "x": self.second_point[0],
                "y": self.second_point[1],
                "theta": self.second_point[2],
                "backMode": 0,
                "maxSpeed": 0.1,
                "maxRot": math.radians(10),
                "coordinate": Coordinate.WORLD
            }
            self.go3_args = {
                "x": self.third_point[0],
                "y": self.third_point[1],
                "theta": self.third_point[2],
                "backMode": 0,
                "maxSpeed": 0.1,
                "maxRot": math.radians(10),
                "coordinate": Coordinate.WORLD
            }

        if not self.go_step[0]:
            if self.go1.status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go1.run(self.go1_args)
            if self.go1.status == ActionStatus.FINISHED:
                self.go_step[0] = True
        elif self.go_step[0] and not self.go_step[1]:
            if self.go2.status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go2.run(self.go2_args)
            if self.go2.status == ActionStatus.FINISHED:
                self.go_step[1] = True
        elif self.go_step[1] and not self.go_step[2]:
            if self.go3.status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go3.run(self.go3_args)
            if self.go3.status == ActionStatus.FINISHED:
                self.go_step[2] = True
        if all(self.go_step):
            self.action_status = ActionStatus.FINISHED

    def cal_angle(self, start_pos, end_pos):
        start2end = pos2Base(start_pos, end_pos)
        angle = math.degrees(math.atan2(start2end[1], start2end[0]))
        print(angle)
        return angle

    def search_min_angle_str(self, max_angle, step):
        temp_start = []
        for n in range(1, step + 1):
            adjust_dist = self.ahead_dist / self.step * n
            # 临时构造一个新的起点：在原 start_pos 基础上往前平移
            temp_start = pos2World([adjust_dist, 0, 0], self.start_pos)
            angle = abs(self.cal_angle(temp_start, self.second_point))

            if angle <= max_angle:
                # self.first_point = temp_start
                print(f"满足角度要求，当前角度：{angle:.2f}°，使用第 {n} 次调整")
                return angle, temp_start  # 成功，返回当前角度

        angle = abs(self.cal_angle(temp_start, self.second_point))
        print(f"未满足角度要求，当前角度：{angle:.2f}°")
        return angle, temp_start

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class PGVSecondaryAdjust(BaseAction):  # 二次调整
    def __init__(self, use_which_pgv, pgv_x_adjust, pgv_x_angle_adjust, pgv_adjust_dist, pgv_reach_dist,
                 pgv_reach_angle, pgv_adjust_way):
        super().__init__("PGVSecondaryAdjust")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.adjust_param = dict()
        self.use_which_pgv = use_which_pgv
        self.pgv_x_adjust = pgv_x_adjust
        self.pgv_x_angle_adjust = pgv_x_angle_adjust
        self.pgv_adjust_dist = pgv_adjust_dist
        self.pgv_reach_dist = pgv_reach_dist
        self.pgv_reach_angle = pgv_reach_angle
        self.pgv_adjust_way = pgv_adjust_way

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.reset()
        self.set_adjust_param(j.code_info["tag_diff_x"], j.code_info["tag_diff_y"])
        self.action_status = Navigation.goPGVRun(self.adjust_param)

        j.report_info["PGVSecondaryAdjust"] = {
            "actionStatus": self.action_status,
            "codeInfo": j.code_info
        }
        Module.reportInfo(j.report_info)

    def set_adjust_param(self, pgv_adjust_cx, pgv_adjust_cy):
        # if self.use_which_pgv == "useUpPgv":
        #     self.adjust_param['R2AUP'] = True  # 使用上视pgv, args里需要增加use_pgv参数
        #     self.adjust_param['R2ADP'] = False  # 使用下视pgv
        # elif self.use_which_pgv == "useDownPgv":
        #     self.adjust_param['R2AUP'] = False  # 使用上视pgv, args里需要增加use_pgv参数
        #     self.adjust_param['R2ADP'] = True
        if self.use_which_pgv == "useUpPgv":
            self.adjust_param['R2AUP'] = True  # 使用上视pgv, args里需要增加use_pgv参数
            self.adjust_param['R2ADP'] = False  # 使用下视pgv
        elif self.use_which_pgv == "useDownPgv":
            self.adjust_param['R2AUP'] = False  # 使用上视pgv, args里需要增加use_pgv参数
            self.adjust_param['R2ADP'] = True
        if self.pgv_adjust_way == "pgvAdjust90":
            self.adjust_param['pgvAdjust90'] = True  # 当agv和外部设备对齐时， 理想里程中心在二维码坐标下的位姿 x
        elif self.pgv_adjust_way == "pgvAdjust180":
            self.adjust_param['pgvAdjust180'] = True  # 当agv和外部设备对齐时， 理想里程中心在二维码坐标下的位姿 x
        self.adjust_param['pgvXAdjust'] = self.pgv_x_adjust  # 按照x纵方向进行二次调整
        self.adjust_param['pgvXAngleAdjust'] = self.pgv_x_angle_adjust  # 沿着车子方向的偏差进行调整，并且到点后调整角度偏差
        self.adjust_param['pgvAdjustDist'] = self.pgv_adjust_dist  # 最大的调整半径,尽量小以二维码中心为圆心
        self.adjust_param['pgvAdjustCx'] = pgv_adjust_cx  # 调整范围的圆心为二维码坐标系下的坐标x
        self.adjust_param['pgvAdjustCy'] = pgv_adjust_cy  # 调整范围的圆心为二维码坐标系下的坐标y
        self.adjust_param['pgvReachDist'] = self.pgv_reach_dist  # pgv二次调整距离精度
        self.adjust_param['pgvReachAngle'] = self.pgv_reach_angle  # pgv二次调整角度精度

    def reset(self):
        debug_trace("reset PGV secondary adjustment")
        self.action_status = ActionStatus.RUNNING
        Navigation.resetGoPGV()


# --- 枚举定义 ---
# class Coordinate:
#     """ 坐标系枚举 """
#     ROBOT = "robot"
#     WORLD = "world"
#     INCREASE = "increase"


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
        "operation.jackLoad.recFile": "default.srec",
        "operation.jackLoad.insertShelfDir": "A",
        "operation.jackLoad.recognize": "OFF",
        "operation.jackLoad.howGoSite": "bezier",
        "operation.jackLoad.isSecondaryAdjust": "OFF",
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

# 添加 "jackUp" 动作模板
param_loader.addAction(
    action_name="jackUp",
    policy={},
    args={
        "operation": "jackHeight",
        "operation.jackHeight.endHeight": 0.06,
    },
    config={}
)

# 添加 "jackDown" 动作模板
param_loader.addAction(
    action_name="jackDown",
    policy={},
    args={
        "operation": "jackHeight",
        "operation.jackHeight.endHeight": 0,
    },
    config={}
)

# 保存动作模板到文件
param_loader.saveAction()

def main():
    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    Container.initContainer(max_id=0, self_id="0")
    validator = ParamValidator(InputParams.builder.toDict())
    j = Jack()

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
            j.matched_recfile = None  # 清空已匹配的货架尺寸文件
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
