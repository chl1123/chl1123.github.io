# -*- coding: utf-8 -*-
# @Date: 2025/12/24
# @Author: zengweibin & xukeyi
# @File: actions.py
# @Update: 支持功能说明，机器人底盘单独旋转，托盘单独旋转，机器人和托盘同时旋转，顶升功能

import math
import time
from enum import Enum, IntEnum

from syspy import (Module, Di, Motor, Navigation, Loc, ScriptStatus, Trace,
                   ActionBase, ActionTask, ActionStatus)
from syspy.lib.module import ModuleBase
from syspy.utils.param_server import ParamBuilder, ParamType, ScriptParam
param_loader = ScriptParam(__file__)
from syspy.lib.robot import RobotParam
from syspy.utils import ScriptType


LOG_NAME = "actions"
MOTION_EPS = 1e-6
OMNI_CHASSIS_TYPES = {  # 支持全向运动的底盘类型
    "multipleDifferentialSteers",
    "multiStandardAndDifferentialSteers",
    "multiSteers",
    "omni",
    "quadruped",
    "wheeledLeggedQuadruped",
}


class RotateDirection(IntEnum):
    """旋转方向枚举"""
    NEARBY = 0
    COUNTERCLOCKWISE = 1
    CLOCKWISE = -1


class ShelfCoordinateAxis(str, Enum):
    """托盘角度坐标系枚举。

    `ROBOT`:
    `shelfRotateAngle` 表示机器人坐标系下的托盘目标角。

    `WORLD`:
    `shelfRotateAngle` 表示世界坐标系下的托盘目标角。

    `INCREMENTAL`:
    `shelfRotateAngle` 表示相对当前托盘角的增量角。
    """
    ROBOT = "robotSpinAngle"
    WORLD = "globalSpinAngle"
    INCREMENTAL = "increaseSpinAngle"


_FRAME_TYPE_VALUE_TO_AXIS = {
    "robot": ShelfCoordinateAxis.ROBOT,
    ShelfCoordinateAxis.ROBOT.value: ShelfCoordinateAxis.ROBOT,
    "world": ShelfCoordinateAxis.WORLD,
    ShelfCoordinateAxis.WORLD.value: ShelfCoordinateAxis.WORLD,
    "spin": ShelfCoordinateAxis.INCREMENTAL,
    ShelfCoordinateAxis.INCREMENTAL.value: ShelfCoordinateAxis.INCREMENTAL,
}
_AXIS_VALUE_TO_FRAME_TYPE = {
    ShelfCoordinateAxis.ROBOT.value: "robot",
    ShelfCoordinateAxis.WORLD.value: "world",
    ShelfCoordinateAxis.INCREMENTAL.value: "spin",
}


class LocMode(IntEnum):
    """运动定位模式枚举。"""
    ODO = 0
    LOC = 1


def _trace_log(msg: str, name: str = LOG_NAME) -> None:
    Trace.log(msg, name=name)


def _trace_dict(msg: dict, name: str, output_console: bool = False) -> None:
    Trace.log(msg, output_console=output_console, name=name)


def _normalize_angle_rad(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))

def _set_if_not_none(target: dict, key: str, value, transform=None) -> None:
    if value is None:
        return
    target[key] = transform(value) if transform else value


def _deg_to_rad_or_none(value):
    if value is None:
        return None
    return math.radians(float(value))


def _format_exception(exc: Exception) -> str:
    detail = str(exc).strip()
    if detail:
        return f"{exc.__class__.__name__}: {detail}"
    return exc.__class__.__name__


def _parse_frame_type(value):
    if value is None:
        return None
    text = str(value).strip()
    axis = _FRAME_TYPE_VALUE_TO_AXIS.get(text)
    if axis is not None:
        return axis
    lower_text = text.lower()
    axis = _FRAME_TYPE_VALUE_TO_AXIS.get(lower_text)
    if axis is not None:
        return axis
    raise ValueError(f"invalid frameType: {value}")


def _normalize_frame_type_value(value):
    if value is None:
        return None
    text = str(value).strip()
    axis = _FRAME_TYPE_VALUE_TO_AXIS.get(text)
    if axis is None:
        axis = _FRAME_TYPE_VALUE_TO_AXIS.get(text.lower())
    if axis is not None:
        return _AXIS_VALUE_TO_FRAME_TYPE.get(axis.value, text)
    return text


def _parse_rotate_direction(value):
    if value is None:
        return None
    return RotateDirection(int(value))


def _parse_loc_mode(value):
    if value is None:
        return LocMode.ODO
    return LocMode(int(value))

def _normalize_motion_status(status):
    # TODO(seer): 当前部分运动接口首拍会返回 INIT，导致 ActionTask 可能出现
    # RUNNING -> INIT -> RUNNING 的状态回跳。这里先在 actions.py 内做兼容，
    # 后续应在 syspy/lib/action_task.py 中收敛状态机，避免 RUNNING 之后再次回到 INIT。
    if status == ActionStatus.INIT:
        return ActionStatus.RUNNING
    return status


