# -*- coding: utf-8 -*-
# @Date : 2025/08/19
# @Author : zengweibin
# @Coding : none
# @Update : 3.5顶升车示例模板

import json
import math
import time
from enum import IntEnum

from syspy.utils.time import Timer

start_time = time.time()

from syspy import (Module, Logger, Di, Do, Motor, Navigation, Loc, Abnormal, Recognize, ScriptStatus,
                   Odometer, Pgv, ScriptStatus, NetProtocol, Trace)
from syspy.lib.module import Pos2Base, Pos2World, ModuleBase, SafeMoveStatus
from tasks.standard import goPath,goBezier
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ParamServer
from syspy.lib.robot_param import RobotParam

log = Logger("jack")


# --- Module 类（放在前面） ---
class ConfigParams:
    """生成和定义配置参数的示例"""
    param_server = ParamServer(__file__)
    timeout = param_server.loadParam("timeout", type="int", default=120, maxValue=999, minValue=0, unit="s",
                                     group="", comment="脚本运行超时时间")
    # 是否有识别、二次调整
    is_recognize = param_server.loadParam("is_recognize", type="bool", default=True, comment="取货是否有识别")
    is_secondary_adjust = param_server.loadParam("is_secondary_adjust", type="bool", default=False,
                                                 comment="是否有二次调整")
    is_goods_qrcode = param_server.loadParam("goods_qrcode", type="bool", default=False,
                                             comment="放货时是否需要根据货物在托盘上的位置补偿AP点偏差")

    # 采用什么方式前往AP点
    how_go_site = param_server.loadParam("how_go_site", type="str", default="bezier",
                                         comment="采用直线(straight)、贝塞尔曲线(bezier)、2段直线(polyline)方式前往识别点")

    # 电机相关
    # jack_motor_name = param_server.loadParam("jack_motor_name", type="str", default="Motor-003", comment="顶升电机名称")
    module_type = RobotParam.getDevice("Model-000", "moduleType")
    jack_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.jackMotor")
    jack_motor_speed = param_server.loadParam("jack_motor_speed", type="float", default=0.015,
                                              comment="顶升电机升降速度")
    # jack_min_height = param_server.loadParam("jack_min_height", type="float", default=0.000, comment="顶升升降零位")
    # jack_max_height = param_server.loadParam("jack_max_height", type="float", default=0.03, comment="顶升抬升指定高度")
    motor_func = RobotParam.getDevice(f"{jack_motor_name}", "func")
    jack_min_height = RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.minLength")
    jack_max_height = RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.maxLength")
    robot_type = RobotParam.getDevice("Model-000", "getRobotType")
    jack_up_di = RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.upLimitDI")
    jack_zero_di = RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.zeroDI")
    spin_motor_name = param_server.loadParam("spin_motor_name", type="str", default="Motor-002",
                                             comment="托盘旋转电机名称")

    # 测试前近距离
    go_distance = param_server.loadParam("go_distance", type="float", default=0.5, comment="测试前进距离")

    log.debug("jack create config params")

def create_start_height(builder: ParamBuilder):
    with builder.CHILD(key="start_height", name="Start Height",
                       desc="The start height for operations"):
        builder.TYPE(ParamType.FLOAT)
        # builder.REQUIRED(True)
        builder.MIN_VALUE(ConfigParams.jack_min_height)
        builder.MAX_VALUE(ConfigParams.jack_max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.00)

def create_end_height(builder: ParamBuilder):
    """创建顶可被引用参数"""
    with builder.CHILD(key="end_height", name="End Height",
                       desc="The end height for operations"):
        builder.TYPE(ParamType.FLOAT)
        # builder.REQUIRED(True)
        builder.MIN_VALUE(ConfigParams.jack_min_height)
        builder.MAX_VALUE(ConfigParams.jack_max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.05)

