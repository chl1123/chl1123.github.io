# -*- coding: utf-8 -*-
# Author: zzm
# version: 1.0
# Time: 2025/09/04
# description: CBD15-MF移植
# update:
#   08/29 屏蔽激光，支持原地载货卸货
#   09/04 适配识别文件识别面，不同坐标系，modbus


import json
import math
import time
import struct
from enum import IntEnum
from typing import Optional
from syspy.lib.net_protocol import parse_modbus
from syspy.utils.time import Timer
from syspy import NavSpeed, Controller
from syspy.script_data import ScriptData
from syspy.utils.param_server import ParamBuilder, ParamType, ParamValidator, ParamServer, BindType
from syspy import Module, ParamServer, Logger, Di, Do, Motor, Navigation, Loc, Abnormal, Recognize, ScriptStatus, \
    Odometer, Pgv, Laser, NetProtocol, Trace
from syspy.lib.module import Pos2Base, Pos2World, ModuleBase, SafeMoveStatus
from syspy.lib.robot_param import RobotParam
import tasks.standard.goBezier as GoBezier

log = Logger("Fork")

"""

"""


def clamp(val, lo, hi):
    return max(lo, min(val, hi))


EPS = 1e-6  # 浮点比较公差


class ConfigParams:
    """生成和定义配置参数的示例"""

    # 从模型文件中获取的参数

    second_rec_yaw = 1
    second_rec_y = 0.01
    load_unload_check = False
    module_type = RobotParam.getDevice("Model-000", "moduleType")
    fork_motor_name = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.liftMotor")
    shape = RobotParam.getDevice("Model-000", "shape")
    head = RobotParam.getDevice("Model-000", f"shape.{shape}.head")
    tail = RobotParam.getDevice("Model-000", f"shape.{shape}.tail")
    width = RobotParam.getDevice("Model-000", f"shape.{shape}.width")

    # 先判断是否是线性电机
    motor_func = RobotParam.getDevice(f"{fork_motor_name}", "func")
    min_height = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.minLength")
    max_height = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.maxLength")
    up_di = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.upLimitDI")
    down_di = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.DownLimitDI")
    fork_max_speed = RobotParam.getDevice(f"{fork_motor_name}", f"func.{motor_func}.maxSpeed")
    fork_root_3D_camera = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.forkRoot3DCamera")
    fork_root_2D_lasers = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.forkRoot2DLasers")
    fork_tip_3D_cameras = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.forkTip3DCameras").split(",")
    fork_tip_2D_lasers = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.forkTip2DLasers").split(",")
    fork_tip_distance_sensors = RobotParam.getDevice("Model-000",
                                                     f"moduleType.{module_type}.forkTipDistanceSensors").split(",")
    contact_ids_str = RobotParam.getDevice("Model-000", f"moduleType.{module_type}.id").split(",")

    # 如果是搬运车，需要判断一下是否是变轴距的车
    if module_type == "liftFork":
        robot_type = RobotParam.getDevice("Model-000", "getRobotType")
        if (robot_type == "variableWheelbaseSingleStandardSteer"
                or robot_type == "variableWheelbaseSingleDifferentialSteer"):
            base_shift = True
    elif module_type == "straddleLiftFork":
        pass

    # 从脚本配置参数里定义的参数，显示为小驼峰
    param_server = ParamServer(__file__)

    # 脚本相关
    timeout = param_server.loadParam(
        "timeout", type="float", default=120, comment="脚本超时时间", group="script")

    # fork 相关配置
    up_max_speed_with_goods = param_server.loadParam(
        "upMaxSpeedWithGoods", type="float", default=0.06, maxValue=0.1, minValue=0,
        comment="载货时的货叉上升最大速度", group="fork")
    down_max_speed_with_goods = param_server.loadParam(
        "downMaxSpeedWithGoods", type="float", default=0.06, maxValue=2, minValue=0,
        comment="载货时的货叉上升最大速度", group="fork")
    back_laser_enable_height = param_server.loadParam(
        "backLaserEnableHeight", type="float", default=0.3, maxValue=2, minValue=0,
        comment="后置激光避障生效时的货叉高度", group="fork")
    check_goods_while_load = param_server.loadParam(
        "checkGoodsWhileLoad", type="bool", default=True, comment="载货时检测到位 di", group="fork")
    check_all_contact_dis = param_server.loadParam(
        "checkAllContactDi", type="bool", default=False, comment="检测所有到位di", group="fork")

    # Do 控 fork 配置
    down_delay_time = param_server.loadParam(
        "downDelayTime", type="float", default=10, maxValue=0.1, minValue=20,
        comment="下降到位判断时间", group="forkByDO")
    up_delay_time = param_server.loadParam(
        "upDelayTime", type="float", default=10, maxValue=0.1, minValue=20,
        comment="上升到位判断时间", group="forkByDO")
    down_di_dofork = param_server.loadParam(
        "downDiDoFork", type="str", default="", comment="下到位di，输入DI name", group="forkByDO")
    up_di_dofork = param_server.loadParam(
        "upDiDoFork", type="str", default="", comment="上到位di, 输入DI name", group="forkByDO")
    leak_do = param_server.loadParam(
        "leakDo", type="str", default="", comment="泵电机Do, 输入DO name", group="forkByDO")
    pump_do = param_server.loadParam(
        "pumpDo", type="str", default="", comment="泄流阀Do, 输入DO name", group="forkByDO")

    # 取放货相关配置
    laser_detection_width = param_server.loadParam(
        "laserDetectionWidth", type="float", default=0.05, maxValue=2, minValue=0,
        comment="进叉时的激光宽度", group="load unload")
    back_dist = param_server.loadParam(
        "backDist", type="float", default=1, maxValue=3, minValue=0,
        comment="识别取货的后退距离", group="load unload")
    ahead_dist = param_server.loadParam(
        "aheadDist", type="float", default=0.8, maxValue=2, minValue=0,
        comment="识别取货的前置距离", group="load unload")  # 前置距离
    min_ahead_dist = param_server.loadParam(
        "minAheadDist", type="float", default=1, maxValue=2, minValue=0,
        comment="识别取货的最小直线距离", group="load unload")  # 最小直线距离，叉车起效
    use_straight_line = param_server.loadParam(
        "useStraightLine", type="bool", default=False,
        comment="识别取货的识别调整是否走直线曲线", group="load unload")  # 识别调整贝塞尔曲线
    load_adjust_distance = param_server.loadParam(
        "loadAdjustDistance", type="float", default=0.2, maxValue=2, minValue=-2, unit="m",
        comment="识别取货触发货叉开关后不抬升前移一小段", group="load unload")
    load_adjust_max_speed = param_server.loadParam(
        "load Adjust Max Speed", type="float", default=0.5, unit="m/s",
        comment="识别取货触发货叉开关后不抬升前移一小段的最大速度",
        group="load unload")
    bezier_return = param_server.loadParam("bezierReturn", type="bool", default=True, comment="是否按原路返回",
                                           group="load unload")
    fork_di_dist = param_server.loadParam(
        "forkDiDist", type="float", default=0.2, maxValue=0.5, minValue=0, group="load unload")

    # 线性堆栈相关
    laser_width = param_server.loadParam(
        "laserWidth", type="float", default=0.1, maxValue=1, minValue=0,
        comment="线性堆栈激光宽度", group="linear unload")  # 线性堆栈激光宽度
    obs_dist = param_server.loadParam(
        "obsDist", type="float", default=0.5, maxValue=1, minValue=0,
        comment="线性堆栈的避障距离", group="linear unload")  # 线性堆栈的避障距离
    load_obs_dist = param_server.loadParam(
        "loadObsDist", type="float", default=0.1, maxValue=11, minValue=0,
        comment="取货进叉时的避障距离", group="linear unload")  # 取货进叉时的避障距

    # 检测货物有无相关
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

    z_max = True
    error_rec_y = param_server.loadParam(
        "errorRecY", type="float", default=0.1, unit="m", comment="识别结果相对AP点报错的y方向偏移，-1不启用",
        group="Recognition")
    error_rec_angle = param_server.loadParam(
        "errorRecAngle", type="float", default=15, unit="m", comment="识别别结果相对AP点报错的yaw方向偏移，-1不启用",
        group="Recognition")


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
        # builder.MIN_VALUE(min_height)
        # builder.MAX_VALUE(max_height)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.1)


