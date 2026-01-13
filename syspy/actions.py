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
from syspy import (Module, Logger, Di, Motor, Navigation, Loc, Abnormal,
                   Odometer, ScriptStatus, Trace, Controller)
from syspy.lib.module import pos2Base, pos2World, ModuleBase, SafeMoveStatus
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ScriptParam

param_loader = ScriptParam(__file__)
from syspy.lib.robot_param import RobotParam
from syspy.utils import Coordinate, ScriptType

log = Logger("actions")


# --- ConfigParams 类 ---
class ConfigParams:
    """配置管理器，用于管理动态配置参数"""
    config = {}
    lift_motor_speed = None

    module_type = RobotParam.getDevice("Model-000", "moduleType")
    lift_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.jackMotor")
    spin_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.spinMotor")
    motor_func = RobotParam.getDevice(f"{lift_motor_name}", "func") if lift_motor_name else None

    def __init__(self):
        self._build_and_load_config()

    @classmethod
    def _build_and_load_config(cls):
        """构建并加载配置参数"""
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
        Trace.log("Reloading config parameters")
        cls.config = param_loader.loadConfig()
        Trace.log(f"Loaded config: {cls.config}")
        cls.lift_motor_speed = cls.config.get("liftMotorSpeed")
        Trace.log(f"Updated config: {cls.config}")


# 创建全局配置管理器实例
config_params = ConfigParams()


def script_config_callback():
    Trace.log("Reloading script config parameters")
    config_params.reload_config()


