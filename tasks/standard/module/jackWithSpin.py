# -*- coding: utf-8 -*-
# @Date : 2025/09/10
# @Author : zengweibin
# @Coding : none
# @Update : 3.5顶升车示例模板

import json
import math
import time
from enum import IntEnum

from syspy.utils.time import Timer

start_time = time.time()

from syspy import (Module, Logger, Di, Do, Motor, Navigation, Loc, Abnormal, Recognize,
                   Odometer, Pgv, ScriptStatus, NetProtocol, Trace, NavSpeed, Controller)
from syspy.lib.module import Pos2Base, Pos2World, ModuleBase, SafeMoveStatus
from tasks.standard import goPath, goBezier
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ParamServer
from syspy.lib.robot_param import RobotParam
from syspy.utils import Coordinate

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
    resetBySpeed = RobotParam.getDevice(f"{jack_motor_name}", "resetMode")
    jack_min_height = RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.minLength")
    jack_max_height = RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.maxLength")
    jack_up_di = RobotParam.getDevice(f"{jack_motor_name}", f"func.{motor_func}.upLimitDI")
    jack_zero_di = RobotParam.getDevice(f"{jack_motor_name}", f"resetMode.{resetBySpeed}.zeroDI")
    spin_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.spinMotor")

    # 测试前近距离
    go_distance = param_server.loadParam("go_distance", type="float", default=0.5, comment="测试前进距离")

    log.debug("jack create config params")


