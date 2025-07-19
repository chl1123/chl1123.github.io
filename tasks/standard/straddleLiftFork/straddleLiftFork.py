# -*- coding: utf-8 -*-
# @Time : 2025/07/12 19:26
# @Author : xu
# @File: straddleLiftFork.py
# @FileDescription : 普通堆高叉车机器人脚本
# @Version: 1.0.0
# @Description: 适配RBK-3.5


import json
import math
import os
import time
from collections import defaultdict
from datetime import datetime
from enum import IntEnum
from typing import List, Dict, Optional

from syspy import (Module, Logger, Di, Motor, NavSpeed, Do, Loc, Recognize, Trace, Distance, Navigation, Abnormal, ScriptStatus,
                   Odometer, RobotParam)
from syspy.bin import Bin
from syspy.lib.module import Pos2Base, Pos2World
from syspy.lib.py_rpc import Message
from syspy.script_data import ScriptData
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ParamServer
from syspy.utils.time import Timer
from tasks.standard import goPath

log = Logger("Fork_robot")


class ConfigParams:
    """生成和定义脚本全局配置参数"""

    # 全局参数
    # 机器人参数
    module_type = RobotParam.getDevice("Model-000", "moduleType")
    if module_type != "straddleLiftFork":
        Abnormal.setModel(53000, "模块类型不匹配",
                          f"当前模块类型为{module_type}，应为straddleLiftFork",
                          "修改参数module_type为straddleLiftFork",
                          "robot.model", "Model", "Model-000", "moduleType"
                          )
    param_server = ParamServer(__file__)
    # 底盘类型，是否为全向
    omni_model = False
    if (RobotParam.getDevice("Model-000", "getRobotType") == "omni"
        or RobotParam.getDevice("Model-000", "getRobotType") == "multipleDifferentialSteers") \
            or (RobotParam.getDevice("Model-000", "getRobotType") == "multiStandardAndDifferentialSteers"
                or RobotParam.getDevice("Model-000", "getRobotType") == "multiSteers"):
        omni_model = True
    module_to_odo_x = RobotParam.getDevice("Model-000",
                                           "moduleType.straddleLiftFork.installPosition.x")
    module_to_odo_y = RobotParam.getDevice("Model-000",
                                           "moduleType.straddleLiftFork.installPosition.y")
    module_to_odo_z = RobotParam.getDevice("Model-000",
                                           "moduleType.straddleLiftFork.installPosition.z")
    module_to_odo_roll = RobotParam.getDevice("Model-000",
                                              "moduleType.straddleLiftFork.installPosition.roll")
    module_to_odo_pitch = RobotParam.getDevice("Model-000",
                                               "moduleType.straddleLiftFork.installPosition.pitch")
    module_to_odo_yaw = RobotParam.getDevice("Model-000",
                                             "moduleType.straddleLiftFork.installPosition.yaw")

    # todo
    camera_on_fork = param_server.loadParam("Camera On Fork", type="bool", default=False, group="Basic",
                                            comment="相机是否标定在叉尖")
    fork_width = param_server.loadParam("Fork Width", type="float", default=0.08, minValue=0.05, maxValue=0.5,
                                        unit="m",
                                        group="Basic", comment="单个货叉宽度，识别取货时用于确认是否可以插进栈板")
    fork_offset_x = param_server.loadParam("Fork Offset X", type="float", default=0, minValue=-2, maxValue=2,
                                           unit="m",
                                           group="Basic", comment="货叉在X方向偏置距离")
    fork_offset_y = param_server.loadParam("Fork offset Y", type="float", default=0, minValue=-3, maxValue=3,
                                           unit="m",
                                           group="Basic", comment="货叉叉尖在Y方向偏置距离")
    fork_offset_theta = param_server.loadParam("Fork Offset Theta", type="float", default=0, minValue=-180,
                                               maxValue=180,
                                               unit="°", group="Basic", comment="货叉相对里程中心旋转角度")
    pallet2odo = param_server.loadParam("Pallet To Odometer", type="float", default=0.6, minValue=0, maxValue=2,
                                        unit="m",
                                        group="Basic",
                                        comment="取货后栈板前表面与里程的距离，有货物到位di则是到位DI与里程中心距离")
    if camera_on_fork:
        fork2robot = [fork_offset_x, fork_offset_y,
                      math.radians(fork_offset_theta)]  # 叉尖相对里程中心的位置
    else:
        fork2robot = [0.0, 0.0, 0.0]

    # 货叉升降机构参数
    lift_motor = RobotParam.getDevice("Model-000",
                                      "moduleType.straddleLiftFork.liftMotor")
    lift_max_height = RobotParam.getDevice(f"{lift_motor}", "func.linear.maxLength")
    lift_zero = RobotParam.getDevice(f"{lift_motor}", "func.linear.minLength")
    lift_vel = RobotParam.getDevice(f"{lift_motor}", "func.linear.maxSpeed")
    print(f"{lift_motor=}")
    print(f"{lift_max_height=}")
    print(f"{lift_zero=}")
    print(f"{lift_vel=}")
    lift_up_reach_di = param_server.loadParam("Lift Up Reach DI", type="int", default=-1, minValue=-1, maxValue=100,
                                              group="Module Lift", comment="货叉升降到位DI的ID")
    lift_precision = param_server.loadParam("Lift Precision", type="float", default=0.001, minValue=0.0,
                                            maxValue=0.01, unit="m", group="Module Lift",
                                            comment="货叉升降电机位置控制精度")

    # 到位DI
    # reachDi = param_server.loadParam("reachDi", type="int", default=8, comment="货物到位DI的ID")
    # reach_di1 = RobotParam.getDevice("Model-000",
    #                                  "moduleType.straddleLiftFork.id")
    reach_di1 = param_server.loadParam("Reach DI1", type="int", default=-1, minValue=-1, maxValue=100,
                                       group="Basic", comment="货物到位DI1的ID")
    reach_di2 = param_server.loadParam("Reach DI2", type="int", default=-1, minValue=-1, maxValue=100,
                                       group="Basic", comment="货物到位DI2的ID")
    multi_reach_di = [reach_di1, reach_di2]
    print(f"{multi_reach_di=}")
    check_all_di = param_server.loadParam("Check All DI", type="bool", default=False,
                                          group="Basic", comment="是否检测全部货物到位DI")
    # back_slow_down_dist = param_server.loadParam("back_slow_down_dist", type="float", default=0.1, minValue=0.0,
    #                                        maxValue=0.3,
    #                                        unit="m", group="Basic", comment="倒车取货运动时减速距离（距离目标位置）")
    back_slow_down_vel = param_server.loadParam("Back Slow Down Velocity", type="float", default=0.05, minValue=0.0,
                                                maxValue=0.3, unit="m/s", group="Basic",
                                                comment="倒车取货运动时末端速度")

    # 距离传感器
    distance_node_id1 = param_server.loadParam("Distance Node ID1", type="int", default=-1, minValue=-1, maxValue=100,
                                               group="Basic", comment="distanceNode1的ID号")
    distance_node_id2 = param_server.loadParam("Distance Node ID2", type="int", default=-1, minValue=-1, maxValue=100,
                                               group="Basic", comment="distanceNode1的ID号")
    obs_stop_dist = param_server.loadParam("Obs Stop Dist", type="float", default=0.25, minValue=0.0, maxValue=2,
                                           unit="m",
                                           group="Basic",
                                           comment="# 报警距离， 这个距离传感器的死区为0.2m，因此不能配置成小于0.2m")
    distance_node_id = (distance_node_id1, distance_node_id2)  # distanceNode的ID号

    # 尾部激光
    back_laser_id1 = param_server.loadParam("Back Laser ID1", type="int", default=-1, minValue=-1, maxValue=100,
                                            group="Basic", comment="后置激光1id")
    back_laser_id2 = param_server.loadParam("back Laser ID2", type="int", default=-1, minValue=-1, maxValue=100,
                                            group="Basic", comment="后置激光2id")
    back_laser = [back_laser_id1, back_laser_id2]

    # 叉尖碰撞DI
    fork_tail_di1 = param_server.loadParam("Fork Tail DI1", type="int", default=-1, minValue=-1, maxValue=100,
                                           group="Basic", comment="叉尖碰撞DI1的id")
    fork_tail_di2 = param_server.loadParam("Fork Tail DI2", type="int", default=-1, minValue=-1, maxValue=100,
                                           group="Basic", comment="叉尖碰撞DI2的id")

    # 识别调整参数
    rec_file1 = param_server.loadParam("Recognition File1", type="str", default="plt/p0001.plt",
                                       group="Recognition", comment="modbus脚本识别文件1")
    rec_file2 = param_server.loadParam("Recognition File2", type="str", default="plt/p0002.plt",
                                       group="Recognition", comment="modbus脚本识别文件2")
    rec_file3 = param_server.loadParam("Recognition File3", type="str", default="plt/p0003.plt",
                                       group="Recognition", comment="modbus脚本识别文件3")
    filled_detect_device = param_server.loadParam("Filled Detect Device", type="str", default="None",
                                                  group="Recognition", comment="空间占用状态检测设备")
    obs_area_min_height = param_server.loadParam("Obs Area Min Height", type="float", default=0.1, minValue=0,
                                                 maxValue=10,
                                                 unit="m", group="Recognition", comment="识别范围最小高度")
    obs_area_max_height = param_server.loadParam("Obs Area Max Height", type="float", default=1.0, minValue=0,
                                                 maxValue=10,
                                                 unit="m", group="Recognition", comment="识别范围最大高度")
    obs_area_length = param_server.loadParam("Obs Area Length", type="float", default=1.0, minValue=0, maxValue=10,
                                             unit="m",
                                             group="Recognition", comment="识别范围长度")
    obs_area_width = param_server.loadParam("Obs Area Width", type="float", default=1.0, minValue=0, maxValue=10,
                                            unit="m",
                                            group="Recognition", comment="识别范围宽度")
    rec_center_x = param_server.loadParam("Recognition Center X", type="float", default=0, minValue=-10, maxValue=10,
                                          unit="m",
                                          group="Recognition", comment="识别有效范围中心点x坐标")
    rec_center_y = param_server.loadParam("Recognition Center Y", type="float", default=0, minValue=-10, maxValue=10,
                                          unit="m",
                                          group="Recognition", comment="识别有效范围中心点y坐标")
    rec_radius = param_server.loadParam("Recognition Radius", type="float", default=0.1, minValue=0, maxValue=1,
                                        unit="m",
                                        group="Recognition", comment="识别有效范围半径")
    ahead_dist = param_server.loadParam("Ahead Dist", type="float", default=0.6, minValue=0.0, maxValue=2, unit="m",
                                        group="Recognition",
                                        comment="双折线识别调整时，调整距离不够时，第二段折线长度")
    min_ahead_dist = param_server.loadParam("Min Ahead Dist", type="float", default=0.6, minValue=-3.0, maxValue=3.0,
                                            unit="m",
                                            group="Recognition",
                                            comment="识别调整偏差后进栈板前，里程中心在栈板前的直线距离")
    back_dist = param_server.loadParam("Back Dist", type="float", default=0.6, minValue=-3.0, maxValue=3.0, unit="m",
                                       group="Recognition",
                                       comment="识别调整结束时，里程中心在栈板后的直线距离，不进入栈板为负")
    adjust_for_str = param_server.loadParam("Adjust For Str", type="float", default=0.3, minValue=0, maxValue=3.0,
                                            unit="m",
                                            group="Recognition", comment="识别调整不足时，前进距离")
    rec_beizer = param_server.loadParam("Recognition Beizer", type="bool", default=True,
                                        group="Recognition",
                                        comment="识别调整时是否使用贝塞尔曲线行驶，beizer、straight")
    beizer_dist = param_server.loadParam("Beizer Dist", type="float", default=1, minValue=0, maxValue=3.0, unit="m",
                                         group="Recognition",
                                         comment="识别后贝塞尔曲线调整时是否需要先向前行驶的最小调整距离，机器人当前位置与栈板前置点（min_ahead_dist）之间的距离")
    reach_dist = param_server.loadParam("Reach Dist", type="float", default=0.1,
                                        group="Recognition", comment="检测货物到位DI时的位置范围")
    reach_angle = param_server.loadParam("Reach Angle", type="float", default=1, minValue=0, maxValue=10, unit="°",
                                         group="Recognition", comment="检测货物到位DI时的角度范围")
    lift_up_height = param_server.loadParam("Lift Up Height", type="float", default=0.3, minValue=0, maxValue=1.0,
                                            unit="m",
                                            group="Recognition", comment="取货时取到货后抬升高度")
    lift_down_height = param_server.loadParam("Lift Down Height", type="float", default=0.3, minValue=0, maxValue=3.0,
                                              unit="m",
                                              group="Recognition", comment="放货时到点后下降高度")
    readjust = param_server.loadParam("Readjust", type="bool", default=False,
                                      group="Recognition", comment="是否开启二次识别调整取货，以提高取货精度 ")
    adjust_max_times = param_server.loadParam("Adjust Max Times", type="int", default=3, minValue=0, maxValue=5,
                                              group="Recognition", comment="二次识别调整次数 ")
    dist_precision = param_server.loadParam("Dist Precision", type="float", default=0.02, minValue=0, maxValue=0.05,
                                            unit="m",
                                            group="Recognition", comment="识别调整位置精度")
    angle_precision = param_server.loadParam("Angle Precision", type="float", default=0.5, minValue=0, maxValue=5,
                                             unit="°",
                                             group="Recognition", comment="识别调整角度精度")
    readjust_forward_dist = param_server.loadParam("Readjust Forward Dist", type="float", default=1,
                                                   minValue=0, maxValue=2, unit="m",
                                                   group="Recognition", comment="二次识别调整前进距离")
    adjust_dir_first = param_server.loadParam("Adjust Direction First", type="bool", default=True,
                                              group="Recognition", comment="是否开启识别前角度调整")
    leave_loc = param_server.loadParam("Leave Loc", type="bool", default=True,
                                       group="Recognition", comment="取货完成后是否先脱离库位后再调整货叉")
    adjust_speed = param_server.loadParam("Adjust Speed", type="float", default=0.2,
                                          minValue=0, maxValue=0.5, unit="m/s",
                                          group="Recognition", comment="识别后调整的最大速度")
    minus_result_filter = param_server.loadParam("Minus Result Filter", type="bool", default=False,
                                                 group="Recognition",
                                                 comment="识别时过滤掉高度结果为的负值或者0的数据")

    # 解垛参数
    classify_rang = param_server.loadParam("Classify Rang", type="float", default=0.03, minValue=0, maxValue=1,
                                           unit="m",
                                           group="Unstack", comment="解垛分类宽度差范围")
    error_rang = param_server.loadParam("Error Rang", type="float", default=0.03, minValue=0, maxValue=1, unit="m",
                                        group="Unstack", comment="解垛类别判断宽度差范围")
    pallet_normal_count = param_server.loadParam("Pallet Normal Count", type="int", default=8, minValue=0, maxValue=50,
                                                 group="Unstack", comment="解垛最大栈板层数")
    pallet_check = param_server.loadParam("Pallet Check", type="bool", default=False,
                                          group="Unstack", comment="解垛过程是否检查栈板类型及数量")

    # # 称重参数
    # weightGoodOn = param_server.loadParam("weightGoodOn", type="bool", default=False,
    #                                       group="weight", comment="是否启用称重检测")
    # maxWeightDetectTimes = param_server.loadParam("maxWeightDetectTimes", type="int", default=3, minValue=0,
    #                                               maxValue=10,
    #                                               group="weight", comment="重量检测最大次数")
    # detectPeriodTime = param_server.loadParam("detectPeriodTime", type="float", default=0.1, minValue=0,
    #                                           maxValue=1,
    #                                           unit="s",
    #                                           group="weight", comment="重量检测时间间隔")
    # maxWeight = param_server.loadParam("maxWeight", type="float", default=1000, minValue=0, maxValue=9999,
    #                                    unit="kg",
    #                                    group="weight", comment="重量上限")