def create_start_height_param(builder: ParamBuilder, min_height: float, max_height: float):
    with builder.CHILD(key="startHeight", name="Start Height",
                       desc="The fork height before load"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        # builder.MIN_VALUE(min_height)
        # builder.MAX_VALUE(max_height)
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

                with builder.CHILD(key="recSide", name="Rec Side",
                                   desc="Rec Side"):
                    builder.TYPE(ParamType.STRING)
                    builder.DEFAULTVALUE("A")


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
                with builder.CHILD(key="forkLoad", name="Fork Load", desc="load the pallet"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 取货路径导航前的货叉高度
                        create_start_height_param(builder, min_height, max_height)

                        # 取完后的货叉高度
                        create_end_height_param(builder, min_height, max_height)

                        # 识别参数
                        create_rec_param(builder)

                # 放货操作
                with builder.CHILD(key="forkUnload", name="Fork Unload",
                                   desc="unload the pallet"):
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

                    with builder.CHILD(key="forkSpeed", name="Fork Speed", desc="fork lift speed"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.SINGLESTEP(0.01)
                        builder.REQUIRED(True)
                        builder.DEFAULTVALUE(ConfigParams.fork_max_speed)

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

        with builder.CHILD(key="targetName", name="Target Name", desc="Target ID Name"):
            builder.TYPE(ParamType.STRING)
            builder.DEFAULTVALUE("AP1")

    builder.save_to_file()


class Fork(ModuleBase):
    def __init__(self):
        super().__init__()
        self.do_fork = False
        self.task_args = {}
        self.forkSpeed = 0.
        self.endHeight = 0.
        self.recfile = ""

        self.target_pos = [0, 0, 0, -1]
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
        self.move_task = dict()
        self.first_point = None
        self.second_path = None
        self.first_point_return = None
        self.second_path_return = None
        self.pallet_width = 0
        self.cur_state = {}
        self.rec_sides = []
        self.move_info = {}
        self.trace_chart = {}

    def run(self, args):
        self.script_status = ScriptStatus.RUNNING
        if Abnormal.exists(53320):
            self.script_status = ScriptStatus.FAILED
            return
        if not self.init_args:
            self.init_args = True
            self.task_args = args

            self._init_args()
        self._check_timeout()

        if self.opt == "forkLoad":
            self.load()
        elif self.opt == "forkUnload":
            self.unload()
        elif self.opt == "forkHeight":
            self.fork_move()
        elif self.opt == "rec":
            self.rec()
        elif self.opt == "leaveLoc":
            self.leave_loc()
        elif self.opt == "test":
            self.test()
        else:
            Abnormal.setTask(53300, f"wrong operation:{self.opt}, script failed", "input operation not define",
                             "check the input param", "")
            self.script_status = ScriptStatus.FAILED
        self._execute_actions()
        if self.action_status == ScriptStatus.FAILED:
            self.script_status = ScriptStatus.FAILED

        # Module.report_info()

    def suspend(self):
        self.script_status = ScriptStatus.SUSPENDED
        Trace.log("suspend")

    def resume(self):
        if self.script_status == ScriptStatus.SUSPENDED:
            self.script_status = ScriptStatus.RUNNING
        Trace.log("resume")

    def cancel(self):
        self.script_status = ScriptStatus.FAILED
        Trace.log("cancel")

    def modbus(self):
        # modbus解析器

        # 读取数据
        operation = None
        operation_int = NetProtocol.getModbusData("4x", 200, 1)
        if operation_int == 1:
            operation = "forkHeight"

        modbus_data = NetProtocol.getModbusData("4x", 201, 2)
        data = parse_modbus(modbus_data, "float")

        print(f"operation:{operation_int}, modbus_data:{modbus_data},fork height:{data}")

        regs = self.float32_to_regs(-1.0)
        NetProtocol.setModbusData("4x", 13, regs)
        args = {"operation": operation, "forkHeight": data}

        # 解析映射表
        self.event_modbus = False
        # 做对应的动作
        return args

    def to_float32_little(self, data):
        """
        data: list of two 16-bit words [low, high]
        拼接为 float32，小端模式（低位在前）
        """
        raw = ((data[1] & 0xFFFF) << 16) | (data[0] & 0xFFFF)
        return struct.unpack("!f", raw.to_bytes(4, byteorder="big"))[0]

    def float32_to_regs(self, value: float):
        """float32 转成两个寄存器（小端：低位在前）"""
        raw = struct.pack("!f", value)  # 转成 4 字节
        word1 = int.from_bytes(raw[2:], "big")  # 低地址寄存器 = 低 16 位
        word2 = int.from_bytes(raw[:2], "big")  # 高地址寄存器 = 高 16 位
        return [word1, word2]

    def safe_move_check(self):
        status = SafeMoveStatus.FINISHED
        self.set_safe_move_status(status)
        # Trace.log(f"safe_move_check {Module.get_safe_move_check()}")
        if status == SafeMoveStatus.FAILED or status == SafeMoveStatus.FINISHED:
            self.event_safe_move_check = False

    def get_target_pos(self):
        target_id = self.move_task.get("target_name", "")  # int, 可能是 LM，可能是 AP

        if target_id == "":
            # task_args 里已经是带前缀的字符串
            target_id_str = self.task_args.get("targetName", "")
            pos = Navigation.getLM(target_id_str, True)
            return pos
        else:
            # 尝试 AP 和 LM 两个前缀
            for prefix in ["AP", "LM"]:
                target_id_str = f"{prefix}{target_id}"
                pos = Navigation.getLM(target_id_str, True)
                if pos[3] != -1:  # 找到有效结果
                    Trace.log(f"target_id_str:{target_id_str}, target_id:{target_id}, pos:{pos}")
                    return pos  # 优先返回成功的结果

            # 如果走到这里，说明 AP 和 LM 都失败了
            Trace.log(f"Both AP{target_id} and LM{target_id} not found, return last pos:{pos}")
            return pos

    def test(self):
        if not self.operation_init:
            self.operation_init = True

            r_loc = Loc.get_pose()
            self.target_pos = Navigation.getLM("AP10", True)

            rec_world_pos = Pos2World([-1, 0, 0], [r_loc["x"], r_loc["y"], math.radians(r_loc["yaw"])])

            # 根据AP点，异常识别结果报警，如果 AP 点没有角度怎么办
            rec2ap_pos = Pos2Base(rec_world_pos, self.target_pos)
            angle = math.degrees(rec2ap_pos[2])
            Trace.log(
                f"rec2ap_pos: {rec2ap_pos},rec_world_pos: {rec_world_pos},target_pos:{self.target_pos},angle2ap:{angle}")
            y = rec2ap_pos[1]
            if abs(angle) > ConfigParams.error_rec_angle != -1:
                Abnormal.setTask(53303, f"rec result yaw angle too large:{angle}°", "", "", "")
                self.script_status = ScriptStatus.FAILED
                return
            if abs(y) > ConfigParams.error_rec_y != -1:
                Abnormal.setTask(53321, f"rec result y too large:{y}m", "", "", "")
                self.script_status = ScriptStatus.FAILED
                return

            # 根据参数配置是否走贝塞尔曲线选择调整办法
            args = {
                "back_dist": ConfigParams.back_dist,
                "min_ahead_dist": ConfigParams.min_ahead_dist,
                "adjust_dist": ConfigParams.ahead_dist,
            }
            if ConfigParams.use_straight_line:
                method = "twoStraightLine"
                args["max_angle"] = 10
            else:
                method = "goBezier"
                args["max_curve"] = 3
            self.action_list.extend([
                GoPathWithContactDi(ConfigParams.contact_ids_str, rec_world_pos, 0.05, method, args),
            ])
        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED

    # 识别取货和非识别取货
    def load(self):
        if not self.operation_init:
            self.operation_init = True
            self.do_fork = self.do_fork_check()
            r_loc = Loc.get_pose()

            # 从任务参数 或者从 脚本任务参数里获取到AP点及其坐标
            self.target_pos = self.get_target_pos()

            target2robot = Pos2Base(self.target_pos, [r_loc["x"], r_loc["y"], math.radians(r_loc["yaw"])])

            Trace.log(f"target pos :{self.target_pos}")

            # 如果有货,脚本无法取货并报错
            if Navigation.hasGoods() and ConfigParams.load_unload_check:
                Abnormal.setTask(53302, f"fork has goods, cannot load, script failed",
                                 "fork has goods",
                                 "unload goods before loading", "load")
                self.script_status = ScriptStatus.FAILED
                return

            # 不需要根据识别结果通过盲走插货
            if not self.recognize:
                if self.do_fork:
                    self.action_list = [
                        RunMotorByDOInterlock("down", ConfigParams.pump_do, ConfigParams.leak_do,
                                              ConfigParams.up_di_dofork, ConfigParams.down_di_dofork,
                                              ConfigParams.up_delay_time, ConfigParams.down_delay_time),
                        GoPathWithContactDi(ConfigParams.contact_ids_str, self.target_pos, 0.05, "goPath",
                                            {"fork_di_dist": ConfigParams.fork_di_dist}),
                        RunMotorByDOInterlock("up", ConfigParams.pump_do, ConfigParams.leak_do,
                                              ConfigParams.up_di_dofork, ConfigParams.down_di_dofork,
                                              ConfigParams.up_delay_time, ConfigParams.down_delay_time),
                    ]
                else:
                    if not self.target_pos or self.target_pos[3] == -1:
                        self.action_list = [
                            RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
                        ]
                    else:
                        self.action_list = [
                            RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height),
                            GoPathWithContactDi(ConfigParams.contact_ids_str, self.target_pos, 0.05, "goPath",
                                                {"fork_di_dist": ConfigParams.fork_di_dist}),
                            RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
                        ]

            # 如果需要识别后再取货
            else:
                if self.do_fork:
                    self.action_list = [
                        RunMotorByDOInterlock("down", ConfigParams.pump_do, ConfigParams.leak_do,
                                              ConfigParams.up_di_dofork, ConfigParams.down_di_dofork,
                                              ConfigParams.up_delay_time, ConfigParams.down_delay_time),
                    ]
                else:
                    self.action_list = [RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height)]

                self.action_list.append(Rec(self.recfile, target2robot, "RecPallet"))

            Trace.log(f"task:{self.action_list}")

        # 识别结束后动态加调整的类
        if self.action_id < len(self.action_list) and self.recognize:
            current_action = self.action_list[self.action_id]
            r_loc = Loc.get_pose()
            if (isinstance(current_action, Rec)
                    and current_action.action_name == "RecPallet"
                    and current_action.action_status == ActionStatus.FINISHED):
                results = current_action.results_list

                # 处理识别结果时，既需要考虑z方向的，又需要考虑x轴 和 y 轴的。默认取 z 离 startHeight 上下 10cm的结果先过滤一次
                filter_results_by_z = [result for result in results if abs(result["z"] - self.start_height) <= 0.1]
                self.pallet_width = filter_results_by_z[0]["palletWidth"]

                # 拿到 y 最小的值
                results_in_r = []

                if self.rec_info.get("coordinateSystem") == Coordinate.WORLD:
                    for result in filter_results_by_z:
                        results_in_r.append(Pos2Base([result["x"], result["y"], result["yaw"]],
                                                     [r_loc["x"], r_loc["y"], math.radians(r_loc["yaw"])]))
                else:
                    for result in filter_results_by_z:
                        results_in_r.append([result["x"], result["y"], result["yaw"]])

                # 相对于机器人取 y 最小的
                min_y_result = min(results_in_r, key=lambda result_in_r: result_in_r[1])

                rec_result2r = min_y_result
                rec_world_pos = Pos2World(rec_result2r, [r_loc["x"], r_loc["y"], math.radians(r_loc["yaw"])])
                # rec_world_pos = [self.rec_result["x"], self.rec_result["y"], self.rec_result["yaw"]]
                # if self.rec_params['recCoordinate'] == "robot":
                #     robot_pos = Loc.get_data()
                #     rec_world_pos = Pos2World(rec_world_pos, [robot_pos["x"], robot_pos["y"], robot_pos["angle"]])

                # 根据AP点，异常识别结果报警，如果 AP 点没有角度怎么办
                if self.target_pos and self.target_pos[3] != -1:
                    rec2ap_pos = Pos2Base(rec_world_pos, self.target_pos)
                    angle = math.degrees(rec2ap_pos[2])
                    Trace.log(
                        f"rec2ap_pos: {rec2ap_pos},rec_world_pos: {rec_world_pos},target_pos:{self.target_pos},angle2ap:{angle}")
                    y = rec2ap_pos[1]
                    if abs(angle) > ConfigParams.error_rec_angle != -1:
                        Abnormal.setTask(53303, f"rec result yaw angle too large:{angle}°", "", "", "")
                        self.script_status = ScriptStatus.FAILED
                        return
                    if abs(y) > ConfigParams.error_rec_y != -1:
                        Abnormal.setTask(53321, f"rec result y too large:{y}m", "", "", "")
                        self.script_status = ScriptStatus.FAILED
                        return

                # # 识别二次调整，先靠近，再次识别，再决定进叉还是
                # if rec_result2r[1] >= ConfigParams.second_rec_y or rec_result2r[2] >= math.radians(
                #         ConfigParams.second_rec_yaw):
                #     arg = {
                #         'x': r_loc["x"],
                #         'y': r_loc["y"],
                #         'theta': math.radians(r_loc["yaw"]),
                #         'coordinate': 'world',
                #         'backMode': 0,
                #         'maxRot': 10,
                #         'maxSpeed': 0.2,
                #         'useOdo': 0
                #     }
                #     self.action_list = [GoPath(arg)]

                # 根据参数配置是否走贝塞尔曲线、直线选择调整办法
                args = {
                    "back_dist": ConfigParams.back_dist,
                    "min_ahead_dist": ConfigParams.min_ahead_dist,
                    "adjust_dist": ConfigParams.ahead_dist,
                }
                if ConfigParams.use_straight_line:
                    method = "twoStraightLine"
                    args["max_angle"] = 20
                else:
                    method = "goBezier"
                    args["max_curve"] = 3
                self.action_list.extend([
                    # RunMotorByPosition(ConfigParams.fork_motor_name, self.rec_result["z"]),
                    GoPathWithContactDi(ConfigParams.contact_ids_str, rec_world_pos, 0.05, method, args),
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
                ])

        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            Navigation.setGoodsShape(ConfigParams.head, ConfigParams.tail, max(self.pallet_width, ConfigParams.width))
            self.script_status = ScriptStatus.FINISHED

    def leave_loc(self):
        if not self.operation_init:
            self.operation_init = True
            self.do_fork = self.do_fork_check()

            target_pos = self.get_target_pos()
            if target_pos[3] == -1:
                Abnormal.setTask(53323, f"cannot find point, script failed", "wrong LM point", "check the input param",
                                 "")
                self.script_status = ScriptStatus.FAILED
                return
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
            if ConfigParams.bezier_return and not ConfigParams.use_straight_line:
                self.action_list = [
                    GoBezier.GoBezierWorldReturn(False)
                ]
            elif ConfigParams.bezier_return and ConfigParams.use_straight_line:
                self.action_list = [
                    GoTwoStraightLine(0, 0, 0, 0, 0, 0, 0, True)
                ]
            else:
                self.action_list = [
                    GoPath(args)
                ]
            if self.do_fork:
                self.action_list.append(
                    RunMotorByDOInterlock("down", ConfigParams.pump_do, ConfigParams.leak_do,
                                          ConfigParams.up_di_dofork, ConfigParams.down_di_dofork,
                                          ConfigParams.up_delay_time, ConfigParams.down_delay_time))
            else:
                self.action_list.append(RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height))

        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED

    def unload(self):
        if not self.operation_init:
            self.operation_init = True
            self.do_fork = self.do_fork_check()

            # if not Navigation.hasGoods():
            #     Abnormal.setTask(53903, f"fork has no goods, cannot unload, script failed", "", "", "unload")
            #     self.script_status = ScriptStatus.FAILED
            #     return
            # target_pos = self.get_target_pos()
            target_pos = []
            if not target_pos:
                self.action_list = [
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
                ]
            # target_pos = Navigation.getLM("LM2", True)
            else:
                args = {
                    'x': target_pos[0],
                    'y': target_pos[1],
                    'theta': target_pos[2],
                    'coordinate': 'world',
                    'backMode': 1,
                    'maxRot': 10,
                    'maxSpeed': 0.1,
                    'useOdo': 0
                }
                self.action_list = [
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.start_height),
                    GoPath(args),
                    RunMotorByPosition(ConfigParams.fork_motor_name, self.end_height)
                ]

        if self.action_id >= len(self.action_list) and self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED
            Navigation.clearGoodsShape()
        #
        #     if current_action.action_name == "GoPath" and current_action.action_status == ActionStatus.RUNNING:

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
                Abnormal.setTask(53305, f"execute action {current_action} failed!", "", "", "")
                self.action_status = ActionStatus.FAILED
                return
            elif current_action.action_status == ActionStatus.INIT:
                current_action.reset()
                # print(1)
            else:
                current_action.run()
                # print(2)
            self.trace_chart.update(
                self._flat_attrs(current_action, idx1=self.action_id)
            )

            self.trace_chart.update({
                "script.action_id": self.action_id,
                "script.action_status": self.action_status,
                "script.cur_action": current_action.action_name,
                "script.cur_action_status": current_action.action_status,
                "script.script_state": self.script_status
            })
        else:
            self.action_status = ActionStatus.FINISHED

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        Trace.log(f"{Module.get_task_args()=}")
        Trace.log(f"{Module.get_task_id()=}")
        Trace.log(f"{Module.get_status()=}")

    def fork_move(self):
        if not self.operation_init:
            self.operation_init = True
            self.do_fork = self.do_fork_check()
            # forkHeight 和 forkSpeed 为任务输入参数
            if ConfigParams.fork_motor_name:
                self.action_list = [RunMotorByPosition(ConfigParams.fork_motor_name, self.forkHeight, self.forkSpeed)]
        if self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED
        # print("action_status:" + json.dumps(cur_status))

    def _init_args(self):

        # 解析任务参数，script_args 里的参数
        self.recfile = self.task_args.get("recfile", "")
        self.opt = self.task_args.get("operation", "")
        self.start_height = self.task_args.get("startHeight", 0.09)
        self.end_height = self.task_args.get("endHeight", 0.2)
        self.recognize = self.task_args.get("recognize")
        self.forkHeight = self.task_args.get("forkHeight")
        self.forkSpeed = self.task_args.get("forkSpeed")
        self.recSide = self.task_args.get("recSide")

        # 解析识别文件
        if self.recfile:
            recognitionSide_key = "recognitionObject.pallet.recognitionSide"
            recognitionSide_size = RobotParam.getConfigCloneSize("recognition", recognitionSide_key, self.recfile)
            for i in range(recognitionSide_size):
                side_value = RobotParam.getConfig("recognition", f"{recognitionSide_key}._{i}", self.recfile)
                coordinateSystem = RobotParam.getConfig("recognition",
                                                        f"{recognitionSide_key}._{i}.{side_value}.coordinateSystem",
                                                        self.recfile)
                enableCargoContactDI = RobotParam.getConfig("recognition",
                                                            f"{recognitionSide_key}._{i}.{side_value}.enableCargoContactDI",
                                                            self.recfile)
                enableBackDistance = RobotParam.getConfig("recognition",
                                                          f"{recognitionSide_key}._{i}.{side_value}.enableBackDistance",
                                                          self.recfile)
                side_info = {
                    "side_value": side_value,
                    "coordinateSystem": coordinateSystem,
                    "enableCargoContactDI": enableCargoContactDI,
                    "enableBackDistance": enableBackDistance
                }

                if enableBackDistance:
                    backDistance = RobotParam.getConfig("recognition",
                                                        f"{recognitionSide_key}._{i}.{side_value}.backDistance",
                                                        self.recfile)
                    side_info["backDistance"] = backDistance
                self.rec_sides.append(side_info)
            if self.recSide:
                self.rec_info = next((s for s in self.rec_sides if s["side_value"] == self.recSide), None)
            else:
                self.rec_info = self.rec_sides[0]

            if any(v is None or v == "none" for v in self.rec_info.values()):
                Abnormal.setTask(53325, f"Invalid side_info, found None: {self.rec_info},script failed",
                                 "recognize file param wrong", "check the param", "")
                self.script_status = ScriptStatus.FAILED

        # 解析任务下发的参数，不含在 script_args 里的参数
        self.move_task = Navigation.moveTask()

        self.start_time = time.time()
        # self.opt = "rec"
        # Abnormal.setTask(53000, "test", "", "", "")

    def _check_timeout(self):
        self.script_runtime = time.time() - self.start_time
        if self.script_runtime > ConfigParams.timeout:
            self.script_status = ScriptStatus.FAILED
            return

    def _flat_attrs(self, action, idx1: int):
        """把 action 展平为 {1.Class.attr: value, ...}"""
        snap = {}
        cls = action.__class__.__name__
        for name in dir(action):
            if name.startswith("_"):
                continue
            try:
                val = getattr(action, name)
                if not callable(val):
                    # 尝试序列化，不行就转成 str
                    try:
                        # 尝试序列化
                        json.dumps(val)
                        safe_val = val
                    except TypeError:
                        # 序列化失败就转字符串
                        safe_val = str(val)
                    snap[f"action.{idx1}.{cls}.{name}"] = safe_val
            except Exception:
                pass
        return snap

    # def _report(self):
    #     cur_status = dict()
    #     if self.action_id < len(self.action_list):
    #         cur_status['action_id'] = self.action_id
    #         cur_status['action_num'] = len(self.action_list)
    #         cur_status['action_list'] = [str(action) for action in self.action_list]
    #         cur_status['action_status'] = self.action_list[self.action_id].action_status
    #         cur_status['script_status'] = self.script_status

    def rec(self):
        if not self.operation_init:
            self.operation_init = True
            self.action_list = [Rec(self.recfile, self.target_pos)]
        if self.action_status == ActionStatus.FINISHED:
            self.script_status = ScriptStatus.FINISHED

    def reset(self):
        self.target_pos = [0, 0, 0, -1]
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
        # self.contact_di = [ConfigParams.contact_di_1, ConfigParams.contact_di_2]
        self.contact_di = [9]
        self.recfile = ""
        self.move_task = dict()
        self.first_point = None
        self.second_path = None
        self.first_point_return = None
        self.second_path_return = None
        self.cur_state = {}

    def period_run(self):
        fork_height = Motor.get_motor_pos(ConfigParams.fork_motor_name)
        self.trace_chart.update({
            "forkHeight": fork_height,  # 货叉高度, 单位 m
            # "forkHeightInPlace": Motor.isMotorReached(ConfigParams.fork_motor_name),  # 货叉高度是否到位, true = 到位, false = 未到位
            "forkAutoFlag": not Controller.get_is_external_control(),
            # 叉车的控制模式(通过叉车上的物理按钮切换), ture = 自动控制(控制器控制), false = 手动控制(方向盘驾驶)
        })
        Module.report_info(self.trace_chart)
        # print(self.move_info)

        # Trace.log(f"fork height :{fork_height}, di 5:{Di.get_di('DI-005')},di 2:{Di.get_di('DI-002')}")

        # 堆高车处理后激光的屏蔽
        if ConfigParams.module_type == "straddleLiftFork":
            # fork_height = Motor.get_motor_pos(ConfigParams.fork_motor_name)
            # 获取当前避障设备列表
            if fork_height <= ConfigParams.back_laser_enable_height:
                # print("here")
                current_collision_device_str = (RobotParam.getConfig("navigation",
                                                                     "collisionDetection.detectionDevice"))
                current_collision_device = current_collision_device_str.split(",")
                if ConfigParams.fork_root_2D_lasers in current_collision_device:
                    current_collision_device.remove(ConfigParams.fork_root_2D_lasers)
                    current_collision_device_str = ",".join(current_collision_device)
                policy = {
                    "navigation.collisionDetection.detectionDevice": current_collision_device_str
                }
                Navigation.appendCustomPolicy("policy", policy)
            # dev_1 = (RobotParam.getConfig("navigation", "collisionDetection.detectionDevice"))
            # Trace.log(f"Device 1: {dev_1}")
            # loadMaxSpeed = RobotParam.getConfig("navigation", "basic.load.loadMaxSpeed")
            # print("loadMax end2", loadMaxSpeed)

        # 处理载货时di状态监控
        if Navigation.hasGoods() and ConfigParams.check_goods_while_load and ConfigParams.check_all_contact_dis:
            # 获取到位 di 的状态
            di_status = []
            contact_ids_str = RobotParam.getDevice("Model-000", f"moduleType.straddleLiftFork.id").split(",")
            for di in contact_ids_str:
                di_status.append(Di.get_di(di))

            # 根据是否检测所有到位di 决定错误状态
            if ConfigParams.check_all_contact_dis:
                missing_goods = not all(di_status)
            else:
                missing_goods = not any(di_status)

            # 做 0.3s 的延时处理
            if missing_goods and Timer.delay(0.3):
                Abnormal.setTask(53319, "fork missing goods",
                                 f"check the contact dis :{ConfigParams.contact_ids_str}", "", "")
            else:
                if Timer.delay(0.3):
                    if Abnormal.exists(53319):
                        Abnormal.clear(53319)
            # Trace.log(f"di status: {di_status}, missing_goods:{missing_goods}")

    def do_fork_check(self):
        if ConfigParams.fork_motor_name is None:
            missing_params = []
            if ConfigParams.down_di is None:
                missing_params.append("down_di_dofork")
            if ConfigParams.up_di_dofork is None:
                missing_params.append("up_di_dofork")
            if ConfigParams.leak_do is None:
                missing_params.append("leak_do")
            if ConfigParams.pump_do is None:
                missing_params.append("pump_do")

            # 输出为空的参数，或者返回 True
            if missing_params:
                Abnormal.setTask(53320, f"when fork lift motor is None, check the do fork config:{missing_params}", "",
                                 "", "")
            else:
                return True


