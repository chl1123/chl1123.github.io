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
from standard import goPath, goBezier
if hasattr(ScriptParam, '_instance'):
    ScriptParam._instance = None 
    ScriptParam._initialized = False
    ScriptParam.config_change_callback = None
    ScriptParam.event_task_config = False
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

    
    

# # 生成圆弧上的点
# def generate_arc_points(center_x, center_y,x,y, radius, rotSpeed, angle, steps=20):
#     steps=100
#     points = []
#     start_angle=math.atan2(y-center_y,x-center_x)
#     total_rad=math.radians(angle)
#     angle_step = total_rad / steps
#     if  rotSpeed > 0:
#         direction = 1
#     else:
#         direction = -1
#     if radius > 0:
#         pass
#     else:
#         radius = -radius
#     for i in range(steps + 1):
#         current_angle = start_angle + i * angle_step
#         x = center_x + (radius * math.cos(current_angle))
#         y = center_y + (radius * math.sin(current_angle))
#         points.append((round(x, 6), round(y, 6)))
#         print(f"{i=}, {current_angle=}, {x=}, {y=}, {direction=}")
#         print("\n")
#     print(f"{points=}")
#     return points

# # 计算中心坐标
# def generate_arc_from_robot(radius, angle, rotSpeed, steps=20):

#     robot_pose = Loc.getPose()
#     robot_x = robot_pose["x"]
#     robot_y = robot_pose["y"]
#     robot_yaw = math.radians(robot_pose["yaw"]) 
#     if radius > 0:
#         status = 1
#     else:
#         status = -1
#         radius = -radius
#     center_x = robot_x + radius * math.sin(robot_yaw)
#     center_y = robot_y + radius * math.cos(robot_yaw)*status

#     print(f"{center_x=}, {center_y=}, {radius=}, {rotSpeed=}, {angle=}")
#     return generate_arc_points(center_x, center_y,robot_x,robot_y, radius, rotSpeed, angle, steps)