def create_start_height(builder: ParamBuilder):
    with builder.CHILD(key="startHeight", name="Start Height",
                       desc="The start height for operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.MIN_VALUE(ConfigParams.jack_min_height)
        builder.MAX_VALUE(ConfigParams.jack_max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(ConfigParams.jack_min_height)


def create_end_height(builder: ParamBuilder):
    """创建顶可被引用参数"""
    with builder.CHILD(key="endHeight", name="End Height",
                       desc="The end height for operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.MIN_VALUE(ConfigParams.jack_min_height)
        builder.MAX_VALUE(ConfigParams.jack_max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(ConfigParams.jack_max_height)


def create_ap_id(builder: ParamBuilder):
    with builder.CHILD(key="targetName", name="Target ID",
                       desc="the ap id for operation"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE("AP1")


def create_recfile(builder: ParamBuilder):
    with builder.CHILD(key="recFile", name="Recfile", desc="file for recognizing"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE("default.srec")
    with builder.CHILD(key="insertShelfDir", name="Insert Shelf Direction", desc="direction to go under the shelf"):
        builder.TYPE(ParamType.STRING)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE("A")


def create_bezier(builder: ParamBuilder):
    with builder.CHILD(key="backDist", name="back_dist", desc="the back dist for goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.0)
    with builder.CHILD(key="adjustDistForCurvatureLimit", name="adjust_dist_for_curvature_limit",
                       desc="the adjust dist for decreasing curvature limit"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(2.0)
    with builder.CHILD(key="minAheadDist", name="min_ahead_dist", desc="the min ahead dist for goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.0)
    with builder.CHILD(key="isBackwards", name="is_backwards", desc="Backward or forward mode"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(False)
    with builder.CHILD(key="isHoldDir", name="is_hold_dir", desc="whether the robot will hold direction"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(False)
    with builder.CHILD(key="maxSpeed", name="max_speed", desc="max_speed when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.5)
    with builder.CHILD(key="maxAccele", name="max_accele", desc="max_acceleration when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.3)
    with builder.CHILD(key="maxDecele", name="max_decele", desc="max_deceleration when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.2)
    with builder.CHILD(key="deceleDist", name="decele_dist",
                       desc="The speed will slow down after reaching this distance from the target point."):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(1)
    with builder.CHILD(key="curvatureLimit", name="curvature_limit", desc="Curvature limits for Bezier paths"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(1.3)
    with builder.CHILD(key="pathDistAccuracy", name="path_dist_accuracy",
                       desc="Position accuracy of Bezier curve for robot walking"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.01)
    with builder.CHILD(key="pathAngleAccuracy", name="path_angle_accuracy",
                       desc="angle accuracy of Bezier curve for robot walking"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.05)


def create_polyline(builder: ParamBuilder):
    with builder.CHILD(key="backDist", name="back_dist", desc="the back dist for goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(0.0)
    with builder.CHILD(key="aheadDist", name="ahead_dist",
                       desc="the adjust dist for decreasing the angle between two straight lines"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(2.0)
    with builder.CHILD(key="minAheadDist", name="min_ahead_dist", desc="the min ahead dist for goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.0)
    with builder.CHILD(key="isBackwards", name="is_backwards", desc="Backward or forward mode"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(False)
    with builder.CHILD(key="isHoldDir", name="is_hold_dir", desc="whether the robot will hold direction"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(False)
    with builder.CHILD(key="maxSpeed", name="max_speed", desc="max_speed when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.5)
    with builder.CHILD(key="maxAccele", name="max_accele", desc="max_acceleration when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.3)
    with builder.CHILD(key="maxDecele", name="max_decele", desc="max_deceleration when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.2)
    with builder.CHILD(key="deceleDist", name="decele_dist",
                       desc="The speed will slow down after reaching this distance from the target point."):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(1)
    with builder.CHILD(key="maxAngle", name="max_angle", desc="max angle for the two lines"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(1.3)
    with builder.CHILD(key="pathDistAccuracy", name="path_dist_accuracy",
                       desc="Position accuracy of Bezier curve for robot walking"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.01)
    with builder.CHILD(key="pathAngleAccuracy", name="path_angle_accuracy",
                       desc="angle accuracy of Bezier curve for robot walking"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.05)


def create_gopath(builder: ParamBuilder):
    with builder.CHILD(key="isBackwards", name="is_backwards", desc="Backward or forward mode"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(False)
    with builder.CHILD(key="isHoldDir", name="is_hold_dir", desc="whether the robot will hold direction"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE(False)
    with builder.CHILD(key="maxSpeed", name="max_speed", desc="max_speed when goBezier"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.5)
    with builder.CHILD(key="pathDistAccuracy", name="path_dist_accuracy",
                       desc="Position accuracy of Bezier curve for robot walking"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.01)
    with builder.CHILD(key="pathAngleAccuracy", name="path_angle_accuracy",
                       desc="angle accuracy of Bezier curve for robot walking"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.05)


def create_secondary_adjust_pgv(builder: ParamBuilder):
    with builder.CHILD(key="useWhichPgv", name="use_which_pgv", desc="using up or down pgv"):
        builder.TYPE(ParamType.STRING_COMBO_LIST)
        builder.DEFAULTVALUE("up_down_pgv")

        with builder.CHILDREN():
            with builder.CHILD("up_down_pgv", "up_down_pgv", "up_down_pgv"):
                builder.TYPE(ParamType.STRING)
            with builder.CHILD("up_up_pgv", "up_up_pgv", "up_up_pgv"):
                builder.TYPE(ParamType.STRING)

    with builder.CHILD(key="pgvXAdjust", name="pgv_x_adjust", desc="Secondary adjustment in the x-direction"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(True)

    with builder.CHILD(key="pgvXAngleAdjust", name="pgv_x_angle_adjust",
                       desc="Adjust the deviation along the direction of the car, and adjust the angle deviation after reaching the point"):
        builder.TYPE(ParamType.BOOL)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(True)

    with builder.CHILD(key="pgvAdjustDist", name="pgv_adjust_dist",
                       desc="The maximum adjustment radius should be as small as possible with the center of the QR code as the center of the circle"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.2)

    with builder.CHILD(key="pgvReachDist", name="pgv_reach_dist", desc="PGV secondary adjustment distance accuracy"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.02)

    with builder.CHILD(key="pgvReachAngle", name="pgv_reach_angle", desc="PGV secondary adjustment angle accuracy"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE(0.02)


def create_jack_load(builder: ParamBuilder):
    create_ap_id(builder)
    create_start_height(builder)
    create_end_height(builder)

    with builder.CHILD(key="isRecognize", name="whether the loading progress need recognition",
                       desc="Enable recognition"):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE(0)
        with builder.CHILDREN():
            # OFF 选项，不需要填识别文件
            with builder.CHILD(key="OFF", name="Recognize",
                               desc="Load Without Recognition"):
                builder.TYPE(ParamType.ARRAY)
            # ON 也就是勾选需要识别后才会需要填写识别文件
            with builder.CHILD(key="ON", name="Recognize",
                               desc="Load With Recognition"):
                builder.TYPE(ParamType.ARRAY)
                create_recfile(builder)

    with builder.CHILD(key="howGoSite", name="how_go_site", desc="choose the way to the landmark"):
        builder.TYPE(ParamType.COMBO_BOX)
        builder.DEFAULTVALUE("bezier")
        builder.REQUIRED(True)
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

    with builder.CHILD(key="isSecondaryAdjust", name="whether the loading progress need secondary adjust",
                       desc="Enable secondary adjust"):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE(0)
        with builder.CHILDREN():
            # OFF 选项，不需要填二次调整内容
            with builder.CHILD(key="OFF", name="secondary_adjust",
                               desc="Load Without secondary_adjust"):
                builder.TYPE(ParamType.ARRAY)
            # ON 也就是勾选需要二次调整后才会出现二次调整相关内容
            with builder.CHILD(key="ON", name="secondary_adjust",
                               desc="Load With secondary_adjust"):
                builder.TYPE(ParamType.ARRAY)
                create_secondary_adjust_pgv(builder)


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

                    with builder.CHILD(key="createOrDeleteDeductedArea", name="create_or_delete_deducted_area", desc="create_or_delete_deducted_area"):
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

                # 识别取货
                with builder.CHILD(key="jackLoad", name="JackLoad", desc="recognize and load the shelf"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        create_jack_load(builder)

                # 识别放货
                with builder.CHILD(key="jackUnLoad", name="JackUnLoad", desc="recognize and unload the shelf"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        create_ap_id(builder)
                        create_start_height(builder)
                        create_end_height(builder)
                        create_recfile(builder)
                        create_bezier(builder)

                # 抬高托盘操作
                with builder.CHILD(key="jackHeight", name="JackHeight", desc="lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        create_end_height(builder)
                        create_recfile(builder)

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
                        create_polyline(builder)

                # JackSpin操作
                # with builder.CHILD(key="spinTray", name="spinTray", desc="Spin the tray"):
                #     builder.TYPE(ParamType.ARRAY)
                #
                #     with builder.CHILDREN():
                #         # 旋转角度参数
                #         with builder.CHILD(key="spin_angle", name="spin_angle", desc="the angle that the tray spin"):
                #             builder.MIN_VALUE(-360)
                #             builder.MAX_VALUE(360)
                #             builder.TYPE(ParamType.FLOAT)
                #             builder.REQUIRED(True)
                #             builder.UNIT("degree")
                #             builder.DEFAULTVALUE(0)
                #
                #         with builder.CHILD(key="spinMode", name="spin_mode", desc="Spin mode(robot coordinate/world coordinate/increase)"):
                #             builder.TYPE(ParamType.COMBO_BOX)
                #             builder.REQUIRED(False)
                #             with builder.CHILDREN():
                #                 with builder.CHILD("robot", "robot", "robot"):
                #                     builder.TYPE(ParamType.ARRAY)
                #                     with builder.CHILDREN():
                #                         with builder.CHILD(key="spin_dir", name="spin_dir",
                #                                            desc="Spin direction(clockwise-1/counterclockwise1/shortest0)"):
                #                             builder.TYPE(ParamType.STRING_COMBO_LIST)
                #                             builder.REQUIRED(True)
                #                             builder.DEFAULTVALUE(0)
                #                             with builder.CHILDREN():
                #                                 with builder.CHILD(0, "shortest", "shortest"):
                #                                     builder.TYPE(ParamType.STRING)
                #                                 with builder.CHILD(-1, "clockwise", "clockwise"):
                #                                     builder.TYPE(ParamType.STRING)
                #                                 with builder.CHILD(1, "counterclockwise", "counterclockwise"):
                #                                     builder.TYPE(ParamType.STRING)
                #
                #                 with builder.CHILD("world", "world", "world"):
                #                     builder.TYPE(ParamType.ARRAY)
                #                     with builder.CHILDREN():
                #                         with builder.CHILD(key="spin_dir", name="spin_dir",
                #                                            desc="Spin direction(clockwise-1/counterclockwise1/shortest0)"):
                #                             builder.TYPE(ParamType.STRING_COMBO_LIST)
                #                             builder.REQUIRED(True)
                #                             builder.DEFAULTVALUE(0)
                #                             with builder.CHILDREN():
                #                                 with builder.CHILD(0, "shortest", "shortest"):
                #                                     builder.TYPE(ParamType.STRING)
                #                                 with builder.CHILD(-1, "clockwise", "clockwise"):
                #                                     builder.TYPE(ParamType.STRING)
                #                                 with builder.CHILD(1, "counterclockwise", "counterclockwise"):
                #                                     builder.TYPE(ParamType.STRING)
                #
                #                 with builder.CHILD("increase", "increase", "increase"):
                #                     builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="spinTray", name="spinTray", desc="Spin the tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 旋转角度参数
                        with builder.CHILD(key="spinAngle", name="spin_angle", desc="the angle that the tray spin"):
                            builder.MIN_VALUE(-360)
                            builder.MAX_VALUE(360)
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("degree")
                            builder.DEFAULTVALUE(0)

                        with builder.CHILD(key="spinMode", name="spin_mode", desc="Spin mode(robot coordinate/world coordinate/increase)"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.DEFAULTVALUE("robot")
                            builder.REQUIRED(True)
                            with builder.CHILDREN():
                                with builder.CHILD("robot", "robot", "robot"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("world", "world", "world"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD("increase", "increase", "increase"):
                                    builder.TYPE(ParamType.STRING)

                        with builder.CHILD(key="spinDir", name="spin_dir",
                                           desc="Spin direction(clockwise-1/counterclockwise1/shortest0)"):
                            builder.TYPE(ParamType.STRING_COMBO_LIST)
                            builder.REQUIRED(True)
                            builder.DEFAULTVALUE(0)
                            with builder.CHILDREN():
                                with builder.CHILD(0, "shortest", "shortest"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD(-1, "clockwise", "clockwise"):
                                    builder.TYPE(ParamType.STRING)
                                with builder.CHILD(1, "counterclockwise", "counterclockwise"):
                                    builder.TYPE(ParamType.STRING)


                with builder.CHILD(key="rotateHoldSpin", name="rotateHoldSpin", desc="Rotate the robot"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="spinAngle", name="rotate_angle", desc="the angle that the robot rotate"):
                        builder.MIN_VALUE(-360)
                        builder.MAX_VALUE(360)
                        builder.TYPE(ParamType.FLOAT)
                        builder.REQUIRED(True)
                        builder.UNIT("degree")
                        builder.DEFAULTVALUE(0)
                    with builder.CHILD(key="isSpinFollow", name="is_spin_follow",
                                       desc="whether the tray will keep the angle on world coordinate"):
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

                with builder.CHILD(key="PGVSecondaryAdjust", name="PGVSecondaryAdjust", desc="pgv secondary adjust"):
                    builder.TYPE(ParamType.ARRAY)
                    create_secondary_adjust_pgv(builder)

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

        Trace.log(f"module_type = {ConfigParams.module_type}")
        Trace.log(f"jack_motor_name = {ConfigParams.jack_motor_name}")
        Trace.log(f"spin_motor_name = {ConfigParams.spin_motor_name}")
        Trace.log(f"jack_min_height = {ConfigParams.jack_min_height}")
        Trace.log(f"jack_max_height = {ConfigParams.jack_max_height}")
        Trace.log(f"jack_up_di = {ConfigParams.jack_up_di}")
        Trace.log(f"jack_zero_di = {ConfigParams.jack_zero_di}")

        # Module.set_status(ScriptStatus.NONE)

    def _init_args(self):
        if not self.init_args:
            self.init_args = True
            # 获取任务参数
            self.opt = self.task_args.get("operation", None)
            self.ap_id = self.task_args.get("targetName", None)
            # 顶升高度相关
            self.start_height = self.task_args.get("startHeight", None)
            self.end_height = self.task_args.get("endHeight", None)
            # 识别相关
            self.is_recognize = self.task_args.get("isRecognize", None)
            self.recfile = self.task_args.get("recfile", None)
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
            self.how_go_site = self.task_args.get("howGoSite", None)
            # path相关
            self.back_dist = self.task_args.get("backDist", None)
            self.adjust_dist_for_curvature_limit = self.task_args.get("adjustDistForCurvatureLimit", None)
            self.min_ahead_dist = self.task_args.get("minAheadDist", None)
            self.is_backwards = self.task_args.get("isBackwards", None)
            self.is_hold_dir = self.task_args.get("isHoldDir", None)
            self.max_speed = self.task_args.get("maxSpeed", None)
            self.max_rot = self.task_args.get("max_rot", None)
            self.max_accele = self.task_args.get("maxAccele", None)
            self.max_decele = self.task_args.get("maxDecele", None)
            self.decele_dist = self.task_args.get("deceleDist", None)
            self.curvature_limit = self.task_args.get("curvatureLimit", None)
            self.path_dist_accuracy = self.task_args.get("pathDistAccuracy", None)
            self.path_angle_accuracy = self.task_args.get("pathAngleAccuracy", None)

            # goPath相关
            self.goPath_x = self.task_args.get("goPathX", None)
            self.goPath_y = self.task_args.get("goPathY", None)
            self.goPath_theta = self.task_args.get("goPathTheta", None)

            # secondaryAdjust相关
            self.is_secondary_adjust = self.task_args.get("isSecondaryAdjust", None)
            self.use_which_pgv = self.task_args.get("useWhichPgv", None)
            self.pgv_x_adjust = self.task_args.get("pgvXAdjust", None)
            self.pgv_x_angle_adjust = self.task_args.get("pgvXAngleAdjust", None)
            self.pgv_adjust_dist = self.task_args.get("pgvAdjustDist", None)
            self.pgv_reach_dist = self.task_args.get("pgvReachDist", None)
            self.pgv_reach_angle = self.task_args.get("pgvReachAngle", None)

            # laser area deduction
            self.create_or_delete_deducted_area = self.task_args.get("createOrDeleteDeductedArea", None)

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
        elif self.opt == "spinTray":  # 托盘旋转指定角度
            self.spin()
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
        else:
            Module.set_status(ScriptStatus.FAILED)

        Trace.log(f"self.action_list: {self.action_list}")
        self._execute_actions()

    def laser_area_deduction(self):
        if not self.operation_init:
            self.operation_init = True

            if self.create_or_delete_deducted_area == "create":

                self.laser_area_deduct_info = self.laser_area_deduct(self.recfile, "shelf")
                robot_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
                Trace.log(f"robot_loc = {robot_loc}")
                area_device = {
                    "deduct_device": self.laser_area_deduct_info["deduct_device"],
                    "area": []
                }
                clear_region = None
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
                            wx, wy, wz = Pos2World([x, y, 0], robot_loc)
                            x_list_deduct_area.append(wx)
                            y_list_deduct_area.append(wy)
                    area_device["area"].append({
                        "x_list": x_list_deduct_area,
                        "y_list": y_list_deduct_area
                    })
                    # 对每个area执行操作
                    Navigation.setClearRegion(f"ForbiddenArea{idx}", x_list_deduct_area, y_list_deduct_area, self.laser_area_deduct_info["deduct_device"], Coordinate.ROBOT)
            
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
                    Module.report_info(self.report_info)

    def laser_area_deduct(self, recfile, object_key: str = "shelf"):
        # 激光区域扣除
        if recfile:
            # 路径前缀：recognitionObject.{object_key}.recognitionSide
            recognition_obstacle_deduction_path = f"recognitionObject.{object_key}.obstacleDeduction"

            # 1) 获取obstacle_deduction
            deduct_device = RobotParam.getConfig("recognition", f"{recognition_obstacle_deduction_path}.deductDevice", recfile).spilt(",")
            deduct_shape = RobotParam.getConfig("recognition", f"{recognition_obstacle_deduction_path}.deductShape", recfile)

            # 转换为 Python 对象
            shapes = json.loads(deduct_shape)

            # 设备列表
            device_list = [deduct_device]

            info = {
                "deductDevice": device_list,
                "area": []
            }

            for shape in shapes:
                x_list = [p["x"] for p in shape["points"]]
                y_list = [p["y"] for p in shape["points"]]
                info["area"].append({
                    "xList": x_list,
                    "yList": y_list
                })

            Trace.log(f"laser_area_deduct_info={info}")
            return info

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
            Module.set_status(ScriptStatus.FAILED)

        # 2) 命中后读取 enableBackDistance / backDistance
        base = f"{recognition_side_key}._{target_idx}.{side_name}"
        enable_back = RobotParam.getConfig("recognition", f"{base}.enableBackDistance", recfile)
        back_dist = RobotParam.getConfig("recognition", f"{base}.backDistance", recfile)
        info = {
            "side": side_name,
            "enableBackDistance": enable_back,
            "backDistance": back_dist
        }

        # 3) 基本校验
        if any(v is None or v == "none" for v in info.values()):
            Abnormal.setTask(53325, f"Invalid back_distance_info, found None: {info}, script failed",
                             "recognize file param wrong", "check the param", "get_back_distance_info")
            Module.set_status(ScriptStatus.FAILED)

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
        Module.report_info(self.report_info)
        Trace.log(f"getLM={result}")
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
            robot_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
            ap_to_robot_angle = math.atan2(self.ap_world_pos[1] - robot_loc[1], self.ap_world_pos[0] - robot_loc[0])
            Trace.log(f'AP_pos: {self.ap_world_pos}')
            Trace.log(f'ap_to_robot_angle: {ap_to_robot_angle}')

            self.report_info["jack_load"] = {
                "apToRobotAngle": ap_to_robot_angle,
                "robotLoc": robot_loc,
                "apWorldPos": self.ap_world_pos
            }

            # 第一步转到指向ap点的方向
            self.action_list.append(RobotRotate(ap_to_robot_angle, "world", False))
            self.action_list.append(JackHeight(ConfigParams.jack_motor_name, self.start_height, ConfigParams.jack_motor_speed, self.recfile))
            # 转到指向ap点的位置
            self.action_list.append(RecShelf(self.recfile, "FirstRec"))  # 识别货架，得到坐标放入j.rec_result

            # 动态添加action_list
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            Trace.log(f'{self.action_id=}, {self.action_list=}')
            Trace.log(f'{current_action.action_name=}, {current_action.action_status=}')

            if current_action.action_name == "FirstRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                robot_pos = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
                result_robot = Pos2Base(result_world, robot_pos)

                # 如果离shelf太近，先后退一段距离再第二次识别（离太近可能存在偏差）
                if result_robot[0] < 1:
                    Trace.log(f'{current_action.action_name=}')
                    self.action_list.append(GoPath([-0.3, 0, 0], "robot", True))
                    self.action_list.append(RecShelf(self.recfile, "SecondRec"))  # 识别货架，得到坐标放入j.rec_result
                else:
                    # 如果用户未传入back_dist数值，则用识别文件中的数值（需要enableBackDistance启用，否则为back_distance为0）
                    recfile_back_dist = self.get_back_distance_info(self.recfile, "shelf", "A")
                    print(f"{recfile_back_dist}")
                    if self.back_dist is not None:
                        pass
                    elif self.back_dist is None and recfile_back_dist["enableBackDistance"] is True:
                        self.back_dist = recfile_back_dist["backDistance"]
                    elif self.back_dist is None and recfile_back_dist["enableBackDistance"] is False:
                        self.back_dist = 0

                    self.action_list.append(
                        GoBezier(result_world, self.back_dist, self.adjust_dist_for_curvature_limit,
                                 self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                                 self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                                 self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))

            if current_action.action_name == "SecondRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                self.action_list.append(
                    GoBezier(result_world, self.back_dist, self.adjust_dist_for_curvature_limit,
                             self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                             self.max_speed, self.max_accele, self.max_decele, self.decele_dist, self.curvature_limit,
                             self.path_dist_accuracy, self.path_angle_accuracy))

            if current_action.action_name == "GoBezier" and current_action.action_status == ActionStatus.FINISHED:
                self.action_list.append(Spin(0, "robot", 0))
                self.action_list.append(JackHeight(ConfigParams.jack_motor_name, self.end_height, ConfigParams.jack_motor_speed))
                self.action_list.append(
                    GoBezierReturn(not self.is_backwards, self.is_hold_dir, self.max_speed,
                                   self.max_accele, self.max_decele, self.decele_dist))

    def jack_load(self):
        # =====完整：旋转车体调整对准——识别货架——导航——二次调整——顶起 流程=====
        if not self.operation_init:
            self.operation_init = True
            # 下降到起始高度
            self.action_list.append(JackHeight(ConfigParams.jack_motor_name, self.start_height, ConfigParams.jack_motor_speed))

            # 获取AP点坐标
            if not self.ap_id:
                self.ap_id = Navigation.moveTask().get("target_name", None)
                self.ap_id = "AP" + str(self.ap_id)
            self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
            self.ap_robot_pos = Navigation.getLM(self.ap_id, False)
            robot_loc = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
            ap_to_robot_angle = math.atan2(self.ap_world_pos[1] - robot_loc[1], self.ap_world_pos[0] - robot_loc[0])
            Trace.log(f'AP_pos: {self.ap_world_pos}')
            Trace.log(f'ap_to_robot_angle: {ap_to_robot_angle}')

            self.report_info["jack_load"] = {
                "apToRobotAngle": ap_to_robot_angle,
                "robotLoc": robot_loc,
                "apWorldPos": self.ap_world_pos
            }

            # 第一步转到指向ap点的方向
            self.action_list.append(RobotRotate(ap_to_robot_angle, Coordinate.WORLD, False))

            # 第二步判断是否有识别
            # 如果有识别
            if self.is_recognize:  # 要求启用识别时必须有recfile
                # 转到指向ap点的位置
                self.action_list.append(RecShelf(self.recfile, "FirstRec"))  # 识别货架，得到坐标放入j.rec_result
            # 如果没有识别
            else:
                # 直接前进到任务的AP点坐标
                if self.how_go_site == "straight":
                    self.action_list.append(
                        GoPath(self.ap_world_pos, "world", self.is_backwards, self.is_hold_dir, self.max_speed,
                               self.max_rot, self.path_dist_accuracy, self.path_angle_accuracy))
                elif self.how_go_site == "bezier":
                    self.action_list.append(
                        GoBezier(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                                 self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                                 self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                                 self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))
                elif self.how_go_site == "polyline":
                    self.action_list.append(
                        GoPolyline(self.ap_world_pos, self.min_ahead_dist, self.adjust_dist_for_curvature_limit,
                                   self.back_dist, self.max_speed, self.max_rot, self.decele_dist))

                # 加入二次调整，取货前托盘调整，抬升托盘动作
                if self.is_secondary_adjust:
                    self.action_list.append(GetPGVData())
                    self.action_list.append(
                        PGVSecondaryAdjust(self.use_which_pgv, self.pgv_x_adjust, self.pgv_x_angle_adjust,
                                           self.pgv_adjust_dist, self.pgv_reach_dist, self.pgv_reach_angle))
                self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_max_height,
                                                   ConfigParams.jack_motor_speed))

        # 动态添加action_list，仅在有识别时有效
        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            Trace.log(f'{self.action_id=}, {self.action_list=}')
            Trace.log(f'{current_action.action_name=}, {current_action.action_status=}')

            if current_action.action_name == "FirstRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                robot_pos = [Loc.get_pose()["x"], Loc.get_pose()["y"], math.radians(Loc.get_pose()["yaw"])]
                result_robot = Pos2Base(result_world, robot_pos)

                # 如果离shelf太近，先后退一段距离再第二次识别（离太近可能存在偏差）
                if result_robot[0] < 1:
                    self.action_list.append(GoPath([-0.3, 0, 0], "robot", not self.is_backwards, self.is_hold_dir))
                    Trace.log(f"go back 0.3m to recognize again")
                    self.action_list.append(RecShelf(self.recfile, "SecondRec"))  # 识别货架，得到坐标放入j.rec_result
                else:

                    if self.how_go_site == "straight":
                        self.action_list.append(
                            GoPath(self.ap_world_pos, "world", self.is_backwards, self.is_hold_dir,
                                   self.max_speed, self.max_rot, self.path_dist_accuracy, self.path_angle_accuracy))
                    elif self.how_go_site == "bezier":
                        self.action_list.append(
                            GoBezier(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                                     self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                                     self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                                     self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))
                    elif self.how_go_site == "polyline":
                        self.action_list.append(
                            GoPolyline(self.ap_world_pos, self.min_ahead_dist, self.adjust_dist_for_curvature_limit,
                                       self.back_dist, self.max_speed, self.max_rot, self.decele_dist))

            if current_action.action_name == "SecondRec" and current_action.action_status == ActionStatus.FINISHED:
                result_world = self.rec_result
                self.action_list.append(GoBezier(result_world))
                # 加入二次调整，取货前托盘调整，抬升托盘动作
                if self.is_secondary_adjust:
                    self.action_list.append(GetPGVData())
                    self.action_list.append(
                        PGVSecondaryAdjust(self.use_which_pgv, self.pgv_x_adjust, self.pgv_x_angle_adjust,
                                           self.pgv_adjust_dist, self.pgv_reach_dist, self.pgv_reach_angle))
                self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_max_height,
                                                   ConfigParams.jack_motor_speed))

    def jack_unload(self):
        if not self.operation_init:
            self.operation_init = True

            # 第一步判断是否有识别
            if ConfigParams.is_recognize:  # 要求启用识别时必须有recfile
                self.action_list.append(RecShelf(self.recfile))  # 识别货架，得到坐标放入self.rec_result
            else:
                # 如果没有识别
                # 第二步选择是否需要根据货物下方的二维码调整放货位置
                if ConfigParams.is_goods_qrcode:
                    self.action_list.append(GetApPosAdjustedViaPgv())  # 前往识别点,并根据货物二维码调整放货坐标
                else:
                    if not self.ap_id:
                        self.ap_id = Navigation.moveTask().get("target_name", None)
                        self.ap_id = "AP" + str(self.ap_id)
                    self.ap_world_pos = Navigation.getLM(self.ap_id, True)  # AP在世界坐标系下的位置
                    Trace.log(f'AP_pos: {self.ap_world_pos}')
                # 在动作类内部选择直线、贝塞尔、二段线方式前往识别点
                if self.how_go_site == "straight":
                    self.action_list.append(
                        GoPath(self.ap_world_pos, "world", self.is_backwards, self.is_hold_dir,
                               self.max_speed, self.max_rot, self.path_dist_accuracy, self.path_angle_accuracy))
                elif self.how_go_site == "bezier":
                    self.action_list.append(
                        GoBezier(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
                                 self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                                 self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                                 self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))
                elif self.how_go_site == "polyline":
                    self.action_list.append(
                        GoPolyline(self.ap_world_pos, self.min_ahead_dist, self.adjust_dist_for_curvature_limit,
                                   self.back_dist, self.max_speed, self.max_rot, self.decele_dist))
                # 加入二次调整
                if self.is_secondary_adjust:
                    self.action_list.append(GetPGVData())
                    self.action_list.append(
                        PGVSecondaryAdjust(self.use_which_pgv, self.pgv_x_adjust, self.pgv_x_angle_adjust,
                                           self.pgv_adjust_dist, self.pgv_reach_dist, self.pgv_reach_angle))

        if 0 <= self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_name == "RecShelf" and current_action.action_status == ActionStatus.FINISHED:
                result = self.rec_result
                # 在动作类内部选择直线、贝塞尔、二段线方式前往识别点
                if self.how_go_site == "straight":
                    self.action_list.append(
                        GoPath(result, "world", self.is_backwards, self.is_hold_dir,
                               self.max_speed, self.max_rot, self.path_dist_accuracy, self.path_angle_accuracy))
                elif self.how_go_site == "bezier":
                    self.action_list.append(
                        GoBezier(result, self.back_dist, self.adjust_dist_for_curvature_limit,
                                 self.min_ahead_dist, self.is_backwards, self.is_hold_dir,
                                 self.max_speed, self.max_accele, self.max_decele, self.decele_dist,
                                 self.curvature_limit, self.path_dist_accuracy, self.path_angle_accuracy))
                elif self.how_go_site == "polyline":
                    self.action_list.append(
                        GoPolyline(result, self.min_ahead_dist, self.adjust_dist_for_curvature_limit,
                                   self.back_dist, self.max_speed, self.max_rot, self.decele_dist))
                # 加入二次调整
                if self.is_secondary_adjust:
                    self.action_list.append(GetPGVData())
                    self.action_list.append(
                        PGVSecondaryAdjust(self.use_which_pgv, self.pgv_x_adjust, self.pgv_x_angle_adjust,
                                           self.pgv_adjust_dist, self.pgv_reach_dist, self.pgv_reach_angle))

                # 放货
                self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_min_height, ConfigParams.jack_motor_speed))


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
                GoBezierCombined(self.ap_world_pos, self.back_dist, self.adjust_dist_for_curvature_limit,
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

            self.action_list.append(JackHeight(ConfigParams.jack_motor_name, self.end_height,
                                               ConfigParams.jack_motor_speed))

    def spin(self):
        """旋转托盘"""
        if not self.operation_init:
            self.operation_init = True
            print("进入spin动作")
            self.action_list.append(Spin(self.spin_angle, self.spin_mode, self.spin_dir))

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
                       self.is_hold_dir, self.max_speed, self.max_rot, self.path_dist_accuracy,self.path_angle_accuracy))

    def rec_shelf(self):
        """识别货架"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(Rec(self.recfile))  # 导航到终点

    def pgv_adjust(self):
        """二次调整"""
        if not self.operation_init:
            self.operation_init = True
            self.action_list.append(GetPGVData())
            self.action_list.append(PGVSecondaryAdjust(self.use_which_pgv, self.pgv_x_adjust, self.pgv_x_angle_adjust,
                                                       self.pgv_adjust_dist, self.pgv_reach_dist, self.pgv_reach_angle))

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
        Trace.log(f'{self.action_id=}, {self.action_list=}')
        Trace.log(f"self.action_list: {self.action_list}")

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        Trace.log(f"{self.task_args=}")
        Trace.log(f"{Module.get_task_id()=}")
        Trace.log(f"{Module.get_status()=}")

    def suspend(self):
        Module.set_status(ScriptStatus.SUSPENDED)
        Trace.log("suspend")

    def resume(self):
        if Module.get_status() == ScriptStatus.SUSPENDED:
            Module.set_status(ScriptStatus.RUNNING)
        Trace.log("resume")

    def cancel(self):
        Module.set_status(ScriptStatus.FAILED)
        Trace.log("cancel")

    def safe_move_check(self):
        self.count += 1
        status = SafeMoveStatus.RUNNING
        if self.count == 100:
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
                "operation": "spinTray",
                "spin_angle": 90,
                "spin_dir": 2,
                "coordinate": "robot"
            }
        }
        # 读取数据
        # modbus_data = NetProtocol.getModbusData("3x", 0, 1)
        modbus_data = ["4"]
        # 解析映射表
        args = modbus_data2args.get(modbus_data[0])
        Trace.log(f"---------------------------------modbus_args={args}")
        status = Module.get_status()
        Module.set_status(ScriptStatus.RUNNING)
        # if status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
        #     self.event_modbus = False
        # 做对应的动作
        return args

    def set_info(self):
        self.jack_motors = NavSpeed.get_motor_cmd()
        # print(f"jack_motors= {self.jack_motors}")
        # for jack_motor in jack_motors:
        #     jack_state = jack_motor.jack_state
        #     jack_speed = jack_motor.jack_speed
        self.jack_speed = Motor.get_motor_speed(ConfigParams.jack_motor_name)
        self.jack_isFull = Navigation.hasGoods()
        # motor_infos = Odometer.get_data()["motorInfo"]
        # for motor_info in motor_infos:
        #     if motor_info["motorName"] == ConfigParams.jack_motor_name:
        #         # self.jack_emc = motor_info["position"]
        #         self.jack_height = motor_info["position"]
        #     if motor_info["motorName"] == ConfigParams.spin_motor_name:
        #         self.jack_spin = motor_info["position"]
        self.jack_emc = Controller.get_emc()
        self.jack_height = Motor.get_motor_pos(ConfigParams.jack_motor_name)
        self.jack_spin = Motor.get_motor_pos(ConfigParams.spin_motor_name)
        self.report_info.update({
            "jackMode": True,
            "jackEnable": True,
            # "jack_state": jack_state,
            "jackApeed": self.jack_speed,
            "jackEmc": self.jack_emc,
            "jackIsFull": self.jack_isFull,
            "jackHeight": self.jack_height,
            "jackSpin": self.jack_spin
        })
        # self.report_info["motor_info"] = {
        #     "motor_infos": motor_infos
        # }
        Module.report_info(self.report_info)
        self.info_count = self.info_count + 1
        print(f"--------------setinfo---{self.info_count}---{self.jack_spin}-----------")


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


class Spin(BaseAction):
    """托盘旋转到机器人/世界坐标系下固定角度，额外旋转固定角度"""

    def __init__(self, angle, spin_mode="world", direction=None):
        super().__init__("Spin")
        self.action_status = ActionStatus.INIT
        self.init = True
        self.angle = angle
        self.dir = direction  # 0 counterclockwise; 1 clockwise; 2 shortest
        self.coordinate_system = spin_mode
        Motor.resetMotor(ConfigParams.spin_motor_name)

    def run(self, j: Jack):
        if self.init:
            self.init = False
            self.action_status = ActionStatus.RUNNING
            if self.coordinate_system == "robot":
                Trace.log("setRobotSpinAngle")
                Navigation.setRobotSpinAngle(self.angle, self.dir)
            elif self.coordinate_system == "world":
                Trace.log("setGlobalSpinAngle")
                Navigation.setGlobalSpinAngle(self.angle, self.dir)
            elif self.coordinate_system == "increase":
                Trace.log("setIncreaseSpinAngle")
                Navigation.setIncreaseSpinAngle(self.angle)
        if Navigation.spinRun():
            self.action_status = ActionStatus.FINISHED
        Trace.log(f"弧度{self.angle=}")
        Trace.log(f"坐标系{self.coordinate_system=}")

        j.report_info["Spin"] = {
            "actionStatus": self.action_status,
            "spinAngle": self.angle,
            "spinMode": self.coordinate_system,
            "direction": self.dir
        }
        Module.report_info(j.report_info)

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class RobotRotate(BaseAction):
    """只转车不转托盘"""

    def __init__(self, angle, coordinate, spin=True, direction=0):
        super().__init__("RobotRotate")
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
            self.move_args['speed_w'] = self.speed
            if self.coordinate == Coordinate.ROBOT:
                self.move_args['loc_mode'] = 0  # 基于里程定位
                self.move_args['move_angle'] = self.angle
                if self.angle < 0:
                    self.move_args['move_angle'] = -self.angle
                    self.move_args['speed_w'] = -self.speed
            elif self.coordinate == Coordinate.WORLD:
                self.move_args["loc_mode"] = 1  # 激光定位

                # 1. 当前朝向：Loc 返回的是度 - 立即转弧度 - 归一化
                cur_angle_rad = self.normalize(math.radians(Loc.get_pose()["yaw"]))

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
                    "speed_w": speed_w,
                    "move_angle": move_ang
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
        Module.report_info(j.report_info)

    def reset(self):
        Navigation.resetOdoMove()
        Trace.log("reset RobotRotate")
        self.action_status = ActionStatus.RUNNING

    def normalize(self, rad: float) -> float:
        """把任意弧度角归一化到 (-π, π] 区间"""
        return (rad + math.pi) % (2 * math.pi) - math.pi


class JackHeight(BaseAction):
    """顶升动作，通过设置电机位置实现顶升"""

    def __init__(self, motor_name, target_height, jack_motor_speed, recfile=None, object_key="shelf"):
        super().__init__("JackHeight")
        self.motor_name = motor_name
        self.target_height = target_height
        self.jack_motor_speed = jack_motor_speed
        self.recfile = recfile
        self.object_key = object_key
        self.init = False
        self.jack_start_height = None
        Motor.resetMotor(self.motor_name)

    def run(self, j: Jack):
        if not self.init:
            self.init = True
            self.action_status = ActionStatus.RUNNING
            self.jack_start_height = Motor.get_motor_pos(ConfigParams.jack_motor_name)
            if self.target_height > self.jack_start_height:
                Motor.setMotorPosition(self.motor_name, self.target_height, self.jack_motor_speed, ConfigParams.jack_up_di)
            else:
                Motor.setMotorPosition(self.motor_name, self.target_height, self.jack_motor_speed, ConfigParams.jack_zero_di)

            if self.target_height > ConfigParams.jack_min_height:
                # Navigation.setGoodsShape(0.35, 0.35, 0.5)
                if self.recfile:
                    # 路径前缀：recognitionObject.{object_key}.goodsParameter
                    recognition_goodsParameter_path = f"recognitionObject.{self.object_key}.goodsParameter"
                    # 1) 获取goodsShape
                    goods_shape = RobotParam.getConfig("recognition",
                                                        f"{recognition_goodsParameter_path}.goodsShape",
                                                        self.recfile)
                    # 转换为 Python 对象
                    shapes = json.loads(goods_shape)
                    print(f"shapes={shapes}")
                    shape = shapes[0]["points"]
                else:
                    shape = [
                    {"x": 0.5, "y": 0.5},
                    {"x": -0.5, "y": 0.5},
                    {"x": -0.5, "y": -0.5},
                    {"x": 0.5, "y": -0.5}]
                Navigation.setGoodsPolyShape(shape, "shelf")
            else:
                Navigation.clearGoodsShape()

        motor_info = Odometer.get_motor_infos()
        Trace.log(f"{motor_info=}")
        Trace.log(f"{self.target_height=}")

        if self.target_height > self.jack_start_height:
            if Motor.isMotorReached(self.motor_name) or Di.get_di(ConfigParams.jack_up_di):
                self.action_status = ActionStatus.FINISHED
                Motor.resetMotor(self.motor_name)
        else:
            if Motor.isMotorReached(self.motor_name) or Di.get_di(ConfigParams.jack_zero_di):
                self.action_status = ActionStatus.FINISHED
                Motor.resetMotor(self.motor_name)

        j.report_info["JackHeight"] = {
            "actionStatus": self.action_status,
            "motorName": self.motor_name,
            "targetHeight": self.target_height,
            "jackMotorSpeed": self.jack_motor_speed,
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

        Module.report_info({"GoStraightDist": {"status": self.action_status}})
        Module.report_info({"GoStraightDist": {"goDist": self.go_dist}})


class GoPath(BaseAction):
    """直线走到指定点"""

    def __init__(self, go_pos, coordinate='robot', back_mode=False, is_hold_dir=None, max_speed=0.5, max_rot=0.3,
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
            "maxRot": self.max_rot,
            "reachDist": self.path_dist_accuracy,
            "reachAngle": self.path_angle_accuracy
        }
        Module.report_info(j.report_info)


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
        self.init = True
        self.action_status = ActionStatus.INIT
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
        Module.report_info(j.report_info)


class GoBezierReturn(BaseAction):
    """执行行走贝塞尔曲线到达取货点"""

    def __init__(self, is_backwards=True, is_hold_dir=None, max_speed=0.3, max_accele=1, max_decele=0.7,
                 decele_dist=0.1):
        super().__init__()
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
        start2end = Pos2Base(start_pos, end_pos)
        angle = math.degrees(math.atan2(start2end[1], start2end[0]))
        print(angle)
        return angle

    def search_min_angle_str(self, max_angle, step):
        temp_start = []
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
    def __init__(self, recfile, action_name="RecShelf", recognition_side="A"):
        super().__init__(action_name)
        self.init = False
        self.rec_status = None
        self.result = dict()
        self.action_status = ActionStatus.INIT
        self.recfile = recfile
        self.recognition_side = recognition_side
        self.attempts = 0
        self.max_attempts = 3
        self.success = False
        self.results = list
        self.do_rec = False
        Recognize.resetRec()

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
            rec_x = self.result['x']
            rec_y = self.result['y']
            rec_yaw = self.result['yaw']
            rec_yaw = (rec_yaw + math.pi) % (2 * math.pi) - math.pi
            rec_x_y_yaw = [rec_x, rec_y, rec_yaw]
            j.rec_result = rec_x_y_yaw
            self.action_status = ActionStatus.FINISHED

        j.report_info["RecShelf"] = {
            "actionStatus": self.action_status,
            "recResult": j.rec_result,
            "recFile": self.recfile,
            "recStatus": self.rec_status,
            "recTimes": self.attempts
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
            if not self.do_rec:
                self.do_rec = True
                Recognize.doRec(self.recfile, False, 0, 0, 0, 0, self.recognition_side)
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
        Recognize.doRec(self.recfile, False, 0, 0, 0, 0, "A")
        self.report_info = {}

    def run(self, j: Jack):
        self.action_status = ActionStatus.RUNNING
        Trace.log("recognizing the shelf")
        rec_status = Recognize.getRecStatus()
        Trace.log(f"{rec_status=}")
        # rec_result = Recognize.getRecFile(self.recfile)  # 读到识别文件原始数据
        # Trace.log(f"{rec_result=}")
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            Trace.log(f"{rec_result=}")
            Recognize.resetRec()
            Trace.log(f"rec_result={rec_result}")
            rec_x = rec_result['reco_list'][0]['x']
            rec_y = rec_result['reco_list'][0]['y']
            rec_yaw = rec_result['reco_list'][0]['yaw']
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

        j.report_info["RecShelf"] = {
            "actionStatus": self.action_status,
            "recResult": j.rec_result,
            "recFile": self.recfile,
            "recStatus": rec_status,
            "recTimes": self.attempts
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
        Recognize.recTargetObs(self.device_name,0,0,0,0,0,0,0)

        j.report_info["RecTargetObs"] = {
            "actionStatus": self.action_status
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
                self.target_world_pos = Pos2World(self.pgv_info, [self.target_world_pos[0], self.target_world_pos[1], self.target_world_pos[2]])
                j.ap_world_pos = self.target_world_pos
                self.action_status = ActionStatus.FINISHED

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
            Trace.log(f"read code success: {self.tag_value}")
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
            "actionStatus": self.action_status,
            "codeInfo": j.code_info
        }
        Module.report_info(j.report_info)


class PGVSecondaryAdjust(BaseAction):  # 二次调整
    def __init__(self, use_which_pgv, pgv_x_adjust, pgv_x_angle_adjust, pgv_adjust_dist, pgv_reach_dist, pgv_reach_angle):
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
        Module.report_info(j.report_info)

    def set_adjust_param(self, pgv_adjust_cx, pgv_adjust_cy):
        if self.use_which_pgv == "use_down_pgv":
            self.adjust_param['use_pgv'] = False  # 使用上视pgv, args里需要增加use_pgv参数
            self.adjust_param['use_down_pgv'] = True  # 使用下视pgv
        else:
            self.adjust_param['use_pgv'] = True  # 使用上视pgv, args里需要增加use_pgv参数
            self.adjust_param['use_down_pgv'] = False
        self.adjust_param['pgv_x_adjust'] = self.pgv_x_adjust  # 按照x纵方向进行二次调整
        self.adjust_param['pgv_x_angle_adjust'] = self.pgv_x_angle_adjust  # 沿着车子方向的偏差进行调整，并且到点后调整角度偏差
        self.adjust_param['pgv_adjust_dist'] = self.pgv_adjust_dist  # 最大的调整半径,尽量小以二维码中心为圆心
        self.adjust_param['pgv_adjust_cx'] = pgv_adjust_cx  # 调整范围的圆心为二维码坐标系下的坐标x
        self.adjust_param['pgv_adjust_cy'] = pgv_adjust_cy  # 调整范围的圆心为二维码坐标系下的坐标y
        self.adjust_param['PGV_ReachDist'] = self.pgv_reach_dist  # pgv二次调整距离精度
        self.adjust_param['PGV_ReachAngle'] = self.pgv_reach_angle  # pgv二次调整角度精度

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
    Module.init()

    validator = ParamValidator(InputParams.builder.to_dict())
    j = Jack()
    modbus_params = None
    while True:
        # 打印数据
        j.set_info()

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
                if input_params:
                    try:
                        # 验证参数
                        validated_params = validator.validate(input_params)
                        print("check ok, args:", json.dumps(validated_params, indent=2))
                    except ValueError as e:
                        print("check error:", e)
            else:
                validated_params = modbus_params
            j.run(validated_params)
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            j.init_args = False
            j.action_id = 0
            j.action_list = []
            j.operation_init = False

        # j.print_info()
        time.sleep(0.1)


if __name__ == '__main__':
    main()