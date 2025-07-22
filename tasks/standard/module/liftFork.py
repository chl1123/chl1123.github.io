# -*- coding: utf-8 -*-
# Author: zzm
# version: 1.0
# Time: 2025/05/30
# description: CBD15-MF移植

import json
import math
import time
from enum import IntEnum
from syspy.utils.time import Timer
import pprint

start_time = time.time()
from typing import Optional
from syspy import Module, ParamServer, Logger, Di, Do, Motor, Navigation, Loc, Abnormal, Recognize, ScriptStatus, \
    Odometer, Pgv, Laser
from syspy.lib.module import Pos2Base, Pos2World
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ParamServer, BindType
from syspy.lib.robot_param import RobotParam

# import syspy.goPath

log = Logger("jack")

"""

"""


class ConfigParams:
    """生成和定义配置参数的示例"""

    # 从模型文件中获取的参数
    module_type = RobotParam.getDevice("Model-000", "moduleType")
    fork_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.liftMotor")
    motor_func = RobotParam.getDevice(f"{fork_motor_name}", "func")
    min_height = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.minLength")
    max_height = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.maxLength")
    up_di = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.upLimitDI")
    down_di = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.DownLimitDI")
    robot_type = RobotParam.getDevice("Model-000", "getRobotType")

    # 从脚本参数里定义的参数
    param_server = ParamServer(__file__)
    load_whether_recognize = param_server.loadParam(
        "loadWhetherRecognize", type="bool", default=False,
        comment="是否识别取货", group="Recognition")
    load_laser_width = param_server.loadParam(
        "load_laser_width", type="float", default=0.05, maxValue=2, minValue=0,
        comment="进叉时的激光宽度", group="motion")
    back_dist = param_server.loadParam(
        "backDist", type="float", default=1, maxValue=3, minValue=0,
        comment="识别取货的后退距离", group="motion")
    ahead_dist = param_server.loadParam(
        "aheadDist", type="float", default=0.8, maxValue=2, minValue=0,
        comment="识别取货的前置距离", group="motion")  # 前置距离
    min_ahead_dist = param_server.loadParam(
        "minAheadDist", type="float", default=1, maxValue=2, minValue=0,
        comment="识别取货的最小直线距离", group="motion")  # 最小直线距离，叉车起效
    use_straight_line = param_server.loadParam(
        "useStraightLine", type="bool", default=False,
        comment="识别取货的识别调整是否走直线曲线", group="motion")  # 识别调整贝塞尔曲线
    load_adjust_distance = param_server.loadParam(
        "loadAdjustDistance", type="float", default=0.2, maxValue=2, minValue=-2, unit="m",
        comment="识别取货触发货叉开关后不抬升前移一小段", group="motion")
    load_adjust_max_speed = param_server.loadParam("loadAdjustMaxSpeed", type="float", default=0.5, unit="m/s",
                                                   comment="识别取货触发货叉开关后不抬升前移一小段的最大速度",
                                                   group="motion")
    leave_loc = param_server.loadParam("leaveLoc", type="bool", default=True, comment="是否先直线退出", group="motion")

    # min_height = param_server.loadParam(
    #     "min_height", type="float", default="0.085", unit="m",
    #     comment="货叉最小高度", group="module-fork")
    # max_height = param_server.loadParam(
    #     "max_height", type="float", default="0.205", unit="m",
    #     comment="货叉最大高度", group="module-fork")
    # fork_motor_name = param_server.loadParam(
    #     "fork_motor_name", type="str", default="Motor-002",
    #     comment="升降电机名", group="module-fork")
    # up_di = param_server.loadParam(
    #     "upDI", type="int", default=5, maxValue=11, minValue=0,
    #     comment="上到位DI", group="module-fork")
    # down_di = param_server.loadParam(
    #     "down_di", type="int", default=2, maxValue=11, minValue=0,
    #     comment="下到位DI", group="module-fork")
    tail_laser_id_1 = param_server.loadParam(
        "tailLaserId1", type="int", default=3,
        comment="叉尖避障激光 id ,-1代表没有", group="module-fork")
    tail_laser_id_2 = param_server.loadParam(
        "tailLaserId2", type="int", default=4,
        comment="叉尖避障激光 id ,-1代表没有", group="module-fork")
    beck_laser_id = param_server.loadParam(
        "beckLaserId", type="int", default=4,
        comment="后置避障激光的 id ,-1代表没有", group="module-fork")
    contact_di_1 = param_server.loadParam(
        "contactDi1", type="int", default=1,
        comment="货叉的栈板到位 di,-1代表没有 ", group="module-fork")
    contact_di_2 = param_server.loadParam(
        "contactDi2", type="int", default=9,
        comment="货叉的栈板到位 di，-1代表没有 ", group="module-fork")
    laser_width = param_server.loadParam(
        "laserWidth", type="float", default=0.1, maxValue=1, minValue=0,
        comment="线性堆栈激光宽度", group="motion")  # 线性堆栈激光宽度
    obs_dist = param_server.loadParam(
        "obsDist", type="float", default=0.5, maxValue=1, minValue=0,
        comment="线性堆栈的避障距离", group="motion")  # 线性堆栈的避障距离
    load_obs_dist = param_server.loadParam(
        "loadObsDist", type="float", default=0.1, maxValue=11, minValue=0,
        comment="取货进叉时的避障距离", group="motion")  # 取货进叉时的避障距
    obs_area_min_height = param_server.loadParam(
        "obsAreaMinHeight", type="float", default=0.0,
        comment="rec检测区域为长方体，检测区域最低高度", group="Recognition")
    obs_area_max_height = param_server.loadParam(
        "obsAreaMaxHeight", type="float", default=0.0,
        comment="检测区域为长方体，检测区域最高高度", group="Recognition")
    obs_area_length = param_server.loadParam(
        "obsAreaLength", type="float", default=0.0,
        comment="检测区域为长方体，检测区域长度", group="Recognition")
    obs_area_width = param_server.loadParam(
        "obsAreaWidth", type="float", default=0.0,
        comment="检测区域为长方体，检测区域宽度", group="Recognition")
    deviceName = param_server.loadParam(
        "deviceName", type="str", default="",
        comment="检测设备名称", group="Recognition")
    timeout = param_server.loadParam(
        "timeout", type="float", default=120,
        comment="脚本超时时间", group="Recognition")


