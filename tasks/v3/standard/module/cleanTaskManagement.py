# -*- coding: utf-8 -*-
# @Date : 2025/12/01
# @Author : zeng
# @File : cleanRobotManage.py
#
# 说明：
# - 管理清洁任务：接车载屏/单车平台任务、监控电池和水位，并给调度系统发送 HTTP 运单。
# - 包含多个状态机：ERP状态机、机构状态机、车辆状态机、GongPath状态机
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
# - goBoustrophedonPath(area, entrance, exit, startPos, params): 执行弓字形清扫
# - cancelBoustrophedonPath(): 取消清扫，返回当前位置
# - resetGongPath(): 重置清扫状态
#
"""
####BEGIN DEFAULT ARGS####
{}
####END DEFAULT ARGS####
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple
from enum import IntEnum, auto
import requests

from syspy import Module, ScriptStatus, Trace, Navigation, Abnormal, Battery, Controller

from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ScriptParam

from syspy.lib.robot_param import RobotParam

from cleanRobotMech_1213 import CleanRobot

# 本脚本自己的 param loader
param_loader = ScriptParam(__file__)

# 调度/任务相关常量（如需可改成 Param 配置）
SCENE_ID = "69362A244E80897DC945DEAA"
ROBOT_NAME = "SVJ-01"
LOW_BATTERY_SOC = 20.0
HIGH_BATTERY_SOC = 90.0
HMI_PERIOD = 1.0  # /s 车载屏轮询周期
ROBOSHOP_PERIOD = 1.0  # /s 单车平台轮询周期

# 调度 HTTP 地址
SCHEDULER_URL = "http://192.168.8.191:5800/api/fleet/orders/create"
SCHEDULER_CANCEL_URL = "http://192.168.8.191:5800/api/fleet/orders/cancel"


# ============================================================
#  状态机枚举定义
# ============================================================

class ERPState(IntEnum):
    """ERP状态机 - 控制何时可以发单给M4调度系统"""
    IDLE = 0  # 空闲，可以接收新任务并发单
    TASK_RUNNING = 1  # 任务执行中
    TASK_PAUSED = 2  # 任务暂停（充电/加水等）
    TASK_COMPLETED = 3  # 任务完成，准备切换到IDLE
    ERROR = 4  # 错误状态，需要人工干预


class MechState(IntEnum):
    """机构状态机 - 清洁机构的工作状态"""
    IDLE = 0  # 无任务，机构空闲
    CHARGE_WATER = 1  # 充电加水中
    CLEAN_STARTING = 2  # 清洁启动中（机构正在展开）
    CLEANING = 3  # 清洁中（机构已全部工作）
    CLEAN_STOPPING = 4  # 清洁关闭中（机构正在收起）


class VehicleState(IntEnum):
    """车辆状态机 - 机器人本身的状态"""
    IDLE = 0  # 无任务
    ADD_WATER = 1  # 加水/排污中
    CHARGING = 2  # 充电中
    CLEANING = 3  # 清洁中（在清洁区域内执行清洁）
    NAVIGATING = 4  # 无清洁导航中（在清洁区和清洁区之间的过程）


class BoustrophedonPathState(IntEnum):
    """GongPath状态机 - 走工艺路径的状态"""
    INIT = 0  # 初始化
    RUNNING = 1  # 路径运行中
    FINISHED = 3  # 路径完成
    FAILED = 4  # 路径失败
    SUSPENDED = 5  # 路径暂停


class TaskType(IntEnum):
    """任务类型枚举"""
    NONE = 0  # 无任务
    CLEAN = 1  # 清洁任务
    CHARGE = 2  # 充电任务
    WATER_CHANGE = 3  # 换水任务


class CleanAreaStatus(IntEnum):
    """清洁区域状态枚举"""
    NOT_STARTED = 0  # 未开始
    IN_PROGRESS = 1  # 进行中
    COMPLETED = 2  # 已完成
    INTERRUPTED = 3  # 已中断（待恢复）


# ============================================================
#  清洁任务断点数据结构
# ============================================================

class CleanTaskCheckpoint:
    """
    清洁任务断点数据结构
    用于在充电/换水中断时保存清洁任务状态，以便后续恢复

    关键变化：使用机器人坐标位置（startPos）而非进度百分比来实现断点续扫
    """

    def __init__(self):
        # 原始任务数据
        self.task_data: Optional[Dict[str, Any]] = None

        # 断点位置信息
        self.step_index: int = 0  # 中断时的步骤索引
        self.location: Optional[str] = None  # 中断时的位置（站点或清洁区域）
        self.is_in_clean_area: bool = False  # 是否在清洁区域内中断

        # 清洁区域内的位置（用于断点续扫）
        self.robot_position: Optional[List[float]] = None  # [x, y, yaw] 机器人坐标
        self.area_name: Optional[str] = None  # 清洁区域名称
        self.entrance: Optional[str] = None  # 入口站点
        self.exit_station: Optional[str] = None  # 出口站点

        # 各清洁区域的完成状态
        self.area_status: Dict[str, CleanAreaStatus] = {}

        # 中断原因
        self.interrupt_reason: Optional[str] = None  # "charge" 或 "water_change"
        self.interrupt_time: float = 0.0  # 中断时间戳

        # 运单ID（用于取消）
        self.order_id: Optional[str] = None

    def save_checkpoint(
            self,
            task_data: Dict[str, Any],
            step_index: int,
            location: str,
            is_in_clean_area: bool,
            robot_position: Optional[List[float]] = None,
            area_name: Optional[str] = None,
            entrance: Optional[str] = None,
            exit_station: Optional[str] = None,
            area_status: Optional[Dict[str, CleanAreaStatus]] = None,
            interrupt_reason: str = "",
            order_id: Optional[str] = None
    ):
        """保存断点信息"""
        self.task_data = task_data.copy() if task_data else None
        self.step_index = step_index
        self.location = location
        self.is_in_clean_area = is_in_clean_area
        self.robot_position = robot_position.copy() if robot_position else None
        self.area_name = area_name
        self.entrance = entrance
        self.exit_station = exit_station
        self.area_status = area_status.copy() if area_status else {}
        self.interrupt_reason = interrupt_reason
        self.interrupt_time = time.time()
        self.order_id = order_id

        Trace.log(f"[CleanTaskCheckpoint] Saved: location={location}, "
                  f"step_index={step_index}, is_in_clean_area={is_in_clean_area}, "
                  f"robot_position={robot_position}, reason={interrupt_reason}")

    def has_checkpoint(self) -> bool:
        """检查是否有保存的断点"""
        return self.task_data is not None

    def clear(self):
        """清除断点信息"""
        self.task_data = None
        self.step_index = 0
        self.location = None
        self.is_in_clean_area = False
        self.robot_position = None
        self.area_name = None
        self.entrance = None
        self.exit_station = None
        self.area_status = {}
        self.interrupt_reason = None
        self.interrupt_time = 0.0
        self.order_id = None
        Trace.log("[CleanTaskCheckpoint] Cleared")

    def get_resume_info(self) -> Dict[str, Any]:
        """
        获取用于恢复的信息

        Returns:
            包含恢复所需信息的字典
        """
        return {
            "task_data": self.task_data,
            "step_index": self.step_index,
            "is_in_clean_area": self.is_in_clean_area,
            "robot_position": self.robot_position,
            "area_name": self.area_name,
            "entrance": self.entrance,
            "exit_station": self.exit_station,
            "area_status": self.area_status,
        }


# ============================================================
#  配置参数管理
# ============================================================

class ConfigParams:
    """生成和定义配置参数"""
    config: Dict[str, Any] = {}

    def __init__(self):
        self.build_and_load_config()

    @classmethod
    def build_and_load_config(cls):
        """构建并加载配置参数"""
        _ = RobotParam.getDevice("Model-000", "moduleType")
        builder = param_loader.builderConfig()

        with builder.GROUPS():
            with builder.GROUP(
                    key="basicConfig",
                    name="Motor Configuration",
                    desc="Motor related configuration parameters"
            ):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(key="timeout", name="timeout",
                                       desc="脚本运行超时时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(120.0, min_value=0.000, max_value=999)
                        builder.UNIT("s")
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="min_clean_water_level", name="min_clean_water_level",
                                       desc="清水液位最小值，达到此值机器人停止工作去加水"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="max_clean_water_level", name="max_clean_water_level",
                                       desc="清水液位最大值，达到此值机器人停止加水"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(95.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="min_waste_water_level", name="min_waste_water_level",
                                       desc="污水液位最小值，达到此值机器人停止排污"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="max_waste_water_level", name="max_waste_water_level",
                                       desc="污水液位最大值，达到此值机器人停止工作去排污"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(90.0)
                        builder.SINGLESTEP(0.001)

                    with builder.CHILD(key="add_water_do", name="add_water_do",
                                       desc="加水DO"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(4)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="brush_power", name="brush_power",
                                       desc="刷盘电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(67)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="suck_power", name="suck_power",
                                       desc="吸风电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(50)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="jet_power", name="jet_power",
                                       desc="喷水泵电机默认功率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(20)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="auto_adjust_power", name="auto_adjust_power",
                                       desc="是否启动电机功率自动调节模式, 1: 启动， 0: 不启动"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1)
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="add_water_delay_time", name="add_water_delay_time",
                                       desc="加水延时关闭时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.SINGLESTEP(1.0)

                    with builder.CHILD(key="close_jet_delay_time", name="close_jet_delay_time",
                                       desc="关闭喷水电机后延时停止清洁工作的时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.SINGLESTEP(1.0)

                    with builder.CHILD(key="high_mode_x_speed", name="high_mode_x_speed",
                                       desc="x速度大于该值时, 清洁机构以高功率工作"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.8)
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="std_mode_x_speed", name="std_mode_x_speed",
                                       desc="x速度大于该值时, 清洁机构以标准功率工作"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.4)
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="stop_x_speed", name="stop_x_speed",
                                       desc="x速度小于该值时, 清洁机构停止工作"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.05)
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="gong_path_max_speed", name="gong_path_max_speed",
                                       desc="弓字形路径最大直线速度"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="gong_path_max_rot", name="gong_path_max_rot",
                                       desc="弓字形路径最大旋转速度"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5)
                        builder.UNIT("rad/s")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="gong_path_free_bypass", name="gong_path_free_bypass",
                                       desc="弓字形路径是否启用绕障"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(0)  # 默认不启用
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="roboshop_task_interval", name="roboshop_task_interval",
                                       desc="单车平台定时清洁任务执行间隔时间"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(5.0)
                        builder.UNIT("h")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="roboshop_clean_areas", name="roboshop_clean_areas",
                                       desc="单车平台定时清洁任务的清洁区域路径"):
                        builder.TYPE(ParamType.ARRAY)
                        builder.DEFAULTVALUE(["LM1", "AP2", "CA3", "AP4", "AP5", "CA6", "AP7"])

        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        Trace.log("Reloading cleanRobotManage config parameters")
        cls.config = param_loader.loadConfig()

        cls.timeout = cls.config.get("timeout")
        cls.min_clean_water_level = cls.config.get("min_clean_water_level")
        cls.max_clean_water_level = cls.config.get("max_clean_water_level")
        cls.min_waste_water_level = cls.config.get("min_waste_water_level")
        cls.max_waste_water_level = cls.config.get("max_waste_water_level")
        cls.add_water_do = cls.config.get("add_water_do")
        cls.brush_power = cls.config.get("brush_power")
        cls.suck_power = cls.config.get("suck_power")
        cls.jet_power = cls.config.get("jet_power")
        cls.auto_adjust_power = cls.config.get("auto_adjust_power")
        cls.add_water_delay_time = cls.config.get("add_water_delay_time")
        cls.close_jet_delay_time = cls.config.get("close_jet_delay_time")
        cls.high_mode_x_speed = cls.config.get("high_mode_x_speed")
        cls.std_mode_x_speed = cls.config.get("std_mode_x_speed")
        cls.stop_x_speed = cls.config.get("stop_x_speed")
        cls.gong_path_max_speed = cls.config.get("gong_path_max_speed", 1.0)
        cls.gong_path_max_rot = cls.config.get("gong_path_max_rot", 0.5)
        cls.gong_path_free_bypass = cls.config.get("gong_path_free_bypass", 0)
        cls.roboshop_task_interval = cls.config.get("roboshop_task_interval")
        cls.roboshop_clean_areas = cls.config.get("roboshop_clean_areas")

        Trace.log(f"Updated cleanRobotManage config: {cls.config}")


# 创建全局配置管理器实例
config_params = ConfigParams()


def script_config_callback():
    Trace.log("Reloading script config parameters for cleanRobotManage")
    config_params.reload_config()


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

    builder.save_to_file()


# ============================================================
#  清洁任务数据结构
# ============================================================

class CleanTaskData:
    """清洁任务数据结构"""

    def __init__(self, task_dict: Dict[str, Any]):
        self.raw_data = task_dict

        self.step_locations: List[str] = task_dict.get("step_locations", [])
        self.robot_name: str = task_dict.get("robot_name", ROBOT_NAME)
        self.priority: int = task_dict.get("priority", 50)
        self.trigger_ts: float = task_dict.get("trigger_ts", time.time())
        self.task_id: str = task_dict.get("task_id", "")

        self.current_step_index: int = 0
        self.clean_areas: List[str] = []
        self.normal_stations: List[str] = []

        # 恢复相关（从断点恢复时使用）
        self.resume_position: Optional[List[float]] = task_dict.get("resume_position")
        self.resume_area: Optional[str] = task_dict.get("resume_area")
        self.resume_entrance: Optional[str] = task_dict.get("resume_entrance")
        self.resume_exit: Optional[str] = task_dict.get("resume_exit")

        self._parse_locations()

    def _parse_locations(self):
        """解析站点列表，区分清洁区域和普通站点"""
        for loc in self.step_locations:
            if loc.startswith("CA"):
                self.clean_areas.append(loc)
            else:
                self.normal_stations.append(loc)

    def get_current_location(self) -> Optional[str]:
        """获取当前执行的站点"""
        if self.current_step_index < len(self.step_locations):
            return self.step_locations[self.current_step_index]
        return None

    def is_current_clean_area(self) -> bool:
        """判断当前站点是否是清洁区域"""
        current = self.get_current_location()
        return current is not None and current.startswith("CA")

    def advance_to_next_step(self) -> bool:
        """前进到下一个站点，返回是否还有后续站点"""
        self.current_step_index += 1
        return self.current_step_index < len(self.step_locations)

    def is_completed(self) -> bool:
        """判断任务是否完成"""
        return self.current_step_index >= len(self.step_locations)

    def get_entry_exit_for_area(self, area: str) -> Tuple[Optional[str], Optional[str]]:
        """获取清洁区域的入口和出口站点"""
        try:
            idx = self.step_locations.index(area)
            entry = self.step_locations[idx - 1] if idx > 0 else None
            exit_station = self.step_locations[idx + 1] if idx < len(self.step_locations) - 1 else None
            return entry, exit_station
        except ValueError:
            return None, None


# ============================================================
#  主管理类
# ============================================================

class CleanRobotManage:

    def __init__(self):
        # ========== 状态机 ==========
        self.erp_state = ERPState.IDLE
        self.mech_state = MechState.IDLE
        self.vehicle_state = VehicleState.IDLE
        self.gong_path_state = BoustrophedonPathState.INIT

        self.current_task_type = TaskType.NONE

        # ========== 机构脚本实例 ==========
        self.clean_robot = CleanRobot()  # 创建清洁机构控制实例

        # ========== 任务缓存 ==========
        self.hmi_immediate: List[Dict[str, Any]] = []
        self.hmi_schedule: List[Dict[str, Any]] = []
        self.last_hmi_pull = 0.0

        self.roboshop_schedule: List[Dict[str, Any]] = []
        self.last_roboshop_pull = 0.0
        self.last_roboshop_task_time = 0.0

        self.current_task: Optional[CleanTaskData] = None
        self.current_order_id: Optional[str] = None

        # ========== 自动任务标记 ==========
        self.auto_charge_sent = False
        self.auto_water_sent = False

        # ========== 水位信息 ==========
        self.clean_water_level: Optional[float] = None
        self.waste_water_level: Optional[float] = None

        # ========== 清洁路径上下文 ==========
        self.current_area: Optional[str] = None
        self.current_entrance: Optional[str] = None
        self.current_exit: Optional[str] = None
        self.current_start_pos: Optional[List[float]] = None  # [x, y, yaw] 断点续扫位置

        # ========== 清洁区域状态跟踪 ==========
        self.area_status: Dict[str, CleanAreaStatus] = {}

        # ========== 清洁任务断点 ==========
        self.clean_checkpoint = CleanTaskCheckpoint()

        # ========== 上报信息 ==========
        self.report_info: Dict[str, Any] = {}

        # ========== 时间戳 ==========
        self.last_rbk_sync_time = time.time()
        self.state_change_time = time.time()

        # ========== 急停相关 ==========
        self.emc_triggered = False
        self.emc_suspended_vehicle_state: Optional[VehicleState] = None
        self.emc_suspended_task_type: Optional[TaskType] = None
        self.emc_suspended_position: Optional[List[float]] = None

        # ========== runCleanPath ==========
        self.run_clean_path_init = True

        Trace.log("[cleanRobotManage] Initialized with coordinate-based checkpoint support")

    # ============================================================
    #  ERP状态机
    # ============================================================

    def can_dispatch_to_m4(self) -> bool:
        return self.erp_state == ERPState.IDLE

    def _erp_state_update(self):
        if self.erp_state == ERPState.IDLE:
            pass
        elif self.erp_state == ERPState.TASK_RUNNING:
            if self.vehicle_state in (VehicleState.CHARGING, VehicleState.ADD_WATER):
                self.erp_state = ERPState.TASK_PAUSED
            elif self.current_task and self.current_task.is_completed():
                self.erp_state = ERPState.TASK_COMPLETED
        elif self.erp_state == ERPState.TASK_PAUSED:
            if self.vehicle_state in (VehicleState.CLEANING, VehicleState.NAVIGATING):
                self.erp_state = ERPState.TASK_RUNNING
        elif self.erp_state == ERPState.TASK_COMPLETED:
            self.current_task = None
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.IDLE


    # ============================================================
    #  车辆状态机更新
    # ============================================================

    def _vehicle_state_update(self):
        if self.current_task_type == TaskType.NONE:
            self.vehicle_state = VehicleState.IDLE
        elif self.current_task_type == TaskType.CHARGE:
            self.vehicle_state = VehicleState.CHARGING
        elif self.current_task_type == TaskType.WATER_CHANGE:
            self.vehicle_state = VehicleState.ADD_WATER
        elif self.current_task_type == TaskType.CLEAN:
            if self.current_task:
                if self.current_task.is_current_clean_area():
                    self.vehicle_state = VehicleState.CLEANING
                else:
                    self.vehicle_state = VehicleState.NAVIGATING
            else:
                self.vehicle_state = VehicleState.IDLE

    # ============================================================
    #  GongPath状态机更新
    # ============================================================

    def _gong_path_state_update(self, status_value: int):
        try:
            new_state = BoustrophedonPathState(status_value)
            self.gong_path_state = new_state
        except ValueError:
            Trace.log(f"[GONG_PATH] Unknown status value: {status_value}")


    # ============================================================
    #  清洁任务中断与恢复机制
    # ============================================================

    def _interrupt_clean_for_priority_task(self, interrupt_reason: str) -> bool:
        """
        中断当前清洁任务以执行高优先级任务（充电/换水）

        流程：
        1. 调用 cancelBoustrophedonPath() 取消弓字形导航，获取当前位置
        2. 保存断点（包含机器人坐标）
        3. 关闭清洁机构
        4. 取消当前运单
        """
        if self.current_task_type != TaskType.CLEAN or not self.current_task:
            Trace.log(f"[cleanRobotManage] No clean task to interrupt, reason={interrupt_reason}")
            return True

        Trace.log(f"[cleanRobotManage] Interrupting clean task for {interrupt_reason}")

        is_in_clean_area = self.vehicle_state == VehicleState.CLEANING
        current_location = self.current_task.get_current_location()
        robot_position = None

        # 1. 如果在清洁区域内，取消弓字形导航并获取当前位置
        if is_in_clean_area:
            robot_position = self._cancel_gong_path()
            if self.current_area:
                self.area_status[self.current_area] = CleanAreaStatus.INTERRUPTED

        # 2. 保存断点
        self.clean_checkpoint.save_checkpoint(
            task_data=self.current_task.raw_data,
            step_index=self.current_task.current_step_index,
            location=current_location,
            is_in_clean_area=is_in_clean_area,
            robot_position=robot_position,
            area_name=self.current_area,
            entrance=self.current_entrance,
            exit_station=self.current_exit,
            area_status=self.area_status,
            interrupt_reason=interrupt_reason,
            order_id=self.current_order_id
        )

        # 3. 关闭清洁机构
        self.call_mech("WashEnd")

        # 4. 取消当前运单
        self._cancel_current_order()

        # 5. 清理当前任务状态
        self.current_task = None
        self.current_task_type = TaskType.NONE
        self.vehicle_state = VehicleState.IDLE
        self.gong_path_state = BoustrophedonPathState.INIT

        Trace.log(f"[cleanRobotManage] Clean task interrupted, checkpoint saved with position={robot_position}")
        return True

    def _cancel_gong_path(self) -> dict:
        """取消弓字形导航，返回当前机器人位置 [x, y, yaw]"""
        return Navigation.cancelBoustrophedonPath()

    def _reset_gong_path(self):
        """重置弓字形导航状态"""
        Navigation.resetBoustrophedonPath()
        self.gong_path_state = BoustrophedonPathState.INIT

    def _cancel_current_order(self):
        """
        取消当前运单
        通过HTTP调用调度系统的取消运单API
        """
        if not self.current_order_id:
            Trace.log("[cleanRobotManage] No order to cancel")
            return

        payload = {
            "orderId": self.current_order_id,
            "reason": "Priority task interrupt"
        }

        Trace.log(f"[cleanRobotManage] Cancelling order: {self.current_order_id}")

        try:
            response = requests.post(
                SCHEDULER_CANCEL_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )

            if response.status_code == 200:
                Trace.log(f"[cleanRobotManage] Order {self.current_order_id} cancelled successfully")
                self.current_order_id = None
            else:
                Trace.log(f"[cleanRobotManage] Failed to cancel order: HTTP {response.status_code}, {response.text}")

        except requests.exceptions.Timeout:
            Trace.log(f"[cleanRobotManage] Request timeout when cancelling order")
        except requests.exceptions.ConnectionError as e:
            Trace.log(f"[cleanRobotManage] Connection error when cancelling order: {e}")
        except Exception as e:
            Trace.log(f"[cleanRobotManage] Unexpected error cancelling order: {e}")

    def _check_and_resume_clean_task(self):
        """检查充电/换水是否完成，如果完成则恢复清洁任务"""
        if not self.clean_checkpoint.has_checkpoint():
            return

        if self.erp_state != ERPState.IDLE:
            return

        interrupt_reason = self.clean_checkpoint.interrupt_reason
        can_resume = False

        if interrupt_reason == "charge":
            soc = Battery.getPercentage()
            if soc >= HIGH_BATTERY_SOC:
                can_resume = True
                self.auto_charge_sent = False
                Trace.log(f"[cleanRobotManage] Charge completed (SOC={soc}%), ready to resume")

        elif interrupt_reason == "water_change":
            clean_level, waste_level = 50,50
            if clean_level is not None and waste_level is not None:
                if (clean_level >= ConfigParams.max_clean_water_level and
                        waste_level <= ConfigParams.min_waste_water_level):
                    can_resume = True
                    self.auto_water_sent = False
                    Abnormal.clear(53301)
                    Trace.log(f"[cleanRobotManage] Water change completed, ready to resume")

        if can_resume:
            self._resume_clean_task_from_checkpoint()

    def _resume_clean_task_from_checkpoint(self):
        """从断点恢复清洁任务"""
        resume_info = self.clean_checkpoint.get_resume_info()
        if not resume_info["task_data"]:
            Trace.log("[cleanRobotManage] No task data to resume")
            self.clean_checkpoint.clear()
            return

        Trace.log(f"[cleanRobotManage] Resuming clean task from checkpoint: "
                  f"location={self.clean_checkpoint.location}, "
                  f"position={self.clean_checkpoint.robot_position}")

        # 重置弓字形导航状态
        self._reset_gong_path()

        # 恢复区域状态
        self.area_status = resume_info["area_status"].copy()

        # 构造恢复任务数据
        original_task = resume_info["task_data"]
        step_index = resume_info["step_index"]

        # 从断点位置开始的站点列表
        resume_locations = original_task.get("step_locations", [])[step_index:]

        resume_task_data = original_task.copy()
        resume_task_data["step_locations"] = resume_locations
        resume_task_data["task_id"] = f"{original_task.get('task_id', '')}_resume_{int(time.time())}"

        # 如果在清洁区域内中断，添加恢复位置信息
        if resume_info["is_in_clean_area"] and resume_info["robot_position"]:
            resume_task_data["resume_position"] = resume_info["robot_position"]
            resume_task_data["resume_area"] = resume_info["area_name"]
            resume_task_data["resume_entrance"] = resume_info["entrance"]
            resume_task_data["resume_exit"] = resume_info["exit_station"]

        # 设置当前任务
        self.current_task = CleanTaskData(resume_task_data)
        self.current_task_type = TaskType.CLEAN

        # 恢复路径上下文
        if resume_info["is_in_clean_area"]:
            self.current_area = resume_info["area_name"]
            self.current_entrance = resume_info["entrance"]
            self.current_exit = resume_info["exit_station"]
            self.current_start_pos = resume_info["robot_position"]

        # 构造并发送恢复运单
        payload = self.build_resume_clean_order_json(resume_task_data)
        Trace.log(f"[cleanRobotManage] Sending resume clean order")
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id

        self.erp_state = ERPState.TASK_RUNNING
        self.clean_checkpoint.clear()

    def build_resume_clean_order_json(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """构造从断点恢复的清洁任务 JSON"""
        step_locations = task.get("step_locations", [])
        robot_name = task.get("robot_name", ROBOT_NAME)
        priority = task.get("priority", 50)

        # 恢复位置信息
        resume_position = task.get("resume_position")
        resume_area = task.get("resume_area")

        steps = []
        for i, location in enumerate(step_locations):
            is_clean_area = location.startswith("CA")
            is_last_step = (i == len(step_locations) - 1)

            next_is_clean_area = False
            if i < len(step_locations) - 1:
                next_is_clean_area = step_locations[i + 1].startswith("CA")

            rbk_args = {}

            # 如果是恢复的清洁区域，添加起始位置信息
            if is_clean_area and location == resume_area and resume_position:
                rbk_args["startPos"] = resume_position

            if next_is_clean_area:
                rbk_args["binTask"] = "StartClean"

            step = {
                "location": location,
                "rbkArgs": rbk_args,
                "forLoad": False,
                "forUnload": False,
                "withdrawOrderAllowed": True,
                "nextStepSameOrder": not is_last_step
            }
            steps.append(step)

        return {
            "sceneId": SCENE_ID,
            "priority": priority,
            "expectedRobotNames": [robot_name],
            "expectedRobotGroups": [],
            "keyLocations": [],
            "stepFixed": True,
            "steps": steps
        }

    # ============================================================
    #  急停处理
    # ============================================================

    def _handle_emc(self, emc_status: bool):
        if emc_status and not self.emc_triggered:
            self._on_emc_triggered()
        elif not emc_status and self.emc_triggered:
            self._on_emc_recovered()

    def _on_emc_triggered(self):
        Trace.log("[cleanRobotManage] EMC triggered")
        self.emc_triggered = True

        self.emc_suspended_vehicle_state = self.vehicle_state
        self.emc_suspended_task_type = self.current_task_type

        # 如果在清洁中，取消弓字形并保存位置
        if self.vehicle_state == VehicleState.CLEANING:
            self.emc_suspended_position = self._cancel_gong_path()

        self.vehicle_state = VehicleState.IDLE
        self.erp_state = ERPState.TASK_PAUSED

        Trace.log(f"[cleanRobotManage] EMC state saved: position={self.emc_suspended_position}")

    def _on_emc_recovered(self):
        Trace.log("[cleanRobotManage] EMC recovered")
        self.emc_triggered = False

        if self.emc_suspended_vehicle_state == VehicleState.CLEANING:
            self._resume_clean_after_emc()
        elif self.emc_suspended_vehicle_state == VehicleState.NAVIGATING:
            self.vehicle_state = VehicleState.NAVIGATING
            self.current_task_type = self.emc_suspended_task_type
            self.erp_state = ERPState.TASK_RUNNING
        elif self.emc_suspended_vehicle_state in (VehicleState.CHARGING, VehicleState.ADD_WATER):
            self.vehicle_state = self.emc_suspended_vehicle_state
            self.current_task_type = self.emc_suspended_task_type
            self.erp_state = ERPState.TASK_RUNNING
        else:
            self.vehicle_state = VehicleState.IDLE
            self.erp_state = ERPState.IDLE

        self.emc_suspended_vehicle_state = None
        self.emc_suspended_task_type = None
        self.emc_suspended_position = None

    def _resume_clean_after_emc(self):
        """急停恢复后继续清洁任务"""
        Trace.log(f"[cleanRobotManage] Resuming clean after EMC, position={self.emc_suspended_position}")

        # 使用保存的位置作为起始点
        if self.emc_suspended_position:
            self.current_start_pos = self.emc_suspended_position

        self.current_task_type = TaskType.CLEAN
        self.vehicle_state = VehicleState.CLEANING
        self.erp_state = ERPState.TASK_RUNNING

        self.call_mech(
            "WashStart",
            brush_power=ConfigParams.brush_power,
            suck_power=ConfigParams.suck_power,
            jet_power=ConfigParams.jet_power,
            auto_adjust_power=ConfigParams.auto_adjust_power,
        )

    # ============================================================
    #  外部调用接口
    # ============================================================

    def run(self, args: Dict[str, Any]):
        op = args.get("operation")
        Trace.log(f"[cleanRobotManage] external run(): {op}")

        if not op:
            return

        self._update_path_context(args)

        if op == "WashStart":
            self._handle_wash_start(args)
        elif op == "WashEnd":
            self._handle_wash_end()
        elif op == "Charge":
            self._handle_charge()
        elif op == "AddWater":
            self._handle_add_water()
        elif op == "RunCleanPath":
            self._handle_run_clean_path()
        elif op == "CancelCleanPath":
            self._handle_cancel_clean_path()
        elif op == "ResetCleanPath":
            self._handle_reset_clean_path()
        elif op == "SetTask":
            self._handle_set_task(args)
        elif op == "SendOrders":
            self._handle_send_orders(args)

    def _handle_send_orders(self, args: Dict[str, Any]):
        """
        发送运单给M4调度系统

        Args:
            args: {
                "operation": "SendOrders",
                "order_type": "clean" / "charge" / "water",
                "step_locations": ["LM29", "LM55", ...],  # 站点列表
                "priority": 90,
                "robot_name": "SVJ-01"
            }
        """
        order_type = args.get("order_type", "clean")

        if order_type == "clean":
            step_locations = args.get("step_locations", ["LM3","LM30"])
            if not step_locations:
                Trace.log("[cleanRobotManage] SendOrders: step_locations is empty")
                return

            # 构造任务数据
            task = {
                "step_locations": step_locations,
                "robot_name": args.get("robot_name", ROBOT_NAME),
                "priority": args.get("priority", 90)
            }

            self.current_task = CleanTaskData(task)
            self.current_task_type = TaskType.CLEAN

            for area in self.current_task.clean_areas:
                self.area_status[area] = CleanAreaStatus.NOT_STARTED

            # 构造运单
            payload = self._build_simple_order(
                step_locations=step_locations,
                robot_name=args.get("robot_name", ROBOT_NAME),
                priority=args.get("priority", 90)
            )
            order_id = self.post_to_scheduler(payload)
            self.current_order_id = order_id
            self.erp_state = ERPState.TASK_RUNNING

        elif order_type == "charge":
            payload = self._build_simple_order(
                step_locations=["CP1"],  # 充电桩位置
                robot_name=args.get("robot_name", ROBOT_NAME),
                priority=args.get("priority", 90)
            )
            order_id = self.post_to_scheduler(payload)
            self.current_order_id = order_id
            self.current_task_type = TaskType.CHARGE
            self.vehicle_state = VehicleState.CHARGING
            self.erp_state = ERPState.TASK_RUNNING

        elif order_type == "water":
            payload = self._build_simple_order(
                step_locations=["CP1"],  # 换水站位置
                robot_name=args.get("robot_name", ROBOT_NAME),
                priority=args.get("priority", 90)
            )
            order_id = self.post_to_scheduler(payload)
            self.current_order_id = order_id
            self.current_task_type = TaskType.WATER_CHANGE
            self.vehicle_state = VehicleState.ADD_WATER
            self.erp_state = ERPState.TASK_RUNNING

        else:
            Trace.log(f"[cleanRobotManage] SendOrders: unknown order_type={order_type}")

        Module.setStatus(ScriptStatus.FINISHED)

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
            "sceneId": SCENE_ID,
            "expectedRobotNames": [robot_name],
            "stepFixed": True,
            "priority": priority,
            "steps": steps
        }

    def _update_path_context(self, args: Dict[str, Any]):
        if "area" in args:
            self.current_area = args["area"]
        if "entrance" in args:
            self.current_entrance = args["entrance"]
        if "exit" in args:
            self.current_exit = args["exit"]
        if "startPos" in args:
            self.current_start_pos = args["startPos"]

    def _handle_wash_start(self, args: Dict[str, Any]):
        self.call_mech(
            "WashStart",
            brush_power=args.get("brush_power"),
            suck_power=args.get("suck_power"),
            jet_power=args.get("jet_power"),
            auto_adjust_power=args.get("auto_adjust_power"),
        )

    def _handle_wash_end(self):
        self.call_mech("WashEnd")

    def _handle_charge(self):
        if self.vehicle_state == VehicleState.CLEANING:
            self._cancel_gong_path()
        self.current_task_type = TaskType.CHARGE
        self.vehicle_state = VehicleState.CHARGING
        self.call_mech("Charge")

    def _handle_add_water(self):
        if self.vehicle_state == VehicleState.CLEANING:
            self._cancel_gong_path()
        self.current_task_type = TaskType.WATER_CHANGE
        self.vehicle_state = VehicleState.ADD_WATER
        self.call_mech("AddWater")

    def _handle_run_clean_path(self):
        self.current_task_type = TaskType.CLEAN
        self.vehicle_state = VehicleState.CLEANING
        self.run_clean_path()

    def _handle_cancel_clean_path(self):
        """处理取消清洁路径"""
        if self.vehicle_state == VehicleState.CLEANING:
            pos = self._cancel_gong_path()
            Trace.log(f"[cleanRobotManage] Clean path cancelled, position={pos}")

    def _handle_reset_clean_path(self):
        """处理重置清洁路径"""
        self._reset_gong_path()

    def _handle_set_task(self, args: Dict[str, Any]):
        task_data = CleanTaskData(args)
        self.current_task = task_data
        self.current_task_type = TaskType.CLEAN
        # 初始化区域状态
        for area in task_data.clean_areas:
            self.area_status[area] = CleanAreaStatus.NOT_STARTED
        Trace.log(f"[cleanRobotManage] New task set: {task_data.step_locations}")

    # ============================================================
    #  机构脚本调用封装
    # ============================================================

    def call_mech(
            self,
            operation: str,
            brush_power: Optional[int] = None,
            suck_power: Optional[int] = None,
            jet_power: Optional[int] = None,
            auto_adjust_power: Optional[int] = None,
    ):
        if brush_power is None:
            brush_power = ConfigParams.brush_power
        if suck_power is None:
            suck_power = ConfigParams.suck_power
        if jet_power is None:
            jet_power = ConfigParams.jet_power
        if auto_adjust_power is None:
            auto_adjust_power = ConfigParams.auto_adjust_power

        args = {
            "operation": operation,
            "brush_power": brush_power,
            "suck_power": suck_power,
            "jet_power": jet_power,
            "auto_adjust": auto_adjust_power,
        }
        Trace.log(f"[cleanRobotManage] call_mech -> {args}")

        # 重置机构脚本状态，准备新操作
        self.clean_robot.init = False
        self.clean_robot.action_status = ScriptStatus.NONE

        # 调用机构脚本执行操作
        status = self.clean_robot.run(args)

        # 更新机构状态机
        if operation == "WashStart":
            self.mech_state = MechState.CLEAN_STARTING
        elif operation == "WashEnd":
            self.mech_state = MechState.CLEAN_STOPPING
        elif operation in ("Charge", "AddWater"):
            self.mech_state = MechState.CHARGE_WATER

        return status

    def update_mech_state(self):
        """
        根据机构脚本的实际状态更新机构状态机

        通过检查 clean_robot 的 action_status 和 clean_robot_working/clean_robot_closed 状态
        来更新 mech_state
        """
        if self.clean_robot.action_status == ScriptStatus.FINISHED:
            # 操作完成
            if self.clean_robot.operation == "WashStart":
                if self.clean_robot.clean_robot_working:
                    self.mech_state = MechState.CLEANING
                else:
                    self.mech_state = MechState.CLEAN_STARTING
            elif self.clean_robot.operation == "WashEnd":
                if self.clean_robot.clean_robot_closed:
                    self.mech_state = MechState.IDLE
                else:
                    self.mech_state = MechState.CLEAN_STOPPING
            elif self.clean_robot.operation == "AddWater":
                self.mech_state = MechState.IDLE

        elif self.clean_robot.action_status == ScriptStatus.RUNNING:
            # 操作进行中
            if self.clean_robot.operation == "WashStart":
                if self.clean_robot.clean_robot_working:
                    self.mech_state = MechState.CLEANING
                else:
                    self.mech_state = MechState.CLEAN_STARTING
            elif self.clean_robot.operation == "WashEnd":
                self.mech_state = MechState.CLEAN_STOPPING
            elif self.clean_robot.operation == "AddWater":
                self.mech_state = MechState.CHARGE_WATER

    # ============================================================
    #  任务派发
    # ============================================================

    def dispatch_clean_task_if_needed(self):
        now_ts = time.time()
        task: Optional[Dict[str, Any]] = None

        if not task:
            due = [t for t in self.roboshop_schedule if float(t.get("trigger_ts", 0)) <= now_ts]
            if due:
                due.sort(key=lambda x: x.get("trigger_ts", 0))
                task = due[0]
                self.roboshop_schedule.remove(task)

        if not task:
            return

        self.current_task = CleanTaskData(task)
        self.current_task_type = TaskType.CLEAN

        # 初始化区域状态
        for area in self.current_task.clean_areas:
            self.area_status[area] = CleanAreaStatus.NOT_STARTED

        payload = self.build_clean_order_json(task)
        Trace.log(f"[cleanRobotManage] Dispatching clean task")
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id
        self.erp_state = ERPState.TASK_RUNNING

    def build_clean_order_json(self, task: Dict[str, Any]) -> Dict[str, Any]:
        step_locations = task.get("step_locations", [])
        robot_name = task.get("robot_name", ROBOT_NAME)
        priority = task.get("priority", 50)

        steps = []
        for i, location in enumerate(step_locations):
            is_last_step = (i == len(step_locations) - 1)
            next_is_clean_area = False
            if i < len(step_locations) - 1:
                next_is_clean_area = step_locations[i + 1].startswith("CA")

            rbk_args = {}
            if next_is_clean_area:
                rbk_args["binTask"] = "StartClean"

            step = {
                "location": location,
                "rbkArgs": rbk_args,
                "forLoad": False,
                "forUnload": False,
                "withdrawOrderAllowed": True,
                "nextStepSameOrder": not is_last_step
            }
            steps.append(step)

        return {
            "sceneId": SCENE_ID,
            "priority": priority,
            "expectedRobotNames": [robot_name],
            "expectedRobotGroups": [],
            "keyLocations": [],
            "stepFixed": True,
            "steps": steps
        }

    def build_charge_order_json(self) -> Dict[str, Any]:
        return {
            "sceneId": SCENE_ID,
            "priority": 60,
            "expectedRobotNames": [ROBOT_NAME],
            "expectedRobotGroups": [],
            "keyLocations": [],
            "stepFixed": True,
            "steps": [{
                "location": "CP1",
                "rbkArgs": {"binTask": "Charge"},
                "forLoad": False,
                "forUnload": False,
                "withdrawOrderAllowed": True,
                "nextStepSameOrder": False
            }]
        }

    def build_water_order_json(self) -> Dict[str, Any]:
        return {
            "sceneId": SCENE_ID,
            "priority": 60,
            "expectedRobotNames": [ROBOT_NAME],
            "expectedRobotGroups": [],
            "keyLocations": [],
            "stepFixed": True,
            "steps": [{
                "location": "CP1",
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
        Trace.log(f"[cleanRobotManage] POST {SCHEDULER_URL} -> {json.dumps(payload, ensure_ascii=False)}")
        headers = {
            'xyy-app-id': 'm4',
            'xyy-app-key': 'Seer1234',
            'Content-Type': 'application/json'
        }
        # try:
        response = requests.post(
            SCHEDULER_URL,
            headers=headers,
            json=payload,
            timeout=5
        )

        if response.status_code == 200:
            result = response.json()
            order_id = result.get("orderId") or result.get("order_id") or result.get("id")
            Trace.log(f"[cleanRobotManage] Order created successfully: {order_id}")
            return order_id
        else:
            Trace.log(f"[cleanRobotManage] Failed to create order: HTTP {response.status_code}, {response.text}")
            return None
        #
        # except requests.exceptions.Timeout:
        #     Trace.log(f"[cleanRobotManage] Request timeout when posting to scheduler")
        #     return None
        # except requests.exceptions.ConnectionError as e:
        #     Trace.log(f"[cleanRobotManage] Connection error: {e}")
        #     return None
        # except Exception as e:
        #     Trace.log(f"[cleanRobotManage] Unexpected error posting to scheduler: {e}")
        #     return None


    # ============================================================
    #  清洁路径控制 - 使用新接口
    # ============================================================

    def run_clean_path(self):
        """
        执行弓字形清洁路径

        调用 Navigation.goBoustrophedonPath(area, entrance, exit, startPos, params)
        - startPos 为空时从头开始，有值时从指定位置断点续扫
        """
        self.current_area = "CA1"
        self.current_entrance = "AP3"
        self.current_exit = "AP4"

        if self.run_clean_path_init:
            self.run_clean_path_init = False
            Navigation.resetBoustrophedonPath()

        if not self.current_area or not self.current_entrance or not self.current_exit:
            Trace.log("[cleanRobotManage] run_clean_path: missing path context")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            return

        # 更新区域状态
        self.area_status[self.current_area] = CleanAreaStatus.IN_PROGRESS

        # 启动机构（仅第一次）
        # if self.mech_state == MechState.IDLE:
        #     self.call_mech(
        #         "WashStart",
        #         brush_power=ConfigParams.brush_power,
        #         suck_power=ConfigParams.suck_power,
        #         jet_power=ConfigParams.jet_power,
        #         auto_adjust_power=ConfigParams.auto_adjust_power
        #     )

        # 构造参数
        params = {
            "maxSpeed": ConfigParams.gong_path_max_speed,
            "maxRot": ConfigParams.gong_path_max_rot,
            "isFreeByPass": bool(ConfigParams.gong_path_free_bypass)
        }

        # startPos: 断点续扫位置，None表示从头开始
        start_pos = self.current_start_pos if self.current_start_pos else []

        Trace.log(f"[cleanRobotManage] goBoustrophedonPath: area={self.current_area}, "
                  f"entrance={self.current_entrance}, exit={self.current_exit}, "
                  f"startPos={start_pos}, params={params}")

        # 调用goBoustrophedonPath
        status_value = Navigation.goBoustrophedonPath(
            self.current_entrance,
            self.current_exit,
            start_pos,
            {}
        )
        self.gong_path_state = BoustrophedonPathState(status_value)

        # 清除startPos，避免重复使用
        if self.current_start_pos:
            self.current_start_pos = None

        # 处理状态
        if self.gong_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.gong_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath finished for area {self.current_area}")
            self.area_status[self.current_area] = CleanAreaStatus.COMPLETED
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.gong_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath failed for area {self.current_area}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.gong_path_state == BoustrophedonPathState.SUSPENDED:
            Trace.log("[cleanRobotManage] goBoustrophedonPath suspended")
            return

    def _prepare_next_step(self):
        if not self.current_task:
            return

        current_loc = self.current_task.get_current_location()
        if current_loc and current_loc.startswith("CA"):
            entry, exit_station = self.current_task.get_entry_exit_for_area(current_loc)
            self.current_area = current_loc
            self.current_entrance = entry
            self.current_exit = exit_station
            self.current_start_pos = None  # 新区域从头开始
            self.vehicle_state = VehicleState.CLEANING
        else:
            self.vehicle_state = VehicleState.NAVIGATING

    # ============================================================
    #  电量监控
    # ============================================================

    def check_battery(self):
        soc = Battery.getPercentage()
        if soc < 0:
            return

        if soc <= LOW_BATTERY_SOC and not self.auto_charge_sent:
            Trace.log(f"[cleanRobotManage] Low battery ({soc}%), interrupting for charge")

            if self.current_task_type == TaskType.CLEAN:
                if not self._interrupt_clean_for_priority_task("charge"):
                    return

            payload = self.build_charge_order_json()
            order_id = self.post_to_scheduler(payload)
            self.current_order_id = order_id
            self.auto_charge_sent = True
            self.current_task_type = TaskType.CHARGE
            self.vehicle_state = VehicleState.CHARGING
            self.erp_state = ERPState.TASK_RUNNING

        if soc >= HIGH_BATTERY_SOC:
            self.auto_charge_sent = False

    # ============================================================
    #  水位监控
    # ============================================================



    # ============================================================
    #  上报信息
    # ============================================================

    def update_report_info(self):
        soc = Battery.getPercentage()

        # 从机构脚本同步水位数据
        self.clean_water_level = self.clean_robot.filter_clean_water_level()
        self.waste_water_level = self.clean_robot.filter_waste_water_level()

        self.report_info = {
            # 状态机
            "erp_state": self.erp_state.name,
            "mech_state": self.mech_state.name,
            "vehicle_state": self.vehicle_state.name,
            "gong_path_state": self.gong_path_state.name,
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

            # 任务队列
            "hmi_immediate_count": len(self.hmi_immediate),
            "hmi_schedule_count": len(self.hmi_schedule),
            "roboshop_schedule_count": len(self.roboshop_schedule),

            # 当前路径
            "current_area": self.current_area,
            "current_entrance": self.current_entrance,
            "current_exit": self.current_exit,
            "current_start_pos": self.current_start_pos,

            # 区域状态
            "area_status": {k: v.name for k, v in self.area_status.items()},

            # 当前任务
            "current_task_id": self.current_task.task_id if self.current_task else "",
            "current_task_step": self.current_task.current_step_index if self.current_task else -1,
            "current_task_total_steps": len(self.current_task.step_locations) if self.current_task else 0,

            # 断点信息
            "has_checkpoint": self.clean_checkpoint.has_checkpoint(),
            "checkpoint_reason": self.clean_checkpoint.interrupt_reason,
            "checkpoint_location": self.clean_checkpoint.location,
            "checkpoint_position": self.clean_checkpoint.robot_position,

            # 运单
            "current_order_id": self.current_order_id,

            # 时间
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),

            # 机构脚本信息
            "mech_operation": self.clean_robot.operation,
            "mech_action_status": self.clean_robot.action_status.name if self.clean_robot.action_status else "NONE",
            "mech_clean_robot_working": self.clean_robot.clean_robot_working,
            "mech_clean_robot_closed": self.clean_robot.clean_robot_closed,
            "mech_clean_water_level": self.clean_robot.filter_clean_water_level(),
            "mech_waste_water_level": self.clean_robot.filter_waste_water_level(),
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
    """

    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    validator = ParamValidator(InputParams.builder.toDict())
    mgr = CleanRobotManage()

    while True:
        status = Module.getStatus()
        print(f"---------------status{status}")

        # 周期性运行机构控制脚本，更新机构状态
        mgr.clean_robot.period_run()

        if status in (ScriptStatus.RUNNING, ScriptStatus.NONE):
            input_params = Module.getTaskArgs()
            print("task args:", json.dumps(input_params, indent=2))
            validated_params = {}
            if input_params:
                try:
                    # 验证参数
                    validated_params = validator.validate(input_params)
                    print("check ok, args:", json.dumps(validated_params, indent=2))
                except ValueError as e:
                    print("check error:", e)
                    Abnormal.setTask(53780, f"Input error:{e}", "some input params are not valid",
                                     "check the input params", "input check")

            mgr.run(validated_params)

        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            mgr.init_args = False
            mgr.action_id = 0
            mgr.action_list = []

        # 更新机构状态机
        mgr.update_mech_state()

        # j.print_info()
        time.sleep(0.1)
        Module.reportInfo(mgr.report_info)
        time.sleep(0.1)


if __name__ == "__main__":
    main()