def _normalize_legacy_task_args(task_args: dict) -> dict:
    """将旧版 operation / 字段映射到当前脚本协议。"""
    raw = dict(task_args or {})
    normalized = dict(raw)
    updates = {}
    operation = raw.get("operation")

    if raw.get("frameType") is not None:
        updates["frameType"] = _normalize_frame_type_value(raw.get("frameType"))
    elif raw.get("coordinateAxis") is not None:
        updates["frameType"] = _normalize_frame_type_value(raw.get("coordinateAxis"))

    frame_type = updates.get("frameType", raw.get("frameType"))

    if operation == "line":
        updates["operation"] = "robotLine"
    elif operation == "arc":
        updates["operation"] = "robotArc"
    elif operation == "rotate":
        robot_rotate_angle = raw.get("robotRotateAngle")
        robot_target_angle = raw.get("robotTargetAngle")
        robot_delta_angle = raw.get("robotDeltaAngle")
        rotate_target_mode = raw.get("rotateTargetMode")
        legacy_incremental_rotate = bool(raw.get("isDebug")) == True
        shelf_rotate_angle = raw.get("shelfRotateAngle")
        has_lift = raw.get("liftHeight") is not None

        if robot_rotate_angle is None and robot_target_angle is not None:
            updates["robotRotateAngle"] = robot_target_angle
            robot_rotate_angle = robot_target_angle

        is_incremental_rotate = (
            robot_delta_angle is not None
            or rotate_target_mode == 1
            or (rotate_target_mode is not None and int(rotate_target_mode) == 1)
            # legacy `isDebug=true + robotRotateAngle` 本质是“机器人增量旋转”入口
            or (legacy_incremental_rotate and robot_rotate_angle is not None)
        )

        if is_incremental_rotate:
            angle_value = robot_delta_angle if robot_delta_angle is not None else robot_rotate_angle
            if frame_type == "world":
                updates["operation"] = "rotate"
                if robot_rotate_angle is None and angle_value is not None:
                    updates["robotRotateAngle"] = angle_value
            else:
                updates["operation"] = "robotRotate"
                if angle_value is not None:
                    updates["angle"] = abs(float(angle_value))
                if raw.get("robotRotateDirection") is not None:
                    updates["direction"] = raw.get("robotRotateDirection")
                if raw.get("robotRotateSpeed") is not None:
                    updates["vw"] = raw.get("robotRotateSpeed")
                if frame_type is None:
                    updates["frameType"] = "robot"
                    frame_type = "robot"
                if frame_type not in (None, "robot"):
                    updates["_compatErrorKey"] = "robotRotateFrameTypeUnsupported"
                    updates["_compatErrorDesc"] = "robotRotate only supports frameType=robot; use rotate for frameType=world"
                elif shelf_rotate_angle is not None:
                    updates["_compatErrorKey"] = "shelfRotateNotAllowedInDebug"
                    updates["_compatErrorDesc"] = (
                        "robotRotateAngle + isDebug=true is legacy chassis incremental rotation; "
                        "shelfRotateAngle must be omitted in this combination"
                    )
        elif robot_rotate_angle is None and shelf_rotate_angle is not None and not has_lift:
            updates["operation"] = "spinRotate"
            updates["angle"] = shelf_rotate_angle
            if raw.get("shelfRotateDirection") is not None:
                updates["direction"] = raw.get("shelfRotateDirection")
        else:
            updates["operation"] = "rotate"
    elif operation == "robotRotate":
        if raw.get("angle") is None and raw.get("robotRotateAngle") is not None:
            updates["angle"] = raw.get("robotRotateAngle")
        if raw.get("direction") is None and raw.get("robotRotateDirection") is not None:
            updates["direction"] = raw.get("robotRotateDirection")
        if raw.get("vw") is None and raw.get("robotRotateSpeed") is not None:
            updates["vw"] = raw.get("robotRotateSpeed")
        frame_type = updates.get("frameType", raw.get("frameType"))
        angle_value = updates.get("angle", raw.get("angle"))
        direction_value = updates.get("direction", raw.get("direction"))
        speed_value = updates.get("vw", raw.get("vw"))
        if frame_type == "world":
            normalized.pop("angle", None)
            normalized.pop("direction", None)
            normalized.pop("vw", None)
            normalized.pop("mode", None)
            updates.pop("angle", None)
            updates.pop("direction", None)
            updates.pop("vw", None)
            updates.pop("mode", None)
            updates["operation"] = "rotate"
            if angle_value is not None:
                updates["robotRotateAngle"] = angle_value
            if direction_value is not None:
                updates["robotRotateDirection"] = direction_value
            if speed_value is not None:
                updates["robotRotateSpeed"] = speed_value
    elif operation == "spinRotate":
        if raw.get("angle") is None and raw.get("shelfRotateAngle") is not None:
            updates["angle"] = raw.get("shelfRotateAngle")
        if raw.get("direction") is None and raw.get("shelfRotateDirection") is not None:
            updates["direction"] = raw.get("shelfRotateDirection")

    if updates:
        normalized.update(updates)
    if updates:
        _trace_dict(
            {
                "event": "legacyArgsNormalized",
                "legacyArgs": task_args,
                "normalizedArgs": normalized,
            },
            name=f"{LOG_NAME}.legacy_args",
        )
    return normalized


def _get_nav_defaults(keys: list[str], log_name: str) -> dict:
    has_goods = bool(Navigation.hasGoods())
    state_key = "load" if has_goods else "unload"
    path_map = {}
    for key in keys:
        path_map[key] = [f"basic.{state_key}.{key}"]
    if has_goods:
        path_map["maxSpeed"].append("basic.load.loadMaxSpeed")
    if "maxRot" in path_map:
        path_map["maxRot"].append("basic.load.loadMaxRot")

    params = {}
    for key, paths in path_map.items():
        for path in paths:
            value = RobotParam.getConfig("navigation", path, default=None)
            if value is None:
                continue
            if key == "maxRot":
                params[key] = _deg_to_rad_or_none(value)
            else:
                params[key] = float(value)
            break
    _trace_log(
        f"{log_name} nav defaults ({state_key}): {params}",
        name=f"{LOG_NAME}.cfg",
    )
    return params