# def execute_arc_motion(radius, angle, rotSpeed=0.3, mode=True, steps=20):
    # arc_points = generate_arc_from_robot(radius, angle, rotSpeed, 5)
    # xs = [point[0] for point in arc_points]
    # ys = [point[1] for point in arc_points]
    # Navigation.resetPath()
    # Navigation.setPathMaxSpeed(rotSpeed)
    # Navigation.setPathReachDist(0.01)
    # Navigation.setPathReachAngle(0.05)
    # final_point = arc_points[-1]
    # prev_point = arc_points[-2]
    # final_angle = math.atan2(final_point[1] - prev_point[1], final_point[0] - prev_point[0])
    # print(f"{xs=}, {ys=}, {final_angle=}")
    # Navigation.setPathOnWorld(xs, ys, final_angle)
    # print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    # Navigation.goPathParam(dict())
    # print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')

    # # while not Navigation.isPathReached():
    # #     time.sleep(0.1)
    # return ScriptStatus.FINISHED
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
                            builder.DEFAULTVALUE(10)
                        
                        with builder.CHILD(key='robotRotateDirection', name='Robot Rotate Direction',
                                        desc='底盘旋转方向：-1 顺时针 1 逆时针'):
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
                            builder.REQUIRED(True)
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

        Trace.log(f"moduleType = {config_params.module_type}")
        Trace.log(f"liftMotorName = {config_params.lift_motor_name}")
        Trace.log(f"spinMotorName = {config_params.spin_motor_name}")

        # 获取电机初始位置
        if config_params.lift_motor_name:
            self.lift_pos_init = Motor.getMotorPos(config_params.lift_motor_name)
        if config_params.spin_motor_name:
            self.shelf_pos_init = Motor.getMotorPos(config_params.spin_motor_name)

        self.lift_speed = config_params.lift_motor_speed

        Navigation.clearDeviceError('SPIN_MOTOR_LOST')
        Navigation.clearDeviceError('LIFT_MOTOR_NOT_FOUND')

    def _init_args(self):
        """初始化任务参数"""
        if not self.init_args:
            self.init_args = True
            self.report_info["script_args"] = self.task_args


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

            operation = self.task_args.get("operation", "")
            if operation == 123:
                Trace.log(f"operation is None")
                keys=self.task_args.keys()
                if "robotRotateAngle" in keys or "robotRotateDirection" in keys or "shelfRotateAngle" in keys:
                    operation="rotate"
                    Trace.log(f"operation is rotate")
                elif "dist" in keys:
                    operation="line"
                    Trace.log(f"operation is line")
                elif "rotRadius" in keys or "rotDegree" in keys or "rotSpeed" in keys:
                    operation="arc"
                    Trace.log(f"operation is arc")
                    
            if operation=='line':
                # 获取直线运动参数
                self.dist = self.task_args.get("dist", None)
                self.vx = self.task_args.get("vx", 0.0)
                self.vy = self.task_args.get("vy", 0.0)
                self.mode = self.task_args.get("mode", None)
                if self.mode is None:
                    self.mode = 0  
                v=(self.vx**2+self.vy**2)**0.5
                t=self.dist/v
                pos_x=self.vx*t
                pos_y=self.vy*t
                theta=math.atan2(self.vy,self.vx)
                self.action_list.append(GoPath((pos_x,pos_y,theta),self.mode,max_speed=v))
                
                
            elif operation=='rotate':
                self.mode = self.task_args.get("mode", 0)
                Trace.log(f"mode is {self.mode}")
                # 获取底盘旋转参数

                self.robot_rotate_angle = self.task_args.get("robotRotateAngle", None)
                self.robot_rotate_speed = self.task_args.get("robotRotateSpeed", None)
                self.robot_rotate_direction = self.task_args.get("robotRotateDirection",None)
                self.is_debug = self.task_args.get("isDebug", False)

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
                    Navigation.setTaskError(
                        "No action parameters provided",
                        "No action parameters provided Set rotation angle or lift height Parameter validation"
                    )
                    self.script_status = ScriptStatus.FAILED
                    return
                #优先执行支持里程，定位模式的旋转动作
                if self.robot_rotate_angle is not None:
                    if not self.robot_rotate_direction:
                        if self.robot_rotate_speed is not None:
                            self.robot_rotate_direction = -1 if self.robot_rotate_speed > 0 else 1
                        else:
                            self.robot_rotate_direction =-1
                if self.robot_rotate_speed is None:
                    self.robot_rotate_speed = 30
                self.action_list.append(
                    Rotate(robot_rotate_angle=self.robot_rotate_angle, robot_direction=self.robot_rotate_direction,
                    speed_w_robot=self.robot_rotate_speed,  shelf_angle=self.shelf_rotate_angle, shelf_direction=self.shelf_rotate_direction, mode=self.mode,is_debug=self.is_debug))

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
                Trace.log(f"operation {operation} not support!")
                return
                

    def suspend(self):
        Module.setStatus(ScriptStatus.SUSPENDED)
        self.script_status = ScriptStatus.SUSPENDED
        Trace.log("suspend")

    def resume(self):
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            Module.setStatus(ScriptStatus.RUNNING)
            self.script_status = ScriptStatus.RUNNING
        Trace.log("resume")

    def cancel(self):
        Navigation.resetOdoMove()
        self.init_args = False
        self.action_id = 0
        self.action_list = []
        Module.setStatus(ScriptStatus.FAILED)
        self.script_status = ScriptStatus.FAILED
        Trace.log("cancel")
    



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
                Navigation.setTaskError(
                    "Action failed",
                    f"execute action {current_action} failed!  execute_actions"
                )
                self.script_status = ActionStatus.FAILED
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
            self.script_status = ActionStatus.FINISHED
            Module.setStatus(ScriptStatus.FINISHED)
            # self.action_list = []
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

        self.action_state['action_name'] = self.__class__.__name__
        self.action_state["action_args"] = self.action_args
        self.action_state['action_status'] = self.action_status
        self.action_state["action_runtime"] = time.time() - self.start_time
        

    def reset(self):
        pass


