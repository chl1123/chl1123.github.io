# -*- coding: utf-8 -*-
# @Date: 2025/12/24
# @Author: zengweibin & xukeyi
# @File: actions.py
# @Update: 支持功能说明，机器人底盘单独旋转，托盘单独旋转，机器人和托盘同时旋转，顶升功能

import json
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


class RotateTargetMode(IntEnum):
    """底盘旋转目标模式枚举。

    `ABSOLUTE`:
    `robotTargetAngle` 表示世界坐标系下的底盘目标朝向。

    `INCREMENTAL`:
    `robotDeltaAngle` 表示相对当前底盘朝向的增量角。
    """
    ABSOLUTE = 0
    INCREMENTAL = 1


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

def _normalize_increment_angle_deg(angle_deg: float) -> float:
    angle_deg = math.fmod(float(angle_deg), 360.0)
    if angle_deg > 180.0:
        angle_deg -= 360.0
    elif angle_deg < -180.0:
        angle_deg += 360.0
    if abs(angle_deg) == 180.0:
        return 180.0 if angle_deg > 0 else -180.0
    if abs(angle_deg) < 1e-9:
        return 0.0
    return angle_deg

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


def _parse_coordinate_axis(value):
    if value is None:
        return None
    return ShelfCoordinateAxis(value)


def _parse_rotate_direction(value):
    if value is None:
        return None
    return RotateDirection(int(value))


def _parse_rotate_target_mode(value):
    if value is None:
        return RotateTargetMode.ABSOLUTE
    return RotateTargetMode(int(value))


def _parse_loc_mode(value):
    if value is None:
        return LocMode.ODO
    return LocMode(int(value))


def _normalize_legacy_task_args(task_args: dict) -> dict:
    """将旧版下发字段轻量映射到当前脚本字段。"""
    normalized = dict(task_args or {})
    updates = {}
    is_legacy_debug_rotate = False

    if "robotRotateAngle" in normalized:
        legacy_angle = normalized.get("robotRotateAngle")
        if legacy_angle is not None:
            rotate_target_mode = normalized.get("rotateTargetMode")
            if rotate_target_mode is None and bool(normalized.get("isDebug")) == True:
                # 地图调试窗口旧协议：isDebug 固定为 True，表示底盘增量旋转。
                rotate_target_mode = RotateTargetMode.INCREMENTAL
                updates["rotateTargetMode"] = int(rotate_target_mode)
            else:
                rotate_target_mode = _parse_rotate_target_mode(rotate_target_mode)

            if rotate_target_mode == RotateTargetMode.ABSOLUTE and "robotTargetAngle" not in normalized:
                updates["robotTargetAngle"] = legacy_angle
            if rotate_target_mode == RotateTargetMode.INCREMENTAL and "robotDeltaAngle" not in normalized:
                updates["robotDeltaAngle"] = legacy_angle
                if (
                    bool(normalized.get("isDebug")) == True
                    and normalized.get("operation") == "rotate"
                    and "robotRotateDirection" not in normalized
                ):
                    is_legacy_debug_rotate = True

    if "isDebug" in normalized and "robotRotateDirection" not in normalized:
        legacy_speed = normalized.get("robotRotateSpeed")
        if legacy_speed is not None:
            if float(legacy_speed) > 0:
                updates["robotRotateDirection"] = int(RotateDirection.COUNTERCLOCKWISE)
            elif float(legacy_speed) < 0:
                updates["robotRotateDirection"] = int(RotateDirection.CLOCKWISE)

    if updates:
        normalized.update(updates)
    if is_legacy_debug_rotate:
        normalized["_legacyDebugRotate"] = True
    if updates or is_legacy_debug_rotate:
        _trace_dict(
            {
                "event": "legacyArgsNormalized",
                "legacyArgs": task_args,
                "normalizedArgs": normalized,
            },
            name=f"{LOG_NAME}.legacy_args",
        )
    return normalized


def _is_legacy_debug_rotate(task_args: dict) -> bool:
    return bool(task_args.get("_legacyDebugRotate"))


