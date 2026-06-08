# -*- coding: utf-8 -*-
# @Date: 2025/12/24
# @Author: zengweibin & xukeyi
# @File: actions.py
# @Update: 支持功能说明，机器人底盘单独旋转，托盘单独旋转，机器人和托盘同时旋转，顶升功能

import json
import math
import time
from enum import IntEnum

start_time = time.time()
from syspy import Module, Di, Motor, Navigation, Loc, ScriptStatus, Trace
from syspy.lib.module import ModuleBase
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ScriptParam
from standard import goPath
param_loader = ScriptParam(__file__)
from syspy.lib.robot import RobotParam
from syspy.utils import ScriptType


LOG_NAME = "actions"
OMNI_CHASSIS_TYPES = {
    "multipleDifferentialSteers",
    "multiStandardAndDifferentialSteers",
    "multiSteers",
    "omni",
    "quadruped",
    "wheeledLeggedQuadruped",
}


def _trace_log(msg: str, name: str = LOG_NAME) -> None:
    Trace.log(msg, name=name)


def _trace_chart(msg: dict, name: str = f"{LOG_NAME}.state") -> None:
    Trace.log(msg, False, name=name)


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

def _normalize_operation(task_args: dict) -> str:
    operation = task_args.get("operation")
    if operation and operation != 123:
        return operation
    keys = set(task_args.keys())
    if {"robotRotateAngle", "robotRotateDirection", "shelfRotateAngle", "liftHeight"} & keys:
        return "rotate"
    if "dist" in keys:
        return "line"
    if {"rotRadius", "rotDegree", "rotSpeed"} & keys:
        return "arc"
    return ""

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
        _trace_log("Reloading config parameters", name=f"{LOG_NAME}.cfg")
        cls.config = param_loader.loadConfig()
        _trace_log(f"Loaded config: {cls.config}", name=f"{LOG_NAME}.cfg")
        cls.lift_motor_speed = cls.config.get("liftMotorSpeed")
        _trace_log(f"Updated config: {cls.config}", name=f"{LOG_NAME}.cfg")


# 创建全局配置管理器实例
config_params = ConfigParams()


def script_config_callback():
    _trace_log("Reloading script config parameters", name=f"{LOG_NAME}.cfg")
    config_params.reload_config()