def create_end_height(builder: ParamBuilder):
    """创建顶可被引用参数"""
    with builder.CHILD(key="endHeight", name="End Height",
                       desc="The end height for operations"):
        builder.TYPE(ParamType.FLOAT)
        # builder.REQUIRED(True)
        builder.MIN_VALUE(ConfigParams.lift_zero)
        builder.MAX_VALUE(ConfigParams.lift_max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.1)
        builder.DEFAULTVALUE(0.3)


def create_start_height(builder: ParamBuilder):
    with builder.CHILD(key="startHeight", name="Start Height",
                       desc="The start height for operations"):
        builder.TYPE(ParamType.FLOAT)
        # builder.REQUIRED(True)
        builder.MIN_VALUE(ConfigParams.lift_zero)
        builder.MAX_VALUE(ConfigParams.lift_max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.1)
        builder.DEFAULTVALUE(0.087)


def create_rec_height(builder: ParamBuilder):
    with builder.CHILD(key="recHeight", name="Recognize Height",
                       desc="The start height for operations"):
        builder.TYPE(ParamType.FLOAT)
        # builder.REQUIRED(True)
        builder.MIN_VALUE(ConfigParams.lift_zero)
        builder.MAX_VALUE(ConfigParams.lift_max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_leave_loc(builder: ParamBuilder):
    with builder.CHILD(key="leaveLoc", name="Leave Loc", desc="Enable leave loc or not, when finish load or unload"):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE(0)

        with builder.CHILDREN():
            with builder.CHILD(key="OFF", name="OFF", desc="Not enable leave loc"):
                builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(key="ON", name="ON", desc="Enable leave loc"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 识别文件
                    with builder.CHILD(key="leaveLocDist", name="Leave Loc Distance", desc="Leave loc distance"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.MIN_VALUE(-3)
                        builder.MAX_VALUE(3)
                        builder.UNIT("m")
                        builder.SINGLESTEP(0.1)
                        builder.DEFAULTVALUE(1.2)


def create_goods_status(builder: ParamBuilder):
    with builder.CHILD(key="loadGoods", name="Load Goods",
                       desc="Goods status is load or unload when opeartion is finished"):
        builder.TYPE(ParamType.BOOL)
        builder.DEFAULTVALUE(True)


def create_recognize(builder: ParamBuilder):
    with builder.CHILD(key="recognize", name="Recognize", desc="Enable recognition or not"):
        builder.TYPE(ParamType.COMBO_BOX_BOOL)
        builder.DEFAULTVALUE(0)

        with builder.CHILDREN():
            with builder.CHILD(key="OFF", name="OFF", desc="Not enable recognition"):
                builder.TYPE(ParamType.ARRAY)
        with builder.CHILDREN():
            with builder.CHILD(key="ON", name="ON", desc="Enable recognition"):
                builder.TYPE(ParamType.ARRAY)

                with builder.CHILDREN():
                    # 识别文件
                    with builder.CHILD(key="recFile", name="recFile", desc="recognition file name"):
                        builder.TYPE(ParamType.BIND_TYPE)
                        # builder.REQUIRED(True)
                        builder.BINDTYPE("app:Recognition")
                        builder.DEFAULTVALUE("321(4).srec")
                    # 是否根据识别结果调整取货高度
                    with builder.CHILD(key="adjustHeightEnable", name="Adjust Height Enable",
                                       desc=""):
                        builder.TYPE(ParamType.BOOL)
                        builder.DEFAULTVALUE(True)


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        # 公共参数:

        # 操作组合参数
        with builder.GROUP(key="operation", name="Task Operation", desc="Choose an operation for task"):
            builder.TYPE(ParamType.COMBO_BOX)

            with builder.CHILDREN():
                # # Lift，单独控制货叉升降操作
                with builder.CHILD(key="lift", name="Lift", desc="Single lift"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 开始高度参数
                        create_start_height(builder)

                        # 结束高度参数
                        create_end_height(builder)

                        # 设置载货状态
                        create_goods_status(builder)

                # ForkLoad操作
                with builder.CHILD(key="forkLoad", name="Fork Load", desc="Lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 开始高度参数
                        create_start_height(builder)

                        # 结束高度参数
                        create_end_height(builder)

                        # 识别参数
                        create_recognize(builder)

                        # 是否脱离库位
                        create_leave_loc(builder)

                        # 是否启用到货DI检测
                        with builder.CHILD(key="checkDI", name="Check DI", desc="Enable check di or not"):
                            builder.TYPE(ParamType.BOOL)
                            builder.DEFAULTVALUE(False)
                            
                        with builder.CHILD(key="moveHeightEnable", name="Move Height Enable",
                                           desc="Adjust height to load_move_height after load before move"):
                            builder.TYPE(ParamType.COMBO_BOX_BOOL)
                            builder.DEFAULTVALUE(0)

                            with builder.CHILDREN():
                                with builder.CHILD(key="OFF", name="OFF", desc=""):
                                    builder.TYPE(ParamType.ARRAY)
                            with builder.CHILDREN():
                                with builder.CHILD(key="ON", name="ON", desc=""):
                                    builder.TYPE(ParamType.ARRAY)

                                    with builder.CHILDREN():
                                        # 识别文件
                                        with builder.CHILD(key="loadMoveHeight", name="Load Move Height",
                                                           desc="Adjust height to load_move_height after load before move"):
                                            builder.TYPE(ParamType.FLOAT)
                                            builder.MIN_VALUE(ConfigParams.lift_zero)
                                            builder.MAX_VALUE(10)
                                            builder.UNIT("m")
                                            builder.SINGLESTEP(0.1)
                                            builder.DEFAULTVALUE(0.4)

                with builder.CHILD(key="forkUnload", name="Fork Unload", desc="Lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 开始高度参数
                        create_start_height(builder)

                        # 结束高度参数
                        create_end_height(builder)

                        # 是否脱离库位
                        create_leave_loc(builder)

                with builder.CHILD(key="forkHeight", name="Fork Height", desc="Lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 开始高度参数
                        create_start_height(builder)

                        # 行走高度参数
                        with builder.CHILD(key="forkMidHeight", name="Fork Middle Height",
                                           desc="The fork middle height for operations"):
                            builder.TYPE(ParamType.FLOAT)
                            # builder.REQUIRED(True)
                            builder.MIN_VALUE(ConfigParams.lift_zero)
                            builder.MAX_VALUE(ConfigParams.lift_max_height)
                            builder.UNIT("m")
                            builder.SINGLESTEP(0.1)
                            builder.DEFAULTVALUE(0.087)

                        # 结束高度参数
                        create_end_height(builder)

                with builder.CHILD(key="test", name="Test", desc="test"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="recTest", name="recTest", desc="recTest"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="recFile", name="recFile", desc="recognition file name"):
                            builder.TYPE(ParamType.BIND_TYPE)
                            # builder.REQUIRED(True)
                            builder.BINDTYPE("app:Recognition")
                            builder.DEFAULTVALUE("321(4).srec")

    builder.save_to_file()


class Robot:
    def __init__(self, args):
        super().__init__()
        # 脚本运行module类全局参数
        print(f"{args=}")
        self._init_global_params(args)

    def _init_global_params(self, args):
        self.init = True
        # 任务参数 打印数据
        self.task_args = args
        self.start_connect_time = None
        self.start_time = None
        self.state = dict()
        self.py_name = os.path.basename(__file__).split(".")[0]

        # 是否配置了电机
        self.is_lift_motor = False

        # 电机的实时位置
        self.lift_pos = 0.0

        # 电机的实时速度

        self.lift_speed = 0.0

        # 电机初始位置
        self.init_lift_pos = 0.0

        # 识别&运动
        self.recognize = False
        self.rec_task_init = True
        self.adjust_task1_init = True
        self.adjust_task2_init = True
        self.evaluate_task_init = True
        self.goods_opt_task_init = True
        self.rec_task_status = False
        self.adjust_task1_status = False
        self.adjust_task2_status = False
        self.evaluate_task_status = False
        self.goods_opt_task_status = False
        self.adjust_times = 0

        self.rec_failed_time = 0
        self.max_rec_time = 20
        self.rec_result = None
        self.rec_results = None
        self.rec_result_to_robot = {}
        self.rec_params = {}
        self.pallet_params = {}
        self.rec_location = [0, 0, 0]

        self.load_lift_height = 0.0
        self.unload_lift_height = 0.0
        self.load_lift_up_height = 0.0
        self.first_adjust = True

        # 路径导航
        self.go_path = goPath.GoPath()

        # operation
        self.task_list = []
        self.task_id = 0
        self.action_status = ActionStatus.NONE
        self.cur_task_list = []
        self.adjust_angle = 0.0
        self.target = [0, 0, 0, -1]

        # 解垛
        self.width_data = []
        self.height_data = []
        self.get_rec_result_id = 0
        self.unstack_error_type = None
        self.errors_pallet = None
        self.rec_result_pallet_num = 0

        self.test_rec_file = None

        # 获取任务参数
        print(f"{self.task_args=}")
        self.operation = self.task_args.get("operation", None)
        print(f"{self.operation=}")
        self.start_height = self.task_args.get("startHeight", None)
        self.end_height = self.task_args.get("endHeight", None)
        self.load_goods = self.task_args.get("loadGoods", None)
        self.fork_mid_height = self.task_args.get("forkMidHeight", None)
        self.lift_up_height = self.task_args.get("liftUpHeight", ConfigParams.lift_up_height)
        self.lift_down_height = self.task_args.get("liftDownHeight", ConfigParams.lift_down_height)
        self.useLoad_rec_height = self.task_args.get("useLoadRecHeight", False)
        self.leave_loc_dist = self.task_args.get("leaveLocDist", 0.0)
        self.check_di = self.task_args.get("checkDI", False)
        self.load_all = self.task_args.get("loadAll", True)
        self.readjust = self.task_args.get("readjust", ConfigParams.readjust)
        self.move_height_enable = self.task_args.get("moveHeightEnable", False)
        self.load_move_height = self.task_args.get("loadMoveHeight", False)
        self.adjust_height = self.task_args.get("adjustHeightEnable", False)
        self.fork_move_mode = self.task_args.get("forkMoveMode", 3)
        self.unstack_number = self.task_args.get("unstackNumber", None)
        self.rec_file = self.task_args.get("recFile", None)
        self.station_list = self.task_args.get("stationList", None)
        self.massage_name = self.task_args.get("massage_name", None)
        self.goods_check_enable = self.task_args.get("goods_check_enable", False)
        self.step_height = self.task_args.get("stepHeight", None)
        self.step_length = self.task_args.get("stepLength", None)
        self.loc_name = self.task_args.get("locName", None)
        self.leave_loc = self.task_args.get("leaveLoc", False)
        self.adjust_dir_first = self.task_args.get("adjustDirFirst", ConfigParams.adjust_dir_first)
        self.station_id = self.task_args.get("stationID", True)
        self.rec_file_id = self.task_args.get("recFileID", None)
        self.rec_with_region = self.task_args.get("recWithRegion", False)
        self.recognize = self.task_args.get("recognize", False)

        if self.rec_file_id == 1:
            self.rec_file = ConfigParams.rec_file1
        elif self.rec_file_id == 2:
            self.rec_file = ConfigParams.rec_file2
        elif self.rec_file_id == 3:
            self.rec_file = ConfigParams.rec_file3

        for p in Navigation.moveTask()["params"]:
            if p["key"] == "recognize":
                self.recognize = p["bool_value"]
            if p["key"] == "recFile":
                self.rec_file = p["str_value"]

        # 更新车型参数
        if ConfigParams.lift_motor != "None":
            self.is_lift_motor = True

        # # 更新识别参数
        # if self.rec_file:
        #     # 获取识别文件信息
        #     recFile = json.loads(Recognize.getRecFile(self.rec_file))
        #     self.state["recFile"] = recFile
        #     self.test_rec_file = Recognize.getRecFile(self.rec_file)
        #     # 遍历device_params下的array_param中的params
        #     for param in recFile.get("device_params", []):
        #         if "array_param" in param:
        #             for item in param["array_param"].get("params", []):
        #                 key = item["key"]
        #                 if "double_value" in item:
        #                     value = item["double_value"]
        #                 elif "bool_value" in item:
        #                     value = item["bool_value"]
        #                 else:
        #                     continue
        #                 # 添加到recParams中
        #                 self.rec_params[key] = value
        #         if param["key"] == "template_type":
        #             childKey = param["combo_param"].get("child_key", "")
        #             for item in param["combo_param"].get("child_params", []):
        #                 if item["key"] == childKey:
        #                     for autoParam in item.get("params", []):
        #                         key = autoParam["key"]
        #                         if "double_value" in autoParam:
        #                             value = autoParam["double_value"]
        #                         elif "bool_value" in autoParam:
        #                             value = autoParam["bool_value"]
        #                         else:
        #                             continue
        #                         # 添加到recParams中
        #                         self.rec_params[key] = value
        #     # 添加坐标系名称 recCoordinate
        #     if self.rec_params.get('in_global_framework', None):
        #         self.rec_params['recCoordinate'] = "world"
        #     elif not self.rec_params.get('in_global_framework', None):
        #         self.rec_params['recCoordinate'] = "robot"
        #     if self.rec_params.get('enable_back_dist', None):
        #         ConfigParams.back_dist = self.rec_params['back_dist']
        #     if not self.rec_params.get('enable_cargoContactDI', None):
        #         self.reachDI1 = -1
        #         self.reachDI2 = -1
        #         ConfigParams.multi_reach_di = [self.reachDI1, self.reachDI2]
        #     if self.rec_params.get('pallet_width', 0) == 0:
        #         self.status = ScriptStatus.FAILED
        #         Abnormal.setTask(53000, "识别文件 {self.recFile} 中pallet_width为 0"
        #                          , "", "", "")
        #         return self.status
        # else:
        #     self.recognize = False
        # self.rec_params['recCoordinate'] = "world"
        self.rec_params['recCoordinate'] = "robot"

    # 任务参数检查
    def _init_check_args(self, args):
        if self.operation == "":
            Abnormal.setTask(53000, "operation is empty!!!", "", "", "")
            self.status = ScriptStatus.FAILED
            return self.status
        if self.operation == "lift" and self.end_height is None:
            Abnormal.setTask(53000, "请输入endHeight", "", "", "")
            self.status = ScriptStatus.FAILED
            return self.status
        log.debug("[SFL-scripts][{}]".format(self.task_args))

    def run(self, args):
        self.status = ScriptStatus.RUNNING
        # 实时数据获取
        self.get_message()
        # 运行前车体数据初始化
        self.init_data(args)
        # 任务执行
        self.opt()
        # 数据上报
        self.log_update()
        Module.set_status(self.status)
        return self.status

    def get_message(self):
        # log.debug(str(odo))
        # 获取点击初始位置
        self.motor_info = Odometer.get_data()["motorInfo"]
        # self.state["motor_info"] = self.motor_info
        # Module.report_info(self.state)
        # # 获取电机数据
        self.lift_pos = Motor.get_motor_pos(ConfigParams.lift_motor)
        self.lift_speed = Motor.get_motor_speed(ConfigParams.lift_motor)
        log.debug("[fork_data][{}|{}]".format(self.lift_pos, self.lift_speed, ))

    # def print_info(self):
    #     # 打印当前任务队列、当前任务、当前任务id、当前任务状态
    #     log.info(f"{Module.get_task_args()=}")
    #     log.info(f"{Module.get_task_id()=}")
    #     log.info(f"{Module.get_status()=}")

    def init_data(self, args):
        if self.init:
            self.init = False
            self.task_args = args
            log.info(f"{Module.get_task_args()=}")
            log.info(f"{Module.get_task_id()=}")
            self.init_lift_pos = self.lift_pos

            moveTask = Navigation.moveTask()
            dispatcherArgs = {}
            for p in moveTask["params"]:
                if p["key"] == "dispatcherArgs":
                    ss = p["string_value"]
                    dispatcherArgs = json.loads(ss)
            if "targetLoc" in dispatcherArgs:
                self.target = Navigation.getLM(dispatcherArgs['targetLoc'], True)
            elif "targetLoc" not in dispatcherArgs and 'target_x' in moveTask:
                Module.report_info(self.state)
                self.target = [
                    moveTask['target_x'], moveTask['target_y'], moveTask['target_angle'],
                    moveTask['target_name']
                ]
            else:
                self.target = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0]), -1]

            if self.target[3] != -1:
                self.adjust_angle = self.target[2] - math.radians(Loc.get_angle()[0])

            Recognize.resetRec()  # 重置识别模块
            Abnormal.clear(57300)
            log.debug("[SFLInit][{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}]".format(
                self.operation, self.start_height, self.end_height, self.fork_mid_height, self.lift_up_height,
                self.lift_down_height,
                self.leave_loc_dist, self.check_di, self.load_all, self.readjust, self.move_height_enable,
                self.load_move_height, self.adjust_height, self.fork_move_mode, self.unstack_number, self.rec_file,
                self.recognize))

    def opt(self):
        speed_dict = {}
        if self.operation == "":
            self.status = ScriptStatus.FINISHED
        elif self.operation == "forkLoad":
            self.load()
        elif self.operation == "forkUnload":
            self.unload()
        elif self.operation == "simple_unload":
            self.simple_unload()
        elif self.operation == "lift":
            self.lift()
        elif self.operation == "stepLift":
            self.stepLift()
        elif self.operation == "zero":
            self.zero()
        elif self.operation == "recTest":
            self.rec_test()
        elif self.operation == "forkHeight":
            self.fork_height()
        # elif self.operation == "weightGood":
        #     self.weightGood()
        elif self.operation == "getMassage":
            self.getMassage()
        elif self.operation == "locDetectMid":
            self.locDetectMid()
        elif self.operation == "locDetectBackLaser":
            self.locDetectBackLaser()
        elif self.operation == "goodsCheck":
            self.goodsCheck()
        elif self.operation == "test":
            self.test()
        elif self.operation == "update_data":
            self.update_data()

        else:
            Abnormal.setTask(53000, f"operation 参数错误:{self.operation}", "", "", "")
            self.status = ScriptStatus.FAILED
        if self.action_status == ActionStatus.FINISHED:
            # Abnormal.clear(57300)
            self.status = ScriptStatus.FINISHED
        elif self.action_status == ActionStatus.FAILED:
            self.status = ScriptStatus.FAILED
        if self.status is ScriptStatus.FAILED:
            Navigation.stopRobot(True)
        self.cur_task_list = []
        for task in self.task_list:
            self.cur_task_list.append(task.opt_info)
        # controller = Controller.get_data()
        # self.state["speed_dict"] = speed_dict
        # self.state["controller"] = controller
        self.state["cur_task_list"] = self.cur_task_list

    def log_update(self):

        self.state["MoveStatus"] = self.status
        self.state["rec_params"] = self.rec_params
        if self.is_lift_motor and (self.operation == "lift" or self.operation == "forkLoad"
                                   or self.operation == "forkUnload" or self.operation == "stepLift"
                                   or self.operation == "zero" or self.operation == "fork_height"):
            lift_status = dict()
            lift_status["isLiftMotor"] = self.is_lift_motor
            lift_status["liftPos"] = self.lift_pos
            lift_status["liftSpeed"] = self.lift_speed
            lift_status["minPos"] = ConfigParams.lift_zero
            lift_status["maxPos"] = ConfigParams.lift_max_height
            self.state["lift_status"] = lift_status

        # self.state["lift_reach_state"] = Motor.isMotorReached(self.liftMotor)
        # self.state["testRecFile"] = self.testRecFile
        self.state["args"] = self.task_args
        # self.state["moveTask"] = Navigation.moveTask()
        # self.state["recognize"] = self.recognize
        strState = json.dumps(self.state)
        Module.report_info(self.state)
        log.debug("[SFLState][{}]".format(strState))
        log.debug("[SFLState][{}|{}|{}|{}]".format(
            self.lift_pos, self.status, self.task_id, self.action_status))

    def lift(self):
        if self.end_height is None:
            Abnormal.setTask(53000, "end_height is empty {}".format(json.dumps(self.task_args))
                             , "", "", "")
            self.status = ScriptStatus.FAILED
        else:
            if self.action_status == ActionStatus.NONE:
                self.action_status = ActionStatus.RUNNING
                if self.start_height:
                    self.task_list = [
                        lift(ConfigParams.lift_motor, self.start_height),
                        lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di)
                    ]
                else:
                    self.task_list = [
                        lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di)
                    ]
                self.task_id = 0
            else:
                self.runTaskList()
            if self.action_status == ActionStatus.FINISHED:
                if self.load_goods is not None:
                    if self.load_goods:
                        Navigation.setGoodsShape(0.001, 0.001, 0.001)
                    elif self.load_goods is False:
                        Navigation.clearGoodsShape()
            curState = dict()
            curState["state"] = self.action_status
            curState["liftPos"] = self.lift_pos
            curState["liftSpeed"] = self.lift_speed
            curState["taskId"] = self.task_id
            self.state["lift"] = curState

    def lift_load(self):
        if self.action_status == ActionStatus.NONE:
            if Navigation.hasGoods():
                self.state["load"] = "Fork has goods, cannot load"
                Abnormal.setTask(53000, "Fork has goods, cannot load", "", "", "")
                self.status = ScriptStatus.FAILED
                return self.status
            self.action_status = ActionStatus.RUNNING
            if self.end_height is None:
                Trace.event("end_height is empty {}".format(json.dumps(self.task_args)))
                self.task_list = [
                ]
            else:
                self.task_list = [
                    lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di)
                ]
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["operationStatus"] = self.action_status
        curState["liftPos"] = self.lift_pos
        curState["liftSpeed"] = self.lift_speed
        curState["taskId"] = self.task_id
        self.state["lift_load"] = curState

    def lift_unload(self):
        if self.action_status == ActionStatus.NONE:

            self.action_status = ActionStatus.RUNNING
            if self.end_height is None:
                Trace.event("end_height is empty {}".format(json.dumps(self.task_args)))
                self.task_list = [
                ]
            else:
                self.task_list = [
                    lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di)
                ]
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["operationStatus"] = self.action_status
        curState["liftPos"] = self.lift_pos
        curState["liftSpeed"] = self.lift_speed
        curState["taskId"] = self.task_id
        self.state["lift_unload"] = curState

    def stepLift(self):
        if self.step_height is None:
            Abnormal.setTask(53000, "stepHeight is empty {}".format(json.dumps(self.task_args)),
                             "", "", "")
            self.status = ScriptStatus.FAILED
        elif self.init_lift_pos >= ConfigParams.lift_max_height and self.step_height > 0:
            Trace.event("Current fork height is liftMaxHeight, can not lift up! "
                        "forkHeight：{}".format(self.init_lift_pos))
            self.status = ScriptStatus.FINISHED
        elif self.init_lift_pos <= ConfigParams.lift_zero and self.step_height < 0:
            Trace.event("Current fork height is liftZero, can not lift down! "
                        "forkHeight：{}".format(self.init_lift_pos))
            self.status = ScriptStatus.FINISHED
        else:
            if self.action_status == ActionStatus.NONE:
                self.action_status = ActionStatus.RUNNING
                self.end_height = self.init_lift_pos + self.step_height
                stepLiftHeight = self.init_lift_pos + self.step_height
                if self.end_height > ConfigParams.lift_max_height:
                    self.end_height = ConfigParams.lift_max_height
                    Trace.event(
                        f"end_height{stepLiftHeight} is higher than liftMaxHeight{ConfigParams.lift_max_height}")
                if self.end_height < ConfigParams.lift_zero:
                    self.end_height = ConfigParams.lift_zero
                    Trace.event(f"end_height{stepLiftHeight} is lower than liftZero{ConfigParams.lift_zero}")
                self.task_list = [
                    lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di)
                ]
                self.task_id = 0
            else:
                self.runTaskList()
            curState = dict()
            curState["state"] = self.action_status
            curState["liftPos"] = self.lift_pos
            curState["liftSpeed"] = self.lift_speed
            curState["taskId"] = self.task_id
            self.state["stepLift"] = curState

    def rec_test(self):
        if "recFile" not in self.task_args:
            Abnormal.setTask(53000, "rec_file is empty {}".format(json.dumps(self.task_args)),
                             "", "", "")
            self.status = ScriptStatus.FAILED
        else:
            if self.action_status == ActionStatus.NONE:
                self.action_status = ActionStatus.RUNNING
                self.task_list = [recPallet()]
                self.task_id = 0
            else:
                self.runTaskList()
            curState = dict()
            curState["state"] = self.action_status
            curState["taskId"] = self.task_id
            curState["rec_results"] = self.rec_results
            self.state["recFile"] = json.loads(Recognize.getRecFile(self.rec_file))
            curState["target"] = self.target
            self.state["recTest"] = curState

    def goMapPathDi(self):
        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            self.task_list = [goMapPathDi()]
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.task_id
        curState["moveTask"] = Navigation.moveTask()
        self.state["goMapPathDi"] = curState

    def test(self):
        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            self.task_list = [adjustGo(False, "robot", -1, 0.1, 0.5,
                                       0, 0, 0, False, [-1])]
            self.task_id = 0
        else:
            self.runTaskList()

        curState = dict()

        self.state["diStatus"] = self.batch_check_di_status([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    def update_data(self):
        self.status = ScriptStatus.FINISHED

    def load(self):
        if self.action_status == ActionStatus.NONE:

            if Navigation.hasGoods():
                self.state["load"] = "Fork has goods, cannot load"
                Abnormal.setTask(53000, "Fork has goods, cannot load",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
                return self.status
            if self.start_height is None \
                    and self.end_height is None \
                    and self.lift_up_height is None:
                self.state["load"] = "start_height & end_height & lift_up_height is missing"
                Abnormal.setTask(53000, "start_height & end_height & lift_up_height is missing",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
                return
            elif self.start_height is None:
                self.start_height = self.init_lift_pos

            self.action_status = ActionStatus.RUNNING
        elif self.action_status == ActionStatus.RUNNING:
            # 识别后取货
            if self.recognize:
                # 识别前调整任务：货叉放平（forward）、收回货叉、调整货叉高度至识别高度
                if self.rec_task_init:
                    self.task_list = []
                    if self.target[3] != -1 and self.adjust_dir_first:
                        self.task_list.append(dirAdjust(self.adjust_angle))
                    # 调整货叉高度至识别高度
                    self.task_list.append(lift(ConfigParams.lift_motor, self.start_height))
                    # 识别及二次识别
                    if self.first_adjust:
                        self.task_list.append(recPallet())
                        self.first_adjust = False
                    else:
                        if ConfigParams.omni_model:
                            pass
                        else:
                            self.task_list.extend([
                                GoStraight(ConfigParams.readjust_forward_dist, straightMoveMode.forward),
                                recPallet()
                            ])
                    self.task_id = 0
                    self.rec_task_init = False
                if self.readjust:
                    # 识别后调整
                    if self.adjust_task1_init and not self.rec_task_init and self.rec_task_status:
                        pos2robotTarget = []
                        if self.rec_params['recCoordinate'] == "world":
                            robot2world = [Loc.get_position()[0], Loc.get_position()[1],
                                           math.radians(Loc.get_angle()[0])]  # 获取机器人在世界坐标系下的位置
                            Target = [self.rec_result['x'], self.rec_result['y'],
                                      self.rec_result['yaw']]  # 目标点在世界坐标系的位置
                            pos2robotTarget = Pos2Base(Target, robot2world)  # 转换识别结果到机器人坐标系
                            shelf_center2target = [-0.5, 0, 0]  # 货架中心在识别结果坐标系下的位置（根据识别文件设置的长宽）
                            shelf_center2robot = Pos2World(shelf_center2target, pos2robotTarget)  # 计算实际货架中心在机器人坐标系下的位置
                        elif self.rec_params['recCoordinate'] == "robot":
                            pos2robotTarget = [self.rec_result['x'], self.rec_result['y'],
                                               self.rec_result['yaw']]  # 目标点在机器人坐标系的位置
                        pos2robotForwardX = pos2robotTarget[0] + ConfigParams.min_ahead_dist * math.cos(
                            pos2robotTarget[2])
                        pos2robotForwardY = pos2robotTarget[1] + ConfigParams.min_ahead_dist * math.sin(
                            pos2robotTarget[2])
                        pos2robotForward = [pos2robotForwardX, pos2robotForwardY, pos2robotTarget[2]]
                        self.state["pos2robotForward"] = pos2robotForward
                        self.task_list = [
                            adjustGo(ConfigParams.omni_model, "robot",
                                     pos2robotForward[0], pos2robotForward[1], pos2robotForward[2],
                                     0, 0, 0, False, [-1]),
                            recPallet()
                        ]
                        self.task_id = 0
                        self.adjust_task1_init = False
                    # 二次调整判断
                    if self.evaluate_task_init and not self.adjust_task1_init and self.adjust_task1_status:
                        self.task_list = [
                            precisionEvaluate()
                        ]
                        self.task_id = 0
                        self.evaluate_task_init = False
                    if (self.adjust_task2_init
                            and not self.evaluate_task_init and self.evaluate_task_status
                            and not self.adjust_task1_init and self.adjust_task1_status):
                        self.task_list = [
                            lift(ConfigParams.lift_motor, self.load_lift_height),
                            adjustGo(ConfigParams.omni_model, "robot",
                                     -ConfigParams.min_ahead_dist, 0, 0, ConfigParams.back_dist,
                                     0, 0, ConfigParams.check_all_di, ConfigParams.multi_reach_di),
                        ]
                        self.task_id = 0
                        self.adjust_task2_init = False
                else:
                    if self.adjust_task2_init and not self.rec_task_init and self.rec_task_status:
                        self.task_list = [lift(ConfigParams.lift_motor, self.load_lift_height)]
                        pos2robotTarget = []
                        if self.rec_params['recCoordinate'] == "world":
                            robot2world = [Loc.get_position()[0], Loc.get_position()[1],
                                           math.radians(Loc.get_angle()[0])]
                            Target = [self.rec_result['x'], self.rec_result['y'],
                                      self.rec_result['yaw']]  # 目标点在世界坐标系的位置
                            pos2robotTarget = Pos2Base(Target, robot2world)
                        elif self.rec_params['recCoordinate'] == "robot":
                            pos2robotTarget = [self.rec_result['x'], self.rec_result['y'],
                                               self.rec_result['yaw']]  # 目标点在机器人坐标系的位置
                        self.task_list.append(
                            adjustGo(ConfigParams.omni_model, "robot",
                                     pos2robotTarget[0], pos2robotTarget[1], pos2robotTarget[2],
                                     ConfigParams.back_dist, ConfigParams.min_ahead_dist, ConfigParams.ahead_dist,
                                     ConfigParams.check_all_di, ConfigParams.multi_reach_di)
                        )
                        self.task_id = 0
                        self.adjust_task2_init = False
                        self.evaluate_task_init = False
                        self.evaluate_task_status = True
                if self.goods_opt_task_init and not self.adjust_task2_init and self.adjust_task2_status:
                    # self.task_list = []
                    self.task_list = [
                        backCheckDi(ConfigParams.check_all_di, ConfigParams.multi_reach_di)
                    ]
                    if self.end_height:
                        self.task_list.append(
                            lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di))
                    else:
                        self.task_list.append(lift(ConfigParams.lift_motor, self.start_height + self.lift_up_height,
                                                   ConfigParams.lift_up_reach_di))
                    # 脱离库位
                    if self.leave_loc:
                        if ConfigParams.fork_offset_theta != 0:
                            self.task_list.append(GoStraight(self.leave_loc_dist, straightMoveMode.backward, "y"))
                        else:
                            self.task_list.append(GoStraight(self.leave_loc_dist, straightMoveMode.forward))
                    # 是否调整货叉高度至行走高度
                    if self.move_height_enable:
                        self.task_list.append(lift(ConfigParams.lift_motor, self.load_move_height))

                    self.task_id = 0
                    self.goods_opt_task_init = False
            # 不识别，盲叉取货
            else:
                # 任务动作初始化
                if self.goods_opt_task_init:
                    self.task_list = [
                        lift(ConfigParams.lift_motor, self.start_height),
                        goMapPathDi()
                    ]
                    if self.end_height:
                        self.task_list.append(
                            lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di))
                    else:
                        self.task_list.append(lift(ConfigParams.lift_motor, self.start_height + self.lift_up_height,
                                                   ConfigParams.lift_up_reach_di))
                    # 脱离库位
                    if self.leave_loc:
                        if ConfigParams.fork_offset_theta != 0:
                            self.task_list.append(GoStraight(self.leave_loc_dist, straightMoveMode.backward, "y"))
                        else:
                            self.task_list.append(GoStraight(self.leave_loc_dist, straightMoveMode.forward))
                    # 是否调整货叉高度至行走高度
                    if self.move_height_enable:
                        self.task_list.append(lift(ConfigParams.lift_motor, self.load_move_height))
                    self.task_id = 0
                    self.goods_opt_task_init = False
            self.runTaskList()
        if (not self.rec_task_init and not self.rec_task_status
                and self.action_status == ActionStatus.FINISHED):
            self.rec_task_status = True
            self.action_status = ActionStatus.RUNNING
            Trace.event("recTask Finish")
        if not self.adjust_task1_init and not self.adjust_task1_status and self.action_status == ActionStatus.FINISHED:
            self.adjust_task1_status = True
            self.action_status = ActionStatus.RUNNING
            Trace.event("adjustTask1 Finish")
        if not self.adjust_task2_init and not self.adjust_task2_status and self.action_status == ActionStatus.FINISHED:
            self.adjust_task2_status = True
            self.action_status = ActionStatus.RUNNING
            Trace.event("adjustTask2 Finish")
        if (not self.goods_opt_task_init and not self.goods_opt_task_status
                and self.action_status == ActionStatus.FINISHED):
            self.goods_opt_task_status = True
            Navigation.setGoodsShapeWithName(0.001, 0.001, 0.001, self.task_args.get("recfile", ""))
            # todo
            # if self.rec_file:
            #     width = max(self.rec_params['pallet_width'], self.rec_params['goodsWidth'])
            #     length = max(self.rec_params['pallet_length'], self.rec_params['goodsLength'])
            #     if ConfigParams.fork_offset_theta != 0:
            #         Navigation.setGoodsShape(width / 2, width / 2, length)
            #     else:
            #         Navigation.setGoodsShape(ConfigParams.pallet2odo, length - ConfigParams.pallet2odo, width)
            Trace.event("moveTask Finish")
            self.status = ScriptStatus.FINISHED
        if self.action_status == ActionStatus.FAILED:
            self.status = ScriptStatus.FAILED

        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.lift_pos
        curState["rec_task_init"] = self.rec_task_init
        curState["adjustTaskInit"] = self.adjust_task1_init
        curState["evaluate_task_init"] = self.evaluate_task_init
        curState["moveTaskInit"] = self.goods_opt_task_init

        curState["rec_task_status"] = self.rec_task_status
        curState["adjustTaskStatus"] = self.adjust_task1_status
        curState["evaluate_task_status"] = self.evaluate_task_status
        curState["moveTaskStatus"] = self.goods_opt_task_status
        curState["adjust_times"] = self.adjust_times
        curState["rec_result_to_robot"] = self.rec_result_to_robot  # 叉取的栈板识别结果
        # curState["recPos"] = self.recPos
        curState["back_dist"] = ConfigParams.back_dist
        curState["loadLiftHeight"] = self.load_lift_height  # 栈板叉取时货叉高度
        curState["loadLiftUpHeight"] = self.load_lift_up_height  # 栈板叉取后的货叉高度
        if not self.load_all:
            curState["widthData"] = self.width_data
            curState["unstackErrorType"] = self.unstack_error_type
            curState["errorsPallet"] = self.errors_pallet
            curState["recResultPalletNum"] = self.rec_result_pallet_num  # 识别结果中栈板的数量
            curState["pallet_normal_count"] = ConfigParams.pallet_normal_count  # 栈板正常数量
            curState["palletHeight"] = self.height_data
        curState["taskId"] = self.task_id
        self.state["load"] = curState

    def unload(self):
        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            if self.start_height is None \
                    and self.end_height is None \
                    and self.lift_down_height is None:
                self.state["load"] = "start_height & end_height & lift_down_height is missing"
                Abnormal.setTask(53000,
                                 "start_height & end_height & lift_down_height is missing",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
                return
            if self.start_height:
                if 0 <= self.start_height < ConfigParams.lift_zero:
                    self.start_height = ConfigParams.lift_zero
                    Trace.event(f"start_height 小于货叉最小起升高度{ConfigParams.lift_zero}")
                elif self.start_height > ConfigParams.lift_max_height:
                    self.start_height = ConfigParams.lift_max_height
                    Trace.event(f"start_height 大于货叉最大起升高度{ConfigParams.lift_max_height}")
            else:
                self.start_height = self.lift_pos
            if self.useLoad_rec_height:
                set_info_data = dict()
                end_height_data = ScriptData.get("loadLiftHeight")
                self.end_height = ScriptData.get("loadLiftHeight").get('loadLiftHeight', None)
                end_height_data_time = ScriptData.get("loadLiftHeight").get('end_height_data_time', None)
                # set_info_data["end_height_data"] = end_height_data
                set_info_data["loadLiftHeight"] = self.end_height
                set_info_data["end_height_data_time"] = end_height_data_time
                self.state["unload_end_height_data"] = set_info_data
                if self.end_height is None or end_height_data_time is None:
                    Abnormal.setTask(53000, "loadLiftHeight is not in globalData",
                                     "", "", "")
            if self.end_height:
                if 0 <= self.end_height < ConfigParams.lift_zero:
                    self.end_height = ConfigParams.lift_zero
                    Trace.event(f"end_height 小于货叉最小起升高度{ConfigParams.lift_zero}")
                elif self.end_height > ConfigParams.lift_max_height:
                    self.end_height = ConfigParams.lift_max_height
                    Trace.event(f"end_height 大于货叉最大起升高度{ConfigParams.lift_max_height}")
            else:
                Abnormal.setTask(53000, "end_height is missing",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
                return self.status
        elif self.action_status == ActionStatus.RUNNING:
            if self.rec_task_init:
                self.task_list = []
                if self.target[3] != -1 and self.adjust_dir_first:
                    self.task_list.append(dirAdjust(self.adjust_angle))
                # 调整货叉高度至识别高度并识别
                self.task_list.append(lift(ConfigParams.lift_motor, self.start_height))
                # 是否识别放货
                if self.recognize:
                    self.task_list.append(recPallet())
                elif not self.recognize or not self.adjust_height:
                    self.unload_lift_height = self.start_height
                self.task_id = 0
                self.rec_task_init = False
            if self.goods_opt_task_init and not self.rec_task_init and self.rec_task_status:
                self.task_list = [lift(ConfigParams.lift_motor, self.unload_lift_height)]
                if self.recognize:
                    self.task_list.append(
                        adjustGo(ConfigParams.omni_model, self.rec_params['recCoordinate'],
                                 self.rec_result['x'], self.rec_result['y'], self.rec_result['yaw'],
                                 ConfigParams.back_dist, ConfigParams.min_ahead_dist, ConfigParams.ahead_dist, False,
                                 [-1])
                    )
                    self.task_list.append(lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di))
                else:
                    self.task_list.append(goMapPathDi())
                    self.task_list.append(
                        lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di))
                if self.leave_loc:
                    if ConfigParams.fork_offset_theta != 0:
                        self.task_list.append(GoStraight(self.leave_loc_dist, straightMoveMode.backward, "y"))
                    else:
                        self.task_list.append(GoStraight(self.leave_loc_dist, straightMoveMode.forward))
                self.task_id = 0
                self.goods_opt_task_init = False
            self.runTaskList()
        if (not self.rec_task_init and not self.rec_task_status
                and self.action_status == ActionStatus.FINISHED):
            self.rec_task_status = True
            self.action_status = ActionStatus.RUNNING
            Trace.event("recTask Finish")
        if (not self.goods_opt_task_init and not self.goods_opt_task_status
                and self.action_status == ActionStatus.FINISHED):
            self.goods_opt_task_status = True
            Navigation.clearGoodsShape()
            Trace.event("moveTask Finish")
            self.status = ScriptStatus.FINISHED
        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.lift_pos
        curState["taskId"] = self.task_id
        self.state["forkUnload"] = curState

    def simple_unload(self):
        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            self.task_list = []
            if self.end_height:
                if 0 <= self.end_height < ConfigParams.lift_zero:
                    self.end_height = ConfigParams.lift_zero
                    Trace.event(f"end_height 小于货叉最小起升高度{ConfigParams.lift_zero}")
                elif self.end_height > ConfigParams.lift_max_height:
                    self.end_height = ConfigParams.lift_max_height
                    Trace.event(f"end_height 大于货叉最大起升高度{ConfigParams.lift_max_height}")
                self.task_list.append(lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di))
            self.task_id = 0
        elif self.action_status == ActionStatus.RUNNING:
            self.runTaskList()
        elif self.action_status == ActionStatus.FINISHED:
            Navigation.clearGoodsShape()
            self.status = ScriptStatus.FINISHED
        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.lift_pos
        curState["taskId"] = self.task_id
        self.state["simple_unload"] = curState

    def fork_height(self):

        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            self.task_list = []
            if self.start_height:
                self.task_list.append(lift(ConfigParams.lift_motor, self.start_height))
            self.task_list.append(GoMapWithFork(self.fork_mid_height, self.fork_move_mode))
            if self.end_height:
                self.task_list.append(lift(ConfigParams.lift_motor, self.end_height, ConfigParams.lift_up_reach_di))
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.lift_pos
        curState["taskId"] = self.task_id
        self.state["fork_height"] = curState

    def zero(self):
        if Navigation.hasGoods() or Di.get_di(ConfigParams.reach_di1) or Di.get_di(ConfigParams.reach_di2):
            Abnormal.setTask(53000, "Fork has goods, cannot cannot run operation of zero",
                             "", "", "")
            self.status = ScriptStatus.FAILED
            return
        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            reachDI = -1
            self.task_list = []
            self.task_list.append(lift(ConfigParams.lift_motor, ConfigParams.lift_zero))
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["state"] = self.action_status
        curState["liftPos"] = self.lift_pos
        curState["taskId"] = self.task_id
        self.state["zero"] = curState

    # def weightGood(self):
    #     if self.action_status == ActionStatus.NONE:
    #         self.action_status = ActionStatus.RUNNING
    #         self.taskList = [weightGood()]
    #         self.taskId = 0
    #     else:
    #         self.runTaskList()
    #     curState = dict()
    #     curState["state"] = self.action_status
    #     curState["taskId"] = self.taskId
    #     self.state["weightGood"] = curState

    def goodsCheck(self):
        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            self.task_list = [goodsCheck(self.rec_file)]
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.task_id
        self.state["goodsCheck"] = curState

    def getMassage(self):
        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            self.task_list = [getMassage(f"rbk.protocol.{self.massage_name}")]
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.task_id
        self.state["getMassage"] = curState

    def locDetectMid(self):
        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            self.task_list = [locDetectMid(self.loc_name, self.rec_file)]
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["state"] = self.action_status
        curState["taskId"] = self.task_id
        self.state["locDetectMid"] = curState

    def locDetectBackLaser(self):

        if self.action_status == ActionStatus.NONE:
            self.action_status = ActionStatus.RUNNING
            dispatcherArgs = {}
            moveTask = Navigation.moveTask()
            for p in moveTask["params"]:
                if p["key"] == "dispatcherArgs":
                    ss = p["string_value"]
                    dispatcherArgs = json.loads(ss)
            if "targetLoc" in dispatcherArgs:
                if dispatcherArgs["targetLoc"] != "":
                    self.loc_name = dispatcherArgs["targetLoc"]
            self.target = Navigation.getLM(self.loc_name, True)
            self.adjust_angle = self.target[2] - math.radians(Loc.get_angle()[0])
            if self.target[3] != -1:
                self.task_list = [
                    dirAdjust(self.adjust_angle),
                    lift(ConfigParams.lift_motor, self.end_height),
                    locDetectBackLaser(self.loc_name)
                ]
            else:
                Abnormal.setTask(53000, "{self.loc_name} does not exist",
                                 "", "", "")
                self.status = ScriptStatus.FAILED
            self.task_id = 0
        else:
            self.runTaskList()
        curState = dict()
        curState["state"] = self.action_status
        curState["adjustAngle"] = self.adjust_angle
        curState["target"] = self.target
        curState["taskId"] = self.task_id
        self.state["locDetectBackLaser"] = curState

    def runTaskList(self):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == ActionStatus.NONE:
                self.task_list[self.task_id].reset()
            elif self.task_list[self.task_id].status == ActionStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == ActionStatus.FAILED:
                self.action_status = ActionStatus.FAILED
            else:
                self.task_list[self.task_id].run(self)
        else:
            self.action_status = ActionStatus.FINISHED

    def forkCollision(self, leftDist: float) -> tuple:
        """
        货叉尖端距离传感器的碰撞检测 rbk
        :param leftDist: 剩余距离
        :return: bool, obsDist
        """
        sensor = Distance.get_data()
        obsDist = -1.0
        if "node" not in sensor:
            Trace.event("distanceSensor empty")
            return False, obsDist
        nodeSs = ""
        for data in sensor["node"]:
            if data.get('id', -1) in ConfigParams.distance_node_id \
                    and data.get('valid', False) is True \
                    and data.get('forbidden', True) is False \
                    and 'dist' in data:
                if obsDist < 0:
                    obsDist = data['dist']
                else:
                    obsDist = min(obsDist, data['dist'])
            nodeSs = "{}|{}|{}|{}|{}".format(data.get('id', -1), data.get('valid', False), data.get('forbidden', True),
                                             data.get('dist', -1), obsDist)
            log.debug("[distanceNode][{}]".format(nodeSs))

        if obsDist < 0:
            return False, obsDist
        if leftDist < obsDist:
            return False, obsDist
        elif ConfigParams.obs_stop_dist < obsDist:
            return False, obsDist
        return True, obsDist

    def backLaserCheck(self) -> bool:
        """
        :return: 是否碰撞
        """
        if Navigation.laserCollision(ConfigParams.back_laser):
            return True
        return False

    def move(self, moveArgs) -> bool:
        if self.go_path.status != 3 or self.go_path.status != 4:
            self.go_path.run(moveArgs)
        if self.go_path.status == ScriptStatus.FINISHED:
            self.go_path.reset()
            return True
        return False

    def forkGoodsReach(self, reachDi: list) -> bool:
        """
        货叉到位DI检测
        :return: bool
        """
        DI = Di.get_data()
        if len(reachDi) < 4:
            # 最多支持4个到位DI，不足时补全
            num2Add = 4 - len(reachDi)
            # 使用None补全列表
            reachDi.extend([-1] * num2Add)
        self.allDiStatus = self.batch_check_di_status(reachDi)
        if ConfigParams.check_all_di:
            if all(self.allDiStatus):
                return True
        else:
            if any(self.allDiStatus):
                return True
        return False

    def batch_check_di_status(self, di_ids: List[int]) -> List[Optional[bool]]:
        """批量查询 DI 状态并返回顺序列表

        Args:
            di_ids: DI 编号列表，顺序重要 (例如 [0,1,3,4])

        Returns:
            包含DI状态的列表，顺序与输入di_ids相同
            (状态为bool类型，出错时为None)
        """
        results = []
        for di_id in di_ids:
            try:
                # 调用接口获取单个DI状态
                status = Di.get_di(di_id)
                results.append(status)
            except Exception as e:
                print(f"查询 DI {di_id} 时出错: {str(e)}")
                results.append(None)  # 错误时记录 None

        return results

    def seqGenerate(self):
        # 获取当前时间
        currentTime = datetime.now()

        # 提取年、月、日、小时、分钟、秒、毫秒
        year = currentTime.year
        month = currentTime.month
        day = currentTime.day
        hour = currentTime.hour
        minute = currentTime.minute
        second = currentTime.second
        millisecond = currentTime.microsecond // 1000  # 将微秒转换为毫秒

        # 将时间信息合并成一个字符串
        # 格式为：年月日时分秒毫秒
        currentTimeSeq = int(f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}{millisecond:03d}")
        return currentTimeSeq

    def reset(self):
        self.status = ScriptStatus.RUNNING
        self.start_time = time.time()
        self.init = True
        self.state = dict()
        self.task_id = 0
        self.action_status = ActionStatus.NONE

    def cancel(self):
        Navigation.stopRobot(True)
        log.info("script cancel")
        Module.set_status(ScriptStatus.NONE)
        return

    def suspend(self):
        Navigation.stopRobot(True)
        log.info("script suspended")
        Module.set_status(ScriptStatus.SUSPENDED)
        self.start_connect_time = time.time()

    def resume(self):
        log.info("script resume")
        Module.set_status(ScriptStatus.RUNNING)


class BaseAction:
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        self.action_name = action_name or self.__class__.__name__
        self.start_time = time.time()
        self.action_status = ActionStatus.NONE
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


class lift(BaseAction):
    def __init__(self, motorName: str, dist: float, reachDi=-1):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = ScriptStatus.NONE
        self.init = True
        self.motor = motorName
        self.dist = dist
        self.detectTimes = 0
        self.weightData = []
        self.weightResult = 0
        self.initPos = 0
        # self.weightGoodFlag = True
        self.collision = False
        self.taskContinue = True
        self.resetInit = True
        self.reachDi = reachDi

    def run(self, robot: Robot):
        self.status = ScriptStatus.RUNNING
        if self.init:
            self.initPos = robot.lift_pos
            Abnormal.clear(57300)
            Abnormal.clear(53901)
            if self.dist < ConfigParams.lift_zero:
                Abnormal.setTask(55300, f"升降电机目标位置: {self.dist}, "
                                        f"低于最小高度: {ConfigParams.lift_zero}",
                                 "", "", "")
                self.dist = ConfigParams.lift_zero
            elif self.dist > ConfigParams.lift_max_height:
                Abnormal.setTask(55300, f"升降电机目标位置: {self.dist}, "
                                        f"高于最大高度: {ConfigParams.lift_max_height}",
                                 "", "", "")
                self.dist = ConfigParams.lift_max_height
            print(f"start speed:{NavSpeed.get_speeds()}")
            self.init = False

        # if self.weightGood(robot) and ConfigParams.weightGoodOn and self.dist > self.initPos:
        #     # if Di.get_di(15):
        #     self.taskContinue = False
        if self.taskContinue:
            if self.dist < self.initPos:
                # 货叉下降需要检查一下，货叉下降是否安全
                if robot.backLaserCheck():
                    self.collision = True
                    Navigation.stopRobot(True)
                    Abnormal.setTask(55300, f"后置激光检测到碰撞",
                                     "", "", "")
                elif Di.get_di(ConfigParams.fork_tail_di1) or Di.get_di(ConfigParams.fork_tail_di2):
                    self.collision = True
                    Navigation.stopRobot(True)
                    Abnormal.setTask(55300, f"叉尖DI检测到碰撞，"
                                            f"DI {ConfigParams.fork_tail_di1}:{Di.get_di(ConfigParams.fork_tail_di1)},"
                                            f"DI {ConfigParams.fork_tail_di2}:{Di.get_di(ConfigParams.fork_tail_di2)}",
                                     "", "", "")
                else:
                    Motor.setMotorPosition(self.motor, self.dist, ConfigParams.lift_vel, -1)
            else:
                Motor.setMotorPosition(self.motor, self.dist, ConfigParams.lift_vel, -1)
                robot.state["test"] = "111"
            # if (self.collision is False
            #         and (Motor.isMotorReached(self.motor) or Motor.isMotorPositionReached(self.motor, self.dist, -1)
            #         or (abs(robot.lift_pos - self.dist) <= ConfigParams.lift_precision))):
            if (self.collision is False and
                    (Motor.isMotorReached(self.motor)
                     or abs(robot.lift_pos - self.dist) <= ConfigParams.lift_precision)):
                self.status = ScriptStatus.FINISHED
                Motor.resetMotor(self.motor)
        else:
            if self.resetInit:
                Motor.resetMotor(self.motor)
                self.resetInit = False
            else:
                Motor.setMotorPosition(self.motor, self.initPos, ConfigParams.lift_vel, -1)
                if (Motor.isMotorReached(self.motor) or Motor.isMotorPositionReached(self.motor, self.dist, -1)
                        or (abs(robot.lift_pos - self.dist) <= ConfigParams.lift_precision)):
                    self.status = ScriptStatus.FAILED
                    Abnormal.setTask(53000,
                                     "weight of good is {self.weightResult} kg, "
                                     "Heavier than {ConfigParams.maxWeight} kg",
                                     "", "", "")
                    Motor.resetMotor(self.motor)
        print(f"lift chassis speed:{NavSpeed.get_speeds()}")
        curState = dict()
        curState['liftState'] = self.status
        curState['dist'] = self.dist
        curState['initPos'] = self.initPos
        curState["weightData"] = self.weightData
        curState["weightResult"] = self.weightResult
        # curState["maxWeight"] = ConfigParams.maxWeight
        robot.state['liftOrg'] = curState

    def reset(self, ):
        Motor.resetMotor(self.motor)
        self.status = ScriptStatus.RUNNING

    # def weightGood(self, robot):
    #     fork = Message.get_data(["rbk.protocol.Message_Fork"])
    #     weightTmp = fork["pressure_actual"]
    #     if self.weightGoodFlag:
    #         if self.detectTimes < ConfigParams.maxWeightDetectTimes:
    #             # 延时处理
    #             if Timer.delay(robot.detectPeriodTime):
    #                 self.detectTimes = self.detectTimes + 1
    #                 self.weightData.append(weightTmp)
    #         elif self.detectTimes >= ConfigParams.maxWeightDetectTimes:
    #             self.weightResult = sum(self.weightData) / len(self.weightData)
    #             if self.weightResult >= ConfigParams.maxWeight:
    #                 return True
    #             else:
    #                 self.detectTimes = 0
    #                 self.weightData = []
    #                 Trace.event(f"weight of good is {self.weightResult} kg, lighter than {ConfigParams.maxWeight} kg")
    #                 return False
    #     if Timer.delay(0.1):
    #         self.weightGoodFlag = not self.weightGoodFlag
    #     return False


class rec(BaseAction):
    def __init__(self, filename):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = ActionStatus.NONE
        self.filename = filename
        self.recTimes = 0
        self.maxRecTimes = 10
        self.result = dict()

    def run(self, robot: Robot):
        self.status = ActionStatus.RUNNING
        recStatus = Recognize.getRecStatus()
        log.debug("recStatus: {}".format(recStatus))
        if recStatus == 3:
            self.recTimes = self.recTimes + 1
            if self.recTimes > self.maxRecTimes:
                Abnormal.setTask(53000, "rec_test fail. reach max times {}".format(self.maxRecTimes),
                                 "", "", "")
                self.status = ActionStatus.FAILED
            else:
                Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
                                ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)
        elif recStatus == 0 or recStatus == 1:
            Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
                            ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)
        elif recStatus == 2:
            robot.rec_results = Recognize.getRecResults()
            log.debug("recResult:{}".format(robot.rec_results))
            self.status = ScriptStatus.FINISHED
        curState = dict()
        curState['recResults'] = robot.rec_results
        curState['recState'] = self.status
        curState['recStatus'] = recStatus
        curState['file'] = self.filename
        robot.state['recOrg'] = curState
        log.debug(json.dumps(robot.state))

        return self.status

    def reset(self, ):
        Recognize.resetRec()
        self.status = ActionStatus.RUNNING