class BaseAction:
    """定义动作的基类"""

    def __init__(self, action_name: str = None):
        self.action_name = action_name or self.__class__.__name__

        self.start_time = time.time()
        self.action_status = ActionStatus.INIT
        self.action_state = {}
        self.init = False

    def run(self):
        self.action_state["action_runtime"] = time.time() - self.start_time
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
    def __init__(self, pallet_file, target_pos=None, action_name="RecPallet"):
        super().__init__(action_name)
        self.rec_status = None
        self.result = dict()
        self.action_status = ActionStatus.INIT
        self.target_pos = target_pos
        self.recfile = pallet_file
        self.attempts = 0
        self.max_attempts = 20
        self.success = False
        self.results_dict = {}
        self.results_list = []
        print(f"rec init")

    def run(self):
        if not self.init:
            self.init = True
            self.success = False
        print(f"rec run")

        self.action_status = ActionStatus.RUNNING
        if not self.success:
            self.success, self.rec_status, self.results_dict = self.rec(self.recfile)
        else:
            self.results_list = self.results_dict.get("reco_list", [])
            # 处理识别结果，并按降序排序，z值最大的结果在前
            if ConfigParams.z_max:
                z_max_results = sorted(self.results_list, key=lambda item: item['z'], reverse=True)
                self.result = z_max_results[0]
                Trace.log(f"rec_results: {self.result}")

            self.action_status = ActionStatus.FINISHED

    def reset(self):
        Recognize.resetRec()
        self.action_status = ActionStatus.RUNNING

    def rec(self, recfile):
        rec_status = Recognize.getRecStatus()
        if rec_status == 2:
            rec_result = Recognize.getRecResults()
            Trace.log(f"rec_result:{rec_result}")
            return True, rec_status, rec_result
        elif rec_status in (-1, 3):
            if Timer.delay(0.05):
                self.attempts += 1
                if self.attempts > self.max_attempts:
                    results = Recognize.getRecResults()
                    error_type = results["error_type"]
                    error_msg = results["log_msg"]
                    Trace.log(f"error_type: {error_type}")
                    self.action_status = ActionStatus.FAILED
                    Abnormal.setTask(53306,
                                     "Recognition failed, the maximum number of retries exceeded",
                                     f"{error_msg}",
                                     "",
                                     "")
                else:
                    Recognize.resetRec()
        else:
            Trace.log(f"target_pos_in_rec: {self.target_pos}")

            if self.target_pos is None or (len(self.target_pos) > 3 and self.target_pos[3]) == -1:
                Recognize.doRec(recfile, False)
            else:
                # Recognize.doRec(recfile, False)
                Recognize.doRec(recfile, True, self.target_pos[0], self.target_pos[1], self.target_pos[2], 1)
            Timer.delay(0.05)
        return False, rec_status, list


