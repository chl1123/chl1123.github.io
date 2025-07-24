import math
import json
import random
import time
import uuid

start_time = time.time()
from syspy.utils.time import Timer
from syspy import Module, Logger, Di, Do, Motor, Navigation, ScriptStatus, Abnormal, Controller, Odometer, Recognize
from syspy.bin import Container
from syspy.utils.param_server import ParamBuilder, ParamType, ParamServer, ParamValidator
from tasks.standard.goPath import GoPath
from syspy.lib.net_protocol import NetProtocol

log = Logger("ContainerRobot")


class ConfigParams:
    p = ParamServer(__file__)
    # 超时参数
    timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                          group="script", comment="运行超时时间")
    # 背篓层高参数
    low = dict()
    high = dict()
    low[0] = p.loadParam("low0", type="float", default=0.4, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第0层背篓取料箱高度, 最低层, 从0计数")
    high[0] = p.loadParam("high0", type="float", default=0.41, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第0层背篓放料箱高度, 最低层, 从0计数")
    low[1] = p.loadParam("low1", type="float", default=0.82, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第1层背篓取料箱高度")
    high[1] = p.loadParam("high1", type="float", default=0.83, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第1层背篓放料箱高度")
    low[2] = p.loadParam("low2", type="float", default=1.25, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第2层背篓取料箱高度")
    high[2] = p.loadParam("high2", type="float", default=1.26, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第2层背篓放料箱高度")
    low[3] = p.loadParam("low3", type="float", default=1.675, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第3层背篓取料箱高度")
    high[3] = p.loadParam("high3", type="float", default=1.68, maxValue=10000.0, minValue=0.0, unit="m",
                          comment="第3层背篓放料箱高度")
    low[4] = p.loadParam("low4", type="float", default=2.095, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第4层背篓取料箱高度")
    high[4] = p.loadParam("high4", type="float", default=2.10, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第4层背篓放料箱高度")
    low[5] = p.loadParam("low5", type="float", default=2.515, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第5层背篓取料箱高度")
    high[5] = p.loadParam("high5", type="float", default=2.525, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第5层背篓放料箱高度")
    low[6] = p.loadParam("low6", type="float", default=2.945, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第6层背篓取料箱高度")
    high[6] = p.loadParam("high6", type="float", default=2.955, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第6层背篓放料箱高度")
    low[7] = p.loadParam("low7", type="float", default=3.375, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第7层背篓取料箱高度")
    high[7] = p.loadParam("high7", type="float", default=3.385, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第7层背篓放料箱高度")
    low[8] = p.loadParam("low8", type="float", default=3.825, maxValue=10000.0, minValue=0.0, unit="m",
                         group="trays", comment="第8层背篓取料箱高度")
    high[8] = p.loadParam("high8", type="float", default=3.835, maxValue=10000.0, minValue=0.0, unit="m",
                          group="trays", comment="第8层背篓放料箱高度")
    # 伸缩参数
    stretch_self_length = p.loadParam("stretch_self_length", type="float", default=0.73, maxValue=10000.0,
                                      group="stretch", minValue=0.0, unit="m",
                                      comment="取放自身背篓货物时伸出长度")
    # 识别偏移参数
    rec_offz_box = p.loadParam("rec_offz_box", type="float", default=-0.08, maxValue=1000.0, minValue=-1000.0,
                               group="recognize", unit="m", comment="识别料箱码后抓取料箱时调整高度")
    rec_offz_shelf = p.loadParam("rec_offz_shelf", type="float", default=0.02, maxValue=1000.0,
                                 minValue=-1000.0, group="recognize", unit="m",
                                 comment="识别货架码后放置料箱时调整高度")
    # DI参数
    fork_up_limit = p.loadParam("fork_up_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                group="lift", comment="货叉上限位DI")
    fork_down_limit = p.loadParam("fork_down_limit", type="int", default=2, maxValue=100, minValue=-1, unit="",
                                  group="lift", comment="货叉下限位DI")
    fork_limit = p.loadParam("fork_limit", type="int", default=3, maxValue=100, minValue=-1, unit="",
                             group="lift", comment="货叉升降机械限位限位DI")
    # 高度限制参数
    min_lift_height = p.loadParam("min_fork_height", type="float", default=0.38, maxValue=10000.0,
                                  minValue=0.0, unit="m", comment="货叉最低高度")
    max_lift_height = p.loadParam("max_fork_height", type="float", default=4.5, maxValue=10000.0,
                                  group="lift", minValue=0.0, unit="m", comment="货叉最大高度")
    # 角度限制参数
    max_rotate_angle = p.loadParam("max_rotate_angle", type="float", default=100,
                                   group="rotate", comment="货叉最大旋转角度值")
    # 伸缩限制参数
    max_stretch_length = p.loadParam("max_stretch_length", type="float", default=0.90, unit="m",
                                     group="stretch", comment="货叉最大伸出长度")
    safe_stretch_length = p.loadParam("safe_stretch_length", type="float", default=0.05, maxValue=10000.0,
                                      group="stretch", minValue=0.0, unit="m",
                                      comment="货叉升降、旋转操作时伸缩臂安全长度")
    # 安全高度参数
    safe_lift_height = p.loadParam("safe_lift_height", type="float", default=1.0, maxValue=10000.0,
                                   group="lift", minValue=0.0, unit="m",
                                   comment="货叉安全高度, 货叉导航过程中的最高高度")
    # 传感器参数
    has_fork_sensor = p.loadParam("has_fork_sensor", type="int", default=0,
                                  group="DI", comment="货叉是否有货物检测传感器，1为有，0为无")
    has_tray_sensor = p.loadParam("has_tray_sensor", type="int", default=0,
                                  group="DI", comment="背篓是否有货物检测传感器，1为有，0为无")
    fork_sensor_di = p.loadParam("fork_sensor_di", type="int", default=9, maxValue=100, minValue=-1, unit="",
                                 group="DI", comment="货叉检测DI")
    overlimit_detect_di = p.loadParam("overlimit_detect_di", type="int", default=-1,
                                      group="DI", comment="检测货叉伸出是否超过料箱的DI")
    # 识别文件参数
    box_code_file = p.loadParam("box_code_file", type="str", default="default.srec",
                                group="recognize", comment="料箱二维码识别文件")
    shelf_code_file = p.loadParam("shelf_code_file", type="str", default="default.srec",
                                  group="recognize", comment="货架二维码识别文件")
    barcode_file = p.loadParam("barcode_file", type="str", default="default.srec",
                               group="recognize", comment="条形码识别文件")
    # 电机速度参数
    lift_motor_speed = p.loadParam("lift_motor_speed", type="float", default=1.5,
                                   group="lift", comment="升降电机运转速度")
    stretch_motor_speed = p.loadParam("stretch_motor_speed", type="float", default=1.0,
                                      group="stretch", comment="伸缩电机运转速度")
    rotate_motor_speed = p.loadParam("rotate_motor_speed", type="float", default=1.0,
                                     group="rotate", comment="旋转电机运转速度")
    # 电机名称参数
    lift_motor_name = p.loadParam("lift_motor_name", type="str", default="Motor-003",
                                  group="lift", comment="升降电机名称")
    stretch_motor_name = p.loadParam("stretch_motor_name", type="str", default="Motor-000",
                                     group="stretch", comment="伸缩电机名称")
    rotate_motor_name = p.loadParam("rotate_motor_name", type="str", default="Motor-004",
                                    group="rotate", comment="旋转电机名称")
    # 自动计算参数
    auto_stretch_box_len = p.loadParam("auto_stretch_box_len", type="float", default=0.6, maxValue=100,
                                       group="stretch", minValue=-1, unit="", comment="箱子长度")
    auto_load_stretch_dist = p.loadParam("auto_load_stretch_dist", type="float", default=0.01,
                                         group="stretch", unit="m", comment="自动计算取货伸出长度时的补偿值")
    auto_unload_stretch_dist = p.loadParam("auto_unload_stretch_dist", type="float", default=0.01,
                                           group="stretch", unit="m", comment="自动计算放货伸出长度时的补偿值")
    auto_stretch_odo_len = p.loadParam("auto_stretch_odo_len", type="float", default=0.38, maxValue=100,
                                       group="stretch", minValue=20, unit="",
                                       comment="手指机构到货叉旋转中心的距离")
    auto_adjust_rotate = p.loadParam("auto_adjust_rotate", type="int", default=1,
                                     group="rotate", comment="识别时是否需要自动调整货叉角度，1：需要 0：不需要")
    # 识别补偿参数
    offset_x = p.loadParam("offset_x", type="float", default=0.,
                           group="recognize", comment="针对识别结果误差在x方向的补偿值")
    light_delay_time = p.loadParam("light_delay_time", type="float", default=0.3,
                                   group="recognize", comment="补光灯延时拍照时间")
    load_rec_lift_diff = p.loadParam("load_rec_lift_diff", type="float", default=0.05,
                                     group="recognize", comment="取货识别料箱高度与货架上表面的高度差")
    rec_box_extra_height = p.loadParam("rec_box_extra_height", type="float", default=0.0,
                                       comment="放货识别货架上是否有货物时，在放货高度上需要额外抬升的高度，该值可设置为货架码到料箱码的高度差")

    # 识别微调参数
    ok_x = p.loadParam("ok_x", type="float", default=0.01,
                       comment="x方向行走调整完成阈值")
    ok_yaw = p.loadParam("ok_yaw", type="float", default=0.015,
                         comment="调整完成弧度阈值")
    max_yaw_bias = p.loadParam("max_yaw_bias", type="float", default=0.13,
                               comment="货叉与料箱角度最大偏差, 弧度值")


class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        with builder.CHILD(key="finger", name="finger", desc="手指"):
            builder.TYPE(ParamType.INT)
            builder.REQUIRED(False)
            builder.DEFAULTVALUE(0)

        with builder.CHILD(key="lift", name="Lift", desc="升降高度"):
            builder.MIN_VALUE(0)
            builder.MAX_VALUE(100)
            builder.TYPE(ParamType.FLOAT)
            builder.REQUIRED(False)
            builder.UNIT("m")
            builder.DEFAULTVALUE(0)  # 1.1

        with builder.CHILD(key="rotate", name="Rotate", desc="旋转角度"):
            builder.MIN_VALUE(-100)
            builder.MAX_VALUE(100)
            builder.TYPE(ParamType.DOUBLE)
            builder.REQUIRED(False)
            builder.UNIT("rad")
            builder.DEFAULTVALUE(0)  # -1.57

        with builder.CHILD(key="stretch", name="Stretch", desc="伸缩机构长度"):
            builder.MIN_VALUE(-100)
            builder.MAX_VALUE(100)
            builder.TYPE(ParamType.FLOAT)
            builder.REQUIRED(False)
            builder.UNIT("m")
            builder.DEFAULTVALUE(0)

        with builder.CHILD(key="modbus_ip", name="Modbus IP", desc="Modbus TCP IP"):
            builder.TYPE(ParamType.IP)
            builder.DEFAULTVALUE("192.168.192.6")

        with builder.CHILD(key="visionType", name="visionType", desc="visionType"):
            builder.TYPE(ParamType.STRING)
            builder.DEFAULTVALUE("box")

        with builder.GROUP(key="operation", name="Operation", desc="机构动作选项"):
            builder.TYPE(ParamType.COMBO_BOX)
            with builder.CHILDREN():
                with builder.CHILD(key="rec_qrcode", name="Rec_Qrcode", desc="识别二维码"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="none", name="none", desc="空"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="zero", name="Zero", desc="机构回零"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="load", name="Load", desc="取货"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="unload", name="Unload", desc="放货"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="rec_box_barcode", name="Rec_Box_Barcode", desc="识别料箱一维码"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="take_photo", name="Take_Photo", desc="拍照"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="in_take", name="In_Take", desc="内部取货"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="in_put", name="In_Put", desc="内部放货"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="ex_take", name="Ex_Take", desc="外部取货"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="ex_put", name="Ex_Put", desc="外部放货"):
                    builder.TYPE(ParamType.ARRAY)
    builder.save_to_file()


class ContainerRobot:
    def __init__(self, args=None):
        super().__init__()
        self.offset_x = None
        self.goods_manger = Container()
        self.rec_box = None
        self.stretch_motor_stop = None
        self.rotate_motor_stop = None
        self.lift_motor_stop = None
        self.cur_c = None
        self.start_time = time.time()
        self.goods_id = ""
        self.lift_height = None
        self.door_height = None
        self.stretch_length = None
        self.is_auto_stretch = None
        self.rotate_pos = None
        self.finger_pos = None
        self.self_position = None
        self.lift_status = None
        self.left_finger_real_pos = -1
        self.right_finger_real_pos = -1
        self.finger_info = dict()
        self.stretch_status = None
        self.stretch_real_pos = 0
        self.lift_real_pos = 0
        self.rotate_real_pos = 0
        self.load_height = 0
        self.unload_height = 0
        self.rec_height_diff = 0

        # 手指控制DO
        self.left_finger_up_do = 9  # di1
        self.right_finger_up_do = 7  # di6
        self.right_finger_down_do = 6  # di5
        self.left_finger_down_do = 8  # di4
        # 手指到位DI
        self.left_finger_up_di = 4
        self.left_finger_down_di = 1
        self.right_finger_up_di = 5
        self.right_finger_down_di = 6

        self.fill_light_do = 4  # 补光灯DO
        self.collision_di = 0  # 碰撞条DI
        self.light_st_time = None

        self.lift_zero_di = 8
        self.stretch_limit = 10
        self.rotate_limit = 7
        self.target_type = None
        self.code_type = None
        self.barcode_height = None
        self.rec = None
        self.rec_adjust = None
        self.rotate_status = None
        self.operation = None
        self.containers = None

        self.load_step = [False] * 16
        self.unload_step = [False] * 16
        self.change_step = [False] * 10
        self.rec_box_lift_step = [False] * 5
        self.zero_step = [False] * 4
        self.calib_step = [False] * 3
        self.opt_step = [False] * 10
        self.yaw_adjust = 0
        self.rec_res = None
        self.rec_id = None
        self.rec_box_lift = None
        self.finger_open_start = False
        self.pre_finger = None

        self.in_take_step = [False] * 20
        self.ex_take_step = [False] * 20
        self.in_put_step = [False] * 20
        self.ex_put_step = [False] * 20

        self.lift_motor_calib = None
        self.stretch_motor_calib = None
        self.rotate_motor_calib = None

        self.set_lift_motor_calib = False
        self.set_stretch_motor_calib = False
        self.set_rotate_motor_calib = False
        self.motor_calib_state = False
        self.motor_calib_info = {}
        self.enable_motor = False
        self.send_enable_motor_count = 0
        self.enable_motor_time = time.time()

        self.lift_ok = False
        self.rotate_ok = False
        self.status = ScriptStatus.NONE
        self.report_info = {}
        self.motor_info = {}

        self.box_code_file = ConfigParams.box_code_file
        self.shelf_code_file = ConfigParams.shelf_code_file

        self.goPath = GoPath()
        self.args = args or {}
        Motor.resetMotor(ConfigParams.lift_motor_name)
        self.__init_args(self.args)

    def __init_args(self, args):
        self.goods_id = args.get("goodsId", "")
        self.self_position = args.get("container", self.self_position)
        self.self_position = str(self.self_position) if self.self_position is not None else self.self_position
        self.update_move_task_params()
        self.finger_pos = args.get("finger", 0)
        self.lift_height = args.get("lift", 0)
        self.stretch_length = args.get("stretch", 0)
        self.is_auto_stretch = bool("stretch" not in args)  # 输入参数无"stretch"，则自动计算识别长度
        self.rotate_pos = args.get("rotate", 0)
        self.rec_box_lift = args.get("recBoxLift", 0)
        self.offset_x = args.get("offset_x", ConfigParams.offset_x)
        self.pre_finger = args.get("pre_finger", self.pre_finger)
        if self.rec_box_lift:
            self.rec_box = Rec(ConfigParams.box_code_file, max_rec_times=1)
        self.code_type = args.get("visionBinType", "code")
        self.target_type = args.get("visionType", None)
        self.barcode_height = args.get("barcodeHeight", None)
        self.operation = args.get("operation", None)
        self.load_height = args.get("loadHeight", ConfigParams.rec_offz_box)
        self.unload_height = args.get("unloadHeight", ConfigParams.rec_offz_shelf)
        self.self_position = args.get("container", self.self_position)
        self.self_position = str(self.self_position) if self.self_position else self.self_position
        self.rec_id = uuid.uuid4().hex
        self.box_code_file = args.get("code_file", self.box_code_file)
        self.shelf_code_file = args.get("shelf_code_file", self.shelf_code_file)
        if "recAdjust" in args:
            if self.target_type is None:
                if self.operation == "load" or self.operation == "ex_take":
                    self.rec_adjust = RecAdjust(self.box_code_file)
                elif self.operation == "unload" or self.operation == "ex_put":
                    self.rec_adjust = RecAdjust(self.shelf_code_file)
            elif self.target_type == "box":
                self.rec_adjust = RecAdjust(self.box_code_file)
            elif self.target_type == "shelf":
                self.rec_adjust = RecAdjust(self.shelf_code_file)
        if self.target_type == "box" and self.code_type == "code":
            self.rec = Rec(ConfigParams.box_code_file)
        elif self.target_type == "shelf" and self.code_type == "code":
            self.rec = Rec(ConfigParams.shelf_code_file)

    def run(self):
        Module.set_status(ScriptStatus.RUNNING)
        self.check_motor_emc()  # 检测控制器及驱动器急停状态
        if self.enable_motor and not self.motor_calib_state:  # 使能成功, 且未标零, 则标零
            self.motor_calib()

        if time.time() - self.start_time > ConfigParams.timeout:
            Abnormal.setTask(53000, f"脚本任务运行超时，请重新执行任务！", "", "", "")
            Module.set_status(ScriptStatus.FAILED)
        self.update_report_info()
        if self.motor_calib_state:
            operation = self.operation
            if operation != 'none':
                if operation == 'zero':
                    if self.zero():
                        Module.set_status(ScriptStatus.FINISHED)
                elif operation == 'load':
                    if self.load():
                        Module.set_status(ScriptStatus.FINISHED)
                elif operation == 'unload':
                    if self.unload():
                        Module.set_status(ScriptStatus.FINISHED)
                elif operation == 'rec_box_barcode':
                    self.rec_box_barcode()
                elif operation == 'rec_qrcode':
                    self.rec_qrcode()
                elif operation == 'take_photo':
                    self.take_photo()
                elif operation == 'in_take':
                    if self.in_take():
                        Module.set_status(ScriptStatus.FINISHED)
                elif operation == 'in_put':
                    if self.in_put():
                        Module.set_status(ScriptStatus.FINISHED)
                elif operation == 'ex_take':
                    if self.ex_take():
                        Module.set_status(ScriptStatus.FINISHED)
                elif operation == 'ex_put':
                    if self.ex_put():
                        Module.set_status(ScriptStatus.FINISHED)
                else:
                    Abnormal.setTask(53000, f"不支持的操作类型: {operation}", "", "", "")
                    Module.set_status(ScriptStatus.FAILED)
            else:
                # 处理非操作类型的参数（原有逻辑保持不变）
                if "finger" in self.args:
                    if self.finger(self.finger_pos):
                        self.update_finger_info()
                        Module.set_status(ScriptStatus.FINISHED)
                elif "lift" in self.args or "rotate" in self.args:
                    if "lift" in self.args and not self.lift_ok:
                        self.lift_ok = self.lift(self.lift_height)
                    else:
                        self.lift_ok = True
                    if "rotate" in self.args and not self.rotate_ok:
                        self.rotate_ok = self.rotate(self.rotate_pos)
                    else:
                        self.rotate_ok = True
                    if self.lift_ok and self.rotate_ok:
                        Module.set_status(ScriptStatus.FINISHED)
                elif "stretch" in self.args:
                    if self.stretch(self.stretch_length):
                        Module.set_status(ScriptStatus.FINISHED)
                elif "visionType" in self.args:
                    if self.code_type == "barcode":
                        if self.rec_barcode():
                            Module.set_status(ScriptStatus.FINISHED)
                    elif self.code_type == "code":
                        if self.rec_qrcode():
                            Module.set_status(ScriptStatus.FINISHED)
        self.update_report_info()
        self.report_info["runtime"] = {
            'script_start_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time)),
            'script_running_time': time.time() - self.start_time,
            'script_args': self.args,
            'motor_calib_info': self.motor_calib_info,
            'task_status': self.status,
            'goods_id': self.goods_id,
            'self_position': self.self_position,
            'containers': self.containers,  # 包含 containers
            'motor_info': self.motor_info,
            'current_pos': {  # 来自 update_report_info()
                'lift': round(self.lift_real_pos, 3),
                'stretch': round(self.stretch_real_pos, 3),
                'rotate': round(self.rotate_real_pos * 180 / math.pi, 3),
                'left_finger': self.left_finger_real_pos,
                'right_finger': self.right_finger_real_pos
            }
        }
        log.debug(self.report_info)
        Module.report_info(self.report_info)
        return self.status

    @staticmethod
    def get_motor_info(motor_name: str):
        motor_data = Odometer.get_data().get("motorInfo", [])
        for _motor in motor_data:
            if _motor.get('motorName') == motor_name:
                return _motor
        return {}

    def check_motor_emc(self):
        """
        检测急停状态, 驱动器上使能
        """
        controller_emc = Controller.get_emc()
        lift_motor_info = self.get_motor_info(ConfigParams.lift_motor_name)  # 能查询到电机数据,说明驱动器已供电
        stretch_motor_info = self.get_motor_info(ConfigParams.stretch_motor_name)
        rotate_motor_info = self.get_motor_info(ConfigParams.rotate_motor_name)
        lift_motor_emc = lift_motor_info.get("emc", False)
        stretch_motor_emc = stretch_motor_info.get("emc", False)
        rotate_motor_emc = rotate_motor_info.get("emc", False)

        self.motor_calib_info["lift_motor_emc"] = lift_motor_emc
        self.motor_calib_info["stretch_motor_emc"] = stretch_motor_emc
        self.motor_calib_info["rotate_motor_emc"] = rotate_motor_emc
        self.motor_calib_info["controller_emc"] = controller_emc

        self.enable_motor = not lift_motor_emc and not rotate_motor_emc and not stretch_motor_emc  # 驱动器使能状态
        if not controller_emc and time.time() - self.enable_motor_time > 0.5:  # 控制器未急停
            self.enable_motor_time = time.time()
            if Abnormal.getNum() == 0:
                if lift_motor_info and lift_motor_emc:  # 控制器未急停但是驱动器急停，给电机上使能
                    Motor.enableMotor(ConfigParams.lift_motor_name)
                    self.report_info["lift_motor_info"] = lift_motor_info
                if stretch_motor_info and stretch_motor_emc:
                    Motor.enableMotor(ConfigParams.stretch_motor_name)
                    self.report_info["stretch_motor_info"] = stretch_motor_info
                if rotate_motor_info and rotate_motor_emc:
                    Motor.enableMotor(ConfigParams.rotate_motor_name)
                    self.report_info["rotate_motor_info"] = rotate_motor_info

    def motor_calib(self):
        self.get_motor_calib_state()
        if not self.motor_calib_state:
            if not self.calib_step[0]:
                if not self.set_stretch_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    Motor.motorCalib(ConfigParams.stretch_motor_name)
                    self.set_stretch_motor_calib = True

            elif self.calib_step[0] and not self.calib_step[1]:
                if not self.set_lift_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    Motor.motorCalib(ConfigParams.lift_motor_name)
                    self.set_lift_motor_calib = True

            elif self.calib_step[1] and not self.calib_step[2]:
                if not self.set_rotate_motor_calib and self.lift_motor_stop and self.rotate_motor_stop and self.stretch_motor_stop:
                    Motor.motorCalib(ConfigParams.rotate_motor_name)
                    self.set_rotate_motor_calib = True

            if Abnormal.exists(54305):
                # 检测由车体抖动引起的标零失败，重置标志位，重新下发标零指令
                self.set_lift_motor_calib = False
                self.set_rotate_motor_calib = False
                self.set_stretch_motor_calib = False
                Abnormal.clear(54305)

            self.calib_step[0] = self.stretch_motor_calib
            self.calib_step[1] = self.lift_motor_calib
            self.calib_step[2] = self.rotate_motor_calib

    def get_motor_calib_state(self):
        self.motor_info = Odometer.get_data().get("motorInfo", [])
        for m_f in self.motor_info:
            if m_f.get("motorName") == ConfigParams.lift_motor_name:
                self.lift_motor_calib = m_f.get("calib")
                self.lift_motor_stop = m_f.get("stop", None)
            if m_f.get("motorName") == ConfigParams.stretch_motor_name:
                self.stretch_motor_calib = m_f.get("calib")
                self.stretch_motor_stop = m_f.get("stop", None)
            if m_f.get("motorName") == ConfigParams.rotate_motor_name:
                self.rotate_motor_calib = m_f.get("calib")
                self.rotate_motor_stop = m_f.get("stop", None)
        self.motor_calib_state = self.lift_motor_calib and self.stretch_motor_calib and self.rotate_motor_calib

        self.motor_calib_info['all_motor_enable'] = self.enable_motor
        self.motor_calib_info['all_motor_calib'] = self.motor_calib_state
        self.motor_calib_info['rotate_motor_calib'] = self.rotate_motor_calib
        self.motor_calib_info['stretch_motor_calib'] = self.stretch_motor_calib
        self.motor_calib_info['lift_motor_calib'] = self.lift_motor_calib

    def cancel(self):
        Recognize.resetRec()
        self.close_finger()
        Do.setDO(self.fill_light_do, False)
        Module.set_status(ScriptStatus.NONE)

    def update_move_task_params(self):
        """
        获取moveTask参数
        """
        move_task = Navigation.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsId':
                self.goods_id = p['string_value']
            if p['key'] == '#containerName' and p['string_value'] != "":
                self.self_position = p['string_value']

    def zero(self):
        """
        机构复位
        """
        log.info(f"----- running zero ------")
        if not self.zero_step[0]:
            # Di_1 = Di.get_di(self.left_finger_up_di) and Di.get_di(self.right_finger_up_di)
            # if Di_1:
            self.zero_step[0] = True
        elif self.zero_step[0] and not self.zero_step[1]:
            self.zero_step[1] = self.stretch(0)
        elif self.zero_step[1] and not self.zero_step[2]:
            self.zero_step[2] = self.rotate(0)
            self.zero_step[3] = self.lift(0)
        elif self.zero_step[2] and not self.zero_step[3]:
            self.zero_step[3] = self.lift(0)
        log.debug(f"zero_step:{self.zero_step}")
        if all(self.zero_step):
            return True
        return False

    def lift(self, height):
        log.info(f"----- running lift ------")
        if height < ConfigParams.min_lift_height:
            height = ConfigParams.min_lift_height
        if height > ConfigParams.max_lift_height:
            Abnormal.setTask(53000, f"下发升降高度超上限，最大值：{ConfigParams.max_lift_height}，下发值：{height}", "", "",
                             "")
            Module.set_status(ScriptStatus.FAILED)
            return False
        if self.stretch_real_pos > ConfigParams.safe_stretch_length:
            Abnormal.setTask(53000, f"检测到伸缩机构未回零，无法执行升降，请先执行标零复位！", "", "", "")
            Module.set_status(ScriptStatus.FAILED)
            return False
        Motor.setMotorPosition(ConfigParams.lift_motor_name, height, ConfigParams.lift_motor_speed, -1)
        if Motor.isMotorReached(ConfigParams.lift_motor_name):
            return True
        return False

    def finger(self, pos):
        log.info(f"----- running finger ------")
        if not self.finger_open_start:
            self.finger_open_start = time.time()
        else:
            if time.time() - self.finger_open_start > 3:  # 防止手指机构卡死时电机过流烧毁
                Abnormal.setTask(53000, f"拨指控制超时，请检查拨指是否卡住、检查拨指到位光电是否能正常触发！", "", "", "")
                Do.setDO(self.left_finger_up_do, False)
                Do.setDO(self.right_finger_up_do, False)
                Do.setDO(self.left_finger_down_do, False)
                Do.setDO(self.right_finger_down_do, False)
                Module.set_status(ScriptStatus.FAILED)
                return False
        if pos == 1:
            Do.setDO(self.left_finger_up_do, True)
            Do.setDO(self.right_finger_up_do, True)
            if Di.get_di(self.left_finger_up_di) and not Di.get_di(self.left_finger_down_di):
                self.left_finger_real_pos = 1
                Do.setDO(self.left_finger_up_do, False)
            if Di.get_di(self.right_finger_up_di) and not Di.get_di(self.right_finger_down_di):
                self.right_finger_real_pos = 1
                Do.setDO(self.right_finger_up_do, False)
            if self.left_finger_real_pos == 1 and self.right_finger_real_pos == 1:
                self.finger_open_start = False
                Module.set_status(ScriptStatus.FINISHED)
                return True
        elif pos == 0:
            if Di.get_di(ConfigParams.overlimit_detect_di):
                Abnormal.setTask(53000, f"伸出长度不够，货叉超限光电检测到障碍物！可上调取货伸出补偿参数值！", "", "", "")
                Module.set_status(ScriptStatus.FAILED)
                return False
            Do.setDO(self.left_finger_down_do, True)
            Do.setDO(self.right_finger_down_do, True)
            if Di.get_di(self.left_finger_down_di) and not Di.get_di(self.left_finger_up_di):
                Do.setDO(self.left_finger_down_do, False)
                self.left_finger_real_pos = 0
            if Di.get_di(self.right_finger_down_di) and not Di.get_di(self.right_finger_up_di):
                Do.setDO(self.right_finger_down_do, False)
                self.right_finger_real_pos = 0
            if self.left_finger_real_pos == 0 and self.right_finger_real_pos == 0:
                self.finger_open_start = False  # 重置记录拨指动作开始的时刻
                Module.set_status(ScriptStatus.FINISHED)
                return True
        return False

    def close_finger(self):
        Do.setDO(self.left_finger_up_do, False)
        Do.setDO(self.right_finger_up_do, False)
        Do.setDO(self.left_finger_down_do, False)
        Do.setDO(self.right_finger_down_do, False)

    def update_finger_info(self):
        if Di.get_di(self.left_finger_down_di) and not Di.get_di(self.left_finger_up_di):
            self.left_finger_real_pos = 0
        elif Di.get_di(self.left_finger_up_di) and not Di.get_di(self.left_finger_down_di):
            self.left_finger_real_pos = 1
        if Di.get_di(self.right_finger_down_di) and not Di.get_di(self.right_finger_up_di):
            self.right_finger_real_pos = 0
        elif Di.get_di(self.right_finger_up_di) and not Di.get_di(self.right_finger_down_di):
            self.right_finger_real_pos = 1
        self.finger_info["left_finger"] = self.left_finger_real_pos
        self.finger_info["right_finger"] = self.right_finger_real_pos

    def stretch(self, length):
        log.info(f"----- running stretch ------")
        temp_motor_speed = ConfigParams.stretch_motor_speed
        if ConfigParams.max_stretch_length < length < ConfigParams.max_stretch_length + 0.1:
            Abnormal.setTask(54000,
                             f"下发伸出长度值略微超上限，下发值：{length}，上限值：{ConfigParams.max_stretch_length}。请检查货物是否离车体太远了！",
                             "", "", "")
            length = ConfigParams.max_stretch_length
        elif length > ConfigParams.max_stretch_length + 0.1:
            Abnormal.setTask(53000,
                             f"下发伸出长度值远超上限，下发值：{length}，上限值：{ConfigParams.max_stretch_length}。请检查货物是否离车体太远了！！！",
                             "", "", "")
            Module.set_status(ScriptStatus.FAILED)
            return False

        # 手臂伸出且目标位置大于0.1m, 后半段速度减半
        if length > 0.1 and self.stretch_real_pos > length * 0.6:
            temp_motor_speed = ConfigParams.stretch_motor_speed * 0.6
        Motor.setMotorPosition(ConfigParams.stretch_motor_name, length, temp_motor_speed, -1)
        if Motor.isMotorReached(ConfigParams.stretch_motor_name):
            return True
        return False

    def rotate(self, pos, max_speed=None):
        log.info(f"----- running rotate ------")
        if abs(pos) > abs(ConfigParams.max_rotate_angle / 180 * math.pi):
            Abnormal.setTask(53000,
                             f"下发角度值超上限，下发值：{pos / math.pi * 180}，上限值：{ConfigParams.max_rotate_angle}，请检查箱子是否摆歪，二维码是否破损！",
                             "", "", "")
            Module.set_status(ScriptStatus.FAILED)
            return False

        if self.stretch_real_pos > ConfigParams.safe_stretch_length:
            Abnormal.setTask(53000, f"检测到伸缩机构未回零，无法执行旋转动作，请先执行标零复位！", "", "", "")
            Module.set_status(ScriptStatus.FAILED)
            return False

        if max_speed is not None:
            speed = max_speed
        else:
            speed = ConfigParams.rotate_motor_speed

        Motor.setMotorPosition(ConfigParams.rotate_motor_name, pos, speed, -1)
        if Motor.isMotorReached(ConfigParams.rotate_motor_name):
            return True
        return False

    def rec_barcode(self):
        """
        识别一维码
        """
        if not self.change_step[0]:
            Do.setDO(self.fill_light_do, True)
            if Do.get_do(self.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.change_step[0] = True
        else:
            if self.rec_res and self.rec_res.get("status", 1) == 0:
                Do.setDO(self.fill_light_do, False)
                if self.rec_res['barCode'] != self.goods_id:
                    Abnormal.setTask(53000,
                                     f"货物编码不匹配, 任务下发的货物编码: {self.goods_id}, 识别的货物编码: {self.rec_res['barCode']}",
                                     "", "", "")
                    Module.set_status(ScriptStatus.FAILED)
                Module.report_info({"barcode": self.rec_res['barCode']})
                return self.rec_res['barCode']
            else:
                if Timer.delay(0.05):
                    Recognize.doRec(ConfigParams.barcode_file, False, 0.0, 0.0, 0.0, 0.0)
                Module.report_info({"barcode": "None"})
            Module.report_info({"rec_id": self.rec_id})

    def rec_box_barcode(self):
        """
        指定货叉高度和角度位置识别一维码
        """
        if time.time() - self.start_time > 20:
            Abnormal.setTask(53000, f"未识别到一维码！请检查相机是否对准了一维码！", "", "", "")
            Module.set_status(ScriptStatus.FAILED)
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(self.rotate_pos)
        if self.opt_step[0] and self.opt_step[1] and not self.opt_step[2]:
            self.rec_barcode()
            if self.rec_res and self.rec_res.get("status", 1) == 0:
                Module.report_info({"barcode": self.rec_res['barCode']})
                self.opt_step[2] = True
        if all(self.opt_step[0:3]):
            Module.set_status(ScriptStatus.FINISHED)

    def rec_qrcode(self):
        """
        指定货叉高度和角度位置识别二维码
        """
        rec_qrcode_info = {}
        if time.time() - self.start_time > 20:
            Abnormal.setTask(53000, f"未识别到二维码！请检查相机是否对准了二维码！", "", "", "")
            Module.set_status(ScriptStatus.FAILED)
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(self.rotate_pos)
        if all(self.opt_step[0:2]) and not self.opt_step[2]:
            Do.setDO(self.fill_light_do, True)
            if Timer.delay(ConfigParams.light_delay_time):
                self.opt_step[2] = True
        if all(self.opt_step[0:3]) and not self.opt_step[3]:
            if self.rec.status == ScriptStatus.FINISHED:
                data = {
                    "containerRobot": {
                        "locName": Module.get_task_args().get("locName", ""),
                        "taskId": Module.get_task_args().get("taskId", ""),
                        "load": {
                            "lift": self.lift_real_pos + self.rec.result['z'] + ConfigParams.load_rec_lift_diff
                        },
                        "unload": {
                            "lift": self.lift_real_pos + self.rec.result['z']
                        }
                    }
                }
                NetProtocol.tcpUploadString(json.dumps(data))
                rec_qrcode_info["rec_qrcode_data"] = data
                self.rec.reset()
                Do.setDO(self.fill_light_do, False)
                self.opt_step[3] = True
            else:
                self.rec.run(self)
        rec_qrcode_info["opt_step"] = self.opt_step
        rec_qrcode_info["rec_info"] = self.rec.get_info()
        self.report_info["rec_qrcode_info"] = rec_qrcode_info
        if all(self.opt_step[0:4]):
            Module.set_status(ScriptStatus.FINISHED)

    def take_photo(self):
        """
        指定货叉高度和角度拍照
        """
        if not self.opt_step[0]:
            self.opt_step[0] = self.lift(self.lift_height)
        if not self.opt_step[1]:
            self.opt_step[1] = self.rotate(self.rotate_pos)

        if all(self.opt_step[0:2]) and not self.opt_step[2]:
            Do.setDO(self.fill_light_do, True)
            Recognize.resetRec()  # 重置识别模块
            if Do.get_do(self.fill_light_do):
                if Timer.delay(ConfigParams.light_delay_time):
                    self.opt_step[2] = True
        else:
            Recognize.doRec(ConfigParams.box_code_file, False, 0.0, 0.0, 0.0, 0.0)  # 下发拍照指令
            if Timer.delay(0.5):
                Do.setDO(self.fill_light_do, False)
                Module.set_status(ScriptStatus.FINISHED)

    def load(self):
        log.info(f"----- running load  {self.goods_id}------")
        load_info = dict()
        if not self.cur_c:
            if self.goods_id and self.goods_manger.goods_id_exist(self.goods_id):
                Abnormal.setTask(53000, f"货物{self.goods_id}已存在，请检查是否重复下发任务！", "", "", "")
                Module.set_status(ScriptStatus.FAILED)
            if self.self_position:
                if self.goods_manger.has_goods(self.self_position):
                    Abnormal.setTask(53000,
                                     f"第{self.self_position}层背篓已有货物，无法继续取货！请核对任务数据和背篓数据！", "",
                                     "", "")
                    Module.set_status(ScriptStatus.FAILED)
                self.cur_c = self.self_position
            else:
                self.cur_c = self.search_operable_container('load')
            log.info(f"load begin: {json.dumps(self.containers)}")
            if self.cur_c is None:  # 车体满载了
                Abnormal.setTask(53000, f"车体所有背篓已满，无法继续取货！", "", "", "")
                Module.set_status(ScriptStatus.FAILED)
                return
            if self.goods_manger.has_goods("999"):  # 货叉已载货
                Abnormal.setTask(53000, f"料斗已载货，无法执行取货任务！请核对任务数据和背篓数据！", "", "", "")
                Module.set_status(ScriptStatus.FAILED)
                return
        else:
            if not self.load_step[0]:
                self.load_step[0] = self.finger(1)
            if not self.load_step[1]:
                self.load_step[1] = self.rotate(self.rotate_pos)
            if not self.load_step[2]:
                self.load_step[2] = self.lift(self.lift_height)
            elif (self.load_step[0] and self.load_step[1] and self.load_step[2] and
                  not self.load_step[3]):
                if self.barcode_height is not None:
                    self.lift(self.barcode_height)
                    self.load_step[3] = self.goods_id == self.rec_barcode()
                else:
                    self.load_step[3] = True
            elif self.load_step[3] and not self.load_step[4]:
                if self.rec_adjust is not None:
                    if self.light_st_time is None:
                        Do.setDO(self.fill_light_do, True)
                        self.light_st_time = time.time()
                    if time.time() - self.light_st_time > ConfigParams.light_delay_time:
                        if self.rec_adjust.status is ScriptStatus.FINISHED:
                            Do.setDO(self.fill_light_do, False)
                            self.light_st_time = None
                            self.load_step[4] = True
                        elif self.rec_adjust.status is ScriptStatus.FAILED:
                            Module.set_status(ScriptStatus.FAILED)
                        else:
                            self.rec_adjust.run(self)
                else:
                    self.load_height = 0
                    self.load_step[4] = True
            elif self.load_step[4] and not self.load_step[5]:
                self.load_step[5] = self.lift(self.lift_height + self.load_height)
            elif self.load_step[5] and not self.load_step[6]:
                if Di.get_di(self.left_finger_up_di) and Di.get_di(self.right_finger_up_di):
                    self.load_step[6] = self.stretch(self.stretch_length)
                else:
                    Abnormal.setTask(53000, f"检测到拨指未打开，取消执行伸出动作！请检查拨指及其到位光电是否正常！", "",
                                     "", "")
                    Module.set_status(ScriptStatus.FAILED)
            elif self.load_step[6] and not self.load_step[7]:
                self.load_step[7] = self.finger(0)
            elif self.load_step[7] and not self.load_step[8]:
                self.load_step[8] = self.stretch(0)
            elif self.load_step[8] and (not self.load_step[9] or not self.load_step[10]):
                if not self.load_step[9]:
                    self.load_step[9] = self.rotate(0)
                if self.cur_c == "999":
                    self.load_step[:15] = [True] * 15
                else:
                    if not self.load_step[10]:
                        self.load_step[10] = self.lift(ConfigParams.high[int(self.cur_c)])
            elif self.load_step[9] and self.load_step[10] and not self.load_step[11]:
                self.load_step[11] = self.stretch(ConfigParams.stretch_self_length)
            elif self.load_step[11] and not self.load_step[12]:
                self.load_step[12] = self.finger(1)
            elif self.load_step[12] and not self.load_step[13]:
                self.load_step[13] = self.stretch(0)
            elif self.load_step[13] and not self.load_step[14]:
                self.load_step[14] = self.finger(0)
            elif self.load_step[14] and not self.load_step[15]:
                self.load_step[15] = self.lift_safe_height()

            load_info['cur_container'] = self.cur_c
            load_info['goodsId'] = self.goods_id
            load_info['load_step'] = self.load_step
            load_info['lift-height'] = self.lift_height
            load_info['load-height'] = self.load_height
            load_info['lift-real-height'] = self.lift_real_pos
            Module.report_info({"load_info": load_info})
            if all(self.load_step):
                self.goods_manger.setContainer(self.cur_c, self.goods_id, "")
                return True

    def in_take(self):
        """
        内部取货： 从背篓取货到货叉
        """
        in_take_info = dict()
        if not self.cur_c:
            self.check_take()
        else:
            if self.cur_c == "999":
                Module.set_status(ScriptStatus.FINISHED)
            else:
                if not self.in_take_step[0]:
                    self.in_take_step[0] = self.finger(1)
                if not self.in_take_step[1]:
                    self.in_take_step[1] = self.lift(ConfigParams.low[int(self.cur_c)])
                if not self.in_take_step[2]:
                    self.in_take_step[2] = self.rotate(0)
                if all(self.in_take_step[0:3]) and not self.in_take_step[3]:
                    self.in_take_step[3] = self.stretch(ConfigParams.stretch_self_length)
                elif self.in_take_step[3] and not self.in_take_step[4]:
                    self.in_take_step[4] = self.finger(0)
                elif self.in_take_step[4] and not self.in_take_step[5]:
                    self.in_take_step[5] = self.stretch(0)
                elif self.in_take_step[5] and not self.in_take_step[6]:
                    self.in_take_step[6] = self.rotate(self.rotate_pos)
                if self.in_take_step[5] and not self.in_take_step[7]:
                    self.in_take_step[7] = self.lift(self.lift_height)

        in_take_info["in_take_step"] = self.in_take_step[:8]
        in_take_info["cur_container"] = self.cur_c
        in_take_info["goodsId"] = self.goods_id
        Module.report_info = ({"in_take_info": in_take_info})
        if all(self.in_take_step[:8]):
            Container.clearContainer(self.cur_c)
            goods_id = self.goods_manger.get_goodsId_by_container(self.cur_c)
            Container.setContainer("999", goods_id, "")
            return True

    def in_put(self):
        """
        内部放货： 从货叉放货到背篓
        """
        if not self.cur_c:
            self.check_put()
        else:
            if not self.in_put_step[0]:
                self.in_put_step[0] = self.lift(ConfigParams.high[int(self.cur_c)])
            if not self.in_put_step[1]:
                self.in_put_step[1] = self.rotate(0)
            if not self.in_put_step[2]:
                self.in_put_step[2] = True
            if all(self.in_put_step[0:3]) and not self.in_put_step[3]:
                self.in_put_step[3] = self.stretch(ConfigParams.stretch_self_length)
            if all(self.in_put_step[0:4]) and not self.in_put_step[4]:
                self.in_put_step[4] = self.finger(1)
            if all(self.in_put_step[0:5]) and not self.in_put_step[5]:
                self.in_put_step[5] = self.stretch(0)
            if all(self.in_put_step[0:6]) and not self.in_put_step[6]:
                self.in_put_step[6] = self.finger(0)
            if all(self.in_put_step[0:7]) and not self.in_put_step[7]:
                self.in_put_step[7] = self.lift_safe_height()
        log.info(f"----- running in_put ------")
        in_put_info = dict()
        in_put_info["goodsId"] = self.goods_id
        in_put_info["in_put_info"] = self.in_put_step[:7]
        Module.report_info({"in_take_info": in_put_info})

        if all(self.in_put_step[0:8]):
            goods_id = self.goods_manger.get_goodsId_by_container("999")
            Container.setContainer(self.cur_c, goods_id, "")
            Container.clearContainer("999")
            return True

    def ex_take(self):
        """
        外部取货： 从货架取货到货叉
        """
        if self.goods_manger.has_goods("999"):  # 抓斗有货
            Abnormal.setTask(53000, f"检测到料斗已载货，无法执行外部取货动作！请核对任务数据和背篓数据！", "", "", "")
            Module.set_status(ScriptStatus.FAILED)
            return
        log.info(f"----- running ex_take ------")
        ex_take_info = dict()
        if self.barcode_height is not None:
            if not self.ex_take_step[0]:
                self.ex_take_step[0] = self.lift(self.barcode_height)
            if not self.ex_take_step[1]:
                self.ex_take_step[1] = self.rotate(self.rotate_pos)
            if all(self.ex_take_step[0:2]) and not self.ex_take_step[2]:
                self.ex_take_step[2] = self.goods_id == self.rec_barcode()
        else:
            self.ex_take_step[0:3] = [True] * 3

        if self.rec_adjust is not None:
            if not self.change_step[0]:
                self.change_step[0] = self.lift(self.lift_height)
            if not self.change_step[1]:
                self.change_step[1] = self.rotate(self.rotate_pos)
            if all(self.change_step[0:2]) and not self.change_step[2]:
                Do.setDO(self.fill_light_do, True)
                self.rec_adjust.status = ScriptStatus.RUNNING
                if Do.get_do(self.fill_light_do):
                    if Timer.delay(ConfigParams.light_delay_time):
                        self.change_step[2] = True
            if self.change_step[2] and not self.ex_take_step[3]:
                if self.rec_adjust.status is ScriptStatus.FINISHED:
                    Do.setDO(self.fill_light_do, False)
                    self.ex_take_step[3] = True
                elif self.rec_adjust.status is ScriptStatus.FAILED:
                    Module.set_status(ScriptStatus.FAILED)
                else:
                    self.rec_adjust.run(self)
        else:
            self.ex_take_step[3] = True

        if all(self.ex_take_step[0:4]) and not self.ex_take_step[4]:
            self.ex_take_step[4] = self.lift(self.lift_height + self.load_height)
            self.ex_take_step[5] = True
        if all(self.ex_take_step[0:6]) and not self.ex_take_step[6]:
            self.ex_take_step[6] = self.finger(1)
        if all(self.ex_take_step[0:7]) and not self.ex_take_step[7]:
            self.ex_take_step[7] = self.stretch(self.stretch_length)
        if all(self.ex_take_step[0:8]) and not self.ex_take_step[8]:
            self.ex_take_step[8] = self.finger(0)
        if all(self.ex_take_step[0:9]) and not self.ex_take_step[9]:
            self.ex_take_step[9] = self.stretch(0)

        ex_take_info['goodsId'] = self.goods_id
        ex_take_info['cur_container'] = self.cur_c
        ex_take_info['ex_take_step'] = self.ex_take_step[:10]
        Module.report_info({"ex_take_info": ex_take_info})
        if all(self.ex_take_step[:10]):
            Container.setContainer("999", self.goods_id, "")
            return True

    def ex_put(self):
        """
        外部放货： 从货叉放货到货架
        """
        log.info(f"----- running ex_put ------")
        if not self.goods_manger.has_goods("999"):  # 抓斗没货
            return self.unload()

        ex_put_info = dict()
        if self.rec_box_lift:
            if not self.ex_put_step[0]:
                self.ex_put_step[0] = self.lift(self.rec_box_lift)
            if not self.ex_put_step[1]:
                self.ex_put_step[1] = self.rotate(self.rotate_pos)
            if all(self.ex_put_step[0:2]) and not self.ex_put_step[2]:
                self.rec_box.status = ScriptStatus.RUNNING
                self.rec_box.is_error = True
                Do.setDO(self.fill_light_do, True)
                if Do.get_do(self.fill_light_do):
                    if Timer.delay(ConfigParams.light_delay_time):
                        self.ex_put_step[2] = True
            if all(self.ex_put_step[0:3]) and not self.ex_put_step[3]:
                if self.rec_box.status is ScriptStatus.FINISHED:
                    self.rec_box.reset()
                    self.rec_box.is_error = None
                    Do.setDO(self.fill_light_do, False)
                    if self.rec_box.has_goods and not self.rec_box.goods_out_dist:
                        Abnormal.setTask(53000, "检测到货架上已经有货，取消放货动作！请人工核查货架和任务数据！", "", "",
                                         "")
                        Module.set_status(ScriptStatus.FAILED)
                        return
                    else:
                        self.ex_put_step[3] = True
                elif self.rec_box.status is ScriptStatus.FAILED:
                    Do.setDO(self.fill_light_do, False)
                    self.ex_put_step[3] = True
                else:
                    self.rec_box.run(self)
        else:
            self.ex_put_step[0:4] = [True] * 4

        if all(self.ex_put_step[0:4]) and not self.ex_put_step[4]:
            self.ex_put_step[4] = self.lift(self.lift_height)
        if all(self.ex_put_step[0:4]) and not self.ex_put_step[5]:
            self.ex_put_step[5] = self.rotate(self.rotate_pos)
        if all(self.ex_put_step[0:6]) and not self.ex_put_step[6]:
            if self.rec_adjust is not None:
                if not self.change_step[0]:
                    Do.setDO(self.fill_light_do, True)
                    self.rec_adjust.status = ScriptStatus.RUNNING
                    if Do.get_do(self.fill_light_do):
                        if Timer.delay(ConfigParams.light_delay_time):
                            self.change_step[0] = True
                else:
                    if self.rec_adjust.status is ScriptStatus.FINISHED:
                        Do.setDO(self.fill_light_do, False)
                        self.ex_put_step[6] = True
                    elif self.rec_adjust.status is ScriptStatus.FAILED:
                        Module.set_status(ScriptStatus.FAILED)
                    else:
                        self.rec_adjust.run(self)
            else:
                self.ex_put_step[6] = True
        if all(self.ex_put_step[0:7]) and not self.ex_put_step[7]:
            self.ex_put_step[7] = self.lift(self.lift_height + self.unload_height)
        if all(self.ex_put_step[0:8]) and not self.ex_put_step[8]:
            self.ex_put_step[8] = self.stretch(self.stretch_length)
        if all(self.ex_put_step[0:9]) and not self.ex_put_step[9]:
            self.ex_put_step[9] = self.finger(1)
        if all(self.ex_put_step[0:10]) and not self.ex_put_step[10]:
            self.ex_put_step[10] = self.stretch(0)
        if all(self.ex_put_step[0:11]) and not self.ex_put_step[11]:
            self.ex_put_step[11] = self.rotate(0)
        if all(self.ex_put_step[0:11]) and not self.ex_put_step[12]:
            self.ex_put_step[12] = self.finger(0)
        if all(self.ex_put_step[0:12]) and not self.ex_put_step[13]:
            self.ex_put_step[13] = self.lift_safe_height()

        ex_put_info["ex_put_info"] = self.ex_put_step[:13]
        ex_put_info["goodsId"] = self.goods_id
        Module.report_info({"ex_put_info": ex_put_info})
        if all(self.ex_put_step[:14]):
            Container.clearContainer("999")
            return True

    def unload(self):
        log.info(f"----- running unload ------")
        unload_info = dict()

        if not self.cur_c:
            if self.self_position:
                if self.goods_manger.get_goodsId_by_container(self.self_position) != self.goods_id:
                    Abnormal.setTask(53000,
                                     f"{self.self_position}号背篓中的货物Id与任务的货物ID({self.goods_id})不匹配！请核对任务数据和背篓数据！",
                                     "", "", "")
                    Module.set_status(ScriptStatus.FAILED)
                if not self.goods_manger.has_goods(self.self_position):
                    Abnormal.setTask(53000,
                                     f"{self.self_position}号背篓是空的，无法执行放货任务！请核对任务数据和背篓数据！", "",
                                     "", "")
                    Module.set_status(ScriptStatus.FAILED)
                if self.self_position != "999" and self.goods_manger.has_goods("999"):
                    Abnormal.setTask(53000, f"料斗已载货，无法执行背篓的放货任务！请核对任务数据和背篓数据！", "", "", "")
                    Module.set_status(ScriptStatus.FAILED)
                self.cur_c = self.self_position
            else:
                if self.goods_manger.has_goods("999"):  # 抓斗有货
                    self.cur_c = "999"
                    if self.goods_manger.get_goodsId_by_container("999") != self.goods_id:
                        Abnormal.setTask(53000, f"料斗已载货，无法先执行背篓的放货任务，必须优先释放料斗的货物！", "", "",
                                         "")
                        Module.set_status(ScriptStatus.FAILED)
                        return
                else:
                    self.cur_c = self.goods_manger.get_container_by_goodsId(self.goods_id)
            if not self.cur_c:
                Abnormal.setTask(53000, f"背篓中不存在货物: {self.goods_id}，无法执行放货任务！请核对任务数据和背篓数据！",
                                 "", "", "")
                Module.set_status(ScriptStatus.FAILED)
                return
            log.info(f"unload begin: {json.dumps(self.containers)}")
        else:
            if self.cur_c == "999":
                self.unload_step[:6] = [True] * 6
            else:
                if not self.unload_step[0] or not self.unload_step[1] or not self.unload_step[2]:
                    if not self.unload_step[0]:
                        self.unload_step[0] = self.lift(ConfigParams.low[int(self.cur_c)])
                    if not self.unload_step[1]:
                        self.unload_step[1] = self.finger(1)
                    if not self.unload_step[2]:
                        self.unload_step[2] = self.rotate(0)
                elif self.unload_step[1] and self.unload_step[2] and not self.unload_step[3]:
                    self.unload_step[3] = self.stretch(ConfigParams.stretch_self_length)
                elif self.unload_step[3] and not self.unload_step[4]:
                    self.unload_step[4] = self.finger(0)
                elif self.unload_step[4] and not self.unload_step[5]:
                    if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                        if not self.unload_step[6]:
                            self.unload_step[6] = self.lift(self.lift_height)
                        if not self.unload_step[7]:
                            self.unload_step[7] = self.rotate(self.rotate_pos)
                    self.unload_step[5] = self.stretch(0)
                    goods_id = self.goods_manger.get_goodsId_by_container(self.cur_c)
                    Container.setContainer("999", goods_id, "")
                    Container.clearContainer(self.cur_c)

            if all(self.unload_step[:6]) and (not self.unload_step[6] or not self.unload_step[7]):
                if self.rec_box_lift:
                    if not self.unload_step[6]:
                        if not self.rec_box_lift_step[0]:
                            self.rec_box_lift_step[0] = self.rotate(self.rotate_pos)
                        if not self.rec_box_lift_step[1]:
                            self.rec_box_lift_step[1] = self.lift(self.rec_box_lift)
                        if self.rec_box_lift_step[0] and self.rec_box_lift_step[1]:
                            self.unload_step[6] = True
                    if not self.unload_step[7] and self.unload_step[6]:
                        if self.rec_box is not None:
                            if not self.rec_box_lift_step[2]:
                                self.rec_box.status = ScriptStatus.RUNNING
                                self.rec_box.is_error = True
                                Do.setDO(self.fill_light_do, True)
                                if Do.get_do(self.fill_light_do):
                                    if Timer.delay(ConfigParams.light_delay_time):
                                        self.rec_box_lift_step[2] = True
                            if not self.rec_box_lift_step[3] and self.rec_box_lift_step[2]:
                                if self.rec_box.status is ScriptStatus.FINISHED:
                                    self.rec_box.reset()
                                    self.rec_box.is_error = None
                                    Do.setDO(self.fill_light_do, False)
                                    if self.rec_box.has_goods and not self.rec_box.goods_out_dist:
                                        Abnormal.setTask(53000, "检测到货架上有货，取消放货动作！", "", "",
                                                         "execute_actions")
                                        Module.set_status(ScriptStatus.FAILED)
                                        return
                                    else:
                                        self.rec_box_lift_step[3] = True
                                elif self.rec_box.status is ScriptStatus.FAILED:
                                    Do.setDO(self.fill_light_do, False)
                                    self.rec_box_lift_step[3] = True
                                else:
                                    self.rec_box.run(self)
                            if not self.rec_box_lift_step[4] and self.rec_box_lift_step[3]:
                                self.rec_box_lift_step[4] = self.lift(self.lift_height)
                            if self.rec_box_lift_step[4]:
                                self.unload_step[7] = True
                        else:
                            self.unload_step[7] = True
                else:
                    if not self.unload_step[6]:
                        self.unload_step[6] = self.lift(self.lift_height)
                    if not self.unload_step[7]:
                        self.unload_step[7] = self.rotate(self.rotate_pos)
            elif self.unload_step[7] and not self.unload_step[8]:
                if self.rec_adjust is not None:
                    if not self.change_step[0]:
                        Do.setDO(self.fill_light_do, True)
                        self.rec_adjust.status = ScriptStatus.RUNNING
                        if Do.get_do(self.fill_light_do):
                            if Timer.delay(ConfigParams.light_delay_time):
                                self.change_step[0] = True
                    else:
                        if self.rec_adjust.status is ScriptStatus.FINISHED:
                            Do.setDO(self.fill_light_do, False)
                            self.unload_step[8] = True
                        elif self.rec_adjust.status is ScriptStatus.FAILED:
                            Module.set_status(ScriptStatus.FAILED)
                        else:
                            self.rec_adjust.run(self)
                else:
                    self.unload_step[8] = True
            elif self.unload_step[8] and not self.unload_step[9]:
                self.unload_step[9] = self.lift(self.lift_height + self.unload_height)
            elif self.unload_step[9] and not self.unload_step[10]:
                if self.pre_finger is not None:
                    self.finger(self.pre_finger)
                self.unload_step[10] = self.stretch(self.stretch_length)
            elif self.unload_step[10] and not self.unload_step[11]:
                self.unload_step[11] = self.finger(1)
            elif self.unload_step[11] and not self.unload_step[12]:
                self.unload_step[12] = self.stretch(0)
            elif self.unload_step[12] and (not self.unload_step[13]
                                           or not self.unload_step[14]
                                           or not self.unload_step[15]):
                if not self.unload_step[13]:
                    self.unload_step[13] = self.finger(0)
                if not self.unload_step[14]:
                    self.unload_step[14] = self.rotate(0)
                if not self.unload_step[15]:
                    self.unload_step[15] = self.lift_safe_height()

            unload_info['unload_step'] = self.unload_step
            unload_info['cur_container'] = self.cur_c
            unload_info['goodsId'] = self.goods_id
            Module.report_info({"unload_info": unload_info})

        if all(self.unload_step):
            Container.clearContainer("999")
            return True

    def lift_safe_height(self):
        if self.lift_real_pos > ConfigParams.safe_lift_height:
            return self.lift(ConfigParams.safe_lift_height)
        return True

    def update_report_info(self):
        self.lift_real_pos = Motor.get_motor_pos(ConfigParams.lift_motor_name)
        self.stretch_real_pos = Motor.get_motor_pos(ConfigParams.stretch_motor_name)
        self.rotate_real_pos = Motor.get_motor_pos(ConfigParams.rotate_motor_name)
        self.update_finger_info()

        motor_info_raw = Odometer.get_data().get("motorInfo", [])
        self.motor_info = {}
        for motor in motor_info_raw:
            name = motor.get("motorName")
            info = {
                "motor_pos": round(motor.get("position", -1), 3),
                "motor_type": motor.get("type", None),
            }
            if name == ConfigParams.lift_motor_name:
                self.motor_info["lift"] = info
            elif name == ConfigParams.stretch_motor_name:
                self.motor_info["stretch"] = info
            elif name == ConfigParams.rotate_motor_name:
                self.motor_info["rotate"] = info
        self.containers = Container.getContainers()

    def has_goods_id(self, r, goods_id: str):
        r.logInfo(f"goodsId: {goods_id}")
        for c in self.containers:
            if goods_id == c['goods_id']:
                return True
        return False

    def search_operable_container(self, opt):
        ct = None
        if opt == 'load':
            for c in self.containers:
                if not c['has_goods']:
                    ct = c['container_name']
                    break
        elif opt == 'unload':
            for c in self.containers:
                if c['has_goods'] and self.goods_id == c['goods_id']:
                    ct = c['container_name']
        return ct

    def check_put(self):
        """
        放货到背篓前，检查背篓有空位且货叉有货
        """
        if not self.goods_manger.has_goods("999"):  # 货叉无货
            Abnormal.setTask(57300, f"料斗没有货物，无需内部放货！", "", "", "")
            Module.set_status(ScriptStatus.FINISHED)
            return

        # 货物在背篓里
        if self.goods_id and self.goods_manger.goods_id_exist(self.goods_id):
            Abnormal.setTask(57300, f"货物已在背篓中", "", "", "")
            Module.set_status(ScriptStatus.FINISHED)
            return

        if self.self_position:
            if self.goods_manger.has_goods(self.self_position):
                Abnormal.setTask(53000, f"第{self.self_position}层背篓已有货物，无法继续存放货物！", "", "", "")
                Module.set_status(ScriptStatus.FAILED)
                return
            self.cur_c = self.self_position
        else:
            self.cur_c = self.search_operable_container('load')  # 查找空位

        if self.cur_c is None:  # 车体满载了
            Abnormal.setTask(57300, f"车体所有背篓已满，货叉载货中", "", "", "")
            Module.set_status(ScriptStatus.FINISHED)
            return

    def check_take(self):
        """
        从背篓取货前检测背篓货物信息，检查货叉为空
        """
        if self.self_position:
            if not self.goods_manger.has_goods(self.self_position):
                Abnormal.setTask(53000, f"第{self.self_position}层背篓是空的，无法执行内部取货动作！", "", "", "")
                Module.set_status(ScriptStatus.FAILED)
            self.cur_c = self.self_position
        else:
            self.cur_c = self.goods_manger.get_container_by_goodsId(self.goods_id)

        if self.goods_manger.has_goods("999"):  # 抓斗有货
            self.cur_c = "999"

        if not self.cur_c:
            Abnormal.setTask(53000, f"货物{self.goods_id}不存在，请核对货物编号和背篓数据！", "", "", "")
            Module.set_status(ScriptStatus.FAILED)
            return


def main():
    Module.init()
    # 获取并验证参数
    raw_args = Module.get_task_args()
    validator = ParamValidator(InputParams.builder.to_dict())
    try:
        # 验证参数
        args = validator.validate(raw_args)
        log.info(f"参数验证成功: {args}")
    except ValueError as e:
        log.error(f"参数验证失败: {e}")
        Abnormal.setTask(53000, f"脚本输入参数验证失败: {e}", "", "", "")
        Module.set_status(ScriptStatus.FAILED)
        return

    robot = ContainerRobot(args)
    while True:
        status = Module.get_status()
        if status is ScriptStatus.RUNNING:
            robot.run()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            NetProtocol().release()
            Do.setDO(robot.fill_light_do, False)
            return
        log.info(f"{Module.get_task_args()=}, {Module.get_task_id()=}, {Module.get_status()=}")
        time.sleep(0.1)


class Rec:
    def __init__(self, filename, is_error=None, max_rec_times=10):
        self.status = ScriptStatus.NONE
        self.is_error = is_error
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = max_rec_times
        self.result = dict()
        self.has_goods = None
        self.goods_out_dist = None
        self.max_goods_dist = 0.8
        self.rec_info = dict()

    def get_info(self):
        return self.rec_info

    def run(self, agv: ContainerRobot = None):
        self.status = ScriptStatus.RUNNING
        rec_results = None
        rec_status = Recognize.getRecStatus()
        if rec_status == 3 or rec_status == -1:
            log.info("rec failed:{}".format(self.result))
            if Timer.delay(0.05):
                self.rec_times = self.rec_times + 1
                if self.rec_times > self.max_rec_times:
                    if not self.is_error:
                        Abnormal.setTask(53000,
                                         f"连续识别{self.max_rec_times}次失败，请检查二维码是否损坏，请手动识别并查看照片是否清晰！",
                                         "", "", "")
                        self.status = ScriptStatus.FAILED
                    else:
                        self.status = ScriptStatus.FINISHED
                else:
                    Recognize.resetRec()
        elif rec_status == 2:
            rec_results = Recognize.getRecResults()
            if "reco_list" in rec_results:
                if len(rec_results["reco_list"]) == 1:
                    self.result = rec_results["reco_list"][0]
            if "resultImg" in self.result:
                self.result.pop("resultImg")
            Recognize.resetRec()
            self.has_goods = True
            if "x" in self.result:
                if self.result["x"] > self.max_goods_dist:
                    self.goods_out_dist = True
            self.status = ScriptStatus.FINISHED
            log.info(f"rec success: {Module.get_status().name} {self.result}")
        else:
            log.info(f"--------------- doRec ----------------")
            Recognize.doRec(self.filename, False, 0.0, 0.0, 0.0, 0.0)

        self.rec_info['rec_results'] = rec_results
        self.rec_info['rec_count'] = self.rec_times
        self.rec_info['rec_task_status'] = self.status
        self.rec_info['rec_status'] = rec_status
        self.rec_info['file'] = self.filename

    def reset(self):
        Recognize.resetRec()
        self.status = ScriptStatus.RUNNING


class RecAdjust:
    def __init__(self, filename):
        self.rotate_step = None
        self.lift_step = None
        self.status = ScriptStatus.NONE
        self.rec = Rec(filename)
        self.result = []
        self.max_rec_fail_times = 10
        self.max_adjust_time = 30
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.go_args = dict()
        self.ok = False
        self.ok_x = ConfigParams.ok_x
        self.ok_yaw = ConfigParams.ok_yaw
        self.max_yaw_bias = ConfigParams.max_yaw_bias
        self.next_rotate_pos = 1.5708
        self.diff_height = 0
        self.last_yaw_adjust = 1.5708
        self.plan_status = ScriptStatus.NONE
        self.goPath = GoPath()
        self.code2robot = -1

    @staticmethod
    def move_x(dx, dy, yaw, rotate_pos, offset_x=0):
        """
        计算车体在x方向上移动的距离
        """
        if rotate_pos > 0:
            if yaw > 0:
                return -dy - dx * math.tan(math.pi - yaw) - offset_x
            elif yaw < 0:
                return -dy + dx * math.tan(math.pi + yaw) - offset_x
        else:
            if yaw > 0:
                return dy + dx * math.tan(math.pi - yaw) + offset_x
            elif yaw < 0:
                return dy - dx * math.tan(math.pi + yaw) + offset_x

    def run(self, agv: ContainerRobot):
        cur_state = dict()
        self.status = ScriptStatus.RUNNING
        if self.plan_status is not ScriptStatus.FINISHED:
            self.plan_status = ScriptStatus.RUNNING
            if self.rec.status is ScriptStatus.RUNNING or self.rec.status is ScriptStatus.NONE:
                log.info(f"----- rec to adjust {self.rec.status.name}------")
                self.rec.run()
            elif self.rec.status is ScriptStatus.FAILED:
                self.rec_fail_time = self.rec_fail_time + 1
                random_dist = random.choice([1, -1]) * (1 / 180 * math.pi)
                agv.rotate(agv.rotate_real_pos + random_dist, max_speed=0.3)
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.rec.reset()
                    self.rec.run()
                else:
                    self.status = ScriptStatus.FAILED
                log.info("rec fail!!! {}".format(self.rec_fail_time))
            elif self.rec.status is ScriptStatus.FINISHED:
                log.info(f"------------------ move to adjust -----------------")
                self.rec_fail_time = 0

                """获取结果"""
                # 计算手臂伸出长度
                if agv.is_auto_stretch:
                    if agv.operation == "load":
                        agv.stretch_length = (abs(self.rec.result['x']) - ConfigParams.auto_stretch_odo_len +
                                              ConfigParams.auto_load_stretch_dist + ConfigParams.auto_stretch_box_len)
                    elif agv.operation == "unload":
                        agv.stretch_length = (abs(self.rec.result['x']) - ConfigParams.auto_stretch_odo_len +
                                              ConfigParams.auto_unload_stretch_dist + ConfigParams.auto_stretch_box_len)

                code2fork = [self.rec.result['x'], self.rec.result['y'], self.rec.result['z'],
                             self.rec.result['yaw']]

                self.diff_height = self.rec.result['z']
                agv.rec_height_diff = self.rec.result['z']
                # 根据反馈的yaw来判断rotate调整方向
                agv.yaw_adjust = math.pi - abs(code2fork[3])  # 角度偏差
                if code2fork[3] > 0:  # 识别结果为正值
                    self.next_rotate_pos = agv.rotate_real_pos - agv.yaw_adjust
                else:  # 识别结果为负值
                    self.next_rotate_pos = agv.rotate_real_pos + agv.yaw_adjust

                # 计算移动距离
                if bool(ConfigParams.auto_adjust_rotate):
                    rec_yaw = self.rec.result['yaw']
                else:
                    rec_yaw = math.pi
                x_dist = self.move_x(self.rec.result['x'], self.rec.result['y'], rec_yaw, agv.rotate_real_pos,
                                     agv.offset_x)
                self.go_args["x"] = x_dist
                self.go_args["coordinate"] = "robot"
                self.go_args["y"] = 0
                self.go_args["theta"] = 0
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["maxSpeed"] = 0.3
                self.go_args["maxAcc"] = 0.3
                self.go_args["maxDec"] = 0.3
                self.go_args["reachDist"] = 0.003
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                else:
                    self.go_args["backMode"] = 0

                if abs(agv.yaw_adjust) > self.max_yaw_bias:
                    self.status = ScriptStatus.FAILED
                    Abnormal.setTask(53000,
                                     f"识别到角度偏差{agv.yaw_adjust}超出上限值{self.max_yaw_bias}，请检查料箱是否摆正，二维码是否损坏！",
                                     "", "", "")
                else:
                    if self.adjust_count >= (self.max_adjust_time - 3):
                        self.ok_x = 0.01
                        self.ok_yaw = 0.02
                    # 精度满足, 识别调整任务完成
                    if not bool(ConfigParams.auto_adjust_rotate) and abs(self.rec.result['y']) < self.ok_x:
                        log.info(f"adjust finished, adjust count: {self.adjust_count}")
                        self.status = ScriptStatus.FINISHED
                    elif bool(ConfigParams.auto_adjust_rotate) and abs(self.rec.result['y']) < self.ok_x and abs(
                            agv.yaw_adjust) <= self.ok_yaw:
                        log.info(f"adjust finished, adjust count: {self.adjust_count}")
                        self.status = ScriptStatus.FINISHED
                    else:
                        if self.adjust_count >= self.max_adjust_time:
                            self.status = ScriptStatus.FAILED
                            Abnormal.setTask(53000,
                                             f"识别调整{self.adjust_count}次未达到精度要求，请检查二维码是否损坏，相机画面是否清晰，精度参数是否设置合理！",
                                             "", "", "")
                self.plan_status = ScriptStatus.FINISHED
                self.rec.reset()
        elif self.status is not ScriptStatus.FINISHED and self.status is not ScriptStatus.FAILED:
            if self.goPath.status != ScriptStatus.FINISHED and self.goPath.status != ScriptStatus.FAILED:
                if abs(self.go_args['x']) < 0.003:
                    self.goPath.status = ScriptStatus.FINISHED
                else:
                    if self.goPath.status != ScriptStatus.FINISHED and self.goPath.status != ScriptStatus.FAILED:
                        self.goPath.run(self.go_args)
            elif not self.rotate_step and self.goPath.status == ScriptStatus.FINISHED:
                if abs(agv.yaw_adjust) <= 0.01:
                    self.rotate_step = True
                if not self.rotate_step and bool(ConfigParams.auto_adjust_rotate):
                    self.rotate_step = agv.rotate(self.next_rotate_pos, max_speed=0.3)
                else:
                    self.rotate_step = True
            elif self.goPath.status == ScriptStatus.FAILED:
                self.status = ScriptStatus.FAILED
            elif self.goPath.status == ScriptStatus.FINISHED and self.rotate_step:
                self.reset()
                self.adjust_count += 1
                self.last_yaw_adjust = agv.yaw_adjust
                self.plan_status = ScriptStatus.NONE
                self.rotate_step = False

        cur_state["auto_stretch_length"] = agv.stretch_length
        cur_state["go_path_status"] = self.goPath.status
        cur_state["go_args"] = self.go_args
        cur_state["rec_result"] = self.rec.result
        cur_state["rec_fail_time"] = self.rec_fail_time
        cur_state["adjust_count"] = self.adjust_count
        cur_state["cur_rotate"] = agv.rotate_real_pos / math.pi * 180
        cur_state["cur_lift"] = agv.lift_real_pos
        cur_state["cur_stretch"] = agv.stretch_real_pos
        cur_state["status"] = self.status
        cur_state["agv_yaw_adjust"] = agv.yaw_adjust / math.pi * 180
        cur_state["last_yaw_adjust"] = self.last_yaw_adjust / math.pi * 180
        cur_state["next_rotate_pos"] = self.next_rotate_pos / math.pi * 180
        Module.report_info({'rec_adjust': cur_state})

    def reset(self):
        self.rec.reset()
        self.status = ScriptStatus.RUNNING
        self.rec_fail_time = 0
        self.goPath.reset()


if __name__ == '__main__':
    main()