class goMapPathDi(BaseAction):
    def __init__(self, check_di=None):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = dict()
        self.status = ActionStatus.NONE
        ConfigParams.check_all_di = False
        self.check_di = check_di
        self.reachDi = []
        self.allDiStatus = []
        self.allDiStatusDict = dict()
        self.backCheckDi = None

    def run(self, robot: Robot):
        self.status = ActionStatus.RUNNING
        if self.init:
            self.init = False
            self.task = Navigation.moveTask()

            if self.check_di is None:
                self.check_di = robot.check_di
            self.reachDi = ConfigParams.multi_reach_di
            self.backCheckDi = backCheckDi(ConfigParams.check_all_di, self.reachDi)
            self.allDiStatus = [False] * len(self.reachDi)
        log.info("goMapPath args {}".format(str(self.task)))
        goMapPathStatus = Navigation.goMapPath()
        if self.check_di:
            if robot.operation == "forkLoad" or robot.operation == "unStack":
                if robot.forkGoodsReach(self.reachDi):
                    Navigation.stopRobot(True)
                    self.status = ActionStatus.FINISHED
                if goMapPathStatus == ActionStatus.FINISHED:
                    if self.reachDi[0] != -1 and not robot.forkGoodsReach(self.reachDi):  # 取货异常
                        self.backCheckDi.run(robot)
                        # Navigation.stopRobot(True)
                        # self.status = ScriptStatus.FAILED
                        # Abnormal.setTask(53000, "已到达目标点，但未触发到位DI",
                        #                              "", "", "")
                    else:
                        self.status = ActionStatus.FINISHED
                elif goMapPathStatus == ActionStatus.FAILED:
                    self.status = ActionStatus.FAILED
            else:
                self.status = goMapPathStatus
        else:
            self.status = goMapPathStatus
        return self.status

    def reset(self):
        log.info("reset goMapPath")
        self.status = ScriptStatus.RUNNING
        Navigation.resetGoMapPath()