class GoPathWithContactDi(BaseAction):
    def __init__(self, contact_dis, world_pos, obs_dist, method, args):
        super().__init__()
        self.di_filter_time = 1
        self.check_all_contact_di = False
        self.laser_id = []
        self.check_di = False
        self.laser_width = None
        self.walk_dist = None
        self.di_status = []
        self.contact_di = contact_dis
        Trace.log(f"contact_di: {self.contact_di}")
        if self.contact_di:
            self.check_di = True
        self.goal = [0, 0, 0]
        self.init = False
        self.action_status = ScriptStatus.NONE
        self.obsDist = obs_dist
        self.start_loc = None
        self.method = method
        self.di_trigger_time = None

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
            self.back_action = GoBezier.GoBezierWorld(world_pos, args["back_dist"], args["adjust_dist"],
                                                      args["min_ahead_dist"], True,
                                                      None, 0.1, 0.3, 0.2, 0.1, args["max_curve"])
        elif method == "twoStraightLine":
            self.back_action = GoTwoStraightLine(world_pos, args["min_ahead_dist"], args["adjust_dist"],
                                                 args["back_dist"], 0.2, args['max_angle'], 1)
        # self.back_status = self.back_action.action_status

    def run(self):
        self.action_status = ScriptStatus.RUNNING
        if not self.init:
            self.init = True
            self.start_loc = Loc.get_pose()
            if ConfigParams.fork_tip_2D_lasers:
                for laser in ConfigParams.fork_tip_2D_lasers:
                    Laser.setLaserWidth(laser, 0.05)

        # 开始后退
        if self.back_action.action_status not in [ScriptStatus.FAILED, ScriptStatus.FINISHED]:
            Navigation.setObsStopDist(0.1)
            self.back_action.run()

        # 如果没有到位 di
        if not self.check_di:
            self.action_status = self.back_action.action_status

        # 获取到位 di 的状态
        self.di_status = []
        for di in self.contact_di:
            if di != '':
                self.di_status.append(Di.get_di(di))

        # 如果不需要检查所有的到位 di，一个到位任务结束
        if not self.check_all_contact_di:
            # 任务结束超过 1 s，且没有到位 di 触发，则报错结束任务
            if self.back_action.action_status == ActionStatus.FINISHED and not all(self.di_status) and Timer.delay(1):
                Abnormal.setTask(53307, f"not trigger di but robot reach goal",
                                 f"please check the di dist or reach di:{self.contact_di}", "", "")
                self.action_status = ActionStatus.FAILED
            # 一个到位任务结束
            if any(self.di_status):
                if self.stop_robot():
                    self.action_status = ActionStatus.FINISHED

        # 仅检查所有到位 di 的情况
        else:
            # 所有到位 di 没有全部触发，则报错结束任务
            if self.back_action.action_status == ActionStatus.FINISHED and not any(self.di_status) and Timer.delay(1):
                Abnormal.setTask(53308, f"not trigger di but robot reach goal",
                                 f"please check the di dist or reach di:{self.contact_di[0]},di:{self.contact_di[1]}",
                                 "", "")
                self.action_status = ActionStatus.FAILED
            # 到位触发判断，从一个 di 触发后的一段时间内，其他 di 都触发，算任务结束；如果没有全部触发，则报错
            if any(self.di_status):
                if Timer.delay(self.di_trigger_time):
                    if all(self.di_status):
                        if self.stop_robot():
                            self.action_status = ActionStatus.FINISHED
                    else:
                        Abnormal.setTask(53308, f"not all di triggered but robot reach goal",
                                         f"please check the di dist or reach di:{self.contact_di[0]},di:{self.contact_di[1]}",
                                         "", "")
                        self.action_status = ActionStatus.FAILED
        if self.action_status in [ActionStatus.FINISHED, ActionStatus.FAILED]:
            Laser.clearLaserWidth()
        # cur_state = dict()
        # cur_state['status'] = self.action_status
        # cur_state['method'] = self.method
        # cur_state['back status'] = self.back_action.action_status
        # cur_state['check_di'] = self.check_di
        # cur_state['contact_di'] = self.contact_di
        # cur_state['walk_dist'] = self.cal_walk_dist()
        # cur_state['di_status'] = self.di_status
        # cur_state['obs_dist'] = self.obsDist

    def reset(self):
        self.action_status = ScriptStatus.RUNNING
        self.init = False

    def cal_walk_dist(self):
        cur_loc = Loc.get_pose()
        cur_dist = math.sqrt(
            (self.start_loc["x"] - cur_loc["x"]) ** 2 + (self.start_loc["y"] - cur_loc["y"]) ** 2)
        return cur_dist

    def stop_robot(self):
        # set_speeds = NavSpeed.set_speeds(0, 0, 0)
        # Trace.log(f"set speeds: {set_speeds}")
        # v_x, v_y, v_w = NavSpeed.get_speeds()
        # if all(abs(v) <= 0.01 for v in (v_x, v_y, v_w)):
        #     return True
        Navigation.stopRobot(True)
        Navigation.resetPath()


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

    def run(self):
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
                    Abnormal.setTask(53309, f"{self.loc_name} is not filled", "", "", "LocDetectGoods")
                    # f.is_goods_detected = False
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
                    Abnormal.setTask(53310, f"{self.loc_name} is filled", "", "", "LocDetectGoods")
                    # f.is_goods_detected = True
                    self.action_status = ActionStatus.FINISHED
        else:
            Abnormal.setTask(53311, f"{self.loc_name} does not exist", "", "", "LocDetectGoods")
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

    def __init__(self, motor_name, position, max_speed=0.1, stop_di=""):
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

        self.positions = []
        self.check_duration = 20
        self.fork_timestamps = []
        self.last_sample_time = None

    def run(self):
        cur_fork_height = Motor.get_motor_pos(self.motor_name)

        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.last_sample_time = time.time()
            self.init = True

            min_h, max_h = ConfigParams.min_height, ConfigParams.max_height
            # 先夹到允许区间
            self.position = clamp(self.position, min_h, max_h)

            # 如果是搬运车，做一些最大最小高度的逻辑处理
            if ConfigParams.module_type == "liftFork":

                # 方向判断：>0 上升；<0 下降；=0 到位
                delta = self.position - cur_fork_height
                if abs(delta) <= EPS:
                    self.action_status = ActionStatus.FINISHED
                else:
                    self.position = max_h if delta > 0 else min_h

            # 从输入参数和配置参数里选出最大速度
            max_speed = min(ConfigParams.fork_max_speed, self.max_speed)

            # 考虑载货时的货叉升降速度
            if Navigation.hasGoods():
                delta = self.position - cur_fork_height
                if abs(delta) <= EPS:
                    self.action_status = ActionStatus.FINISHED
                else:
                    # 上/下行分别套上限
                    if delta > 0:
                        max_speed = min(max_speed, ConfigParams.up_max_speed_with_goods)
                    else:
                        max_speed = min(max_speed, ConfigParams.down_max_speed_with_goods)

            self.max_speed = max_speed
            # Motor.setMotorSpeed(self.motor_name,0.06,5)

            Motor.setMotorPosition(self.motor_name, self.position, self.max_speed, self.stop_di)
        # pos = Motor.get_motor_pos(self.motor_name)

        if Motor.isMotorReached(ConfigParams.fork_motor_name):
            self.action_status = ActionStatus.FINISHED

        # 检测货叉的运动是否卡住了
        now = time.time()
        # 0.5s 采一次数据，50ms过于频繁似乎没有必要
        if now - self.last_sample_time > 0.5:
            self.last_sample_time = now
            self.positions.append(cur_fork_height)
            self.fork_timestamps.append(now)

            if self.fork_timestamps and now - self.fork_timestamps[0] >= self.check_duration:
                min_pos = min(self.positions)
                max_pos = max(self.positions)
                if abs(max_pos - min_pos) <= 0.005:
                    Abnormal.setTask(53312,
                                     f"fork height not change between:{min_pos}m-{max_pos}m in {self.check_duration}s",
                                     "", "", "")
                    self.action_status = ActionStatus.FAILED
                    return

            while self.fork_timestamps and now - self.fork_timestamps[0] > self.check_duration:
                self.positions.pop(0)
                self.fork_timestamps.pop(0)

        # self.action_state["motor_name"] = self.motor_name
        # self.action_state["motor_speed"] = Motor.get_motor_speed(self.motor_name)
        # self.action_state["motor_position"] = Motor.get_motor_pos(self.motor_name)
        # self.action_state["status"] = self.action_status
        # Trace.log(self.action_state)
        # print(json.dumps(self.action_state))

    def reset(self):
        Motor.resetMotor(self.motor_name)
        self.action_status = ActionStatus.RUNNING
        self.fork_timestamps.clear()
        self.positions.clear()
        self.init = False


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

    def run(self):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            Motor.setMotorSpeed(self.motor_name, self.max_speed, self.stop_di)
        if Motor.isMotorReached(self.motor_name):
            self.action_status = ActionStatus.FINISHED

    def reset(self):
        self.action_status = ActionStatus.INIT
        Motor.resetMotor(self.motor_name)