# --- ConfigParams 类 ---
class ConfigParams:
    """配置管理器，用于管理动态配置参数"""
    config = {}
    lift_motor_speed = None
    chassis_type = RobotParam.getDevice("Model-000", "chassisType")

    module_type = RobotParam.getDevice("Model-000", "moduleType")
    lift_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.jackMotor")
    spin_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.spinMotor")
    motor_func = RobotParam.getDevice(f"{lift_motor_name}", "func") if lift_motor_name else None

    def __init__(self):
        self._build_and_load_config()

    @classmethod
    def _build_and_load_config(cls):
        """构建并加载配置参数"""
        cls.chassis_type = RobotParam.getDevice("Model-000", "chassisType")
        module_type = RobotParam.getDevice("Model-000", "moduleType")
        lift_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.jackMotor")
        motor_func = RobotParam.getDevice(f"{lift_motor_name}", "func") if lift_motor_name else None

        builder = param_loader.builderConfig()

        with builder.GROUPS():
            with builder.GROUP(key="motorConfig", name="Motor Configuration",
                               desc="Motor related configuration parameters"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    with builder.CHILD(key="liftMotorSpeed", name="Lift Motor Speed",
                                       desc="Speed of the lift motor"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.015, min_value=0.001, max_value=0.1)
                        builder.UNIT("m/s")
                        builder.SINGLESTEP(0.001)

        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        """重新加载配置参数"""
        cls.config = param_loader.loadConfig()

# 创建全局配置管理器实例
config_params = ConfigParams()


def script_config_callback():
    _trace_log("Reloading script config parameters", name=f"{LOG_NAME}.cfg")
    config_params.reload_config()
    _trace_log(f"config loaded: {config_params.config}", name=f"{LOG_NAME}.cfg")


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        with builder.GROUP(key="operation", name="运动行为", desc="选择机器人的运动行为"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            with builder.CHILDREN():
                with builder.CHILD(key="robotLine", name="平动", desc="机器人平动"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="dist", name="直线运动距离",
                                           desc="直线运动距离，绝对值，单位 m"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("m")
                        with builder.CHILD(key="vx", name="X 方向运动速度",
                                           desc="机器人坐标系下 X 方向运动的速度，正为向前，负为向后，单位 m/s"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("m/s")
                        with builder.CHILD(key="vy", name="Y 方向运动速度",
                                           desc="机器人坐标系下 Y 方向运动的速度，正为向左，负为向右，单位 m/s"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("m/s")
                        with builder.CHILD(key="mode", name="模式选择",
                                           desc="运动模式：0 = 里程模式, 1 = 定位模式"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                with builder.CHILD(key="robotRotate", name="机器人转动", desc="机器人增量转动"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="angle", name="转动角度",
                                           desc="机器人坐标系下的增量转动角度，单位度"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("°")
                        with builder.CHILD(key="vw", name="转动角速度",
                                           desc="机器人转动角速度，单位度每秒；正为逆时针，负为顺时针"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("°/s")
                        with builder.CHILD(key="direction", name="转动方向",
                                           desc="机器人转动方向：-1 顺时针 0 自主选择 1 逆时针"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                        with builder.CHILD(key="frameType", name="坐标系",
                                           desc="机器人角度坐标系：robot = 机器人坐标系增量角，world = 世界坐标系目标角（内部走 rotate 分支）"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE("robot")
                            with builder.CHILDREN():
                                with builder.CHILD(key="robot", name="robot",
                                                   desc="机器人坐标系增量角"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD(key="world", name="world",
                                                   desc="世界坐标系目标角，内部走 rotate 分支"):
                                    builder.TYPE(ParamType.STRING)
                        with builder.CHILD(key="mode", name="模式选择",
                                           desc="运动模式：0 = 里程模式, 1 = 定位模式"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                with builder.CHILD(key="spinRotate", name="托盘转动", desc="托盘独立转动"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="angle", name="托盘旋转角度",
                                           desc="托盘旋转角度，单位度"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("°")
                        with builder.CHILD(key="direction", name="托盘旋转方向",
                                           desc="托盘旋转方向：-1 顺时针 0 自主选择 1 逆时针"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                        with builder.CHILD(key="frameType", name="坐标系",
                                           desc="托盘角度坐标系：robot = 机器人坐标系绝对角，world = 世界坐标系绝对角，spin = 相对当前托盘角的增量"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE("robot")
                            with builder.CHILDREN():
                                with builder.CHILD(key="robot", name="robot",
                                                   desc="机器人坐标系绝对角"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD(key="world", name="world",
                                                   desc="世界坐标系绝对角"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD(key="spin", name="spin",
                                                   desc="相对当前托盘角的增量"):
                                    builder.TYPE(ParamType.STRING)
                with builder.CHILD(key="rotate", name="组合旋转", desc="机器人绝对旋转或机器人与托盘同时旋转"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="robotRotateAngle", name="Robot Rotate Angle",
                                           desc="机器人在世界坐标系下的目标角度，单位度"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("°")
                        with builder.CHILD(key="robotRotateDirection", name="Robot Rotate Direction",
                                           desc="机器人旋转方向：-1 顺时针 0 自主选择 1 逆时针"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                        with builder.CHILD(key="robotRotateSpeed", name="Robot Rotate Speed",
                                           desc="机器人旋转角速度，单位度每秒"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("°/s")
                        with builder.CHILD(key="shelfRotateAngle", name="Shelf Rotate Angle",
                                           desc="托盘旋转角度；组合旋转时仅支持机器人坐标系绝对角，单位度"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("°")
                        with builder.CHILD(key="shelfRotateDirection", name="Shelf Rotate Direction",
                                           desc="托盘旋转方向：-1 顺时针 0 自主选择 1 逆时针"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                        with builder.CHILD(key="frameType", name="坐标系",
                                           desc="托盘角度坐标系；组合旋转时仅支持 robot"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE("robot")
                            with builder.CHILDREN():
                                with builder.CHILD(key="robot", name="robot",
                                                   desc="机器人坐标系绝对角"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD(key="world", name="world",
                                                   desc="世界坐标系绝对角"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD(key="spin", name="spin",
                                                   desc="相对当前托盘角的增量"):
                                    builder.TYPE(ParamType.STRING)
                        with builder.CHILD(key="liftHeight", name="Lift Height",
                                           desc="升降高度，模型文件中的第一个线性电机"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("m")
                            builder.SINGLESTEP(0.01)
                        with builder.CHILD(key="recFile", name="Rec File",
                                           desc="货物模型文件"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE("default.srec")
                with builder.CHILD(key="robotArc", name="圆弧运动", desc="选择机器人圆弧运动"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="rotRadius", name="圆弧运动半径",
                                        desc="圆弧运动的半径"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("m")
                        with builder.CHILD(key="rotDegree", name="圆弧运动角度",
                                        desc="圆弧运动的角度"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(True)
                            builder.UNIT("°")
                        with builder.CHILD(key="rotSpeed", name="圆弧运动速度",
                                        desc="圆弧运动的导航速度"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("rad/s")
                        with builder.CHILD(key="mode", name="模式选择",
                                        desc="定位模式：0 = 里程模式, 1 = 定位模式"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)

    builder.save()

class ActionPlanner:
    """将任务参数转换为可执行动作列表。"""

    def __init__(self, task_args: dict, lift_stop_di: int):
        self.task_args = task_args
        self.lift_stop_di = lift_stop_di
        self.script_status = ScriptStatus.RUNNING

    def build(self):
        if self._check_device_prerequisites():
            return []
        compat_error_key = self.task_args.get("_compatErrorKey")
        compat_error_desc = self.task_args.get("_compatErrorDesc")
        if compat_error_key and compat_error_desc:
            raise ActionBuildError(compat_error_key, compat_error_desc)

        operation = self.task_args.get("operation")
        _trace_log(f"normalized operation: {operation or 'unknown'}", name=f"{LOG_NAME}.task")

        if operation == "robotLine":
            return self._build_robot_line_actions()
        if operation == "robotRotate":
            return self._build_robot_rotate_actions()
        if operation == "spinRotate":
            return self._build_spin_rotate_actions()
        if operation == "rotate":
            return self._build_rotate_actions()
        if operation == "robotArc":
            return self._build_arc_actions()

        self._fail(
            "operationNotSupported",
            f"operation {operation} not support",
        )
        return []

    def _check_device_prerequisites(self) -> bool:
        spin_requested = (
            self.task_args.get("operation") == "spinRotate"
            or self.task_args.get("shelfRotateAngle") is not None
        )
        if config_params.spin_motor_name is None and spin_requested:
            _trace_log(
                "spinMotorLost: shelf rotation requested but spin motor is not configured",
                name=f"{LOG_NAME}.err",
            )
            Navigation.setDeviceError(
                "spinMotorLost",
                "The tray spin motor is missing, this abnormality is caused by incorrect robot model configuration, please check the robot model configuration to fix this problem",
            )
            self.script_status = ScriptStatus.FAILED
            return True

        if config_params.lift_motor_name is None and self.task_args.get("liftHeight") is not None:
            _trace_log(
                "liftMotorNotFound: lift requested but lift motor is not configured",
                name=f"{LOG_NAME}.err",
            )
            Navigation.setDeviceError(
                "liftMotorNotFound",
                "Lift motor (linear) not found, cause: device not detected, solution: check robot model configuration and perform motor check",
            )
            self.script_status = ScriptStatus.FAILED
            return True
        return False

    def _build_robot_line_actions(self):
        return [RobotLineActionBuilder(self.task_args).build()]

    def _build_robot_rotate_actions(self):
        return [RobotRotateActionBuilder(self.task_args).build()]

    def _build_spin_rotate_actions(self):
        return [SpinRotateActionBuilder(self.task_args).build()]

    def _build_rotate_actions(self):
        return RotateActionBuilder(self.task_args, self.lift_stop_di).build()

    def _build_arc_actions(self):
        return [ArcActionBuilder(self.task_args).build()]

    def _fail(self, key: str, desc: str) -> None:
        Navigation.setTaskError(key, desc)
        self.script_status = ScriptStatus.FAILED
        _trace_log(f"{key}: {desc}", name=f"{LOG_NAME}.err")


class RobotLineActionBuilder:
    """构建 robotLine 动作。"""

    def __init__(self, task_args: dict):
        self.task_args = task_args

    def build(self):
        dist = self.task_args.get("dist", None)
        if dist is None:
            raise ActionBuildError(
                "missingLineDist",
                "robotLine requires dist",
            )
        move_dist = abs(float(dist))
        if move_dist <= MOTION_EPS:
            raise ActionBuildError(
                "lineDistInvalid",
                "robotLine requires dist to be non-zero",
            )

        vx = self.task_args.get("vx", None)
        vy = self.task_args.get("vy", None)
        mode = _parse_loc_mode(self.task_args.get("mode", None))

        speed_x = None if vx is None else float(vx)
        speed_y = None if vy is None else float(vy)
        if config_params.chassis_type not in OMNI_CHASSIS_TYPES:
            abs_vx = 0.0 if vx is None else abs(float(vx))
            abs_vy = 0.0 if vy is None else abs(float(vy))
            if abs_vy > MOTION_EPS and abs_vx <= MOTION_EPS:
                raise ActionBuildError(
                    "lateralMoveUnsupported",
                    f"chassisType {config_params.chassis_type} does not support lateral motion",
                )

        if speed_x is None and speed_y is None:
            line_defaults = _get_nav_defaults(["maxSpeed"], "line")
            speed_x = line_defaults.get("maxSpeed")

        vx_value = 0.0 if speed_x is None else float(speed_x)
        vy_value = 0.0 if speed_y is None else float(speed_y)
        if abs(vx_value) <= MOTION_EPS and abs(vy_value) <= MOTION_EPS:
            raise ActionBuildError(
                "lineSpeedInvalid",
                "robotLine requires vx or vy to be non-zero",
            )

        return GoLineByOdo(
            move_dist=move_dist,
            speed_x=speed_x,
            speed_y=speed_y,
            mode=mode,
        )


class RobotRotateActionBuilder:
    """构建 robotRotate 动作。"""

    def __init__(self, task_args: dict):
        self.task_args = task_args

    def build(self):
        angle = self.task_args.get("angle", None)
        if angle is None:
            raise ActionBuildError(
                "missingRobotRotateAngle",
                "robotRotate requires angle",
            )
        angle_deg = float(angle)
        if abs(angle_deg) <= MOTION_EPS:
            raise ActionBuildError(
                "robotRotateAngleInvalid",
                "robotRotate requires angle to be non-zero",
            )

        direction = _parse_rotate_direction(self.task_args.get("direction", None))
        vw = self.task_args.get("vw", None)
        speed_w_deg = None if vw is None else float(vw)
        frame_type = _normalize_frame_type_value(self.task_args.get("frameType", None))

        if frame_type not in (None, "robot"):
            raise ActionBuildError(
                "robotRotateFrameTypeUnsupported",
                "robotRotate only supports frameType=robot; use rotate for frameType=world",
            )

        if direction is None:
            if speed_w_deg is None:
                raise ActionBuildError(
                    "robotRotateDirectionRequired",
                    "robotRotate requires direction or vw",
                )
            if abs(speed_w_deg) <= MOTION_EPS:
                raise ActionBuildError(
                    "robotRotateDirectionRequired",
                    "robotRotate requires direction when vw is zero",
                )
            direction = (
                RotateDirection.COUNTERCLOCKWISE
                if speed_w_deg > 0
                else RotateDirection.CLOCKWISE
            )

        return GoRobotRotateByOdo(
            angle_deg=angle_deg,
            direction=direction,
            speed_w_deg=speed_w_deg,
            mode=_parse_loc_mode(self.task_args.get("mode", None)),
        )


class SpinRotateActionBuilder:
    """构建 spinRotate 动作。"""

    def __init__(self, task_args: dict):
        self.task_args = task_args

    def build(self):
        angle = self.task_args.get("angle", None)
        if angle is None:
            raise ActionBuildError(
                "missingShelfRotateAngle",
                "spinRotate requires angle",
            )

        direction = _parse_rotate_direction(
            self.task_args.get("direction", RotateDirection.NEARBY)
        )
        frame_type = _parse_frame_type(self.task_args.get("frameType", None))
        return SpinRotateAction(
            angle_deg=float(angle),
            direction=direction,
            frame_type=frame_type,
        )


class RotateActionBuilder:
    """构建 rotate 动作。"""

    def __init__(self, task_args: dict, lift_stop_di: int):
        self.task_args = task_args
        self.lift_stop_di = lift_stop_di

    def build(self):
        robot_rotate_angle = self.task_args.get("robotRotateAngle", None)
        robot_rotate_speed = self.task_args.get("robotRotateSpeed", None)
        robot_rotate_direction = self._resolve_robot_direction(robot_rotate_speed)
        shelf_rotate_angle = self.task_args.get("shelfRotateAngle", None)
        shelf_rotate_direction = _parse_rotate_direction(
            self.task_args.get("shelfRotateDirection", RotateDirection.NEARBY)
        )
        frame_type = _parse_frame_type(self.task_args.get("frameType", None))
        lift_height = self.task_args.get("liftHeight", None)
        lift_speed = self.task_args.get("lift_speed", None)
        rec_file = self.task_args.get("recFile", None)

        if robot_rotate_angle is None and shelf_rotate_angle is None and lift_height is None:
            raise ActionBuildError(
                "missingActionParams",
                "No action parameters provided Set rotation angle or lift height Parameter validation",
            )

        actions = []
        if robot_rotate_angle is not None:
            if shelf_rotate_angle is not None and frame_type not in (None, ShelfCoordinateAxis.ROBOT):
                raise ActionBuildError(
                    "rotateCoordinateUnsupported",
                    "rotate with robotRotateAngle and shelfRotateAngle only supports frameType=robot",
                )
            actions.append(
                RunRotateMoveAction(
                    robot_rotate_angle=robot_rotate_angle,
                    robot_direction=robot_rotate_direction,
                    robot_rotate_speed_deg=robot_rotate_speed,
                    shelf_angle=shelf_rotate_angle,
                    shelf_direction=shelf_rotate_direction,
                )
            )
        elif shelf_rotate_angle is not None:
            raise ActionBuildError(
                "rotateShelfOnlyUnsupported",
                "rotate does not support shelf-only rotation; use spinRotate instead",
            )

        if lift_height is not None:
            actions.append(
                Jack(
                    config_params.lift_motor_name,
                    lift_height,
                    lift_speed,
                    self.lift_stop_di,
                    rec_file,
                )
            )
        return actions

    def _resolve_robot_direction(self, robot_rotate_speed):
        robot_rotate_direction = _parse_rotate_direction(
            self.task_args.get("robotRotateDirection", None)
        )
        if self.task_args.get("robotRotateAngle") is None:
            return robot_rotate_direction
        if robot_rotate_direction is not None:
            return robot_rotate_direction
        if robot_rotate_speed is None:
            return RotateDirection.NEARBY
        if float(robot_rotate_speed) > 0:
            return RotateDirection.COUNTERCLOCKWISE
        if float(robot_rotate_speed) < 0:
            return RotateDirection.CLOCKWISE
        return RotateDirection.NEARBY

class ArcActionBuilder:
    """构建圆弧动作。"""

    def __init__(self, task_args: dict):
        self.task_args = task_args

    def build(self):
        radius = self.task_args.get("rotRadius", None)
        angle = self.task_args.get("rotDegree", None)
        speed = self.task_args.get("rotSpeed", None)
        return GoArc(
            radius,
            angle,
            speed,
            _parse_loc_mode(self.task_args.get("mode", None)),
        )


class ActionBuildError(Exception):
    def __init__(self, key: str, desc: str):
        super().__init__(desc)
        self.key = key
        self.desc = desc


# --- 主控制类 ---
class Actions(ModuleBase):
    """动作控制主类，只负责生命周期管理和动作编排。"""

    def __init__(self):
        super().__init__()
        self.task_args = {}
        self.script_status = ScriptStatus.NONE
        self.action_task = ActionTask(mod=LOG_NAME)

        self.lift_stop_di = -1

        # 电机状态
        self.lift_pos = None
        self.lift_pos_init = None
        self.shelf_pos = None
        self.shelf_pos_init = None

        # 获取电机初始位置
        if config_params.lift_motor_name:
            self.lift_pos_init = Motor.getMotorPos(config_params.lift_motor_name)
        if config_params.spin_motor_name:
            self.shelf_pos_init = Motor.getMotorPos(config_params.spin_motor_name)
        Navigation.clearDeviceError('spinMotorLost')
        Navigation.clearDeviceError('liftMotorNotFound')

    def set_status(self, new_status: ScriptStatus) -> None:
        """统一状态切换入口，避免重复状态日志。"""
        if self.script_status == new_status:
            return
        prev_name = ScriptStatus(self.script_status).name
        next_name = ScriptStatus(new_status).name
        _trace_log(f"status {prev_name} -> {next_name}", name=f"{LOG_NAME}.task")
        self.script_status = new_status

    def init_task(self, args: dict) -> None:
        """初始化任务参数并装配动作队列。"""
        self.task_args = dict(args or {})
        planner = ActionPlanner(self.task_args, self.lift_stop_di)
        try:
            actions = planner.build()
        except ActionBuildError as exc:
            self._fail_task(exc.key, exc.desc)
            return
        except Exception as exc:
            self._fail_task(
                "actionPlanBuildFailed",
                f"unexpected error while building action plan: {_format_exception(exc)}",
            )
            return

        if planner.script_status == ScriptStatus.FAILED:
            self.set_status(ScriptStatus.FAILED)
            return
        if not actions:
            self._fail_task(
                "emptyActionPlan",
                "planner did not generate executable actions",
            )
            return

        _trace_log(
            f"task start operation={self.task_args.get('operation', 'unknown')} task_id={Module.getTaskId()}",
            name=f"{LOG_NAME}.task",
        )
        self.action_task.build(actions)
        self.set_status(ScriptStatus.RUNNING)

    def _fail_task(self, key: str, desc: str) -> None:
        Navigation.setTaskError(key, desc)
        if self.action_task.status in (ActionStatus.RUNNING, ActionStatus.SUSPENDED):
            self.action_task.cancel(reason=desc)
        self.set_status(ScriptStatus.FAILED)
        _trace_log(f"{key}: {desc}", name=f"{LOG_NAME}.err")

    def suspend(self):
        if self.script_status == ScriptStatus.RUNNING:
            self.action_task.suspend()
            self.set_status(ScriptStatus.SUSPENDED)

    def resume(self):
        if self.script_status == ScriptStatus.SUSPENDED:
            self.action_task.resume()
            self.set_status(ScriptStatus.RUNNING)

    def cancel(self):
        self.action_task.cancel()
        self.set_status(ScriptStatus.FAILED)
        _trace_log("task cancelled", name=f"{LOG_NAME}.task")

    def run(self):
        """推进当前动作队列。"""
        try:
            self.action_task.step(self)
            if self.action_task.is_done:
                if self.action_task.status == ActionStatus.FAILED:
                    self.set_status(ScriptStatus.FAILED)
                else:
                    self.set_status(ScriptStatus.FINISHED)
        except Exception as exc:
            self._fail_task(
                "actionRuntimeUnexpected",
                f"unexpected error while running actions: {_format_exception(exc)}",
            )
        return self.script_status

    def reset_task_state(self) -> None:
        """单次任务结束后复位，继续驻留等待下一次任务。"""
        self.action_task.reset()
        self.task_args = {}
        self.set_status(ScriptStatus.NONE)

# --- 动作定义 ---
class Jack(ActionBase):
    """顶升动作"""

    def __init__(self, motor_name: str, height: float, speed=None, stop_di="", rec_file=None):
        super().__init__("Jack")
        self.motor_name = motor_name
        self.height = height
        self.speed = speed
        self.stop_di = stop_di
        self.rec_file = rec_file

    def reset(self):
        super().reset()
        if self.motor_name:
            return
        self.action_status = ActionStatus.FAILED
        Navigation.setDeviceError(
            "liftMotorNotFound",
            "Lift motor not found Check motor configuration Motor check",
        )

    def run(self, a: Actions):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        Motor.setMotorPosition(self.motor_name, self.height, self.speed, str(self.stop_di))
        if Motor.isMotorReached(self.motor_name) or (self.stop_di >= 0 and Di.getDi(self.stop_di)):
            if self.height > 0:
                if self.rec_file:
                    Navigation.setLocalShelfArea(self.rec_file)
            else:
                Navigation.resetLocalShelfArea()
            self.action_status = ActionStatus.FINISHED
        return self.action_status


class RunRotateMoveAction(ActionBase):
    """使用 runRotateMove 执行机器人绝对旋转或机器人与托盘组合旋转。"""

    def __init__(self, robot_rotate_angle, robot_direction=RotateDirection.NEARBY,
                 robot_rotate_speed_deg=None, shelf_angle=None, shelf_direction=RotateDirection.NEARBY):
        super().__init__("RunRotateMoveAction")
        self.robot_direction = robot_direction
        self.shelf_direction = shelf_direction
        self.robot_rotate_speed_deg = None if robot_rotate_speed_deg is None else float(robot_rotate_speed_deg)
        self.robot_rotate_angle_rad = None if robot_rotate_angle is None else math.radians(float(robot_rotate_angle))
        self.shelf_angle_rad = None if shelf_angle is None else math.radians(float(shelf_angle))
        self.rparams = None
        self.sparams = None

    def reset(self):
        super().reset()
        Navigation.resetRotateMove()
        self.rparams = None
        self.sparams = None
        if self.robot_rotate_angle_rad is None:
            self.action_status = ActionStatus.FAILED
            Navigation.setTaskError(
                "missingRobotRotateAngle",
                "rotate requires robotRotateAngle",
            )
            return

        self.rparams = {}
        self.rparams.update(_get_nav_defaults(["maxSpeed", "maxRot"], "rotate"))
        self.rparams["moveAngle"] = _normalize_angle_rad(self.robot_rotate_angle_rad)
        self.rparams["dir"] = self.robot_direction.value
        if self.robot_rotate_speed_deg is not None:
            self.rparams["speedW"] = abs(math.radians(self.robot_rotate_speed_deg))
        else:
            _set_if_not_none(self.rparams, "speedW", self.rparams.get("maxRot"), math.fabs)

        if self.shelf_angle_rad is not None:
            self.sparams = {
                "angle": self.shelf_angle_rad,
                "dir": self.shelf_direction.value,
            }
        _trace_log(f"rparams: {self.rparams}, sparams: {self.sparams}", name=f"{LOG_NAME}.task")

    def cancel(self):
        Navigation.resetRotateMove()
        super().cancel()

    def run(self, a: Actions):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        self.action_status = _normalize_motion_status(Navigation.runRotateMove(
            robot_params=self.rparams,
            shelf_params=self.sparams,
        ))
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            Navigation.resetRotateMove()
        return self.action_status


class SpinRotateAction(ActionBase):
    """使用 set*SpinAngle 执行托盘旋转。"""

    def __init__(self, angle_deg=None, direction=RotateDirection.NEARBY, frame_type=None):
        super().__init__("SpinRotateAction")
        self.direction = direction
        self.frame_type = frame_type if frame_type is not None else ShelfCoordinateAxis.ROBOT
        self.angle_rad = None if angle_deg is None else math.radians(float(angle_deg))

    def reset(self):
        super().reset()
        if self.angle_rad is None:
            self.action_status = ActionStatus.FAILED
            Navigation.setTaskError(
                "missingShelfRotateAngle",
                "spinRotate requires angle",
            )
            return
        if self.frame_type == ShelfCoordinateAxis.ROBOT:
            _trace_log("setRobotSpinAngle", name=f"{LOG_NAME}.task")
            Navigation.setRobotSpinAngle(self.angle_rad, self.direction.value)
        elif self.frame_type == ShelfCoordinateAxis.WORLD:
            _trace_log("setGlobalSpinAngle", name=f"{LOG_NAME}.task")
            Navigation.setGlobalSpinAngle(self.angle_rad, self.direction.value)
        else:
            _trace_log("setIncreaseSpinAngle", name=f"{LOG_NAME}.task")
            Navigation.setIncreaseSpinAngle(self.angle_rad)

    def run(self, a: Actions):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        if Navigation.spinRun():
            self.action_status = ActionStatus.FINISHED
        return self.action_status


class GoLineByOdo(ActionBase):
    """使用里程接口执行直线/平移运动"""

    def __init__(self, move_dist: float, speed_x=None, speed_y=None, mode=LocMode.ODO):
        super().__init__("GoLineByOdo")
        self.move_dist = move_dist
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.mode = mode
        self.params = None

    def reset(self):
        super().reset()
        Navigation.resetOdoMove()
        self.params = {
            "moveDist": float(self.move_dist),
            "locMode": self.mode.value,
            "actionName": "GoLineByOdo",
        }
        _set_if_not_none(self.params, "speedX", self.speed_x, float)
        _set_if_not_none(self.params, "speedY", self.speed_y, float)
        _trace_log(f"odo move start params={self.params}", name=f"{LOG_NAME}.nav")

    def cancel(self):
        Navigation.resetOdoMove()
        super().cancel()

    def run(self, j: Actions):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        self.action_status = _normalize_motion_status(Navigation.runOdoMove(self.params))
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            Navigation.resetOdoMove()

        return self.action_status


class GoRobotRotateByOdo(ActionBase):
    """使用 runOdoMove 执行机器人增量转动。"""

    def __init__(self, angle_deg, direction=RotateDirection.NEARBY, speed_w_deg=None, mode=LocMode.ODO):
        super().__init__("GoRobotRotateByOdo")
        self.angle_deg = float(angle_deg)
        self.direction = direction
        self.speed_w_deg = None if speed_w_deg is None else float(speed_w_deg)
        self.mode = mode
        self.params = None

    def reset(self):
        super().reset()
        Navigation.resetOdoMove()
        if abs(self.angle_deg) <= MOTION_EPS:
            self.action_status = ActionStatus.FAILED
            Navigation.setTaskError(
                "robotRotateAngleInvalid",
                "robotRotate requires angle to be non-zero",
            )
            return

        self.params = {
            "moveAngle": math.radians(abs(self.angle_deg)),
            "locMode": self.mode.value,
            "actionName": self.action_name,
        }
        rotate_defaults = _get_nav_defaults(["maxSpeed", "maxRot"], "robotRotate")
        speed_w = None
        if self.speed_w_deg is not None:
            speed_w = abs(math.radians(self.speed_w_deg))
        else:
            default_rot = rotate_defaults.get("maxRot")
            if default_rot is not None:
                speed_w = abs(default_rot)

        if speed_w is not None:
            if self.direction == RotateDirection.CLOCKWISE:
                speed_w = -speed_w
            elif self.direction == RotateDirection.NEARBY and self.angle_deg < 0:
                speed_w = -speed_w
            self.params["speedW"] = speed_w
        _trace_log(f"odo move start params={self.params}", name=f"{LOG_NAME}.nav")

    def cancel(self):
        Navigation.resetOdoMove()
        super().cancel()

    def run(self, a: Actions):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        self.action_status = _normalize_motion_status(Navigation.runOdoMove(self.params))
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            Navigation.resetOdoMove()
        return self.action_status


class GoArc(ActionBase):
    """圆弧走到指定点"""
    
    def __init__(self, radius, angle, speed, mode=LocMode.ODO):
        super().__init__("GoArc")
        self.radius = radius
        self.angle = angle
        self.speed = speed
        self.mode = mode
        self.params = None

    def reset(self):
        super().reset()
        Navigation.resetOdoMove()
        self.params = {
            "locMode": self.mode.value,
            "rotDegree": float(self.angle),
            "rotRadius": float(self.radius),
            "actionName": self.action_name,
        }
        _set_if_not_none(self.params, "rotSpeed", self.speed, float)
        _trace_log(f"arc move start params={self.params}", name=f"{LOG_NAME}.nav")

    def cancel(self):
        Navigation.resetOdoMove()
        super().cancel()

    def run(self, j: Actions):
        if self.action_status != ActionStatus.RUNNING:
            return self.action_status
        self.action_status = _normalize_motion_status(Navigation.runOdoMove(self.params))
        if self.action_status in (ActionStatus.FINISHED, ActionStatus.FAILED):
            Navigation.resetOdoMove()

        return self.action_status

def main():
    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init(script_type=ScriptType.TASK)
    a = Actions()

    while True:
        status = a.script_status
        Module.setStatus(status)

        if status == ScriptStatus.NONE:
            input_params = Module.getTaskArgs()
            if input_params:
                try:
                    normalized_params = _normalize_legacy_task_args(input_params)
                    validated_params = param_loader.loadInput(normalized_params)
                    for key, value in normalized_params.items():
                        validated_params.setdefault(key, value)
                    a.init_task(validated_params)
                except ValueError as e:
                    _trace_log(f"check error: {e}", name=f"{LOG_NAME}.err")
                    Navigation.setTaskError(
                        "invalidInputParams",
                        f"Input error: {e} Some input params are not valid Check the input params Input validation"
                    )
                    a.set_status(ScriptStatus.FAILED)
        elif status == ScriptStatus.RUNNING:
            a.run()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            _trace_log(f"task cycle end status={ScriptStatus(status).name}", name=f"{LOG_NAME}.task")
            break
        time.sleep(0.1)

if __name__ == '__main__':
    main()