class recPallet(BaseAction):
    def __init__(self):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = ScriptStatus.NONE
        self.recFailedTime = 0
        self.maxRecTime = 20
        self.recStatus = 0
        self.recLiftPos = 0
        self.getRecResultId = 1
        self.rec_results = []

    def run(self, robot: Robot):
        self.status = ScriptStatus.RUNNING
        reportInfo = dict()
        if self.init:
            Recognize.resetRec()
            self.init = False
        if robot.operation == "forkLoad" and self.rec(robot):
            if robot.load_all:
                if ConfigParams.minus_result_filter:
                    robot.rec_result = self.filtered_result(robot.rec_results)
                else:
                    robot.rec_result = min(robot.rec_results, key=lambda item: item["z"])  # 获取最底层的识别结果
                if robot.adjust_height:
                    robot.rec_result["z"] = robot.rec_result["z"] + self.recLiftPos - ConfigParams.lift_zero
                    if robot.rec_result["z"] < ConfigParams.lift_zero:
                        robot.load_lift_height = ConfigParams.lift_zero
                    elif ConfigParams.lift_max_height >= robot.rec_result["z"] >= ConfigParams.lift_zero:
                        robot.load_lift_height = robot.rec_result["z"]
                    elif robot.rec_result["z"] > ConfigParams.lift_max_height:
                        Abnormal.setTask(53000, "栈板高度超过货叉最高升降高度",
                                         "", "", "")
                        self.status = ScriptStatus.FAILED
                    if robot.end_height is None:
                        robot.load_lift_up_height = robot.load_lift_height + robot.lift_up_height
                    else:
                        robot.load_lift_up_height = robot.end_height
                    if robot.load_lift_up_height > ConfigParams.lift_max_height:
                        robot.load_lift_up_height = ConfigParams.lift_max_height
                else:
                    robot.load_lift_height = robot.start_height
                    if robot.end_height is None:
                        robot.load_lift_up_height = robot.load_lift_height + robot.lift_up_height
                    else:
                        robot.load_lift_up_height = robot.end_height
                    if robot.load_lift_up_height > ConfigParams.lift_max_height:
                        robot.load_lift_up_height = ConfigParams.lift_max_height
                        # todo
                # if "palletWidth" in robot.rec_result:
                #     targetPalletWidth = robot.rec_result['palletWidth']
                #     dtWidth = abs(targetPalletWidth - robot.rec_params.get('pallet_width', None))
                #     if dtWidth > 0.3 and ConfigParams.pallet_check:
                #         Abnormal.setTask(53000, "实际栈板宽度{targetPalletWidth}，"
                #                                 f"与识别文件中pallet_width{robot.rec_params.get('pallet_width', None)}"
                #                                 f"不一致，请检查！",
                #                          "", "", "")
                #         self.status = ScriptStatus.FAILED
                #         return False
                self.status = ScriptStatus.FINISHED
            else:
                if ConfigParams.pallet_check:
                    # 对数据进行分类
                    classes = self.classifyData(robot.width_data, ConfigParams.classify_rang)
                    # 找到数量超过一半的一类数据的中位数
                    halfCount = math.ceil(len(robot.width_data) / 2)
                    # if len(robot.widthData) <= 3:
                    #     halfCount = 1
                    selectedClass = None
                    for key, values in classes.items():
                        if len(values) >= halfCount:
                            selectedClass = values
                            break
                    # 判断数据数量是否超过正常数量，及栈板宽度是否异常
                    if selectedClass is None:
                        # 没有一类栈板的数量超过所有一半，栈板类型过于混乱，或识别结果异常，视为严重异常
                        if len(robot.width_data) > ConfigParams.pallet_normal_count:
                            reportInfo["palletNum"] = len(robot.width_data)
                            robot.unstack_error_type = 1
                            Module.report_info(reportInfo)
                            Abnormal.setTask(53000, "没有一类栈板的数量超过所有一半，"
                                                    f"且数量超过正常数量 {ConfigParams.pallet_normal_count}，"
                                                    f"实际栈板数量为：{len(robot.width_data)}",
                                             "", "", "")
                            self.status = ScriptStatus.FAILED
                        else:
                            reportInfo["palletNum"] = len(robot.width_data)
                            robot.unstack_error_type = 2
                            Module.report_info(reportInfo)
                            Abnormal.setTask(53000,
                                             f"没有一类栈板的数量超过所有一半，但数量正常，"
                                             f"实际栈板数量为：{len(robot.width_data)}",
                                             "", "", "")
                            self.status = ScriptStatus.FAILED
                    elif selectedClass is not None:
                        widthMedian = self.calculateMedian(self, selectedClass)
                        # 判断原始数据是否为异常数据
                        robot.errors_pallet = [(i + 1, value) for i, value in enumerate(robot.width_data)
                                               if abs(value - widthMedian) > ConfigParams.error_rang]

                        if len(robot.width_data) <= ConfigParams.pallet_normal_count:
                            if robot.errors_pallet:
                                # 栈板数量正常，但有异常栈板
                                reportInfo["palletNum"] = len(robot.width_data)
                                reportInfo["errorsPallet"] = robot.errors_pallet
                                robot.unstack_error_type = 3
                                Module.report_info(reportInfo)
                                Abnormal.setTask(53000, "栈板数量正常 {ConfigParams.pallet_normal_count}，"
                                                        f"实际栈板数量为 {len(robot.width_data)},"
                                                        f"异常栈板数据:{robot.errors_pallet}",
                                                 "", "", "")
                                self.status = ScriptStatus.FAILED
                            else:
                                # 栈板数量正常，且无异常栈板
                                robot.unstack_error_type = 0
                                if ConfigParams.lift_max_height > robot.rec_result["z"] > ConfigParams.lift_zero:
                                    robot.load_lift_height = robot.rec_result["z"]
                                elif robot.rec_result["z"] > ConfigParams.lift_max_height:
                                    Abnormal.setTask(53000, "栈板高度超过货叉最高升降高度",
                                                     "", "", "")
                                    self.status = ScriptStatus.FAILED
                                elif robot.rec_result["z"] < ConfigParams.lift_zero:
                                    robot.load_lift_height = ConfigParams.lift_zero
                                if robot.end_height is None:
                                    robot.load_lift_up_height = robot.load_lift_height + robot.lift_up_height
                                else:
                                    robot.load_lift_up_height = robot.end_height
                                if robot.load_lift_up_height > ConfigParams.lift_max_height:
                                    robot.load_lift_up_height = ConfigParams.lift_max_height
                                self.status = ScriptStatus.FINISHED

                        elif len(robot.width_data) > ConfigParams.pallet_normal_count:
                            if robot.errors_pallet:
                                # 栈板数量超过正常数量
                                reportInfo["palletNum"] = len(robot.width_data)
                                reportInfo["errorsPallet"] = robot.errors_pallet
                                robot.unstack_error_type = 4
                                Module.report_info(reportInfo)
                                Abnormal.setTask(53000, "栈板数量超过正常数量 {ConfigParams.pallet_normal_count}，"
                                                        f"实际栈板数量为 {len(robot.width_data)},"
                                                        f"异常栈板数据:{robot.errors_pallet}",
                                                 "", "", "")
                                self.status = ScriptStatus.FAILED
                            else:
                                # 栈板数量超过正常数量，但宽度没有异常
                                reportInfo["palletNum"] = len(robot.width_data)
                                reportInfo["errorsPallet"] = robot.errors_pallet
                                robot.unstack_error_type = 5
                                Module.report_info(reportInfo)
                                Abnormal.setTask(53000, "栈板数量超过正常数量 {ConfigParams.pallet_normal_count}，"
                                                        f"实际栈板数量为 {len(robot.width_data)},没有异常栈板",
                                                 "", "", "")
                                self.status = ScriptStatus.FAILED
                else:
                    robot.unstack_error_type = 0
                    if ConfigParams.lift_max_height > robot.rec_result["z"] > ConfigParams.lift_zero:
                        robot.load_lift_height = robot.rec_result["z"]
                    elif robot.rec_result["z"] > ConfigParams.lift_max_height:
                        Abnormal.setTask(53000, "栈板高度超过货叉最高升降高度",
                                         "", "", "")
                        self.status = ScriptStatus.FAILED
                    elif robot.rec_result["z"] < ConfigParams.lift_zero:
                        robot.load_lift_height = ConfigParams.lift_zero
                    if robot.end_height is None:
                        robot.load_lift_up_height = robot.load_lift_height + robot.lift_up_height
                    else:
                        robot.load_lift_up_height = robot.end_height
                    if robot.load_lift_up_height > ConfigParams.lift_max_height:
                        robot.load_lift_up_height = ConfigParams.lift_max_height
                    self.status = ScriptStatus.FINISHED
            if self.status == ActionStatus.FINISHED:
                curState = dict()
                data_raw = ScriptData.get("loadLiftHeight")
                end_height_data_time = robot.seqGenerate()
                loadLiftHeight = {
                    "loadLiftHeight": robot.load_lift_height,
                    "end_height_data_time": end_height_data_time
                }
                ScriptData.set("loadLiftHeight", loadLiftHeight)
                data_new = ScriptData.get("loadLiftHeight")
                curState["data_new"] = data_new
                curState["data_raw"] = data_raw
                curState["end_height_data_time"] = end_height_data_time
                robot.state["load_lift_height_data"] = curState
        elif robot.operation == "forkUnload" and self.rec(robot):
            robot.rec_result = robot.rec_results[robot.rec_result_pallet_num - 1]  # 获取第一层的识别结果
            robot.rec_result["z"] = robot.rec_result["z"] + self.recLiftPos - ConfigParams.lift_zero
            robot.unload_lift_height = robot.rec_result["z"] + 0.3
            self.status = ScriptStatus.FINISHED
        elif robot.operation == "stack" and self.rec(robot):
            robot.rec_result = robot.rec_results[robot.unstack_number - 1]  # 获取指定层的识别结果
            robot.rec_result["z"] = robot.rec_result["z"] + self.recLiftPos - ConfigParams.lift_zero
            self.status = ScriptStatus.FINISHED
        elif robot.operation == "recTest" and self.rec(robot):
            self.status = ScriptStatus.FINISHED
        curState = dict()
        recResult_world = []
        curState['recResult'] = robot.rec_result
        curState['recPalletState'] = self.status
        curState['recPos'] = robot.rec_location
        if robot.rec_result:
            recResultPos = [robot.rec_result['x'], robot.rec_result['y'], robot.rec_result['yaw']]
            recResult_world = Pos2World(recResultPos, robot.rec_location)
            dist = math.sqrt(
                (recResult_world[0] - Loc.get_position()[0]) ** 2 + (recResult_world[1] - Loc.get_position()[1]) ** 2)
            curState['dist'] = dist
        curState['recStatus'] = self.recStatus
        curState['file'] = robot.rec_file
        curState['rec_failed_time'] = self.recFailedTime
        robot.state['recPalletOrg'] = curState
        log.debug(json.dumps(robot.state))

        return self.status

    def filtered_result(self, rec_results):
        filtered_result = [result for result in rec_results if result["z"] > 0.00001]
        if not filtered_result:
            return None
        min_z_item = min(filtered_result, key=lambda item: item["z"])  # 返回高度最小值
        return min_z_item

    def rec(self, robot: Robot):
        self.recStatus = Recognize.getRecStatus()
        if self.recStatus == 3:
            self.recFailedTime = self.recFailedTime + 1
            if self.recFailedTime > self.maxRecTime:
                Abnormal.setTask(53000, "rec_test fail. reach max times {}".format(self.maxRecTime),
                                 "", "", "")
                self.status = ScriptStatus.FAILED
                return
            else:
                Recognize.resetRec()
                robot.rec_location = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
                self.recLiftPos = robot.lift_pos
                if robot.target[3] != -1:
                    target2world = [robot.target[0], robot.target[1], robot.target[2]]
                    target2robot = Pos2Base(target2world, robot.rec_location)
                    Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
                                    ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)
                else:
                    Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
                                    ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)
        # elif self.recStatus == 0:
        #     robot.rec_location = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
        #     self.recLiftPos = robot.lift_pos
        #     if robot.target[3] != -1:
        #         target2world = [robot.target[0], robot.target[1], robot.target[2]]
        #         target2robot = Pos2Base(target2world, robot.rec_location)
        #         Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
        #                         ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)
        #     else:
        #         Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
        #                         ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)
        #     self.status = ScriptStatus.RUNNING
        elif self.recStatus == 0 or self.recStatus == 1:
            robot.rec_location = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
            self.recLiftPos = robot.lift_pos
            if robot.target[3] != -1:
                target2world = [robot.target[0], robot.target[1], robot.target[2]]
                target2robot = Pos2Base(target2world, robot.rec_location)
                Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
                                ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)
            else:
                Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
                                ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)
            self.status = ScriptStatus.RUNNING
        elif self.recStatus == 2:
            robot.rec_result_pallet_num = len(Recognize.getRecResults()["reco_list"])
            raw_results = Recognize.getRecResults()["reco_list"]
            # 识别结果排序，按照高度从大到小排列
            robot.rec_results = sorted(raw_results, key=lambda item: item['z'], reverse=True)
            if robot.operation == "forkLoad" and not robot.load_all:
                if robot.unstack_number is None:
                    Abnormal.setTask(53000, "请输入取货数量unStackNum",
                                     "", "", "")
                # 获取指定层的识别结果，从上向下数
                robot.rec_result = robot.rec_results[robot.unstack_number - 1]
                robot.rec_result["z"] = robot.rec_result["z"] + self.recLiftPos - ConfigParams.lift_zero
                # todo
                # while robot.get_rec_result_id < robot.rec_result_pallet_num:
                #     recResultTemp = robot.rec_results[robot.get_rec_result_id]
                #     robot.width_data.append(recResultTemp['palletWidth'])
                #     robot.height_data.append(recResultTemp['z'])
                #     robot.get_rec_result_id = robot.get_rec_result_id + 1
                #     targetPalletWidth = recResultTemp['palletWidth']
                #     dtWidth = abs(targetPalletWidth - robot.rec_params.get('pallet_width', None))
                #     if dtWidth > 0.3 and ConfigParams.pallet_check:
                #         Abnormal.setTask(53000,
                #                          "第 {robot.get_rec_result_id} 层栈板实际宽度为{targetPalletWidth}，"
                #                          f"与识别文件中"
                #                          f"pallet_width{robot.rec_params.get('pallet_width', None)}不一致，请检查！",
                #                          "", "", "")
                #         self.status = ScriptStatus.FAILED
                #         return False
            log.debug("recResult:{}".format(robot.rec_result))
            return True
        if robot.goods_check_enable:
            if Abnormal.exists(54906) and Abnormal.exists(54901):
                Abnormal.setTask(53930, f"栈板货物超限", "", "", "")
                Abnormal.clear(57300)
                self.status = ScriptStatus.FAILED
                self.goodsError = True
                return False
            elif Abnormal.exists(54905) and Abnormal.exists(54901):
                Abnormal.setTask(53931, f"栈板无货物", "", "", "")
                Abnormal.clear(57300)
                self.status = ScriptStatus.FAILED
                self.goodsError = True
                return False

    @staticmethod
    def calculateMedian(self, calData):
        sortedData = sorted(calData)
        n = len(sortedData)
        if n % 2 == 0:
            # 如果数据个数为偶数，取中间两个数的平均值
            middleLeft = sortedData[n // 2 - 1]
            middleRight = sortedData[n // 2]
            widthMedian = (middleLeft + middleRight) / 2
        else:
            # 如果数据个数为奇数，取中间值
            widthMedian = sortedData[n // 2]
        return widthMedian

    @staticmethod
    def classifyData(classifyData, classifyRang):
        classes = defaultdict(list)
        # 对栈板宽度数据进行分类，宽度差值小于classifyRang 被分为一类
        for value in classifyData:
            classified = False
            for key in classes.keys():
                if abs(value - key) < classifyRang:
                    classes[key].append(value)
                    classified = True
                    break
            if not classified:
                classes[value] = [value]
        return classes

    def reset(self):
        log.info("reset findErrorPallet")
        self.status = ScriptStatus.RUNNING
        Recognize.resetRec()


class GoStraight(BaseAction):
    def __init__(self, dist: float, mode: int, direction="x"):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = ScriptStatus.NONE
        self.dist = dist
        self.back_mode = mode
        self.go_path = goPath.GoPath()
        self.move_status = False
        self.direction = direction
        self.mov_args = {}

    def run(self, robot: Robot):
        if self.init:
            Navigation.resetPath()
            self.go_path.reset()
            self.init = False
        self.status = ScriptStatus.RUNNING
        if self.go_path.status == ActionStatus.NONE:
            self.go_path.status = ActionStatus.RUNNING
            if self.direction == "x":
                self.mov_args['coordinate'] = 'robot'
                self.mov_args['y'] = 0
                self.mov_args['theta'] = 0
                self.mov_args['reachAngle'] = 0.005
                self.mov_args['useOdo'] = 0
                self.mov_args['reachDist'] = 0.003
                self.mov_args['maxSpeed'] = ConfigParams.adjust_speed
                self.mov_args["backMode"] = self.back_mode
                if self.back_mode == straightMoveMode.forward:
                    self.mov_args["x"] = self.dist
                if self.back_mode == straightMoveMode.backward:
                    self.mov_args["x"] = -self.dist
            if self.direction == "y":
                self.mov_args['coordinate'] = 'robot'
                self.mov_args['x'] = 0
                self.mov_args['theta'] = 0
                self.mov_args['reachAngle'] = 0.005
                self.mov_args['useOdo'] = 0
                self.mov_args['reachDist'] = 0.003
                self.mov_args['maxSpeed'] = ConfigParams.adjust_speed
                self.mov_args["backMode"] = 0
                self.mov_args['hold_dir'] = (180 / math.pi) * (math.radians(Loc.get_angle()[0]))
                if self.back_mode == straightMoveMode.forward:
                    self.mov_args["y"] = self.dist
                if self.back_mode == straightMoveMode.backward:
                    self.mov_args["y"] = -self.dist

        elif self.go_path.status == ActionStatus.RUNNING:
            self.go_path.run(self.mov_args)
        elif self.go_path.status == ActionStatus.FINISHED:
            self.go_path.reset()
            Navigation.resetPath()
            self.status = ScriptStatus.FINISHED
        elif self.go_path.status == ActionStatus.FAILED:
            Navigation.resetPath()
            self.status = ScriptStatus.FAILED

        return self.status

    def reset(self):
        log.info("reset goStraight")
        self.status = ScriptStatus.RUNNING
        self.go_path.reset()


class adjustGo(BaseAction):
    def __init__(self, omni: bool, coordinate: str, x: float, y: float, angle: float,
                 backDist: float, minAheadDist: float, aheadDist: float, checkAllDi: bool, reachDi: list):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.status = ActionStatus.NONE
        self.goForkPathStatus = ActionStatus.NONE
        self.gopath = goPath.GoPath()
        self.moveArgs = dict()
        self.state = dict()
        self.omni = omni
        self.coordinate = coordinate
        self.beizer = True
        self.x = x
        self.y = y
        self.angle = angle
        self.allDiStatus = None
        self.allDiStatusDict = dict()
        self.backDist = backDist
        ConfigParams.min_ahead_dist = minAheadDist
        self.aheadDist = aheadDist
        self.pos2world = []
        self.pos2robot = []
        self.robot2worldStart = []
        self.loc = dict
        self.dtDist = 0
        self.dtAngle = 0
        self.adjustDist = 0
        self.forwardStatus = False
        self.goForward = False
        self.goForkPathStart = False
        self.adjustStep = [False] * 2
        self.adjustForStr = 0
        ConfigParams.check_all_di = checkAllDi
        self.reachDi = reachDi
        self.check_init = True
        self.target2world = []
        self.fork_holdDir = 0.0

    def run(self, robot: Robot):
        if self.init:
            self.status = ScriptStatus.RUNNING
            self.beizer = ConfigParams.rec_beizer
            self.robot2worldStart = [Loc.get_position()[0], Loc.get_position()[1],
                                     math.radians(Loc.get_angle()[0])]  # 小车在世界坐标系的位置
            if self.coordinate == "world":
                self.pos2world = [self.x, self.y, self.angle]
            elif self.coordinate == "robot":
                if ConfigParams.camera_on_fork:
                    pos2fork = [self.x, self.y, self.angle]  # 识别结果再货叉坐标系的位置
                    pos2robot = Pos2World(pos2fork, ConfigParams.fork2robot)
                    robot.state["pos2robot"] = pos2robot
                    robot.state["pos2fork"] = pos2fork
                    pos2robot_offset = [pos2robot[0] + (ConfigParams.fork2robot[1] * math.sin(pos2fork[2])),
                                        pos2robot[1] - (ConfigParams.fork2robot[1] * math.cos(pos2fork[2])),
                                        pos2robot[2]]  # 识别结果相对里程中心位置 + 叉尖偏移量
                    robot.state["pos2robot_offset"] = pos2robot_offset
                    self.pos2world = Pos2World(pos2robot_offset, self.robot2worldStart)  # 偏移后识别结果在世界坐标系下的位置
                else:
                    pos2robot = [self.x, self.y, self.angle]  # 目标点相对里程中心的位置
                    self.pos2world = Pos2World(pos2robot, self.robot2worldStart)  # 目标点在世界坐标系的位置
            log.info(f"robot2worldStart{self.robot2worldStart}")
            if ConfigParams.min_ahead_dist > 0:
                self.goForward = self.adjustCheck(robot)
            self.gopath.reset()
            self.init = False
        if self.goForward:
            if not self.adjustStep[0]:
                if self.gopath.status == ActionStatus.NONE:
                    self.gopath.status = ActionStatus.RUNNING
                    if (ConfigParams.beizer_dist - self.adjustDist) > ConfigParams.adjust_for_str:
                        Abnormal.setTask(53000,
                                         f"调整距离不足，所需调整距离为{ConfigParams.beizer_dist - self.adjustDist}m, "
                                         f"请在安全的情况下修改 adjust_for_str", "", "", "")
                    else:
                        self.adjustForStr = ConfigParams.beizer_dist - self.adjustDist
                    self.moveArgs['coordinate'] = 'robot'
                    self.moveArgs["x"] = self.adjustForStr
                    self.moveArgs['y'] = 0
                    self.moveArgs['theta'] = 0
                    self.moveArgs['reachAngle'] = math.pi
                    self.moveArgs['useOdo'] = 0
                    self.moveArgs['reachDist'] = 0.003
                    self.moveArgs['maxSpeed'] = 0.3
                    self.moveArgs["backMode"] = 0
                    if self.moveArgs["x"] < 0:
                        self.moveArgs["backMode"] = 1
                elif self.gopath.status == ActionStatus.RUNNING:
                    self.gopath.run(self.moveArgs)
                elif self.gopath.status == ActionStatus.FINISHED:
                    self.gopath.reset()
                    self.adjustStep[0] = True
                elif self.gopath.status == ActionStatus.FAILED:
                    self.status = ScriptStatus.FAILED
            elif self.adjustStep[0] and not self.adjustStep[1]:
                self.robot2worldStart = [Loc.get_position()[0], Loc.get_position()[1],
                                         math.radians(Loc.get_angle()[0])]  # 小车在世界坐标系的位置
                if self.coordinate == "robot":
                    pos2robot = [self.x - self.adjustForStr, self.y, self.angle]  # 目标点相对小车的位置
                    self.pos2world = Pos2World(pos2robot, self.robot2worldStart)  # 目标点在世界坐标系的位置
                Navigation.resetGoForkPath(self.pos2world[0], self.pos2world[1], self.pos2world[2], self.backDist,
                                           ConfigParams.min_ahead_dist, self.aheadDist)
                if self.omni:
                    self.fork_holdDir = math.degrees(self.pos2world[2] - ConfigParams.fork2robot[2])
                    Navigation.setGoForkForkPos(0, 0, ConfigParams.fork2robot[2], self.fork_holdDir)
                if not self.beizer:
                    Navigation.goForkUseStraightLine()
                self.adjustStep[1] = True
                self.goForkPathStart = True
        else:
            if not self.goForkPathStart:
                Navigation.resetGoForkPath(self.pos2world[0], self.pos2world[1], self.pos2world[2], self.backDist,
                                           ConfigParams.min_ahead_dist, self.aheadDist)
                Navigation.setPathReachAngle(0.01)
                Navigation.setPathReachDist(0.005)
                if self.omni:
                    self.fork_holdDir = math.degrees(self.pos2world[2] - ConfigParams.fork2robot[2])
                    Navigation.setGoForkForkPos(0, 0, ConfigParams.fork2robot[2], self.fork_holdDir)
                if not self.beizer:
                    Navigation.goForkUseStraightLine()
                self.goForkPathStart = True
        if self.goForkPathStart:
            self.goForkPathStatus = Navigation.goForkPath()
            if self.goForkPathStatus == ActionStatus.FINISHED and not self.reachCheck(robot):
                self.status = ScriptStatus.FAILED
                Abnormal.setTask(53000, f"任务结束，但未在到点范围内"
                                        f"（{ConfigParams.reach_dist}、{ConfigParams.reach_angle}）! "
                                        f"当前与目标点距离为{self.dtDist}，角度差{self.dtAngle}", "", "", "")
            else:
                self.status = self.goForkPathStatus
            if robot.check_di and self.reachDi[0] != -1 and robot.forkGoodsReach(self.reachDi):
                Navigation.stopRobot(True)
                Navigation.resetPath()
                self.status = ScriptStatus.FINISHED

        curState = dict()
        curState['adjustStep'] = self.adjustStep
        curState['forkGoodsReach'] = robot.forkGoodsReach(self.reachDi)
        curState['allDiStatus'] = self.allDiStatus
        robot.state['adjustGo'] = curState
        log.debug(json.dumps(robot.state))
        return self.status

    def reachCheck(self, robot) -> bool:
        if self.check_init:
            self.check_init = False
            self.pos2robot = Pos2Base(self.pos2world, self.robot2worldStart)  # 初始目标点在小车坐标系的位置
            if ConfigParams.camera_on_fork:
                pos2fork = [self.x, self.y, self.angle]  # 识别结果再货叉坐标系的位置
                pos2robot = Pos2World(pos2fork, ConfigParams.fork2robot)
                pos2robot_offset = [
                    pos2robot[0] + (ConfigParams.fork2robot[1] * math.sin(pos2robot[2] - ConfigParams.fork2robot[2])),
                    pos2robot[1] - (ConfigParams.fork2robot[1] * math.cos(pos2robot[2] - ConfigParams.fork2robot[2])),
                    pos2robot[2]]  # 识别结果相对里程中心位置 + 叉尖偏移量
                pos2world = Pos2World(pos2robot_offset, self.robot2worldStart)  # 偏移后识别结果在世界坐标系下的位置
                self.pos2robot = Pos2Base(pos2world, self.robot2worldStart)  # 目标点相对里程中心位置

            pos2robotNewNewX = self.pos2robot[0] - self.backDist * math.cos(self.pos2robot[2])
            pos2robotNewNewY = self.pos2robot[1] - self.backDist * math.sin(self.pos2robot[2])
            pos2robotNew = [pos2robotNewNewX, pos2robotNewNewY, self.pos2robot[2]]
            self.target2world = Pos2World(pos2robotNew, self.robot2worldStart)  # 增加backDist后的目标点在世界坐标系的位置
        self.dtDist = math.sqrt(
            (self.target2world[0] - Loc.get_position()[0]) ** 2 + (self.target2world[1] - Loc.get_position()[1]) ** 2)
        if ConfigParams.fork_offset_theta == 0:
            self.dtAngle = math.degrees(abs(math.radians(Loc.get_angle()[0]) - self.target2world[2]))
        else:
            self.dtAngle = math.degrees(
                abs(math.radians(Loc.get_angle()[0]) - (self.target2world[2] - ConfigParams.fork2robot[2])))
        if self.dtAngle > 180:
            self.dtAngle = 360 - self.dtAngle
        if self.dtDist < ConfigParams.reach_dist and self.dtAngle < ConfigParams.reach_angle:
            return True
        return False

    def adjustCheck(self, robot) -> bool:
        if self.omni:
            return False
        else:
            self.robot2worldStart = [Loc.get_position()[0], Loc.get_position()[1],
                                     math.radians(Loc.get_angle()[0])]  # 小车在世界坐标系的位置
            pos2robot = Pos2Base(self.pos2world, self.robot2worldStart)  # 初始目标点在小车坐标系的位置
            pos2robotNewX = pos2robot[0] + ConfigParams.min_ahead_dist * math.cos(pos2robot[2])
            pos2robotNewY = pos2robot[1] + ConfigParams.min_ahead_dist * math.sin(pos2robot[2])
            pos2robotNew = [pos2robotNewX, pos2robotNewY, pos2robot[2]]

            target2world = Pos2World(pos2robotNew, self.robot2worldStart)  # 增加minAheadDist后的目标点在小车坐标系的位置
            self.adjustDist = math.sqrt(
                (target2world[0] - Loc.get_position()[0]) ** 2 + (target2world[1] - Loc.get_position()[1]) ** 2)
            # log.info(f"dtDist{self.dtDist},dtAngle{self.dtAngle}")
            if self.adjustDist < ConfigParams.beizer_dist:
                return True
        return False

    def reset(self):
        log.info("reset adjustGo")
        Navigation.resetPath()
        self.status = ScriptStatus.RUNNING
        self.gopath.reset()


class backCheckDi(BaseAction):
    def __init__(self, checkAllDi: bool, reachDi: list):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = ScriptStatus.NONE
        self.goForwardDist = 0
        self.gopath = goPath.GoPath()
        self.moveArgs = dict()
        self.reachDi = reachDi
        ConfigParams.check_all_di = checkAllDi
        self.allDiStatus = [False] * len(reachDi)
        self.allDiStatusDict = dict()

    def run(self, robot: Robot):
        if self.gopath.status == ActionStatus.NONE:
            if Abnormal.exists(55300):
                Abnormal.clear(55300)
            self.gopath.status = ActionStatus.RUNNING
            self.moveArgs['coordinate'] = 'robot'
            self.moveArgs["x"] = -ConfigParams.reach_dist
            self.moveArgs['y'] = 0
            self.moveArgs['theta'] = 0
            self.moveArgs['reachAngle'] = math.pi
            self.moveArgs['useOdo'] = 0
            self.moveArgs['reachDist'] = 0.003
            self.moveArgs['maxSpeed'] = ConfigParams.back_slow_down_vel
            self.moveArgs["backMode"] = 0
            if self.moveArgs["x"] < 0:
                self.moveArgs["backMode"] = 1

        if self.gopath.status == ActionStatus.RUNNING:
            self.gopath.run(self.moveArgs)
            print(f"back speed:{NavSpeed.get_speeds()=}")
        if self.reachDi[0] != -1 and robot.forkGoodsReach(self.reachDi):
            Navigation.stopRobot(True)
            self.gopath.reset()
            Navigation.resetPath()
            print(f"back speed:{NavSpeed.get_speeds()=}")
            self.status = ScriptStatus.FINISHED
        elif self.gopath.status == ActionStatus.FINISHED:
            if self.reachDi[0] != -1 and not robot.forkGoodsReach(self.reachDi):  # 前移取货异常
                Navigation.stopRobot(True)
                self.status = ScriptStatus.FAILED
                Abnormal.setTask(53000, "已到达目标点，但未触发货物到位DI", "", "", "")
            else:
                self.status = ScriptStatus.FINISHED
        elif self.gopath.status == ActionStatus.FAILED:
            self.status = ScriptStatus.FAILED
        return self.status

    def reset(self):
        log.info("reset goForward")
        self.status = ScriptStatus.RUNNING
        self.gopath.reset()


class dirAdjust(BaseAction):
    def __init__(self, angle):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"

        self.init = True
        self.task = None
        self.status = ScriptStatus.NONE
        self.goForwardDist = 0
        self.gopath = goPath.GoPath()
        self.angle = angle
        self.moveArgs = dict()

    def run(self, robot: Robot):
        if self.init:
            self.moveArgs['coordinate'] = 'robot'
            self.moveArgs['x'] = 0
            self.moveArgs['y'] = 0
            self.moveArgs['theta'] = self.angle
            self.moveArgs['reachAngle'] = math.radians(0.1)
            self.moveArgs['useOdo'] = 0
            self.moveArgs['reachDist'] = 0.003
            self.moveArgs['maxSpeed'] = 0.3
            self.moveArgs["backMode"] = 0
        self.status = ScriptStatus.RUNNING
        if self.move(self.moveArgs):
            self.status = ScriptStatus.FINISHED
        return self.status

    def move(self, moveArgs) -> bool:
        if self.gopath.status != 3 or self.gopath.status != 4:
            self.gopath.run(moveArgs)
        if self.gopath.status == ActionStatus.FINISHED:
            self.gopath.reset()
            return True
        return False

    def reset(self):
        log.info("reset dirAdjust")
        self.status = ScriptStatus.RUNNING
        self.gopath.reset()


class GoMapWithFork(BaseAction):
    def __init__(self, liftPos: float, mode=-1):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = ScriptStatus.NONE
        self.liftMotor = ""
        self.liftPos = liftPos
        self.liftVel = 0
        self.finishedMode = mode
        self.goMapStatus = ScriptStatus.NONE

    def run(self, robot: Robot):
        self.status = ScriptStatus.RUNNING
        if self.init:
            self.init = False
            self.liftMotor = ConfigParams.lift_motor
            self.liftVel = ConfigParams.lift_vel
            self.task = Navigation.moveTask()
        if "target_x" in self.task and "target_y" in self.task and self.status != ActionStatus.FINISHED:
            log.info("goMapPath task {}".format(str(self.task)))
            self.goMapStatus = Navigation.goMapPath()
        if self.liftPos >= 0:
            Motor.setMotorPosition(self.liftMotor, self.liftPos, self.liftVel, -1)
        print(f"{self.liftMotor=}")
        print(f"{self.liftPos=}")
        self.finishCheck(robot)

        if self.goMapStatus == ActionStatus.FAILED:
            self.status = ScriptStatus.FAILED

        if self.status == ActionStatus.FINISHED or self.status == ActionStatus.FAILED:
            Navigation.stopRobot(True)
            Motor.resetMotor(self.liftMotor)
            Navigation.resetGoMapPath()
        return self.status

    def finishCheck(self, robot):
        if (self.finishedMode == forkMoveMode.movePriority  # 底盘运动优先模式：底盘到点后立即结束
                and self.goMapStatus == ActionStatus.FINISHED):
            self.status = ScriptStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.liftPriority  # 货叉升降优先模式，升降完成则结束
              and Motor.isMotorReached(self.liftMotor)):
            self.status = ScriptStatus.FINISHED
        # 任意动作完成即结束
        elif (self.finishedMode == forkMoveMode.anyFinished and
              (Motor.isMotorReached(self.liftMotor)
               or self.goMapStatus == ActionStatus.FINISHED)):
            self.status = ScriptStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.allFinished  # 全部完成结束
              and Motor.isMotorReached(self.liftMotor)
              and self.goMapStatus == ActionStatus.FINISHED):

            self.status = ScriptStatus.FINISHED

    def reset(self):
        log.info("reset GoMapWithFork")
        self.status = ScriptStatus.RUNNING
        Motor.resetMotor(self.liftMotor)
        Navigation.resetGoMapPath()


class GoPathWithFork(BaseAction):
    def __init__(self, liftPos: float, mode=-1):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.status = ScriptStatus.NONE
        self.liftMotor = ""
        self.liftPos = liftPos
        self.liftVel = 0
        self.finishedMode = mode
        self.goMapStatus = ScriptStatus.NONE

    def run(self, robot: Robot):
        self.status = ScriptStatus.RUNNING
        if self.init:
            self.init = False
            self.liftMotor = ConfigParams.lift_motor
            self.liftVel = ConfigParams.lift_vel
        if self.liftPos >= 0:
            Motor.setMotorPosition(self.liftMotor, self.liftPos, self.liftVel, -1)

        self.finishCheck(robot)

        if self.status == ActionStatus.FINISHED or self.status == ActionStatus.FAILED:
            Navigation.stopRobot(True)
            Motor.resetMotor(self.liftMotor)
        return self.status

    def finishCheck(self, robot):
        if (self.finishedMode == forkMoveMode.movePriority  # 底盘运动优先模式：底盘到点后立即结束
                and self.goMapStatus == ActionStatus.FINISHED):
            self.status = ScriptStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.liftPriority  # 货叉升降优先模式，升降完成则结束
              and Motor.isMotorReached(self.liftMotor)):
            self.status = ScriptStatus.FINISHED
        # 任意动作完成即结束
        elif (self.finishedMode == forkMoveMode.anyFinished and
              (Motor.isMotorReached(self.liftMotor)
               or self.goMapStatus == ActionStatus.FINISHED)):
            self.status = ScriptStatus.FINISHED
        elif (self.finishedMode == forkMoveMode.allFinished  # 全部完成结束
              and Motor.isMotorReached(self.liftMotor)
              and self.goMapStatus == ActionStatus.FINISHED):
            self.status = ScriptStatus.FINISHED

    def reset(self):
        log.info("reset GoMapWithFork")
        self.status = ScriptStatus.RUNNING
        Motor.resetMotor(self.liftMotor)
        Navigation.resetGoMapPath()