class RunMotorByDOInterlock(BaseAction):
    """
    功能说明：控制DO电机运动，采用interlock方式，up_di/down_di触发时结束运动,超过延时时间自动停止
    """

    def __init__(self, operation, pump_do, leak_do, up_di, down_di, up_delay_time=5.0, down_delay_time=5.0):
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
        self.pump_do = pump_do
        self.leak_do = leak_do
        self.up_di = up_di
        self.down_di = down_di
        self.up_delay_time = up_delay_time
        self.down_delay_time = down_delay_time
        self.start_time = 0
        self.action_state = dict()

    def run(self):
        if not self.init:
            self.action_status = ActionStatus.RUNNING
            self.init = True
            self.start_time = time.time()
            self.reset()

        if self.is_reached():
            Do.setDO(self.pump_do, False)
            Do.setDO(self.leak_do, False)
            self.action_status = ActionStatus.FINISHED
            return

        if self.operation == "up":
            Do.setDO(self.pump_do, True)
            Do.setDO(self.leak_do, False)
        elif self.operation == "down":
            Do.setDO(self.pump_do, False)
            Do.setDO(self.leak_do, True)

        #
        # self.action_state['action_name'] = self.__class__.__name__
        # self.action_state["action_runtime"] = time.time() - self.start_time
        # self.action_state["up_or_down_operation"] = self.operation
        # self.action_state["positive_do"] = self.positive_do
        # self.action_state["negative_do"] = self.negative_do
        # self.action_state["up_di"] = self.up_di
        # self.action_state['down_di'] = self.down_di
        # self.action_state['status'] = self.action_status

    def is_reached(self):
        is_reach = False
        if self.operation == "up":
            up_di_status = Di.get_di(self.up_di)
            if up_di_status:
                is_reach = True
            if time.time() - self.start_time > self.up_delay_time:
                is_reach = True
        elif self.operation == "down":
            down_di_status = Di.get_di(self.down_di)
            if down_di_status:
                is_reach = True
            if time.time() - self.start_time > self.down_delay_time:
                is_reach = True
        return is_reach

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        Do.setDO(self.leak_do, False)
        Do.setDO(self.pump_do, False)