def print_info():
    print(f"{config_params.lift_motor_speed=}")
    print(f"{config_params.lift_motor_name=}")
    print(f"{config_params.spin_motor_name=}")


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():

        # 底盘旋转角度
        with builder.CHILD(key="robotRotateAngle", name="Robot Rotate Angle",
                           desc="底盘旋转的目标角度，任务结束时机器人在世界坐标系下的角度，单位°，范围 [-180~180]"):
            builder.TYPE(ParamType.FLOAT)
            builder.MIN_VALUE(-180)
            builder.MAX_VALUE(180)
            builder.REQUIRED(False)
            builder.UNIT("°")
            builder.SINGLESTEP(1)
            builder.DEFAULTVALUE(0.0)

        # 底盘旋转方向
        with builder.CHILD(key="robotRotateDirection", name="Robot Rotate Direction",
                           desc="底盘旋转方向：-1 顺时针 0 自主选择 1 逆时针"):
            builder.TYPE(ParamType.INT)
            builder.REQUIRED(False)
            builder.DEFAULTVALUE(1)

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

        # 货物模型文件
        with builder.CHILD(key="recFile", name="Rec File",
                           desc="货物模型文件"):
            builder.TYPE(ParamType.STRING)
            builder.REQUIRED(False)
            builder.DEFAULTVALUE("default.srec")

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
class Actions:
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
        self.speed_w_robot = None
        self.lift_speed = None
        self.lift_stop_di = -1

        # 电机状态
        self.lift_pos = None
        self.lift_pos_init = None
        self.shelf_pos = None
        self.shelf_pos_init = None

        Trace.log(f"moduleType = {config_params.module_type}")
        Trace.log(f"liftMotorName = {config_params.lift_motor_name}")
        Trace.log(f"spinMotorName = {config_params.spin_motor_name}")

        # 获取电机初始位置
        if config_params.lift_motor_name:
            self.lift_pos_init = Motor.getMotorPos(config_params.lift_motor_name)
        if config_params.spin_motor_name:
            self.shelf_pos_init = Motor.getMotorPos(config_params.spin_motor_name)

        self.lift_speed = config_params.lift_motor_speed

        Abnormal.clear(53780)
        Abnormal.clear(55300)
        Abnormal.clear(57300)

    def _init_args(self):
        """初始化任务参数"""
        if not self.init_args:
            self.init_args = True
            self.report_info["script_args"] = self.task_args

            # 获取速度参数
            self.speed_w_robot = self.task_args.get("speed_w_robot", None)
            if self.speed_w_robot is None:
                self.speed_w_robot = 0.5  # 默认角速度

            # 检查托盘电机
            if config_params.spin_motor_name is None and (
                    self.task_args.get("shelfRotateAngle") is not None):
                Abnormal.setTask(53780, "没有找到托盘旋转电机（spin）",
                                 "Spin motor not found",
                                 "Check robot model configuration",
                                 "Motor check")
                self.script_status = ScriptStatus.FAILED
                return

            # 检查升降电机
            if config_params.lift_motor_name is None and self.task_args.get("liftHeight") is not None:
                Abnormal.setTask(53780, "没有找到升降电机（linear）",
                                 "Lift motor not found",
                                 "Check robot model configuration",
                                 "Motor check")
                self.script_status = ScriptStatus.FAILED
                return

            # 获取底盘旋转参数
            self.robot_rotate_angle = self.task_args.get("robotRotateAngle", None)
            self.robot_rotate_direction = self.task_args.get("robotRotateDirection", RotateDirection.NEARBY)

            # 获取托盘旋转参数
            self.shelf_rotate_angle = self.task_args.get("shelfRotateAngle", None)
            self.shelf_rotate_direction = self.task_args.get("shelfRotateDirection", RotateDirection.NEARBY)

            # 获取顶升参数
            self.lift_height = self.task_args.get("liftHeight", None)
            self.lift_speed = self.task_args.get("lift_speed", self.lift_speed)
            self.rec_file = self.task_args.get("recFile", None)

            # 检查是否有任何动作参数
            if (self.robot_rotate_angle is None
                    and self.shelf_rotate_angle is None
                    and self.lift_height is None):
                Abnormal.setTask(53780, "请设置底盘、货架旋转角度或者顶升高度",
                                 "No action parameters provided",
                                 "Set rotation angle or lift height",
                                 "Parameter validation")
                self.script_status = ScriptStatus.FAILED
                return

            # 需要先执行旋转动作，再执行顶升动作
            if self.robot_rotate_angle is not None or self.shelf_rotate_angle is not None:
                self.action_list.append(
                    Rotate(self.robot_rotate_angle, self.robot_rotate_direction,
                           self.speed_w_robot, self.shelf_rotate_angle, self.shelf_rotate_direction))

            if self.lift_height is not None:
                self.action_list.append(
                    Jack(config_params.lift_motor_name, self.lift_height,
                         self.lift_speed, self.lift_stop_di, self.rec_file))

    def run(self, args):
        """运行任务"""
        self.script_status = ScriptStatus.RUNNING
        self.task_args = args
        self._init_args()
        self._execute_actions()

        if self.action_id < len(self.action_list):
            self.report_info["current_action"] = self.action_list[self.action_id].action_state
        self._update_report_info()
        Module.reportInfo(self.report_info)
        Trace.log(json.dumps(self.report_info))
        return self.script_status

    def _execute_actions(self):
        """执行动作列表"""
        # if self.action_id < len(self.action_list):
        #     if self.action_list[self.action_id].action_status == ActionStatus.FINISHED:
        #         self.action_id += 1
        #     elif self.action_list[self.action_id].action_status == ActionStatus.FAILED:
        #         self.script_status = ScriptStatus.FAILED
        #
        #     else:
        #         self.action_list[self.action_id].run(self)
        # else:
        #     self.script_status = ScriptStatus.FINISHED


        if self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_status == ActionStatus.FINISHED:
                self.action_id += 1
            elif current_action.action_status == ActionStatus.FAILED:
                Abnormal.setTask(53780, f"execute action {current_action} failed!",
                                 "",
                                 "",
                                 "execute_actions")
                self.script_status = ActionStatus.FAILED
                Module.setStatus(ScriptStatus.FAILED)
            else:
                current_action.run(self)
        else:
            self.script_status = ActionStatus.FINISHED
            Module.setStatus(ScriptStatus.FINISHED)
            self.action_list = []
        Trace.log(f'{self.action_id=}, {self.action_list=}')
        Trace.log(f"self.action_list: {self.action_list}")

    def _update_report_info(self):
        """更新上报信息"""
        current_robot_angle = Loc.getPose().get("yaw", 0.)

        # 获取电机位置
        if config_params.lift_motor_name:
            self.lift_pos = Motor.getMotorPos(config_params.lift_motor_name)
        if config_params.spin_motor_name:
            self.shelf_pos = Motor.getMotorPos(config_params.spin_motor_name)

        if self.lift_pos is not None:
            self.report_info["current_lift_height"] = self.lift_pos
        if self.shelf_pos is not None:
            current_shelf_angle_in_robot = self.shelf_pos / math.pi * 180
            self.report_info["current_shelf_angle_in_robot"] = current_shelf_angle_in_robot
            self.report_info["current_shelf_angle_in_world"] = current_robot_angle + current_shelf_angle_in_robot

        self.report_info["action_list_name"] = [a.__class__.__name__ for a in self.action_list]
        self.report_info["action_id"] = self.action_id
        self.report_info["current_robot_angle"] = current_robot_angle
        self.report_info["script_status"] = self.script_status


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
        self.action_state['action_name'] = self.__class__.__name__
        self.action_state["action_args"] = self.action_args
        self.action_state['action_status'] = self.action_status
        self.action_state["action_runtime"] = time.time() - self.start_time

    def reset(self):
        pass

    def __str__(self):
        return json.dumps({"action_state": self.action_state})


