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
# - goBoustrophedonPath(area, entrance, exit, startPos, params): 执行弓字形清扫
# - cancelBoustrophedonPath(): 取消清扫，返回当前位置
# - resetBoustrophedonPath(): 重置清扫状态
#
"""
####BEGIN DEFAULT ARGS####
{}
####END DEFAULT ARGS####
"""

import json
import math
import time
import datetime
import base64
from typing import Any, Dict, List, Optional, Tuple
from enum import IntEnum, auto
import requests

import can
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp

from syspy import Module, ScriptStatus, Trace, Navigation, Abnormal, Battery, Controller, Logger, Do, Can, NavStatus, \
    NavSpeed, Loc

from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ScriptParam

from syspy.lib.robot import RobotParam

# 机构控制日志
log = Logger("clean_robot")

# 本脚本自己的 param loader
param_loader = ScriptParam(__file__)

# 调度/任务相关常量（如需可改成 Param 配置）
SCENE_ID = "690843857C47EE4EE84D5AB7"
ROBOT_NAME = "300J"
CHARGING_SITE = "AP20100"
LOW_BATTERY_SOC = 0.2
HIGH_BATTERY_SOC = 0.9
HMI_PERIOD = 1.0  # /s 车载屏轮询周期
ROBOSHOP_PERIOD = 1.0  # /s 单车平台轮询周期

# 调度 HTTP 地址
SCHEDULER_URL = "http://172.17.30.50:5800/api/fleet/orders/create"
SCHEDULER_CANCEL_URL = "http://172.17.30.50:5800/api/fleet/orders/cancel"


# ============================================================
#  状态机枚举定义
# ============================================================

class ERPState(IntEnum):
    """
    ERP状态机 - 控制何时可以发单给M4调度系统

    注：仅保留 IDLE、TASK_RUNNING、ERROR 三个状态
    - TASK_PAUSED 和 TASK_COMPLETED 可以通过 IDLE + 断点信息来表达
    """
    IDLE = 0  # 空闲，可以接收新任务并发单
    TASK_RUNNING = 1  # 任务执行中
    ERROR = 4  # 错误状态，需要人工干预


# 删除 MechState:
# 原因：mech_state 只在初始化时赋值为 IDLE，从未被更新或使用
# 机构的实际状态已由 CleanRobotMech 类内部管理（如 action_status）


class VehicleState(IntEnum):
    """车辆状态机 - 机器人本身的状态"""
    IDLE = 0  # 无任务
    ADD_WATER = 1  # 加水/排污中
    CHARGING = 2  # 充电中
    CLEANING = 3  # 清洁中（在清洁区域内执行清洁）
    NAVIGATING = 4  # 无清洁导航中（在清洁区和清洁区之间的过程）


class BoustrophedonPathState(IntEnum):
    """BoustrophedonPath状态机 - 走工艺路径的状态"""
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


# 注：CleanAreaStatus 已删除，不再通过CA前缀判断清洁区域


# ============================================================
#  清洁任务断点数据结构
# ============================================================