# class weightGood(BaseAction):
#     def __init__(self):
#         super().__init__()
#         kwargs = locals()
#         del kwargs['self']
#         del kwargs['__class__']
#         self.opt_info = f"{__class__.__name__}{kwargs}"
#         self.init = True
#         self.task = None
#         self.status = ScriptStatus.NONE
#         self.state = dict()
#         self.detectTimes = 0
#         self.weightData = []
#         self.weightResult = 0
# 
#     def run(self, robot):
#         self.status = ScriptStatus.RUNNING
#         if self.init:
#             self.init = False
#             Abnormal.clear(57300)
#             Abnormal.clear(53901)
# 
#         fork = r.getMsg("rbk.protocol.Message_Fork")
#         weightTmp = fork["pressure_actual"]
#         if self.detectTimes < ConfigParams.maxWeightDetectTimes:
#             # 延时处理
#             if Timer.delay(robot.detectPeriodTime):
#                 self.detectTimes = self.detectTimes + 1
#                 self.weightData.append(weightTmp)
#         elif self.detectTimes >= ConfigParams.maxWeightDetectTimes:
#             self.weightResult = sum(self.weightData) / len(self.weightData)
#             if self.weightResult >= ConfigParams.maxWeight:
#                 Abnormal.setTask(53000,
#                                  "weight of good is {self.weightResult} kg, Heavier than {ConfigParams.maxWeight} kg")
#                 self.status = ScriptStatus.FAILED
#             else:
#                 Trace.event(f"weight of good is {self.weightResult} kg, lighter than {ConfigParams.maxWeight} kg")
#                 self.status = ScriptStatus.FINISHED
# 
#         curState = dict()
#         curState["weightData"] = self.weightData
#         curState["weightResult"] = self.weightResult
#         curState["maxWeight"] = ConfigParams.maxWeight
#         curState["weightGoodStatus"] = self.status
#         robot.state['weightGoodOrg'] = curState
# 
#         return self.status
# 
#     def reset(self):
#         log.info("reset weightGood")
#         self.status = ScriptStatus.RUNNING
# 