def _get_rotate_nav_defaults() -> dict:
    has_goods = bool(Navigation.hasGoods())
    state_key = "load" if has_goods else "unload"
    path_map = {
        "maxSpeed": [f"basic.{state_key}.maxSpeed"],
        "maxRot": [f"basic.{state_key}.maxRot"],
    }
    if has_goods:
        path_map["maxSpeed"].append("basic.load.loadMaxSpeed")
        path_map["maxRot"].append("basic.load.loadMaxRot")

    params = {}
    for key, paths in path_map.items():
        for path in paths:
            value = RobotParam.getConfig("navigation", path, default=None)
            value = _deg_to_rad_or_none(value) if key == "maxRot" else float(value) if value is not None else None
            if value is not None:
                params[key] = value
                break
    _trace_log(
        f"rotate nav defaults ({state_key}): {params}",
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
        with builder.GROUP(key="operation", name="运动行为",desc="选择机器人的运动行为"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            with builder.CHILDREN():
                with builder.CHILD(key="rotate", name="旋转", desc="选择机器人旋转"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        # 底盘旋转角度
                        with builder.CHILD(key="robotTargetAngle", name="Robot Target Angle",
                                        desc="底盘绝对目标角，机器人在世界坐标系下的目标角度，单位°"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("°")
                            builder.SINGLESTEP(1)

                        with builder.CHILD(key="robotDeltaAngle", name="Robot Delta Angle",
                                        desc="底盘增量角，基于当前底盘角度增量旋转，单位°，正数逆时针，负数顺时针"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("°")
                            builder.SINGLESTEP(1)

                        # 底盘旋转角速度
                        with builder.CHILD(key="robotRotateSpeed", name="Robot Rotate Speed",
                                        desc="底盘旋转的速度，单位°/s"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                        
                        with builder.CHILD(key='robotRotateDirection', name='Robot Rotate Direction',
                                        desc='底盘旋转方向：-1 顺时针 0 自主选择 1 逆时针；不填时根据角速度正负自动推导'):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE(0)

                        # 升降高度
                        with builder.CHILD(key="liftHeight", name="Lift Height",
                                        desc="升降高度，模型文件中的第一个线性电机"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("m")
                            builder.SINGLESTEP(0.01)

                        # 托盘旋转角度
                        with builder.CHILD(key="shelfRotateAngle", name="Shelf Rotate Angle",
                                        desc="托盘旋转角度，coordinateAxis 为空或 ROBOT 时表示机器人坐标系目标角，WORLD 时表示世界坐标系目标角，INCREMENTAL 时表示相对当前托盘角的增量，单位°"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.MIN_VALUE(-180)
                            builder.MAX_VALUE(180)
                            builder.REQUIRED(False)
                            builder.UNIT("°")
                            builder.SINGLESTEP(1)

                        # 托盘旋转方向
                        with builder.CHILD(key="shelfRotateDirection", name="Shelf Rotate Direction",
                                        desc="托盘旋转方向：-1 顺时针 0 自主选择 1 逆时针"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE(1)

                        #基于哪个坐标系旋转
                        with builder.CHILD(key="coordinateAxis", name="coordinateAxis",
                                        desc="托盘角度的解释方式：空或 ROBOT = 机器人坐标系绝对角，WORLD = 世界坐标系绝对角，INCREMENTAL = 相对当前托盘角的增量"):
                            builder.TYPE(ParamType.COMBO_BOX)
                            builder.REQUIRED(False)
                            with builder.CHILDREN():
                                builder.CHILD(key=ShelfCoordinateAxis.INCREMENTAL.value, name="INCREMENTAL",desc="在当前托盘角度基础上增加一个角度, 角度为正数则逆时针旋转, 为负数顺时针旋转")
                                builder.CHILD(key=ShelfCoordinateAxis.ROBOT.value, name="ROBOT",desc="将托盘的角度转到机器人坐标系下的一个角度。spinDirection为0, 则就近转过去; spinDirection为1, 则逆时针转过去; spinDirection为-1, 则顺时针转过去")
                                builder.CHILD(key=ShelfCoordinateAxis.WORLD.value, name="WORLD",desc="将托盘的角度转到世界坐标系下的一个角度。spinDirection为0, 则就近转过去; spinDirection为1, 则逆时针转过去; spinDirection为-1, 则顺时针转过去")

                        with builder.CHILD(key="rotateTargetMode", name="Rotate Target Mode",
                                        desc="仅作用于底盘角度字段：0 = 使用 robotTargetAngle 作为世界坐标系绝对角，1 = 使用 robotDeltaAngle 作为相对当前底盘角的增量角"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE(int(RotateTargetMode.ABSOLUTE))

                        # 货物模型文件
                        with builder.CHILD(key="recFile", name="Rec File",
                                        desc="货物模型文件"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE("default.srec")
                        with builder.CHILD(key="mode", name="模式选择",
                                        desc="locMode，仅用于 runOdoMove 路径：0 = 里程模式, 1 = 定位模式"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)

            with builder.CHILDREN():
                with builder.CHILD(key="line", name="直线运动", desc="选择机器人直线运动"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="dist", name="直线运动距离",
                                        desc="直线运动的目标距离"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("m")
                        with builder.CHILD(key="vx", name="X 方向运动的速度",
                                        desc="机器人坐标系下 X 方向运动的速度, 正为向前, 负为向后, 单位: m/s"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("m/s")
                        with builder.CHILD(key="vy", name="Y 方向运动的速度",
                                        desc="机器人坐标系下 Y 方向运动的速度, 正为向右, 负为向左, 单位: m/s"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("m/s")
                        with builder.CHILD(key="mode", name="模式选择",
                                        desc="定位模式：0 = 里程模式, 1 = 定位模式"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
            with builder.CHILDREN():
                with builder.CHILD(key="arc", name="圆弧运动", desc="选择机器人圆弧运动"):
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
                                        desc="圆弧运动的速度"):
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

        operation = self.task_args.get("operation")
        _trace_log(f"normalized operation: {operation or 'unknown'}", name=f"{LOG_NAME}.task")

        if operation == "line":
            return self._build_line_actions()
        if operation == "rotate":
            return self._build_rotate_actions()
        if operation == "arc":
            return self._build_arc_actions()

        self._fail(
            "OperationNotSupported",
            f"operation {operation} not support",
        )
        return []

    def _check_device_prerequisites(self) -> bool:
        if config_params.spin_motor_name is None and self.task_args.get("shelfRotateAngle") is not None:
            _trace_log(
                "SPIN_MOTOR_LOST: shelf rotation requested but spin motor is not configured",
                name=f"{LOG_NAME}.err",
            )
            Navigation.setDeviceError(
                "SPIN_MOTOR_LOST",
                "The tray spin motor is missing, this abnormality is caused by incorrect robot model configuration, please check the robot model configuration to fix this problem",
            )
            self.script_status = ScriptStatus.FAILED
            return True

        if config_params.lift_motor_name is None and self.task_args.get("liftHeight") is not None:
            _trace_log(
                "LIFT_MOTOR_NOT_FOUND: lift requested but lift motor is not configured",
                name=f"{LOG_NAME}.err",
            )
            Navigation.setDeviceError(
                "LIFT_MOTOR_NOT_FOUND",
                "Lift motor (linear) not found, cause: device not detected, solution: check robot model configuration and perform motor check",
            )
            self.script_status = ScriptStatus.FAILED
            return True
        return False

    def _build_line_actions(self):
        return [LineActionBuilder(self.task_args).build()]

    def _build_rotate_actions(self):
        return RotateActionBuilder(self.task_args, self.lift_stop_di).build()

    def _build_arc_actions(self):
        return [ArcActionBuilder(self.task_args).build()]

    def _fail(self, key: str, desc: str) -> None:
        Navigation.setTaskError(key, desc)
        self.script_status = ScriptStatus.FAILED
        _trace_log(f"{key}: {desc}", name=f"{LOG_NAME}.err")


class LineActionBuilder:
    """构建直线/平移动作。"""

    def __init__(self, task_args: dict):
        self.task_args = task_args

    def build(self):
        dist = self.task_args.get("dist", None)
        vx = self.task_args.get("vx", None)
        vy = self.task_args.get("vy", None)
        mode = _parse_loc_mode(self.task_args.get("mode", None))

        vx_value = 0.0 if vx is None else float(vx)
        vy_value = 0.0 if vy is None else float(vy)
        speed = math.hypot(vx_value, vy_value)
        if speed <= 1e-6:
            raise ActionBuildError(
                "LineSpeedInvalid",
                "Line motion requires vx or vy to be non-zero",
            )
        if abs(vy_value) > 1e-6 and config_params.chassis_type not in OMNI_CHASSIS_TYPES:
            raise ActionBuildError(
                "LineLateralUnsupported",
                f"chassisType {config_params.chassis_type} does not support lateral motion",
            )

        return GoLineByOdo(
            move_dist=abs(float(dist)),
            speed_x=None if vx is None else float(vx),
            speed_y=None if vy is None else float(vy),
            mode=mode,
        )


class RotateActionBuilder:
    """构建底盘旋转、托盘旋转和顶升动作。"""

    def __init__(self, task_args: dict, lift_stop_di: int):
        self.task_args = task_args
        self.lift_stop_di = lift_stop_di

    def build(self):
        mode = _parse_loc_mode(self.task_args.get("mode", 0))
        rotate_target_mode = _parse_rotate_target_mode(self.task_args.get("rotateTargetMode", None))
        _trace_log(
            f"mode is {mode}, rotateTargetMode is {rotate_target_mode}",
            name=f"{LOG_NAME}.task",
        )

        robot_target_angle = self.task_args.get("robotTargetAngle")
        robot_delta_angle = self.task_args.get("robotDeltaAngle")
        if robot_target_angle is not None and robot_delta_angle is not None:
            raise ActionBuildError(
                "RobotRotateAngleConflict",
                "robotTargetAngle and robotDeltaAngle cannot both be set",
            )

        robot_rotate_angle = (
            robot_target_angle
            if rotate_target_mode == RotateTargetMode.ABSOLUTE
            else robot_delta_angle
        )
        robot_rotate_speed = self.task_args.get("robotRotateSpeed", None)
        robot_rotate_speed_rad = _deg_to_rad_or_none(robot_rotate_speed)
        robot_rotate_direction = self._resolve_robot_direction(robot_rotate_speed)
        disable_nearby_for_incremental = _is_legacy_debug_rotate(self.task_args)
        shelf_rotate_angle = self.task_args.get("shelfRotateAngle", None)
        shelf_rotate_direction = _parse_rotate_direction(
            self.task_args.get("shelfRotateDirection", RotateDirection.NEARBY)
        )
        coordinate_axis = _parse_coordinate_axis(self.task_args.get("coordinateAxis", None))
        lift_height = self.task_args.get("liftHeight", None)
        lift_speed = self.task_args.get("lift_speed", None)
        rec_file = self.task_args.get("recFile", None)

        if robot_rotate_angle is None and shelf_rotate_angle is None and lift_height is None:
            raise ActionBuildError(
                "No action parameters provided",
                "No action parameters provided Set rotation angle or lift height Parameter validation",
            )

        actions = []
        if rotate_target_mode == RotateTargetMode.ABSOLUTE:
            actions.extend(
                AbsoluteRotateBuilder(
                    mode=mode,
                    robot_target_angle=robot_rotate_angle,
                    robot_direction=robot_rotate_direction,
                    robot_rotate_speed_rad=robot_rotate_speed_rad,
                    shelf_angle=shelf_rotate_angle,
                    shelf_direction=shelf_rotate_direction,
                    coordinate_axis=coordinate_axis,
                ).build()
            )
        else:
            actions.extend(
                IncrementalRotateBuilder(
                    mode=mode,
                    robot_delta_angle=robot_rotate_angle,
                    robot_direction=robot_rotate_direction,
                    robot_rotate_speed_rad=robot_rotate_speed_rad,
                    shelf_angle=shelf_rotate_angle,
                    shelf_direction=shelf_rotate_direction,
                    coordinate_axis=coordinate_axis,
                    disable_nearby_for_incremental=disable_nearby_for_incremental,
                ).build()
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
        robot_target_angle = self.task_args.get("robotTargetAngle")
        robot_delta_angle = self.task_args.get("robotDeltaAngle")
        if robot_target_angle is None and robot_delta_angle is None:
            return robot_rotate_direction
        if robot_rotate_direction is not None:
            return robot_rotate_direction
        if robot_rotate_speed is None:
            return RotateDirection.NEARBY
        if robot_rotate_speed > 0:
            return RotateDirection.COUNTERCLOCKWISE
        if robot_rotate_speed < 0:
            return RotateDirection.CLOCKWISE
        return RotateDirection.NEARBY


class AbsoluteRotateBuilder:
    """构建绝对角旋转动作。"""

    def __init__(self, mode, robot_target_angle, robot_direction, robot_rotate_speed_rad,
                 shelf_angle, shelf_direction, coordinate_axis):
        self.mode = mode
        self.robot_target_angle = robot_target_angle
        self.robot_direction = robot_direction
        self.robot_rotate_speed_rad = robot_rotate_speed_rad
        self.shelf_angle = shelf_angle
        self.shelf_direction = shelf_direction
        self.coordinate_axis = coordinate_axis

    def build(self):
        if self.coordinate_axis == ShelfCoordinateAxis.INCREMENTAL:
            raise ActionBuildError(
                "CoordinateAxisUnsupported",
                "increaseSpinAngle only supports incremental shelf rotation",
            )
        if (self.robot_target_angle is not None
                and self.shelf_angle is not None
                and self.coordinate_axis == ShelfCoordinateAxis.WORLD):
            raise ActionBuildError(
                "CoordinateAxisUnsupported",
                "globalSpinAngle cannot be combined with robotTargetAngle in a single absolute rotate action",
            )

        if self.robot_target_angle is not None and self.shelf_angle is not None:
            return [
                AbsoluteRobotAndShelfRotate(
                    robot_target_angle=self.robot_target_angle,
                    robot_direction=self.robot_direction,
                    speed_w_robot=self.robot_rotate_speed_rad,
                    shelf_angle=self.shelf_angle,
                    shelf_direction=self.shelf_direction,
                )
            ]
        if self.robot_target_angle is not None:
            return [
                AbsoluteRobotRotate(
                    robot_target_angle=self.robot_target_angle,
                    robot_direction=self.robot_direction,
                    speed_w_robot=self.robot_rotate_speed_rad,
                    mode=self.mode,
                )
            ]
        if self.shelf_angle is not None:
            return [
                AbsoluteShelfRotate(
                    shelf_angle=self.shelf_angle,
                    shelf_direction=self.shelf_direction,
                    coordinate_axis=self.coordinate_axis,
                )
            ]
        return []


class IncrementalRotateBuilder:
    """构建增量旋转动作。"""

    def __init__(self, mode, robot_delta_angle, robot_direction, robot_rotate_speed_rad,
                 shelf_angle, shelf_direction, coordinate_axis, disable_nearby_for_incremental=False):
        self.mode = mode
        self.robot_delta_angle = robot_delta_angle
        self.robot_direction = robot_direction
        self.robot_rotate_speed_rad = robot_rotate_speed_rad
        self.shelf_angle = shelf_angle
        self.shelf_direction = shelf_direction
        self.coordinate_axis = coordinate_axis
        self.disable_nearby_for_incremental = disable_nearby_for_incremental

    def build(self):
        if self.robot_delta_angle is not None and self.coordinate_axis is not None:
            raise ActionBuildError(
                "IncrementalRotateConflict",
                "robotDeltaAngle and coordinateAxis-based shelf rotation cannot be set together",
            )

        actions = []
        if self.robot_delta_angle is not None:
            actions.append(
                RobotIncrementalRotate(
                    robot_delta_angle=self.robot_delta_angle,
                    robot_direction=self.robot_direction,
                    speed_w_robot=self.robot_rotate_speed_rad,
                    mode=self.mode,
                    disable_nearby=self.disable_nearby_for_incremental,
                )
            )
        elif self.coordinate_axis is not None or self.shelf_angle is not None:
            actions.append(
                ShelfCoordinateRotate(
                    shelf_angle=self.shelf_angle,
                    shelf_direction=self.shelf_direction,
                    coordinate_axis=self.coordinate_axis,
                )
            )
        return actions


class ArcActionBuilder:
    """构建圆弧动作。"""

    def __init__(self, task_args: dict):
        self.task_args = task_args

    def build(self):
        return GoArc(
            self.task_args.get("rotRadius", None),
            self.task_args.get("rotDegree", None),
            self.task_args.get("rotSpeed", None),
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
        self.init_args = False
        self.task_args = {}
        self.report_info = {}
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
        Navigation.clearDeviceError('SPIN_MOTOR_LOST')
        Navigation.clearDeviceError('LIFT_MOTOR_NOT_FOUND')

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
        if self.init_args:
            return

        self.init_args = True
        self.task_args = dict(args or {})
        self.report_info = {"scriptArgs": self.task_args}
        planner = ActionPlanner(self.task_args, self.lift_stop_di)
        try:
            actions = planner.build()
        except ActionBuildError as exc:
            self._fail_task(exc.key, exc.desc)
            return
        except Exception as exc:
            self._fail_task(
                "ActionPlanBuildFailed",
                f"unexpected error while building action plan: {_format_exception(exc)}",
            )
            return

        if planner.script_status == ScriptStatus.FAILED:
            self.set_status(ScriptStatus.FAILED)
            return
        if not actions:
            self._fail_task(
                "ActionPlanEmpty",
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
        self.report_info["taskError"] = {"key": key, "desc": desc}
        self.set_status(ScriptStatus.FAILED)
        _trace_log(f"{key}: {desc}", name=f"{LOG_NAME}.err")

    def _tick_report(self) -> None:
        try:
            self._update_report_info()
            Module.reportInfo(self.report_info)
        except Exception as exc:
            detail = _format_exception(exc)
            _trace_log(f"ReportInfoFailed: {detail}", name=f"{LOG_NAME}.err")

    def suspend(self):
        if self.script_status == ScriptStatus.RUNNING:
            self.action_task.suspend()
            self.set_status(ScriptStatus.SUSPENDED)

    def resume(self):
        if self.script_status == ScriptStatus.SUSPENDED:
            self.action_task.resume()
            self.set_status(ScriptStatus.RUNNING)

    def cancel(self):
        Navigation.resetOdoMove()
        Navigation.resetRotateMove()
        self.action_task.cancel()
        self.set_status(ScriptStatus.FAILED)
        _trace_log("task cancelled", name=f"{LOG_NAME}.task")

    def run(self):
        """推进当前动作队列。"""
        try:
            self.action_task.step(self)
            current_action = self.action_task.current
            if current_action:
                self.report_info["currentAction"] = current_action.action_state
            else:
                self.report_info.pop("currentAction", None)
            if self.action_task.is_done:
                if self.action_task.status == ActionStatus.FAILED:
                    self.set_status(ScriptStatus.FAILED)
                else:
                    self.set_status(ScriptStatus.FINISHED)
        except Exception as exc:
            self._fail_task(
                "ActionRuntimeUnexpected",
                f"unexpected error while running actions: {_format_exception(exc)}",
            )
        return self.script_status

    def reset_task_state(self) -> None:
        """单次任务结束后复位，继续驻留等待下一次任务。"""
        Navigation.resetOdoMove()
        Navigation.resetRotateMove()
        self.action_task.reset()
        self.init_args = False
        self.task_args = {}
        self.report_info = {}
        self.set_status(ScriptStatus.NONE)

    def _update_report_info(self):
        """更新上报信息"""
        current_robot_angle = Loc.getPose().get("yaw", 0.)
        current_action = self.action_task.current
        counts = self.action_task.status_counts()

        # 获取电机位置
        if config_params.lift_motor_name:
            self.lift_pos = Motor.getMotorPos(config_params.lift_motor_name)
        if config_params.spin_motor_name:
            self.shelf_pos = Motor.getMotorPos(config_params.spin_motor_name)

        if self.lift_pos is not None:
            self.report_info["currentLiftHeight"] = self.lift_pos
        if self.shelf_pos is not None:
            current_shelf_angle_in_robot = self.shelf_pos / math.pi * 180
            self.report_info["currentShelfAngleInRobot"] = current_shelf_angle_in_robot
            self.report_info["currentShelfAngleInWorld"] = current_robot_angle + current_shelf_angle_in_robot

        self.report_info.update({
            "actionListName": [a.__class__.__name__ for a in self.action_task.action_list],
            "actionId": current_action.action_id if current_action else "",
            "currentRobotAngle": current_robot_angle,
            "scriptStatus": int(self.script_status),
            "taskId": Module.getTaskId(),
        })

        _trace_dict(
            {
                "scriptStatus": int(self.script_status),
                "total": int(self.action_task.total),
                "runningCount": int(counts["running"]),
                "waitingCount": int(counts["init"]),
                "finishedCount": int(counts["finished"]),
                "failedCount": int(counts["failed"]),
                "suspendedCount": int(counts["suspended"]),
            },
            name=f"{LOG_NAME}.task",
        )


# --- 基础动作类 ---
class BaseAction(ActionBase):
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        super().__init__(action_name=action_name)
        self.action_args = {}
        self.init = False
        self.start_time = time.time()
        self.action_state = {}

    def run(self, a: Actions):
        """外部调用时，输出或打印实例对象的 action_state 字段"""
        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.start_time = time.time()

    def __str__(self):
        return json.dumps({"action_state": self.action_state})


class Jack(BaseAction):
    """顶升动作"""

    def __init__(self, motor_name: str, height: float, speed=None, stop_di="", rec_file=None):
        super().__init__("Jack")
        self.action_args = {
            "motorName": motor_name,
            "height": height,
            "speed": speed,
            "stopDi": stop_di,
            "recFile": rec_file
        }
        self.motor_name = motor_name
        self.height = height
        self.speed = speed
        self.stop_di = stop_di
        self.rec_file = rec_file

    def run(self, a: Actions):
        self.action_status = ActionStatus.RUNNING
        if not self.init:
            self.init = True

        if self.motor_name:
            Motor.setMotorPosition(self.motor_name, self.height, self.speed, str(self.stop_di))
            if Motor.isMotorReached(self.motor_name) or (self.stop_di >= 0 and Di.getDi(self.stop_di)):
                if self.height > 0:
                    if self.rec_file:
                        Navigation.setLocalShelfArea(self.rec_file)
                else:
                    Navigation.resetLocalShelfArea()
                self.action_status = ActionStatus.FINISHED
        else:
            self.action_status = ActionStatus.FAILED
            Navigation.setDeviceError(
                "LIFT_MOTOR_NOT_FOUND",
                "Lift motor not found Check motor configuration Motor check"
            )

        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time
        

    def reset(self):
        pass


class AbsoluteRobotRotate(BaseAction):
    """底盘绝对角旋转动作。

    坐标系对应关系:
    `robotTargetAngle` 表示世界坐标系下的底盘目标朝向。
    """

    def __init__(self, robot_target_angle=None, robot_direction=RotateDirection.NEARBY,
                 speed_w_robot=None, mode=LocMode.ODO):
        super().__init__("AbsoluteRobotRotate")
        self.action_args = {
            "mode": mode.value,
            "robotTargetAngle": robot_target_angle,
            "robotRotateDirection": robot_direction.value,
            "robotRotateSpeed": speed_w_robot,
        }
        self.mode = mode
        self.action_status = ActionStatus.INIT
        self.init = True
        self.robot_direction = robot_direction
        self.speed_w_robot = float(speed_w_robot) if speed_w_robot is not None else None
        self.robot_target_angle = None
        if robot_target_angle is not None:
            self.robot_target_angle = math.radians(robot_target_angle)
        self.rparams = None

    def run(self, a: Actions):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetRotateMove()
            Navigation.resetOdoMove()
            if self.robot_target_angle is None:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError(
                    "No rotation angle provided",
                    "Absolute robot rotation requires robotTargetAngle",
                )
                return self.action_status
            self.robot_target_angle = _normalize_angle_rad(self.robot_target_angle)
            self.rparams = {}
            self.rparams.update(_get_rotate_nav_defaults())
            self.rparams["moveAngle"] = self.robot_target_angle
            self.rparams["dir"] = self.robot_direction.value
            if self.speed_w_robot is not None:
                self.rparams["speedW"] = math.fabs(self.speed_w_robot)
            else:
                _set_if_not_none(self.rparams, "speedW", self.rparams.get("maxRot"), math.fabs)
            _trace_log(f"rparams: {self.rparams}", name=f"{LOG_NAME}.task")
        self.action_status = Navigation.runRotateMove(
            robot_params=self.rparams if self.rparams else None,
            shelf_params=None,
        )

        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['rparams'] = self.rparams
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time

        return self.action_status


class AbsoluteRobotAndShelfRotate(BaseAction):
    """底盘与托盘同时执行绝对角旋转。

    坐标系对应关系:
    `robotTargetAngle` 表示世界坐标系下的底盘目标朝向。
    `shelfRotateAngle` 表示机器人坐标系下的托盘目标角。
    """

    def __init__(self, robot_target_angle=None, robot_direction=RotateDirection.NEARBY,
                 speed_w_robot=None, shelf_angle=None, shelf_direction=RotateDirection.NEARBY):
        super().__init__("AbsoluteRobotAndShelfRotate")
        self.action_args = {
            "robotTargetAngle": robot_target_angle,
            "robotRotateDirection": robot_direction.value,
            "robotRotateSpeed": speed_w_robot,
            "shelfRotateAngle": shelf_angle,
            "shelfRotateDirection": shelf_direction.value,
        }
        self.robot_direction = robot_direction
        self.shelf_direction = shelf_direction
        self.speed_w_robot = float(speed_w_robot) if speed_w_robot is not None else None
        self.robot_target_angle = None if robot_target_angle is None else math.radians(robot_target_angle)
        self.shelf_angle = None if shelf_angle is None else math.radians(shelf_angle)
        self.rparams = None
        self.sparams = None
        self.init = True

    def run(self, a: Actions):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetRotateMove()
            Navigation.resetOdoMove()
            if self.robot_target_angle is None or self.shelf_angle is None:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError(
                    "No rotation angle provided",
                    "Combined absolute rotation requires robotTargetAngle and shelfRotateAngle",
                )
                return self.action_status

            self.robot_target_angle = _normalize_angle_rad(self.robot_target_angle)
            self.rparams = {}
            self.rparams.update(_get_rotate_nav_defaults())
            self.rparams["moveAngle"] = self.robot_target_angle
            self.rparams["dir"] = self.robot_direction.value
            if self.speed_w_robot is not None:
                self.rparams["speedW"] = math.fabs(self.speed_w_robot)
            else:
                _set_if_not_none(self.rparams, "speedW", self.rparams.get("maxRot"), math.fabs)

            self.sparams = {
                "angle": self.shelf_angle,
                "dir": self.shelf_direction.value,
            }
            _trace_log(f"rparams: {self.rparams}, sparams: {self.sparams}", name=f"{LOG_NAME}.task")

        self.action_status = Navigation.runRotateMove(
            robot_params=self.rparams,
            shelf_params=self.sparams,
        )

        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['rparams'] = self.rparams
        self.action_state['sparams'] = self.sparams
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time

        return self.action_status


class AbsoluteShelfRotate(BaseAction):
    """托盘绝对角旋转动作。

    坐标系对应关系:
    `coordinateAxis == ShelfCoordinateAxis.WORLD` 时，`shelfRotateAngle` 表示世界坐标系下的托盘目标角。
    `coordinateAxis == ShelfCoordinateAxis.ROBOT` 或不带 `coordinateAxis` 时，`shelfRotateAngle` 表示机器人坐标系下的托盘目标角。
    """

    def __init__(self, shelf_angle=None, shelf_direction=RotateDirection.NEARBY, coordinate_axis=None):
        super().__init__("AbsoluteShelfRotate")
        if coordinate_axis is None:
            coordinate_axis = ShelfCoordinateAxis.ROBOT
        self.action_args = {
            "shelfRotateAngle": shelf_angle,
            "shelfRotateDirection": shelf_direction.value,
            "coordinateAxis": coordinate_axis.value,
        }
        self.shelf_direction = shelf_direction
        self.coordinate_axis = coordinate_axis
        self.action_status = ActionStatus.INIT
        self.init = True
        self.shelf_angle = None
        if shelf_angle is not None:
            self.shelf_angle = math.radians(shelf_angle)

    def run(self, a: Actions):
        if self.init:
            Navigation.resetRotateMove()
            Navigation.resetOdoMove()
            self.init = False
            self.action_status = ActionStatus.RUNNING
            if self.shelf_angle is None:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError(
                    "No rotation angle provided",
                    "Absolute shelf rotation requires shelfRotateAngle",
                )
                return self.action_status

            if self.coordinate_axis == ShelfCoordinateAxis.ROBOT:
                _trace_log("setRobotSpinAngle", name=f"{LOG_NAME}.task")
                Navigation.setRobotSpinAngle(self.shelf_angle, self.shelf_direction.value)
            elif self.coordinate_axis == ShelfCoordinateAxis.WORLD:
                _trace_log("setGlobalSpinAngle", name=f"{LOG_NAME}.task")
                Navigation.setGlobalSpinAngle(self.shelf_angle, self.shelf_direction.value)
            else:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError(
                    "CoordinateAxisUnsupported",
                    f"coordinateAxis {self.coordinate_axis.value} not support in absolute shelf rotation",
                )
                return self.action_status

        if Navigation.spinRun():
            self.action_status = ActionStatus.FINISHED

        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time

        return self.action_status


class RobotIncrementalRotate(BaseAction):
    """底盘增量旋转动作。

    坐标系对应关系:
    `robotDeltaAngle`: 相对当前底盘朝向的增量角。
    该动作只处理底盘，不处理托盘坐标系旋转。
    """

    def __init__(self, robot_delta_angle=None, robot_direction=RotateDirection.NEARBY,
                 speed_w_robot=None, mode=LocMode.ODO, disable_nearby=False):
        super().__init__("RobotIncrementalRotate")
        self.action_args = {
            "mode": mode.value,
            "robotDeltaAngle": robot_delta_angle,
            "robotRotateDirection": robot_direction.value,
            "robotRotateSpeed": speed_w_robot,
            "disableNearby": disable_nearby,
        }
        self.mode = mode
        self.robot_direction = robot_direction
        self.speed_w_robot = float(speed_w_robot) if speed_w_robot is not None else None
        self.disable_nearby = disable_nearby
        self.action_status = ActionStatus.INIT
        self.init = True
        self.rparams = None

        self.robot_delta_angle_deg = None
        if robot_delta_angle is not None:
            self.robot_delta_angle_deg = float(robot_delta_angle)

    def run(self, j: Actions):
        if self.init:
            Navigation.resetRotateMove()
            Navigation.resetOdoMove()
            self.init = False
            self.action_status = ActionStatus.RUNNING
            self.rparams = {}
            if self.robot_delta_angle_deg is None:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError(
                    "No rotation angle provided",
                    "Incremental robot rotation requires robotDeltaAngle"
                )
                return self.action_status
            if self.disable_nearby:
                move_angle_deg = float(self.robot_delta_angle_deg)
            else:
                move_angle_deg = _normalize_increment_angle_deg(self.robot_delta_angle_deg)
            self.rparams["moveAngle"] = math.radians(abs(move_angle_deg))
            self.rparams["locMode"] = self.mode.value
            self.rparams["actionName"] = self.action_name
            speed_w = abs(self.speed_w_robot) if self.speed_w_robot is not None else None
            if speed_w is None:
                rotate_defaults = _get_rotate_nav_defaults()
                default_rot_speed = rotate_defaults.get("maxRot")
                if default_rot_speed is not None:
                    speed_w = abs(default_rot_speed)
            if speed_w is not None:
                if self.disable_nearby:
                    if self.robot_direction == RotateDirection.CLOCKWISE:
                        speed_w = -speed_w
                    elif self.robot_direction == RotateDirection.NEARBY and move_angle_deg < 0:
                        speed_w = -speed_w
                elif self.robot_direction == RotateDirection.NEARBY:
                    if move_angle_deg < 0:
                        speed_w = -speed_w
                elif self.robot_direction == RotateDirection.CLOCKWISE:
                    speed_w = -speed_w
                self.rparams["speedW"] = speed_w
            _trace_log(f"rparams: {self.rparams}", name=f"{LOG_NAME}.task")

        self.action_status = Navigation.runOdoMove(
            self.rparams if self.rparams else None
        )

        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['rparams'] = self.rparams
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time

        return self.action_status


class ShelfCoordinateRotate(BaseAction):
    """托盘坐标系旋转动作。

    坐标系对应关系:
    `coordinateAxis == ShelfCoordinateAxis.ROBOT` 时，`shelfRotateAngle` 表示机器人坐标系下的托盘目标角。
    `coordinateAxis == ShelfCoordinateAxis.WORLD` 时，`shelfRotateAngle` 表示世界坐标系下的托盘目标角。
    `coordinateAxis == ShelfCoordinateAxis.INCREMENTAL` 时，`shelfRotateAngle` 表示相对当前托盘角的增量角。
    """

    def __init__(self, shelf_angle=None, shelf_direction=RotateDirection.NEARBY, coordinate_axis=None):
        super().__init__("ShelfCoordinateRotate")
        self.action_args = {
            "shelfRotateAngle": shelf_angle,
            "shelfRotateDirection": shelf_direction.value,
            "coordinateAxis": None if coordinate_axis is None else coordinate_axis.value,
        }
        self.shelf_direction = shelf_direction
        self.coordinate_axis = coordinate_axis
        self.action_status = ActionStatus.INIT
        self.init = True

        self.shelf_angle = None
        if shelf_angle is not None:
            self.shelf_angle = math.radians(shelf_angle)

    def run(self, j: Actions):
        if self.init:
            Navigation.resetRotateMove()
            Navigation.resetOdoMove()
            self.init = False
            self.action_status = ActionStatus.RUNNING
            if self.shelf_angle is None:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError(
                    "No rotation angle provided",
                    "Shelf coordinate rotation requires shelfRotateAngle"
                )
                return self.action_status
            if self.coordinate_axis == ShelfCoordinateAxis.ROBOT:
                _trace_log("setRobotSpinAngle", name=f"{LOG_NAME}.task")
                Navigation.setRobotSpinAngle(self.shelf_angle, self.shelf_direction.value)
            elif self.coordinate_axis == ShelfCoordinateAxis.WORLD:
                _trace_log("setGlobalSpinAngle", name=f"{LOG_NAME}.task")
                Navigation.setGlobalSpinAngle(self.shelf_angle, self.shelf_direction.value)
            elif self.coordinate_axis == ShelfCoordinateAxis.INCREMENTAL:
                _trace_log("setIncreaseSpinAngle", name=f"{LOG_NAME}.task")
                Navigation.setIncreaseSpinAngle(self.shelf_angle)
            else:
                self.action_status = ActionStatus.FAILED
                Navigation.setTaskError(
                    "CoordinateAxisUnsupported",
                    f"coordinateAxis {self.coordinate_axis.value if self.coordinate_axis else self.coordinate_axis} not support"
                )
                return self.action_status

        if Navigation.spinRun():
            self.action_status = ActionStatus.FINISHED

        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time

        return self.action_status

class GoLineByOdo(BaseAction):
    """使用里程接口执行直线/平移运动"""

    def __init__(self, move_dist: float, speed_x=None, speed_y=None, mode=LocMode.ODO):
        super().__init__("GoLineByOdo")
        self.move_dist = move_dist
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.mode = mode
        self.init = True
        self.action_status = ActionStatus.INIT

    def run(self, j: Actions):
        if self.init:
            Navigation.resetOdoMove()
            self.init = False
            self.action_status = ActionStatus.RUNNING
        params = {
            "moveDist": float(self.move_dist),
            "locMode": self.mode.value,
            "actionName": "GoLineByOdo",
        }
        _set_if_not_none(params, "speedX", self.speed_x, float)
        _set_if_not_none(params, "speedY", self.speed_y, float)
        if self.action_status == ActionStatus.RUNNING and "GoLineByOdo" not in j.report_info:
            _trace_log(f"odo move start params={params}", name=f"{LOG_NAME}.nav")
        self.action_status = Navigation.runOdoMove(params)

        j.report_info["GoLineByOdo"] = {
            "actionStatus": self.action_status,
            "moveDist": self.move_dist,
            "speedX": self.speed_x,
            "speedY": self.speed_y,
            "mode": self.mode.value,
        }

class GoArc(BaseAction):
    """圆弧走到指定点"""
    
    def __init__(self, rot_radius, rot_degree, rot_speed, mode=LocMode.ODO):
        super().__init__("GoArc")
        self.rot_radius = rot_radius
        self.rot_degree = rot_degree
        self.rot_speed = rot_speed
        self.mode = mode
        self.action_status = ActionStatus.INIT

        self.init = True

    
    def run(self, j: Actions):
        if self.init:
            Navigation.resetOdoMove()
            self.init = False
            self.action_status = ActionStatus.RUNNING
        self.arg={
            "locMode": self.mode.value,
            "rotDegree": float(self.rot_degree),
            "rotRadius": float(self.rot_radius),
            "actionName": self.action_name,
        }
        _set_if_not_none(self.arg, "rotSpeed", self.rot_speed, float)
        if self.action_status == ActionStatus.RUNNING and "GoArc" not in j.report_info:
            _trace_log(f"arc move start params={self.arg}", name=f"{LOG_NAME}.nav")
        self.action_status=Navigation.runOdoMove(self.arg)

        j.report_info["GoArc"] = {
            "actionStatus": self.action_status,
            "rotRadius": self.rot_radius,
            "rotDegree": self.rot_degree,
            "rotSpeed": self.rot_speed,
            "mode": self.mode.value
        }

def main():
    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init(script_type=ScriptType.TASK)
    a = Actions()

    while True:
        status = a.script_status
        Module.setStatus(status)
        a._tick_report()

        if status == ScriptStatus.NONE:
            input_params = Module.getTaskArgs()
            if input_params:
                try:
                    validated_params = param_loader.loadInput(input_params)
                    validated_params = _normalize_legacy_task_args(validated_params)
                    a.init_task(validated_params)
                except ValueError as e:
                    _trace_log(f"check error: {e}", name=f"{LOG_NAME}.err")
                    Navigation.setTaskError(
                        "Input parameters invalid",
                        f"Input error: {e} Some input params are not valid Check the input params Input validation"
                    )
                    a.set_status(ScriptStatus.FAILED)
        elif status == ScriptStatus.RUNNING:
            a.run()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            _trace_log(f"task cycle end status={ScriptStatus(status).name}", name=f"{LOG_NAME}.task")
            # a.reset_task_state()
            break
        time.sleep(0.1)

if __name__ == '__main__':
    main()
