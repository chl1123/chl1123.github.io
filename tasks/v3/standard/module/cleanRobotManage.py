# -*- coding: utf-8 -*-
# @Date : 2025/1/26
# @Author : zeng
# @File : cleanRobotManage.py
#
# 说明：
# - 管理清洁任务：接车载屏/单车平台任务、监控电池和水位，并给调度系统发送 HTTP 运单。
# - 包含多个状态机：ERP状态机、机构状态机、车辆状态机、BoustrophedonPath状态机
# - 提供外部调用接口 run()，可直接触发 cleanRobotMech 的机构动作。
#
# 运单格式说明：
# - 站点list格式: LM1-AP2-CA1-AP3-AP4-CA2-AP5
# - CA 表示清洁区域，其他都是站点
# - 运单包含：机器人名称、优先级、运行时刻等
#
# 重要更新 (2025/12/08)：
# - M4调度系统不会自动中断低优先级运单
# - 发送充电/换水运单前，需先取消当前清洁运单
# - 充电/换水完成后，从断点恢复清洁任务
# - 使用机器人坐标位置（而非进度百分比）实现断点续扫
#
# 接口说明：
# - goBoustrophedonPath(entrance, exit, startPos, params): 执行弓字形清扫
# - cancelBoustrophedonPath(): 取消清扫，返回当前位置
# - resetBoustrophedonPath(): 重置清扫状态
#

import json
import math
import time
import datetime
import base64
import threading
from typing import Any, Dict, List, Optional, Tuple
from enum import IntEnum
import requests
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp

from syspy import (
    Module,
    ScriptStatus,
    Trace as RbkTrace,
    Navigation,
    Battery,
    Controller,
    Loc,
    Logger,
    Do,
    Can,
    NavStatus,
    NavSpeed,
    LevelDB,
)

from syspy.lib.robot import RobotParam
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ScriptParam


class Trace:
    """为本脚本日志按配置统一添加时间。"""

    LOG_FILE = f"/home/cleanRobotManage_{time.strftime('%Y%m%d_%H%M%S')}.log"
    file_error_logged = False

    @staticmethod
    def log(message):
        if getattr(globals().get("ConfigParams"), "addTime", False):
            message = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        RbkTrace.log(message)
        Trace._write_file(message)

    @staticmethod
    def debug(message):
        """仅在开启日志落盘时记录高频调试信息，避免刷屏。"""
        if not getattr(globals().get("ConfigParams"), "logWrite", False):
            return
        if getattr(globals().get("ConfigParams"), "addTime", False):
            message = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        Trace._write_file(message)

    @staticmethod
    def _write_file(message):
        if getattr(globals().get("ConfigParams"), "logWrite", False):
            try:
                with open(Trace.LOG_FILE, "a", encoding="utf-8") as log_file:
                    log_file.write(f"{message}\n")
            except Exception as exc:
                if not Trace.file_error_logged:
                    RbkTrace.log(f"Failed to write log file {Trace.LOG_FILE}: {exc}")
                    Trace.file_error_logged = True


# 本脚本自己的 param loader
param_loader = ScriptParam(__file__)


# 添加动作
for action_name in [
    "WashStart",
    "WashEnd",
    "MechanismOpen",
    "MechanismClose",
    "DustStart",
    "DustEnd",
    "Charge",
    "AddWater",
    "RunCleanPath",
    "RunCleanPathAndWashStart",
    "CancelCleanPath",
    "ResetCleanPath",
]:
    param_loader.addAction(
        action_name=action_name,
        policy={},
        args={"operation": action_name},
        config={}
    )
param_loader.saveAction()