class getMassage(BaseAction):
    def __init__(self, massageName: str):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.status = ScriptStatus.NONE
        self.state = dict()
        self.massageName = massageName
        self.data = dict()

    def run(self, robot):
        self.status = ScriptStatus.RUNNING
        if self.init:
            self.init = False
            Abnormal.clear(57300)
            Abnormal.clear(53901)
        self.data = Message.get_data([self.massageName])

        curState = dict()
        curState["data"] = self.data
        curState["getMassageStatus"] = self.status
        robot.state['getMassageOrg'] = curState

        return self.status

    def reset(self):
        log.info("reset getMassage")
        self.status = ScriptStatus.RUNNING


class locDetectMid(BaseAction):
    def __init__(self, locName: str, recFile: str):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.status = ScriptStatus.NONE
        self.state = dict()
        self.locName = locName
        self.recFile = recFile
        self.target = (0, 0, 0, -1)
        self.detectResult = None
        self.recFailedTime = 0
        self.maxRecTime = 10
        self.recStatus = 0

    def run(self, robot):
        self.status = ScriptStatus.RUNNING
        if self.init:
            self.init = False
            Recognize.resetRec()
            Abnormal.clear(57300)
            self.target = Navigation.getLM(self.locName, True)
        self.recStatus = Recognize.getRecStatus()
        if self.target[3] != -1:
            robot2World = [Loc.get_position()[0], Loc.get_position()[1], math.radians(Loc.get_angle()[0])]
            targetRobot = Pos2Base([self.target[0], self.target[1], self.target[2]], robot2World)
            if self.recStatus == 3:
                self.recFailedTime = self.recFailedTime + 1
                if self.recFailedTime > self.maxRecTime:
                    Trace.event(f"{self.locName} is not filled")
                    self.status = ScriptStatus.FINISHED
                else:
                    Recognize.recTargetObs(ConfigParams.filled_detect_device, targetRobot[0], targetRobot[1],
                                           targetRobot[2], ConfigParams.obs_area_min_height,
                                           ConfigParams.obs_area_max_height, ConfigParams.obs_area_length,
                                           ConfigParams.obs_area_width)
            elif self.recStatus == 0 or self.recStatus == 1:
                Recognize.recTargetObs(ConfigParams.filled_detect_device, targetRobot[0], targetRobot[1],
                                       targetRobot[2], ConfigParams.obs_area_min_height,
                                       ConfigParams.obs_area_max_height, ConfigParams.obs_area_length,
                                       ConfigParams.obs_area_width)
                self.status = ScriptStatus.RUNNING
            elif self.recStatus == 2:
                self.detectResult = Recognize.getRecResults["reco_list"][0]["valid"]
                if self.detectResult:
                    Abnormal.setTask(53000, "{self.loc_name} is filled", "", "", "")
                    self.status = ScriptStatus.FAILED
        else:
            Abnormal.setTask(53000, "{self.loc_name} does not exist", "", "", "")
            self.status = ScriptStatus.FAILED

        curState = dict()
        curState["locName"] = self.locName
        curState["target"] = self.target
        curState["recFile"] = self.recFile
        curState["detectResult"] = self.detectResult
        curState["locDetectMid70Status"] = self.status
        robot.state['locDetectMid70Org'] = curState

        return self.status

    def reset(self):
        log.info("reset locDetectMid")
        self.status = ScriptStatus.RUNNING


