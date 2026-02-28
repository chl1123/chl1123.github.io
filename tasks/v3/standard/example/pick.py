# -*- coding: utf-8 -*-
# @Date : 2026/1/27
# @Author : zhaopengfei
# @Coding : none
# @Update : P300配送车脚本

import json
import math
import time
import struct
import serial  # type: ignore
from enum import IntEnum
from typing import List, Optional
from syspy.utils.time import Timer

start_time = time.time()
from datetime import datetime
from syspy import (Module, Logger, Motor, Navigation, Loc, Abnormal, Recognize,
                   CodeScanner, ScriptStatus, Trace, NavSpeed, Controller, LevelDB)
from syspy.lib.module import pos2Base, pos2World, ModuleBase, SafeMoveStatus
from standard import goPath, goBezier
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ScriptParam

param_loader = ScriptParam(__file__)
from syspy.lib.robot_param import RobotParam
from syspy.utils import Coordinate

log = Logger("jack")


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
                Trace.log("JackCountManager: 数据库初始化完成")
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
            Trace.log(f"JackCountManager: 顶升次数已更新 - 累计={total_count + 1}, 今日={today_count + 1}")
        except Exception as e:
            Trace.log(f"JackCountManager: 更新顶升次数失败: {e}")


# 创建全局实例
jack_count_manager = JackCountManager()


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

        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        Trace.log("Reloading config parameters")
        cls.config = param_loader.loadConfig()
        Trace.log(f"Loaded config: {cls.config}")

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

        Trace.log(f"Updated config: debug_mode={cls.debug_mode}")


# 创建全局配置管理器实例
config_params = ConfigParams()