def create_fork_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    """创建顶升高度参数（可复用）"""
    with builder.CHILD(key="forkHeight", name="Fork Height",
                       desc="The height for lift operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.MIN_VALUE(min_height)
        builder.MAX_VALUE(max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_end_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="endHeight", name="End Height",
                       desc="The fork height after load"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.MIN_VALUE(min_height)
        builder.MAX_VALUE(max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)

def create_start_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="startHeight", name="Start Height",
                       desc="The fork height before load"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.MIN_VALUE(min_height)
        builder.MAX_VALUE(max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.1)
        builder.DEFAULTVALUE(0.1)

def create_rec_param(builder: ParamBuilder):
    # 识别参数
    with builder.CHILD(key="recognize", name="Pallet Identification",
                       desc="Enable pallet recognition"):
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

                with builder.CHILD(key="recfile", name="Recognition File Name",
                                   desc="Recognition file name"):
                    builder.TYPE(ParamType.STRING)
                    builder.DEFAULTVALUE("default.srec")


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    min_height = ConfigParams.min_height
    max_height = ConfigParams.max_height

    with builder.GROUPS():
        # 公共参数:
        # 使用PGV参数
        # with builder.CHILD(key="use_pgv", name="Use PGV", desc="Use PGV for position adjustment"):
        #     builder.TYPE(ParamType.BOOL)
        #     builder.DEFAULTVALUE(False)

        # 操作组合框
        with builder.GROUP(key="operation", name="Operations", desc="Task script input parameters"):
            builder.TYPE(ParamType.COMBO_BOX)

            with builder.CHILDREN():
                # 取货操作
                with builder.CHILD(key="load", name="Load Operation", desc="load the pallet"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 取货路径导航前的货叉高度
                        create_start_height_param(builder, min_height, max_height)

                        # 取完后的货叉高度
                        create_end_height_param(builder, min_height, max_height)

                        # 识别参数
                        create_rec_param(builder)

                # 放货操作
                with builder.CHILD(key="unload", name="Unload Operation",
                                   desc="Lower the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 取货路径导航前的货叉高度
                        create_start_height_param(builder, min_height, max_height)

                        # 取完后的货叉高度
                        create_end_height_param(builder, min_height, max_height)

                # ForkHeight 操作
                with builder.CHILD(key="forkHeight", name="Fork Height",
                                   desc="Lift the fork"):
                    builder.TYPE(ParamType.ARRAY)
                    create_fork_height_param(builder, min_height, max_height)

                # ForkLoad 操作
                with builder.CHILD(key="forkLoad", name="Fork Load",
                                   desc="ForkUp and load goods"):
                    builder.TYPE(ParamType.ARRAY)
                    create_fork_height_param(builder, min_height, max_height)

                # ForkUnload 操作
                with builder.CHILD(key="forkUnload", name="Fork Unload",
                                   desc="ForkDown and unload goods"):
                    builder.TYPE(ParamType.ARRAY)
                    create_fork_height_param(builder, min_height, max_height)

                # 识别操作
                with builder.CHILD(key="rec", name="Rec", desc="Rec the pallet"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILD(key="recfile", name="Recognition File Name",
                                       desc="Recognition file name"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("default.srec")

                # 脱离库位操作
                with builder.CHILD(key="leaveLoc", name="Leave Loc",
                                   desc="Leave loc after load"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        create_end_height_param(builder, min_height, max_height)

                with builder.CHILD(key="test", name="Test",
                                   desc="test"):
                    builder.TYPE(ParamType.ARRAY)
    builder.save_to_file()


class Fork:
    def __init__(self, task_args):
        super().__init__()
        self.rec_params = dict()
        self.start_time = None
        self.init_args = False
        self.action_id = 0
        self.action_list = list()
        self.operation_init = False
        self.script_status = ScriptStatus.NONE
        self.action_status = ActionStatus.INIT
        # 识别相关
        self.rec_result = dict()
        # 定义脚本运行相关的成员变量
        self.opt = ""
        self.hasReachDi = None
        self.fork_cur_height = None
        self.motor_infos = dict()
        self.nav_speed = dict()
        self.is_goods_detected = None
        self.goPathArgs = None  # 堆栈的终点坐标点
        self.tail_laser_id = [ConfigParams.tail_laser_id_1, ConfigParams.tail_laser_id_2]
        self.contact_di = [ConfigParams.contact_di_1, ConfigParams.contact_di_2]
        self.recfile = ""
        self.task_args = task_args
        self.move_task = dict()
        self.first_point = None
        self.second_path = None
        self.first_point_return = None
        self.second_path_return = None
        self.cur_state = {}

    def run(self):
        self.script_status = ScriptStatus.RUNNING

        self._init_args()
        self._check_timeout()
        self._report()

        if self.opt == "load":
            self.load()
        elif self.opt == "unload":
            self.unload()
        elif self.opt == "forkHeight":
            self.fork_height()
        elif self.opt == "forkLoad":
            self.fork_load()
        elif self.opt == "forkUnload":
            self.fork_unload()
        elif self.opt == "rec":
            self.rec()
        elif self.opt == "leaveLoc":
            self.leave_loc()
        elif self.opt == "rec":
            self.test()
        else:
            Abnormal.setTask(53000,f"wrong operation:{self.opt}, script failed","input operation not define","check the input param","")
            self.script_status = ScriptStatus.FAILED

        self._execute_actions()

        # Module.report_info()

    def suspend(self):
        Module.set_status(ScriptStatus.SUSPENDED)
        log.info("suspend")

    def resume(self):
        Module.set_status(ScriptStatus.RUNNING)
        log.info("resume")

    def cancel(self):
        Module.set_status(ScriptStatus.FINISHED)
        self.script_status = ScriptStatus.NONE
        log.info("cancel")

    def get_target_pos(self):
        move_task = Navigation.moveTask()
        # target_id = move_task.get("target_name", "")
        target_id = "AP3"
        return Navigation.getLM(target_id, True)

    def test(self):
        if not self.operation_init:
            self.operation_init = True
            world_pos = self.get_target_pos()
            self.action_list: list[BaseAction] = [
                # RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height),
                # Rec(self.recfile, "RecPallet"),
                # GoPathWithContactDi(self.contact_di, world_pos, 0.05, "goBezier", args),
                RecordBezierPath(world_pos)
            ]
        if self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_name == "RecordBezierPath" and current_action.action_status == ActionStatus.FINISHED:
                self.action_list.append(GoRecordedPath(self.first_point, self.second_path))
                # self.action_list.append(JackHeight(ConfigParams.jack_motor_name, ConfigParams.jack_max_height,
                #                                    ConfigParams.jack_motor_speed, ConfigParams.jack_up_di))
                # self.action_list.append(JackMinHeight(ConfigParams.jack_motor_name, ConfigParams.jack_min_height,
                #                                       ConfigParams.jack_motor_speed, ConfigParams.jack_zero_di))
                self.action_list.append(GoRecordedPathReturn(self.first_point_return, self.second_path_return, False))

    # 识别取货和非识别取货
    def load(self):
        if not self.operation_init:
            self.operation_init = True
            # 如果有货,脚本无法取货并报错
            if Navigation.hasGoods():
                Abnormal.setTask(53900, f"fork has goods, cannot load, script failed",
                                 "fork has goods",
                                 "unload goods before loading", "load")
                self.script_status = ScriptStatus.FAILED
                return
            print(f"recognize：{self.recognize}")

            # 如果需要识别后再取货
            if self.recognize:
                self.action_list: list[BaseAction] = [
                    # RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height),
                    Rec(self.recfile, "RecPallet"),
                ]

            # 不需要根据识别结果通过盲走插货
            else:
                self.action_list = [
                    GoPathWithContactDi([1, 9], self.get_target_pos(), 0.05, "goPath", {"fork_di_dist": 0.2}),
                    # RunMotorByPosition(ConfigParams.fork_motor_name, ConfigParams.max_height)
                ]
        if self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_name == "RecPallet" and current_action.action_status == ActionStatus.FINISHED:
                world_pos = [self.rec_result["x"], self.rec_result["y"], self.rec_result["yaw"]]
                if self.rec_params['recCoordinate'] == "robot":
                    robot_pos = Loc.get_data()
                    world_pos = Pos2World(world_pos, [robot_pos["x"], robot_pos["y"], robot_pos["angle"]])
                args = {
                    "back_dist": ConfigParams.back_dist,
                    "min_ahead_dist": ConfigParams.min_ahead_dist,
                    "adjust_dist": ConfigParams.ahead_dist,
                }
                method = "goBezier"
                # if ConfigParams.use_straight_line:
                #     method = "twoStraightLine"
                #     args["max_angle"] = 10
                # else:
                #     method = "goBezier"
                #     args["max_curve"] = 3
                self.action_list.extend([
                    # RunMotorByPosition(ConfigParams.fork_motor_name, self.rec_result["z"]),
                    GoPathWithContactDi(self.contact_di, world_pos, 0.05, method, args),
                    # RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
                ])

        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED

    def leave_loc(self):
        if not self.operation_init:
            self.operation_init = True

            move_task = Navigation.moveTask()
            target_id = move_task.get("target_name", "")
            target_pos = Navigation.getLM(f"LM{target_id}", True)

            args = {
                'x': target_pos[0],
                'y': target_pos[1],
                'theta': target_pos[2],
                'coordinate': 'world',
                'backMode': 0,
                'maxRot': 10,
                'maxSpeed': 0.2,
                'useOdo': 0
            }
            if ConfigParams.leave_loc:
                go_forward_args = {
                    'x': 1,
                    'y': 0,
                    'theta': 0,
                    'coordinate': 'robot',
                    'backMode': 0,
                    'maxRot': 10,
                    'maxSpeed': 0.2,
                    'useOdo': 0
                }
                self.action_list = [
                    GoPath(go_forward_args),
                    GoPath(args),
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
                ]
            else:
                self.action_list = [
                    GoPath(args),
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
                ]

    def unload(self):
        if not self.operation_init:
            self.operation_init = True
            # if not Navigation.hasGoods():
            #     Abnormal.setTask(53903, f"fork has no goods, cannot unload, script failed", "", "", "unload")
            #     self.script_status = ScriptStatus.FAILED
            #     return
            # target_pos = self.get_target_pos()
            target_pos = Navigation.getLM("LM2", True)
            print(target_pos)
            args = {
                'x': target_pos[0],
                'y': target_pos[1],
                'theta': target_pos[2],
                'coordinate': 'world',
                'backMode': 1,
                'maxRot': 10,
                'maxSpeed': 0.2,
                'useOdo': 0
            }
            self.action_list = [
                RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height),
                GoPath(args),
                RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
            ]

    def get_ap_pos(self):
        org_task = Navigation.moveTask()
        if org_task.get("target_name", ""):
            targetID = "AP" + org_task['target_name']
            targetPos = dict()
            targetPos['x'] = Navigation.getLM(targetID, True)[0]
            targetPos['y'] = Navigation.getLM(targetID, True)[1]
            targetPos['theta'] = Navigation.getLM(targetID, True)[2]
            targetPos['coordinate'] = Coordinate.WORLD
            targetPos['backMode'] = 1
            targetPos['maxRot'] = 0.1
            targetPos['maxSpeed'] = 0.5
            targetPos['useOdo'] = 0
            self.goPathArgs = targetPos

    def _execute_actions(self):
        if self.action_id < len(self.action_list):
            current_action = self.action_list[self.action_id]
            if current_action.action_status == ActionStatus.FINISHED:
                self.action_id += 1
                # print(3)
            elif current_action.action_status == ActionStatus.FAILED:
                Abnormal.setTask(53000, f"execute action {current_action} failed!", "", "", "")
                self.script_status = ActionStatus.FAILED
                return
            elif current_action.action_status == ActionStatus.INIT:
                current_action.reset()
                # print(1)
            else:
                current_action.run(self)
                # print(2)

        else:
            self.action_status = ActionStatus.FINISHED

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.info(f"{Module.get_task_args()=}")
        log.info(f"{Module.get_task_id()=}")
        log.info(f"{Module.get_status()=}")

    def fork_height(self):
        if not self.operation_init:
            self.operation_init = True
            # self.action_list = [RunMotorByPosition(ConfigParams.fork_motor_name, self.fork_height)]
            self.action_list = [RunMotorByPosition("Motor-003", 0,10)]

        # print("action_status:" + json.dumps(cur_status))

    # 获取货叉的高度位置和速度
    def get_fork_mes(self):
        self.motor_infos = Odometer.get_motor_infos()
        for motor_info in self.motor_infos:
            motor_name = motor_info.get('motor_name', "")
            if ConfigParams.fork_motor_name == motor_name:
                self.fork_cur_height = motor_info.get('position', 0)

        self.nav_speed = Odometer.get_speeds()
        temp_navSpeed_list = list(self.nav_speed)  # 将tuple改为list
        temp_navSpeed_list[0] = 0
        temp_navSpeed_list[1] = 0
        temp_navSpeed_list[2] = 0
        self.nav_speed = temp_navSpeed_list

    # 是否有栈板到位 DI
    def is_reach_di(self):
        if ConfigParams.contact_di_1 >= 0 or ConfigParams.contact_di_2 >= 0:
            self.hasReachDi = True
        else:
            self.hasReachDi = False

    def _init_args(self):
        if not self.init_args:
            self.init_args = True
            # 解析任务参数，script_args 里的参数
            self.recfile = self.task_args.get("recfile", "")
            self.opt = self.task_args.get("operation", "")
            self.load_init_height = self.task_args.get("load_init_height", 0.09)
            self.start_height = self.task_args.get("startHeight", 0.09)
            self.end_height = self.task_args.get("endHeight", 0.2)
            self.recognize = self.task_args.get("recognize")
            self.forkHeight = self.task_args.get("forkHeight")

            # 解析识别文件
            RobotParam.getDevice("Recognition", "recognitionObject")

            if self.recfile:
                # 获取识别文件信息
                recFile = json.loads(Recognize.getRecFile(self.recfile))
                # 遍历device_params下的array_param中的params
                for param in recFile.get("device_params", []):
                    if "array_param" in param:
                        for item in param["array_param"].get("params", []):
                            key = item["key"]
                            if "double_value" in item:
                                value = item["double_value"]
                            elif "bool_value" in item:
                                value = item["bool_value"]
                            else:
                                continue
                            # 添加到recParams中
                            self.rec_params[key] = value
                    if param["key"] == "template_type":
                        childKey = param["combo_param"].get("child_key", "")
                        for item in param["combo_param"].get("child_params", []):
                            if item["key"] == childKey:
                                for autoParam in item.get("params", []):
                                    key = autoParam["key"]
                                    if "double_value" in autoParam:
                                        value = autoParam["double_value"]
                                    elif "bool_value" in autoParam:
                                        value = autoParam["bool_value"]
                                    else:
                                        continue
                                    # 添加到recParams中
                                    self.rec_params[key] = value
                # 添加坐标系名称 recCoordinate
                if self.rec_params.get('in_global_framework', None):
                    self.rec_params['recCoordinate'] = "world"
                elif not self.rec_params.get('in_global_framework', None):
                    self.rec_params['recCoordinate'] = "robot"
                if self.rec_params.get('enable_back_dist', None):
                    ConfigParams.back_dist = self.rec_params['back_dist']

            # 解析任务下发的参数，不含在 script_args 里的参数
            self.move_task = Navigation.moveTask()

            self.start_time = time.time()
            self.is_reach_di()
            # self.opt = "rec"
            # Abnormal.setTask(53000, "test", "", "", "")

    def _check_timeout(self):
        self.script_runtime = time.time() - self.start_time
        if self.script_runtime > ConfigParams.timeout:
            self.script_status = ScriptStatus.FAILED
            return

    def _report(self):
        cur_status = dict()
        if self.action_id < len(self.action_list):
            cur_status['action_id'] = self.action_id
            cur_status['action_num'] = len(self.action_list)
            cur_status['action_list'] = [str(action) for action in self.action_list]
            cur_status['action_status'] = self.action_list[self.action_id].action_status
            cur_status['script_status'] = self.script_status
            print(cur_status)

    def fork_load(self):
        if not self.operation_init:
            self.operation_init = True
            self.action_list = [RunMotorByPosition(ConfigParams.fork_motor_name, self.forkHeight)]
        if self.action_status == ActionStatus.FINISHED:
            Navigation.setGoodsShape(0, 0, 0)
            # if ConfigParams.robot_type == "VariableWheelbaseSingleStandardSteer" or ConfigParams.robot_type == "VariableWheelbaseSingleDifferentialSteer":
            status = Navigation.wheelBaseShift(True)
            log.info(f"status:{status}")

            if status:
                print("load")
                self.script_status = ActionStatus.FINISHED

    def fork_unload(self):
        if not self.operation_init:
            self.operation_init = True
            self.action_list = [RunMotorByPosition(ConfigParams.fork_motor_name, 0.085)]
        if self.action_status == ActionStatus.FINISHED:
            Navigation.clearGoodsShape()
            # if ConfigParams.robot_type == "VariableWheelbaseSingleStandardSteer" or ConfigParams.robot_type == "VariableWheelbaseSingleDifferentialSteer":
            status = Navigation.wheelBaseShift(False)
            log.info(f"status:{status}")

            if status:
                print("unload")
                self.script_status = ActionStatus.FINISHED

    def rec(self):
        if not self.operation_init:
            self.operation_init = True
            self.action_list = [Rec(self.recfile)]
        if self.action_status == ActionStatus.FINISHED:
            self.script_status = ActionStatus.FINISHED


class BaseAction:
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        self.action_args = locals()
        self.action_args.pop('self')
        self.action_args.pop('__class__', None)
        self.action_name = action_name or self.__class__.__name__

        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.action_state = {}
        self.init = False

    def run(self, m):
        self.action_state["action_runtime"] = time.time() - self.start_time
        self.action_state["action_args"] = self.action_args
        self.action_state['action_name'] = self.action_name
        pass

    def reset(self):
        pass

    def __str__(self):
        return json.dumps({
            "class_name": self.action_name
        })


# class GoBezier(BaseAction):
#     def __init__(self, goal, back_dist, ahead_dist, min_ahead_dist):
#         super().__init__()
#         self.obs_dist = 0.05
#         self.action_status = ActionStatus.INIT
#         self.goal = goal
#         self.init = False
#         self.back_dist = back_dist
#         self.ahead_dist = ahead_dist
#         self.min_ahead_dist = min_ahead_dist
#         self.start_time = 0.0
#
#     def run(self, f: Fork):
#         if not self.init:
#             self.init = True
#             self.action_status = ActionStatus.RUNNING
#             Navigation.resetGoForkPath(self.goal[0], self.goal[1], self.goal[2], self.back_dist,
#                                        self.min_ahead_dist, self.ahead_dist)
#             if ConfigParams.use_straight_line:
#                 Navigation.goForkUseStraightLine()  # 走折线
#         Navigation.setObsStopDist(self.obs_dist)  # 设置避障距离
#         self.action_status = Navigation.goForkPath()
#         self.action_state['obs dist'] = self.obs_dist
#         self.action_state['task status'] = self.action_status
#
#     def reset(self):
#         self.action_status = ActionStatus.RUNNING
#         self.init = False


# 用于识别栈板并获取识别的栈板坐标，坐标为世界坐标系，且plt文件勾选in global
class Rec(BaseAction):
    def __init__(self, pallet_file, action_name="RecPallet"):
        super().__init__(action_name)
        self.rec_status = None
        self.result = dict()
        self.action_status = ActionStatus.INIT
        self.recfile = pallet_file
        self.attempts = 0
        self.max_attempts = 3
        self.success = False
        self.results = list

    def run(self, f: Fork):
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
            f.rec_result = self.result
            self.action_status = ActionStatus.FINISHED
        self.action_state['recfile'] = self.recfile
        self.action_state['status'] = self.action_status
        self.action_state['rec_status'] = self.rec_status
        self.action_state['rec_times'] = self.attempts
        self.action_state['rec_result'] = self.result
        print(self.action_state)

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
                    Abnormal.setTask(53900,
                                     "Recognition failed, the maximum number of retries exceeded",
                                     "The recognition distance may be too close or too far, or the sensor used for recognition may be faulty",
                                     "Check whether the recognition distance is too close or too far and whether the sensor used for recognition is normal.",
                                     "Recognize the shelf")
                else:
                    Recognize.resetRec()
        else:
            Recognize.doRec(recfile)
            Timer.delay(0.05)
        return False, rec_status, list


class GoPathWithContactDi(BaseAction):
    def __init__(self, contact_dis, world_pos, obs_dist, method, args):
        super().__init__()
        self.di_filter_time = 0.1
        self.check_all_contact_di = False
        self.laser_id = []
        self.check_di = False
        self.laser_width = None
        self.walk_dist = None
        self.di_status = []
        self.contact_di = contact_dis
        if self.contact_di:
            self.check_di = True
        self.goal = [0, 0, 0]
        self.init = False
        self.action_status = ScriptStatus.NONE
        self.obsDist = obs_dist
        self.start_loc = None
        self.method = method

        if method == "goPath":
            target_pos = Pos2World([-args["fork_di_dist"], 0, 0], world_pos)
            self.back_args = {
                'x': target_pos[0],
                'y': target_pos[1],
                'theta': target_pos[2],
                'coordinate': 'world',
                'backMode': 1,
                'maxRot': 10,
                'maxSpeed': 0.15,
                'useOdo': 0
            }
            self.back_action = GoPath(self.back_args)
        elif method == "goBezier":
            self.back_action = GoBezier(world_pos, args["back_dist"], args["adjust_dist"], args["min_ahead_dist"])
        elif method == "twoStraightLine":
            self.back_action = GoTwoStraightLine(world_pos, args["min_ahead_dist"], args["adjust_dist"],
                                                 args["back_dist"], 0.2, 10, 1)
        # self.back_status = self.back_action.action_status

    def run(self, f: Module):
        self.action_status = ScriptStatus.RUNNING
        if not self.init:
            self.init = True
            self.start_loc = Loc.get_position()

        # 开始后退
        if self.back_action.action_status not in [ActionStatus.FAILED, ActionStatus.FINISHED]:
            self.back_action.run(f)

        # 如果没有到位 di
        if not self.check_di:
            self.action_status = self.back_action.action_status
            return

        # 获取到位 di 的状态
        self.di_status = []
        for di in self.contact_di:
            if di > -1:
                self.di_status.append(Di.get_di(di))
        # 如果不需要检查所有的到位 di，一个到位任务结束
        if not self.check_all_contact_di:
            # 检查所有的到位 di ，同时需要考虑到位 di 触发的延时
            if self.back_action.action_status == ActionStatus.FINISHED and not all(self.di_status) and Timer.delay(1):
                Abnormal.setTask(53000, f"not trigger di but robot reach goal",
                                 f"please check the di dist or reach di:{self.contact_di[0]},di:{self.contact_di[1]}")
                self.action_status = ActionStatus.FAILED
                return
            if any(self.di_status):
                Navigation.stopRobot(True)
                self.action_status = ActionStatus.FINISHED
        # 仅检查一个到位 di 的情况
        else:
            if self.back_action.action_status == ActionStatus.FINISHED and not any(self.di_status) and Timer.delay(1):
                Abnormal.setTask(53000, f"not trigger di but robot reach goal",
                                 f"please check the di dist or reach di:{self.contact_di[0]},di:{self.contact_di[1]}")
                self.action_status = ActionStatus.FAILED
                return
            if any(self.di_status):
                di_trigger_time = time.time()
                if all(self.di_status) and (time.time() - di_trigger_time) <= self.di_filter_time:
                    Navigation.stopRobot(True)
                    self.action_status = ActionStatus.FINISHED

        cur_state = dict()
        cur_state['status'] = self.action_status
        cur_state['method'] = self.method
        # cur_state['go path args'] = self.back_args
        cur_state['check_di'] = self.check_di
        cur_state['contact_di'] = self.contact_di
        cur_state['walk_dist'] = self.cal_walk_dist()
        cur_state['di_status'] = self.di_status
        cur_state['obs_dist'] = self.obsDist
        print(cur_state)

    def reset(self):
        self.action_status = ScriptStatus.RUNNING
        self.init = False

    def cal_walk_dist(self):
        cur_loc = Loc.get_position()
        cur_dist = math.sqrt(
            (self.start_loc[0] - cur_loc[0]) ** 2 + (self.start_loc[1] - cur_loc[1]) ** 2)
        return cur_dist


class LocDetectGoods(BaseAction):
    def __init__(self, loc_name: str, rec_file: str):
        super().__init__()
        kwargs = locals()
        del kwargs['self']
        del kwargs['__class__']
        self.opt_Info = f"{__class__.__name__}{kwargs}"
        self.init = True
        self.action_status = ActionStatus.INIT
        self.state = dict()
        self.loc_name = loc_name
        self.rec_file = rec_file
        self.target = [0, 0, 0, -1]
        self.detect_result = None
        self.rec_failed_time = 0
        self.max_rec_time = 10
        self.rec_status = 0

    def run(self, f: Fork):
        self.action_status = ActionStatus.RUNNING
        if self.init:
            self.init = False
            Recognize.resetRec()
            Abnormal.clear(57300)
            self.target = Navigation.getLM(self.loc_name, True)
            # self.target = [-5.67, 9.56, 3.14, 1]
        self.rec_status = Recognize.getRecStatus()
        if self.target[3] != -1:
            if self.rec_status == 3:
                self.rec_failed_time = self.rec_failed_time + 1
                if self.rec_failed_time > self.max_rec_time:
                    Abnormal.setTask(57300, f"{self.loc_name} is not filled", "", "", "LocDetectGoods")
                    f.is_goods_detected = False
                    self.action_status = ActionStatus.FAILED
                else:
                    Recognize.recTargetObs(ConfigParams.deviceName, self.target[0], self.target[1], self.target[2],
                                           ConfigParams.obs_area_min_height, ConfigParams.obs_area_max_height,
                                           ConfigParams.obs_area_length, ConfigParams.obs_area_width)
            elif self.rec_status == 0 or self.rec_status == 1:
                Recognize.recTargetObs(ConfigParams.deviceName, self.target[0], self.target[1], self.target[2],
                                       ConfigParams.obs_area_min_height, ConfigParams.obs_area_max_height,
                                       ConfigParams.obs_area_length, ConfigParams.obs_area_width)
                self.action_status = ActionStatus.RUNNING
            elif self.rec_status == 2:
                self.detect_result = Recognize.getRecResults()
                # r.setError(f"result:{self.detectResult}")
                if self.detect_result:
                    Abnormal.setTask(57300, f"{self.loc_name} is filled", "", "", "LocDetectGoods")
                    f.is_goods_detected = True
                    self.action_status = ActionStatus.FINISHED
        else:
            Abnormal.setTask(53107, f"{self.loc_name} does not exist", "", "", "LocDetectGoods")
            self.action_status = ActionStatus.FAILED

        self.action_state["locName"] = self.loc_name
        self.action_state["target"] = self.target
        self.action_state["recFile"] = self.rec_file
        self.action_state["detectResult"] = self.detect_result
        self.action_state["locDetectMid70Status"] = self.action_status
        self.action_state["recStatus"] = self.rec_status
        self.action_state["recTime"] = self.rec_failed_time

    def reset(self):
        Recognize.resetRec()
        self.action_status = ActionStatus.RUNNING


class RunMotorByPosition(BaseAction):
    """功能说明：控制线性电机运动，发送电机运行终点高度，触发stop_di时终止运动"""

    def __init__(self, motor_name, position, max_speed=0.1, stop_di=-1):
        """
        Args:
            motor_name(string): 电机名
            position(float): 电机运行目标位置
            max_speed(float): 电机运行速度
            stop_di(int): 如果这个StopDI触发则表示运动到位

        使用示例：
        """
        super().__init__()
        self.motor_name = motor_name
        self.position = position
        self.max_speed = max_speed
        self.stop_di = stop_di
        self.init = False
        Motor.resetMotor(self.motor_name)
        print(f"motor name:{self.motor_name}, position:{self.position}, max_speed:{self.max_speed}")

    def run(self, f: Fork):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            Motor.setMotorPosition(self.motor_name, self.position, self.max_speed, self.stop_di)
        if Motor.isMotorReached(self.motor_name):
            self.action_status = ActionStatus.FINISHED

        self.action_state["motor_name"] = self.motor_name
        self.action_state["motor_speed"] = Motor.get_motor_speed(self.motor_name)
        self.action_state["motor_position"] = Motor.get_motor_pos(self.motor_name)
        self.action_state["status"] = self.action_status
        log.info(self.action_state)
        # print(json.dumps(self.action_state))

    def reset(self):
        Motor.resetMotor(self.motor_name)
        self.action_status = ActionStatus.RUNNING


class RunMotorBySpeed(BaseAction):
    def __init__(self, motor_name, max_speed, stop_di=-1):
        """
        控制线性电机运动，发送电机运行速度，直到触发stop_di结束运动
        Args:
            motor_name(string): 电机名
            max_speed(float): 电机运行速度
            stop_di(int): 如果这个StopDI触发则表示运动到位

        """
        super().__init__()
        self.motor_name = motor_name
        self.max_speed = max_speed
        self.stop_di = stop_di
        self.init = False
        Motor.resetMotor(self.motor_name)

    def run(self, f: Fork):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            Motor.setMotorSpeed(self.motor_name, self.max_speed, self.stop_di)
        if Motor.isMotorReached(self.motor_name):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.INIT
        Motor.resetMotor(self.motor_name)

    def __str__(self):
        self.action_state["motor_name"] = self.motor_name
        self.action_state["speed"] = Motor.get_motor_speed(self.motor_name)
        self.action_state["stopDI"] = self.stop_di
        self.action_state["status"] = self.action_status
        return json.dumps(self.action_state)


class RunMotorByDOInterlock(BaseAction):
    """
    功能说明：控制DO电机运动，采用interlock方式，up_di/down_di触发时结束运动,超过延时时间自动停止
    """

    def __init__(self, operation, positive_do, negative_do, up_di, down_di, up_delay_time=5.0, down_delay_time=5.0):
        super().__init__()
        """
            Args:
                operation(string): "up" or "down" 选择上升或者下降
                positive_do(int): 泵电机DO,正向DO,不能和negative_do同时打开
                negative_do(int): 泄漏阀DO,负向DO,不能和positive_do同时打开
                up_di(int): 抬升到位 DI。货叉举升过程中，该 DI 触发可以结束货叉举升过程。
                down_di(int): 下降到位 DI。货叉下降过程中，该 DI 触发可以结束货叉下降过程。
                up_delay_time(float): 上升延时时间。货叉举升过程中，此参数用来限制货叉上升的最大时间，若超过此延时时间举升未到位，举升动作也会停止。
                down_delay_time(float): 下降延时时间。货叉下降过程中，此参数用来限制货叉下降的最大时间，若超过此延时时间下降未到位，下降动作也会停止。

        """
        self.operation = operation  # 如果是 up 上升，如果是 down 下降
        self.init = False
        self.positive_do = positive_do
        self.negative_do = negative_do
        self.up_di = up_di
        self.down_di = down_di
        self.up_delay_time = up_delay_time
        self.down_delay_time = down_delay_time
        self.start_time = 0
        self.action_state = dict()

    def run(self, f: Fork):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            self.start_time = time.time()
            self.reset()

        if self.operation == "up":
            if not Do.get_do(self.positive_do):
                Do.setDO(self.positive_do, True)
                Do.setDO(self.negative_do, False)
        elif self.operation == "down":
            if not Do.get_do(self.negative_do):
                Do.setDO(self.positive_do, False)
                Do.setDO(self.negative_do, True)

        if self.is_reached():
            Do.setDO(self.positive_do, False)
            Do.setDO(self.negative_do, False)
            self.action_status = ActionStatus.FINISHED

        self.action_state['action_name'] = self.__class__.__name__
        self.action_state["action_runtime"] = time.time() - self.start_time
        self.action_state["up_or_down_operation"] = self.operation
        self.action_state["positive_do"] = self.positive_do
        self.action_state["negative_do"] = self.negative_do
        self.action_state["up_di"] = self.up_di
        self.action_state['down_di'] = self.down_di
        self.action_state['status'] = self.action_status

    def is_reached(self):
        is_reach = False
        if self.operation == "up":
            up_di_status = Di.get_di(self.up_di)
            if up_di_status:
                is_reach = True
            if time.time() - self.start_time > self.up_delay_time:
                is_reach = True
                Abnormal.setTask(55900,
                                 "Motor up timeout",
                                 "",
                                 "",
                                 "RunMotorByDOInterlock")
        elif self.operation == "down":
            down_di_status = Di.get_di(self.down_di)
            if down_di_status:
                is_reach = True
            if time.time() - self.start_time > self.down_delay_time:
                is_reach = True
                Abnormal.setTask(55900,
                                 "Motor down timeout",
                                 "",
                                 "",
                                 "RunMotorByDOInterlock")
        return is_reach

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        Do.setDO(self.positive_do, False)
        Do.setDO(self.negative_do, False)


class RunMotorByDOEnable(BaseAction):
    """
    功能说明：控制DO电机运动，采用reverseAndEnable方式，up_di/down_di触发时结束运动，超过延时时间自动停止
    """

    def __init__(self, operation, reverse_do, enable_do, up_di, down_di, up_delay_time=5.0, down_delay_time=5.0):
        super().__init__()
        """
        Args:
            operation(string): "up" or "down" 选择上升或者下降
            reverse_do(int): 反转do，启用时电机运动方向改变
            enable_do(int): 使能do，启用时电机运动
            up_di(int): 抬升到位 DI。货叉举升过程中，该 DI 触发可以结束货叉举升过程。
            down_di(int): 下降到位 DI。货叉下降过程中，该 DI 触发可以结束货叉下降过程。
            up_delay_time(float): 上升延时时间。货叉举升过程中，此参数用来限制货叉上升的最大时间，若超过此延时时间举升未到位，举升动作也会停止。
            down_delay_time(float): 下降延时时间。货叉下降过程中，此参数用来限制货叉下降的最大时间，若超过此延时时间下降未到位，下降动作也会停止。

        """
        self.operation = operation
        self.init = False
        self.reverse_do = reverse_do
        self.enable_do = enable_do
        self.up_di = up_di
        self.down_di = down_di
        self.up_delay_time = up_delay_time
        self.down_delay_time = down_delay_time
        self.start_time = 0

    def run(self, f: Fork):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            self.start_time = time.time()
            self.reset()
        if self.operation == "up":
            if not Do.get_do(self.enable_do):
                Do.setDO(self.enable_do, True)
            Do.setDO(self.reverse_do, False)
        elif self.operation == "down":
            if not Do.get_do(self.enable_do):
                Do.setDO(self.enable_do, True)
            Do.setDO(self.reverse_do, True)
        if self.is_reached():
            Do.setDO(self.enable_do, False)
            self.action_status = ActionStatus.FINISHED

        self.action_state["Up_or_Down_operation"] = self.operation
        self.action_state["enable_do"] = self.enable_do
        self.action_state["reverse_do"] = self.reverse_do
        self.action_state["up_di"] = self.up_di
        self.action_state['down_di'] = self.down_di
        self.action_state['status'] = self.action_status

    def is_reached(self):
        is_reach = False
        if self.operation == "up":
            up_di_status = Di.get_di(self.up_di)
            if up_di_status:
                is_reach = True
            if time.time() - self.start_time > self.up_delay_time:
                is_reach = True
                Abnormal.setTask(55900, "Motor up timeout", "", "", "RunMotorByDOEnable")
        elif self.operation == "down":
            down_di_status = Di.get_di(self.down_di)
            if down_di_status:
                is_reach = True
            if time.time() - self.start_time > self.down_delay_time:
                is_reach = True
                Abnormal.setTask(55900, "Motor down timeout", "", "", "RunMotorByDOEnable")
        return is_reach

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        Do.setDO(self.enable_do, False)
        Do.setDO(self.reverse_do, False)


# 用于走直线
class GoPath(BaseAction):
    def __init__(self, args: Optional[dict] = None):
        super().__init__()
        self.goal = [0, 0, 0]
        self.init = False
        self.action_status = ActionStatus.INIT
        self.param = {}
        self.args = args if args else {}
        """ eg.
        args = {"x":0,
                "y":0,
                "coordinate":0,
                "reachAngle":0,
                "reachDist":0
                }
        """
        print(f"go path init")

    def run(self, f: Fork):
        self.action_status = ActionStatus.RUNNING
        args = self.args
        if args is None:
            args = Module.get_task_args()
        if Abnormal.exists(52111):
            self.action_status = ActionStatus.FAILED
        print(f"go args:{args}")

        if not self.init:
            self.init = True
            Navigation.resetPath()
            if "x" in args and "y" in args and "coordinate" in args:
                if "x" in args:
                    self.goal[0] = float(args["x"])
                if "y" in args:
                    self.goal[1] = float(args["y"])
                if "theta" in args:
                    self.goal[2] = float(args["theta"])
                    if "reachAngle" in args:
                        Navigation.setPathReachAngle(float(args["reachAngle"]))
                else:
                    Navigation.setPathReachAngle(math.pi)
                if "reachAngle" in args:
                    Navigation.setPathReachAngle(float(args["reachAngle"]))
                if "reachDist" in args:
                    Navigation.setPathReachDist(float(args["reachDist"]))
                if "useOdo" in args:
                    Navigation.setPathUseOdo(bool(int(args["useOdo"])))
                if "backMode" in args:
                    Navigation.setPathBackMode(bool(int(args["backMode"])))
                if "maxSpeed" in args:
                    Navigation.setPathMaxSpeed(float(args["maxSpeed"]))
                if "maxRot" in args:
                    Navigation.setPathMaxRot(float(args["maxRot"]))
                if "hold_dir" in args:
                    Navigation.setPathHoldDir(float(args["hold_dir"]))
                if "maxAcc" in args:
                    self.param["maxAcc"] = float(args["maxAcc"])
                if "maxDec" in args:
                    self.param["maxDec"] = float(args["maxDec"])
                if "maxRotAcc" in args:
                    self.param["maxRotAcc"] = float(args["maxRotAcc"])
                if "maxRotDec" in args:
                    self.param["maxRotDec"] = float(args["maxRotDec"])
                log.info("goal: %s", str(self.goal))
                if args["coordinate"] == "robot":
                    angle, __, __ = Loc.get_angle()
                    goal_theta_of_robot = angle + self.goal[2]
                    Navigation.setPathOnRobot([0, self.goal[0]], [0, self.goal[1]], goal_theta_of_robot)
                elif args["coordinate"] == "world":
                    x, y, __ = Loc.get_position()
                    Navigation.setPathOnWorld([x, self.goal[0]], [y, self.goal[1]], self.goal[2])
                    Navigation.goPathParam(self.param)
                else:
                    Abnormal.setTask(55900,
                                     f"coordinate wrong",
                                     f"coordinate only support robot and world. Input is {args['coordinate']}",
                                     "coordinate Input 'robot' or 'world'",
                                     "GoPath")
                    self.action_status = ActionStatus.FAILED
            else:
                Abnormal.setTask(55900,
                                 f"args wrong",
                                 f"no x or y or coordinate",
                                 "input 'x' , 'y' and 'coordinate'",
                                 "GoPath")
                self.action_status = ActionStatus.FAILED

        if self.action_status != ActionStatus.FAILED:
            if Navigation.isPathReached():
                self.action_status = ActionStatus.FINISHED
            else:
                self.action_status = ActionStatus.RUNNING

        self.action_state['status'] = self.action_status

    def reset(self):
        Navigation.resetPath()
        self.action_status = ActionStatus.RUNNING
        self.init = False


class GoBezier(BaseAction):
    """
        走二阶贝塞尔
    """

    def __init__(self, target_world, back_dist=0, adjust_dist_for_curvature_limit=2, min_ahead_dist=0,
                 is_backwards=True,
                 max_speed=0.2, max_accele=0.3, max_decele=0.3, decele_dist=1, curvature_limit=1):
        super().__init__("GoBezier")
        self.dec_dist_speed = 0.1
        del target_world[3:]
        self.target_world = target_world
        self.target_world[2] = (self.target_world[2] + math.pi) % (2 * math.pi)

        log.info(f"target_world={target_world}")
        self.back_dist = back_dist
        self.end_position_world = [0, 0, 0]
        self.end_position_robot = [0, 0, 0]
        self.min_ahead_dist = min_ahead_dist
        self.adjust_dist_for_curvature_limit = adjust_dist_for_curvature_limit

        self.is_backwards = is_backwards
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist
        self.curvature_limit = curvature_limit

        self.action_status = ActionStatus.INIT
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        self.go_path = GoPath()
        # 第一段线到位标识
        self.is_first_path_reached = False
        self.xs = []
        self.ys = []
        self.offset_dist = 0.0
        self.k_max = 0  # 定义曲率
        self.first_point = None

    def run(self, f: Module):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            self.init = False

            # 获取机器人位置（world系）
            loc_data = Loc.get_data()
            robot_loc = [loc_data["x"], loc_data["y"], loc_data["angle"]]

            # 计算终点
            self.end_position_world = Pos2World([self.back_dist, 0, 0], self.target_world)
            self.target_world = Pos2World([-self.min_ahead_dist, 0, 0], self.target_world)

            # 贝塞尔曲线终点 → robot坐标系
            self.target_robot = Pos2Base(self.target_world, robot_loc)
            self.end_position_robot = Pos2Base(self.end_position_world, robot_loc)

            success = False
            max_offset = self.adjust_dist_for_curvature_limit
            offset_step = 0.1
            alpha = 0.35  # 固定控制点比例
            P0_xy = P1 = P2 = P3_xy = [0, 0, 0]

            while self.offset_dist <= max_offset:
                # 起点从(0, 0)往后移，作为新的P0
                if self.is_backwards:
                    P0 = [self.offset_dist, 0, math.pi]
                else:
                    P0 = [-self.offset_dist, 0, 0]
                # P0 = [self.offset_dist, 0, math.pi]
                P3 = self.target_robot

                # 生成贝塞尔曲线控制点与路径
                P0_xy, P1, P2, P3_xy = self.compute_bezier_controls_dir(P0, P3, alpha)
                self.xs, self.ys = self.bezier_points(P0_xy, P1, P2, P3_xy)
                log.info(f"xs={self.xs}, ys={self.ys}")

                # 添加末端直线路径
                self.xs.append(self.end_position_robot[0])
                self.ys.append(self.end_position_robot[1])

                # 判断曲率是否超限
                # self.k_max = self.max_curvature(self.xs, self.ys)
                self.k_max = self.bezier_curvature(P0_xy, P1, P2, P3_xy)
                if self.k_max <= self.curvature_limit:
                    success = True
                    break

                self.offset_dist += offset_step
            print(f"offset_dist:{self.offset_dist}")
            self.first_point = [self.xs[0], self.ys[0]]

            if not success:
                log.info(f"curvature limit exceeded. max_curvature={self.k_max}")
                self.action_status = ActionStatus.FAILED
                return

            # 成功构造路径,需要将路径分为2段，第一段后退至贝塞尔起始点
            self.control_point = [P0_xy, P1, P2, P3_xy]
            # 规划第一段倒退路线参数
            Navigation.setPathReachAngle(0.05)  # 到位精度
            Navigation.setPathReachDist(0.01)
            Navigation.setPathBackMode(not self.is_backwards)  # 设置正走倒走
            Navigation.setPathMaxSpeed(self.max_speed)
            Navigation.setPathOnRobot([0, self.xs[0]], [0, self.ys[0]], 0)
            self.param["maxAcc"] = float(self.max_accele)
            self.param["maxDec"] = float(self.max_decele)
            Navigation.goPathParam(self.param)

        if not self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走第一段路线到曲率合适的贝塞尔起点
            # Navigation.goPathParam(self.param)
            self.is_first_path_reached = Navigation.isPathReached()
            log.info(f"is_first_path_reached:{self.is_first_path_reached}")
            if self.is_first_path_reached:
                Navigation.resetPath()
                if self.is_backwards:
                    for i in range(len(self.xs)):
                        self.xs[i] -= self.offset_dist
                else:
                    for i in range(len(self.xs)):
                        self.xs[i] += self.offset_dist

                Navigation.setPathReachAngle(0.05)
                Navigation.setPathReachDist(0.01)
                Navigation.setPathBackMode(self.is_backwards)
                Navigation.setPathMaxSpeed(self.max_speed)

                end_angle_robot = self.end_position_robot[2]
                if self.is_backwards:
                    end_angle_robot = (end_angle_robot + math.pi) % (2 * math.pi)
                    if end_angle_robot > math.pi:
                        end_angle_robot -= 2 * math.pi

                Navigation.setPathOnRobot(self.xs, self.ys, end_angle_robot)
                self.param["maxAcc"] = float(self.max_accele)
                self.param["maxDec"] = float(self.max_decele)
                Navigation.goPathParam(self.param)

        if self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走贝塞尔到终点
            # Navigation.goPathParam(self.param)
            is_reached = Navigation.isPathReached()
            log.info(f"is_reached:{is_reached}")
            if is_reached:
                self.action_status = ActionStatus.FINISHED
                return
            else:
                self.action_status = ActionStatus.RUNNING

            robot_current_loc = list(Loc.get_position())
            dist_cur_loc_end_loc = math.hypot(
                self.end_position_world[0] - robot_current_loc[0],
                self.end_position_world[1] - robot_current_loc[1]
            )
            if dist_cur_loc_end_loc < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(self.dec_dist_speed)
                # Abnormal.setTask(55900, "has slow the speed", "", "", "")

        robot_loc = [Loc.get_position()[0], Loc.get_position()[1], Loc.get_angle()[0]]
        curstate = {
            "action_status": self.action_status,
            "k_max": self.k_max,
            "first_point": self.first_point,
            "xEnd,yEnd": [self.xs[-1], self.ys[-1]],
            "target_pos_world": [self.end_position_world[0], self.end_position_world[1]],
            "max_speed": self.max_speed,
            "max_accele": self.max_accele,
            "robot_loc": robot_loc
        }
        Module.report_info(curstate)

    def reset(self):
        self.action_status = ActionStatus.RUNNING

    def compute_bezier_controls_dir(self, p0, p3, alpha=0.3):
        """
        计算三次 Bezier 的 4 个控制点（含端点），支持端点方向。
        参数
        ----
        p0, p3 : [x, y, theta]   theta 为弧度，表示该点切线方向
        alpha  : 0~1，控制 P1/P2 到端点的相对距离 (d = alpha * |P3-P0|)

        返回
        ----
        [P0_xy, P1, P2, P3_xy]   仅保留 (x, y)
        """
        x0, y0, th0 = p0
        x3, y3, th3 = p3

        # 端点间直线距离
        dist = math.hypot(x3 - x0, y3 - y0)
        d = alpha * dist  # 控制点到端点的绝对距离

        # 控制点
        p1 = [x0 + d * math.cos(th0), y0 + d * math.sin(th0)]
        p2 = [x3 - d * math.cos(th3), y3 - d * math.sin(th3)]

        return [p0, p1, p2, p3]  # 去掉角度，只留坐标

    def bezier_points(self, p0, p1, p2, p3, steps=100):
        """
        生成 Bezier 曲线采样点
        ----
        p0~p3 : [x, y]
        steps : 采样分段数，返回 steps+1 个点
        返回
        ----
        (xs, ys) : 两个长度相等的列表
        """
        xs, ys = [], []
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 三次 Bezier 伯恩斯坦基函数
            b0 = one_t ** 3
            b1 = 3 * one_t ** 2 * t
            b2 = 3 * one_t * t ** 2
            b3 = t ** 3

            x = (b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0])
            y = (b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1])
            xs.append(x)
            ys.append(y)
        return xs, ys

    def max_curvature(self, xs, ys):
        """
            计算bezier曲线的最大曲率
            ----
            (xs, ys) : 途径的每个离散点
        """
        k_max = 0.0
        for i in range(1, len(xs) - 1):
            x1, y1 = xs[i - 1], ys[i - 1]
            x2, y2 = xs[i], ys[i]
            x3, y3 = xs[i + 1], ys[i + 1]

            # 三角形边长
            a = math.hypot(x2 - x1, y2 - y1)
            b = math.hypot(x3 - x2, y3 - y2)
            c = math.hypot(x3 - x1, y3 - y1)
            if a * b * c == 0:
                continue

            # 海伦公式求面积，再转曲率
            s = 0.5 * (a + b + c)
            area_sq = max(s * (s - a) * (s - b) * (s - c), 0)
            if area_sq == 0:
                continue
            k = 4.0 * math.sqrt(area_sq) / (a * b * c)
            k_max = max(k_max, k)
        return k_max

    def bezier_curvature(self, p0, p1, p2, p3, steps=500):
        """
        基于导数计算三次贝塞尔曲线最大曲率
        p0~p3: 控制点[x, y]
        返回最大曲率
        比上面的方法更准确
        """
        k_max = 0.0
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 一阶导数
            dx_dt = 3 * one_t ** 2 * (p1[0] - p0[0]) + \
                    6 * one_t * t * (p2[0] - p1[0]) + \
                    3 * t ** 2 * (p3[0] - p2[0])
            dy_dt = 3 * one_t ** 2 * (p1[1] - p0[1]) + \
                    6 * one_t * t * (p2[1] - p1[1]) + \
                    3 * t ** 2 * (p3[1] - p2[1])

            # 二阶导数
            ddx_dt = 6 * one_t * (p2[0] - 2 * p1[0] + p0[0]) + \
                     6 * t * (p3[0] - 2 * p2[0] + p1[0])
            ddy_dt = 6 * one_t * (p2[1] - 2 * p1[1] + p0[1]) + \
                     6 * t * (p3[1] - 2 * p2[1] + p1[1])

            # 曲率公式
            numerator = abs(dx_dt * ddy_dt - dy_dt * ddx_dt)
            denominator = (dx_dt ** 2 + dy_dt ** 2) ** 1.5
            if denominator == 0:
                continue
            k = numerator / denominator
            k_max = max(k_max, k)
        return k_max


class RecordBezierPath(BaseAction):
    """
        走二阶贝塞尔
    """

    def __init__(self, target_world, back_dist=0, adjust_dist_for_curvature_limit=1, min_ahead_dist=0.5,
                 is_backwards=True, curvature_limit=1.5):
        super().__init__("RecordBezierPath")
        del target_world[3:]
        self.target_world = target_world
        self.target_world[2] = (self.target_world[2] + math.pi) % (2 * math.pi)
        log.info(f"target_world={target_world}")
        self.back_dist = back_dist
        self.end_position_world = [0, 0, 0]
        self.end_position_robot = [0, 0, 0]
        self.end_angle_robot = None

        self.min_ahead_dist = min_ahead_dist
        self.adjust_dist_for_curvature_limit = adjust_dist_for_curvature_limit

        self.is_backwards = is_backwards
        self.curvature_limit = curvature_limit

        self.action_status = ActionStatus.INIT
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        # self.go_path = GoPath()
        # 第一段线到位标识
        self.is_first_path_reached = False
        self.xs = []
        self.ys = []
        self.xs_ret = []
        self.ys_ret = []
        self.theta_ret = None
        self.offset_dist = 0.0
        self.k_max = 0  # 定义曲率
        self.first_point = []
        self.first_point_return = []
        self.second_path = []
        self.second_path_return = []

    def run(self, f: Fork):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            self.init = False

            # 获取机器人位置（world系）
            loc_data = Loc.get_data()
            robot_loc = [loc_data["x"], loc_data["y"], loc_data["angle"]]

            # 计算终点
            self.end_position_world = Pos2World([self.back_dist, 0, 0], self.target_world)
            self.target_world = Pos2World([-self.min_ahead_dist, 0, 0], self.target_world)

            # 贝塞尔曲线终点 → robot坐标系
            self.target_robot = Pos2Base(self.target_world, robot_loc)
            self.end_position_robot = Pos2Base(self.end_position_world, robot_loc)

            success = False
            max_offset = self.adjust_dist_for_curvature_limit
            offset_step = 0.1
            alpha = 0.35  # 固定控制点比例
            P0_xy = P1 = P2 = P3_xy = [0, 0, 0]

            while self.offset_dist <= max_offset:
                # 起点从(0, 0)往后移，作为新的P0
                if self.is_backwards:
                    P0 = [self.offset_dist, 0, math.pi]
                else:
                    P0 = [-self.offset_dist, 0, 0]
                # P0 = [self.offset_dist, 0, 0]
                P3 = self.target_robot

                # 生成贝塞尔曲线控制点与路径
                P0_xy, P1, P2, P3_xy = self.compute_bezier_controls_dir(P0, P3, alpha)
                self.xs, self.ys = self.bezier_points(P0_xy, P1, P2, P3_xy)
                # log.info(f"xs={self.xs}, ys={self.ys}")

                # 添加末端直线路径
                self.xs.append(self.end_position_robot[0])
                self.ys.append(self.end_position_robot[1])

                # 判断曲率是否超限
                # self.k_max = self.max_curvature(self.xs, self.ys) #海伦公式
                self.k_max = self.bezier_curvature(P0_xy, P1, P2, P3_xy)  # 二阶导
                if self.k_max <= self.curvature_limit:
                    success = True
                    break

                self.offset_dist += offset_step

            if not success:
                log.info(f"curvature limit exceeded. max_curvature={self.k_max}")
                print(f"P0_xy, P1, P2, P3_xy={[P0_xy, P1, P2, P3_xy]}")
                self.action_status = ActionStatus.FAILED
                return

            # 成功构造路径,需要将路径分为2段，第一段后退至贝塞尔起始点
            self.control_point = [P0_xy, P1, P2, P3_xy]

            # 此处记录xs【0】，ys【0】
            self.first_point = [self.xs[0], self.ys[0]]
            self.first_point_return = [-self.xs[0], -self.ys[0]]

            if self.is_backwards:
                for i in range(len(self.xs)):
                    self.xs[i] -= self.offset_dist
            else:
                for i in range(len(self.xs)):
                    self.xs[i] += self.offset_dist

            self.end_angle_robot = self.end_position_robot[2]
            if self.is_backwards:
                self.end_angle_robot = (self.end_angle_robot + math.pi) % (2 * math.pi)
                if self.end_angle_robot > math.pi:
                    self.end_angle_robot -= 2 * math.pi

            # 此处记录self.xs & self.ys & end_angle_robot
            self.second_path = [self.xs, self.ys, self.end_angle_robot]
            self.xs_ret, self.ys_ret, self.theta_ret = self.generate_return_path(self.xs, self.ys)
            self.second_path_return = [self.xs_ret, self.ys_ret, self.theta_ret]

        self.action_status = ActionStatus.FINISHED

        robot_loc = [Loc.get_position()[0], Loc.get_position()[1], Loc.get_angle()[0]]
        f.cur_state["recordBezier"] = {
            "action_status": self.action_status,
            "k_max": self.k_max,
            "control_point": self.control_point,
            "xEnd,yEnd": [self.xs[-1], self.ys[-1]],
            "target_robot": self.target_robot,
            "target_pos_world": [self.end_position_world[0], self.end_position_world[1]],
            "robot_loc": robot_loc,
            "second_path_x": [self.second_path[0][0],self.second_path[0][-1]],
            "second_path_return_x": [self.second_path_return[0][0],self.second_path_return[0][-1]]
        }
        Module.report_info(f.cur_state)
        print(f.cur_state)

        f.first_point = self.first_point
        f.second_path = self.second_path
        f.first_point_return = self.first_point_return
        del self.second_path_return[0][1]
        f.second_path_return = self.second_path_return
        log.info(f"first_point={self.first_point}, second_path={self.second_path}")

    def reset(self):
        self.action_status = ActionStatus.RUNNING

    def compute_bezier_controls_dir(self, p0, p3, alpha=0.3):
        """
        计算三次 Bezier 的 4 个控制点（含端点），支持端点方向。
        :param
        p0, p3 : [x, y, theta]   theta 为弧度，表示该点切线方向
        alpha  : 0~1，控制 P1/P2 到端点的相对距离 (d = alpha * |P3-P0|)
        :return
        [P0_xy, P1, P2, P3_xy]   仅保留 (x, y)
        """
        x0, y0, th0 = p0
        x3, y3, th3 = p3

        # 端点间直线距离
        dist = math.hypot(x3 - x0, y3 - y0)
        d = alpha * dist  # 控制点到端点的绝对距离

        # 控制点
        p1 = [x0 + d * math.cos(th0), y0 + d * math.sin(th0)]
        p2 = [x3 - d * math.cos(th3), y3 - d * math.sin(th3)]

        return [p0, p1, p2, p3]  # 去掉角度，只留坐标

    def bezier_points(self, p0, p1, p2, p3, steps=1000):
        """
        生成 Bezier 曲线采样点
        :param
        p0~p3 : [x, y]
        steps : 采样分段数，返回 steps+1 个点
        :return
        (xs, ys) : 两个长度相等的列表
        """
        xs, ys = [], []
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 三次 Bezier 伯恩斯坦基函数
            b0 = one_t ** 3
            b1 = 3 * one_t ** 2 * t
            b2 = 3 * one_t * t ** 2
            b3 = t ** 3

            x = (b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0])
            y = (b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1])
            x = round(x, 7)
            y = round(y, 7)
            xs.append(x)
            ys.append(y)
        return xs, ys

    def bezier_curvature(self, p0, p1, p2, p3, steps=500):
        """
        基于导数计算三次贝塞尔曲线最大曲率
        p0~p3: 控制点[x, y]
        返回最大曲率
        """
        k_max = 0.0
        for i in range(steps + 1):
            t = i / steps
            one_t = 1 - t

            # 一阶导数
            dx_dt = 3 * one_t ** 2 * (p1[0] - p0[0]) + \
                    6 * one_t * t * (p2[0] - p1[0]) + \
                    3 * t ** 2 * (p3[0] - p2[0])
            dy_dt = 3 * one_t ** 2 * (p1[1] - p0[1]) + \
                    6 * one_t * t * (p2[1] - p1[1]) + \
                    3 * t ** 2 * (p3[1] - p2[1])

            # 二阶导数
            ddx_dt = 6 * one_t * (p2[0] - 2 * p1[0] + p0[0]) + \
                     6 * t * (p3[0] - 2 * p2[0] + p1[0])
            ddy_dt = 6 * one_t * (p2[1] - 2 * p1[1] + p0[1]) + \
                     6 * t * (p3[1] - 2 * p2[1] + p1[1])

            # 曲率公式
            numerator = abs(dx_dt * ddy_dt - dy_dt * ddx_dt)
            denominator = (dx_dt ** 2 + dy_dt ** 2) ** 1.5
            if denominator == 0:
                continue
            k = numerator / denominator
            k_max = max(k_max, k)
        return k_max

    def generate_return_path(self, xs, ys):
        """
        基于贝塞尔路径，返回原路倒退路径：机器人坐标系为终点局部坐标系，返回格式为 [xs, ys, theta]
        """
        if len(xs) < 2:
            return [], [], 0.0

        # 末段切线方向作为返回路径的正向角度
        dx = xs[-1] - xs[-2]
        dy = ys[-1] - ys[-2]
        theta_end = math.atan2(dy, dx)

        origin_x = xs[-1]
        origin_y = ys[-1]
        world_pts = list(zip(xs, ys))
        world_pts.reverse()

        cos_t = math.cos(theta_end)
        sin_t = math.sin(theta_end)

        xs_ret, ys_ret = [], []
        for wx, wy in world_pts:
            dx = wx - origin_x
            dy = wy - origin_y
            x_r = cos_t * dx + sin_t * dy
            y_r = -sin_t * dx + cos_t * dy
            xs_ret.append(-x_r)
            ys_ret.append(-y_r)

        return xs_ret, ys_ret, theta_end


class GoRecordedPath(BaseAction):
    """
        走记录过点坐标的路径
    """

    def __init__(self, first_point, second_path, is_backwards=True, max_speed=0.3, max_accele=1, max_decele=0.7,
                 decele_dist=1):
        super().__init__("GoRecordedPath")
        self.end_position_world = [0, 0, 0]
        self.end_position_robot = [0, 0, 0]

        self.first_point = first_point
        self.second_path = second_path
        self.is_backwards = is_backwards
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist

        self.action_status = ActionStatus.INIT
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        # 第一段线到位标识
        self.is_first_path_reached = False

    def run(self, f: Fork):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            self.init = False
            # 规划第一段倒退路线参数
            Navigation.setPathReachAngle(0.05)  # 到位精度
            Navigation.setPathReachDist(0.01)
            Navigation.setPathBackMode(not self.is_backwards)  # 设置正走倒走
            Navigation.setPathMaxSpeed(self.max_speed)
            Navigation.setPathOnRobot([0, self.first_point[0]], [0, self.first_point[1]], 0)
            self.param["maxAcc"] = float(self.max_accele)
            self.param["maxDec"] = float(self.max_decele)
            Navigation.goPathParam(self.param)

        if not self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走第一段路线到曲率合适的贝塞尔起点
            self.is_first_path_reached = Navigation.isPathReached()
            log.info(f"is_first_path_reached:{self.is_first_path_reached}")
            if self.is_first_path_reached:
                Navigation.resetPath()

                Navigation.setPathReachAngle(0.05)
                Navigation.setPathReachDist(0.01)
                Navigation.setPathBackMode(self.is_backwards)
                Navigation.setPathMaxSpeed(self.max_speed)

                Navigation.setPathOnRobot(self.second_path[0], self.second_path[1], self.second_path[2])
                self.param["maxAcc"] = float(self.max_accele)
                self.param["maxDec"] = float(self.max_decele)
                Navigation.goPathParam(self.param)

        if self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走贝塞尔到终点
            # Navigation.goPathParam(self.param)
            is_reached = Navigation.isPathReached()
            log.info(f"is_reached:{is_reached}")
            if is_reached:
                self.action_status = ActionStatus.FINISHED
                # return
            else:
                self.action_status = ActionStatus.RUNNING

            robot_current_loc = list(Loc.get_position())
            dist_cur_loc_end_loc = math.hypot(
                self.end_position_world[0] - robot_current_loc[0],
                self.end_position_world[1] - robot_current_loc[1]
            )
            if dist_cur_loc_end_loc < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(0.15)
                # Abnormal.setTask(55900, "has slow the speed", "", "", "")

        robot_loc = [Loc.get_position()[0], Loc.get_position()[1], Loc.get_angle()[0]]
        cur_state = {
            "action_status": self.action_status,
            "is_first_path_reached": self.is_first_path_reached,
            "first_point": self.first_point,
            "second_path": [self.second_path[0][-1], self.second_path[1][-1], self.second_path[2]],
            "target_pos_world": [self.end_position_world[0], self.end_position_world[1]],
            "max_speed": self.max_speed,
            "max_accele": self.max_accele,
            "robot_loc": robot_loc
        }
        Module.report_info(cur_state)

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        Navigation.resetPath()


class GoRecordedPathReturn(BaseAction):
    """
        走记录过点坐标的路径
    """

    def __init__(self, first_point, second_path, is_backwards=True, max_speed=0.3, max_accele=1, max_decele=0.7,
                 decele_dist=1):
        super().__init__("GoRecordedPathReturn")
        self.end_position_world = [0, 0, 0]
        self.end_position_robot = [0, 0, 0]

        self.first_point = first_point
        self.second_path = second_path
        self.is_backwards = is_backwards
        self.max_speed = max_speed
        self.max_accele = max_accele
        self.max_decele = max_decele
        self.decele_dist = decele_dist

        self.action_status = ActionStatus.INIT
        self.init = True
        self.target_robot = [0, 0, 0]
        self.control_point = None
        self.param = {}
        self.is_set_min_speed = False

        # 第一段线到位标识
        self.is_first_path_reached = False

    def run(self, f: Fork):
        if self.init:
            self.action_status = ActionStatus.RUNNING
            Navigation.resetPath()
            self.init = False
            # # 规划第一段倒退路线参数
            Navigation.setPathReachAngle(0.05)  # 到位精度
            Navigation.setPathReachDist(0.01)
            Navigation.setPathBackMode(self.is_backwards)  # 设置正走倒走
            Navigation.setPathMaxSpeed(self.max_speed)
            Navigation.setPathOnRobot(self.second_path[0], self.second_path[1], 0)
            self.param["maxAcc"] = float(self.max_accele)
            self.param["maxDec"] = float(self.max_decele)
            Navigation.goPathParam(self.param)

        if not self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走第一段路线到曲率合适的贝塞尔起点
            self.is_first_path_reached = Navigation.isPathReached()
            log.info(f"is_first_path_reached:{self.is_first_path_reached}")
            if self.is_first_path_reached:
                Navigation.resetPath()

                Navigation.setPathReachAngle(0.05)
                Navigation.setPathReachDist(0.01)
                Navigation.setPathBackMode(not self.is_backwards)
                Navigation.setPathMaxSpeed(self.max_speed)
                Navigation.setPathOnRobot([0, self.first_point[0]], [0, self.first_point[1]], 0)
                self.param["maxAcc"] = float(self.max_accele)
                self.param["maxDec"] = float(self.max_decele)
                Navigation.goPathParam(self.param)

        if self.is_first_path_reached and self.action_status != ActionStatus.FAILED:  # 走贝塞尔到终点
            # Navigation.goPathParam(self.param)
            is_reached = Navigation.isPathReached()
            log.info(f"is_reached:{is_reached}")
            if is_reached:
                self.action_status = ActionStatus.FINISHED
                # return
            else:
                self.action_status = ActionStatus.RUNNING

            robot_current_loc = list(Loc.get_position())
            dist_cur_loc_end_loc = math.hypot(
                self.end_position_world[0] - robot_current_loc[0],
                self.end_position_world[1] - robot_current_loc[1]
            )
            if dist_cur_loc_end_loc < self.decele_dist and not self.is_set_min_speed:
                self.is_set_min_speed = True
                Navigation.setPathMaxSpeed(0.15)
                # Abnormal.setTask(55900, "has slow the speed", "", "", "")

        robot_loc = [Loc.get_position()[0], Loc.get_position()[1], Loc.get_angle()[0]]
        cur_state = {
            "action_status": self.action_status,
            "is_first_path_reached": self.is_first_path_reached,
            "target_pos_world": [self.end_position_world[0], self.end_position_world[1]],
            "max_speed": self.max_speed,
            "max_accele": self.max_accele,
            "robot_loc": robot_loc
        }
        Module.report_info(cur_state)

    def reset(self):
        self.action_status = ActionStatus.RUNNING


class GoTwoStraightLine(BaseAction):
    def __init__(self, world_target, min_ahead_dist, ahead_dist, back_dist, speed, max_angle, dec_dist):
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
    input_params = Module.get_task_args()
    print("task args:", json.dumps(input_params, indent=2))
    validated_params = {}
    try:
        # 验证参数
        validated_params = validator.validate(input_params)
        print("check ok, args:", json.dumps(validated_params, indent=2))
    except ValueError as e:
        print("check error:", e)

    f = Fork(validated_params)

    Module.set_cancel_callback(f.cancel)
    while True:
        f.run()
        time.sleep(0.1)
        if f.script_status == ScriptStatus.FINISHED:
            Module.set_status(ScriptStatus.FINISHED)
            return
        if f.script_status == ScriptStatus.FAILED:
            Module.set_status(ScriptStatus.FAILED)
            return
        if f.script_status == ScriptStatus.NONE:
            Module.set_status(ScriptStatus.NONE)
            return


if __name__ == '__main__':
    main()