class locDetectBackLaser(BaseAction):
    def __init__(self, locName: str):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.status = ScriptStatus.NONE
        self.locName = locName
        self.target = (0, 0, 0, -1)
        self.binDetectResult = None
        self.binDetectMatchCount = 0
        self.detectMatchTime = 0.2
        self.detectTime = 0.5  # 库位检测最长时间，不小于detectMatchTime"
        self.seq = 0
        self.time = time.time()
        self.startTime = 0
        self.locFilled = False

    def run(self, robot):
        self.status = ScriptStatus.RUNNING
        if self.init:
            self.init = False
            Recognize.resetRec()
            Abnormal.clear(57300)
            self.target = Navigation.getLM(self.locName, True)
            self.startTime = time.time()
        if time.time() - self.startTime < self.detectTime:
            if self.target[3] != -1:
                if self.binFilled(self.locName):
                    self.locFilled = True
                    Abnormal.setTask(53000, "loc({self.loc_name}) is filled", "", "", "")
                    self.status = ScriptStatus.FAILED
            else:
                Abnormal.setTask(53000, "{self.loc_name} does not exist", "", "", "")
                self.status = ScriptStatus.FAILED
        else:
            self.status = ScriptStatus.FINISHED

        curState = dict()
        curState["locName"] = self.locName
        curState["target"] = self.target
        curState['seq'] = self.seq
        curState['locFilled'] = self.locFilled
        curState["binDetectResult"] = self.binDetectResult
        curState["locDetectBackLaserStatus"] = self.status
        robot.state['locDetectBackLaserOrg'] = curState

        return self.status

    def binFilled(self, targetLoc) -> bool:
        self.seq = self.seqGenerate()
        Bin.binDetection(self.seq)
        self.binDetectResult = Bin.get_data()
        log.info(f"binDetectResult, {self.binDetectResult}")
        matchingBin = {}
        detectMatchCnt = self.detectMatchTime / 0.02
        if self.binDetectResult["bins"]:
            for binData in self.binDetectResult["bins"]:
                if binData["binId"] == targetLoc:
                    matchingBin = binData
                    break
            if matchingBin:
                # 判断 filled 是否为 True
                if matchingBin["filled"]:
                    self.binDetectMatchCount += 1
                else:
                    self.binDetectMatchCount = 0
            if self.binDetectMatchCount >= detectMatchCnt:
                return True
        return False

    def seqGenerate(self):
        # 获取当前时间
        currentTime = datetime.now()

        # 提取年、月、日、小时、分钟、秒、毫秒
        year = currentTime.year
        month = currentTime.month
        day = currentTime.day
        hour = currentTime.hour
        minute = currentTime.minute
        second = currentTime.second
        millisecond = currentTime.microsecond // 1000  # 将微秒转换为毫秒

        # 将时间信息合并成一个字符串
        # 格式为：年月日时分秒毫秒
        currentTimeSeq = int(f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}{millisecond:03d}")
        return currentTimeSeq

    def reset(self):
        log.info("reset locDetectBackLaser")
        self.status = ScriptStatus.RUNNING