# 用于走直线
class GoPath(BaseAction):
    def __init__(self, args: Optional[dict] = None):
        super().__init__("GoPath")
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

    def run(self):
        self.action_status = ActionStatus.RUNNING
        args = self.args
        if args is None:
            args = Module.get_task_args()
        if Abnormal.exists(52111):
            self.action_status = ActionStatus.FAILED

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

                Trace.log(f"goal: {str(self.goal)}")
                if args["coordinate"] == "robot":
                    Navigation.setPathOnRobot([0, self.goal[0]], [0, self.goal[1]], self.goal[2])
                elif args["coordinate"] == "world":
                    x = Loc.get_pose()["x"]
                    y = Loc.get_pose()["y"]
                    Navigation.setPathOnWorld([x, self.goal[0]], [y, self.goal[1]], self.goal[2])
                else:
                    Abnormal.setTask(53326, f"coordinate only support robot and world. Input is {args["coordinate"]}",
                                     "wrong coordinate", "", "")
                    self.action_status = ScriptStatus.FAILED

            else:
                Abnormal.setTask(53318,
                                 f"args wrong",
                                 f"no x or y or coordinate",
                                 "input 'x' , 'y' and 'coordinate'",
                                 "GoPath")
                self.action_status = ActionStatus.FAILED
            Navigation.goPathParam(self.param)

        if self.action_status != ActionStatus.FAILED:
            print(f"is reach:{Navigation.isPathReached()}")
            if Navigation.isPathReached():
                self.action_status = ActionStatus.FINISHED
            else:
                self.action_status = ActionStatus.RUNNING

    def reset(self):
        Navigation.resetPath()
        self.action_status = ActionStatus.RUNNING
        self.init = False