class Rotate(BaseAction):
    """旋转动作，支持底盘和托盘同时旋转或单独旋转"""

    def __init__(self, robot_rotate_angle=None, robot_direction=RotateDirection.NEARBY,
                 speed_w_robot=None, shelf_angle=None, shelf_direction=RotateDirection.NEARBY,mode=0,is_debug=False):
        super().__init__("Rotate")
        self.action_args = {
            "mode": mode,
            "robotRotateAngle": robot_rotate_angle,
            "robot_direction": robot_direction,
            "speed_w_robot": speed_w_robot,
            "shelf_angle": shelf_angle,
            "shelf_direction": shelf_direction,
            "mode": mode,
            "isDebug": is_debug
        }
        self.mode = mode
        self.action_status = ActionStatus.INIT
        self.init = True
        self.robot_direction = robot_direction
        self.shelf_direction = shelf_direction
        self.speed_w_robot = math.radians(speed_w_robot) if speed_w_robot is not None else 0.5
        self.is_debug = is_debug


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
        self.action_status = ActionStatus.RUNNING

        if self.init:
            self.init = False
            Navigation.resetRotateMove()
            self.rparams = dict()
            self.sparams = dict()
            if not self.is_debug:
                if self.robot_rotate_angle is not None:
                    while math.fabs(self.robot_rotate_angle) > math.pi:
                        self.robot_rotate_angle = math.fabs(self.robot_rotate_angle) - 2 * math.pi
                    self.rparams["moveAngle"] = self.robot_rotate_angle
                    self.rparams["dir"] = self.robot_direction
                    self.rparams["speedW"] = math.fabs(self.speed_w_robot)
                    if self.robot_direction == RotateDirection.NEARBY:
                        self.action_status = ActionStatus.FAILED
                        Navigation.setTaskError(
                            "Auto direction not supported",
                            "Auto direction not supported for robot rotation Set explicit rotation direction Parameter validation"
                        )
                        return self.action_status

                if self.shelf_angle is not None:
                    self.sparams["angle"] = self.shelf_angle
                    self.sparams["dir"] = self.shelf_direction
                    # if self.shelf_direction == RotateDirection.NEARBY:
                    #     self.action_status = ActionStatus.FAILED
                    #     Abnormal.setTask(53780, "不支持不指定方向旋转托盘",
                    #                      "Auto direction not supported for shelf rotation",
                    #                      "Set explicit rotation direction",
                    #                      "Parameter validation")
                    #     return self.action_status

                if self.shelf_angle is None and self.robot_rotate_angle is None:
                    self.action_status = ActionStatus.FAILED
                    Navigation.setTaskError(
                        "No rotation angle provided",
                        "No rotation angle provided Set robot or shelf rotation angle Parameter validation"
                    )
                    return self.action_status
            else:
                self.robot_rotate_angle = math.fabs(self.robot_rotate_angle)
                self.rparams["moveAngle"] = self.robot_rotate_angle
                self.rparams["speedW"] = self.speed_w_robot
                self.rparams["locMode"] = self.mode 
                
        if not self.is_debug:
            # 执行旋转
            print("DEBUG-----执行RotateMove,当前为旋转模式")
            self.action_status = Navigation.runRotateMove(
                robot_params=self.rparams if self.rparams else None,
                shelf_params=self.sparams if self.sparams else None
            )
        else:
            print("DEBUG-----执行OdoMove,当前为调试模式")
            self.action_status = Navigation.runOdoMove(
                self.rparams if self.rparams else None
            )
        self.action_state['action_name'] = self.__class__.__name__
        self.action_state["action_args"] = self.action_args
        self.action_state['rparams'] = self.rparams
        self.action_state['sparams'] = self.sparams
        self.action_state['action_status'] = self.action_status
        self.action_state["action_runtime"] = time.time() - self.start_time

        return self.action_status

class GoPath(BaseAction):
    """直线走到指定点"""

    def __init__(self, go_pos,mode=True,coordinate='robot', back_mode=False, is_hold_dir=None, max_speed=0.5, max_rot=0.3,
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
            "hold_dir": self.is_hold_dir,
            "coordinate": self.coordinate,
            "maxSpeed": self.max_speed,
            "maxRot": self.max_rot,
            "reachDist": self.path_dist_accuracy,
            "reachAngle": self.path_angle_accuracy,
            "useOdo": self.useOdo
        }
        print(f"参数：{args}")
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
            "rotSpeed": self.rot_speed,
            "maxRotAcc":0.05,
            "maxRotDec":0.05,
            "actionName": "ass"
        }


        print(f"参数：{self.arg},status:{self.action_status}")
        # self.arg={'rotDegree': 180.0, 'rotRadius': -1.0, 'rotSpeed': 0.3, 'actionName': 'GoLeftArc'}
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
        print(f"-------------------------status:{status}")
        if status in (ScriptStatus.RUNNING, ScriptStatus.NONE):
            input_params = Module.getTaskArgs()
            print("task args:", json.dumps(input_params, indent=2))
            # input_params = {
            #     "type": "Arc",
            #     "rotRadius": -1,
            #     "rotDegree": 360,
            #     "rotSpeed": -0.01,
            #     "mode": 1
            # }
            # input_params={
            #     "type" : "Line",
            #     "vx": 0.1,
            #     "vy": 0.1,
            #     "dist": 3,
            #     "mode": 1

            # }

            validated_params = {}
            input_params["operation"]=input_params.get("operation", 123)
            if input_params:
                try:
                    # 验证参数
                    validated_params = param_loader.loadInput(input_params)
                    print("check ok, args:", json.dumps(validated_params, indent=2))
                except ValueError as e:
                    print("check error:", e)
                    Navigation.setTaskError(
                        "Input parameters invalid",
                        f"Input error: {e} Some input params are not valid Check the input params Input validation"
                    )
            a.run(validated_params)

        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
                break

        time.sleep(0.1)

if __name__ == '__main__':
    main()