class CleanTaskCheckpoint:
    """
    清洁任务断点数据结构（简化版）
    用于在充电/换水中断时保存清洁任务状态，以便后续恢复

    简化说明：只记录站点，不再使用清洁区域概念
    使用 Navigation.moveTask().get("targetName") 获取当前导航目标点
    """

    def __init__(self):
        # 原始任务数据
        self.task_data: Optional[Dict[str, Any]] = None

        # 断点位置信息
        self.step_index: int = 0  # 中断时的步骤索引
        self.location: Optional[str] = None  # 中断时的位置（站点名称）

        # 当前导航目标点（用于断点续扫时计算恢复起点）
        self.nav_target: Optional[str] = None  # 中断时正在前往的目标点名称
        self.nav_target_index: int = -1  # 目标点在任务站点列表中的索引

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
            interrupt_reason: str = "",
            order_id: Optional[str] = None,
            nav_target: Optional[str] = None,
            nav_target_index: int = -1,
    ):
        """保存断点信息（简化版：只记录站点）"""
        self.task_data = task_data.copy() if task_data else None
        self.step_index = step_index
        self.location = location
        self.interrupt_reason = interrupt_reason
        self.interrupt_time = time.time()
        self.order_id = order_id
        self.nav_target = nav_target
        self.nav_target_index = nav_target_index

        Trace.log(f"[CleanTaskCheckpoint] Saved: location={location}, "
                  f"step_index={step_index}, reason={interrupt_reason}, "
                  f"nav_target={nav_target}, nav_target_index={nav_target_index}")

    def has_checkpoint(self) -> bool:
        """检查是否有保存的断点"""
        return self.task_data is not None

    def clear(self):
        """清除断点信息"""
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
        """
        获取用于恢复的信息（简化版）
        """
        return {
            "task_data": self.task_data,
            "step_index": self.step_index,
            "nav_target": self.nav_target,
            "nav_target_index": self.nav_target_index,
        }

    def get_resume_start_index(self) -> int:
        """
        获取恢复任务时的起始索引

        逻辑：
        - 如果有 nav_target_index，从它的前一个站点开始（确保机器人先到达前一个点）
        - 如果 nav_target_index 是 0，则从 0 开始
        - 否则使用 step_index
        """
        if self.nav_target_index > 0:
            return self.nav_target_index - 1
        elif self.nav_target_index == 0:
            return 0
        else:
            return self.step_index


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
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("DO-004")

                    with builder.CHILD(key="push_rod_length", name="push_rod_length",
                                       desc="刷盘推杆行程, 取值: 70-100, 刷盘下降的高度,参数可缺省"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(75)
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

                    with builder.CHILD(key="boustrophedon_path_max_speed", name="boustrophedon_path_max_speed",
                                       desc="弓字形路径最大直线速度"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(1.0)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="boustrophedon_path_max_rot", name="boustrophedon_path_max_rot",
                                       desc="弓字形路径最大旋转速度"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5)
                        builder.UNIT("rad/s")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="boustrophedon_path_free_bypass", name="boustrophedon_path_free_bypass",
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

                    with builder.CHILD(key="scheduled_clean_enabled", name="scheduled_clean_enabled",
                                       desc="是否启用每日定时清洁任务"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1)  # 默认启用
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="scheduled_clean_hour", name="scheduled_clean_hour",
                                       desc="每日定时清洁任务执行时间（小时，0-23）"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(8)  # 默认早上8点
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="scheduled_clean_minute", name="scheduled_clean_minute",
                                       desc="每日定时清洁任务执行时间（分钟，0-59）"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(0)  # 默认整点
                        builder.SINGLESTEP(1)

                    with builder.CHILD(key="scheduled_clean_locations", name="scheduled_clean_locations",
                                       desc="每日定时清洁任务的站点路径"):
                        builder.TYPE(ParamType.ARRAY)
                        builder.DEFAULTVALUE(
                            ["LM1", "LM2", "AP3", "AP4", "LM5", "AP6", "AP7", "AP8", "AP9", "AP10", "LM11", "LM12"])

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
        cls.roboshop_task_interval = cls.config.get("roboshop_task_interval")
        cls.roboshop_clean_areas = cls.config.get("roboshop_clean_areas")

        # 每日定时清洁任务配置
        cls.scheduled_clean_enabled = cls.config.get("scheduled_clean_enabled", 1)
        cls.scheduled_clean_hour = cls.config.get("scheduled_clean_hour", 8)
        cls.scheduled_clean_minute = cls.config.get("scheduled_clean_minute", 0)
        cls.scheduled_clean_locations = cls.config.get("scheduled_clean_locations", [])

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

    builder.save_to_file()


# ============================================================
#  清洁任务数据结构
# ============================================================




# ============================================================
#  机构控制相关枚举和类（原 cleanRobotMech.py）
# ============================================================

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

    def ctrl_suck(self, power=0):
        cmd = MechCmd.SUCK[:12] + hex(power)[2:].zfill(2) + MechCmd.SUCK[14:]
        self.send_cmd(cmd)

    def ctrl_brush(self, power=0):
        cmd = MechCmd.BRUSH[:12] + hex(power)[2:].zfill(2) + MechCmd.BRUSH[14:]
        self.send_cmd(cmd)

    def ctrl_jet_pump(self, power=0):
        cmd = MechCmd.JET_PUMP[:12] + hex(power)[2:].zfill(2) + MechCmd.JET_PUMP[14:]
        self.send_cmd(cmd)

    def ctrl_pod_length(self, power=0):
        cmd = MechCmd.BRUSH_POD_DOWN[:12] + hex(power)[2:].zfill(2) + MechCmd.BRUSH_POD_DOWN[14:]
        self.send_cmd(cmd)

    def ctrl_brush_lift(self, state):
        cmd = MechCmd.BRUSH_LIFT_DOWN if state == MechWorkState.OPEN else MechCmd.BRUSH_LIFT_UP
        self.send_cmd(cmd)

    def ctrl_mop_lift(self, state):
        cmd = MechCmd.MOP_LIFT_DOWN if state == MechWorkState.OPEN else MechCmd.MOP_LIFT_UP
        self.send_cmd(cmd)

    def ctrl_clean_valve(self, state):
        cmd = MechCmd.WATER_VALVE_OPEN if state == MechWorkState.OPEN else MechCmd.WATER_VALVE_CLOSE
        self.send_cmd(cmd)

    def ctrl_waste_valve(self, state):
        cmd = MechCmd.BRAIN_BALL_VALVE_OPEN if state == MechWorkState.OPEN else MechCmd.BRAIN_BALL_VALVE_CLOSE
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
        data = Can.getData()
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
        # Modbus TCP 连接
        self.ip = "127.0.0.1"
        self.port = 502
        self.modbus_tcp = modbus_tcp.TcpMaster(self.ip, self.port, 1)
        self.is_connected = False
        self.rbk_addr = 110

        # 清洁机构工作状态
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

        # 液位数据
        self.clean_water_level: float = -1
        self.waste_water_level: float = -1
        self.clean_filter = MeanValue(1000)
        self.waste_filter = MeanValue(1000)

        # 控制参数
        self.auto_adjust_power = config_params.auto_adjust_power
        self.jet_power = config_params.jet_power
        self.brush_power = config_params.brush_power
        self.suck_power = config_params.suck_power
        self.push_rod_length = config_params.push_rod_length

        # 时间戳
        self.wash_start_time = None
        self.add_water_time_start = None
        self.close_jet_pump_start = None
        self.add_water_opt_start = False

        # 操作状态
        self.operation = None
        self.init = False
        self.action_status = ScriptStatus.NONE
        self.report_info = {}

        # 计数器
        self.period_run_start = time.time()
        self.task_update_start = time.time()
        self.period_run_counter = 0

        # 硬件接口
        self.hardware = CleanRobotHardware(self)

        log.info("CleanRobotMech initialized")

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
            #TODO:检查后可以删除这部分内容，
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
            self.wash_start()
        elif self.operation == "WashEnd":
            self.wash_end()
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
            Abnormal.setTask(53910, f"args error: {self.operation}", "参数错误", "检查operation参数", "run")
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

        if task_status == 2:  # Running
            if self.operation == "WashStart" and self.action_status == ScriptStatus.FINISHED:
                self.wash_open()
        elif task_status == 3:  # Suspended
            self.wash_suspend()
        elif task_status == 5:  # Failed
            self.wash_end()
        elif task_status == 6:  # Canceled
            self.wash_suspend()

        if Controller.getEmc():
            self.wash_end()

        loc_state = Loc.getLocState()
        if self.filter_waste_water_level() > config_params.max_waste_water_level:
            Abnormal.setTask(53980, "Waste water full!", "污水满", "去排水", "update_by_task_status")
            if self.operation != "AddWater" and loc_state == 1:
                self.wash_end()
        elif self.filter_clean_water_level() < config_params.min_clean_water_level and self.filter_clean_water_level() != -1:
            Abnormal.setTask(53980, "Clean water empty!", "清水空", "去加水", "update_by_task_status")
            if self.operation != "AddWater" and loc_state == 1:
                self.wash_end()
        else:
            if Abnormal.exists(53980):
                Abnormal.clear(53980)

    def connect(self):
        """连接Modbus TCP"""
        try:
            self.modbus_tcp.open()
            self.is_connected = True
        except Exception as e:
            log.info(f"connect error: {e}")

    def save_to_rbk(self):
        """保存液位数据到RBK"""
        try:
            self.modbus_tcp.execute(1, cst.WRITE_MULTIPLE_REGISTERS, self.rbk_addr,
                                    output_value=[round(self.filter_clean_water_level()),
                                                  round(self.filter_waste_water_level())])
        except Exception as e:
            log.info(f"save_to_rbk error: {e}")

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
        elif self.jet_status != MechWorkingStatus.RUNNING:
            self.hardware.ctrl_jet_pump(self.jet_power)

    def is_fit_push_rod(self):
        """检查推杆长度"""
        if int(self.push_rod_length) < 70 or int(self.push_rod_length) > 100:
            Abnormal.setTask(53901, f"Push rod length limit: {self.push_rod_length}", "推杆超限", "调整参数",
                             "is_fit_push_rod")
            self.wash_end()
        else:
            self.hardware.ctrl_pod_length(self.push_rod_length)

    def wash_start(self):
        """开始清洗"""
        self.operation = "WashStart"
        self.wash_open()
        if self.clean_robot_working:
            self.action_status = ScriptStatus.FINISHED

    def wash_water(self):
        """排空水管"""
        if self.operation == "WashEnd":
            if self.jet_status != MechWorkingStatus.RUNNING:
                self.hardware.ctrl_jet_pump(self.jet_power)
            if self.clean_valve_status != MechWorkingStatus.RUNNING:
                self.hardware.ctrl_clean_valve(MechWorkState.OPEN)

    def wash_end(self):
        """结束清洗"""
        self.operation = "WashEnd"
        Do.setDo(config_params.add_water_do, False)

        if self.waste_valve_status == MechWorkingStatus.RUNNING:
            self.hardware.ctrl_waste_valve(MechWorkState.CLOSE)

        if not self.close_jet_pump_start:
            self.close_jet_pump_start = time.time()

        if not self.clean_robot_closed:
            if self.close_jet_pump_start and time.time() - self.close_jet_pump_start < 3:
                self.wash_water()

        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > config_params.close_jet_delay_time * 0.7:
            if self.brush_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_brush(0)
            if self.jet_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_jet_pump(0)
            if self.clean_valve_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_clean_valve(MechWorkState.CLOSE)
            if self.brush_lift_status != MechWorkingStatus.INIT:
                self.hardware.ctrl_brush_lift(MechWorkState.CLOSE)

        if self.close_jet_pump_start and time.time() - self.close_jet_pump_start > config_params.close_jet_delay_time:
            if self.mop_lift_status != MechWorkingStatus.INIT:
                self.hardware.ctrl_mop_lift(MechWorkState.CLOSE)
            if self.suck_status == MechWorkingStatus.RUNNING:
                self.hardware.ctrl_suck(0)

        if self.clean_robot_closed:
            self.close_jet_pump_start = None
            self.action_status = ScriptStatus.FINISHED

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
        # if self.mop_lift_status != MechWorkingStatus.RUNNING:
        #     self.hardware.ctrl_mop_lift(MechWorkState.OPEN)
        # if self.suck_status != MechWorkingStatus.RUNNING:
        #     self.hardware.ctrl_suck(self.suck_power)
        # else:
        #     self.action_status = ScriptStatus.FINISHED
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
            Abnormal.setTask(53900, "Not charging!", "未充电", "移动到充电桩", "add_water")
            self.action_status = ScriptStatus.FAILED
        else:
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
        print(f"{recv_data=}")
        if self.hardware.query_all_cmd_status == MechWorkingStatus.FINISHED:
            self.hardware.query_all_cmd_status = MechWorkingStatus.INIT
            state = bin(int(recv_data[12:14], 16))[2:].zfill(8)
            self.clean_water_level = int(recv_data[8:10], 16)
            self.waste_water_level = int(recv_data[10:12], 16)
            self.push_rod_status = int(recv_data[14:16], 16)
            self.jet_status = MechWorkingStatus(int(state[1:2]))
            self.brush_status = MechWorkingStatus(int(state[2:3]))
            self.suck_status = MechWorkingStatus(int(state[3:4]))
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
        Module.reportInfo(self.report_info)

    def cancel(self):
        """取消操作"""
        Trace.log("CleanRobotMech cancel")
        Do.setDo(config_params.add_water_do, False)
        self.wash_end()
        self.action_status = ScriptStatus.FAILED

    def get_water_levels(self) -> Tuple[float, float]:
        """获取水位信息 (清水, 污水)"""
        return self.filter_clean_water_level(), self.filter_waste_water_level()


# ============================================================
#  主管理类
# ============================================================

class CleanRobotManage:

    def __init__(self):
        # ========== 状态机 ==========
        self.erp_state = ERPState.IDLE
        # 删除 mech_state：机构状态由 CleanRobotMech 内部管理
        self.vehicle_state = VehicleState.IDLE
        self.mech_status = ScriptStatus.NONE
        self.boustrophedon_path_state = BoustrophedonPathState.INIT

        self.current_task_type = TaskType.NONE

        # ========== 机构脚本实例 ==========
        self.mech = CleanRobotMech()

        # ========== 任务缓存 ==========

        self.roboshop_schedule: List[Dict[str, Any]] = []
        self.last_roboshop_pull = 0.0
        self.last_roboshop_task_time = 0.0

        self.current_task: Optional[Dict[str, Any]] = None
        self.current_order_id: Optional[str] = None

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
        self.pos = []

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

        # ========== 当前导航目标点跟踪 ==========
        self.current_nav_target: Optional[str] = None  # 当前正在前往的目标点名称

        # ========== 每日定时清洁任务 ==========
        self.last_scheduled_clean_date: Optional[str] = None  # 上次执行定时清洁的日期，格式 "YYYY-MM-DD"
        self.scheduled_clean_triggered_today: bool = False  # 今天是否已触发定时清洁

        # ========== cancel once ==========
        self.cancel_once = True
        self.cancel_count = 0
        self.saved_exit_id = None
        self.have_cancelled = False

        # ========== 原始站点列表（用于断点续传）==========
        self.original_step_locations: List[str] = []  # 保存SendOrders的原始站点列表
        self.remaining_step_locations: List[str] = []  # 实时更新的剩余站点列表

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

    # ============================================================
    #  ERP状态机
    # ============================================================

    def can_dispatch_to_m4(self) -> bool:
        return self.erp_state == ERPState.IDLE

    def _erp_state_update(self):
        """
        ERP状态机更新（简化版）

        只保留 IDLE、TASK_RUNNING、ERROR 三个状态:
        - 充电/换水期间的"暂停"通过 clean_checkpoint 断点信息表达
        - 任务完成后直接切换到 IDLE
        """
        if self.erp_state == ERPState.IDLE:
            pass
        elif self.erp_state == ERPState.TASK_RUNNING:
            # 任务完成检查已在其他地方处理（通过 current_task = None）
            pass
        # ERROR 状态需要人工干预，不自动转换

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
        5. 关闭清洁机构
        6. 取消当前运单

        恢复逻辑：
        - 假设原任务: [LM1, LM2, AP3, AP4, LM5, AP6, AP7, AP8, AP9, AP10, LM11, LM12]
        - 中断时正在前往 AP8（nav_target_index = 7）
        - 恢复时从 AP7（index 6）开始，发送: [AP7, AP8, AP9, AP10, LM11, LM12]
        """
        if self.current_task_type != TaskType.CLEAN or not self.current_task:
            Trace.log(f"[cleanRobotManage] No clean task to interrupt, reason={interrupt_reason}")
            return True

        Trace.log(f"[cleanRobotManage] Interrupting clean task for {interrupt_reason}")

        step_locations = self.current_task.get("step_locations", [])
        current_location = step_locations[0] if step_locations else None

        # 1. 获取当前导航目标点
        nav_target = self._get_current_nav_target()
        nav_target_index = self._get_nav_target_index_in_task()
        Trace.log(f"[cleanRobotManage] Current nav target: {nav_target}, index: {nav_target_index}")

        # 2. 直接获取机器人当前位置（使用 Loc.getPos()）
        robot_position = [Loc.getPose()["x"], Loc.getPose()["y"], math.radians(Loc.getPose()["yaw"])]

        # 3. 如果弓字形路径正在运行，取消它
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

        # 5. 关闭清洁机构
        self.call_mech("WashEnd")

        # 6. 取消当前运单
        self._cancel_current_order()

        # 7. 清理当前任务状态
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

    def _reset_boustrophedon_path(self):
        """重置弓字形导航状态"""
        Navigation.resetBoustrophedonPath()
        self.pos = []
        self.boustrophedon_path_state = BoustrophedonPathState.INIT

    def _cancel_current_order(self):
        """
        取消当前运单

        通过HTTP POST调用调度系统的取消运单API

        API地址: SCHEDULER_CANCEL_URL
        请求格式: {"orderId": "xxx", "reason": "xxx"}
        """
        if not self.current_order_id:
            Trace.log("[cleanRobotManage] No order to cancel")
            return

        payload = {
            "sceneId": SCENE_ID,
            "orderId": self.current_order_id
            # "reason": "Priority task interrupt"
        }

        Trace.log(f"[cleanRobotManage] Cancelling order: {self.current_order_id}")

        # try:
        response = requests.post(
            SCHEDULER_CANCEL_URL,
            json=payload,
            headers = {
            'xyy-app-id': 'm4',
            'xyy-app-key': 'Seer1234',
            'Content-Type': 'application/json'},
            timeout=5
        )

        if response.status_code == 200:
            Trace.log(f"[cleanRobotManage] Order {self.current_order_id} cancelled successfully")
            self.current_order_id = None
        else:
            Trace.log(f"[cleanRobotManage] Failed to cancel order: HTTP {response.status_code}, {response.text}")
        #
        # except requests.exceptions.Timeout:
        #     Trace.log(f"[cleanRobotManage] Request timeout when cancelling order {self.current_order_id}")
        # except requests.exceptions.ConnectionError as e:
        #     Trace.log(f"[cleanRobotManage] Connection error when cancelling order: {e}")
        # except Exception as e:
        #     Trace.log(f"[cleanRobotManage] Unexpected error cancelling order: {e}")

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
            clean_level, waste_level = 50, 50  # TODO
            if clean_level is not None and waste_level is not None:
                if (clean_level >= config_params.max_clean_water_level and
                        waste_level <= config_params.min_waste_water_level):
                    can_resume = True
                    self.auto_water_sent = False
                    Abnormal.clear(53301)
                    Trace.log(f"[cleanRobotManage] Water change completed, ready to resume")

        if can_resume:
            self._resume_clean_task_from_checkpoint()

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
            return

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

        # 设置当前任务
        self.current_task = resume_task_data
        self.current_task_type = TaskType.CLEAN

        # 构造并发送恢复运单（使用简单格式）
        payload = self._build_simple_order(
            step_locations=resume_locations,
            robot_name=resume_task_data.get("robot_name", ROBOT_NAME),
            priority=resume_task_data.get("priority", 50)
        )
        Trace.log(f"[cleanRobotManage] Sending resume clean order")
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id

        self.erp_state = ERPState.TASK_RUNNING
        self.clean_checkpoint.clear()

    # 删除 build_resume_clean_order_json 方法，改用 _build_simple_order

    # ============================================================
    #  急停处理
    # ============================================================

    def _handle_emc(self, emc_status: bool):
        """
        处理急停状态变化

        Args:
            emc_status: True=急停触发, False=急停解除
        """
        if emc_status and not self.emc_triggered:
            # 急停刚触发
            self._on_emc_triggered()
        elif not emc_status and self.emc_triggered:
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
        self.emc_triggered = True

        # 1. 保存急停前的状态（用于恢复）
        self.emc_suspended_vehicle_state = self.vehicle_state
        self.emc_suspended_task_type = self.current_task_type
        Trace.log(
            f"[cleanRobotManage] EMC: Saved pre-EMC state: vehicle={self.vehicle_state.name}, task={self.current_task_type.name}")

        # 4. 关闭清洁机构
        Trace.log("[cleanRobotManage] EMC: Closing cleaning mechanism (WashEnd)")
        self.call_mech("WashEnd")

        # 5. 重置车辆状态
        self.vehicle_state = VehicleState.IDLE
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
        self.emc_triggered = False

        # 根据急停前的状态进行恢复
        if self.emc_suspended_vehicle_state == VehicleState.CLEANING:
            # 恢复清洁任务
            Trace.log("[cleanRobotManage] EMC Recovery: Resuming CLEANING state")
            self._resume_clean_after_emc()
        elif self.emc_suspended_vehicle_state == VehicleState.NAVIGATING:
            # 恢复导航状态
            Trace.log("[cleanRobotManage] EMC Recovery: Resuming NAVIGATING state")
            self.vehicle_state = VehicleState.NAVIGATING
            self.current_task_type = self.emc_suspended_task_type
            self.erp_state = ERPState.TASK_RUNNING
        elif self.emc_suspended_vehicle_state in (VehicleState.CHARGING, VehicleState.ADD_WATER):
            # 恢复充电/换水状态
            Trace.log(f"[cleanRobotManage] EMC Recovery: Resuming {self.emc_suspended_vehicle_state.name} state")
            self.vehicle_state = self.emc_suspended_vehicle_state
            self.current_task_type = self.emc_suspended_task_type
            self.erp_state = ERPState.TASK_RUNNING
        else:
            # 其他情况恢复为空闲状态
            Trace.log("[cleanRobotManage] EMC Recovery: Resuming to IDLE state")
            self.vehicle_state = VehicleState.IDLE
            self.erp_state = ERPState.IDLE

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
            self.current_start_pos = self.emc_suspended_position

        self.current_task_type = TaskType.CLEAN
        self.vehicle_state = VehicleState.CLEANING
        self.erp_state = ERPState.TASK_RUNNING

        self.call_mech(
            "WashStart",
            brush_power=config_params.brush_power,
            suck_power=config_params.suck_power,
            jet_power=config_params.jet_power,
            auto_adjust_power=config_params.auto_adjust_power,
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
        elif op == "DustStart":
            self._handle_dust_start()
        elif op == "DustStart":
            self._handle_dust_end()
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
        elif op == "SendContinueOrders":
            self._handle_send_continue_orders(args)
        elif op == "CancelOrder":
            self._handle_cancel_order(args)
        elif op == "SendChargeOrder":
            self._handle_send_charge_order(args)
        elif op == "SendWaterOrder":
            self._handle_send_water_order(args)
        elif op == "RunCleanPathAndWashStart":
            self._handle_run_clean_path_and_wash(args)

    def _handle_send_charge_order(self, args: Dict[str, Any]):
        """
        发送充电运单（会中断当前清洁任务）

        Args:
            args: {
                "operation": "SendChargeOrder",
                "charge_station": "CP1",  # 可选，充电站位置
                "robot_name": "SVJ-01",   # 可选
                "priority": 90            # 可选
            }

        流程：
        1. 如果正在执行清洁任务，先中断并保存断点
        2. 发送充电运单
        """
        Trace.log("[cleanRobotManage] SendChargeOrder triggered")

        # 如果正在执行清洁任务，先中断
        if self.current_task_type == TaskType.CLEAN and self.current_task:
            if not self._interrupt_clean_for_priority_task("charge"):
                Trace.log("[cleanRobotManage] Failed to interrupt clean task for charging")
                Module.setStatus(ScriptStatus.FAILED)
                return

        # 发送充电运单
        charge_station = args.get("charge_station", CHARGING_SITE)
        payload = self._build_simple_order(
            step_locations=[charge_station],
            robot_name=args.get("robot_name", ROBOT_NAME),
            priority=args.get("priority", 90)
        )
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id
        self.current_task_type = TaskType.CHARGE
        self.vehicle_state = VehicleState.CHARGING
        self.erp_state = ERPState.TASK_RUNNING
        self.auto_charge_sent = True

        Module.setStatus(ScriptStatus.FINISHED)

    def _handle_send_water_order(self, args: Dict[str, Any]):
        """
        发送换水运单（会中断当前清洁任务）

        Args:
            args: {
                "operation": "SendWaterOrder",
                "water_station": "CP1",   # 可选，换水站位置
                "robot_name": "SVJ-01",   # 可选
                "priority": 90            # 可选
            }

        流程：
        1. 如果正在执行清洁任务，先中断并保存断点
        2. 发送换水运单
        """
        Trace.log("[cleanRobotManage] SendWaterOrder triggered")

        # 如果正在执行清洁任务，先中断
        if self.current_task_type == TaskType.CLEAN and self.current_task:
            if not self._interrupt_clean_for_priority_task("water_change"):
                Trace.log("[cleanRobotManage] Failed to interrupt clean task for water change")
                Module.setStatus(ScriptStatus.FAILED)
                return

        # 发送换水运单
        water_station = args.get("water_station", CHARGING_SITE)
        payload = self._build_simple_order(
            step_locations=[water_station],
            robot_name=args.get("robot_name", ROBOT_NAME),
            priority=args.get("priority", 90)
        )
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id
        self.current_task_type = TaskType.WATER_CHANGE
        self.vehicle_state = VehicleState.ADD_WATER
        self.erp_state = ERPState.TASK_RUNNING
        self.auto_water_sent = True

        Module.setStatus(ScriptStatus.FINISHED)

    def _handle_run_clean_path_and_wash(self, args: Dict[str, Any]):
        self.current_task_type = TaskType.CLEAN
        self.vehicle_state = VehicleState.CLEANING

        self.current_entrance = Navigation.moveTask().get("sourceName", None)
        self.current_exit = Navigation.moveTask().get("targetName", None)

        print(f"-----{self.current_exit=}")
        print(f"-----{self.saved_exit_id=}")
        print(f"-----{self.have_cancelled=}")

        if not self.saved_exit_id:
            self.run_clean_path_and_wash(args)
        else:
            if self.saved_exit_id != self.current_exit and self.current_exit != "":
                print(f"---------run_cross_path")
                self.run_cross_path()
            elif self.have_cancelled:
                print(f"---------run_exit_path")
                self.run_exit_path()  # self.have_cancelled重置
            elif self.saved_exit_id == self.current_exit:
                print(f"---------run_exit_path")
                self.run_remaining_path()  # self.saved_exit_id重置
            else:
                print(f"---------run_no_path")

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
        # step_locations = args.get("step_locations", ["AP20001", "AP20002", "AP20112", "AP20111"])
        #TODO：可以在配置项里上传，最后一个点是停靠点，每2个站点表示一个清洁区（一个入口，一个出口）
        step_locations = args.get("step_locations", ["AP20116", "AP20115", "AP20114", "AP20113", "AP20027", "AP20028",
                                                     "AP20031", "AP20032", "AP20033", "AP20034", "AP20040", "AP20041",
                                                     "AP20045", "AP20046", "AP20054", "AP20055", "AP20063", "AP20064",
                                                     "AP20071", "AP20072", "AP20077", "AP20078", "AP20083", "AP20084",
                                                     "AP20089", "AP20090", "AP20095", "AP20096", "LM20103"])

        if not step_locations:
            Trace.log("[cleanRobotManage] SendOrders: step_locations is empty")
            return

        # 保存原始站点列表，用于断点续传
        self.original_step_locations = step_locations.copy()
        self.remaining_step_locations = step_locations.copy()  # 初始时剩余站点等于原始站点
        Trace.log(f"[cleanRobotManage] SendOrders: saved original locations = {self.original_step_locations}")

        # 构造任务数据
        task = {
            "step_locations": step_locations,
            "robot_name": args.get("robot_name", ROBOT_NAME),
            "priority": args.get("priority", 90)
        }

        self.current_task = task
        self.current_task_type = TaskType.CLEAN

        # 构造运单
        payload = self._build_simple_order(
            step_locations=step_locations,
            robot_name=args.get("robot_name", ROBOT_NAME),
            priority=args.get("priority", 90)
        )
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id
        self.erp_state = ERPState.TASK_RUNNING

        Module.setStatus(ScriptStatus.FINISHED)

    def _handle_send_continue_orders(self, args: Dict[str, Any]):
        """
        发送续传运单给M4调度系统

        直接使用在main循环中持续更新的 remaining_step_locations

        Args:
            args: {
                "operation": "SendContinueOrders",
                "robot_name": "SVJ-01",   # 可选
                "priority": 90            # 可选
            }
        """
        Trace.log(f"[cleanRobotManage] SendContinueOrders: "
                  f"original={self.original_step_locations}, "
                  f"remaining={self.remaining_step_locations}")

        # 检查是否有剩余站点列表
        if not self.remaining_step_locations:
            # 如果没有剩余站点，尝试使用参数中的站点列表
            step_locations = args.get("step_locations", [])
            if not step_locations:
                Trace.log("[cleanRobotManage] SendContinueOrders: no remaining locations and no new locations provided")
                Module.setStatus(ScriptStatus.FAILED)
                return
            # 如果提供了新的站点列表，直接使用
            Trace.log(f"[cleanRobotManage] SendContinueOrders: using provided locations = {step_locations}")
        else:
            # 使用实时更新的剩余站点列表
            step_locations = self.remaining_step_locations.copy()

        Trace.log(f"[cleanRobotManage] SendContinueOrders: sending locations = {step_locations}")

        # 构造任务数据
        task = {
            "step_locations": step_locations,
            "robot_name": args.get("robot_name", ROBOT_NAME),
            "priority": args.get("priority", 90)
        }

        self.current_task = task
        self.current_task_type = TaskType.CLEAN

        # 构造运单
        payload = self._build_simple_order(
            step_locations=step_locations,
            robot_name=args.get("robot_name", ROBOT_NAME),
            priority=args.get("priority", 90)
        )
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id
        self.erp_state = ERPState.TASK_RUNNING

        Module.setStatus(ScriptStatus.FINISHED)

    def _update_remaining_locations(self):
        """
        持续更新剩余站点列表（在main循环中调用）

        通过 Navigation.moveTask() 获取当前导航状态，
        根据 source_name 更新 remaining_step_locations

        逻辑：
        - 当 source_name 在原始列表中时，从 source_name 开始（包含）到列表末尾
        - 随着机器人移动，source_name 会变化，remaining_step_locations 会逐步缩短

        示例：
            原始列表: ["AP1", "AP2", "AP3", "AP4", "AP5"]

            机器人在 AP1 → AP2 途中: source_name="AP1", target_name="AP2"
                → remaining = ["AP1", "AP2", "AP3", "AP4", "AP5"]

            机器人在 AP2 → AP3 途中: source_name="AP2", target_name="AP3"
                → remaining = ["AP2", "AP3", "AP4", "AP5"]

            机器人在 AP4 → AP5 途中: source_name="AP4", target_name="AP5"
                → remaining = ["AP4", "AP5"]
        """
        # 如果没有原始站点列表，不需要更新
        if not self.original_step_locations:
            return

        # 获取当前导航状态
        source_name = Navigation.moveTask().get("sourceName", None)
        target_name = Navigation.moveTask().get("targetName", None)

        # 如果 source_name 为空，不更新
        if not source_name:
            return

        # 如果 source_name 在原始列表中，更新剩余站点
        if source_name in self.original_step_locations:
            source_index = self.original_step_locations.index(source_name)
            new_remaining = self.original_step_locations[source_index:]

            # 只有当剩余站点变化时才更新和打印日志
            if new_remaining != self.remaining_step_locations:
                self.remaining_step_locations = new_remaining
                Trace.log(f"[cleanRobotManage] Updated remaining locations: "
                          f"source={source_name}, target={target_name}, "
                          f"remaining={self.remaining_step_locations}")

    def _handle_cancel_order(self, args: Dict[str, Any]):
        self._cancel_current_order()

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
        if "entrance" in args:
            self.current_entrance = args["entrance"]
        if "exit" in args:
            self.current_exit = args["exit"]
        if "startPos" in args:
            self.current_start_pos = args["startPos"]

    def _handle_wash_start(self, args: Dict[str, Any]):
        self.mech_status = self.call_mech(
            "WashStart",
            brush_power=args.get("brush_power"),
            suck_power=args.get("suck_power"),
            jet_power=args.get("jet_power"),
            auto_adjust_power=args.get("auto_adjust_power"),
        )

    def _handle_wash_end(self):
        self.mech_status = self.call_mech("WashEnd")

    def _handle_dust_start(self):
        self.mech_status = self.call_mech("DustStart")

    def _handle_dust_end(self):
        self.mech_status = self.call_mech("DustEnd")

    def _handle_charge(self):
        if self.vehicle_state == VehicleState.CLEANING:
            self._cancel_boustrophedon_path()
        self.current_task_type = TaskType.CHARGE
        self.vehicle_state = VehicleState.CHARGING
        self.call_mech("Charge")

    def _handle_add_water(self):
        if self.vehicle_state == VehicleState.CLEANING:
            self._cancel_boustrophedon_path()
        self.current_task_type = TaskType.WATER_CHANGE
        self.vehicle_state = VehicleState.ADD_WATER
        self.call_mech("AddWater")

    def _handle_run_clean_path(self):
        self.current_task_type = TaskType.CLEAN
        self.vehicle_state = VehicleState.CLEANING

        self.current_entrance = Navigation.moveTask().get("sourceName", None)
        self.current_exit = Navigation.moveTask().get("targetName", None)

        print(f"-----{self.current_exit=}")
        print(f"-----{self.saved_exit_id=}")
        print(f"-----{self.have_cancelled=}")

        #TODO:绘制电子图方便理解
        if not self.saved_exit_id:
            self.run_clean_path()

        else:
            if self.have_cancelled:
                print(f"---------run_exit_path")
                self.run_exit_path() # self.have_cancelled重置
            elif self.saved_exit_id != self.current_exit and self.current_exit != "":
                print(f"---------run_cross_path")
                self.run_cross_path()
            elif self.saved_exit_id == self.current_exit:
                print(f"---------run_remaining_path")
                self.run_remaining_path() # self.saved_exit_id重置
            else:
                print(f"---------run_no_path")
                Module.setStatus(ScriptStatus.FAILED)
    def _handle_cancel_clean_path(self):
        """处理取消清洁路径"""
        # TODO:写一下指向逻辑
        self.cancel_count = self.cancel_count + 1
        if self.cancel_count > 5:
            self.cancel_once = False

        if self.vehicle_state == VehicleState.CLEANING:
            self.saved_exit_id = self.current_exit
            Trace.log(f"Saved exit id when canceling clean path = {self.saved_exit_id}")
            self.pos = self._cancel_boustrophedon_path()

            Trace.log(f"[cleanRobotManage] Clean path cancelled, position={self.pos}")
            self.have_cancelled = True
            Module.setStatus(ScriptStatus.FINISHED)

    def _handle_reset_clean_path(self):
        """处理重置清洁路径"""
        self._reset_boustrophedon_path()
        print("reset clean path")
        self.cancel_once = True
        self.cancel_count = 0
        self.have_cancelled = False
        self.saved_exit_id = None
        # 同时清除原始站点列表和剩余站点列表
        self.original_step_locations = []
        self.remaining_step_locations = []
        Module.setStatus(ScriptStatus.FINISHED)

    def _handle_set_task(self, args: Dict[str, Any]):
        self.current_task = args
        self.current_task_type = TaskType.CLEAN
        # 初始化区域状态
        Trace.log(f"[cleanRobotManage] New task set: {args.get('step_locations', [])}")

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
            "brush_power": brush_power,
            "suck_power": suck_power,
            "jet_power": jet_power,
            "auto_adjust_power": auto_adjust_power,
            "push_rod_length": push_rod_length,
        }
        Trace.log(f"[cleanRobotManage] call_mech -> {args}")

        # 重置机构状态并调用
        self.mech.reset_state()
        return self.mech.run(args)

    def get_water_levels(self) -> Tuple[float, float]:
        """从机构获取水位信息"""
        return self.mech.get_water_levels()

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

        self.current_task = task
        self.current_task_type = TaskType.CLEAN

        # 初始化区域状态

        payload = self.build_clean_order_json(task)
        Trace.log(f"[cleanRobotManage] Dispatching clean task")
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id
        self.erp_state = ERPState.TASK_RUNNING

    def build_clean_order_json(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """构造清洁任务运单（简化版：不再判断CA前缀）"""
        step_locations = task.get("step_locations", [])
        robot_name = task.get("robot_name", ROBOT_NAME)
        priority = task.get("priority", 50)

        steps = []
        for i, location in enumerate(step_locations):
            is_last_step = (i == len(step_locations) - 1)
            step = {
                "location": location,
                "rbkArgs": {},
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
                "location": CHARGING_SITE,
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
                "location": CHARGING_SITE,
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

        self.current_entrance = Navigation.moveTask().get("sourceName", None)
        self.current_exit = Navigation.moveTask().get("targetName", None)

        if self.run_clean_path_init:
            self.run_clean_path_init = False
            # Navigation.resetBoustrophedonPath()

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
        # start_pos = self.current_start_pos if self.current_start_pos else []
        start_pos = [self.pos['x'], self.pos['y'], self.pos['angle']] if self.pos else []

        Trace.log(f"entrance={self.current_entrance}, exit={self.current_exit}, "
                  f"startPos={start_pos}, params={params}")

        # 调用goBoustrophedonPath
        status_value = Navigation.goBoustrophedonPath(
            self.current_entrance,
            self.current_exit,
            start_pos,
            {}
        )
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)

        # 清除startPos，避免重复使用
        if self.current_start_pos:
            self.current_start_pos = None

        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            self.pos = {}
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath finished for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            self.cancel_once = True
            self.cancel_count = 0
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath failed for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            self.cancel_once = True
            self.cancel_count = 0
            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            Trace.log("[cleanRobotManage] goBoustrophedonPath suspended")
            return

    def run_clean_path_and_wash(self, args: Dict[str, Any]):
        """
                执行弓字形清洁路径

                调用 Navigation.goBoustrophedonPath(area, entrance, exit, startPos, params)
                - startPos 为空时从头开始，有值时从指定位置断点续扫
                """
        self.current_entrance = Navigation.moveTask().get("sourceName", None)
        self.current_exit = Navigation.moveTask().get("targetName", None)

        if self.run_clean_path_init:
            self.run_clean_path_init = False
            # Navigation.resetBoustrophedonPath()

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
        # start_pos = self.current_start_pos if self.current_start_pos else []
        start_pos = [self.pos['x'], self.pos['y'], self.pos['angle']] if self.pos else []

        Trace.log(f"entrance={self.current_entrance}, exit={self.current_exit}, "
                  f"startPos={start_pos}, params={params}")

        # 调用goBoustrophedonPath
        status_value = Navigation.goBoustrophedonPath(
            self.current_entrance,
            self.current_exit,
            start_pos,
            {}
        )
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)

        # 清除startPos，避免重复使用
        if self.current_start_pos:
            self.current_start_pos = None

        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            self.call_mech(
                "WashStart",
                brush_power=args.get("brush_power"),
                suck_power=args.get("suck_power"),
                jet_power=args.get("jet_power"),
                auto_adjust_power=args.get("auto_adjust_power"),
            )
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath finished for area  which entr {self.current_entrance}")
            self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goBoustrophedonPath failed for area  which entr {self.current_entrance}")
            self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            self.call_mech("WashEnd")
            Trace.log("[cleanRobotManage] goBoustrophedonPath suspended")
            return

    def run_cross_path(self):
        """
                执行横穿清洁区域路径

                调用 Navigation.goCrossArea(entrance, exit, params)
        """

        self.current_entrance = Navigation.moveTask().get("sourceName", None)
        self.current_exit = Navigation.moveTask().get("targetName", None)

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

        Trace.log(f"entrance={self.current_entrance}, exit={self.current_exit}, params={params}")

        # 调用goBoustrophedonPath
        status_value = Navigation.goCrossArea(
            self.current_entrance,
            self.current_exit,
            {}
        )
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)

        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goCrossArea finished for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            self.cancel_once = True
            self.cancel_count = 0
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goCrossArea failed for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            self.cancel_once = True
            self.cancel_count = 0
            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            Trace.log("[cleanRobotManage] goCrossArea suspended")
            return

    def run_exit_path(self):
        """
                cancel完后走到出口

                调用 Navigation.goExitPoint(entrance, exit, params)
        """

        self.current_entrance = Navigation.moveTask().get("sourceName", None)
        self.current_exit = Navigation.moveTask().get("targetName", None)

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

        # Trace.log(f"entrance={self.current_entrance}, exit={self.current_exit}, params={params}")

        # 调用goBoustrophedonPath
        status_value = Navigation.goExitPoint(
            self.current_entrance,
            self.current_exit,
            {}
        )
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)

        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goExitPoint finished for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            self.cancel_once = True
            self.cancel_count = 0
            self.have_cancelled = False
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goExitPoint failed for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            self.cancel_once = True
            self.cancel_count = 0
            Module.setStatus(ScriptStatus.FAILED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.SUSPENDED:
            Trace.log("[cleanRobotManage] goExitPoint suspended")
            return

    def run_remaining_path(self):
        """
                执行清洁区域剩余路径

                调用 Navigation.goCrossArea(entrance, exit, params)
        """

        self.current_entrance = ""
        self.current_exit = Navigation.moveTask().get("targetName", None)

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

        Trace.log(f"entrance={self.current_entrance}, exit={self.current_exit}, params={params}")

        # 调用goBoustrophedonPath
        status_value = Navigation.goRemainingPath(
            self.current_entrance,
            self.current_exit,
            {}
        )
        self.boustrophedon_path_state = BoustrophedonPathState(status_value)

        # 处理状态
        if self.boustrophedon_path_state in (BoustrophedonPathState.INIT, BoustrophedonPathState.RUNNING):
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FINISHED:
            Trace.log(f"[cleanRobotManage] goRemainingPath finished for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            Navigation.resetBoustrophedonPath()
            self.cancel_once = True
            self.cancel_count = 0
            self.saved_exit_id = ""
            Module.setStatus(ScriptStatus.FINISHED)
            return

        if self.boustrophedon_path_state == BoustrophedonPathState.FAILED:
            Trace.log(f"[cleanRobotManage] goRemainingPath failed for area which exit {self.current_exit}")
            # self.call_mech("WashEnd")
            self.vehicle_state = VehicleState.IDLE
            self.current_task_type = TaskType.NONE
            self.erp_state = ERPState.ERROR
            self.cancel_once = True
            self.cancel_count = 0
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

    # ============================================================
    #  电量监控
    # ============================================================

    def check_battery(self):
        soc = Battery.getPercentage()
        if soc < 0:
            return

        if soc <= LOW_BATTERY_SOC and not self.auto_charge_sent:
            Trace.log(f"[cleanRobotManage] Low battery ({soc}), interrupting for charge")

            if self.current_task_type == TaskType.CLEAN:
                if not self._interrupt_clean_for_priority_task("charge"):
                    return

            #发送前往充电点运单
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
    #  每日定时清洁任务
    # ============================================================

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

        # 检查是否有配置的站点
        if not config_params.scheduled_clean_locations:
            Trace.log(f"[cleanRobotManage] haven't set up the scheduled clean locations, won't send clean task")
            return

        # 获取当前时间
        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_hour = now.hour
        current_minute = now.minute
        print(f"current_time: {current_date} , {current_hour} , {current_minute}")

        # 检查是否跨天，重置触发标记
        if self.last_scheduled_clean_date != current_date:
            self.scheduled_clean_triggered_today = False
            self.last_scheduled_clean_date = current_date

        # 如果今天已经触发过，跳过
        if self.scheduled_clean_triggered_today:
            return

        # 检查是否到达触发时间
        target_hour = config_params.scheduled_clean_hour
        target_minute = config_params.scheduled_clean_minute

        if current_hour == target_hour and current_minute >= target_minute:
            # 检查是否可以发送任务（空闲状态）
            if not self.can_dispatch_to_m4():
                Trace.log(
                    f"[cleanRobotManage] Scheduled clean time reached but cannot dispatch (erp_state={self.erp_state.name})")
                return

            # 检查是否有正在执行的任务
            if self.current_task is not None:
                Trace.log("[cleanRobotManage] Scheduled clean time reached but task is running")
                return

            # 触发定时清洁任务
            self._send_scheduled_clean_task()
            self.scheduled_clean_triggered_today = True
            Trace.log(f"[cleanRobotManage] Scheduled clean task triggered at {current_hour:02d}:{current_minute:02d}")

    def _send_scheduled_clean_task(self):
        """
        发送每日定时清洁任务
        """
        step_locations = config_params.scheduled_clean_locations

        Trace.log(f"[cleanRobotManage] Sending scheduled clean task: {step_locations}")

        # 构造任务数据
        task = {
            "step_locations": step_locations,
            "robot_name": ROBOT_NAME,
            "priority": 50,  # 定时任务使用中等优先级
            "task_id": f"scheduled_clean_{int(time.time())}"
        }

        self.current_task = task
        self.current_task_type = TaskType.CLEAN

        # 初始化区域状态

        # 构造并发送运单
        payload = self._build_simple_order(
            step_locations=step_locations,
            robot_name=ROBOT_NAME,
            priority=50
        )
        order_id = self.post_to_scheduler(payload)
        self.current_order_id = order_id
        self.erp_state = ERPState.TASK_RUNNING

        Trace.log(f"[cleanRobotManage] Scheduled clean order sent: {order_id}")

    # ============================================================
    #  上报信息
    # ============================================================

    def update_report_info(self):
        soc = Battery.getPercentage()

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

            # 任务队列
            "roboshop_schedule_count": len(self.roboshop_schedule),

            # 当前路径
            "current_entrance": self.current_entrance,
            "current_exit": self.current_exit,
            "current_start_pos": self.current_start_pos,

            # 当前导航目标点
            "current_nav_target": self.current_nav_target,

            # 原始站点列表（用于断点续传）
            "original_step_locations": self.original_step_locations,
            "remaining_step_locations": self.remaining_step_locations,

            # 区域状态

            # 当前任务
            "current_task_id": self.current_task.get("task_id", "") if self.current_task else "",
            "current_task_step": 0,  # 原 current_step_index 从未被更新，始终为 0
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
    - main循环中持续调用 _update_remaining_locations() 根据 Navigation.moveTask() 更新剩余站点
    - 当机器人从 AP2 前往 AP3 时 (source_name="AP2", target_name="AP3")
      remaining_step_locations 会更新为 ["AP2", "AP3", "AP4", "AP5"]
    - SendContinueOrders 直接使用 remaining_step_locations 发送运单
    - 这样中断后恢复时，不会重复走已经经过的站点
    """

    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    validator = ParamValidator(InputParams.builder.toDict())
    mgr = CleanRobotManage()

    while True:
        status = Module.getStatus()
        print(f"---------------status{status}")

        # ============================================================
        # 每日定时清洁任务检查（每天8:00触发）
        # ============================================================
        mgr.check_scheduled_clean_task()
        # 获取当前时间
        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_hour = now.hour
        current_minute = now.minute
        print(f"current_time: {current_date} , {current_hour} , {current_minute}")

        # ============================================================
        # 2. 机构周期性运行（更新液位等）
        # ============================================================
        # 说明：周期性更新机构状态、液位数据，并同步到RBK
        mgr.mech.period_run()

        # ============================================================
        # 2.5 持续更新剩余站点列表（用于断点续传）
        # ============================================================
        # 说明：通过 Navigation.moveTask() 获取当前导航状态，
        #       根据 source_name 实时更新 remaining_step_locations
        #       这样中断后重新发送运单时，不会重复走过的站点
        mgr._update_remaining_locations()

        # ============================================================
        # 3. 同步水位信息到管理类
        # ============================================================
        mgr.clean_water_level, mgr.waste_water_level = mgr.get_water_levels()

        # ============================================================
        # 4. 水位监控 - 污水满检测
        # ============================================================
        # 说明：当污水液位超过 max_waste_water_level 阈值时，
        #       需要中断当前清洁任务，去充电桩排污
        #
        # 处理流程：
        #   1. 调用 _interrupt_clean_for_priority_task("water_change") 中断清洁任务
        #      该函数内部会：
        #      - 保存断点信息（任务数据、当前位置、导航目标等）
        #      - 关闭清洁机构 (调用 call_mech("WashEnd"))
        #      - 取消当前运单 (调用 _cancel_current_order())
        #      - 取消弓字形路径 (调用 _cancel_boustrophedon_path()，即 CancelCleanPath)
        #   2. 发送换水运单到 M4 调度系统
        #   3. 更新状态机
        if mgr.waste_water_level > config_params.max_waste_water_level:
            # 只有在执行清洁任务且尚未发送换水运单时才处理
            if mgr.current_task_type == TaskType.CLEAN and not mgr.auto_water_sent:
                Trace.log(
                    f"[cleanRobotManage] Waste water full ({mgr.waste_water_level}%), interrupting for water change")

                # 中断当前清洁任务并保存断点
                if mgr._interrupt_clean_for_priority_task("water_change"):
                    # 构造并发送换水运单
                    payload = mgr.build_water_order_json()
                    order_id = mgr.post_to_scheduler(payload)

                    # 更新状态
                    mgr.current_order_id = order_id
                    mgr.auto_water_sent = True  # 标记已发送，防止重复发送
                    mgr.current_task_type = TaskType.WATER_CHANGE
                    mgr.vehicle_state = VehicleState.ADD_WATER
                    mgr.erp_state = ERPState.TASK_RUNNING

                    Trace.log(f"[cleanRobotManage] Water change order sent (waste water full), order_id={order_id}")

        # ============================================================
        # 5. 水位监控 - 清水不足检测
        # ============================================================
        # 说明：当清水液位低于 min_clean_water_level 阈值时，
        #       需要中断当前清洁任务，去充电桩加水
        #
        # 处理流程与污水满检测相同
        #TODO:可以和上面污水水位检测合并
        elif mgr.clean_water_level < config_params.min_clean_water_level and mgr.clean_water_level != -1:
            # 只有在执行清洁任务且尚未发送换水运单时才处理
            # 注意：clean_water_level == -1 表示传感器未初始化，不处理
            if mgr.current_task_type == TaskType.CLEAN and not mgr.auto_water_sent:
                Trace.log(
                    f"[cleanRobotManage] Clean water low ({mgr.clean_water_level}%), interrupting for water change")

                # 中断当前清洁任务并保存断点
                if mgr._interrupt_clean_for_priority_task("water_change"):
                    # 构造并发送换水运单
                    payload = mgr.build_water_order_json()
                    order_id = mgr.post_to_scheduler(payload)

                    # 更新状态
                    mgr.current_order_id = order_id
                    mgr.auto_water_sent = True
                    mgr.current_task_type = TaskType.WATER_CHANGE
                    mgr.vehicle_state = VehicleState.ADD_WATER
                    mgr.erp_state = ERPState.TASK_RUNNING

                    Trace.log(f"[cleanRobotManage] Water change order sent (clean water low), order_id={order_id}")

        # ============================================================
        # 6. 电量监控（自动充电）
        # ============================================================
        # 说明：check_battery() 内部会：
        #   - 检测电量是否低于 LOW_BATTERY_SOC (20%)
        #   - 如果低于阈值且正在执行清洁任务：
        #     1. 调用 _interrupt_clean_for_priority_task("charge") 中断清洁
        #     2. 发送充电运单
        #   - 检测电量是否高于 HIGH_BATTERY_SOC (90%)
        #   - 如果高于阈值，重置 auto_charge_sent 标记
        mgr.check_battery()

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
        mgr._handle_emc(emc_status)

        # ============================================================
        # 8. 检查是否可以恢复清洁任务（充电/换水完成后）
        # ============================================================
        # 说明：_check_and_resume_clean_task() 会：
        #   1. 检查是否有保存的断点 (clean_checkpoint.has_checkpoint())
        #   2. 检查 ERP 状态是否为 IDLE（当前无任务执行）
        #   3. 根据中断原因检查恢复条件：
        #      - charge: 电量 >= HIGH_BATTERY_SOC (90%)
        #      - water_change: 清水满 且 污水空
        #   4. 如果满足条件，调用 _resume_clean_task_from_checkpoint() 恢复任务
        #
        # 恢复任务时会：
        #   - 计算恢复起点（从目标点的前一个站点开始）
        #   - 构造恢复任务（剩余站点列表）
        #   - 发送恢复运单到 M4 调度系统
        #   - 清除断点信息
        #TODO:这部分可能是无用的，可以删除
        mgr._check_and_resume_clean_task()

        # ============================================================
        # 9. 更新ERP状态机
        # ============================================================
        # 说明：检查任务完成情况，自动切换状态
        #   - TASK_RUNNING -> IDLE: 当任务完成时
        #   - ERROR: 需要人工干预，不自动转换
        # TODO:erp相关需要检查后删除
        mgr._erp_state_update()

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

        # ============================================================
        # 11. 派发定时清洁任务
        # ============================================================
        # 说明：从任务队列中取出到期的任务并发送到 M4 调度系统
        #   - 只有在 can_dispatch_to_m4() 返回 True 时才派发
        #   - 即 ERP 状态为 IDLE
        # TODO:此部分内容检查后可以删除
        if mgr.can_dispatch_to_m4():
            mgr.dispatch_clean_task_if_needed()

        if status in (ScriptStatus.RUNNING, ScriptStatus.NONE):
            input_params = Module.getTaskArgs()
            print("task args:", json.dumps(input_params, indent=2))
            validated_params = {}
            if input_params:
                try:
                    # 验证参数
                    validated_params = param_loader.loadInput(input_params)
                    print("check ok, args:", json.dumps(validated_params, indent=2))
                except ValueError as e:
                    print("check error:", e)
                    Abnormal.setTask(53780, f"Input error:{e}", "some input params are not valid",
                                     "check the input params", "input check")
            print(f"validated_params={validated_params}")
            mgr.run(validated_params)
            # 机构周期性运行（更新液位等）
            mgr.mech.period_run()
            soc = Battery.getPercentage()
            # 同步水位信息到管理类
            mgr.clean_water_level, mgr.waste_water_level = mgr.get_water_levels()
            print(f"{mgr.clean_water_level=},{mgr.waste_water_level=}")
            print(f"{soc=}")

        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            mgr.mech.reset_state()

        # ============================================================
        # 12. 更新并上报状态信息
        # ============================================================
        # 说明：
        # - update_report_info() 收集所有状态信息到 report_info 字典
        # - Module.reportInfo() 将状态信息上报给系统
        # - 上报的信息包括：状态机状态、电池水位、任务进度、断点信息等
        mgr.update_report_info()
        time.sleep(0.1)
        Module.reportInfo(mgr.report_info)
        time.sleep(0.1)


if __name__ == "__main__":
    main()