class GoTwoStraightLine:
    def __init__(self, world_target, min_ahead_dist, ahead_dist, back_dist, speed, max_angle, dec_dist,
                 return_back=False):
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
        self.return_back = return_back
        pos = Loc.get_pose()
        if not self.return_back:
            self.start_pos = [pos['x'], pos['y'], math.radians(pos['yaw'])]
            if abs(self.cal_angle(self.start_pos, self.second_point)) > self.max_angle:
                self.start_pos[2] = self.world_target[2]
                angle, self.temp_start = self.search_min_angle_str(self.max_angle, self.step)
            else:
                self.temp_start = self.start_pos
            ScriptData.set('goTwoStraightLine',
                           {'points': [self.start_pos, self.temp_start, self.second_point, self.world_target]})
        else:
            points = ScriptData.get('goTwoStraightLine').get('points', [])
            if not points:
                self.action_status = ActionStatus.FAILED
                Abnormal.setTask(53324, "no route before leave loc, scirpt failed",
                                 "rec and goStraightLine first",
                                 "rec and goStraightLine first", "")

            self.temp_start = points[2]  # 退出库位的第一个点，栈板 min_ahead_dist 前置点
            self.second_point = points[1]  # 退出库位第二个点，ahead_dist 点
            self.second_point = points[0]  # 退出库位第三个点，前置点
            check_point = points[3]
            dist = math.sqrt((check_point[0] - pos['x']) ** 2 + (check_point[1] - pos['x']) ** 2)
            if dist >= 0.5:
                Abnormal.setTask(53325, "cannot leave loc when robot is not at last load point",
                                 f"too far:{dist}m", "", "")
                self.action_status = ActionStatus.FAILED
            ScriptData.set('goTwoStraightLine', {})

    def run(self):
        if not self.init:
            self.init = True
            if not self.return_back:
                go1_args = {
                    "x": self.temp_start[0],
                    "y": self.temp_start[1],
                    "theta": self.temp_start[2],
                    "backMode": 0,
                    "maxSpeed": 0.2,
                    "maxRot": math.radians(10),
                    "coordinate": Coordinate.WORLD
                }
                go2_args = {
                    "x": self.second_point[0],
                    "y": self.second_point[1],
                    "theta": self.second_point[2],
                    "backMode": 1,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(10),
                    "coordinate": Coordinate.WORLD
                }
                go3_args = {
                    "x": self.third_point[0],
                    "y": self.third_point[1],
                    "theta": self.third_point[2],
                    "backMode": 1,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(10),
                    "coordinate": Coordinate.WORLD
                }
            else:
                go1_args = {
                    "x": self.temp_start[0],
                    "y": self.temp_start[1],
                    "theta": self.temp_start[2],
                    "backMode": 0,
                    "maxSpeed": 0.2,
                    "maxRot": math.radians(10),
                    "coordinate": Coordinate.WORLD
                }
                go2_args = {
                    "x": self.second_point[0],
                    "y": self.second_point[1],
                    "theta": self.second_point[2],
                    "backMode": 0,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(10),
                    "coordinate": Coordinate.WORLD
                }
                go3_args = {
                    "x": self.third_point[0],
                    "y": self.third_point[1],
                    "theta": self.third_point[2],
                    "backMode": 0,
                    "maxSpeed": 0.1,
                    "maxRot": math.radians(10),
                    "coordinate": Coordinate.WORLD
                }
            self.go1 = GoPath(go1_args)
            self.go2 = GoPath(go2_args)
            self.go3 = GoPath(go3_args)

        if not self.go_step[0]:
            if self.go1.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go1.run()
            if self.go1.action_status == ActionStatus.FINISHED:
                self.go_step[0] = True
        elif self.go_step[0] and not self.go_step[1]:
            if self.go2.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go2.run()
            if self.go2.action_status == ActionStatus.FINISHED:
                self.go_step[1] = True
        elif self.go_step[1] and not self.go_step[2]:
            if self.go3.action_status not in [ActionStatus.FINISHED, ActionStatus.FAILED]:
                self.go3.run()
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
        Trace.log(f"未满足角度要求，当前角度：{angle:.2f}°")
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

    validated_params = {}
    validator = ParamValidator(InputParams.builder.to_dict())
    checked_args = False

    f = Fork()

    # time.sleep(5)

    while True:
        # print(f"event_modbus_before:{f.event_modbus}")

        if f.event_safe_move_check:
            f.safe_move_check()
        if f.event_modbus:
            validated_params = f.modbus()
        # print(f"event_modbus_after:{f.event_modbus}")

        f.period_run()

        # 任务开始时，盛哥会将状态置为 running，并传入任务参数
        input_params = validated_params or Module.get_task_args()
        status = Module.get_status()
        print(f"status: {status}")

        if status == ScriptStatus.RUNNING:
            args = {}
            if not checked_args:
                checked_args = True
                f.reset()
                try:
                    # 验证参数
                    args = validator.validate(input_params)
                    Trace.log(f"check ok, args:{json.dumps(args, indent=2)}")
                except ValueError as e:
                    Trace.log(f"check error:f{e}")

            if f.script_status in [ScriptStatus.FINISHED, ScriptStatus.FAILED] and checked_args:
                keys_to_delete = [k for k in f.trace_chart if k.startswith("action.")]
                for k in keys_to_delete:
                    del f.trace_chart[k]
                Module.set_status(f.script_status)
                checked_args = False
                validated_params = {}
                # f.reset()   # 我为啥要初始化所有的参数
            f.run(args)

        time.sleep(0.1)


if __name__ == '__main__':
    main()