def print_info():
    _trace_chart(
        {
            "liftMotorSpeed": config_params.lift_motor_speed,
            "liftMotorName": config_params.lift_motor_name,
            "spinMotorName": config_params.spin_motor_name,
        },
        name=f"{LOG_NAME}.cfg",
    )


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
                        with builder.CHILD(key="robotRotateAngle", name="Robot Rotate Angle",
                                        desc="底盘旋转的目标角度，任务结束时机器人在世界坐标系下的角度，单位°，范围 >=0"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(False)
                            builder.UNIT("°")
                            builder.SINGLESTEP(1)
                            builder.DEFAULTVALUE(0.0)

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
                            builder.DEFAULTVALUE(0.0)

                        # 托盘旋转角度
                        with builder.CHILD(key="shelfRotateAngle", name="Shelf Rotate Angle",
                                        desc="托盘旋转目标角度，任务结束时托盘在机器人坐标系下的角度，单位°，范围 [-180~180]"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.MIN_VALUE(-180)
                            builder.MAX_VALUE(180)
                            builder.REQUIRED(False)
                            builder.UNIT("°")
                            builder.SINGLESTEP(1)
                            builder.DEFAULTVALUE(0.0)


                        # 托盘旋转方向
                        with builder.CHILD(key="shelfRotateDirection", name="Shelf Rotate Direction",
                                        desc="托盘旋转方向：-1 顺时针 0 自主选择 1 逆时针"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE(1)



                        #基于哪个坐标系旋转
                        with builder.CHILD(key="coordinateAxis", name="coordinateAxis",
                                        desc="基于哪个坐标系旋转"):
                            builder.TYPE(ParamType.COMBO_BOX)
                            builder.REQUIRED(False)
                            with builder.CHILDREN():
                                builder.CHILD(key="increaseSpinAngle", name="increaseSpinAngle",desc="在当前托盘角度基础上增加一个角度, 角度为正数则逆时针旋转, 为负数顺时针旋转")
                                builder.CHILD(key="robotSpinAngle", name="Robot Spin Angle",desc="将托盘的角度转到机器人坐标系下的一个角度。spinDirection为0, 则就近转过去; spinDirection为1, 则逆时针转过去; spinDirection为-1, 则顺时针转过去")
                                builder.CHILD(key="globalSpinAngle", name="将托盘的角度转到世界坐标系下的一个角度。spinDirection为0, 则就近转过去; spinDirection为1, 则逆时针转过去; spinDirection为-1, 则顺时针转过去")



                        #是否用于调试
                        with builder.CHILD(key="isDebug", name="Is Debug",
                                        desc="是否用于调试，若为 True，则在调试模式下运行，否则在正常模式下运行"):
                            builder.TYPE(ParamType.BOOL)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE(False)

                        # 货物模型文件
                        with builder.CHILD(key="recFile", name="Rec File",
                                        desc="货物模型文件"):
                            builder.TYPE(ParamType.STRING)
                            builder.REQUIRED(False)
                            builder.DEFAULTVALUE("default.srec")
                        with builder.CHILD(key="mode", name="模式选择",
                                        desc="0 = 里程模式(根据里程进行运动), 1 = 定位模式, 若缺省则默认为里程模式"):
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
                                        desc="0 = 里程模式(根据里程进行运动), 1 = 定位模式, 若缺省则默认为里程模式"):
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
                                        desc="0 = 里程模式(根据里程进行运动), 1 = 定位模式, 若缺省则默认为里程模式"):
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(False)





    builder.save()


# --- 枚举定义 ---
class ActionStatus(IntEnum):
    """动作运行状态枚举"""
    INIT = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


class RotateDirection(IntEnum):
    """旋转方向枚举"""
    NEARBY = 0  # 不指定方向旋转
    COUNTERCLOCKWISE = 1  # 逆时针
    CLOCKWISE = -1  # 顺时针


# --- 主控制类 ---
class Actions(ModuleBase):
    """动作控制主类"""

    def __init__(self):
        self.init_args = False
        self.action_list = []
        self.action_id = 0
        self.task_args = {}
        self.report_info = {}
        self.script_status = ScriptStatus.NONE

        # 任务参数
        self.robot_rotate_angle = None
        self.robot_rotate_direction = RotateDirection.NEARBY
        self.shelf_rotate_angle = None
        self.shelf_rotate_direction = RotateDirection.NEARBY
        self.lift_height = None
        self.rec_file = None
        self.lift_speed = None
        self.lift_stop_di = -1

        # 电机状态
        self.lift_pos = None
        self.lift_pos_init = None
        self.shelf_pos = None
        self.shelf_pos_init = None

        _trace_log(f"moduleType = {config_params.module_type}", name=f"{LOG_NAME}.cfg")
        _trace_log(f"liftMotorName = {config_params.lift_motor_name}", name=f"{LOG_NAME}.cfg")
        _trace_log(f"spinMotorName = {config_params.spin_motor_name}", name=f"{LOG_NAME}.cfg")

        # 获取电机初始位置
        if config_params.lift_motor_name:
            self.lift_pos_init = Motor.getMotorPos(config_params.lift_motor_name)
        if config_params.spin_motor_name:
            self.shelf_pos_init = Motor.getMotorPos(config_params.spin_motor_name)

        self.lift_speed = None

        Navigation.clearDeviceError('SPIN_MOTOR_LOST')
        Navigation.clearDeviceError('LIFT_MOTOR_NOT_FOUND')

    def _init_args(self):
        """初始化任务参数"""
        if not self.init_args:
            self.init_args = True
            self.action_list = []
            self.action_id = 0
            self.report_info["scriptArgs"] = self.task_args


            # 检查托盘电机
            if config_params.spin_motor_name is None and (
                    self.task_args.get("shelfRotateAngle") is not None):
                Navigation.setDeviceError("SPIN_MOTOR_LOST", "The tray spin motor is missing, this abnormality is caused by incorrect robot model configuration, please check the robot model configuration to fix this problem")
                self.script_status = ScriptStatus.FAILED
                return

            # 检查升降电机
            if config_params.lift_motor_name is None and self.task_args.get("liftHeight") is not None:
                Navigation.setDeviceError("LIFT_MOTOR_NOT_FOUND", "Lift motor (linear) not found, cause: device not detected, solution: check robot model configuration and perform motor check")
                self.script_status = ScriptStatus.FAILED
                return

            operation = _normalize_operation(self.task_args)
            _trace_log(f"normalized operation: {operation or 'unknown'}", name=f"{LOG_NAME}.task")
                    
            if operation=='line':
                # 获取直线运动参数
                self.dist = self.task_args.get("dist", None)
                self.vx = self.task_args.get("vx", None)
                self.vy = self.task_args.get("vy", None)
                self.mode = self.task_args.get("mode", None)
                if self.mode is None:
                    self.mode = 0
                vx_value = 0.0 if self.vx is None else float(self.vx)
                vy_value = 0.0 if self.vy is None else float(self.vy)
                v = math.hypot(vx_value, vy_value)
                if v <= 1e-6:
                    Navigation.setTaskError(
                        "LineSpeedInvalid",
                        "Line motion requires vx or vy to be non-zero"
                    )
                    self.script_status = ScriptStatus.FAILED
                    return
                if abs(vy_value) > 1e-6 and config_params.chassis_type not in OMNI_CHASSIS_TYPES:
                    Navigation.setTaskError(
                        "LineLateralUnsupported",
                        f"chassisType {config_params.chassis_type} does not support lateral motion"
                    )
                    self.script_status = ScriptStatus.FAILED
                    return
                move_dist = abs(float(self.dist))
                if self.mode == 0:
                    self.action_list.append(
                        GoLineByOdo(
                            move_dist=move_dist,
                            speed_x=None if self.vx is None else float(self.vx),
                            speed_y=None if self.vy is None else float(self.vy),
                        )
                    )
                else:
                    t = move_dist / v
                    pos_x = vx_value * t
                    pos_y = vy_value * t
                    heading = 0.0
                    back_mode = False
                    hold_dir = None
                    if abs(vx_value) > 1e-6 and abs(vy_value) <= 1e-6:
                        back_mode = vx_value < 0
                        pos_x = abs(pos_x)
                        pos_y = 0.0
                        heading = 0.0
                    else:
                        hold_dir = float(Loc.getPose().get("yaw", 0.0))
                    self.action_list.append(
                        GoPath(
                            (pos_x, pos_y, heading),
                            self.mode,
                            back_mode=back_mode,
                            is_hold_dir=hold_dir,
                            max_speed=v,
                        )
                    )
                
                
            elif operation=='rotate':
                self.mode = self.task_args.get("mode", 0)
                _trace_log(f"mode is {self.mode}", name=f"{LOG_NAME}.task")
                # 获取底盘旋转参数

                self.robot_rotate_angle = self.task_args.get("robotRotateAngle", None)
                self.robot_rotate_speed = self.task_args.get("robotRotateSpeed", None)
                self.robot_rotate_speed_rad = _deg_to_rad_or_none(self.robot_rotate_speed)
                self.robot_rotate_direction = self.task_args.get("robotRotateDirection", None)
                self.is_debug = self.task_args.get("isDebug", False)

                # 获取托盘旋转参数
                self.shelf_rotate_angle = self.task_args.get("shelfRotateAngle", None)
                self.shelf_rotate_direction = self.task_args.get("shelfRotateDirection", RotateDirection.NEARBY)
                self.selfCoordinateAxis = self.task_args.get("coordinateAxis", None)

                # 获取顶升参数
                self.lift_height = self.task_args.get("liftHeight", None)
                self.lift_speed = self.task_args.get("lift_speed", None)
                self.rec_file = self.task_args.get("recFile", None)


                # 检查是否有任何动作参数
                if (self.robot_rotate_angle is None
                        and self.shelf_rotate_angle is None
                        and self.lift_height is None):
                    Navigation.setTaskError(
                        "No action parameters provided",
                        "No action parameters provided Set rotation angle or lift height Parameter validation"
                    )
                    self.script_status = ScriptStatus.FAILED
                    return
                #优先执行支持里程，定位模式的旋转动作
                if self.robot_rotate_angle is not None:
                    if self.robot_rotate_direction is None:
                        if self.robot_rotate_speed is not None:
                            if self.robot_rotate_speed > 0:
                                self.robot_rotate_direction = RotateDirection.COUNTERCLOCKWISE
                            elif self.robot_rotate_speed < 0:
                                self.robot_rotate_direction = RotateDirection.CLOCKWISE
                            else:
                                self.robot_rotate_direction = RotateDirection.NEARBY
                        else:
                            self.robot_rotate_direction = RotateDirection.NEARBY
                has_rotate_action = (
                    self.robot_rotate_angle is not None
                    or self.shelf_rotate_angle is not None
                    or self.selfCoordinateAxis is not None
                )
                if has_rotate_action:
                    rotate_kwargs = {
                        "robot_rotate_angle": self.robot_rotate_angle,
                        "robot_direction": self.robot_rotate_direction,
                        "shelf_angle": self.shelf_rotate_angle,
                        "shelf_direction": self.shelf_rotate_direction,
                        "selfCoordinateAxis": self.selfCoordinateAxis,
                        "mode": self.mode,
                        "is_debug": self.is_debug,
                    }
                    if self.robot_rotate_speed_rad is not None:
                        rotate_kwargs["speed_w_robot"] = self.robot_rotate_speed_rad
                    self.action_list.append(Rotate(**rotate_kwargs))

                if self.lift_height is not None:
                    self.action_list.append(
                        Jack(config_params.lift_motor_name, self.lift_height,
                            self.lift_speed, self.lift_stop_di, self.rec_file))
            elif operation=='arc':
                # 获取圆弧运动参数
                self.rot_radius = self.task_args.get("rotRadius", None)
                self.rot_degree = self.task_args.get("rotDegree", None)
                self.rot_speed = self.task_args.get("rotSpeed", None)
                self.mode = self.task_args.get("mode", None)
                if self.mode is None:
                    self.mode = 0  
                self.action_list.append(GoArc(self.rot_radius, self.rot_degree, self.rot_speed, self.mode))
            else:
                _trace_log(f"operation {operation} not support!", name=f"{LOG_NAME}.err")
                Navigation.setTaskError(
                    "OperationNotSupported",
                    f"operation {operation} not support"
                )
                self.script_status = ScriptStatus.FAILED
                return
                

    def suspend(self):
        Module.setStatus(ScriptStatus.SUSPENDED)
        self.script_status = ScriptStatus.SUSPENDED
        _trace_log("suspend", name=f"{LOG_NAME}.task")

    def resume(self):
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            Module.setStatus(ScriptStatus.RUNNING)
            self.script_status = ScriptStatus.RUNNING
        _trace_log("resume", name=f"{LOG_NAME}.task")

    def cancel(self):
        Navigation.resetOdoMove()
        Navigation.resetRotateMove()
        self.init_args = False
        self.action_id = 0
        self.action_list = []
        Module.setStatus(ScriptStatus.FAILED)
        self.script_status = ScriptStatus.FAILED
        _trace_log("cancel", name=f"{LOG_NAME}.task")
    



    def run(self, args):
        """运行任务"""
        self.script_status = ScriptStatus.RUNNING
        self.task_args = args
        self._init_args()
        if self.script_status == ScriptStatus.FAILED:
            self._update_report_info()
            Module.reportInfo(self.report_info)
            _trace_chart(self.report_info, name=f"{LOG_NAME}.report")
            return self.script_status
        self._execute_actions()

        if self.action_id < len(self.action_list):
            self.report_info["currentAction"] = self.action_list[self.action_id].action_state
        self._update_report_info()
        Module.reportInfo(self.report_info)
        _trace_chart(self.report_info, name=f"{LOG_NAME}.report")
        return self.script_status

    def _execute_actions(self):
        """执行动作列表"""
        if self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_status == ActionStatus.FINISHED:
                self.action_id += 1
            elif current_action.action_status == ActionStatus.FAILED:
                Navigation.setTaskError(
                    "Action failed",
                    f"execute action {current_action} failed!  execute_actions"
                )
                self.script_status = ScriptStatus.FAILED
                Navigation.resetOdoMove()
                self.init_args = False
                self.action_id = 0
                self.action_list = []
                Module.setStatus(ScriptStatus.FAILED)
            else:
                Module.setStatus(ScriptStatus.RUNNING)
                current_action.run(self)
        else:
            Navigation.resetOdoMove()
            self.init_args = False
            self.action_id = 0
            self.action_list = []
            self.script_status = ScriptStatus.FINISHED
            Module.setStatus(ScriptStatus.FINISHED)

    def _update_report_info(self):
        """更新上报信息"""
        current_robot_angle = Loc.getPose().get("yaw", 0.)

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

        self.report_info["actionListName"] = [a.__class__.__name__ for a in self.action_list]
        self.report_info["actionId"] = self.action_id
        self.report_info["currentRobotAngle"] = current_robot_angle
        self.report_info["scriptStatus"] = self.script_status


# --- 基础动作类 ---
class BaseAction:
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        self.action_name = action_name or self.__class__.__name__
        self.action_args = {}
        self.init = False
        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.action_state = {}

    def run(self, a: Actions):
        """外部调用时，输出或打印实例对象的 action_state 字段"""
        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time

    def reset(self):
        pass

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


class Rotate(BaseAction):
    """旋转动作，支持底盘和托盘同时旋转或单独旋转"""

    def __init__(self, robot_rotate_angle=None, robot_direction=RotateDirection.NEARBY,
                 speed_w_robot=None, shelf_angle=None, shelf_direction=RotateDirection.NEARBY,selfCoordinateAxis=None, mode=0,is_debug=False):
        super().__init__("Rotate")
        self.action_args = {
            "mode": mode,
            "robotRotateAngle": robot_rotate_angle,
            "robot_direction": robot_direction,
            "speed_w_robot": speed_w_robot,
            "shelf_angle": shelf_angle,
            "shelf_direction": shelf_direction,
            "isDebug": is_debug
        }
        self.mode = mode
        self.action_status = ActionStatus.INIT
        self.init = True
        self.robot_direction = robot_direction
        self.shelf_direction = shelf_direction
        self.speed_w_robot = float(speed_w_robot) if speed_w_robot is not None else None
        self.is_debug = is_debug
        self.selfCoordinateAxis = selfCoordinateAxis 


        # 底盘角度处理
        self.robot_rotate_angle = None
        if robot_rotate_angle is not None:
            self.robot_rotate_angle = math.radians(robot_rotate_angle)

        # 托盘角度处理
        self.shelf_angle = None
        if shelf_angle is not None:
            self.shelf_angle = math.radians(shelf_angle)

        self.rparams = None
        self.sparams = None
    def run(self, a: Actions):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetRotateMove()
            Navigation.resetOdoMove()
            self.rparams = dict()
            self.sparams = dict()
            if not self.is_debug:
                if self.robot_rotate_angle is not None:
                    self.robot_rotate_angle = _normalize_angle_rad(self.robot_rotate_angle)
                    self.rparams.update(_get_rotate_nav_defaults())
                    self.rparams["moveAngle"] = self.robot_rotate_angle
                    self.rparams["dir"] = self.robot_direction
                    if self.speed_w_robot is not None:
                        self.rparams["speedW"] = math.fabs(self.speed_w_robot)
                    else:
                        _set_if_not_none(self.rparams, "speedW", self.rparams.get("maxRot"), math.fabs)

                if self.shelf_angle is not None:
                    self.sparams["angle"] = self.shelf_angle
                    self.sparams["dir"] = self.shelf_direction

                if self.shelf_angle is None and self.robot_rotate_angle is None:
                    self.action_status = ActionStatus.FAILED
                    Navigation.setTaskError(
                        "No rotation angle provided",
                        "No rotation angle provided Set robot or shelf rotation angle Parameter validation"
                    )
                    return self.action_status
            else:
                if self.selfCoordinateAxis is not None:
                    if self.selfCoordinateAxis == "robotSpinAngle":
                        _trace_log("setRobotSpinAngle", name=f"{LOG_NAME}.task")
                        Navigation.setRobotSpinAngle(self.shelf_angle, self.shelf_direction)
                    elif self.selfCoordinateAxis == "globalSpinAngle":
                        _trace_log("setGlobalSpinAngle", name=f"{LOG_NAME}.task")
                        Navigation.setGlobalSpinAngle(self.shelf_angle, self.shelf_direction)
                    elif self.selfCoordinateAxis == "increaseSpinAngle":
                        _trace_log("setIncreaseSpinAngle", name=f"{LOG_NAME}.task")
                        Navigation.setIncreaseSpinAngle(self.shelf_angle)
                else:
                    move_angle_deg = float(self.action_args["robotRotateAngle"])
                    move_angle = math.radians(abs(move_angle_deg))
                    self.rparams["moveAngle"] = move_angle
                    speed_w = None
                    if self.speed_w_robot is not None:
                        speed_w = abs(self.speed_w_robot)
                    else:
                        nav_default = _get_rotate_nav_defaults()
                        default_rot_speed = nav_default.get("maxRot")
                        if default_rot_speed is not None:
                            speed_w = abs(default_rot_speed)

                    if speed_w is not None:
                        if self.robot_direction == RotateDirection.NEARBY:
                            if move_angle_deg < 0:
                                speed_w = -speed_w
                        elif self.robot_direction == RotateDirection.CLOCKWISE:
                            speed_w = -speed_w
                        self.rparams["speedW"] = speed_w
                    self.rparams["locMode"] = self.mode 
            _trace_log(f"rparams: {self.rparams}, sparams: {self.sparams}", name=f"{LOG_NAME}.task")           
        if self.selfCoordinateAxis is  None:
            if not self.is_debug:
                # 执行旋转
                self.action_status = Navigation.runRotateMove(
                    robot_params=self.rparams if self.rparams else None,
                    shelf_params=self.sparams if self.sparams else None
                )
            else:
                self.action_status = Navigation.runOdoMove(
                    self.rparams if self.rparams else None
                )
        else:
            if Navigation.spinRun():
                self.action_status = ActionStatus.FINISHED
                
        self.action_state['actionName'] = self.__class__.__name__
        self.action_state["actionArgs"] = self.action_args
        self.action_state['rparams'] = self.rparams
        self.action_state['sparams'] = self.sparams
        self.action_state['actionStatus'] = self.action_status
        self.action_state["actionRuntime"] = time.time() - self.start_time

        return self.action_status

class GoPath(BaseAction):
    """直线走到指定点"""

    def __init__(self, go_pos,mode=True,coordinate='robot', back_mode=False, is_hold_dir=None, max_speed=None, max_rot=None,
                 path_dist_accuracy=0.01, path_angle_accuracy=0.05):
        super().__init__("GoPath")

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
        self.useOdo = True if mode == 0 else False
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
            "coordinate": self.coordinate,
            "reachDist": self.path_dist_accuracy,
            "reachAngle": self.path_angle_accuracy,
            "useOdo": self.useOdo
        }
        _set_if_not_none(args, "maxSpeed", self.max_speed)
        _set_if_not_none(args, "maxRot", self.max_rot)
        if self.is_hold_dir is not None:
            args["holdDir"] = self.is_hold_dir
        _trace_chart(args, name=f"{LOG_NAME}.go_path")
        self.action_status = self.go_path.run(args)

        j.report_info["GoPath"] = {
            "actionStatus": self.action_status,
            "goPos": self.go_pos,
            "backMode": self.back_mode,
            "holdDir": self.is_hold_dir,
            "coordinate": self.coordinate,
            "maxSpeed": self.max_speed,
            "maxRot": self.max_rot,
            "reachDist": self.path_dist_accuracy,
            "reachAngle": self.path_angle_accuracy
        }
        Module.reportInfo(j.report_info)