def create_ap_id(builder: ParamBuilder):
    with builder.CHILD(key="AP_id", name="AP_id",
                       desc="the ap id for operation"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE("AP1")

def create_recfile(builder: ParamBuilder):
    with builder.CHILD(key="recfile", name="recfile", desc="file for recognize"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE("shelf-A.srec")
    with builder.CHILD(key="insert_shelf_dir", name="insert_shelf_dir", desc="direction to go under the shelf"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE("A")

def create_bezier(builder: ParamBuilder):
    with builder.CHILD(key="back_dist", name="back_dist", desc="the back dist for goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.0)
    with builder.CHILD(key="adjust_dist_for_curvature_limit", name="adjust_dist_for_curvature_limit",
                       desc="the adjust dist for decreasing curvature limit"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(2.0)
    with builder.CHILD(key="min_ahead_dist", name="min_ahead_dist", desc="the min ahead dist for goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.0)
    with builder.CHILD(key="is_backwards", name="is_backwards", desc="Backward or forward mode"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(False)
    with builder.CHILD(key="is_hold_dir", name="is_hold_dir", desc="whether the robot will hold direction"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(False)
    with builder.CHILD(key="max_speed", name="max_speed", desc="max_speed when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.5)
    with builder.CHILD(key="max_accele", name="max_accele", desc="max_acceleration when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.3)
    with builder.CHILD(key="max_decele", name="max_decele", desc="max_deceleration when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.2)
    with builder.CHILD(key="decele_dist", name="decele_dist",
                       desc="The speed will slow down after reaching this distance from the target point."):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(1)
    with builder.CHILD(key="curvature_limit", name="curvature_limit", desc="Curvature limits for Bezier paths"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(1.3)
    with builder.CHILD(key="path_dist_accuracy", name="curvature_limit",
                       desc="Position accuracy of Bezier curve for robot walking"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.01)
    with builder.CHILD(key="path_angle_accuracy", name="curvature_limit",
                       desc="angle accuracy of Bezier curve for robot walking"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.05)


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        # 公共参数:
        pass

        # 操作组合参数
        with builder.GROUP(key="operation", name="Task Operation", desc="Choose an operation for task"):
            builder.TYPE(ParamType.COMBO_BOX)

            with builder.CHILDREN():
                with builder.CHILD(key="getLM", name="getLM",
                                   desc="get the position of LM point"):
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

                # 识别取货
                with builder.CHILD(key="jackLoad", name="JackLoad", desc="recognize and load the shelf"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        create_ap_id(builder)
                        create_recfile(builder)

                # 识别放货
                with builder.CHILD(key="jackUnLoad", name="JackUnLoad", desc="recognize and unload the shelf"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        create_ap_id(builder)
                        create_recfile(builder)

                # 抬高托盘操作
                with builder.CHILD(key="jackHeight", name="JackHeight", desc="lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_end_height(builder)

                with builder.CHILD(key="jackMinHeight", name="JackMinHeight", desc="lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="goBezier", name="goBezier", desc="go bezier line to target position"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 旋转角度参数
                        create_ap_id(builder)
                        create_bezier(builder)

                with builder.CHILD(key="goPolyline", name="goPolyline", desc="go polyline line to target position"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 旋转角度参数
                        create_ap_id(builder)

                # JackSpin操作
                with builder.CHILD(key="spinAngle", name="spinAngle", desc="Spin the tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 旋转角度参数
                        with builder.CHILD(key="spin_angle", name="spin_angle", desc="the angle that the tray spin"):
                            builder.MIN_VALUE(-360)
                            builder.MAX_VALUE(360)
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("degree")
                            builder.DEFAULTVALUE(0)

                        with builder.CHILD(key="coordinate", name="coordinate", desc="Spin coordinate"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE("robot")

                            with builder.CHILDREN():
                                with builder.CHILD("robot", "robot", "robot"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("world", "world", "world"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("increase", "increase", "increase"):
                                    builder.TYPE(ParamType.STRING)

                        with builder.CHILD(key="spin_dir", name="spin_dir",
                                           desc="Spin direction(clockwise0/counterclockwise1/shortest2)"):
                            builder.MIN_VALUE(0)
                            builder.MAX_VALUE(2)
                            builder.TYPE(ParamType.INT)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE(2)

                with builder.CHILD(key="spinZero", name="spinZero", desc="Spin the tray to 0 degree"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="rotateHoldSpin", name="rotateHoldSpin", desc="Rotate the robot"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="spin_angle", name="spin_angle", desc="the angle that the tray spin"):
                        builder.MIN_VALUE(-360)
                        builder.MAX_VALUE(360)
                        builder.TYPE(ParamType.FLOAT)
                        builder.REQUIRED(True)
                        builder.UNIT("degree")
                        builder.DEFAULTVALUE(0)
                    with builder.CHILD(key="is_spin_follow", name="is_spin_follow",
                                       desc="whether the tray will follow"):
                        builder.TYPE(ParamType.BOOL)
                        builder.REQUIRED(True)
                        builder.DEFAULTVALUE(False)
                    with builder.CHILD(key="coordinate", name="coordinate", desc="Spin coordinate"):
                        builder.TYPE(ParamType.STRING_COMBO_LIST)
                        builder.DEFAULTVALUE("robot")

                        with builder.CHILDREN():
                            with builder.CHILD("robot", "robot", "robot"):
                                builder.TYPE(ParamType.STRING)
                            with builder.CHILD("world", "world", "world"):
                                builder.TYPE(ParamType.STRING)

                with builder.CHILD(key="goDist", name="goDist", desc="go straight distance"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILD(key="goPath_x", name="goPath_x",
                                       desc="The dist of the target point to which robot will go in a straight line"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.REQUIRED(True)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0)

                with builder.CHILD(key="goPath", name="goPath", desc="go straight to target position"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILD(key="goPath_x", name="goPath_x",
                                       desc="The coordinate x of the target point to which robot will go in a straight line"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.REQUIRED(True)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0)
                    with builder.CHILD(key="goPath_y", name="goPath_y",
                                       desc="The coordinate y of the target point to which robot will go in a straight line"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.REQUIRED(True)
                        builder.UNIT("m")
                        builder.DEFAULTVALUE(0)
                    with builder.CHILD(key="goPath_theta", name="goPath_theta",
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
                    with builder.CHILD(key="max_speed", name="max_speed", desc="max_speed when goPath"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.REQUIRED(False)
                        builder.DEFAULTVALUE(0.5)
                    with builder.CHILD(key="is_backwards", name="is_backwards", desc="Backward or forward mode"):
                        builder.TYPE(ParamType.BOOL)
                        builder.REQUIRED(False)
                        builder.DEFAULTVALUE(False)

                with builder.CHILD(key="PGVSecondaryAdjust", name="PGVSecondaryAdjust", desc="pgv secondary adjust"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="recTargetObs", name="recTargetObs", desc="recTargetObs"):
                    builder.TYPE(ParamType.ARRAY)
    builder.save_to_file()


class Jack(ModuleBase):
    def __init__(self):
        super().__init__()
        # 脚本任务管理
        # safe_move_check test
        self.count = 0
        # 脚本运行相关变量
        self.task_args = None
        self.init_args = False
        self.action_id = 0
        self.action_list = []
        self.operation_init = False
        # 定义动作相关的变量
        self.ap_world_pos = None  # 定义ap点在世界坐标系的位置
        self.ap_robot_pos = None  # 定义ap点在机器人坐标系的位置
        self.ap_id = None
        self.coordinate = None  # 定义坐标系
        self.spin_angle = None
        self.action_parameters = None  # vda
        self.opt = None
        self.recfile = None
        # 取货前调整托盘旋转
        self.global_spin_angle_before_jack = None
        self.increase_spin_angle_before_jack = None
        self.robot_spin_angle_before_jack = None
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

        log.info(f"module_type = {ConfigParams.module_type}")
        log.info(f"jack_motor_name = {ConfigParams.jack_motor_name}")
        log.info(f"jack_min_height = {ConfigParams.jack_min_height}")
        log.info(f"jack_max_height = {ConfigParams.jack_max_height}")
        log.info(f"robot_type = {ConfigParams.robot_type}")
        log.info(f"jack_up_di = {ConfigParams.jack_up_di}")
        log.info(f"jack_zero_di = {ConfigParams.jack_zero_di}")

        Module.set_status(ScriptStatus.NONE)

    def _init_args(self):
        if not self.init_args:
            self.init_args = True
            # 获取任务参数
            self.opt = self.task_args.get("operation", None)
            self.ap_id = self.task_args.get("AP_id", None)
            # 顶升高度相关
            self.start_height = self.task_args.get("start_height", None)
            self.end_height = self.task_args.get("end_height", None)
            # 识别相关
            self.recfile = self.task_args.get("recfile", None)
            self.insert_shelf_dir = self.task_args.get("insert_shelf_dir", "A")
            # spin,rotate相关
            self.spin_angle = self.task_args.get("spin_angle", 0)  # 角度
            rad = math.radians(self.spin_angle)  # 把spin_angle转为rad
            self.spin_angle = (rad + math.pi) % (2 * math.pi) - math.pi  # 归一化到 (-pi, pi]
            self.spin_dir = self.task_args.get("spin_dir", 0)
            self.coordinate = self.task_args.get("coordinate", "world")
            self.is_spin_follow = self.task_args.get("is_spin_follow", False)

            self.robot_spin_angle_before_jack = self.task_args.get("robot_spin_angle_before_jack", None)
            self.increase_spin_angle_before_jack = self.task_args.get("increase_spin_angle_before_jack", None)
            self.global_spin_angle_before_jack = self.task_args.get("global_spin_angle_before_jack", None)

            # Bezier相关
            self.back_dist = self.task_args.get("back_dist", None)
            self.adjust_dist_for_curvature_limit = self.task_args.get("adjust_dist_for_curvature_limit", None)
            self.min_ahead_dist = self.task_args.get("min_ahead_dist", None)
            self.is_backwards = self.task_args.get("is_backwards", None)
            self.is_hold_dir = self.task_args.get("is_hold_dir", None)
            self.max_speed = self.task_args.get("max_speed", None)
            self.max_accele = self.task_args.get("max_accele", None)
            self.max_decele = self.task_args.get("max_decele", None)
            self.decele_dist = self.task_args.get("decele_dist", None)
            self.curvature_limit = self.task_args.get("curvature_limit", None)
            self.path_dist_accuracy = self.task_args.get("path_dist_accuracy", None)
            self.path_angle_accuracy = self.task_args.get("path_angle_accuracy", None)

            # goPath相关
            self.goPath_x = self.task_args.get("goPath_x", None)
            self.goPath_y = self.task_args.get("goPath_y", None)
            self.goPath_theta = self.task_args.get("goPath_theta", None)

    def run(self, args):
        # 获取输入参数
        Module.set_status(ScriptStatus.RUNNING)
        self.task_args = args
        print(f"self.task_args={self.task_args}")
        self._init_args()

        self.set_vda_param()
        # 选择执行动作
        if self.opt == "jackLoad":  # 识别/非识别取货
            self.jack_load()
        elif self.opt == "jackUnload":  # 识别/非识别放货
            self.jack_unload()
        elif self.opt == "jackBezierReturn":
            self.jack_bezier_return()
        elif self.opt == "getLM":
            self.get_lm()
        elif self.opt == "goAPSite":  # 前往ap点，直线，bezier，两段线
            self.go_ap_site()
        elif self.opt == "goBezier":
            self.go_bezier()
        elif self.opt == "goPolyline":
            self.go_polyline()
        elif self.opt == "jackHeight":  # 控制托盘抬升高度
            self.jack_height()
        elif self.opt == "jackMinHeight":  # 控制托盘高度降到最低
            self.jack_min_height()
        elif self.opt == "spinAngle":  # 托盘旋转指定角度
            self.spin()
        elif self.opt == "spinZero":  # 托盘旋转到0度
            self.spin_zero_deg()
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
        elif self.opt == "getRobotData":
            self.get_robot_data()
        elif self.opt == "recTargetObs":
            self.rec_target_obs()
        else:
            Module.set_status(ScriptStatus.FAILED)

        log.info(f"self.action_list: {self.action_list}")
        self._execute_actions()

    def rec_target_obs(self):
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(RecTargetObs())

    def set_vda_param(self):
        # VDA下发的参数
        self.action_parameters = self.task_args.get("action_parameters", None)

    def get_lm(self):
        log.info("getLM ==============================================")
        result = Navigation.getLM("LM1", True)
        self.report_info["getLM"] = {
            "LM":result
        }
        Module.report_info(self.report_info)
        log.info("getLM", result)
        Module.set_status(ScriptStatus.FINISHED)
        return Module.get_status()

    def jack_bezier_return(self):
        if not self.operation_init:
            self.operation_init = True

            # 获取AP点坐标
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            self.ap_robot_pos = Navigation.getLM(self.ap_id, False)
            robot_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], Loc.get_pose()["yaw"]]
            ap_to_robot_angle = math.atan2(self.ap_world_pos[1] - robot_loc[1], self.ap_world_pos[0] - robot_loc[0])
            log.info(f'AP_pos: {self.ap_world_pos}')
            log.info(f'ap_to_robot_angle: {ap_to_robot_angle}')

            self.report_info["jack_load"] = {
                "ap_to_robot_angle": ap_to_robot_angle,
                "robot_loc": robot_loc,
                "ap_world_pos": self.ap_world_pos
            }

            # 第一步转到指向ap点的方向
            self.action_list.append(RobotRotate(ap_to_robot_angle, Coordinate.WORLD, False))

            # 第二步判断是否有识别
            # 如果有识别
            # 转到指向ap点的位置
            self.action_list.append(RecShelf(self.recfile, "FirstRec"))  # 识别货架，得到坐标放入j.rec_result

        # 动态添加action_list
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            log.info(f'{self.action_id=}, {self.action_list=}')
            log.info(f'{current_action.action_name=}, {current_action.action_status=}')

            if current_action.action_name == "FirstRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                robot_pos = [Loc.get_pose()["x"],Loc.get_pose()["y"],Loc.get_pose()["yaw"]]
                result_robot = Pos2Base(result_world, robot_pos)

                # 如果离shelf太近，先后退一段距离再第二次识别（离太近可能存在偏差）
                if result_robot[0] < 1:
                    log.info(f'{current_action.action_name=}')
                    self.action_list.append(GoPath([-0.3, 0, 0], Coordinate.ROBOT, 0.2, True))
                    self.action_list.append(RecShelf(self.recfile, "SecondRec"))  # 识别货架，得到坐标放入j.rec_result
                else:
                    self.action_list.append(
                        GoBezier(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                                 self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                                 self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                                 self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))

            if current_action.action_name == "SecondRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                self.action_list.append(
                    GoBezier(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                             self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                             self.max_speed, self.max_accele, self.max_decele, self.decele_dist, self.curvature_limit,
                             self.path_dist_accuracy, self.path_angle_accuracy))

            if current_action.action_name == "RecordBezierPath" and current_action.action_status == ActionStatus.FINISHED:
                self.action_list.append(JackHeight(ConfigParams.jack_motor_name, self.end_height,
                                                   ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))
                self.action_list.append(JackMinHeight(ConfigParams.jack_motor_name, ConfigParams.jack_motor_speed))
                self.action_list.append(
                    GoBezierReturn(self.is_backwards, self.is_hold_dir, self.max_speed,
                                   self.max_accele, self.max_decele, self.decele_dist))

    def jack_load(self):
        # =====完整：旋转车体调整对准——识别货架——导航——二次调整——顶起 流程=====
        if not self.operation_init:
            self.operation_init = True

            # 获取AP点坐标
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            self.ap_robot_pos = Navigation.getLM(self.ap_id, False)
            robot_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], Loc.get_pose()["yaw"]]
            ap_to_robot_angle = math.atan2(self.ap_world_pos[1] - robot_loc[1], self.ap_world_pos[0] - robot_loc[0])
            log.info(f'AP_pos: {self.ap_world_pos}')
            log.info(f'ap_to_robot_angle: {ap_to_robot_angle}')

            self.report_info["jack_load"] = {
                "ap_to_robot_angle": ap_to_robot_angle,
                "robot_loc": robot_loc,
                "ap_world_pos": self.ap_world_pos
            }

            # 第一步转到指向ap点的方向
            self.action_list.append(RobotRotate(ap_to_robot_angle, Coordinate.WORLD, False))

            # 第二步判断是否有识别
            # 如果有识别 # 改为输入参数n
            if ConfigParams.is_recognize:  # 要求启用识别时必须有recfile
                # 转到指向ap点的位置
                self.action_list.append(RecShelf(self.recfile, "FirstRec"))  # 识别货架，得到坐标放入j.rec_result

            else:
                # 如果没有识别，直接前进到任务的AP点坐标
                if ConfigParams.how_go_site == "straight":
                    self.action_list.append(GoPath(self.ap_world_pos, Coordinate.WORLD))
                elif ConfigParams.how_go_site == "bezier":
                    self.action_list.append(GoBezier(self.ap_world_pos))
                elif ConfigParams.how_go_site == "polyline":
                    self.action_list.append(GoPolylineNew(self.ap_world_pos))
                self.jack_load_adjust_and_jack()  # 加入二次调整，取货前托盘调整，抬升托盘动作

        # 动态添加action_list
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            log.info(f'{self.action_id=}, {self.action_list=}')
            log.info(f'{current_action.action_name=}, {current_action.action_status=}')

            if current_action.action_name == "FirstRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                robot_pos = [Loc.get_pose()["x"], Loc.get_pose()["y"], Loc.get_pose()["yaw"]]
                result_robot = Pos2Base(result_world, robot_pos)

                # 如果离shelf太近，先后退一段距离再第二次识别（离太近可能存在偏差）
                if result_robot[0] < 1:
                    log.info(f'{current_action.action_name=}')
                    self.action_list.append(GoPath([-0.3, 0, 0], Coordinate.ROBOT, 0.2, True))
                    self.action_list.append(RecShelf(self.recfile, "SecondRec"))  # 识别货架，得到坐标放入j.rec_result
                else:
                    self.action_list.append(GoBezier(result_world))
                    # self.jack_load_adjust_and_jack()  # 加入二次调整，取货前托盘调整，抬升托盘动作
                    self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_max_height,
                                                       ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))
                    self.action_list.append(JackMinHeight(ConfigParams.jack_motor_name, ConfigParams.jack_motor_speed))

            if current_action.action_name == "SecondRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                self.action_list.append(GoBezier(result_world))
                # self.jack_load_adjust_and_jack() # 加入二次调整，取货前托盘调整，抬升托盘动作
                self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_max_height,
                                                   ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))
                self.action_list.append(JackMinHeight(ConfigParams.jack_motor_name, ConfigParams.jack_motor_speed))

    def jack_load_adjust_and_jack(self):
        # 到达货物下方，第三步判断是否有上下视pgv二次调整
        if ConfigParams.is_secondary_adjust:
            self.action_list.append(GetPGVData())
            self.action_list.append(PGVSecondaryAdjust())

        # 第四步在取货前旋转托盘角度，根据输入的参数决定如何调整
        if self.robot_spin_angle_before_jack is not None:
            self.robot_spin_angle_before_jack = math.pi * self.robot_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.robot_spin_angle_before_jack, "robot", self.spin_dir))
        if self.increase_spin_angle_before_jack is not None:
            self.increase_spin_angle_before_jack = math.pi * self.increase_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.increase_spin_angle_before_jack, "increase", 0))
        if self.global_spin_angle_before_jack is not None:
            self.global_spin_angle_before_jack = math.pi * self.global_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.global_spin_angle_before_jack, "world", self.spin_dir))

        # 抬升托盘取货
        self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_max_height,
                                           ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))
        log.info(f"self.action_list: {self.action_list}")

    def jack_unload(self):
        if not self.operation_init:
            self.operation_init = True

            # 第一步判断是否有识别
            if ConfigParams.is_recognize:  # 要求启用识别时必须有recfile
                self.action_list.append(RecShelf(self.recfile))  # 识别货架，得到坐标放入self.rec_result
            else:
                # 在动作类内部选择直线、贝塞尔+直线、二段直线方式前往识别点
                # 第二步选择是否需要根据货物下方的二维码调整放货位置
                if ConfigParams.is_goods_qrcode:
                    self.action_list.append(GetApPosAdjustedViaPgv())  # 前往识别点,并根据货物二维码调整放货坐标
                else:
                    if not self.ap_id:
                        self.ap_id = Navigation.moveTask().get("target_name", None)
                        self.ap_id = "AP" + str(self.ap_id)
                    self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
                    log.info(f'AP_pos: {self.ap_world_pos}')
                    if ConfigParams.how_go_site == "straight":
                        self.action_list.append(GoPath(self.ap_world_pos, Coordinate.WORLD))
                    elif ConfigParams.how_go_site == "bezier":
                        self.action_list.append(GoBezier(self.ap_world_pos))
                    elif ConfigParams.how_go_site == "polyline":
                        self.action_list.append(GoPolylineNew(self.ap_world_pos))
                # 加入后续动作
                self.jack_unload_adjust_and_jack()

        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_name == "RecShelf" and current_action.action_status == ActionStatus.FINISHED:
                result = self.rec_result
                self.action_list.append(GoBezier(result))
                # 加入后续动作
                self.jack_unload_adjust_and_jack()

    def jack_unload_adjust_and_jack(self):
        # 到达放货点，第三步判断是否有下视pgv二次调整
        if ConfigParams.is_secondary_adjust:
            self.action_list.append(GetPGVData())
            self.action_list.append(PGVSecondaryAdjust())

        # 第四步在放货前旋转托盘角度，根据输入的参数决定如何调整
        if self.robot_spin_angle_before_jack is not None:
            self.robot_spin_angle_before_jack = math.pi * self.robot_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.robot_spin_angle_before_jack, "robot", self.spin_dir))
        if self.increase_spin_angle_before_jack is not None:
            self.increase_spin_angle_before_jack = math.pi * self.increase_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.increase_spin_angle_before_jack, "increase", 0))
        if self.global_spin_angle_before_jack is not None:
            self.global_spin_angle_before_jack = math.pi * self.global_spin_angle_before_jack / 180
            self.action_list.append(
                Spin(self.global_spin_angle_before_jack, "world", self.spin_dir))

        # 放货
        self.action_list.append(JackMinHeight(ConfigParams.jack_motor_name, ConfigParams.jack_motor_speed))

    def go_ap_site(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            log.info(f'AP_pos: {self.ap_world_pos}')
            if ConfigParams.how_go_site == "straight":
                self.action_list.append(GoPath(self.ap_world_pos, Coordinate.WORLD))
            elif ConfigParams.how_go_site == "bezier":
                self.action_list.append(GoBezier(self.ap_world_pos))
            elif ConfigParams.how_go_site == "polyline":
                self.action_list.append(GoPolylineNew(self.ap_world_pos))

    def go_bezier(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            log.info(f'AP_pos: {self.ap_world_pos}')
            self.action_list.append(
                GoBezier(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit, self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                 self.max_speed, self.max_accele, self.max_decele, self.decele_dist, self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))

        # 动态添加action_list
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            log.info(f'{self.action_id=}, {self.action_list=}')
            log.info(f'{current_action.action_name=}, {current_action.action_status=}')

            if current_action.action_name == "GoBezierWorld" and current_action.action_status == ActionStatus.FINISHED:
                self.action_list.append(
                    GoBezierReturn(self.is_backwards, self.is_hold_dir, self.max_speed, self.max_accele, self.max_decele, self.decele_dist))

    def go_polyline(self):
        if not self.operation_init:
            self.operation_init = True
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在机器人坐标系下的位置
            log.info(f'AP_pos: {self.ap_world_pos}')
            self.action_list.append(GoPolylineNew(self.ap_world_pos))

    def go_map_path(self):
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(GoMapPath())

    def jack_height(self):
        """抬升托盘到指定高度"""
        if not self.operation_init:
            self.operation_init = True

            # self.action_list.append(JackHeight(ConfigParams.jack_motor_name, self.end_height,
            #                                    ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))
            self.action_list.append(JackHeight(ConfigParams.jack_motor_name, self.end_height,
                                               ConfigParams.jack_motor_speed, 3))

    def jack_min_height(self):
        """放货至最低点"""
        if not self.operation_init:
            self.operation_init = True

            self.action_list.append(JackMinHeight(ConfigParams.jack_motor_name, ConfigParams.jack_motor_speed))

    def spin(self):
        """旋转托盘"""
        if not self.operation_init:
            self.operation_init = True
            print("进入spin动作")
            self.action_list.append(Spin(self.spin_angle, self.coordinate, self.spin_dir))

    def spin_zero_deg(self):
        """旋转托盘到0度位置"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(Spin(0, "robot", 2))

    def rotate_hold_spin(self):
        """旋转托盘时启动随动"""
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
                GoPath([self.goPath_x, self.goPath_y, self.goPath_theta], self.coordinate, self.max_speed,
                       self.is_backwards))

    def rec_shelf(self):
        """识别货架"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(RecShelf(self.recfile))  # 导航到终点

    def pgv_adjust(self):
        """二次调整"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(GetPGVData())
            self.action_list.append(PGVSecondaryAdjust())

    def get_robot_data(self):
        """获取设备数据"""
        self.lift_motor = RobotParam.getDevice("Motor-003", "moduleType")

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
                self.script_status = ActionStatus.FAILED
                Module.set_status(ScriptStatus.FAILED)
            else:
                current_action.run(self)
        else:
            self.script_status = ActionStatus.FINISHED
            Module.set_status(ScriptStatus.FINISHED)
            self.action_list = []
        log.info(f'{self.action_id=}, {self.action_list=}')
        log.info(f"self.action_list: {self.action_list}")

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.info(f"{self.task_args=}")
        log.info(f"{Module.get_task_id()=}")
        log.info(f"{Module.get_status()=}")

    def suspend(self):
        Module.set_status(ScriptStatus.SUSPENDED)
        log.info("suspend")

    def resume(self):
        if Module.get_status() == ScriptStatus.SUSPENDED:
            Module.set_status(ScriptStatus.RUNNING)
        log.info("resume")

    def cancel(self):
        Module.set_status(ScriptStatus.FAILED)
        log.info("cancel")

    def safe_move_check(self):
        self.count += 1
        status = SafeMoveStatus.RUNNING
        if self.count == 10:
            self.count = 0
            status = SafeMoveStatus.FINISHED
        self.set_safe_move_status(status)
        Trace.log(f"safe_move_check {Module.get_safe_move_check()}")
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False

    def modbus(self):
        # 模拟映射表
        modbus_data2args = {
            "1": {
                "height": 0.1
            },
            "2": {
                "height": 0.1
            },
            "3": {
                "spinAngle": 90
            },
            "4": {
                "operation": "spinAngle",
                "spin_angle": 30,
                "spin_dir": 2,
                "coordinate":"increase"
            }
        }
        # 读取数据
        # modbus_data = NetProtocol.getModbusData("3x", 0, 1)
        modbus_data = ["4"]
        # 解析映射表
        args = modbus_data2args.get(modbus_data[0])
        log.info(f"---------------------------------modbus_args={args}")
        status = Module.get_status()
        Module.set_status(ScriptStatus.RUNNING)
        # if status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
        #     self.event_modbus = False
        # 做对应的动作
        return args

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


class Spin(BaseAction):  # 托盘旋转到机器人/世界坐标系下固定角度
    def __init__(self, angle, coordinate="world", direction=2):
        super().__init__("Spin")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.angle = angle
        self.dir = direction  # 0 counterclockwise; 1 clockwise; 2 shortest
        self.coordinate_system = coordinate

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            if self.coordinate_system == "robot":
                Navigation.setRobotSpinAngle(self.angle, self.dir)
                log.info("setRobotSpinAngle")
            elif self.coordinate_system == "world":
                Navigation.setGlobalSpinAngle(self.angle, self.dir)
                log.info("setGlobalSpinAngle")
            elif self.coordinate_system == "increase":
                Navigation.setIncreaseSpinAngle(self.angle)
                log.info("setIncreaseSpinAngle")
        if Navigation.spinRun():
            self.action_status = ActionStatus.FINISHED
        log.info(f"弧度{self.angle=}")
        log.info(f"坐标系{self.coordinate_system=}")

        self.action_state['spin_state'] = self.action_status
        self.action_state['spin_angle'] = self.angle
        self.action_state['spin_direction'] = self.dir

        j.report_info["Spin"] = {
            "action_status": self.action_status,
            "spin_angle": self.angle,
            "coordinate": self.coordinate_system,
            "direction": self.dir
        }
        Module.report_info(j.report_info)

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class RobotRotate(BaseAction):
    """只转车不转托盘"""

    def __init__(self, angle, coordinate, spin=True, direction=2):
        super().__init__("RobotRotate")
        self.action_status = ActionStatus.INIT
        self.init = True

        self.angle = angle
        self.coordinate = coordinate
        self.spin = spin
        self.direction = direction  # 0 counterclockwise; 1 clockwise; 2 shortest
        self.speed = 0.7
        self.move_args = dict()
        self.robot_ang = []

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            Navigation.resetOdoMove()
            self.move_args['spin'] = self.spin  # 是否随动
            self.move_args['speed_w'] = self.speed
            if self.coordinate == Coordinate.ROBOT:
                self.move_args['loc_mode'] = 0  # 基于里程定位
                self.move_args['move_angle'] = self.angle
                if self.angle < 0:
                    self.move_args['move_angle'] = -self.angle
                    self.move_args['speed_w'] = -self.speed
            elif self.coordinate == Coordinate.WORLD:
                self.move_args["loc_mode"] = 1  # 激光定位

                # ① 当前朝向：Loc 返回的是度 → 立即转弧度 → 归一化
                cur_angle_rad = self.normalize(math.radians(Loc.get_pose()["yaw"]))

                # ② 目标朝向：假设外部传进来是“度”——> 先转弧度，再归一化
                target_rad = self.normalize(math.radians(self.angle) if abs(self.angle) > math.pi else self.angle)

                # ③ 差值也要再归一化一次，确保 (-π, π]
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

                # ④ 最终写回 move_args（注意 move_angle 一律为正幅值）
                self.move_args.update({
                    "spin": self.spin,
                    "speed_w": speed_w,
                    "move_angle": move_ang
                })

        status = Navigation.runOdoMove(self.move_args)
        log.info(f"{status=}")
        if status == ActionStatus.FINISHED:
            self.action_status = ActionStatus.FINISHED

        j.report_info["RobotRotate"] = {
            "action_status": self.action_status,
            "is_spin_held": self.move_args['spin'],
            "angle": self.angle,
            "coordinate": self.coordinate,
            "direction": self.direction
        }
        Module.report_info(j.report_info)

    def reset(self):
        Navigation.resetOdoMove()
        log.info("reset RobotRotate")
        self.action_status = ActionStatus.RUNNING

    def normalize(self, rad: float) -> float:
        """把任意弧度角归一化到 (-π, π] 区间"""
        return (rad + math.pi) % (2 * math.pi) - math.pi


class JackHeight(BaseAction):
    """顶升动作，通过设置电机位置实现顶升"""

    def __init__(self, motor_name, target_height, jack_motor_speed, jack_up_di):
        super().__init__("JackHeight")
        self.motor_name = motor_name
        self.target_height = target_height
        self.jack_motor_speed = jack_motor_speed
        self.jack_up_di = jack_up_di
        self.init = False
        Motor.resetMotor(self.motor_name)

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            Motor.setMotorPosition(self.motor_name, self.target_height, self.jack_motor_speed, self.jack_up_di)
            Navigation.setGoodsShape(0, 0, 0)
        motor_info = Odometer.get_motor_infos()
        log.info(f"{motor_info=}")
        log.info(f"{self.target_height=}")

        if Motor.isMotorReached(self.motor_name) or Di.get_di(ConfigParams.jack_up_di):
            self.action_status = ActionStatus.FINISHED
            Motor.resetMotor(self.motor_name)

        j.report_info["JackHeight"] = {
            "action_status": self.action_status,
            "motor_name": self.motor_name,
            "target_height": self.target_height,
            "jack_motor_speed": self.jack_motor_speed,
            "jack_up_di": self.jack_up_di
        }
        Module.report_info(j.report_info)


class JackMinHeight(BaseAction):
    """顶升动作，通过设置电机位置实现顶升"""

    def __init__(self, motor_name, jack_motor_speed):
        super().__init__("JackMinHeight")
        self.motor_name = motor_name
        self.jack_motor_speed = jack_motor_speed
        self.init = False
        Motor.resetMotor(self.motor_name)

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
        Motor.setMotorPosition(self.motor_name, ConfigParams.jack_min_height, self.jack_motor_speed,
                               ConfigParams.jack_zero_di)
        motor_info = Odometer.get_motor_infos()
        log.info(f"{motor_info=}")
        log.info(f"Lowering tray")

        if Motor.isMotorReached(self.motor_name) or Di.get_di(ConfigParams.jack_zero_di):
            self.action_status = ActionStatus.FINISHED
            Navigation.clearGoodsShape()
            Motor.resetMotor(self.motor_name)

        j.report_info["JackMinHeight"] = {
            "action_status": self.action_status,
            "motor_name": self.motor_name,
            "jack_min_height": ConfigParams.jack_min_height,
            "jack_motor_speed": self.jack_motor_speed,
            "jack_zero_di": ConfigParams.jack_zero_di
        }
        Module.report_info(j.report_info)


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
        finished = Navigation.goMapPath(json.dumps(self.task))
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

        Module.report_info({"GoStraightDist": {"status": self.action_status}})
        Module.report_info({"GoStraightDist": {"go_dist": self.go_dist}})


class GoPath(BaseAction):
    """直线走到指定点"""

    def __init__(self, go_pos, coordinate='robot', max_speed=0.5, back_mode=False):
        super().__init__("GoPath")

        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_pos = go_pos
        self.coordinate = coordinate
        self.max_speed = max_speed
        self.back_mode = back_mode
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
            "maxSpeed": self.max_speed,
            "maxRot": 0.3,
            "coordinate": self.coordinate
        }
        self.action_status = self.go_path.run(args)

        j.report_info["GoPath"] = {
            "action_status": self.action_status,
            "go_pos": self.go_pos,
            "coordinate": self.coordinate,
            "max_speed": self.max_speed,
            "back_mode": self.back_mode
        }
        Module.report_info(j.report_info)


class GoBezierCombined(BaseAction):
    """执行行走贝塞尔曲线到达取货点"""
    def __init__(self, target_world, back_dist=0.0, adjust_dist_for_curvature_limit=2, min_ahead_dist=0, is_backwards=False,
                 max_speed=0.3, max_accele=0.3, max_decele=0.2, decele_dist=1,curvature_limit=1.3, path_dist_accuracy=0.01,
                 path_angle_accuracy=0.05):
        super().__init__()
        self.init = True
        self.action_status = ActionStatus.INIT
        self.bezier_status = ActionStatus.INIT
        self.bezier_return_status = ActionStatus.INIT
        self.go_bezier = goBezier.GoBezierWorld(target_world, back_dist, adjust_dist_for_curvature_limit,
                                                    min_ahead_dist, is_backwards, max_speed, max_accele, max_decele, decele_dist,
                                                    curvature_limit, path_dist_accuracy, path_angle_accuracy)
        self.go_bezier_return = goBezier.GoBezierWorldReturn(False)

    def run(self, j:Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

        if self.bezier_status in (ActionStatus.INIT, ActionStatus.RUNNING):
            self.bezier_status = self.go_bezier.run()
            log.info(f"bezier_status={self.bezier_status}")
        elif self.bezier_status == ActionStatus.FAILED:
            self.action_status = ActionStatus.FAILED
        elif self.bezier_status == ActionStatus.FINISHED:
            if self.bezier_return_status in (ActionStatus.INIT, ActionStatus.RUNNING):
                self.bezier_return_status = self.go_bezier_return.run()
                log.info(f"bezier_return_status={self.bezier_return_status}")
            elif self.bezier_return_status == ActionStatus.FAILED:
                self.action_status = ActionStatus.FAILED
            elif self.bezier_return_status == ActionStatus.FINISHED:
                self.action_status = ActionStatus.FINISHED
        time.sleep(0.1)


class GoBezier(BaseAction):
    """执行行走贝塞尔曲线到达取货点"""
    def __init__(self, target_world, back_dist=0.0, adjust_dist_for_curvature_limit=2, min_ahead_dist=0.0, is_backwards=False, is_hold_dir=None,
                 max_speed=0.3, max_accele=0.3, max_decele=0.2, decele_dist=0.1, curvature_limit=1.3, path_dist_accuracy=0.01, path_angle_accuracy=0.05):
        super().__init__()
        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_bezier = goBezier.GoBezierWorld(target_world, back_dist, adjust_dist_for_curvature_limit, min_ahead_dist,
                                                is_backwards, is_hold_dir, max_speed, max_accele, max_decele, decele_dist,
                                                curvature_limit, path_dist_accuracy, path_angle_accuracy)

    def run(self, j:Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

        if self.action_status in (ActionStatus.INIT, ActionStatus.RUNNING):
            self.action_status = self.go_bezier.run()
        log.info(f"bezier_status={self.action_status}")
        time.sleep(0.1)


class GoBezierReturn(BaseAction):
    """执行行走贝塞尔曲线到达取货点"""
    def __init__(self, is_backwards=True, is_hold_dir=None, max_speed=0.3, max_accele=1, max_decele=0.7, decele_dist=0.1):
        super().__init__()
        self.init = True
        self.action_status = ActionStatus.INIT
        self.go_bezier_return = goBezier.GoBezierWorldReturn(is_backwards, is_hold_dir, max_speed, max_accele, max_decele, decele_dist)

    def run(self, j:Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING

        if self.action_status in (ActionStatus.INIT, ActionStatus.RUNNING):
            self.action_status = self.go_bezier_return.run()
        log.info(f"bezier_return_status={self.action_status}")
        time.sleep(0.1)

class GoPolylineNew(BaseAction):
    def __init__(self, world_target, min_ahead_dist=0, ahead_dist=0, back_dist=0, speed=0.5, max_angle=0.5, dec_dist=1):
        """
        target_world, back_dist = 0.0, adjust_dist_for_curvature_limit = 2, min_ahead_dist = 0, is_backwards = False,
        max_speed = 0.5, max_accele = 0.3, max_decele = 0.2, decele_dist = 1, curvature_limit = 1.3
        """
        super().__init__()
        self.go3 = None
        self.go2 = None
        self.go1 = None
        self.temp_start = []
        self.first_point = None
        self.start_pos = []
        self.world_target = world_target
        self.min_ahead_dist = min_ahead_dist
        self.ahead_dist = ahead_dist
        self.back_dist = back_dist
        self.speed = speed
        self.max_angle = max_angle
        self.dec_dist = dec_dist
        self.step = 20
        self.second_point = Pos2World([self.min_ahead_dist, 0, 0], self.world_target)
        self.third_point = Pos2World([-self.back_dist, 0, 0], self.world_target)
        self.go_step = [False] * 3
        self.action_status = ActionStatus.INIT
        self.init = False

    def run(self, f):
        if not self.init:
            self.init = True
            pos = Loc.get_data()
            self.start_pos = [pos['x'], pos['y'], pos['angle']]
            if abs(self.cal_angle(self.start_pos, self.second_point)) > self.max_angle:
                self.start_pos[2] = self.world_target[2]
                angle, self.temp_start = self.search_min_angle_str(self.max_angle, self.step)
            else:
                self.temp_start = self.start_pos
            go1_args = {
                "x": self.temp_start[0],
                "y": self.temp_start[1],
                "theta": self.temp_start[2],
                "backMode": 0,
                "maxSpeed": 0.2,
                "maxRot": math.radians(10),
                "coordinate": Coordinate.WORLD
            }
            self.go1 = GoPath(go1_args)
            go2_args = {
                "x": self.second_point[0],
                "y": self.second_point[1],
                "theta": self.second_point[2],
                "backMode": 1,
                "maxSpeed": 0.1,
                "maxRot": math.radians(10),
                "coordinate": Coordinate.WORLD
            }
            self.go2 = GoPath(go2_args)
            go3_args = {
                "x": self.third_point[0],
                "y": self.third_point[1],
                "theta": self.third_point[2],
                "backMode": 1,
                "maxSpeed": 0.1,
                "maxRot": math.radians(10),
                "coordinate": Coordinate.WORLD
            }
            self.go3 = GoPath(go3_args)

        if not self.go_step[0]:
            if self.go1.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go1.run(f)
            if self.go1.action_status == ActionStatus.FINISHED:
                self.go_step[0] = True
        elif self.go_step[0] and not self.go_step[1]:
            if self.go2.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go2.run(f)
            if self.go2.action_status == ActionStatus.FINISHED:
                self.go_step[1] = True
        elif self.go_step[1] and not self.go_step[2]:
            if self.go3.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go3.run(f)
            if self.go3.action_status == ActionStatus.FINISHED:
                self.go_step[2] = True
        if all(self.go_step):
            self.action_status = ActionStatus.FINISHED

    def cal_angle(self, start_pos, end_pos):
        start2end = Pos2Base(start_pos, end_pos)
        angle = math.degrees(math.atan2(start2end[1], start2end[0]))
        print(angle)
        return angle

    def search_min_angle_str(self, max_angle, step):
        for n in range(1, step + 1):
            adjust_dist = self.ahead_dist / self.step * n
            # 临时构造一个新的起点：在原 start_pos 基础上往前平移
            temp_start = Pos2World([adjust_dist, 0, 0], self.start_pos)
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


class Rec(BaseAction):
    def __init__(self, recfile, action_name="RecShelf"):
        super().__init__(action_name)
        self.init = False
        self.rec_status = None
        self.result = dict()
        self.action_status = ActionStatus.INIT
        self.recfile = recfile
        self.attempts = 0
        self.max_attempts = 3
        self.success = False
        self.results = list

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.success = False

        self.action_status = ActionStatus.RUNNING
        if not self.success:
            self.success, self.rec_status, self.results = self.rec(self.recfile)
        else:
            # 处理识别结果，并按降序排序，z值最大的结果在前
            results = self.results.get("reco_list", [])
            z_max_results = sorted(results, key=lambda item: item['z'])
            self.result = z_max_results[0]
            j.rec_result = self.result
            self.action_status = ActionStatus.FINISHED

        j.report_info["RecShelf"] = {
            "action_status": self.action_status,
            "rec_result": j.rec_result,
            "recfile": self.recfile,
            "rec_status": self.rec_status,
            "rec_times": self.attempts
        }
        Module.report_info(j.report_info)

    def reset(self):
        Recognize.resetRec()
        self.action_status = ActionStatus.RUNNING

    def rec(self, recfile):
        rec_status = Recognize.getRecStatus()
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            log.debug("rec_result:{}".format(rec_result))
            print(rec_result)
            return True, rec_status, rec_result
        elif rec_status in (-1, 3):
            if Timer.delay(0.05):
                self.attempts += 1
                if self.attempts > self.max_attempts:
                    self.action_status = ActionStatus.FAILED
                    Abnormal.setTask(53781,
                                     "Recognition failed, the maximum number of retries exceeded",
                                     "The recognition distance may be too close or too far, or the sensor used for recognition may be faulty",
                                     "Check whether the recognition distance is too close or too far and whether the sensor used for recognition is normal.",
                                     "Recognize the recTarget")
                else:
                    Recognize.resetRec()
        else:
            Recognize.doRec(recfile)
            Timer.delay(0.05)
        return False, rec_status, list


class RecShelf(BaseAction):
    """识别货架"""

    def __init__(self, shelf_file, action_name="RecShelf"):
        super().__init__(action_name)
        self.action_status = ActionStatus.INIT
        self.recfile = shelf_file
        self.attempts = 0
        self.max_attempts = 3
        Recognize.resetRec()
        self.report_info = {}

    def run(self, j: Jack):
        self.action_status = ActionStatus.RUNNING
        log.info("recognizing the shelf")
        rec_status = Recognize.getRecStatus()
        log.info(f"{rec_status=}")
        # rec_result = Recognize.getRecFile(self.recfile)  # 读到识别文件原始数据
        # log.info(f"{rec_result=}")
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            log.info(f"{rec_result=}")
            Recognize.resetRec()
            log.info(f"rec_result={rec_result}")
            rec_x = rec_result['reco_list'][0]['x']
            rec_y = rec_result['reco_list'][0]['y']
            rec_yaw = rec_result['reco_list'][0]['yaw']
            rec_yaw = (rec_yaw + math.pi) % (2 * math.pi)
            if rec_yaw > math.pi:
                rec_yaw -= 2 * math.pi
            rec_x_y_yaw = [rec_x, rec_y, rec_yaw]
            log.info(f"{rec_x_y_yaw=}")
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
        else:
            Recognize.doRec(self.recfile, False, 0, 0, 0, 0, "A")
            Timer.delay(0.05)
            log.info(f"doRec")

        j.report_info["RecShelf"] = {
            "action_status": self.action_status,
            "rec_result": j.rec_result,
            "recfile": self.recfile,
            "rec_status": rec_status,
            "rec_times": self.attempts
        }
        Module.report_info(j.report_info)


class RecTargetObs(BaseAction):
    """识别货架"""

    def __init__(self, device_name):
        super().__init__()
        self.action_status = ActionStatus.INIT
        self.device_name = device_name

    def run(self, j: Jack):
        self.action_status = ActionStatus.RUNNING
        Recognize.resetRec()
        Recognize.recTargetObs(self.device_name)

        j.report_info["RecTargetObs"] = {
            "action_status": self.action_status
        }
        Module.report_info(j.report_info)


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
                self.target_world_pos = Pos2World(self.pgv_info, [self.target_world_pos[0], self.target_world_pos[1],
                                                                  self.target_world_pos[2]])

        return self.target_world_pos

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class GetPGVData(BaseAction):
    """获取二维码资料"""

    def __init__(self):
        super().__init__("GetPGVData")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.is_DMT_detected = False
        self.tag_diff_x = 0
        self.tag_diff_y = 0
        self.tag_diff_angle = 0
        self.tag_value = 0
        self.count = 0
        self.max_rec_num = 15

    def run(self, j: Jack):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = False

        pgv_data = Pgv.get_pgvs()
        for pgv in pgv_data:
            self.tag_value = pgv.tag_value
            self.tag_diff_x = pgv.tag_diff_x
            self.tag_diff_y = pgv.tag_diff_y
            self.tag_diff_angle = pgv.tag_diff_angle
            self.is_DMT_detected = pgv.is_DMT_detected

        # 将信息传出至j.code_info, 方便后续调用
        j.code_info = {
            "tag_value": self.tag_value,
            "is_DMT_detected": self.is_DMT_detected,
            "tag_diff_x": self.tag_diff_x,
            "tag_diff_y": self.tag_diff_y,
            "tag_diff_angle": self.tag_diff_angle
        }
        if self.is_DMT_detected and self.tag_value != "":  # 当识别二维码成功并且读到的码值不是空值
            log.info(f"read code success: {self.tag_value}")
            self.action_status = ActionStatus.FINISHED
        else:
            # pgv相机未扫描到二维码
            self.count = self.count + 1
            if self.count >= self.max_rec_num:
                Abnormal.setTask(53782,
                                 f"Rec times over max {self.count} NO shelf_code or recognized code fail or shelf_code is Null",
                                 "The pgv camera is faulty or the robot does not move above or below the QR code",
                                 "Check the position of the QRcode and the installation pos of PGV camera ",
                                 "Secondary adjustment with PGV")

        j.report_info["GetPGVData"] = {
            "action_status": self.action_status,
            "code_info": j.code_info
        }
        Module.report_info(j.report_info)


class PGVSecondaryAdjust(BaseAction):  # 二次调整
    def __init__(self):
        super().__init__("PGVSecondaryAdjust")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.adjust_param = dict()

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.reset()
        self.set_adjust_param(j.code_info["tag_diff_x"], j.code_info["tag_diff_y"])
        self.action_status = Navigation.goPGVRun(self.adjust_param)

        j.report_info["PGVSecondaryAdjust"] = {
            "action_status": self.action_status,
            "code_info": j.code_info
        }
        Module.report_info(j.report_info)

    def set_adjust_param(self, pgv_adjust_cx, pgv_adjust_cy):
        self.adjust_param['use_pgv'] = False  # 使用上视pgv, args里需要增加use_pgv参数
        if self.adjust_param['use_pgv']:
            self.adjust_param['use_down_pgv'] = False  # 使用下视pgv
        else:
            self.adjust_param['use_down_pgv'] = True
        self.adjust_param['pgv_x_adjust'] = True  # 按照x纵方向进行二次调整
        self.adjust_param['pgv_x_angle_adjust'] = False  # 沿着车子方向的偏差进行调整，并且到点后调整角度偏差
        self.adjust_param['pgv_adjust_dist'] = 0.2  # 最大的调整半径,尽量小以二维码中心为圆心
        self.adjust_param['pgv_adjust_cx'] = pgv_adjust_cx  # 调整范围的圆心为二维码坐标系下的坐标x
        self.adjust_param['pgv_adjust_cy'] = pgv_adjust_cy  # 调整范围的圆心为二维码坐标系下的坐标y
        self.adjust_param['PGV_ReachDist'] = 0.02  # pgv二次调整距离精度
        self.adjust_param['PGV_ReachAngle'] = 0.02  # pgv二次调整角度精度

    def reset(self):
        log.info("reset PGV secondary adjustment")
        self.action_status = ActionStatus.RUNNING
        Navigation.resetGoPGV()


# --- 枚举定义 ---
class Coordinate:
    """ 坐标系枚举 """
    ROBOT = "robot"
    WORLD = "world"
    INCREASE = "increase"


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
    Module.init()

    validator = ParamValidator(InputParams.builder.to_dict())
    j = Jack()
    modbus_params = None
    while True:
        # 脚本任务状态管理
        if j.event_safe_move_check:
            j.safe_move_check()
        if j.event_modbus:
            modbus_params = j.modbus()
            print(f"modbus_validated_params={modbus_params}")
            j.event_modbus = False
        status = Module.get_status()
        print(f"-------------------------status:{status}")
        if status in (ScriptStatus.RUNNING, ScriptStatus.NONE):
            if modbus_params is None:
                input_params = Module.get_task_args()
                print("task args:", json.dumps(input_params, indent=2))
                validated_params = {}
                try:
                    # 验证参数
                    validated_params = validator.validate(input_params)
                    print("check ok, args:", json.dumps(validated_params, indent=2))
                except ValueError as e:
                    print("check error:", e)
            else:
                validated_params = modbus_params
            j.run(validated_params)
        elif status in (ScriptStatus.FAILED,ScriptStatus.FINISHED):
            j.init_args = False
            j.action_id = 0
            j.action_list = []
            j.operation_init = False

        # j.print_info()
        time.sleep(0.1)
        j.report_info["jackWithSpin"] = {
            "jack_mode": True,
            "jack_enable": True,
        }
        Module.report_info(j.report_info)


if __name__ == '__main__':
    main()