class ConfigParams:
    """Shared config for clean robot manage/mech modules."""

    config: Dict[str, Any] = {}
    addTime = False
    logWrite = False

    def __init__(self):
        self.build_and_load_config()

    @classmethod
    def build_and_load_config(cls):
        _ = RobotParam.getDevice("Model-000", "moduleType")
        existing_config = {}
        migrate_basic_config = False
        try:
            with open(param_loader.config_file, "r", encoding="utf-8") as config_file:
                existing_definition = json.load(config_file)
            migrate_basic_config = any(
                group.get("key") == "basicConfig"
                for group in existing_definition.get("groups", [])
            )
            if migrate_basic_config:
                existing_config = param_loader.loadConfig()
        except FileNotFoundError:
            pass

        builder = param_loader.builderConfig()

        with builder.GROUPS():
            with builder.GROUP(
                    key="generalConfig",
                    name="通用配置",
                    desc="脚本运行模式和通用参数"
            ):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(
                            key="isDebug",
                            name="isDebug",
                            desc="调试模式：启动后立即尝试发送一次定时清洁运单",
                    ):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

                    with builder.CHILD(
                            key="isTrue",
                            name="isTrue",
                            desc="仿真模式：接管原 isDebug 的仿真行为",
                    ):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

                    with builder.CHILD(
                            key="simulation_charge_enabled",
                            name="simulation_charge_enabled",
                            desc="是否启用仿真充电流程",
                    ):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

                    with builder.CHILD(
                            key="addTime",
                            name="addTime",
                            desc="日志是否添加年月日时分秒",
                    ):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

                    with builder.CHILD(
                            key="logWrite",
                            name="logWrite",
                            desc="是否将日志写入/home文件",
                    ):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(False)

                    with builder.CHILD(key="timeout", name="timeout", desc="脚本运行超时时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(120.0, min_value=0.000, max_value=999)
                        builder.UNIT("s")
                        builder.SINGLESTEP(0.001)

            with builder.GROUP(
                    key="m4Config",
                    name="M4调度配置",
                    desc="M4调度连接、场景和机器人参数"
            ):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(key="scene_id", name="scene_id", desc="M4 场景 ID"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("69FBE6C4F8A8853F8874E107")

                    with builder.CHILD(key="robot_name", name="robot_name", desc="机器人名称"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("AMB-01")
                    
                    with builder.CHILD(key="m4_app_id", name="m4_app_id", desc="M4 应用 ID"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("test")

                    with builder.CHILD(key="m4_app_key", name="m4_app_key", desc="M4 应用密钥"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("test")

                    with builder.CHILD(key="ip", name="ip", desc="M4调度系统IP地址"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("172.16.86.151")

                    with builder.CHILD(key="m4_port", name="m4_port", desc="M4调度系统端口"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(5800, min_value=1, max_value=65535)

                    with builder.CHILD(key="charging_site", name="charging_site", desc="充电站点"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("AP20100")

            with builder.GROUP(
                    key="monitorConfig",
                    name="电量与水位配置",
                    desc="电量、水位阈值和水位监测参数"
            ):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(key="low_battery_soc", name="low_battery_soc", desc="低电量阈值"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.2)
                        builder.SINGLESTEP(0.01)

                    with builder.CHILD(key="high_battery_soc", name="high_battery_soc", desc="高电量恢复阈值"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.9)
                        builder.SINGLESTEP(0.01)

                    with builder.CHILD(key="hmi_period", name="hmi_period", desc="车载屏轮询周期"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("s")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(
                            key="min_clean_water_level",
                            name="min_clean_water_level",
                            desc="清水液位最小值，达到此值机器人停止工作去加水",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(
                            key="max_clean_water_level",
                            name="max_clean_water_level",
                            desc="清水液位最大值，达到此值机器人停止加水",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(95.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(
                            key="min_waste_water_level",
                            name="min_waste_water_level",
                            desc="污水液位最小值，达到此值机器人停止排污",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(
                            key="max_waste_water_level",
                            name="max_waste_water_level",
                            desc="污水液位最大值，达到此值机器人停止工作去排污",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(90.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="add_water_do", name="add_water_do", desc="加水DO"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DO-004")

            with builder.GROUP(
                    key="mechanismConfig",
                    name="清洁机构配置",
                    desc="清洁机构行程、功率和动作延时"
            ):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(
                            key="push_rod_length",
                            name="push_rod_length",
                            desc="刷盘推杆行程, 取值: 70-100, 刷盘下降的高度,参数可缺省",
                    ):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(75)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="brush_power", name="brush_power", desc="刷盘电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(67)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="suck_power", name="suck_power", desc="吸风电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(50)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="jet_power", name="jet_power", desc="喷水泵电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(20)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(
                            key="auto_adjust_power",
                            name="auto_adjust_power",
                            desc="是否启动电机功率自动调节模式, 1: 启动， 0: 不启动",
                    ):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="add_water_delay_time", name="add_water_delay_time", desc="加水延时关闭时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.SINGLESTEP(1.0)

                    with builder.CHILD(
                            key="close_jet_delay_time",
                            name="close_jet_delay_time",
                            desc="关闭喷水电机后延时停止清洁工作的时间",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.SINGLESTEP(1.0)

            with builder.GROUP(
                    key="speedConfig",
                    name="速度功率配置",
                    desc="根据车辆速度调整清洁机构功率的阈值"
            ):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(
                            key="high_mode_x_speed",
                            name="high_mode_x_speed",
                            desc="x速度大于该值时, 清洁机构以高功率工作",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.8)
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(
                            key="std_mode_x_speed",
                            name="std_mode_x_speed",
                            desc="x速度大于该值时, 清洁机构以标准功率工作",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.4)
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(
                            key="stop_x_speed",
                            name="stop_x_speed",
                            desc="x速度小于该值时, 清洁机构停止工作",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05)
                        builder.SINGLESTEP(0.1)

            with builder.GROUP(
                    key="pathConfig",
                    name="清洁路径配置",
                    desc="弓字形清洁路径的导航参数"
            ):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(
                            key="boustrophedon_path_max_speed",
                            name="boustrophedon_path_max_speed",
                            desc="弓字形路径最大直线速度",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(
                            key="boustrophedon_path_max_rot",
                            name="boustrophedon_path_max_rot",
                            desc="弓字形路径最大旋转速度",
                    ):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5)
                        builder.UNIT("rad/s")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(
                            key="boustrophedon_path_free_bypass",
                            name="boustrophedon_path_free_bypass",
                            desc="弓字形路径是否启用绕障",
                    ):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(0)
                        builder.SINGLESTEP(1)

            with builder.GROUP(
                    key="scheduleConfig",
                    name="定时清洁配置",
                    desc="每日定时清洁任务的触发时间和路线"
            ):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(
                            key="scheduled_clean_enabled",
                            name="scheduled_clean_enabled",
                            desc="是否启用每日定时清洁任务",
                    ):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(
                            key="scheduled_clean_hour",
                            name="scheduled_clean_hour",
                            desc="每日定时清洁任务执行时间（小时，0-23）",
                    ):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(8)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(
                            key="scheduled_clean_minute",
                            name="scheduled_clean_minute",
                            desc="每日定时清洁任务执行时间（分钟，0-59）",
                    ):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(0)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(
                            key="scheduled_clean_locations",
                            name="scheduled_clean_locations",
                            desc="每日定时清洁任务的站点路径，支持一维单路线或二维分段路线",
                    ):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE(
                            '["AP9", "AP8", "LM7", "AP5", "AP6", "LM3", "AP1", "AP2"]')

        builder.save(merge=True)
        if migrate_basic_config:
            with open(param_loader.config_file, "r", encoding="utf-8") as config_file:
                config_definition = json.load(config_file)

            def restore_values(nodes):
                for node in nodes:
                    key = node.get("key")
                    if key in existing_config:
                        node["value"] = existing_config[key]
                    restore_values(node.get("children", []))

            restore_values(config_definition.get("groups", []))
            with open(param_loader.config_file, "w", encoding="utf-8") as config_file:
                json.dump(config_definition, config_file, ensure_ascii=False, indent=2)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        cls.config = param_loader.loadConfig()
        cls.addTime = cls.config.get("addTime", False)
        cls.logWrite = cls.config.get("logWrite", False)
        Trace.log("Reloading cleanRobotManage config parameters")
        cls.timeout = cls.config.get("timeout")
        cls.scene_id = cls.config.get("scene_id", "690843857C47EE4EE84D5AB7")
        cls.robot_name = cls.config.get("robot_name", "300J")
        cls.charging_site = cls.config.get("charging_site", "AP20100")
        cls.low_battery_soc = cls.config.get("low_battery_soc", 0.2)
        cls.high_battery_soc = cls.config.get("high_battery_soc", 0.9)
        cls.hmi_period = cls.config.get("hmi_period", 1.0)
        cls.min_clean_water_level = cls.config.get("min_clean_water_level")
        cls.max_clean_water_level = cls.config.get("max_clean_water_level")
        cls.min_waste_water_level = cls.config.get("min_waste_water_level")
        cls.max_waste_water_level = cls.config.get("max_waste_water_level")
        cls.add_water_do = cls.config.get("add_water_do")
        cls.push_rod_length = cls.config.get("push_rod_length")
        cls.brush_power = cls.config.get("brush_power")
        cls.suck_power = cls.config.get("suck_power")
        cls.jet_power = cls.config.get("jet_power")
        cls.auto_adjust_power = cls.config.get("auto_adjust_power")
        cls.add_water_delay_time = cls.config.get("add_water_delay_time")
        cls.close_jet_delay_time = cls.config.get("close_jet_delay_time")
        cls.high_mode_x_speed = cls.config.get("high_mode_x_speed")
        cls.std_mode_x_speed = cls.config.get("std_mode_x_speed")
        cls.stop_x_speed = cls.config.get("stop_x_speed")
        cls.boustrophedon_path_max_speed = cls.config.get("boustrophedon_path_max_speed", 1.0)
        cls.boustrophedon_path_max_rot = cls.config.get("boustrophedon_path_max_rot", 0.5)
        cls.boustrophedon_path_free_bypass = cls.config.get("boustrophedon_path_free_bypass", 0)
        cls.scheduled_clean_enabled = cls.config.get("scheduled_clean_enabled", 1)
        cls.scheduled_clean_hour = cls.config.get("scheduled_clean_hour", 8)
        cls.scheduled_clean_minute = cls.config.get("scheduled_clean_minute", 0)
        previous_locations = getattr(cls, "scheduled_clean_locations", [])
        previous_routes = getattr(cls, "scheduled_clean_routes", [])
        route_config_error = None
        try:
            scheduled_clean_locations = json.loads(
                cls.config.get("scheduled_clean_locations", "[]")
            )
            if scheduled_clean_locations == []:
                scheduled_clean_routes = []
            elif (isinstance(scheduled_clean_locations, list) and
                  all(isinstance(location, str) for location in scheduled_clean_locations)):
                scheduled_clean_routes = [scheduled_clean_locations]
            elif (isinstance(scheduled_clean_locations, list) and
                  all(isinstance(route, list) and route and
                      all(isinstance(location, str) for location in route)
                      for route in scheduled_clean_locations)):
                scheduled_clean_routes = scheduled_clean_locations
            else:
                raise ValueError("route must be a string list or a non-empty list of string lists")
        except (TypeError, json.JSONDecodeError, ValueError) as exc:
            route_config_error = str(exc)
            Trace.log(
                f"Invalid scheduled_clean_locations config: {exc}; "
                "keeping the previous valid route"
            )
            scheduled_clean_locations = previous_locations
            scheduled_clean_routes = previous_routes
        cls.scheduled_clean_locations = scheduled_clean_locations
        cls.scheduled_clean_routes = scheduled_clean_routes
        cls.scheduled_clean_config_valid = route_config_error is None
        try:
            if route_config_error:
                Navigation.setDeviceError(
                    "DeviceError-SCHEDULED-CLEAN-ROUTE",
                    f"Invalid scheduled_clean_locations config: "
                    f"{route_config_error}; please correct it and push again"
                )
            else:
                Navigation.clearDeviceError("DeviceError-SCHEDULED-CLEAN-ROUTE")
        except Exception as exc:
            Trace.log(f"Failed to update scheduled clean route error: {exc}")
        cls.isDebug = cls.config.get("isDebug", False)
        cls.isTrue = cls.config.get("isTrue", False)
        cls.simulation_charge_enabled = cls.config.get("simulation_charge_enabled", False)
        cls.m4_app_id = cls.config.get("m4_app_id", "test")
        cls.m4_app_key = cls.config.get("m4_app_key", "test")
        cls.ip = cls.config.get("ip", "172.16.86.151")
        cls.m4_port = int(cls.config.get("m4_port", 5800))

        Trace.log(f"Updated cleanRobotManage config: {cls.config}")


config_params = ConfigParams()
log = Logger("clean_robot")


def get_scheduler_url() -> str:
    return f"http://{config_params.ip}:{config_params.m4_port}/api/fleet/orders/create"


def get_scheduler_cancel_url() -> str:
    return f"http://{config_params.ip}:{config_params.m4_port}/api/fleet/orders/cancel"


def get_scheduler_order_detail_url() -> str:
    return f"http://{config_params.ip}:{config_params.m4_port}/api/fleet/orders/query-order-detail"

class MechWorkingStatus(IntEnum):
    """机构工作状态枚举"""
    INIT = 0
    RUNNING = 1
    FINISHED = 2


class MechWorkState(IntEnum):
    """机构开关状态枚举"""
    CLOSE = 0
    OPEN = 1


class MechWorkMode(IntEnum):
    """机构工作模式枚举"""
    LOW = 0
    STD = 1
    HIGH = 2
    STOP = 3


class MechCmd:
    """机构CAN控制指令"""
    SUCK = "2B 80 30 01 00 00 00 00"
    BRUSH = "2B 80 30 02 00 00 00 00"
    JET_PUMP = "2B 80 30 03 00 00 00 00"
    BRUSH_LIFT_UP = "2B 80 30 04 64 00 00 00"
    BRUSH_LIFT_DOWN = "2B 80 30 04 FF 9C 00 00"
    BRUSH_POD_DOWN = "2B 86 30 01 00 00 00 00"
    MOP_LIFT_UP = "2B 80 30 05 FF 9C 00 00"
    MOP_LIFT_DOWN = "2B 80 30 05 64 00 00 00"
    WATER_VALVE_OPEN = "2B 80 30 06 64 00 00 00"
    WATER_VALVE_CLOSE = "2B 80 30 06 00 00 00 00"
    BRAIN_BALL_VALVE_OPEN = "2B 80 30 07 64 00 00 00"
    BRAIN_BALL_VALVE_CLOSE = "2B 80 30 07 00 00 00 00"
    SET_ALL_STD = "23 02 40 00 32 43 1E 07"
    SET_ALL_LOW = "23 02 40 00 28 32 14 07"
    SET_ALL_HIGH = "23 02 40 00 46 50 32 07"
    SET_ALL_CLOSED = "23 02 40 00 00 00 00 00"
    QUERY_ALL_INFO = "40 03 40 00 00 00 00 00"


class MeanValue:
    """均值滤波器"""

    def __init__(self, window_size=1000):
        self.window_size = window_size
        self.data = []

    def add_value(self, v):
        self.data.append(v)
        while len(self.data) > self.window_size:
            self.data.pop(0)

    def get_mean_value(self) -> float:
        if not self.data:
            return 0.0
        return round(sum(self.data) / len(self.data), 3)


class CleanRobotHardware:
    """清洁机器人硬件控制接口"""

    def __init__(self, mech_obj):
        self.chanel = 2
        self.can_id = 0x605
        self.dlc = 8
        self.extend = False
        self.mech = mech_obj
        self.default_data = '0' * 16
        self.query_all_cmd_status = MechWorkingStatus.INIT
        self._can_data_lock = threading.Lock()
        self._latest_can_data = {}
        self._can_reader_stop = threading.Event()
        self._can_reader_error_logged = False
        self._can_reader_thread = None
        if not config_params.isTrue:
            self._can_reader_thread = threading.Thread(
                target=self._read_can_data,
                name="clean_robot_can_reader",
                daemon=True,
            )
            self._can_reader_thread.start()

    def _read_can_data(self):
        """后台读取CAN报文，避免阻塞机构周期线程。"""
        while not self._can_reader_stop.is_set():
            try:
                data = Can.getData()
                if isinstance(data, dict) and data:
                    with self._can_data_lock:
                        self._latest_can_data = data.copy()
                self._can_reader_error_logged = False
            except Exception as exc:
                if not self._can_reader_error_logged:
                    Trace.log(f"[cleanRobotManage] CAN reader failed: {exc}")
                    self._can_reader_error_logged = True
                self._can_reader_stop.wait(0.1)
                continue
            self._can_reader_stop.wait(0.01)

    def ctrl_suck(self, power=0):
        cmd = MechCmd.SUCK[:12] + hex(power)[2:].zfill(2) + MechCmd.SUCK[14:]
        Trace.debug(f"[cleanRobotManage] Sending suck cmd:  {cmd}  吸风电机功率: {power}")
        self.send_cmd(cmd)

    def ctrl_brush(self, power=0):
        cmd = MechCmd.BRUSH[:12] + hex(power)[2:].zfill(2) + MechCmd.BRUSH[14:]
        Trace.debug(f"[cleanRobotManage] Sending brush cmd:  {cmd}  滚刷电机功率: {power}")
        self.send_cmd(cmd)

    def ctrl_jet_pump(self, power=0):
        cmd = MechCmd.JET_PUMP[:12] + hex(power)[2:].zfill(2) + MechCmd.JET_PUMP[14:]
        Trace.debug(f"[cleanRobotManage] Sending jet pump cmd:  {cmd}  喷水电机功率: {power}")
        self.send_cmd(cmd)

    def ctrl_pod_length(self, power=0):
        cmd = MechCmd.BRUSH_POD_DOWN[:12] + hex(power)[2:].zfill(2) + MechCmd.BRUSH_POD_DOWN[14:]
        Trace.debug(f"[cleanRobotManage] Sending pod length cmd:  {cmd}  推轮电机功率: {power}")
        self.send_cmd(cmd)

    def ctrl_brush_lift(self, state):
        cmd = MechCmd.BRUSH_LIFT_DOWN if state == MechWorkState.OPEN else MechCmd.BRUSH_LIFT_UP
        Trace.debug(f"[cleanRobotManage] Sending brush lift cmd:  {cmd}  滚刷升降杆状态: {state}")
        self.send_cmd(cmd)

    def ctrl_mop_lift(self, state):
        cmd = MechCmd.MOP_LIFT_DOWN if state == MechWorkState.OPEN else MechCmd.MOP_LIFT_UP
        Trace.debug(f"[cleanRobotManage] Sending mop lift cmd:  {cmd}  水趴升降杆状态: {state}")
        self.send_cmd(cmd)

    def ctrl_clean_valve(self, state):
        """控制清水阀，OPEN表示打开，其他状态表示关闭"""
        cmd = MechCmd.WATER_VALVE_OPEN if state == MechWorkState.OPEN else MechCmd.WATER_VALVE_CLOSE
        Trace.debug(f"[cleanRobotManage] Sending clean valve cmd:  {cmd}  清水阀状态: {state}")
        self.send_cmd(cmd)

    def ctrl_waste_valve(self, state):
        """控制污水排放球阀，OPEN表示打开，其他状态表示关闭"""
        cmd = MechCmd.BRAIN_BALL_VALVE_OPEN if state == MechWorkState.OPEN else MechCmd.BRAIN_BALL_VALVE_CLOSE
        Trace.debug(f"[cleanRobotManage] Sending waste valve cmd:  {cmd}  污水排放球阀状态: {state}")
        self.send_cmd(cmd)

    def ctrl_open_all(self, mode):
        cmd = MechCmd.SET_ALL_STD
        if mode == MechWorkMode.LOW:
            cmd = MechCmd.SET_ALL_LOW
        elif mode == MechWorkMode.HIGH:
            cmd = MechCmd.SET_ALL_HIGH
        elif mode == MechWorkMode.STOP:
            cmd = MechCmd.SET_ALL_CLOSED
        self.send_cmd(cmd)

    def ctrl_close_all(self):
        self.send_cmd(MechCmd.SET_ALL_CLOSED)

    def query_all_info(self):
        self.query_all_cmd_status = MechWorkingStatus.RUNNING
        recv_data = self.send_cmd(MechCmd.QUERY_ALL_INFO)
        if recv_data[:8] == "43034000":
            self.query_all_cmd_status = MechWorkingStatus.FINISHED
            return recv_data
        return self.default_data

    def send_cmd(self, cmd):
        Can.sendCanFrame(self.chanel, self.can_id, self.dlc, self.extend, cmd)
        with self._can_data_lock:
            data = self._latest_can_data.copy()
        b64_str = data.get('data', '')
        can_id = data.get('id', 0)
        hex_str = base64.b64decode(b64_str).hex().upper()
        if can_id + 128 == self.can_id:
            return hex_str
        return self.default_data


class CleanRobotMech:
    """
    清洁机器人机构控制类（原 cleanRobotMech.py）
    负责清洁车机构控制：刷盘/水扒/吸风/喷水/加水排污
    """

    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = 502
        self.modbus_tcp = modbus_tcp.TcpMaster(self.ip, self.port, 1)
        self.is_connected = False
        self.rbk_addr = 110

        self.brush_status = None
        self.jet_status = None
        self.suck_status = None
        self.brush_lift_status = None
        self.push_rod_status = None
        self.mop_lift_status = None
        self.clean_valve_status = None
        self.waste_valve_status = None
        self.clean_robot_working = None
        self.clean_robot_closed = None
        self.work_mode = MechWorkMode.STD

        self.clean_water_level: float = -1
        self.waste_water_level: float = -1
        self.water_level_warning = None
        self.clean_filter = MeanValue(1000)
        self.waste_filter = MeanValue(1000)

        self.auto_adjust_power = config_params.auto_adjust_power
        self.jet_power = config_params.jet_power
        self.brush_power = config_params.brush_power
        self.suck_power = config_params.suck_power
        self.push_rod_length = config_params.push_rod_length

        self.add_water_time_start = None
        self.close_jet_pump_start = None
        self.add_water_opt_start = False
        self.jet_starting = True
        self.jet_command_power = 0
        self.water_stopped_for_path_end = False

        self.operation = None
        self.init = False
        self.action_status = ScriptStatus.NONE
        self.last_unready_mechanisms = None
        self.report_info = {}


        self.task_update_start = time.time()
        self.period_run_counter = 0
        self.drive_speed = 0.0


        self.hardware = CleanRobotHardware(self)

        Trace.log("CleanRobotMech initialized")

    def period_run(self):
        """周期性运行函数"""
        self.period_run_counter += 1
        if self.period_run_counter < 100:
            return True
        if self.period_run_counter == 100:
            self.reset()

        self.update_all_info()

        if not self.is_connected:
            self.connect()

        if time.time() - self.task_update_start > 0.2:
            self.task_update_start = time.time()
            self.save_to_rbk()
            self.update_by_task_status()

        return True

    def run(self, args: dict):
        """主运行函数"""
        self.action_status = ScriptStatus.RUNNING

        if not self.init:
            self.init = True
            self.update_all_info()
            self.operation = args.get("operation", None)
            self.auto_adjust_power = args.get("auto_adjust_power", config_params.auto_adjust_power)
            self.jet_power = int(args.get("jet_power", config_params.jet_power))
            self.brush_power = int(args.get("brush_power", config_params.brush_power))
            self.suck_power = int(args.get("suck_power", config_params.suck_power))
            self.push_rod_length = int(args.get("push_rod_length", config_params.push_rod_length))
            if self.operation == "WashStart":
                self.jet_starting = True
                self.jet_command_power = 0
                self.water_stopped_for_path_end = False

        if self.operation == "WashStart":
            self.wash_start()
        elif self.operation == "WashEnd":
            self.wash_end()
        elif self.operation == "MechanismOpen":
            self.wash_start(operation="MechanismOpen")
        elif self.operation == "MechanismClose":
            self.wash_end(control_water=False, operation="MechanismClose")
        elif self.operation == "DustStart":
            self.dust_start()
        elif self.operation == "DustEnd":
            self.dust_end()
        elif self.operation == "AddWater":
            self.add_water()
        elif self.operation == "CheckInfo":
            self.update_all_info()
            self.action_status = ScriptStatus.FINISHED
        else:
            Navigation.setTaskError("args error",f"cleanRobotMech args error operation not support input: {args}")
            self.action_status = ScriptStatus.FAILED

        self.update_all_info()
        self.report_info['operation'] = self.operation
        return self.action_status

    def reset_state(self):
        """重置操作状态"""
        self.init = False
        self.operation = None
        self.action_status = ScriptStatus.NONE

    def update_by_task_status(self):
        """根据任务状态更新"""
        task_status = NavStatus.getTaskStatus()

        if task_status == 2:
            if self.operation == "WashStart":
                self.update_power_by_speed()
        elif task_status == 3:
            Trace.log("[cleanRobotManage] Task status 3: Suspend")
            self.wash_suspend()
        elif task_status == 5:
            Trace.log("[cleanRobotManage] Task status 5: End")
            self.wash_end()
        elif task_status == 6:
            Trace.log("[cleanRobotManage] Task status 6: End")
            self.wash_end()
        if Controller.getEmc():
            Trace.log("[cleanRobotManage] EMC signal: End")
            self.wash_end()
        loc_state = Loc.getLocState()
        if self.filter_waste_water_level() > config_params.max_waste_water_level:
            if self.water_level_warning != "waste_full":
                Trace.log(
                    f"[cleanRobotManage] Waste water full: "
                    f"level={self.waste_water_level}, limit={config_params.max_waste_water_level}"
                )
            self.water_level_warning = "waste_full"
            if self.operation != "AddWater" and loc_state == 1:
                self.wash_end()
        elif self.filter_clean_water_level() < config_params.min_clean_water_level and self.filter_clean_water_level() != -1:
            if self.water_level_warning != "clean_empty":
                Trace.log(
                    f"[cleanRobotManage] Clean water empty: "
                    f"level={self.clean_water_level}, limit={config_params.min_clean_water_level}"
                )
            self.water_level_warning = "clean_empty"
            if self.operation != "AddWater" and loc_state == 1:
                self.wash_end()
        else:
            self.water_level_warning = None

    def update_power_by_speed(self):
        """根据车速自动调节电机功率"""
        try:
            agv_speed = NavSpeed.getSpeeds()
        except Exception as e:
            Trace.log(f"update_power_by_speed error: {e}")
            self.drive_speed = 0.0
            self.wash_open()
            return

        speed_x = agv_speed[0] if len(agv_speed) > 0 else 0.0
        speed_y = agv_speed[1] if len(agv_speed) > 1 else 0.0
        drive_speed = max(abs(speed_x), abs(speed_y))
        self.drive_speed = drive_speed

        other_mechanisms_working = self.other_clean_mechanisms_working()
        if not other_mechanisms_working:
            self.wash_open()

        if bool(self.auto_adjust_power):
            if drive_speed > config_params.high_mode_x_speed:
                self.work_mode = MechWorkMode.HIGH
                self.suck_power, self.jet_power, self.brush_power = (70, 50, 67)
            elif config_params.std_mode_x_speed < drive_speed <= config_params.high_mode_x_speed:
                self.work_mode = MechWorkMode.STD
                self.suck_power, self.jet_power, self.brush_power = (
                    config_params.suck_power,
                    config_params.jet_power,
                    config_params.brush_power,
                )
            elif config_params.stop_x_speed < drive_speed <= config_params.std_mode_x_speed:
                self.work_mode = MechWorkMode.LOW
                self.suck_power, self.jet_power, self.brush_power = (40, 10, 50)

        if drive_speed <= config_params.stop_x_speed:
            self.work_mode = MechWorkMode.STOP

        target_jet_power = self.jet_power_by_speed(drive_speed)
        if not other_mechanisms_working:
            target_jet_power = 0
        self.set_jet_power(target_jet_power)

    def jet_power_by_speed(self, drive_speed):
        """根据车速计算喷水功率，车辆每次起步时先使用低功率"""
        if drive_speed <= config_params.stop_x_speed:
            self.jet_starting = True
            return 0
        if self.jet_starting:
            return 10
        return self.jet_power

    def set_jet_power(self, power):
        """仅在功率变化或喷水状态异常时下发喷水功率"""
        power = int(power)
        if power > 0 and not self.other_clean_mechanisms_working():
            power = 0
        if (power != self.jet_command_power or
                (power > 0 and self.jet_status != MechWorkingStatus.RUNNING) or
                (power == 0 and self.jet_status == MechWorkingStatus.RUNNING)):
            self.hardware.ctrl_jet_pump(power)
            self.jet_command_power = power
        if power > 0 and self.jet_status == MechWorkingStatus.RUNNING:
            self.jet_starting = False

    def connect(self):
        """连接Modbus TCP"""
        try:
            self.modbus_tcp.open()
            self.is_connected = True
        except Exception as e:
            Trace.log(f"connect error: {e}")

    def save_to_rbk(self):
        """保存液位数据到RBK"""
        try:
            self.modbus_tcp.execute(
                1,
                cst.WRITE_MULTIPLE_REGISTERS,
                self.rbk_addr,
                output_value=[
                    round(self.filter_clean_water_level()),
                    round(self.filter_waste_water_level()),
                ],
            )
        except Exception as e:
            Trace.log(f"save_to_rbk error: {e}")

    def wash_open(self):
        """打开清洁机构"""
        self.is_fit_push_rod()
        if self.brush_lift_status != MechWorkingStatus.RUNNING:
            self.hardware.ctrl_brush_lift(MechWorkState.OPEN)
        if self.mop_lift_status != MechWorkingStatus.RUNNING:
            self.hardware.ctrl_mop_lift(MechWorkState.OPEN)
        elif self.clean_valve_status == MechWorkingStatus.RUNNING:
            self.hardware.ctrl_clean_valve(MechWorkState.CLOSE)
        elif self.suck_status != MechWorkingStatus.RUNNING:
            self.hardware.ctrl_suck(self.suck_power)
        elif self.brush_status != MechWorkingStatus.RUNNING:
            self.hardware.ctrl_brush(self.brush_power)

    def other_clean_mechanisms_working(self):
        """检查喷水泵以外的清洁机构是否全部启动"""
        return all(status == MechWorkingStatus.RUNNING for status in (
            self.brush_status,
            self.suck_status,
            self.mop_lift_status,
        ))

    def is_fit_push_rod(self):
        """检查推杆长度"""
        if int(self.push_rod_length) < 70 or int(self.push_rod_length) > 100:
            Navigation.setDeviceError("DeviceError-PUSH_ROD_LENGTH_LIMIT",f"cleanRobotMech args error push rod length limit: {self.push_rod_length},you need adjust it to 70-100")
            self.wash_end()
        else:
            try:
                Navigation.clearDeviceError("DeviceError-PUSH_ROD_LENGTH_LIMIT")
            except:
                pass
            self.hardware.ctrl_pod_length(self.push_rod_length)

    def wash_start(self, operation: str = "WashStart"):
        """开始清洗"""
        self.operation = operation
        self.wash_open()
        unready_mechanisms = [name for name in ("brush", "suck", "mop_lift")
                              if getattr(self, f"{name}_status") != MechWorkingStatus.RUNNING]
        if unready_mechanisms != self.last_unready_mechanisms:
            if unready_mechanisms:
                Trace.log(f"[cleanRobotManage] WashStart waiting for mechanisms: {', '.join(unready_mechanisms)}")
            else:
                Trace.log("[cleanRobotManage] Other cleaning mechanisms are all running")
                if self.brush_lift_status != MechWorkingStatus.RUNNING:
                    self.hardware.ctrl_brush_lift(MechWorkState.OPEN)
                    self.update_all_info()
                    if self.brush_lift_status == MechWorkingStatus.RUNNING:
                        Trace.log("[cleanRobotManage] Brush lift retry succeeded")
                    else:
                        Trace.log(f"[cleanRobotManage] Brush lift retry failed, status={self.brush_lift_status}")
                else:
                    Trace.log("[cleanRobotManage] Brush lift is already running, retry skipped")
            self.last_unready_mechanisms = unready_mechanisms
        if not unready_mechanisms:
            self.action_status = ScriptStatus.FINISHED
            return True
        else:
            return False

    def wash_stop_water(self):
        """弓字形路径结束时仅停止喷水"""
        self.operation = "WashStopWater"
        self.water_stopped_for_path_end = True
        self.jet_starting = True
        self.set_jet_power(0)
        self.hardware.ctrl_brush_lift(MechWorkState.CLOSE)


    def wash_water(self):
        """排空水管"""
        if self.operation == "WashEnd":
            if self.jet_status != MechWorkingStatus.RUNNING:
                self.hardware.ctrl_jet_pump(self.jet_power)
            if self.clean_valve_status != MechWorkingStatus.RUNNING:
                self.hardware.ctrl_clean_valve(MechWorkState.OPEN)

    def wash_end(self, control_water: bool = True, operation: str = "WashEnd"):
        """结束清洗；control_water=False时只关闭清洁机构。"""
        self.operation = operation
        if control_water:
            Do.setDo(config_params.add_water_do, False)

            if self.waste_valve_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_waste_valve(MechWorkState.CLOSE)

        if not self.close_jet_pump_start:
            self.close_jet_pump_start = time.time()

        if (control_water and not self.water_stopped_for_path_end and
                not self.clean_robot_closed):
            if self.close_jet_pump_start and time.time() - self.close_jet_pump_start < 3:
                self.wash_water()

        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > config_params.close_jet_delay_time * 0.7:
            if self.brush_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_brush(0)
            if control_water and self.jet_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_jet_pump(0)
            if control_water and self.clean_valve_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_clean_valve(MechWorkState.CLOSE)
            # if self.brush_lift_status != MechWorkingStatus.INIT:
            self.hardware.ctrl_brush_lift(MechWorkState.CLOSE)

        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > config_params.close_jet_delay_time:
            if self.mop_lift_status != MechWorkingStatus.INIT:
                self.hardware.ctrl_mop_lift(MechWorkState.CLOSE)
            if self.suck_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_suck(0)

        mechanisms_closed = (
            self.clean_robot_closed if control_water else
            not bool(max([
                self.brush_status,
                self.suck_status,
                self.mop_lift_status,
                self.brush_lift_status,
            ]))
        )
        if mechanisms_closed:
            self.close_jet_pump_start = None
            if control_water:
                self.jet_starting = True
                self.jet_command_power = 0
                self.water_stopped_for_path_end = False
            self.action_status = ScriptStatus.FINISHED
            return True
        else:
            return False

    def wash_suspend(self):
        """暂停清洗"""
        if self.brush_status == MechWorkingStatus.RUNNING:
            self.hardware.ctrl_brush(0)
        if self.jet_status == MechWorkingStatus.RUNNING:
            self.hardware.ctrl_jet_pump(0)
        if self.clean_valve_status != MechWorkingStatus.RUNNING:
            self.hardware.ctrl_clean_valve(MechWorkState.OPEN)
        if self.waste_valve_status == MechWorkingStatus.RUNNING:
            self.hardware.ctrl_waste_valve(MechWorkState.CLOSE)

        if bool(self.auto_adjust_power):
            self.work_mode = MechWorkMode.STOP
            self.suck_power, self.jet_power, self.brush_power = (0, 0, 0)

        if not self.close_jet_pump_start:
            self.close_jet_pump_start = time.time()
        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > config_params.close_jet_delay_time:
            if self.suck_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_suck(0)

    def reset(self):
        """复位机构"""
        if self.jet_status == MechWorkingStatus.RUNNING:
            self.hardware.ctrl_jet_pump(0)
        if self.clean_valve_status == MechWorkingStatus.RUNNING:
            self.hardware.ctrl_clean_valve(MechWorkState.CLOSE)

    def dust_start(self):
        """开始吸尘"""
        self.is_fit_push_rod()

    def dust_end(self):
        """结束吸尘"""
        if self.mop_lift_status != MechWorkingStatus.INIT:
            self.hardware.ctrl_mop_lift(MechWorkState.CLOSE)
        if self.suck_status != MechWorkingStatus.INIT:
            self.hardware.ctrl_suck(0)
        else:
            self.action_status = ScriptStatus.FINISHED

    def add_water(self):
        """加水排污"""
        is_charging = Battery.getIsCharging()

        if not is_charging:
            Do.setDo(config_params.add_water_do, False)
            self.hardware.ctrl_waste_valve(MechWorkState.CLOSE)
            Navigation.setDeviceError("DeviceError-TO_CHARGE_STATION", "cleanRobotMech args error not charging,please move to charge station")
            self.action_status = ScriptStatus.FAILED
        else:
            try:
                Navigation.clearDeviceError("DeviceError-TO_CHARGE_STATION")
            except:
                pass
            if not self.add_water_opt_start:
                Do.setDo(config_params.add_water_do, True)
                self.hardware.ctrl_waste_valve(MechWorkState.OPEN)

        if Do.getDo(config_params.add_water_do) and self.waste_valve_status == MechWorkingStatus.RUNNING:
            self.add_water_opt_start = True

        if self.clean_water_level >= config_params.max_clean_water_level:
            Do.setDo(config_params.add_water_do, False)

        if self.waste_water_level <= config_params.min_waste_water_level:
            self.hardware.ctrl_waste_valve(MechWorkState.CLOSE)

        if self.waste_water_level <= config_params.min_waste_water_level and self.clean_water_level >= config_params.max_clean_water_level:
            if not self.add_water_time_start:
                self.add_water_time_start = time.time()
            if time.time() - self.add_water_time_start > config_params.add_water_delay_time:
                self.add_water_time_start = None
                self.add_water_opt_start = False
                self.action_status = ScriptStatus.FINISHED

    def filter_clean_water_level(self):
        """清水液位滤波"""
        if self.clean_water_level >= 0:
            self.clean_filter.add_value(self.clean_water_level)
            return self.clean_filter.get_mean_value()
        return self.clean_water_level

    def filter_waste_water_level(self):
        """污水液位滤波"""
        if self.waste_water_level >= 0:
            self.waste_filter.add_value(self.waste_water_level)
            return self.waste_filter.get_mean_value()
        return self.waste_water_level

    def update_all_info(self):
        """更新所有机构状态"""
        recv_data = self.hardware.query_all_info()
        if self.hardware.query_all_cmd_status == MechWorkingStatus.FINISHED:
            self.hardware.query_all_cmd_status = MechWorkingStatus.INIT
            state = bin(int(recv_data[12:14], 16))[2:].zfill(8)
            self.clean_water_level = int(recv_data[8:10], 16)
            self.waste_water_level = int(recv_data[10:12], 16)
            self.push_rod_status = int(recv_data[14:16], 16)
            self.jet_status = MechWorkingStatus(int(state[1:2]))
            self.brush_status = MechWorkingStatus(int(state[2:3]))
            previous_suck_status = self.suck_status
            self.suck_status = MechWorkingStatus(int(state[3:4]))
            if previous_suck_status != self.suck_status:
                Trace.debug(
                    f"[cleanRobotManage] Suck status changed: "
                    f"{previous_suck_status} -> {self.suck_status}"
                )
            self.waste_valve_status = MechWorkingStatus(int(state[4:5]))
            self.clean_valve_status = MechWorkingStatus(int(state[5:6]))
            self.mop_lift_status = MechWorkingStatus(int(state[6:7]))
            self.brush_lift_status = MechWorkingStatus(int(state[7:8]))
            self.clean_robot_working = all(list(map(int, state[1:4] + state[6:8])))
            self.clean_robot_closed = not bool(max(list(map(int, state[1:4] + state[5:8]))))

        self.report_info["work_status"] = {
            'suck_state': self.suck_status, 'brush_state': self.brush_status,
            'jet_pump_state': self.jet_status, 'mop_lift_state': self.mop_lift_status,
            'brush_lift_state': self.brush_lift_status, 'waste_valve_state': self.waste_valve_status,
            'clean_valve_state': self.clean_valve_status, 'push_rod_state': self.push_rod_status
        }
        try:
            cur_speed = NavSpeed.getSpeeds()
        except Exception:
            cur_speed = [0.0, 0.0, 0.0]

        self.report_info["auto_adjust"] = {
            "auto_adjust": bool(self.auto_adjust_power),
            "work_mode": self.work_mode.name,
            "suck_power": self.suck_power,
            "jet_power": self.jet_power,
            "brush_power": self.brush_power,
        }
        self.report_info["agv_speed"] = {
            "x": round(cur_speed[0], 6) if len(cur_speed) > 0 else 0.0,
            "y": round(cur_speed[1], 6) if len(cur_speed) > 1 else 0.0,
            "rotate": round(cur_speed[2], 6) if len(cur_speed) > 2 else 0.0,
        }

    def cancel(self):
        """取消操作"""
        Trace.log("CleanRobotMech cancel")
        Do.setDo(config_params.add_water_do, False)
        self.wash_end()
        self.action_status = ScriptStatus.FAILED

    def get_water_levels(self) -> Tuple[float, float]:
        """获取水位信息 (清水, 污水)"""
        return self.filter_clean_water_level(), self.filter_waste_water_level()


def script_config_callback():
    Trace.log("Reloading script config parameters for cleanRobotManage")
    config_params.reload_config()


class ERPState(IntEnum):
    """
    ERP状态机。

    当前脚本里它只承担“总控状态”作用，不再细分任务执行阶段。
    是否存在正在执行的任务，由 current_task / current_task_type 负责表达。
    """
    NORMAL = 0  # 正常状态：系统可继续运行，也允许在满足条件时恢复断点任务
    ERROR = 4   # 异常状态：出现调度或任务错误，需要人工介入处理


class VehicleState(IntEnum):
    """
    车辆状态机。

    用于描述机器人当前在“做什么”，偏向业务层语义，
    例如空闲、充电、换水、清洁、普通导航。
    """
    IDLE = 0        # 空闲：当前没有执行中的业务任务
    ADD_WATER = 1   # 换水：正在执行加清水/排污等补给动作
    CHARGING = 2    # 充电：正在前往充电或处于充电流程中
    CLEANING = 3    # 清洁：正在清洁区内执行清扫动作
    NAVIGATING = 4  # 导航：属于清洁任务的一部分，但当前是在站点间移动


class BoustrophedonPathState(IntEnum):
    """
    BoustrophedonPath 状态机。

    用于描述弓字形工艺路径本身的执行状态，只关注路径模块是否启动、
    运行、结束、失败或被暂停，不直接代表整车任务是否结束。
    """
    INIT = 0       # 初始态：尚未开始执行路径，或路径状态已被重置
    RUNNING = 1    # 运行中：正在按弓字形路径清扫
    STOP_WATER = 2 # 停水：路径即将结束，仅关闭喷水泵
    FINISHED = 3   # 已完成：本次弓字形路径执行完成
    FAILED = 4     # 失败：路径执行失败，需要上层处理
    SUSPENDED = 5  # 暂停：路径被中断或挂起，等待后续恢复/重置


class TaskType(IntEnum):
    """
    当前主任务类型。

    它回答的是“当前主流程属于哪一类任务”，通常和 vehicle_state 配合使用：
    task_type 负责标记任务类别，vehicle_state 负责标记当前执行阶段。
    """
    NONE = 0          # 无任务：当前没有挂载业务任务
    CLEAN = 1         # 清洁任务：包含清洁区清扫和清洁任务内的站点导航
    CHARGE = 2        # 充电任务：低电量触发或外部下发的充电流程
    WATER_CHANGE = 3  # 换水任务：低清水/高污水触发或外部下发的补给流程


class CleanTaskCheckpoint:
    """
    清洁任务断点数据结构。

    用于在充电/换水等高优先级任务中断清洁任务时，保存最小必要信息，
    以便后续从合适的站点位置恢复续扫。
    """

    def __init__(self):
        # 原始任务数据
        self.task_data: Optional[Dict[str, Any]] = None

        # 断点位置信息
        self.step_index: int = 0  # 中断时的步骤索引
        self.location: Optional[str] = None  # 中断时所在站点

        # 当前导航目标点信息
        self.nav_target: Optional[str] = None  # 中断时正在前往的目标点名称
        self.nav_target_index: int = -1  # 目标点在任务站点列表中的索引

        # 中断原因
        self.interrupt_reason: Optional[str] = None  # "charge" 或 "water_change"
        self.interrupt_time: float = 0.0  # 中断时间戳

        # 运单 ID
        self.order_id: Optional[str] = None

    def save_checkpoint(
            self,
            task_data: Dict[str, Any],
            step_index: int,
            location: Optional[str],
            interrupt_reason: str = "",
            order_id: Optional[str] = None,
            nav_target: Optional[str] = None,
            nav_target_index: int = -1,
    ):
        """保存断点信息。"""
        self.task_data = task_data.copy() if task_data else None
        self.step_index = step_index
        self.location = location
        self.interrupt_reason = interrupt_reason
        self.interrupt_time = time.time()
        self.order_id = order_id
        self.nav_target = nav_target
        self.nav_target_index = nav_target_index

        Trace.log(
            f"[CleanTaskCheckpoint] Saved: location={location}, "
            f"step_index={step_index}, reason={interrupt_reason}, "
            f"nav_target={nav_target}, nav_target_index={nav_target_index}"
        )

    def has_checkpoint(self) -> bool:
        """检查是否已有可恢复断点。"""
        return self.task_data is not None

    def clear(self):
        """清除断点信息。"""
        self.task_data = None
        self.step_index = 0
        self.location = None
        self.nav_target = None
        self.nav_target_index = -1
        self.interrupt_reason = None
        self.interrupt_time = 0.0
        self.order_id = None
        Trace.log("[CleanTaskCheckpoint] Cleared")

    def get_resume_info(self) -> Dict[str, Any]:
        """返回恢复清洁任务所需的断点数据。"""
        return {
            "task_data": self.task_data,
            "step_index": self.step_index,
            "nav_target": self.nav_target,
            "nav_target_index": self.nav_target_index,
        }

    def get_resume_start_index(self) -> int:
        """
        计算恢复任务时的起始索引。

        逻辑：
        - 如果已有导航目标点索引，则从它的前一个站点开始恢复
        - 如果导航目标点刚好是第一个站点，则从 0 开始
        - 如果没有导航目标点信息，则退化为 step_index
        """
        if self.nav_target_index > 0:
            return self.nav_target_index - 1
        if self.nav_target_index == 0:
            return 0
        return self.step_index


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        # 公共参数:
        pass

        # 操作组合参数
        with builder.GROUP(key="operation", name="Task Operation", desc="Choose an operation for task"):
            builder.TYPE(ParamType.COMBO_BOX)

            with builder.CHILDREN():
                with builder.CHILD(key="WashStart", name="WashStart", desc="WashStart"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="WashEnd", name="WashEnd", desc="WashEnd"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(
                        key="MechanismOpen",
                        name="MechanismOpen",
                        desc="打开清洁机构，不控制喷水",
                ):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(
                        key="MechanismClose",
                        name="MechanismClose",
                        desc="关闭清洁机构，不控制喷水",
                ):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="DustStart", name="DustStart", desc="DustStart"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="DustEnd", name="DustEnd", desc="DustEnd"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="Charge", name="Charge", desc="Charge"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="AddWater", name="AddWater", desc="AddWater"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="RunCleanPath", name="RunCleanPath", desc="RunCleanPath"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="CancelCleanPath", name="CancelCleanPath", desc="CancelCleanPath"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="ResetCleanPath", name="ResetCleanPath", desc="ResetCleanPath"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="SetTask", name="SetTask", desc="SetTask"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="SendOrders", name="SendOrders", desc="SendOrders"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="SendContinueOrders", name="SendContinueOrders", desc="SendContinueOrders"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="CancelOrder", name="CancelOrder", desc="CancelOrder"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="SendChargeOrder", name="SendChargeOrder",
                                   desc="发送充电运单（中断当前清洁任务）"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="SendWaterOrder", name="SendWaterOrder", desc="发送换水运单（中断当前清洁任务）"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="RunCleanPathAndWashStart", name="RunCleanPathAndWashStart", desc="RunCleanPathAndWashStart"):
                    builder.TYPE(ParamType.ARRAY)



    builder.save_to_file()

class EmcManager:
    """急停类"""

    def __init__(self,manager):
        self.emc_suspended_vehicle_state: Optional[VehicleState] = None
        self.emc_suspended_task_type: Optional[TaskType] = None
        self.emc_suspended_position: Optional[List[float]] = None

        self.manager = manager
    
    def _handle_emc(self, emc_status: bool):
        """
        处理急停状态变化

        Args:
            emc_status: True=急停触发, False=急停解除
        """
        if emc_status and not self.manager.emc_triggered:
            # 急停刚触发
            self._on_emc_triggered()
        elif not emc_status and self.manager.emc_triggered:
            # 急停刚解除
            self._on_emc_recovered()

    def _on_emc_triggered(self):
        """
        急停触发时的处理

        处理流程：
        1. 标记急停状态
        2. 保存当前状态（车辆状态、任务类型）
        3. 取消当前运单（发送HTTP请求到M4调度系统）
        4. 发送 CancelCleanPath 操作（如果在清洁中）
        5. 关闭清洁机构（WashEnd）
        6. 重置车辆状态为 IDLE
        """
        Trace.log("[cleanRobotManage] EMC triggered - starting emergency stop procedure")
        self.manager.emc_triggered = True

        # 1. 保存急停前的状态（用于恢复）
        self.emc_suspended_vehicle_state = self.manager.vehicle_state
        self.emc_suspended_task_type = self.manager.current_task_type
        Trace.log(
            f"[cleanRobotManage] EMC: Saved pre-EMC state: vehicle={self.manager.vehicle_state.name}, task={self.manager.current_task_type.name}")

        # 4. 关闭清洁机构
        Trace.log("[cleanRobotManage] EMC: Closing cleaning mechanism (WashEnd)")
        self.manager.call_mech("WashEnd")

        # 5. 重置车辆状态
        self.manager.vehicle_state = VehicleState.IDLE
        # 注：保持 TASK_RUNNING 状态，通过 emc_triggered 标记来表示暂停
        # 这样急停恢复后可以根据之前的状态进行恢复

        Trace.log(f"[cleanRobotManage] EMC procedure completed, position={self.emc_suspended_position}")

    def _on_emc_recovered(self):
        """
        急停解除时的处理

        根据急停前保存的状态，恢复相应的操作：
        - CLEANING: 恢复清洁任务，从断点位置继续
        - NAVIGATING: 恢复导航状态
        - CHARGING/ADD_WATER: 恢复充电/换水状态
        - 其他: 恢复为空闲状态
        """
        Trace.log("[cleanRobotManage] EMC recovered - starting recovery procedure")
        self.manager.emc_triggered = False

        # 根据急停前的状态进行恢复
        if self.emc_suspended_vehicle_state == VehicleState.CLEANING:
            # 恢复清洁任务
            Trace.log("[cleanRobotManage] EMC Recovery: Resuming CLEANING state")
            self._resume_clean_after_emc()
        elif self.emc_suspended_vehicle_state == VehicleState.NAVIGATING:
            # 恢复导航状态
            Trace.log("[cleanRobotManage] EMC Recovery: Resuming NAVIGATING state")
            self.manager.vehicle_state = VehicleState.NAVIGATING
            self.manager.current_task_type = self.emc_suspended_task_type
            self.manager.erp_state = ERPState.NORMAL
        elif self.emc_suspended_vehicle_state in (VehicleState.CHARGING, VehicleState.ADD_WATER):
            # 恢复充电/换水状态
            Trace.log(f"[cleanRobotManage] EMC Recovery: Resuming {self.emc_suspended_vehicle_state.name} state")
            self.manager.vehicle_state = self.emc_suspended_vehicle_state
            self.manager.current_task_type = self.emc_suspended_task_type
            self.manager.erp_state = ERPState.NORMAL
        else:
            # 其他情况恢复为空闲状态
            Trace.log("[cleanRobotManage] EMC Recovery: Resuming to IDLE state")
            self.manager.vehicle_state = VehicleState.IDLE
            self.manager.erp_state = ERPState.NORMAL

        # 清理急停临时数据
        self.emc_suspended_vehicle_state = None
        self.emc_suspended_task_type = None
        self.emc_suspended_position = None
        Trace.log("[cleanRobotManage] EMC recovery completed")

    def _resume_clean_after_emc(self):
        """急停恢复后继续清洁任务"""
        Trace.log(f"[cleanRobotManage] Resuming clean after EMC, position={self.emc_suspended_position}")

        # 使用保存的位置作为起始点
        if self.emc_suspended_position:
            self.manager.current_start_pos = self.emc_suspended_position

        self.manager.current_task_type = TaskType.CLEAN
        self.manager.vehicle_state = VehicleState.CLEANING
        self.manager.erp_state = ERPState.NORMAL

        self.manager.call_mech(
            "WashStart",
            brush_power=config_params.brush_power,
            suck_power=config_params.suck_power,
            jet_power=config_params.jet_power,
            auto_adjust_power=config_params.auto_adjust_power,
        )
    



# ============================================================
#  主管理类
# ============================================================

class CleanRobotManage:

    def __init__(self):
        # ========== 状态机 ==========
        self.erp_state = ERPState.NORMAL
        # 删除 mech_state：机构状态由 CleanRobotMech 内部管理
        self.vehicle_state = VehicleState.IDLE
        self.boustrophedon_path_state = BoustrophedonPathState.INIT

        self.current_task_type = TaskType.NONE

        # ========== 机构脚本实例 ==========
        self.mech = CleanRobotMech()

        # ========== 任务缓存 ==========

        self.current_task: Optional[Dict[str, Any]] = None
        self.current_order_id: Optional[str] = None
        try:
            self.clean_db = LevelDB("clean")
        except Exception as exc:
            self.clean_db = None
            Trace.log(f"[cleanRobotManage] Failed to initialize clean order database: {exc}")
        self.order_detail_cache: Optional[Dict[str, Any]] = None
        self.order_detail_cache_id: Optional[str] = None
        self.order_detail_query_time: float = 0.0
        self.order_detail_log_state: Optional[Tuple[str, str]] = None
        self.last_scheduler_error: str = ""
        self.scheduler_retry_count: int = 0

        # ========== 自动任务标记 ==========
        self.auto_charge_sent = False
        self.auto_water_sent = False

        # ========== 水位信息 ==========
        self.clean_water_level: Optional[float] = None
        self.waste_water_level: Optional[float] = None

        # ========== 清洁路径上下文（由外部传入，用于弓字形清扫）==========
        self.current_entrance: Optional[str] = None
        self.current_exit: Optional[str] = None
        self.current_start_pos: Optional[List[float]] = None  # [x, y, yaw] 断点续扫位置

        # ========== 清洁任务断点 ==========
        self.clean_checkpoint = CleanTaskCheckpoint()

        # ========== 上报信息 ==========
        self.report_info: Dict[str, Any] = {}

        # ========== 急停相关 ==========
        self.emc_triggered = False

        # ========== 当前导航目标点跟踪 ==========
        self.current_nav_target: Optional[str] = None  # 当前正在前往的目标点名称

        # ========== 每日定时清洁任务 ==========
        self.last_scheduled_clean_date: Optional[str] = None  # 上次执行定时清洁的日期，格式 "YYYY-MM-DD"
        self.scheduled_clean_triggered_today: bool = False  # 今天是否已触发定时清洁
        self.debug_order_attempted: bool = False  # 调试模式启动后是否已经尝试过立即发单
        self.scheduled_clean_pending_routes: List[List[str]] = []
        self.scheduled_clean_order_id: Optional[str] = None
        self.restored_order_sent = False

        self.priority_task_phase: Optional[str] = None
        self.priority_task_reason: Optional[str] = None
        self.priority_exit_required = False
        self.clean_area_pairs: List[Tuple[str, str]] = []
        self.clean_area_index = 0
        self.failed_clean_area_index: Optional[int] = None
        self.simulation_clean_area_count = 0
        self.simulation_charge_started_at = None
        self.simulation_charge_arrived_at = None

        self.saved_exit_id = None
        self.have_cancelled = False

        self.clean_close_pending = False

        # call_mech 原始参数
        self.pre_arg=None

        self.firstRun = True
        self.firstOpen = True

        Trace.log("[cleanRobotManage] Initialized")

    # ============================================================
    #  获取当前导航目标点
    # ============================================================


    def _get_current_nav_target(self) -> Optional[str]:
        """
        获取当前导航过程中的目标点名称

        Returns:
            目标点名称，如 "LM1001"、"AP3" 等，无导航任务时返回 None
        """
        try:
            target_name = Navigation.moveTask().get("targetName", None)
            if target_name:
                self.current_nav_target = target_name
                Trace.log(f"[cleanRobotManage] Current nav target: {target_name}")
            return target_name
        except Exception as e:
            Trace.log(f"[cleanRobotManage] Error getting nav target: {e}")
            return None

    def _get_nav_target_index_in_task(self) -> int:
        """
        获取当前导航目标点在任务站点列表中的索引

        Returns:
            索引值，未找到返回 -1
        """
        if not self.current_task or not self.current_nav_target:
            return -1

        try:
            return self.current_task.get("step_locations", []).index(self.current_nav_target)
        except ValueError:
            Trace.log(f"[cleanRobotManage] Nav target {self.current_nav_target} not found in task locations")
            return -1

    def _get_current_task_step(self) -> int:
        """
        估算当前任务进度索引，用于状态上报。

        优先使用当前导航 sourceName；若没有，则退化为 targetName 的前一站。
        """
        if not self.current_task:
            return 0

        step_locations = self.current_task.get("step_locations", [])
        if not step_locations:
            return 0

        try:
            move_task = Navigation.moveTask()
        except Exception:
            return 0

        source_name = move_task.get("sourceName", None)
        target_name = self.current_nav_target or move_task.get("targetName", None)

        if source_name in step_locations:
            return step_locations.index(source_name)

        if target_name in step_locations:
            return max(step_locations.index(target_name) - 1, 0)

        return 0

    def _save_order_state(self, status: str = "EXECUTING"):
        """保存当前运单的最小恢复状态。"""
        if not self.clean_db or not self.current_order_id:
            return
        data = {
            "order_id": self.current_order_id,
            "order_type": self.current_task_type.name,
            "status": status,
            "clean_area_pairs": [list(pair) for pair in self.clean_area_pairs],
            "clean_area_index": self.clean_area_index,
        }
        try:
            self.clean_db.put(f"order:{self.current_order_id}",
                              json.dumps(data, ensure_ascii=False))
            self.clean_db.put("active_order_id", self.current_order_id)
        except Exception as exc:
            Trace.log(f"[cleanRobotManage] Failed to save order state: {exc}")

    def _load_order_state(self) -> Optional[Dict[str, Any]]:
        if not self.clean_db:
            return None
        try:
            order_id = self.clean_db.get("active_order_id", "str")
            raw = self.clean_db.get(f"order:{order_id}", "str") if order_id else None
            return json.loads(raw) if raw else None
        except Exception as exc:
            Trace.log(f"[cleanRobotManage] Failed to load order state: {exc}")
            return None

    def _set_order_state_status(self, status: str):
        state = self._load_order_state()
        if not state or state.get("status") == "COMPLETED":
            return
        state["status"] = status
        try:
            self.clean_db.put(f"order:{state['order_id']}",
                              json.dumps(state, ensure_ascii=False))
        except Exception as exc:
            Trace.log(f"[cleanRobotManage] Failed to update order state: {exc}")

    def _send_clean_from_saved_state(self, state: Dict[str, Any]) -> bool:
        saved_order_id = state.get("order_id")
        pairs = [tuple(pair) for pair in state.get("clean_area_pairs", [])
                 if isinstance(pair, list) and len(pair) == 2]
        try:
            area_index = int(state.get("clean_area_index", 0))
        except (TypeError, ValueError):
            area_index = 0
        area_index = min(max(0, area_index), len(pairs))
        remaining = [point for pair in pairs[area_index:] for point in pair]
        if not remaining:
            Trace.log(
                f"[cleanRobotManage] No remaining clean route in saved state: "
                f"order_id={saved_order_id}, area_index={area_index}/{len(pairs)}"
            )
            return False
        Trace.log(
            f"[cleanRobotManage] Restoring clean route from saved state: "
            f"order_id={saved_order_id}, area_index={area_index}/{len(pairs)}, "
            f"locations={remaining}"
        )
        order_id = self.post_to_scheduler(
            self._build_simple_order(remaining, config_params.robot_name, 50))
        if not order_id:
            Trace.log(
                f"[cleanRobotManage] Failed to send restored clean order: "
                f"source_order_id={saved_order_id}"
            )
            return False
        self.current_task = {
            "step_locations": remaining,
            "robot_name": config_params.robot_name,
            "priority": 50,
            "task_id": f"recovered_clean_{int(time.time())}",
        }
        self.current_task_type = TaskType.CLEAN
        self.current_order_id = order_id
        self._reset_clean_area_progress(remaining)
        self._save_order_state()
        self.restored_order_sent = True
        Trace.log(
            f"[cleanRobotManage] Restored clean order sent: "
            f"source_order_id={saved_order_id}, order_id={order_id}"
        )
        return True

    def restore_order_from_db(self):
        """启动时检查旧运单，并按保存的剩余路线恢复后续任务。"""
        state = self._load_order_state()
        if not state:
            return

        order_id = state.get("order_id")
        order_type = state.get("order_type")
        if state.get("status") == "COMPLETED":
            if order_type in (TaskType.CHARGE.name, TaskType.WATER_CHANGE.name):
                self._send_clean_from_saved_state(state)
            return
        pairs = [tuple(pair) for pair in state.get("clean_area_pairs", [])
                 if isinstance(pair, list) and len(pair) == 2]
        try:
            area_index = int(state.get("clean_area_index", 0))
        except (TypeError, ValueError):
            area_index = 0
        self.clean_area_pairs = pairs
        self.clean_area_index = min(area_index, len(pairs))

        detail = self._query_order_detail(order_id)
        if not detail:
            return
        status = detail.get("status") if detail else None
        if isinstance(status, dict):
            status = status.get("name") or status.get("value")
        status = str(status).split(".")[-1].lower()
        supply_order = order_type in (TaskType.CHARGE.name, TaskType.WATER_CHANGE.name)
        supply_done = (not config_params.isTrue and supply_order and
                       self._supply_ready())
        if status == "done" or supply_done:
            self._set_order_state_status("COMPLETED")
            if supply_order:
                self._send_clean_from_saved_state(state)
            return
        if status in ("cancelled", "canceled"):
            Trace.log(
                f"[cleanRobotManage] Saved order was cancelled; skip recovery: "
                f"order_id={order_id}"
            )
            return

        self.current_order_id = order_id
        if status in {"tobeallocated", "allocated", "pending", "executing",
                      "cancelling", "withdrawing"}:
            if not self._cancel_current_order():
                return

        if order_type == TaskType.CLEAN.name:
            self._send_clean_from_saved_state(state)
            return

        elif order_type in (TaskType.CHARGE.name, TaskType.WATER_CHANGE.name):
            if config_params.isTrue and order_type == TaskType.CHARGE.name:
                payload = self._build_simple_order(
                    [config_params.charging_site], config_params.robot_name, 60)
            else:
                payload = (self.build_water_order_json()
                           if order_type == TaskType.WATER_CHANGE.name
                           else self.build_charge_order_json())
            new_order_id = self.post_to_scheduler(payload)
            if not new_order_id:
                return
            self.current_order_id = new_order_id
            self.current_task_type = (TaskType.WATER_CHANGE
                                      if order_type == TaskType.WATER_CHANGE.name
                                      else TaskType.CHARGE)
            self.vehicle_state = (VehicleState.ADD_WATER
                                   if self.current_task_type == TaskType.WATER_CHANGE
                                   else VehicleState.CHARGING)
            self._save_order_state()

    def _supply_ready(self) -> bool:
        soc = Battery.getPercentage()
        clean_level = self.clean_water_level
        waste_level = self.waste_water_level
        if clean_level is None or waste_level is None:
            clean_level, waste_level = self.get_water_levels()
            self.clean_water_level = clean_level
            self.waste_water_level = waste_level
        return (soc >= config_params.high_battery_soc and
                clean_level not in (None, -1) and
                waste_level not in (None, -1) and
                clean_level >= config_params.max_clean_water_level and
                waste_level <= config_params.min_waste_water_level)
    def _reset_clean_area_progress(self, route_locations: List[str]):
        """从路线提取 AP 清扫区域，LM 点仅用于导航。"""
        ap_points = [location for location in route_locations
                     if isinstance(location, str) and location.startswith("AP")]
        self.clean_area_pairs = list(zip(ap_points[::2], ap_points[1::2]))
        self.clean_area_index = 0
        self.failed_clean_area_index = None

    def _mark_clean_area_finished(self):
        """仅在弓字形清扫完成后推进清扫区域索引。"""
        if self.clean_area_index >= len(self.clean_area_pairs):
            return
        current_pair = (self.current_entrance, self.current_exit)
        if current_pair == self.clean_area_pairs[self.clean_area_index]:
            self.failed_clean_area_index = None
            self.clean_area_index += 1
            Trace.log(f"[cleanRobotManage] Clean area finished: {current_pair}, "
                      f"next_index={self.clean_area_index}")
            self._save_order_state(
                "COMPLETED" if self.clean_area_index >= len(self.clean_area_pairs)
                else "EXECUTING"
            )

    # ============================================================
    #  ERP状态机
    # ============================================================

    def _query_order_detail(self, order_id: str) -> Optional[Dict[str, Any]]:
        """查询当前脚本运单详情，1秒内复用查询结果。"""
        if not order_id or not isinstance(order_id, str):
            return None

        now = time.time()
        if (self.order_detail_cache_id == order_id and
                now - self.order_detail_query_time < 1.0):
            return self.order_detail_cache

        self.order_detail_query_time = now
        self.order_detail_cache_id = order_id
        detail = None
        log_state = (order_id, "failed")
        log_message = ""
        try:
            response = requests.get(
                get_scheduler_order_detail_url(),
                params={"orderId": order_id},
                headers={
                    "xyy-app-id": config_params.m4_app_id,
                    "xyy-app-key": config_params.m4_app_key,
                },
                timeout=5,
            )
            if response.status_code != 200:
                log_message = f"[cleanRobotManage] Failed to query order detail {order_id}: HTTP {response.status_code}"
            else:
                detail = response.json()
                if isinstance(detail, dict):
                    detail = (detail.get("order-detail") or
                              detail.get("orderDetail") or
                              detail.get("data") or detail)
                if isinstance(detail, dict) and detail:
                    log_state = (order_id, "success")
                    log_message = f"[cleanRobotManage] Order detail query succeeded: {order_id}"
                else:
                    detail = None
                    log_message = f"[cleanRobotManage] Invalid order detail response: {order_id}"
        except Exception as exc:
            log_message = f"[cleanRobotManage] Failed to query order detail {order_id}: {exc}"

        if self.order_detail_log_state != log_state:
            Trace.log(log_message)
            self.order_detail_log_state = log_state
        if detail is not None:
            self.order_detail_cache = detail
            return detail
        self.order_detail_cache = None
        return None

    def _has_active_script_order(self) -> bool:
        """只有脚本记录的有效运单才允许执行清扫。"""
        if not self.current_order_id or not isinstance(self.current_order_id, str):
            return False

        detail = self._query_order_detail(self.current_order_id)
        if not detail:
            return False

        status = detail.get("status")
        if isinstance(status, dict):
            status = status.get("name") or status.get("value")
        status = str(status).split(".")[-1].lower()
        if status in ("done", "cancelled", "canceled"):
            self.current_order_id = None
            self.current_task = None
            if self.current_task_type == TaskType.CLEAN:
                self.current_task_type = TaskType.NONE
                self.vehicle_state = VehicleState.IDLE
            self.order_detail_cache = None
            self.order_detail_cache_id = None
            return False
        return status in {
            "tobeallocated",
            "allocated",
            "pending",
            "executing",
            "cancelling",
            "withdrawing",
        }

    def can_dispatch_to_m4(self) -> bool:
        if self.current_task_type == TaskType.CLEAN and self.current_task:
            self._has_active_script_order()
        return self.erp_state == ERPState.NORMAL and self.current_task_type == TaskType.NONE

    # ============================================================
    #  车辆状态机更新
    # ============================================================

    def _vehicle_state_update(self):
        """
        车辆状态机更新

        注：此方法与 _erp_state_update 存在部分功能重叠，
        实际使用时可以选择其一，或者整合为一个统一的状态更新逻辑
        """
        if self.current_task_type == TaskType.NONE:
            self.vehicle_state = VehicleState.IDLE
        elif self.current_task_type == TaskType.CHARGE:
            self.vehicle_state = VehicleState.CHARGING
        elif self.current_task_type == TaskType.WATER_CHANGE:
            self.vehicle_state = VehicleState.ADD_WATER
        elif self.current_task_type == TaskType.CLEAN:
            # 根据弓字形路径状态判断是清洁中还是导航中
            # - 弓字形路径运行中 → CLEANING（正在执行清扫）
            # - 其他状态 → NAVIGATING（在站点间移动）
            if self.boustrophedon_path_state == BoustrophedonPathState.RUNNING:
                self.vehicle_state = VehicleState.CLEANING
            else:
                self.vehicle_state = VehicleState.NAVIGATING

    # ============================================================
    #  BoustrophedonPath状态机更新
    # ============================================================

    def _boustrophedon_path_state_update(self, status_value: int):
        try:
            new_state = BoustrophedonPathState(status_value)
            self.boustrophedon_path_state = new_state
        except ValueError:
            Trace.log(f"[BOUSTROPHEDON_PATH] Unknown status value: {status_value}")

    # ============================================================
    #  清洁任务中断与恢复机制
    # ============================================================

    def _interrupt_clean_for_priority_task(self, interrupt_reason: str) -> bool:
        """
        中断当前清洁任务以执行高优先级任务（充电/换水）

        流程：
        1. 获取当前导航目标点（通过 Navigation.moveTask().get("targetName")）
        2. 获取机器人当前位置（通过 Loc.getPos()）
        3. 如果弓字形路径正在运行，先取消它
        4. 保存断点
        5. 保留当前运单；后续关闭机构、驶出清洁区域后再取消运单

        恢复逻辑：
        - 假设原任务: [LM1, LM2, AP3, AP4, LM5, AP6, AP7, AP8, AP9, AP10, LM11, LM12]
        - 中断时正在前往 AP8（nav_target_index = 7）
        - 恢复时从 AP7（index 6）开始，发送: [AP7, AP8, AP9, AP10, LM11, LM12]
        """
        if self.current_task_type != TaskType.CLEAN or (not self.current_task and not config_params.isTrue):
            Trace.log(f"[cleanRobotManage] No clean task to interrupt, reason={interrupt_reason}")
            return True

        Trace.log(f"[cleanRobotManage] Interrupting clean task for {interrupt_reason}")

        try:
            step_locations = self.current_task.get("step_locations", [])
        except Exception:
            Trace.log(f"[cleanRobotManage] Error in get step_locations: {self.current_task}")
            step_locations = []
        current_location = step_locations[0] if step_locations else None

        # 1. 获取当前导航目标点
        nav_target = self._get_current_nav_target()
        nav_target_index = self._get_nav_target_index_in_task()
        Trace.log(f"[cleanRobotManage] Current nav target: {nav_target}, index: {nav_target_index}")

        # 2. 直接获取机器人当前位置（使用 Loc.getPos()）
        robot_position = [Loc.getPose()["x"], Loc.getPose()["y"], math.radians(Loc.getPose()["yaw"])]

        # 3. 如果弓字形路径正在运行，取消它
        self.saved_exit_id = self.current_exit

        if self.boustrophedon_path_state == BoustrophedonPathState.RUNNING:
            Trace.log("[cleanRobotManage] Cancelling running boustrophedon path")
            cancel_result = self._cancel_boustrophedon_path()
            # 如果取消操作返回了位置，优先使用它（更精确）
            if cancel_result and isinstance(cancel_result, (list, dict)):
                if isinstance(cancel_result, list) and len(cancel_result) >= 3:
                    robot_position = cancel_result
                    Trace.log(f"[cleanRobotManage] Got position from cancelBoustrophedonPath: {robot_position}")
                elif isinstance(cancel_result, dict):
                    robot_position = [cancel_result.get("x", 0), cancel_result.get("y", 0),
                                      cancel_result.get("theta", 0)]
                    Trace.log(f"[cleanRobotManage] Got position from cancelBoustrophedonPath: {robot_position}")

        # 4. 保存断点（包含机器人位置，用于断点续扫）TODO：导航记录断点，脚本可删除
        self.clean_checkpoint.save_checkpoint(
            task_data=self.current_task,
            step_index=0,  # 原 CleanTaskData.current_step_index 从未被更新，始终为 0
            location=current_location,
            interrupt_reason=interrupt_reason,
            order_id=self.current_order_id,
            nav_target=nav_target,
            nav_target_index=nav_target_index,
            # robot_position=robot_position  # 保存机器人位置用于恢复
        )

        # 5. 保留当前运单的导航上下文，驶出清洁区域后再取消运单
        self.have_cancelled = True
    
        self.current_task = None
        self.current_task_type = TaskType.NONE
        self.vehicle_state = VehicleState.IDLE
        self.boustrophedon_path_state = BoustrophedonPathState.INIT
        self.current_nav_target = None

        Trace.log(f"[cleanRobotManage] Clean task interrupted, checkpoint saved with "
                  f"nav_target={nav_target}, nav_target_index={nav_target_index}, "
                  f"robot_position={robot_position}")
        return True

    def _cancel_boustrophedon_path(self) -> dict:
        """取消弓字形导航，返回当前机器人位置 [x, y, yaw]"""
        return Navigation.cancelBoustrophedonPath()


    def _check_and_resume_clean_task(self):
        """检查充电/换水是否完成，如果完成则恢复清洁任务"""
        if self.priority_task_phase:
            return

        if not self.clean_checkpoint.has_checkpoint():
            return

        if self.erp_state != ERPState.NORMAL:
            return

        interrupt_reason = self.clean_checkpoint.interrupt_reason
        can_resume = False

        if interrupt_reason == "charge":
            if config_params.isTrue and config_params.simulation_charge_enabled:
                detail = self._query_order_detail(self.current_order_id)
                status = detail.get("status") if detail else None
                if isinstance(status, dict):
                    status = status.get("name") or status.get("value")
                status = str(status).split(".")[-1].lower()
                if status == "done" and self.simulation_charge_arrived_at is None:
                    self.simulation_charge_arrived_at = time.time()
                    Trace.log("[cleanRobotManage] Simulated charge point reached, waiting 5s")
                if (self.simulation_charge_arrived_at is not None and
                        time.time() - self.simulation_charge_arrived_at >= 5.0):
                    can_resume = True
                    Trace.log("[cleanRobotManage] Simulated charge completed, ready to resume")
            elif not config_params.isTrue and self._supply_ready():
                soc = Battery.getPercentage()
                can_resume = True
                Trace.log(f"[cleanRobotManage] Supply completed (SOC={soc}), ready to resume")

        elif interrupt_reason == "water_change":
            if self._supply_ready():
                can_resume = True
                Trace.log(f"[cleanRobotManage] Supply completed, ready to resume")

        if can_resume:
            self._set_order_state_status("COMPLETED")
        if can_resume and self._resume_clean_task_from_checkpoint():
            self.simulation_charge_arrived_at = None
            if interrupt_reason == "charge":
                self.auto_charge_sent = False
            elif interrupt_reason == "water_change":
                self.auto_water_sent = False

    def _resume_clean_task_from_checkpoint(self):
        """
        从断点恢复清洁任务（简化版）

        恢复逻辑：
        - 使用 get_resume_start_index() 计算恢复起点
        - 如果中断时正在前往 AP8（nav_target_index = 7），则从 AP7（index 6）开始
        - 例如：原任务 [LM1, LM2, AP3, AP4, LM5, AP6, AP7, AP8, AP9, AP10, LM11, LM12]
                中断于前往 AP8，恢复时发送 [AP7, AP8, AP9, AP10, LM11, LM12]
        """
        resume_info = self.clean_checkpoint.get_resume_info()
        if not resume_info["task_data"]:
            Trace.log("[cleanRobotManage] No task data to resume")
            self.clean_checkpoint.clear()
            return False

        # 计算恢复起点
        resume_start_index = self.clean_checkpoint.get_resume_start_index()

        Trace.log(f"[cleanRobotManage] Resuming clean task from checkpoint: "
                  f"location={self.clean_checkpoint.location}, "
                  f"nav_target={resume_info.get('nav_target')}, "
                  f"nav_target_index={resume_info.get('nav_target_index')}, "
                  f"resume_start_index={resume_start_index}")

        # 构造恢复任务数据
        original_task = resume_info["task_data"]
        original_locations = original_task.get("step_locations", [])

        # 从计算出的恢复起点开始的站点列表
        resume_locations = original_locations[resume_start_index:]

        Trace.log(f"[cleanRobotManage] Original locations: {original_locations}")
        Trace.log(f"[cleanRobotManage] Resume locations (from index {resume_start_index}): {resume_locations}")

        resume_task_data = original_task.copy()
        resume_task_data["step_locations"] = resume_locations
        resume_task_data["task_id"] = f"{original_task.get('task_id', '')}_resume_{int(time.time())}"

        # 构造并发送恢复运单（使用简单格式）
        payload = self._build_simple_order(
            step_locations=resume_locations,
            robot_name=resume_task_data.get("robot_name", config_params.robot_name),
            priority=resume_task_data.get("priority", 50)
        )
        Trace.log(f"[cleanRobotManage] Sending resume clean order")
        order_id = self.post_to_scheduler(payload)
        if not order_id:
            Trace.log(f"[cleanRobotManage] Failed to send resume clean order")
            return False

        self.current_task = resume_task_data
        self.current_task_type = TaskType.CLEAN
        self.current_order_id = order_id
        self._reset_clean_area_progress(resume_locations)
        self._save_order_state()
        if str(resume_task_data.get("task_id", "")).startswith("scheduled_clean_"):
            self.scheduled_clean_order_id = order_id

        self.erp_state = ERPState.NORMAL
        self.clean_checkpoint.clear()
        return True

    # ============================================================
    #  外部调用接口
    # ============================================================

    def period_run(self):
        self.mech.period_run()

    def reset_state(self):
        if not self.priority_task_phase:
            self.mech.reset_state()
        self.clean_close_pending = False

    def run(self, args: Dict[str, Any], isFirstRun: bool = False):
        op = args.get("operation")
        if not op:
            Trace.log(f"[cleanRobotManage] run() called with operation=None, args={args}")

        self._update_path_context(args)

        if op == "RunCleanPathAndWashStart":
            if isFirstRun:
                Trace.log(f"[cleanRobotManage] First go clean path and wash start, validated_params={args}")
            if config_params.isTrue:
                self._handle_run_clean_path_and_wash(args, is_wash=True)
            elif self.firstRun:
                if self.firstOpen:
                    tem_statu = self.call_mech("MechanismOpen")
                    if tem_statu in (ScriptStatus.FINISHED, ScriptStatus.FAILED):
                        self.firstOpen = False
                else:
                    tem_statu2=self.call_mech("MechanismClose")
                    if tem_statu2 in (ScriptStatus.FINISHED, ScriptStatus.FAILED):
                        self.firstRun = False
            else:
                self._handle_run_clean_path_and_wash(args, is_wash=True)
        elif op == "RunCleanPath":
            if isFirstRun:
                Trace.log(f"[cleanRobotManage] First go clean path, validated_params={args}")
            self._handle_run_clean_path_and_wash(args, is_wash=False)
        elif op == "AddWater":
            self._handle_add_water()
        elif op in ("MechanismOpen", "MechanismClose"):
            if config_params.isTrue:
                Trace.log(f"[cleanRobotManage] {op} is unavailable in simulation mode")
                Module.setStatus(ScriptStatus.FAILED)
                return
            mech_status = self.call_mech(op)
            if mech_status in (ScriptStatus.FINISHED, ScriptStatus.FAILED):
                Module.setStatus(mech_status)
        elif op == "CancelCleanPath":
            Trace.log(f"[cleanRobotManage] run() operation={op}, args={args}")
            self._handle_cancel_clean_path('water_change')
        elif op == "ResetCleanPath":
            Trace.log(f"[cleanRobotManage] run() operation={op}, args={args}")
            self._handle_reset_clean_path()
        else:
            if isFirstRun:
                Trace.log(f"[cleanRobotManage] run() called with unknown operation={op}, args={args}")

    # 开始清扫任务接口
    def _handle_run_clean_path_and_wash(self, args: Dict[str, Any], is_wash: bool = False):
        if self.priority_task_phase:
            return

        if not self.current_task or not self._has_active_script_order():
            mech_status = (ScriptStatus.FINISHED if config_params.isTrue
                           else self.call_mech("WashEnd"))
            if mech_status == ScriptStatus.FAILED:
                self.current_task_type = TaskType.NONE
                self.vehicle_state = VehicleState.IDLE
                Module.setStatus(ScriptStatus.FAILED)
                return
            if mech_status != ScriptStatus.FINISHED:
                return

            move_task = Navigation.moveTask()
            self.current_entrance = move_task.get("sourceName", None)
            self.current_exit = move_task.get("targetName", None)
            if not self.current_exit:
                return

            self.current_task_type = TaskType.NONE
            self.vehicle_state = VehicleState.NAVIGATING
            self.run_cross_path()
            return

        if self.clean_close_pending:
            if (config_params.isTrue or
                    self.call_mech("WashEnd") == ScriptStatus.FINISHED):
                terminal_status = (
                    ScriptStatus.FAILED
                    if self.boustrophedon_path_state == BoustrophedonPathState.FAILED
                    else ScriptStatus.FINISHED
                )
                self.clean_close_pending = False
                Navigation.resetBoustrophedonPath()
                Module.setStatus(terminal_status)
            return

        self.current_task_type = TaskType.CLEAN
        self.vehicle_state = VehicleState.CLEANING

        source = Navigation.moveTask().get("sourceName", None)
        target = Navigation.moveTask().get("targetName", None)
        target_is_next = (
            self.clean_area_index < len(self.clean_area_pairs) and
            (source, target) == self.clean_area_pairs[self.clean_area_index]
        )
        if (not target_is_next and
                self.failed_clean_area_index == self.clean_area_index and
                self.clean_area_index + 1 < len(self.clean_area_pairs) and
                (source, target) == self.clean_area_pairs[self.clean_area_index + 1]):
            self.clean_area_index += 1
            self.failed_clean_area_index = None
            self._save_order_state()
            target_is_next = True
            Trace.log(
                f"[cleanRobotManage] Skipping failed clean area, "
                f"resume_index={self.clean_area_index}, target={source}->{target}"
            )

        if self.current_entrance != source or self.current_exit != target:
            self.current_entrance = source
            self.current_exit = target
            Trace.log(f"[cleanRobotManage] run_clean_path: path context changed, {self.current_entrance} -> {self.current_exit}")
            if not target_is_next:
                Trace.log(f"[cleanRobotManage] Target {target} is not the next clean route step, crossing without cleaning")
            elif config_params.isTrue and config_params.simulation_charge_enabled:
                self.simulation_clean_area_count += 1
                if self.simulation_clean_area_count == 2:
                    self.simulation_charge_started_at = time.time()
                    Trace.log("[cleanRobotManage] Second clean area entered, simulated charge timer started")

        if (config_params.isTrue and config_params.simulation_charge_enabled and
                self.simulation_charge_started_at is not None and
                self.simulation_clean_area_count == 2 and
                time.time() - self.simulation_charge_started_at >= 10.0):
            self.simulation_charge_started_at = None
            Trace.log("[cleanRobotManage] Second clean area ran for 10s, interrupting for simulated charge")
            self._handle_cancel_clean_path("charge")
            return

        if not target_is_next:
            mech_status = (ScriptStatus.FINISHED if config_params.isTrue
                           else self.call_mech("WashEnd"))
            if mech_status == ScriptStatus.FAILED:
                Module.setStatus(ScriptStatus.FAILED)
                return
            if mech_status != ScriptStatus.FINISHED:
                return
            self.vehicle_state = VehicleState.NAVIGATING
            self.run_cross_path()
            return
        if not self.saved_exit_id:
            if is_wash:
                self.run_clean_path_and_wash(args)
            else:
                self.run_clean_path()
        else:
            if self.saved_exit_id != self.current_exit and self.current_exit != "":
                self.run_cross_path()
            elif self.have_cancelled:
                self.run_exit_path()  # self.have_cancelled重置
            elif self.saved_exit_id == self.current_exit:
                if is_wash and not config_params.isTrue:
                    mech_status = self.call_mech(
                        "WashStart",
                        brush_power=args.get("brush_power"),
                        suck_power=args.get("suck_power"),
                        jet_power=args.get("jet_power"),
                        auto_adjust_power=args.get("auto_adjust_power"),
                    )
                    if mech_status != ScriptStatus.FINISHED:
                        return
                self.run_remaining_path()  # self.saved_exit_id重置
            else:
                pass

    def _handle_add_water(self):
        if self.vehicle_state == VehicleState.CLEANING:
            self._cancel_boustrophedon_path()
        self.current_task_type = TaskType.WATER_CHANGE
        self.vehicle_state = VehicleState.ADD_WATER
        mech_status = self.call_mech("AddWater")
        if mech_status in (ScriptStatus.FINISHED, ScriptStatus.FAILED):
            Module.setStatus(mech_status)

    #暂停清扫任务
    def _handle_cancel_clean_path(self,reason:str=""):
        if self.priority_task_phase:
            return
        if (self.clean_close_pending and
                self.boustrophedon_path_state == BoustrophedonPathState.FINISHED):
            return

        path_active = self.boustrophedon_path_state in (
            BoustrophedonPathState.RUNNING,
            BoustrophedonPathState.STOP_WATER,
            BoustrophedonPathState.SUSPENDED,
        )
        if path_active and (not self.current_entrance or not self.current_exit):
            Trace.log("[cleanRobotManage] Cannot interrupt clean task: missing path context")
            self.erp_state = ERPState.ERROR
            Module.setStatus(ScriptStatus.FAILED)
            return
        self.priority_exit_required = path_active
        if not self._interrupt_clean_for_priority_task(reason):
            self.priority_exit_required = False
            Module.setStatus(ScriptStatus.FAILED)
            return

        self.priority_task_reason = reason
        self.priority_task_phase = "CLOSING"
        Trace.log(f"[cleanRobotManage] Priority task transition started: reason={reason}, phase=CLOSING")

    def _continue_priority_task(self):
        """关闭机构并驶出清洁区域后，再发送充电或换水运单。"""
        if not self.priority_task_phase:
            return

        if self.priority_task_phase == "CLOSING":
            mech_status = (ScriptStatus.FINISHED if config_params.isTrue
                           else self.call_mech("WashEnd"))
            if mech_status == ScriptStatus.FAILED:
                self.priority_task_phase = None
                self.priority_task_reason = None
                self.priority_exit_required = False
                self.erp_state = ERPState.ERROR
                Module.setStatus(ScriptStatus.FAILED)
                return
            if mech_status != ScriptStatus.FINISHED:
                return

            self.priority_task_phase = "EXITING" if self.priority_exit_required else "SENDING"
            Trace.log(f"[cleanRobotManage] Priority task transition phase={self.priority_task_phase}")
            return

        if self.priority_task_phase == "EXITING":
            self.vehicle_state = VehicleState.NAVIGATING
            self.run_exit_path(report_status=True)
            if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
                self.priority_task_phase = "SENDING"
                Trace.log("[cleanRobotManage] Priority task transition phase=SENDING")
            elif self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
                self.priority_task_phase = None
                self.priority_task_reason = None
                self.priority_exit_required = False
            return

        reason = self.priority_task_reason
        simulated_charge = (config_params.isTrue and
                            config_params.simulation_charge_enabled and
                            reason == "charge")
        if self.current_order_id and (not config_params.isTrue or simulated_charge):
            if not self._cancel_current_order():
                self.priority_task_phase = None
                self.priority_task_reason = None
                self.priority_exit_required = False
                self.erp_state = ERPState.ERROR
                Module.setStatus(ScriptStatus.FAILED)
                return
        if reason == "water_change":
            payload = self.build_water_order_json()
        elif simulated_charge:
            payload = self._build_simple_order(
                [config_params.charging_site], config_params.robot_name, 60)
        else:
            payload = self.build_charge_order_json()
        order_id = (self.post_to_scheduler(payload)
                    if not config_params.isTrue or simulated_charge else True)
        if not order_id:
            Trace.log(f"[cleanRobotManage] Failed to send order ({reason})")
            self.priority_task_phase = None
            self.priority_task_reason = None
            self.priority_exit_required = False
            self.erp_state = ERPState.ERROR
            Module.setStatus(ScriptStatus.FAILED)
            return

        self.current_order_id = order_id
        if reason == "water_change":
            self.auto_water_sent = True
        else:
            self.auto_charge_sent = True
        self.current_task_type = TaskType.WATER_CHANGE if reason == "water_change" else TaskType.CHARGE
        self.vehicle_state = VehicleState.ADD_WATER if reason == "water_change" else VehicleState.CHARGING
        self._save_order_state()
        self.erp_state = ERPState.NORMAL
        self.priority_task_phase = None
        self.priority_task_reason = None
        self.priority_exit_required = False
        Trace.log(f"[cleanRobotManage] Order sent ({reason}), order_id={order_id}")
        Module.setStatus(ScriptStatus.FINISHED)

    #重置任务状态
    def _handle_reset_clean_path(self):
            """处理重置清洁路径"""
            self._reset_boustrophedon_path()
            self.have_cancelled = False
            self.saved_exit_id = None
            Module.setStatus(ScriptStatus.FINISHED)

    
    def _reset_boustrophedon_path(self):
        """重置弓字形导航状态"""
        Navigation.resetBoustrophedonPath()
        self.pos = []
        self.boustrophedon_path_state = BoustrophedonPathState.INIT



    def _build_simple_order(self, step_locations: List[str], robot_name: str, priority: int) -> Dict[str, Any]:
        """
        构造简单运单格式
        """
        steps = []
        for location in step_locations:
            steps.append({
                "location": location,
                "rbkArgs": {}
            })

        return {
            "sceneId": config_params.scene_id,
            "expectedRobotNames": [robot_name],
            "stepFixed": True,
            "priority": priority,
            "steps": steps
        }

    def build_charge_order_json(self) -> Dict[str, Any]:
        return {
            "sceneId": config_params.scene_id,
            "priority": 60,
            "expectedRobotNames": [config_params.robot_name],
            "expectedRobotGroups": [],
            "keyLocations": [],
            "stepFixed": True,
            "steps": [{
                "location": config_params.charging_site,
                "rbkArgs": {"binTask": "WaterChange"},
                "forLoad": False,
                "forUnload": False,
                "withdrawOrderAllowed": True,
                "nextStepSameOrder": False
            }]
        }

    def build_water_order_json(self) -> Dict[str, Any]:
        return {
            "sceneId": config_params.scene_id,
            "priority": 60,
            "expectedRobotNames": [config_params.robot_name],
            "expectedRobotGroups": [],
            "keyLocations": [],
            "stepFixed": True,
            "steps": [{
                "location": config_params.charging_site,
                "rbkArgs": {"binTask": "WaterChange"},
                "forLoad": False,
                "forUnload": False,
                "withdrawOrderAllowed": True,
                "nextStepSameOrder": False
            }]
        }

    def post_to_scheduler(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        通过 HTTP POST 发送运单给调度系统

        Args:
            payload: 运单数据

        Returns:
            运单ID，失败返回None
        """
        scheduler_url = get_scheduler_url()
        Trace.log(f"[cleanRobotManage] POST {scheduler_url} -> {json.dumps(payload, ensure_ascii=False)}")
        headers = {
            'xyy-app-id': config_params.m4_app_id,
            'xyy-app-key': config_params.m4_app_key,
            'Content-Type': 'application/json'
        }
        self.last_scheduler_error = ""
        self.scheduler_retry_count = 0

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            self.scheduler_retry_count = attempt
            try:
                response = requests.post(
                    scheduler_url,
                    headers=headers,
                    json=payload,
                    timeout=5
                )

                if response.status_code == 200:
                    result = response.json()
                    order_id = result.get("orderId") or result.get("order_id") or result.get("id")
                    self.last_scheduler_error = ""
                    Trace.log(f"[cleanRobotManage] Order created successfully: {order_id} (attempt={attempt})")
                    return order_id

                self.last_scheduler_error = f"HTTP {response.status_code}: {response.text}"
                Trace.log(
                    f"[cleanRobotManage] Failed to create order "
                    f"(attempt={attempt}/{max_retries}): {self.last_scheduler_error}"
                )
            except requests.exceptions.Timeout:
                self.last_scheduler_error = "Request timeout when posting to scheduler"
                Trace.log(
                    f"[cleanRobotManage] {self.last_scheduler_error} "
                    f"(attempt={attempt}/{max_retries})"
                )
            except requests.exceptions.ConnectionError as e:
                self.last_scheduler_error = f"Connection error: {e}"
                Trace.log(
                    f"[cleanRobotManage] {self.last_scheduler_error} "
                    f"(attempt={attempt}/{max_retries})"
                )
            except Exception as e:
                self.last_scheduler_error = f"Unexpected error posting to scheduler: {e}"
                Trace.log(
                    f"[cleanRobotManage] {self.last_scheduler_error} "
                    f"(attempt={attempt}/{max_retries})"
                )

            if attempt < max_retries:
                time.sleep(0.5)

        return None

    def _cancel_current_order(self):
        """
        取消当前运单

        通过HTTP POST调用调度系统的取消运单API

        API地址由 M4 IP 和端口配置动态生成
        请求格式: {"orderId": "xxx", "reason": "xxx"}
        """
        if not self.current_order_id:
            Trace.log("[cleanRobotManage] No order to cancel")
            return

        payload = {
            "sceneId": config_params.scene_id,
            "orderId": self.current_order_id
            # "reason": "Priority task interrupt"
        }

        Trace.log(f"[cleanRobotManage] Cancelling order: {self.current_order_id}")

        # try:
        response = requests.post(
            get_scheduler_cancel_url(),
            json=payload,
            headers = {
            'xyy-app-id': config_params.m4_app_id,
            'xyy-app-key': config_params.m4_app_key,
            'Content-Type': 'application/json'},
            timeout=5
        )

        if response.status_code == 200:
            Trace.log(f"[cleanRobotManage] Order {self.current_order_id} cancelled successfully")
            self.current_order_id = None
            return True
        else:
            Trace.log(f"[cleanRobotManage] Failed to cancel order: HTTP {response.status_code}, {response.text}")
            return False
        #
        # except requests.exceptions.Timeout:
        #     Trace.log(f"[cleanRobotManage] Request timeout when cancelling order {self.current_order_id}")
        # except requests.exceptions.ConnectionError as e:
        #     Trace.log(f"[cleanRobotManage] Connection error when cancelling order: {e}")
        # except Exception as e:
        #     Trace.log(f"[cleanRobotManage] Unexpected error cancelling order: {e}")

    def _normalize_start_pos(self, position: Any) -> Optional[List[float]]:
        if not position:
            return None

        if isinstance(position, (list, tuple)) and len(position) >= 3:
            return [position[0], position[1], position[2]]

        if isinstance(position, dict):
            x = position.get("x")
            y = position.get("y")
            yaw = position.get("angle", position.get("theta"))
            if x is not None and y is not None and yaw is not None:
                return [x, y, yaw]

        Trace.log(f"[cleanRobotManage] Invalid start position: {position}")
        return None

    def _update_path_context(self, args: Dict[str, Any]):
        if "entrance" in args:
            self.current_entrance = args["entrance"]
        if "exit" in args:
            self.current_exit = args["exit"]
        if "startPos" in args:
            self.current_start_pos = self._normalize_start_pos(args["startPos"])



    def call_mech(
            self,
            operation: str,
            brush_power: Optional[int] = None,
            suck_power: Optional[int] = None,
            jet_power: Optional[int] = None,
            auto_adjust_power: Optional[int] = None,
            push_rod_length: Optional[int] = None,
    ):
        """
        调用机构控制

        Args:
            operation: 操作类型 (WashStart, WashEnd, DustStart, DustEnd, AddWater, CheckInfo)
            brush_power: 刷盘电机功率
            suck_power: 吸风电机功率
            jet_power: 喷水泵功率
            auto_adjust_power: 是否自动调节功率
            push_rod_length: 推杆长度
        """
        if brush_power is None:
            brush_power = config_params.brush_power
        if suck_power is None:
            suck_power = config_params.suck_power
        if jet_power is None:
            jet_power = config_params.jet_power
        if auto_adjust_power is None:
            auto_adjust_power = config_params.auto_adjust_power
        if push_rod_length is None:
            push_rod_length = config_params.push_rod_length

        args = {
            "operation": operation,
            "brush_power": self.mech.brush_power,
            "suck_power": self.mech.suck_power,
            "jet_power": self.mech.jet_power,
            "auto_adjust_power": auto_adjust_power,
            "push_rod_length": push_rod_length,
        }
        if self.pre_arg != args:
            Trace.log(f"[cleanRobotManage] New args: {self.pre_arg} -> {args}")
            self.pre_arg = args
            self.mech.reset_state()

        if self.mech.action_status in (ScriptStatus.NONE, ScriptStatus.RUNNING):
            return self.mech.run(args)

        return self.mech.action_status

    def get_water_levels(self) -> Tuple[float, float]:
        """从机构获取水位信息"""
        return self.mech.get_water_levels()

    # ============================================================
    #  清洁路径控制 - 使用新接口
    # ============================================================

    def run_clean_path(self):
        """
        执行弓字形清洁路径

        调用 Navigation.goBoustrophedonPath(entrance, exit, startPos, params)
        - startPos 为空时从头开始，有值时从指定位置断点续扫
        """
        if not self.current_exit:
            Trace.log("[cleanRobotManage] run_clean_path: missing path context")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            return

        # 更新区域状态

        # 构造参数
        params = {
            "maxSpeed": config_params.boustrophedon_path_max_speed,
            "maxRot": config_params.boustrophedon_path_max_rot,
            "isFreeByPass": bool(config_params.boustrophedon_path_free_bypass)
        }

        # startPos: 断点续扫位置，None表示从头开始
        start_pos = self.current_start_pos if self.current_start_pos else []

        # Trace.log(f"entrance={self.current_entrance}, exit={self.current_exit}, "
        #           f"startPos={start_pos}, params={params}")

        # 调用goBoustrophedonPath
        status_value = Navigation.goBoustrophedonPath(
            self.current_entrance,
            self.current_exit,
            start_pos,
            params
        )
        pre_state = self.boustrophedon_path_state
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)
        if pre_state != self.boustrophedon_path_state:
            Trace.log(f"[cleanRobotManage] run_clean_path：goBoustrophedonPath status changed from {pre_state} to {self.boustrophedon_path_state}")

        # 清除startPos，避免重复使用
        if self.current_start_pos:
            self.current_start_pos = None

        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath finished for area which exit {self.current_exit}")
            self._mark_clean_area_finished()
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            self.failed_clean_area_index = self.clean_area_index
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath failed for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            Navigation.resetBoustrophedonPath()

            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            Trace.log("[cleanRobotManage] goBoustrophedonPath suspended")
            return

    def run_clean_path_and_wash(self, args: Dict[str, Any]):
        """
                执行弓字形清洁路径

                调用 Navigation.goBoustrophedonPath(entrance, exit, startPos, params)
                - startPos 为空时从头开始，有值时从指定位置断点续扫
                """

        if not self.current_exit:
            Trace.log("[cleanRobotManage] run_clean_path: missing path context")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            return

        if not config_params.isTrue:
            mech_status = self.call_mech(
                "WashStart",
                brush_power=args.get("brush_power"),
                suck_power=args.get("suck_power"),
                jet_power=args.get("jet_power"),
                auto_adjust_power=args.get("auto_adjust_power"),
            )
            if mech_status != ScriptStatus.FINISHED:
                return

        # 更新区域状态

        # 构造参数
        params = {
            "maxSpeed": config_params.boustrophedon_path_max_speed,
            "maxRot": config_params.boustrophedon_path_max_rot,
            "isFreeByPass": bool(config_params.boustrophedon_path_free_bypass)
        }

        # startPos: 断点续扫位置，None表示从头开始
        start_pos = self.current_start_pos if self.current_start_pos else []


        # 调用goBoustrophedonPath
        status_value = Navigation.goBoustrophedonPath(
            self.current_entrance,
            self.current_exit,
            start_pos,
            params
        )
        pre_state = self.boustrophedon_path_state
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)
        if pre_state != self.boustrophedon_path_state:
            Trace.log(f"[cleanRobotManage] run_clean_path_and_wash：goBoustrophedonPath status changed from {pre_state} to {self.boustrophedon_path_state}")
    
        # 清除startPos，避免重复使用
        if self.current_start_pos:
            self.current_start_pos = None

        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.STOP_WATER:
            if not config_params.isTrue:
                self.mech.wash_stop_water()
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath finished for area  which entr {self.current_entrance}")
            self._mark_clean_area_finished()
            if not config_params.isTrue:
                self.mech.wash_stop_water()
            self.clean_close_pending = True
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            self.failed_clean_area_index = self.clean_area_index
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath failed for area  which entr {self.current_entrance}")
            self.erp_state = ERPState.ERROR
            if not config_params.isTrue:
                self.mech.wash_stop_water()
            self.clean_close_pending = True
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            if not config_params.isTrue:
                self.call_mech("WashEnd")
            Trace.log("[cleanRobotManage] goBoustrophedonPath suspended")
            return

    def run_cross_path(self):
        """
                执行横穿清洁区域路径

                调用 Navigation.goCrossArea(entrance, exit, params)
        """


        if not self.current_exit:
            Trace.log("[cleanRobotManage] run_cross_path: missing path context")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            return

        # 更新区域状态

        # 构造参数
        params = {
            "maxSpeed": config_params.boustrophedon_path_max_speed,
            "maxRot": config_params.boustrophedon_path_max_rot,
            "isFreeByPass": bool(config_params.boustrophedon_path_free_bypass)
        }


        # 调用goCrossArea
        status_value = Navigation.goCrossArea(
            self.current_entrance,
            self.current_exit,
            params
        )
        pre_state = self.boustrophedon_path_state
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)
        if pre_state != self.boustrophedon_path_state:
            Trace.log(f"[cleanRobotManage] run_cross_path：goCrossArea status changed from {pre_state} to {self.boustrophedon_path_state}")
        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goCrossArea finished for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goCrossArea failed for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            Navigation.resetBoustrophedonPath()

            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            Trace.log("[cleanRobotManage] goCrossArea suspended")
            return

    def run_exit_path(self, report_status: bool = True):
        """
                取消弓字形路径后走到出口

                调用 Navigation.goExitPoint(entrance, exit, params)
        """


        if not self.current_entrance or not self.current_exit:
            Trace.log("[cleanRobotManage] run_exit_path: missing path context")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.boustrophedon_path_state = BoustrophedonPathState.FAILED
            self.erp_state = ERPState.ERROR
            Module.setStatus(ScriptStatus.FAILED)
            return

        # 更新区域状态

        # 构造参数
        params = {
            "maxSpeed": config_params.boustrophedon_path_max_speed,
            "maxRot": config_params.boustrophedon_path_max_rot,
            "isFreeByPass": bool(config_params.boustrophedon_path_free_bypass)
        }


        # 调用goExitPoint
        status_value = Navigation.goExitPoint(
            self.current_entrance,
            self.current_exit,
            params
        )
        pre_state = self.boustrophedon_path_state
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)
        if pre_state != self.boustrophedon_path_state:
            Trace.log(f"[cleanRobotManage] run_exit_path：goExitPoint status changed from {pre_state} to {self.boustrophedon_path_state}")
        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goExitPoint finished for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            self.have_cancelled = False
            if report_status:
                Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goExitPoint failed for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            return

    def run_remaining_path(self):
        """
                执行清洁区域剩余路径

                调用 Navigation.goCrossArea(entrance, exit, params)
        """


        if not self.current_exit:
            Trace.log("[cleanRobotManage] run_remaining_path: missing path context")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            return

        # 更新区域状态

        # 构造参数
        params = {
            "maxSpeed": config_params.boustrophedon_path_max_speed,
            "maxRot": config_params.boustrophedon_path_max_rot,
            "isFreeByPass": bool(config_params.boustrophedon_path_free_bypass)
        }


        # 调用goRemainingPath
        status_value = Navigation.goRemainingPath(
            self.current_entrance,
            self.current_exit,
            params
        )
        pre_state = self.boustrophedon_path_state
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)
        if pre_state != self.boustrophedon_path_state:
            Trace.log(f"[cleanRobotManage] run_remaining_path：goRemainingPath status changed from {pre_state} to {self.boustrophedon_path_state}")
        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goRemainingPath finished for area which exit {self.current_exit}")
            self._mark_clean_area_finished()
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            self.saved_exit_id = ""
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goRemainingPath failed for area which exit {self.current_exit}")
            self.failed_clean_area_index = self.clean_area_index
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            Navigation.resetBoustrophedonPath()

            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            Trace.log("[cleanRobotManage] goRemainingPath suspended")
            return

    def _prepare_next_step(self):
        """准备下一步（简化版：路径上下文由外部传入）"""
        if not self.current_task:
            return
        # 路径上下文（ current_entrance, current_exit）
        # 现在由外部 args 传入，不再基于 CA 前缀自动判断
        self.vehicle_state = VehicleState.NAVIGATING


    def check_scheduled_clean_task(self):
        """
        检查是否到达每日定时清洁任务的执行时间

        逻辑：
        - 每天只触发一次
        - 当前时间达到配置的 scheduled_clean_hour:scheduled_clean_minute 时触发
        - 只有在 IDLE 状态且没有正在执行的任务时才触发
        - 使用日期字符串判断是否今天已执行过
        """
        # 检查是否启用
        if not config_params.scheduled_clean_enabled:
            return

        if not config_params.scheduled_clean_config_valid:
            return

        # 检查是否有配置的站点
        if not config_params.scheduled_clean_routes:
            Trace.log(f"[cleanRobotManage] haven't set up the scheduled clean locations, won't send clean task")
            return

        # 获取当前时间
        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_hour = now.hour
        current_minute = now.minute

        # 检查是否跨天，重置触发标记
        if self.last_scheduled_clean_date != current_date:
            self.scheduled_clean_triggered_today = False
            self.last_scheduled_clean_date = current_date

        if self.restored_order_sent:
            self.scheduled_clean_triggered_today = True
            self.restored_order_sent = False
            Trace.log("[cleanRobotManage] Restored order already sent; skip scheduled clean dispatch")
            return

        # 如果今天已经触发过，跳过
        if self.scheduled_clean_triggered_today:
            return

        debug_once = config_params.isDebug and not config_params.isTrue
        if debug_once and self.debug_order_attempted:
            return

        # 检查是否到达触发时间
        target_hour = config_params.scheduled_clean_hour
        target_minute = config_params.scheduled_clean_minute

        run_immediately = config_params.isTrue or debug_once
        if (current_hour == target_hour and current_minute >= target_minute) or run_immediately:
            # 检查是否可以发送任务（空闲状态）
            if not self.can_dispatch_to_m4():
                Trace.log(
                    f"[cleanRobotManage] Scheduled clean time reached but cannot dispatch (erp_state={self.erp_state.name})")
                return

            # 检查是否有正在执行的任务
            if self.current_task is not None:
                self._has_active_script_order()
            if self.current_task is not None:
                Trace.log("[cleanRobotManage] Scheduled clean time reached but task is running")
                return

            # isDebug 只立即尝试一次；即使本次发单失败，后续循环也不重复发送。
            if debug_once:
                self.debug_order_attempted = True

            # 触发定时清洁任务
            routes = [list(route) for route in config_params.scheduled_clean_routes]
            if config_params.isTrue:
                self.simulation_clean_area_count = 0
                self.simulation_charge_started_at = None
                self.simulation_charge_arrived_at = None
            self.scheduled_clean_pending_routes = routes[1:]
            if self._send_scheduled_clean_task(routes[0]):
                self.scheduled_clean_triggered_today = True
                Trace.log(f"[cleanRobotManage] Scheduled clean task triggered at {current_hour:02d}:{current_minute:02d}")
            else:
                self.scheduled_clean_pending_routes = []
                Trace.log(f"[cleanRobotManage] Failed to trigger scheduled clean task at {current_hour:02d}:{current_minute:02d}")

    def _send_scheduled_clean_task(self, step_locations: List[str]):
        """
        发送每日定时清洁任务
        """
        Trace.log(f"[cleanRobotManage] Sending scheduled clean task: {step_locations}")

        # 构造任务数据
        task = {
            "step_locations": step_locations,
            "robot_name": config_params.robot_name,
            "priority": 50,  # 定时任务使用中等优先级
            "task_id": f"scheduled_clean_{int(time.time())}"
        }


        # 初始化区域状态

        # 构造并发送运单
        payload = self._build_simple_order(
            step_locations=step_locations,
            robot_name=config_params.robot_name,
            priority=50
        )
        order_id = self.post_to_scheduler(payload)
        if order_id:
            self.current_task = task
            self.current_task_type = TaskType.CLEAN
            self.current_order_id = order_id
            self._reset_clean_area_progress(step_locations)
            self._save_order_state()
            self.scheduled_clean_order_id = order_id
            self.erp_state = ERPState.NORMAL
            Trace.log(f"[cleanRobotManage] Scheduled clean order sent: {order_id}")
            return True
        else:
            Trace.log(f"[cleanRobotManage] Failed to send scheduled clean order")
            Navigation.setTaskError("HTTP-M4-ERROR",f"send scheduled clean order failed, please check: 1. IP and port are correct. 2. M4 server is running. 3. Network connection is stable. 4.token is correct.")
            return False

    def check_scheduled_clean_progress(self):
        """当前分段完成后，顺序发送下一段定时清洁路线。"""
        order_id = self.scheduled_clean_order_id
        if (not order_id or self.clean_checkpoint.has_checkpoint() or
                self.current_task_type in (TaskType.CHARGE, TaskType.WATER_CHANGE)):
            return

        detail = self._query_order_detail(order_id)
        if not detail:
            return
        status = detail.get("status")
        if isinstance(status, dict):
            status = status.get("name") or status.get("value")
        status = str(status).split(".")[-1].lower()
        if detail.get("fault") or status in ("cancelled", "canceled"):
            try:
                fault_reson = detail.get("faultReason")
            except:
                fault_reson = None
            Trace.log(f"[cleanRobotManage] Scheduled clean batch stopped: order_id={order_id}, status={status}, fault_reason={fault_reson}")
            Navigation.setTaskError("SCHEDULED-CLEAN-FAILED", "Scheduled clean route failed or was cancelled")
            self.scheduled_clean_pending_routes = []
            self.scheduled_clean_order_id = None
            self.erp_state = ERPState.ERROR
            return
        if status != "done":
            return

        if self.current_order_id == order_id:
            self.current_order_id = None
            self.current_task = None
            self.current_task_type = TaskType.NONE
            self.vehicle_state = VehicleState.IDLE
        self.scheduled_clean_order_id = None

        if not self.scheduled_clean_pending_routes:
            Trace.log("[cleanRobotManage] All scheduled clean routes completed")
            return

        next_route = self.scheduled_clean_pending_routes.pop(0)
        if not self._send_scheduled_clean_task(next_route):
            self.scheduled_clean_pending_routes = []
            self.erp_state = ERPState.ERROR

    # ============================================================
    #  上报信息
    # ============================================================

    def update_report_info(self):
        soc = Battery.getPercentage()
        current_task_step = self._get_current_task_step()

        self.report_info = {
            # 状态机
            "erp_state": self.erp_state.name,
            # mech_state 已删除：机构状态由 CleanRobotMech.report_info 上报
            "vehicle_state": self.vehicle_state.name,
            "boustrophedon_path_state": self.boustrophedon_path_state.name,
            "current_task_type": self.current_task_type.name,

            # 急停
            "emc_triggered": self.emc_triggered,

            # 电池和水位
            "battery": soc,
            "clean_water_level": self.clean_water_level,
            "waste_water_level": self.waste_water_level,

            # 自动任务标记
            "auto_charge_sent": self.auto_charge_sent,
            "auto_water_sent": self.auto_water_sent,

            # 当前路径
            "current_entrance": self.current_entrance,
            "current_exit": self.current_exit,
            "current_start_pos": self.current_start_pos,

            # 当前导航目标点
            "current_nav_target": self.current_nav_target,


            # 区域状态

            # 当前任务
            "current_task_id": self.current_task.get("task_id", "") if self.current_task else "",
            "current_task_step": current_task_step,
            "current_task_total_steps": len(self.current_task.get("step_locations", [])) if self.current_task else 0,
            "current_task_locations": self.current_task.get("step_locations", []) if self.current_task else [],

            # 断点信息
            "has_checkpoint": self.clean_checkpoint.has_checkpoint(),
            "checkpoint_reason": self.clean_checkpoint.interrupt_reason,
            "checkpoint_location": self.clean_checkpoint.location,
            # "checkpoint_position": self.clean_checkpoint.robot_position,
            "checkpoint_nav_target": self.clean_checkpoint.nav_target,
            "checkpoint_nav_target_index": self.clean_checkpoint.nav_target_index,

            # 运单
            "current_order_id": self.current_order_id,
            "last_scheduler_error": self.last_scheduler_error,
            "scheduler_retry_count": self.scheduler_retry_count,

            # 每日定时清洁任务
            "scheduled_clean_enabled": config_params.scheduled_clean_enabled,
            "scheduled_clean_time": f"{config_params.scheduled_clean_hour:02d}:{config_params.scheduled_clean_minute:02d}",
            "scheduled_clean_triggered_today": self.scheduled_clean_triggered_today,
            "last_scheduled_clean_date": self.last_scheduled_clean_date,

            # 时间
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

# ============================================================
#  主函数
# ============================================================

def main():
    """
    主函数

    SendOrders 操作的 JSON 示例：

    1. 发送清洁运单（导航到多个站点）:
    {
        "operation": "SendOrders",
        "order_type": "clean",
        "step_locations": ["LM29", "LM55", "CA1", "LM60"],
        "robot_name": "SVJ-01",
        "priority": 90
    }

    2. 发送充电运单:
    {
        "operation": "SendOrders",
        "order_type": "charge",
        "robot_name": "SVJ-01",
        "priority": 90
    }

    3. 发送换水运单:
    {
        "operation": "SendOrders",
        "order_type": "water",
        "robot_name": "SVJ-01",
        "priority": 90
    }

    发送给M4调度系统的实际格式:
    {
        "expectedRobotNames": ["SVJ-01"],
        "stepFixed": true,
        "priority": 90,
        "steps": [
            {"location": "LM29", "rbkArgs": {}},
            {"location": "LM55", "rbkArgs": {}}
        ]
    }

    SendContinueOrders 操作的 JSON 示例：

    1. 续传运单（自动计算剩余站点）:
    {
        "operation": "SendContinueOrders",
        "robot_name": "SVJ-01",
        "priority": 90
    }

    说明：
    - SendOrders 会保存原始站点列表到 original_step_locations 和 remaining_step_locations
    - 当机器人从 AP2 前往 AP3 时 (source_name="AP2", target_name="AP3")
      remaining_step_locations 会更新为 ["AP2", "AP3", "AP4", "AP5"]
    - SendContinueOrders 直接使用 remaining_step_locations 发送运单
    - 这样中断后恢复时，不会重复走已经经过的站点
    """

    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    validator = ParamValidator(InputParams.builder.toDict())
    mgr = CleanRobotManage()
    mgr.restore_order_from_db()
    emc_manager = EmcManager(mgr)
    isFirstRun= True
    pre_water_level = -1
    pre_waste_water_level = -1
    pre_soc=-1
    while True:
        status = Module.getStatus()

        # ============================================================
        # 每日定时清洁任务检查（每天8:00触发）
        # ============================================================
        mgr.check_scheduled_clean_task()
        mgr.check_scheduled_clean_progress()
        # 获取当前时间
        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_hour = now.hour
        current_minute = now.minute

        # ============================================================
        # 2. 机构周期性运行（更新液位等）
        # ============================================================
        # 说明：周期性更新机构状态、液位数据，并同步到RBK
        if config_params.isTrue:
            pass
        else:
            mgr.period_run()

        # ============================================================
        # 3. 同步水位信息到管理类
        # ============================================================
        mgr.clean_water_level, mgr.waste_water_level = mgr.get_water_levels()
        if config_params.isTrue:
            pass
        else:
            clean_water_level_int = round(mgr.clean_water_level)
            waste_water_level_int = round(mgr.waste_water_level)
            if pre_water_level != clean_water_level_int or pre_waste_water_level != waste_water_level_int:
                Trace.log(f"[cleanRobotManage] Water levels updated: clean:{pre_water_level} -> {clean_water_level_int}, waste:{pre_waste_water_level} -> {waste_water_level_int}")
                pre_water_level = clean_water_level_int
                pre_waste_water_level = waste_water_level_int
            # ============================================================
            # 4. 水位监控 - 污水满 或 清水不足检测
            # ============================================================
            # 说明：clean_water_level == -1 表示传感器未初始化，不处理
            waste_full = mgr.waste_water_level > config_params.max_waste_water_level
            clean_low = mgr.clean_water_level < config_params.min_clean_water_level and mgr.clean_water_level != -1
            if (waste_full or clean_low) and mgr.current_task_type == TaskType.CLEAN and not mgr.auto_water_sent and not mgr.priority_task_phase:
                water_reason = "waste water full" if waste_full else "clean water low"
                Trace.log(f"[cleanRobotManage] Water change triggered ({water_reason}), interrupting for water change")
                mgr._handle_cancel_clean_path("water_change")

        # ============================================================
        # 6. 电量监控（自动充电）
        # ============================================================
        # 说明：check_battery() 内部会：
        #   - 检测电量是否低于 config_params.low_battery_soc (20%)
        #   - 如果低于阈值且正在执行清洁任务：
        #     1. 调用 _interrupt_clean_for_priority_task("charge") 中断清洁
        #     2. 发送充电运单
        #   - 检测电量是否高于 config_params.high_battery_soc (90%)
        #   - 如果高于阈值，重置 auto_charge_sent 标记
        soc = Battery.getPercentage()
        if config_params.isTrue:
            pass
        else:
            if soc < 0:
                return
            soc_percent = round(soc * 100)
            if pre_soc != soc_percent:
                Trace.log(f"[cleanRobotManage] Battery updated: {pre_soc}% -> {soc_percent}%")
                pre_soc = soc_percent
            if soc <= config_params.low_battery_soc and not mgr.auto_charge_sent and not mgr.priority_task_phase:
                Trace.log(f"[cleanRobotManage] Low battery ({soc}), interrupting for charge")
                mgr._handle_cancel_clean_path("charge")
            if soc >= config_params.high_battery_soc and not mgr.clean_checkpoint.has_checkpoint():
                mgr.auto_charge_sent = False

        # 关闭机构、驶出清洁区域后，再发送充电/换水运单
        mgr._continue_priority_task()
        # ============================================================
        # 7. 急停状态检测和处理
        # ============================================================
        # 说明：检测急停按钮状态，处理急停触发和恢复
        #
        # 急停触发时 (_on_emc_triggered) 会：
        #   1. 保存当前状态（车辆状态、任务类型）
        #   2. 取消当前运单 (调用 _cancel_current_order())
        #   3. 发送 CancelCleanPath 操作（如果在清洁中）
        #   4. 关闭清洁机构 (调用 call_mech("WashEnd"))
        #   5. 重置车辆状态为 IDLE
        #
        # 急停恢复时 (_on_emc_recovered) 会：
        #   - 根据急停前的状态恢复相应操作
        emc_status = Controller.getEmc()
        emc_manager._handle_emc(emc_status)

        # ============================================================
        # 8. 检查是否可以恢复清洁任务（充电/换水完成后）
        # ============================================================
        # 说明：_check_and_resume_clean_task() 会：
        #   1. 检查是否有保存的断点 (clean_checkpoint.has_checkpoint())
        #   2. 检查 ERP 状态是否为 IDLE（当前无任务执行）
        #   3. 根据中断原因检查恢复条件：
        #      - charge: 电量 >= config_params.high_battery_soc (90%)
        #      - water_change: 清水满 且 污水空
        #   4. 如果满足条件，调用 _resume_clean_task_from_checkpoint() 恢复任务
        #
        # 恢复任务时会：
        #   - 计算恢复起点（从目标点的前一个站点开始）
        #   - 构造恢复任务（剩余站点列表）
        #   - 发送恢复运单到 M4 调度系统
        #   - 清除断点信息
        mgr._check_and_resume_clean_task()

        # ============================================================
        # 10. 更新车辆状态机
        # ============================================================
        # 说明：根据当前任务类型和弓字形路径状态更新车辆状态
        #   - NONE -> IDLE
        #   - CHARGE -> CHARGING
        #   - WATER_CHANGE -> ADD_WATER
        #   - CLEAN + 弓字形路径 RUNNING -> CLEANING
        #   - CLEAN + 其他路径状态 -> NAVIGATING
        mgr._vehicle_state_update()

        if status in (ScriptStatus.RUNNING, ScriptStatus.NONE):
            input_params = Module.getTaskArgs()
            validated_params = {}
            if input_params:
                try:
                    # 验证参数
                    validated_params = param_loader.loadInput(input_params)
                    if isFirstRun:
                        isFirstRun = False
                        Trace.log(f"[cleanRobotManage] First run, Parameter validation passed，validated_params={validated_params}")
                        mgr.run(validated_params,True)
                    else:
                        mgr.run(validated_params,False)
                except ValueError as e:
                    Trace.log(f"[cleanRobotManage] Parameter validation failed,Current parameters={input_params},error: {e}")
                    Navigation.setTaskError("args error",f"input args error:{e}")
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            isFirstRun = True
            mgr.reset_state()

        # ============================================================
        # 12. 更新并上报状态信息
        # ============================================================
        # 说明：
        # - update_report_info() 收集所有状态信息到 report_info 字典
        # - Module.reportInfo() 将状态信息上报给系统
        # - 上报的信息包括：状态机状态、电池水位、任务进度、断点信息等
        mgr.update_report_info()
        # time.sleep(0.1)
        Module.reportInfo(mgr.report_info)
        time.sleep(0.1)
        # move_task = Navigation.moveTask()
        # print(move_task.get("sourceName", None),move_task.get("targetName", None))


if __name__ == "__main__":

    main()
