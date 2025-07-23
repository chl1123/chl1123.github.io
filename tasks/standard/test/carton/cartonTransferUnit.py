import sys
import time
import os

start_time = time.time()

sys.path.append(os.path.dirname(__file__) + "/syspy")
sys.path.append("../syspy")
from syspy import Module, Logger, Di, Do, Motor, Navigation, ScriptStatus, Abnormal, Controller, Odometer
from syspy.bin import Container
from syspy.utils.param_server import ParamBuilder, ParamType, ParamServer, ParamValidator

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
    box_code_file = p.loadParam("box_code_file", type="str", default="code/c0001.code",
                                group="recognize", comment="料箱二维码识别文件")
    shelf_code_file = p.loadParam("shelf_code_file", type="str", default="code/c0002.code",
                                  group="recognize", comment="货架二维码识别文件")
    barcode_file = p.loadParam("barcode_file", type="str", default="tag/t0003.tag",
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
            builder.DEFAULTVALUE(0)

        with builder.CHILD(key="rotate", name="Rotate", desc="旋转角度"):
            builder.MIN_VALUE(-100)
            builder.MAX_VALUE(100)
            builder.TYPE(ParamType.DOUBLE)
            builder.REQUIRED(False)
            builder.UNIT("rad")
            builder.DEFAULTVALUE(0)

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

        with builder.GROUP(key="operation", name="Operation", desc="机构动作选项"):
            builder.TYPE(ParamType.COMBO_BOX)
            with builder.CHILDREN():
                with builder.CHILD(key="zero", name="Zero", desc="机构回零"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="load", name="Load", desc="取货"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="unload", name="Unload", desc="放货"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="rec_box_barcode", name="Rec_Box_Barcode", desc="识别料箱一维码"):
                    builder.TYPE(ParamType.ARRAY)
                with builder.CHILD(key="rec_qrcode", name="Rec_Qrcode", desc="识别二维码"):
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
    def __init__(self):
        super().__init__()
        self.stretch_motor_stop = None
        self.rotate_motor_stop = None
        self.lift_motor_stop = None
        self.start_time = time.time()
        self.goods_id = ""
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

        self.containers = None

        self.calib_step = [False] * 3
        self.finger_open_start = False

        self.lift_motor_calib = None
        self.stretch_motor_calib = None
        self.rotate_motor_calib = None

        self.set_lift_motor_calib = False
        self.set_stretch_motor_calib = False
        self.set_rotate_motor_calib = False
        self.motor_calib_state = False
        self.motor_calib_info = {}
        self.enable_motor = False
        self.enable_motor_time = time.time()

        self.status = ScriptStatus.NONE
        self.report_info = {}
        self.motor_info = {}

        Motor.resetMotor(ConfigParams.lift_motor_name)
        self.validator = ParamValidator(InputParams.builder.to_dict())

    def run(self):
        Module.set_status(ScriptStatus.RUNNING)
        self.check_motor_emc()  # 检测控制器及驱动器急停状态
        if self.enable_motor and not self.motor_calib_state:  # 使能成功, 且未标零, 则标零
            self.motor_calib()
            # todo 标零未完成，提前return

        # 获取并验证参数
        raw_args = Module.get_task_args()
        try:
            # 验证参数
            args = self.validator.validate(raw_args)
            log.info(f"参数验证成功: {args}")
        except ValueError as e:
            log.error(f"参数验证失败: {e}")
            Abnormal.setTask(53000, f"脚本输入参数验证失败: {e}", "", "", "")
            Module.set_status(ScriptStatus.FAILED)
            return self.status

        self.self_position = str(self.self_position) if self.self_position is not None else self.self_position
        self.update_move_task_params()
        self.finger_pos = args.get("finger", 0)
        if time.time() - self.start_time > ConfigParams.timeout:
            Abnormal.setTask(53000, f"脚本任务运行超时，请重新执行任务！", "", "", "")
            Module.set_status(ScriptStatus.FAILED)

        self.update_report_info()
        if self.motor_calib_state:
            if "finger" in args:
                if self.finger(self.finger_pos):
                    self.update_finger_info()
                    Module.set_status(ScriptStatus.FINISHED)
            else:
                log.error("不支持的操作")
            # todo
        else:
            log.info("等待电机标零完成")

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
            # todo 机器人如果有异常，增加日志提示
            else:
                log.warning("机器人有异常，等待异常处理完成")

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
            l_d = Di.get_di(self.left_finger_down_di)
            l_u = Di.get_di(self.left_finger_up_di)
            r_d = Di.get_di(self.right_finger_down_di)
            r_u = Di.get_di(self.right_finger_up_di)
            if l_d and not l_u:
                Do.setDO(self.left_finger_down_do, False)
                self.left_finger_real_pos = 0
            if r_d and not r_u:
                Do.setDO(self.right_finger_down_do, False)
                self.right_finger_real_pos = 0
            if self.left_finger_real_pos == 0 and self.right_finger_real_pos == 0:
                self.finger_open_start = False  # 重置记录拨指动作开始的时刻
                Module.set_status(ScriptStatus.FINISHED)
                return True
        return False

    @staticmethod
    def get_motor_info(motor_name: str):
        motor_data = Odometer.get_data().get("motorInfo", [])
        for _motor in motor_data:
            if _motor.get('motorName') == motor_name:
                return _motor
        return {}

    def main(self):
        while True:
            status = Module.get_status()
            if status is ScriptStatus.RUNNING:
                self.run()
            elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED, ScriptStatus.NONE):
                Module.set_status(ScriptStatus.NONE)
                return
            log.info(f"{Module.get_task_args()=}")
            log.info(f"{Module.get_task_id()=}")
            log.info(f"{Module.get_status()=}")
            time.sleep(0.1)


if __name__ == '__main__':
    Module.init()
    robot = ContainerRobot()
    robot.main()