class Jack(BaseAction):
    """顶升动作"""

    def __init__(self, motor_name: str, height: float, speed=0.015, stop_di=-1, rec_file=None):
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
            Motor.setMotorPosition(self.motor_name, self.height, self.speed, self.stop_di)
            if Motor.isMotorReached(self.motor_name) or (self.stop_di >= 0 and Di.getDi(self.stop_di)):
                if self.height > 0:
                    if self.rec_file:
                        Navigation.setLocalShelfArea(self.rec_file)
                else:
                    Navigation.resetLocalShelfArea()
                self.action_status = ActionStatus.FINISHED
        else:
            self.action_status = ActionStatus.FAILED
            Abnormal.setTask(53780, "升降电机不存在",
                             "Lift motor not found",
                             "Check motor configuration",
                             "Motor check")

        self.action_state['action_name'] = self.__class__.__name__
        self.action_state["action_args"] = self.action_args
        self.action_state['action_status'] = self.action_status
        self.action_state["action_runtime"] = time.time() - self.start_time

    def reset(self):
        pass


class Rotate(BaseAction):
    """旋转动作，支持底盘和托盘同时旋转或单独旋转"""

    def __init__(self, robot_rotate_angle=None, robot_direction=RotateDirection.NEARBY,
                 speed_w_robot=None, shelf_angle=None, shelf_direction=RotateDirection.NEARBY):
        super().__init__("Rotate")
        self.action_args = {
            "robotRotateAngle": robot_rotate_angle,
            "robot_direction": robot_direction,
            "speed_w_robot": speed_w_robot,
            "shelf_angle": shelf_angle,
            "shelf_direction": shelf_direction
        }
        self.action_status = ActionStatus.INIT
        self.init = True
        self.robot_direction = robot_direction
        self.shelf_direction = shelf_direction
        self.speed_w_robot = speed_w_robot if speed_w_robot is not None else 0.5

        # 底盘角度处理
        self.robot_rotate_angle = None
        if robot_rotate_angle is not None:
            rad_robot = math.radians(robot_rotate_angle)
            self.robot_rotate_angle = (rad_robot + math.pi) % (2 * math.pi) - math.pi

        # 托盘角度处理
        self.shelf_angle = None
        if shelf_angle is not None:
            rad_shelf = math.radians(shelf_angle)
            self.shelf_angle = (rad_shelf + math.pi) % (2 * math.pi) - math.pi

        self.rparams = None
        self.sparams = None

    def run(self, a: Actions):
        self.action_status = ActionStatus.RUNNING

        if self.init:
            self.init = False
            Navigation.resetRotateMove()
            self.rparams = dict()
            self.sparams = dict()

            if self.robot_rotate_angle is not None:
                self.rparams["moveAngle"] = self.robot_rotate_angle
                self.rparams["dir"] = self.robot_direction
                self.rparams["speedW"] = self.speed_w_robot
                if self.robot_direction == RotateDirection.NEARBY:
                    self.action_status = ActionStatus.FAILED
                    Abnormal.setTask(53780, "不支持不指定方向旋转底盘",
                                     "Auto direction not supported for robot rotation",
                                     "Set explicit rotation direction",
                                     "Parameter validation")
                    return self.action_status

            if self.shelf_angle is not None:
                self.sparams["angle"] = self.shelf_angle
                self.sparams["dir"] = self.shelf_direction
                if self.shelf_direction == RotateDirection.NEARBY:
                    self.action_status = ActionStatus.FAILED
                    Abnormal.setTask(53780, "不支持不指定方向旋转托盘",
                                     "Auto direction not supported for shelf rotation",
                                     "Set explicit rotation direction",
                                     "Parameter validation")
                    return self.action_status

            if self.shelf_angle is None and self.robot_rotate_angle is None:
                self.action_status = ActionStatus.FAILED
                Abnormal.setTask(53780, "请设置底盘或货架旋转角度",
                                 "No rotation angle provided",
                                 "Set robot or shelf rotation angle",
                                 "Parameter validation")
                return self.action_status

        # 执行旋转
        self.action_status = Navigation.runRotateMove(
            robot_params=self.rparams if self.rparams else None,
            shelf_params=self.sparams if self.sparams else None
        )

        self.action_state['action_name'] = self.__class__.__name__
        self.action_state["action_args"] = self.action_args
        self.action_state['rparams'] = self.rparams
        self.action_state['sparams'] = self.sparams
        self.action_state['action_status'] = self.action_status
        self.action_state["action_runtime"] = time.time() - self.start_time

        return self.action_status


# --- 主函数 ---
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
        print(f"-------------------------status:{status}")

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
                    Abnormal.setTask(53780, f"Input error:{e}",
                                     "Some input params are not valid",
                                     "Check the input params",
                                     "Input validation")
            a.run(validated_params)

        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            a.init_args = False
            a.action_id = 0
            a.action_list = []
            break

        time.sleep(0.1)


if __name__ == '__main__':
    main()