# ============================================================================
# 调试任务列表（需要开启 debugMode 才能执行）
# ============================================================================
DEBUG_ONLY_TASKS = [
    "jackHeight",  # 指定高度顶升（RS485推荐使用jackUp/jackDown）
    "goBezier",  # 贝塞尔导航
    "spinTray",  # 托盘旋转
    "rotateHoldSpin",  # 随动旋转
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
# RS485 Modbus RTU 顶升驱动器控制类
# ============================================================================
class RS485JackController:
    """
    RS485 Modbus RTU 顶升驱动器控制器
    替代原有的Motor API，通过串口直接控制顶升电机
    """

    # 控制状态码
    STATE_RESET_DONE = 3  # 复位完成
    STATE_TOP_REACHED = 5  # 到达顶部限位
    STATE_BOTTOM_REACHED = 9  # 到达底部限位
    STATE_ERROR = 4  # 发生错误

    # Modbus指令帧
    CMD_JACK_UP = [0xFF, 0x06, 0x00, 0x00, 0x00, 0x01, 0x5D, 0xD4]  # 伸出(触顶)
    CMD_JACK_DOWN = [0xFF, 0x06, 0x00, 0x00, 0x00, 0x02, 0x1D, 0xD5]  # 下降(触底)
    CMD_RESET = [0xFF, 0x06, 0x00, 0x00, 0x00, 0x03, 0xDC, 0x15]  # 复位
    CMD_READ_STATE = [0xFF, 0x03, 0x00, 0x00, 0x00, 0x01, 0x91, 0xD4]  # 读取控制状态
    CMD_READ_ERROR = [0xFF, 0x03, 0x00, 0x06, 0x00, 0x01, 0x71, 0xD5]  # 读取报错

    _instance = None
    _serial = None

    def __new__(cls, port='/dev/RS485_3', baudrate=9600):
        """单例模式，确保只有一个串口实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, port='/dev/RS485_3', baudrate=9600):
        if self._initialized:
            return
        self._initialized = True
        self.port = port
        self.baudrate = baudrate
        self._init_serial()

    def _init_serial(self):
        """初始化串口"""
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=0.5)
            if not self._serial.is_open:
                self._serial.open()
            Trace.log(f"RS485JackController: Serial port {self.port} opened")
        except Exception as e:
            Trace.log(f"RS485JackController: Failed to open serial port: {e}")
            self._serial = None

    def send_frame(self, frame: List[int]) -> int:
        """发送Modbus RTU帧，返回实际写入字节数"""
        if self._serial is None:
            self._init_serial()
        if self._serial is None:
            return 0
        # 清空接收缓冲区
        self._serial.reset_input_buffer()
        data = bytes(int(b) & 0xFF for b in frame)
        written = self._serial.write(data)
        self._serial.flush()  # 确保发送完成
        return written

    def recv_data(self, wait_time: float = 0.1) -> Optional[List[int]]:
        """
        接收并解析Modbus响应数据

        响应帧格式 (读寄存器 0x03):
        [从机地址][功能码][字节数][数据...][CRC低][CRC高]
        例如: FF 03 02 00 09 xx xx
              地址 功能 字节数 数据(2字节) CRC
        """
        if self._serial is None:
            return None

        import time
        time.sleep(wait_time)  # 等待响应

        # 读取所有可用数据
        buf = self._serial.read(self._serial.in_waiting or 7)

        if len(buf) < 5:
            Trace.log(f"RS485 recv too short: {len(buf)} bytes, data={buf.hex() if buf else 'empty'}")
            return None

        # 解析帧: [地址][功能码][字节数][数据...][CRC]
        addr = buf[0]  # 从机地址 0xFF
        func = buf[1]  # 功能码 0x03
        byte_cnt = buf[2]  # 数据字节数

        Trace.log(f"RS485 recv: addr=0x{addr:02X}, func=0x{func:02X}, byte_cnt={byte_cnt}, raw={buf.hex()}")

        # 检查是读寄存器响应
        if func == 0x03:
            # 期望长度: 地址(1) + 功能码(1) + 字节数(1) + 数据(byte_cnt) + CRC(2)
            expected_len = 3 + byte_cnt + 2
            if len(buf) >= expected_len:
                # 提取数据部分，解析为16位无符号整数
                data_bytes = buf[3:3 + byte_cnt]
                regs = list(struct.unpack('>' + 'H' * (byte_cnt // 2), data_bytes))
                Trace.log(f"RS485 parsed regs: {regs}")
                return regs
        elif func == 0x06:
            # 写单个寄存器的响应，原样返回
            Trace.log(f"RS485 write response received")
            return [0]  # 写成功

        return None

    def read_state(self) -> Optional[int]:
        """读取当前控制状态"""
        self.send_frame(self.CMD_READ_STATE)
        regs = self.recv_data()
        if regs is not None and len(regs) > 0:
            return regs[0]
        return None

    def is_top_reached(self) -> bool:
        """检查是否到达顶部"""
        state = self.read_state()
        return state == self.STATE_TOP_REACHED

    def is_bottom_reached(self) -> bool:
        """检查是否到达底部"""
        state = self.read_state()
        return state == self.STATE_BOTTOM_REACHED

    def is_at_limit(self) -> bool:
        """检查是否到达任意限位（顶部或底部）"""
        state = self.read_state()
        return state in (self.STATE_TOP_REACHED, self.STATE_BOTTOM_REACHED, self.STATE_RESET_DONE)

    def jack_up(self) -> bool:
        """发送顶升指令（只发一次），返回发送是否成功"""
        self.send_frame(self.CMD_JACK_UP)
        self.recv_data()  # 读取响应但不处理
        return True

    def jack_down(self) -> bool:
        """发送下降指令（只发一次），返回发送是否成功"""
        self.send_frame(self.CMD_JACK_DOWN)
        self.recv_data()  # 读取响应但不处理
        return True

    def reset(self) -> bool:
        """发送复位指令"""
        self.send_frame(self.CMD_RESET)
        self.recv_data()  # 读取响应但不处理
        return True

    def check_and_report_error(self) -> Optional[int]:
        """检查错误状态并返回错误码，同时上报异常"""
        state = self.read_state()
        if state != self.STATE_ERROR:
            return None

        # 读取详细错误码
        self.send_frame(self.CMD_READ_ERROR)
        regs = self.recv_data()
        if regs is None or len(regs) == 0:
            return None

        error = regs[0]
        self._report_error(error)
        return error

    def _report_error(self, error: int):
        """根据错误码上报异常"""
        error_messages = {
            1: "上电时电压低于8V，检查/更换电源，重新上电",
            2: "运行时，电源功率不足，电压拉低于8V，检查/更换电源，重新上电",
            5: "控制器受干扰，需要排除干扰源，重新上电",
            6: "硬件异常,返厂维修",
        }

        if error in error_messages:
            Abnormal.setTask(53980, error_messages[error],
                             "顶升驱动器报错", "检查顶升驱动器", "顶升控制")
        elif error in (3, 4):
            # 错误码3,4需要执行复位
            self.reset()
        elif error // 10 >= 1:
            # 电机相关错误
            n = error // 10
            sub_error = error % 10
            motor_errors = {
                0: f"电机{n}旋转方向错误，调换直流电机线或霍尔相线",
                1: f"电机{n}霍尔1缺相，检查霍尔1或连线",
                2: f"电机{n}霍尔2缺相，检查霍尔2或连线",
                3: f"电机{n}霍尔信号异常，检查霍尔供电(5V和GND)和连接线",
                4: f"电机{n}未连接，检查推杆接线是否脱落或直流电机故障",
                5: f"电机{n}堵转保护，检查电机是否内部短路或堵转",
                6: f"电机{n}过流/过载保护，减小负载",
            }
            if sub_error in motor_errors:
                Abnormal.setTask(53980, motor_errors[sub_error],
                                 "顶升电机报错", "检查顶升电机", "顶升控制")


# 创建全局RS485控制器实例
rs485_jack_controller: Optional[RS485JackController] = None


def get_rs485_jack_controller(port='/dev/RS485_3') -> RS485JackController:
    """获取RS485控制器单例"""
    global rs485_jack_controller
    if rs485_jack_controller is None:
        rs485_jack_controller = RS485JackController(port)
    return rs485_jack_controller


def script_config_callback():
    Trace.log("Reloading script config parameters")
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

    with builder.CHILD(key="isRecognize", name="isRecognize",
                       desc="Enable recognition"):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE(0)
        with builder.CHILDREN():
            # OFF 选项，不需要填识别文件
            with builder.CHILD(key="OFF", name="OFF",
                               desc="Load Without Recognition"):
                builder.TYPE(ParamType.ARRAY)
            # ON 也就是勾选需要识别后才会需要填写识别文件
            with builder.CHILD(key="ON", name="ON",
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
        builder.DEFAULTVALUE(0)
        with builder.CHILDREN():
            # OFF 选项，不需要填二次调整内容
            with builder.CHILD(key="OFF", name="OFF",
                               desc="Load Without secondary_adjust"):
                builder.TYPE(ParamType.ARRAY)
            # ON 也就是勾选需要二次调整后才会出现二次调整相关内容
            with builder.CHILD(key="ON", name="ON",
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
    - 调试任务（debugMode=true时显示）：jackHeight, goBezier, spinTray, rotateHoldSpin等
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

                # ============================================
                # 调试/低频任务（需要开启debugMode才显示）
                # ===========================================
                if config_params.debug_mode:
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
                        with builder.CHILDREN():
                            create_ap_id(builder)

                    with builder.CHILD(key="getLM", name="getLM",
                                       desc="get the position of landmark"):
                        builder.TYPE(ParamType.ARRAY)
                        create_ap_id(builder)

                    with builder.CHILD(key="laserAreaDeduction", name="laserAreaDeduction",
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
                        with builder.CHILD(key="coordinate", name="coordinate", desc="Spin coordinate"):
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
        self.info_count = 0
        self.jack_spin = None
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
        self.spin_angle = None
        self.action_parameters = None  # vda
        self.recfile = None
        self.how_go_site = None
        # 取货前调整托盘旋转
        self.spin_dir = None

        # 货架识别
        self.rec_result = []
        # 二维码识别
        self.code_info = dict()

        # 数据打印
        self.report_info = {}
        Abnormal.clear(53780)
        Abnormal.clear(53781)
        Abnormal.clear(53782)
        Abnormal.clear(53783)

        # robotParam
        self.lift_motor = None

        Trace.log(f"moduleType = {config_params.module_type}")
        Trace.log(f"jackMotorName = {config_params.jack_motor_name}")
        Trace.log(f"jackMinHeight = {config_params.jack_min_height}")
        Trace.log(f"jackMaxHeight = {config_params.jack_max_height}")
        Trace.log(f"jackUpDi = {config_params.jack_up_di}")
        Trace.log(f"jackZeroDi = {config_params.jack_zero_di}")

        self.status = ScriptStatus.NONE

        self.cur_action_list = []

    def _init_args(self, args):
        self.task_args = args
        # 获取任务参数
        self.opt = self.task_args.get("operation", None)
        self.ap_id = self.task_args.get("targetName", None)
        # 顶升高度相关
        self.start_height = self.task_args.get("startHeight", 0)
        self.end_height = self.task_args.get("endHeight", 0.06)
        # 识别相关
        self.is_recognize = self.task_args.get("isRecognize", None)
        self.recfile = self.task_args.get("recFile", "default.srec")
        self.insert_shelf_dir = self.task_args.get("insertShelfDir", "A")
        # spin,rotate相关
        self.spin_angle = self.task_args.get("spinAngle", 0)  # 角度
        rad = math.radians(self.spin_angle)  # 把spin_angle转为rad
        self.spin_angle = (rad + math.pi) % (2 * math.pi) - math.pi  # 归一化到 (-pi, pi]
        self.spin_dir = self.task_args.get("spinDir", 0)
        self.coordinate = self.task_args.get("coordinate", "world")
        self.spin_mode = self.task_args.get("spinMode", "increase")
        self.is_spin_follow = self.task_args.get("isSpinFollow", False)
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
        elif self.opt == "jackUp":  # 顶升到顶（推荐）
            self.jack_up()
        elif self.opt == "jackDown":  # 下降到底（推荐）
            self.jack_down()
        elif self.opt == "rotateHoldSpin":  # 随动转
            self.rotate_hold_spin()
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
        Trace.log(f'{self.action_id=}, {self.cur_action_list=}')
        # Trace.log(f'{current_action.action_name=}, {current_action.action_status=}')

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

    def laser_area_deduction(self):
        if not self.operation_init:
            self.operation_init = True

            if self.create_or_delete_deducted_area == "create":

                self.laser_area_deduct_info = self.laser_area_deduct(self.recfile, "shelf")
                robot_loc = [Loc.getPose()["x"], Loc.getPose()["y"], math.radians(Loc.getPose()["yaw"])]
                Trace.log(f"robot_loc = {robot_loc}")
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
        print(f"\n{'=' * 60}")
        print(f"laser_area_deduct: 开始解析识别文件")
        print(f"  recfile = {recfile}")
        print(f"  object_key = {object_key}")
        print(f"{'=' * 60}")

        if not recfile:
            print("laser_area_deduct: No recfile provided")
            return None

        try:
            recognition_obstacle_deduction_path = f"recognitionObject.{object_key}.obstacleDeduction"
            print(f"  配置路径: {recognition_obstacle_deduction_path}")

            # 1) 获取数组大小
            size = RobotParam.getConfigCloneSize("recognition", recognition_obstacle_deduction_path, recfile)
            print(f"  obstacleDeduction 数组大小: {size}")

            if size is None or size == 0:
                print(f"laser_area_deduct: No obstacleDeduction config in {recfile}")
                return None

            # 合并所有设备和区域
            all_devices = []
            all_areas = []

            # 2) 遍历数组 (._0, ._1, ...)
            for i in range(size):
                print(f"\n  --- 读取第 {i} 组配置 ---")

                # 获取设备ID (注意路径格式: ._{i}.deductDevice)
                device_str = RobotParam.getConfig(
                    "recognition",
                    f"{recognition_obstacle_deduction_path}._{i}.deductDevice",
                    recfile
                )
                print(f"    deductDevice 原始值: {device_str}")

                if not device_str:
                    print(f"    跳过: 无 deductDevice")
                    continue

                devices = [d.strip() for d in device_str.split(",") if d.strip()]
                print(f"    deductDevice 解析后: {devices}")

                # 获取形状信息 (注意路径格式: ._{i}.deductShape)
                shape_str = RobotParam.getConfig(
                    "recognition",
                    f"{recognition_obstacle_deduction_path}._{i}.deductShape",
                    recfile
                )
                print(f"    deductShape 原始值: {shape_str[:100] if shape_str else None}...")

                if not shape_str:
                    print(f"    跳过: 无 deductShape")
                    continue

                shapes = json.loads(shape_str)
                print(f"    deductShape 解析后: {len(shapes)} 个形状")

                # 解析每个形状
                for idx, shape in enumerate(shapes):
                    pts = shape.get("points", [])
                    print(f"      Shape {idx}: {len(pts)} points")
                    if len(pts) < 3:
                        print(f"        跳过: 点数不足3个")
                        continue
                    x_list = [p["x"] for p in pts]
                    y_list = [p["y"] for p in pts]
                    all_areas.append({"xList": x_list, "yList": y_list})
                    print(f"        xList: {x_list}")
                    print(f"        yList: {y_list}")

                # 合并设备列表
                for d in devices:
                    if d not in all_devices:
                        all_devices.append(d)

            if not all_areas:
                print("\nlaser_area_deduct: No valid areas found")
                return None

            info = {
                "deductDevice": all_devices,
                "area": all_areas
            }

            print(f"\n{'=' * 60}")
            print(f"laser_area_deduct: 解析完成!")
            print(f"  设备: {info['deductDevice']}")
            print(f"  区域数量: {len(info['area'])}")
            print(f"{'=' * 60}\n")

            Trace.log(f"laser_area_deduct: Parsed info={info}")
            return info

        except json.JSONDecodeError as e:
            print(f"laser_area_deduct: JSON parse error - {e}")
            Trace.log(f"laser_area_deduct: JSON parse error - {e}")
            return None
        except Exception as e:
            print(f"laser_area_deduct: Error - {e}")
            import traceback
            traceback.print_exc()
            Trace.log(f"laser_area_deduct: Error - {e}")
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
            Abnormal.setTask(53325, f"Recognition side '{side_name}' not found in {object_key}",
                             "recognize file param wrong", "check the param", "get_back_distance_info")
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
            Abnormal.setTask(53325, f"Invalid back_distance_info, found None: {info}, script failed",
                             "recognize file param wrong", "check the param", "get_back_distance_info")
            self.status = ScriptStatus.FAILED

        Trace.log(f"backDistanceInfo = {info}")
        return info

    def rec_target_obs(self):
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(RecTargetObs("laser1"))

    def set_vda_param(self):
        # VDA下发的参数
        self.action_parameters = self.task_args.get("action_parameters", None)

    def get_lm(self):
        Trace.log("getLM ==============================================")
        result = Navigation.getLM(self.ap_id, True)
        self.report_info["getLM"] = {
            "LM": result
        }
        Module.reportInfo(self.report_info)
        Trace.log(f"getLM={result}")
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

            # === 初始化时解析并设置扣除区域配置 ===
            if self.recfile:
                self.laser_area_deduct_info = self.laser_area_deduct(self.recfile, "shelf")
                Trace.log(f"jack_load: Parsed laser deduct info: {self.laser_area_deduct_info}")
                self.action_list.append(SetLaserDeductArea(self.laser_area_deduct_info))

            # 下降到起始高度
            if self.start_height:
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, self.start_height, config_params.jack_motor_speed))

            # 获取AP点
            self.ap_id = self.ap_id or self.get_ap()
            if not self.ap_id:
                Abnormal.setTask(53779, "lost ap id", "", "", "")
                return

            Trace.log(f"jack_load: ap_id={self.ap_id}")
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)
            Trace.log(f"jack_load: AP_pos={self.ap_world_pos}")

            self.report_info["jack_load"] = {"apWorldPos": self.ap_world_pos}

            # 转到与AP点方向一致
            self.action_list.append(RobotRotate(math.degrees(self.ap_world_pos[2]), Coordinate.WORLD, False))

            # 启用识别
            if self.is_recognize:
                self.action_list.append(RecShelf(self.recfile, "FirstRec"))

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
                    if self.back_dist is None:
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

                # 顶升
                self.action_list.append(
                    JackHeight(config_params.jack_motor_name, self.end_height, config_params.jack_motor_speed,
                               self.recfile))

                # 取货完成后清除策略
                self.action_list.append(ClearPolicy())

    def jack_unload(self):
        """
        完整放货流程：下降托盘 → 删除激光扣除区域
        """
        if not self.operation_init:
            self.operation_init = True
            Trace.log("jack_unload: Starting unload sequence")

            # 下降托盘
            self.action_list.append(
                JackHeight(config_params.jack_motor_name, 0, config_params.jack_motor_speed, self.recfile))

            # === 放货完成后删除激光扣除区域 ===
            self.action_list.append(DeleteLaserDeductArea())

    def go_ap_site(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            Trace.log(f'AP_pos: {self.ap_world_pos}')
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
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            Trace.log(f'AP_pos: {self.ap_world_pos}')
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
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在机器人坐标系下的位置
            Trace.log(f'AP_pos: {self.ap_world_pos}')
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

    def rotate_hold_spin(self):
        """旋转车体时启动随动"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(RobotRotate(self.spin_angle, self.coordinate, self.is_spin_follow))

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
                Abnormal.setTask(53780, f"execute action {current_action} failed!",
                                 "",
                                 "",
                                 "execute_actions")
                self.status = ScriptStatus.FAILED
            else:
                current_action.run(self)
        else:
            self.status = ScriptStatus.FINISHED
            self.action_list = []
        # Trace.log(f'{self.action_id=}, {self.action_list=}')
        # Trace.log(f"self.action_list: {self.action_list}")

    def suspend(self):
        self.status = ScriptStatus.SUSPENDED
        Trace.log("suspend")

    def resume(self):
        if self.status == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        Trace.log("resume")

    def cancel(self):
        self.status = ScriptStatus.FAILED
        Trace.log("cancel")

    def safe_move_check(self):
        self.count += 1
        status = SafeMoveStatus.RUNNING
        if self.count == 100:
            self.count = 0
            status = SafeMoveStatus.FINISHED
        self.setSafeMoveStatus(status)
        Trace.log(f"safe_move_check {Module.getSafeMoveCheck()}")
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False

    def set_info(self):
        self.jack_motors = NavSpeed.getMotorCmd()
        # print(f"jack_motors= {self.jack_motors}")
        # for jack_motor in jack_motors:
        #     jack_state = jack_motor.jack_state
        #     jack_speed = jack_motor.jack_speed
        self.jack_speed = Motor.getMotorSpeed(config_params.jack_motor_name)
        self.jack_isFull = Navigation.hasGoods()
        self.jack_emc = Controller.getEmc()
        self.jack_height = Motor.getMotorPos(config_params.jack_motor_name)
        self.report_info.update({
            "jackMode": True,
            "jackEnable": True,
            # "jack_state": jack_state,
            "jackSpeed": self.jack_speed,
            "jackEmc": self.jack_emc,
            "jackIsFull": self.jack_isFull,
            "jackHeight": self.jack_height,
            "jackSpin": self.jack_spin
        })
        # self.report_info["motor_info"] = {
        #     "motor_infos": motor_infos
        # }
        Module.reportInfo(self.report_info)
        self.info_count = self.info_count + 1
        # print(f"--------------setinfo---{self.info_count}---{self.jack_spin}-----------")

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
                Trace.log("SetLaserDeductArea: No deduct info, skipping")
                self.action_status = ActionStatus.FINISHED
                return

            try:
                devices = self.deduct_info.get("deductDevice", [])
                areas = self.deduct_info.get("area", [])

                Trace.log(f"SetLaserDeductArea: Setting {len(areas)} areas, devices={devices}")

                for idx, area in enumerate(areas, start=1):
                    x_list = area.get("xList", area.get("x_list", []))
                    y_list = area.get("yList", area.get("y_list", []))

                    if len(x_list) < 3 or len(x_list) != len(y_list):
                        Trace.log(f"SetLaserDeductArea: Skip invalid area idx={idx}")
                        continue

                    region_name = f"{self.prefix}{idx}"
                    Navigation.setClearRegion(region_name, x_list, y_list, devices, self.coordinate)
                    Trace.log(f"SetLaserDeductArea: Created {region_name}")

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
                            Trace.log(f"DeleteLaserDeductArea: Deleted {region}")
                            deleted_count += 1

                Trace.log(f"DeleteLaserDeductArea: Deleted {deleted_count} regions")
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
            Trace.log("ClearPolicy: 已清除导航策略，恢复绕行设置")
            self.action_status = ActionStatus.FINISHED

class RobotRotate(BaseAction):
    """只转车不转托盘"""

    def __init__(self, angle, coordinate, spin=True, direction=None):
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
                self.move_args["locMode"] = 1  # 激光定位

                # 1. 当前朝向：Loc 返回的是度 - 立即转弧度 - 归一化
                cur_angle_rad = self.normalize(math.radians(Loc.getPose()["yaw"]))

                # 2. 目标朝向：外部传进来是“度” - 先转弧度，再归一化
                target_rad = self.normalize(math.radians(self.angle) if abs(self.angle) > math.pi else self.angle)

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
        Trace.log(f"{status=}")
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
        Trace.log("reset RobotRotate")
        self.action_status = ActionStatus.RUNNING

    def normalize(self, rad: float) -> float:
        """把任意弧度角归一化到 (-π, π] 区间"""
        return (rad + math.pi) % (2 * math.pi) - math.pi


class JackHeight(BaseAction):
    """
    顶升动作，通过RS485 Modbus RTU协议控制
    根据目标高度判断升降方向
    """

    def __init__(self, motor_name, target_height, jack_motor_speed, recfile=None, object_key="shelf"):
        super().__init__("JackHeight")

        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.motor_name = motor_name
        self.target_height = target_height
        print(f"{self.target_height=}")
        self.jackMotorSpeed = jack_motor_speed
        self.recfile = recfile
        self.object_key = object_key
        self.init = False
        self.cmd_sent = False
        self.is_going_up = True
        self._count_recorded = False  # 防止重复计数

        self.rs485_ctrl = get_rs485_jack_controller()

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING

            state = self.rs485_ctrl.read_state()
            Trace.log(f"JackHeight init: target={self.target_height}, current_state={state}")

            # 根据目标高度判断升降方向
            max_h = config_params.jack_max_height or 0.3
            min_h = config_params.jack_min_height or 0.0
            threshold = (max_h + min_h) / 2
            self.is_going_up = self.target_height > threshold

            Trace.log(f"JackHeight: target={self.target_height}, threshold={threshold}, is_going_up={self.is_going_up}")

        # 只发送一次指令
        if not self.cmd_sent:
            self.cmd_sent = True
            if self.is_going_up:
                Trace.log("JackHeight: Sending CMD_JACK_UP")
                self.rs485_ctrl.jack_up()
            else:
                Trace.log("JackHeight: Sending CMD_JACK_DOWN")
                self.rs485_ctrl.jack_down()

        # 读取RS485状态
        state = self.rs485_ctrl.read_state()
        Trace.log(f"RS485 state={state}, is_going_up={self.is_going_up}")

        # 检查是否到达目标位置
        if self.is_going_up:
            if state == RS485JackController.STATE_TOP_REACHED:
                self.action_status = ActionStatus.FINISHED
                # 顶升完成，记录次数
                if not self._count_recorded:
                    self._count_recorded = True
                    jack_count_manager.increment_count()
                    Trace.log("JackHeight: 顶升次数已记录")
                # 设置货物形状
                if self.recfile:
                    try:
                        recognition_goodsParameter_path = f"recognitionObject.{self.object_key}.goodsParameter"
                        goods_shape = RobotParam.getConfig("recognition",
                                                           f"{recognition_goodsParameter_path}.goodsShape",
                                                           self.recfile)
                        shapes = json.loads(goods_shape)
                        shape = shapes[0]["points"]
                        Navigation.setGoodsPolyShape(shape, "shelf")
                    except Exception as e:
                        Trace.log(f"JackHeight: 加载货物形状失败: {e}")
                        shape = [{"x": 0.5, "y": 0.3}, {"x": -0.5, "y": 0.3},
                                 {"x": -0.5, "y": -0.3}, {"x": 0.5, "y": -0.3}]
                        Navigation.setGoodsPolyShape(shape, "shelf")
                else:
                    shape = [{"x": 0.5, "y": 0.3}, {"x": -0.5, "y": 0.3},
                             {"x": -0.5, "y": -0.3}, {"x": 0.5, "y": -0.3}]
                    Navigation.setGoodsPolyShape(shape, "shelf")
                Trace.log("JackHeight finished - reached top")
        else:
            if state == RS485JackController.STATE_BOTTOM_REACHED:
                self.action_status = ActionStatus.FINISHED
                Navigation.clearGoodsShape()
                Trace.log("JackHeight finished - reached bottom")

        # 检查错误状态
        if state == RS485JackController.STATE_ERROR:
            self.rs485_ctrl.check_and_report_error()

        j.report_info["JackHeight"] = {
            "actionStatus": self.action_status,
            "motorName": self.motor_name,
            "jackMotorSpeed": self.jackMotorSpeed,
            "rs485State": state,
            "isGoingUp": self.is_going_up,
        }
        Module.reportInfo(j.report_info)


class JackUpDown(BaseAction):
    """
    顶升/下降动作（推荐使用，不需要指定高度）
    - direction="up": 顶升到顶
    - direction="down": 下降到底
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
        self.cmd_sent = False
        self._count_recorded = False

        self.rs485_ctrl = get_rs485_jack_controller()

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            Trace.log(f"JackUpDown init: direction={self.direction}")

        # 只发送一次指令
        if not self.cmd_sent:
            self.cmd_sent = True
            if self.direction == "up":
                Trace.log("JackUpDown: Sending CMD_JACK_UP")
                self.rs485_ctrl.jack_up()
            else:
                Trace.log("JackUpDown: Sending CMD_JACK_DOWN")
                self.rs485_ctrl.jack_down()

        # 读取RS485状态
        state = self.rs485_ctrl.read_state()
        Trace.log(f"RS485 state={state}, direction={self.direction}")

        # 检查是否完成
        if self.direction == "up":
            if state == RS485JackController.STATE_TOP_REACHED:
                self.action_status = ActionStatus.FINISHED
                # 顶升完成，记录次数
                if not self._count_recorded:
                    self._count_recorded = True
                    jack_count_manager.increment_count()
                    Trace.log("JackUpDown: 顶升次数已记录")
                # 设置货物形状
                if self.recfile:
                    try:
                        recognition_goodsParameter_path = f"recognitionObject.{self.object_key}.goodsParameter"
                        goods_shape = RobotParam.getConfig("recognition",
                                                           f"{recognition_goodsParameter_path}.goodsShape",
                                                           self.recfile)
                        shapes = json.loads(goods_shape)
                        shape = shapes[0]["points"]
                        Navigation.setGoodsPolyShape(shape, "shelf")
                    except Exception as e:
                        Trace.log(f"JackUpDown: 加载货物形状失败: {e}")
                        shape = [{"x": 0.5, "y": 0.3}, {"x": -0.5, "y": 0.3},
                                 {"x": -0.5, "y": -0.3}, {"x": 0.5, "y": -0.3}]
                        Navigation.setGoodsPolyShape(shape, "shelf")
                else:
                    shape = [{"x": 0.5, "y": 0.3}, {"x": -0.5, "y": 0.3},
                             {"x": -0.5, "y": -0.3}, {"x": 0.5, "y": -0.3}]
                    Navigation.setGoodsPolyShape(shape, "shelf")
                Trace.log("JackUpDown finished - reached top")
        else:
            if state == RS485JackController.STATE_BOTTOM_REACHED:
                self.action_status = ActionStatus.FINISHED
                Navigation.clearGoodsShape()
                Trace.log("JackUpDown finished - reached bottom")

        # 检查错误状态
        if state == RS485JackController.STATE_ERROR:
            self.rs485_ctrl.check_and_report_error()

        j.report_info["JackUpDown"] = {
            "actionStatus": self.action_status,
            "direction": self.direction,
            "rs485State": state,
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
            Trace.log(f"bezier_status={self.bezier_status}")
        elif self.bezier_status == ActionStatus.FAILED:
            self.action_status = ActionStatus.FAILED
        elif self.bezier_status == ActionStatus.FINISHED:
            if self.bezier_return_status in (ActionStatus.INIT, ActionStatus.RUNNING):
                self.bezier_return_status = self.go_bezier_return.run()
                Trace.log(f"bezier_return_status={self.bezier_return_status}")
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
        Trace.log(f"bezier_status={self.action_status}")
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
        Trace.log(f"bezier_return_status={self.action_status}")
        time.sleep(0.1)


class RecShelf(BaseAction):
    """识别货架"""

    def __init__(self, shelf_file, action_name="RecShelf"):
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
        Recognize.resetRec()

        self.recognitionRegion = {
            "points": [{"x": -2.56, "y": -1.035}, {"x": -0.63, "y": -1.035}, {"x": -0.63, "y": 1.035},
                       {"x": -2.56, "y": 1.035}], "shape": "rectangle"}


        self.report_info = {}

    def run(self, j: Jack):
        self.action_status = ActionStatus.RUNNING
        Trace.log("recognizing the shelf")
        rec_status = Recognize.getRecStatus()
        Trace.log(f"{rec_status=}")
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            Trace.log(f"{rec_result=}")
            Recognize.resetRec()
            Trace.log(f"rec_result={rec_result}")
            rec_x = rec_result['recoList'][0]['x']
            rec_y = rec_result['recoList'][0]['y']
            rec_yaw = rec_result['recoList'][0]['yaw']
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
                    Abnormal.setTask(53781,
                                     "Recognition failed, the maximum number of retries exceeded",
                                     "The recognition distance may be too close or too far, or the sensor used for recognition may be faulty",
                                     "Check whether the recognition distance is too close or too far and whether the sensor used for recognition is normal.",
                                     "Recognize the shelf")
                else:
                    Recognize.resetRec()
                    self.do_rec = False
        elif rec_status == 0:
            self.do_rec = True
            Recognize.doRec(self.recfile, json.dumps(self.recognitionRegion), "A")
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
                self.ap_id = "AP" + str(self.ap_id)
            self.target_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置

            # 获取qrcode的偏移数值，并补偿到终点坐标中
            self.pgv_info[0] = j.code_info["tag_diff_x"]  # 上视pgv读到的货架在车体坐标系偏移,用于补偿货架机械偏差
            self.pgv_info[1] = j.code_info["tag_diff_y"]
            self.pgv_info[2] = j.code_info["tag_diff_angle"]
            if abs(self.pgv_info[0]) > 0.02 and abs(self.pgv_info[1]) > 0.02:
                self.action_status = ActionStatus.FAILED
                Abnormal.setTask(53783,
                                 f"PGV diff_x or diff_y out of range:0.02",
                                 "The QR code of the goods is too biased",
                                 "Check whether there is any deviation of goods when picking up",
                                 "Adjust AP point position with goods QR code deviation")

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
            Trace.log(
                f"read code success: {self.tag_value} (use_upside={self.use_upside})"
            )
            self.action_status = ActionStatus.FINISHED
        else:
            self.count += 1
            if self.count >= self.max_rec_num:
                Abnormal.setTask(53782,
                                 f"Rec times over max {self.count} NO shelf_code or recognized code fail or shelf_code is Null",
                                 "The pgv camera is faulty or the robot does not move above or below the QR code",
                                 "Check the position of the QRcode and the installation pos of PGV camera ",
                                 "Secondary adjustment with PGV")

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
        Trace.log("reset PGV secondary adjustment")
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


def main():
    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    validator = ParamValidator(InputParams.builder.toDict())
    j = Jack()

    while True:
        status = j.status
        Module.setStatus(status)
        # 打印数据
        j.set_info()

        # 脚本任务状态管理
        if j.event_safe_move_check:
            j.safe_move_check()

        if status == ScriptStatus.NONE:
            input_params = Module.getTaskArgs()
            if input_params:
                try:
                    print("task args:", json.dumps(input_params, indent=2))
                    # 验证参数
                    validated_params = validator.validate(input_params)
                    print("check ok, args:", json.dumps(validated_params, indent=2))

                    j._init_args(validated_params)
                except ValueError as e:
                    print("check error:", e)
                    Abnormal.setTask(53780, f"Input error:{e}", "some input params are not valid",
                                     "check the input params", "input check")

        elif status == ScriptStatus.RUNNING:
            j.run()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            j.action_id = 0
            j.action_list = []
            j.operation_init = False
            j.status = ScriptStatus.NONE

        time.sleep(0.1)


if __name__ == '__main__':
    main()