class precisionEvaluate(BaseAction):
    def __init__(self):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.task = None
        self.pos2world = []
        self.status = ScriptStatus.NONE

    def run(self, robot: Robot):
        if self.init:
            self.init = False
            self.status = ScriptStatus.RUNNING
            if robot.rec_result:
                if robot.rec_params['recCoordinate'] == "world":
                    target2world = [robot.rec_result["x"], robot.rec_result["y"], robot.rec_result["yaw"]]
                    robot2world = [robot.rec_location[0], robot.rec_location[1], robot.rec_location[2]]
                    target2Robot = Pos2Base(target2world, robot2world)  # 识别时目标点在小车坐标系的位置
                    robot.rec_result_to_robot["x"] = target2Robot[0]
                    robot.rec_result_to_robot["y"] = target2Robot[1]
                    robot.rec_result_to_robot["yaw"] = target2Robot[2]
                elif robot.rec_params['recCoordinate'] == "robot":  # 识别时目标点在小车坐标系的位置
                    robot.rec_result_to_robot["x"] = robot.rec_result["x"]
                    robot.rec_result_to_robot["y"] = robot.rec_result["y"]
                    robot.rec_result_to_robot["yaw"] = robot.rec_result["yaw"]

        if abs(robot.rec_result_to_robot["y"]) > ConfigParams.dist_precision or abs(
                robot.rec_result_to_robot["yaw"]) > ConfigParams.angle_precision:
            robot.adjust_times = robot.adjust_times + 1
            if robot.adjust_times > ConfigParams.adjust_max_times:
                self.status = ScriptStatus.FAILED
                Abnormal.setTask(53000,
                                 f"识别调整次数{robot.adjust_times}，"
                                 f"但精度[{self.pos2world[1]}] [{self.pos2world[2]}]仍不满足要求",
                                 "", "", "")
            else:
                robot.rec_task_init = True
                robot.rec_task_status = False
                robot.adjust_task1_init = True
                robot.adjust_task1_status = False
                robot.evaluate_task_init = True
                robot.evaluate_task_status = False
                robot.task_id = 0
        else:
            robot.evaluate_task_status = True
            self.status = ScriptStatus.FINISHED
        return self.status

    def reset(self):
        log.info("reset precisionEvaluate")
        self.status = ScriptStatus.RUNNING


class goodsCheck(BaseAction):
    def __init__(self, filename):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_info = f"{__class__.__name__}{kwargs}"
        self.status = ScriptStatus.NONE
        self.filename = filename
        self.recTimes = 0
        self.maxRecTimes = 5
        self.maxExceedTimes = 3
        self.exceedTimes = 0
        self.maxEmptyTimes = 3
        self.emptyTimes = 0
        self.goodsError = False
        self.result = dict()

    def run(self, robot: Robot):
        if self.status == ActionStatus.NONE:
            Recognize.resetRec()
            self.status = ScriptStatus.RUNNING
        curState = dict()
        recStatus = Recognize.getRecStatus()  # 获取识别状态 0: 初始化, 1: 识别中, 2: 获得结果, 3：识别出错, -1: 未知错误
        if recStatus == 2 or recStatus == 3 or recStatus == -1:  # 识别成功或失败
            # Trace.event("rec_test failed:{}".format(self.result))
            if Timer.delay(0.1):
                self.recTimes = self.recTimes + 1
                if Abnormal.exists(54906) and Abnormal.exists(54901):
                    self.exceedTimes = self.exceedTimes + 1
                elif Abnormal.exists(54905) and Abnormal.exists(54901):
                    self.emptyTimes = self.emptyTimes + 1
                if self.exceedTimes > self.maxExceedTimes:
                    Abnormal.setTask(53930, f"栈板货物超限", "", "", "")
                    Abnormal.clear(57300)
                    self.status = ScriptStatus.FAILED
                    self.goodsError = True
                    return
                if self.emptyTimes > self.maxEmptyTimes:
                    Abnormal.setTask(53931, f"栈板无货物", "", "", "")
                    Abnormal.clear(57300)
                    self.status = ScriptStatus.FAILED
                    self.goodsError = True
                    return
                else:
                    Recognize.resetRec()
                if self.recTimes > self.maxRecTimes:
                    self.status = ScriptStatus.FINISHED
                    Trace.event(f"检测完成，货物正常，无超限情况")
        else:
            Trace.event(f"--------------- goodsCheck ----------------")
            Recognize.doRec(robot.rec_file, robot.rec_with_region, ConfigParams.rec_center_x,
                            ConfigParams.rec_center_y, 0, ConfigParams.rec_radius)

        curState['exceedTimes'] = self.exceedTimes
        curState['emptyTimes'] = self.emptyTimes
        curState['recCount'] = self.recTimes
        curState['goodsCheckStatus'] = self.status
        curState['recStatus'] = recStatus
        curState['file'] = self.filename
        curState["status"] = self.status
        curState['goodsError'] = self.goodsError
        robot.state['goodsCheckOrg'] = curState
        log.debug(json.dumps(curState))

    def reset(self, ):
        Recognize.resetRec()
        self.status = ScriptStatus.RUNNING


class forkMoveMode(BaseAction):
    movePriority = 0
    liftPriority = 1
    anyFinished = 2
    allFinished = 3
    Error = -1


class straightMoveMode:
    forward = 0
    backward = 1


class ActionStatus(IntEnum):
    """ 动作运行状态枚举，对标 ActionStatus """
    NONE = 0
    RUNNING = 1
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


def main():
    Module.init()

    validator = ParamValidator(InputParams.builder.to_dict())
    input_params = Module.get_task_args()
    print("task args:", json.dumps(input_params, indent=2))
    validated_params = {}
    try:
        # 验证参数
        validated_params = validator.validate(input_params)
        print("check ok, args:", json.dumps(validated_params, indent=2))
    except ValueError as e:
        Abnormal.setTask(53000, "参数校验失败", "e", "check script args", "")
        print("check error:", e)
        Module.set_status(ScriptStatus.FAILED)
        return

    rob = Robot(validated_params)
    Module.set_suspend_callback(rob.suspend)
    Module.set_resume_callback(rob.resume)
    Module.set_cancel_callback(rob.cancel)

    while True:
        # 脚本任务状态管理
        status = Module.get_status()
        if status is ScriptStatus.RUNNING:
            rob.run(validated_params)
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED, ScriptStatus.NONE):
            Module.set_status(ScriptStatus.NONE)
            return
        # rob.print_info()
        time.sleep(0.1)


if __name__ == '__main__':
    main()