class GoLineByOdo(BaseAction):
    """使用里程接口执行直线/平移运动"""

    def __init__(self, move_dist: float, speed_x=None, speed_y=None):
        super().__init__("GoLineByOdo")
        self.move_dist = move_dist
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.init = True
        self.action_status = ActionStatus.INIT

    def run(self, j: Jack):
        if self.init:
            Navigation.resetOdoMove()
            self.init = False
            self.action_status = ActionStatus.RUNNING
        params = {
            "moveDist": float(self.move_dist),
            "actionName": "GoLineByOdo",
        }
        _set_if_not_none(params, "speedX", self.speed_x, float)
        _set_if_not_none(params, "speedY", self.speed_y, float)
        _trace_chart(params, name=f"{LOG_NAME}.go_line_odo")
        self.action_status = Navigation.runOdoMove(params)

        j.report_info["GoLineByOdo"] = {
            "actionStatus": self.action_status,
            "moveDist": self.move_dist,
            "speedX": self.speed_x,
            "speedY": self.speed_y,
        }
        Module.reportInfo(j.report_info)

class GoArc(BaseAction):
    """圆弧走到指定点"""
    
    def __init__(self, rot_radius, rot_degree, rot_speed, mode=0):
        super().__init__("GoArc")
        self.rot_radius = rot_radius
        self.rot_degree = rot_degree
        self.rot_speed = rot_speed
        self.mode = mode
        self.action_status = ActionStatus.INIT

        self.init = True

    
    def run(self, j: Jack):
        if self.init:
            Navigation.resetOdoMove()
            self.init = False
            self.action_status = ActionStatus.RUNNING
        self.arg={
            "locMode": self.mode,
            "rotDegree": float(self.rot_degree),
            "rotRadius": float(self.rot_radius),
            "actionName": "ass"
        }
        _set_if_not_none(self.arg, "rotSpeed", self.rot_speed, float)

        _trace_chart(
            {
                "params": self.arg,
                "status": self.action_status,
            },
            name=f"{LOG_NAME}.go_arc",
        )
        self.action_status=Navigation.runOdoMove(self.arg)

        j.report_info["GoArc"] = {
            "actionStatus": self.action_status,
            "rotRadius": self.rot_radius,
            "rotDegree": self.rot_degree,
            "rotSpeed": self.rot_speed,
            "mode": self.mode
        }
        Module.reportInfo(j.report_info)

def main():
    # 注册脚本参数变更回调
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init(script_type=ScriptType.TASK)
    validator = ParamValidator(InputParams.builder.toDict())
    a = Actions()
    print_info()

    while True:
        # 脚本任务状态管理
        status = Module.getStatus()
        if status in (ScriptStatus.RUNNING, ScriptStatus.NONE):
            input_params = Module.getTaskArgs()
            _trace_chart({"taskArgs": input_params}, name=f"{LOG_NAME}.task_args")
            validated_params = {}
            input_params["operation"]=input_params.get("operation", 123)
            if input_params:
                try:
                    # 验证参数
                    validated_params = param_loader.loadInput(input_params)
                    _trace_chart({"validatedArgs": validated_params}, name=f"{LOG_NAME}.task_args")
                except ValueError as e:
                    _trace_log(f"check error: {e}", name=f"{LOG_NAME}.err")
                    Navigation.setTaskError(
                        "Input parameters invalid",
                        f"Input error: {e} Some input params are not valid Check the input params Input validation"
                    )
            a.run(validated_params)

        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
                _trace_log(f"status:{status}", name=f"{LOG_NAME}.task")
                break
                
        time.sleep(0.1)

if __name__ == '__main__':
    main()
