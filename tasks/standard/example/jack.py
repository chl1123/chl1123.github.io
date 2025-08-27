# -*- coding: utf-8 -*-
# @Date: 2024/12/08
# @Project: 3.5版本脚本示例
# @Coding:
# @Update:
import json
import time

from syspy.lib.net_protocol import parse_modbus

start_time = time.time()
from syspy import Di, Motor, Navigation, NetProtocol, Trace
from syspy.lib.module import SafeMoveStatus
from syspy import Logger, Module, ScriptStatus
from syspy.utils.param_server import  ParamValidator, ParamServer, ParamBuilder, ParamType
from syspy.lib.module import ModuleBase

log = Logger("jack_example")


class ConfigParams:
    param_server = ParamServer(__file__)
    jack_motor_name = param_server.loadParam("jack_motor_name", type="str", default="Motor-003", comment="顶升电机名称")
    jack_motor_speed = param_server.loadParam("jack_motor_speed", type="float", default=0.015,
                                              comment="顶升电机升降速度")
    jack_lift_zero = param_server.loadParam("jack_lift_zero", type="float", default=0.000, comment="顶升升降零位")

    jack_up_di = param_server.loadParam("jack_up_di", type="int", default=6, comment="顶升机构上极限DI")
    jack_zero_di = param_server.loadParam("jack_zero_di", type="int", default=3, comment="顶升机构零位DI")
    log.debug(f"{param_server.data=}")

# 创建可复用的 jack_height 参数
def create_jack_height_param(builder: ParamBuilder):
    """创建顶升高度参数（可复用）"""
    with builder.CHILD(key="height", name="Jacking height",
                       desc="The height for lift operations"):
        builder.TYPE(ParamType.FLOAT)
        builder.REQUIRED(True)
        builder.MIN_VALUE(0.0)
        builder.MAX_VALUE(0.06)
        builder.UNIT("m")
        builder.SINGLESTEP(0.01)
        builder.DEFAULTVALUE(0.01)

class InputParams:
    builder = ParamBuilder(__file__, desc="Input Params Config")

    with builder.GROUPS():
        # 顶升操作组合框
        with builder.GROUP(key="operation", name="Lift Operations", desc="Lift Task script input parameters"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)

            with builder.CHILDREN():
                # load操作
                with builder.CHILD(key="load", name="Load Operation", desc="Lift the robot tray"):
                    builder.TYPE(ParamType.ARRAY)

                    with builder.CHILDREN():
                        # 顶升高度参数
                        create_jack_height_param(builder)

                # unload操作
                with builder.CHILD(key="unload", name="Unload Operation",
                                   desc="Lower the robot tray"):
                    builder.TYPE(ParamType.STRING)

                # spin
                with builder.CHILD(key="spin", name="Spin Operation", desc="Spin the robot"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        with builder.CHILD(key="spinAngle", name="Spin Angle",
                                           desc="Spin angle"):
                            builder.TYPE(ParamType.FLOAT)
                            builder.REQUIRED(True)
                            builder.UNIT("度")
                            builder.SINGLESTEP(1)

                with builder.CHILD(key="getCurrentPathProperty", name="Get Current Path Property", desc="Get current path property"):
                    builder.TYPE(ParamType.ARRAY)
    builder.save_to_file()

class Jack(ModuleBase):
    def __init__(self):
        super().__init__()
        self.opt = None
        self.height = 0.03
        self.spin_angle = 0
        self.init_path = True
        self.init_odo = True
        self.go_path_x = 0
        self.go_path_y = 0
        self.go_path_a = 0
        self.count = 0
        self.report_info = {}
        self.args = {}

    def reset(self):
        self.spin_angle = 0
        self.init_path = True
        self.init_odo = True
        self.go_path_x = 0
        self.go_path_y = 0
        self.go_path_a = 0

    def __init_args(self, args):
        self.args = args or Module.get_task_args()
        ...

    def run(self, args=None):
        self.count += 1
        Module.set_status(ScriptStatus.RUNNING)
        self.__init_args(args)
        self.report_info["args"] = self.args
        self.report_info["count"] = self.count
        self.report_info["run_time"] = round(time.time() - start_time, 2)
        self.opt = self.args.get('operation', None)
        self.height = self.args.get('height', None)
        log.info("opt = ", self.opt, "+++++++++++++++++++++++++++++++++")
        if self.opt == "load":
            self.load()
        elif self.opt == "unload":
            self.unload()
        elif self.opt == "spin":
            self.spin_angle = self.args.get('spinAngle', None)
            self.spin()
        elif self.opt == "goPath":
            self.go_path_x = self.args.get('x', 0)
            self.go_path_y = self.args.get('y', 0)
            self.go_path_a = self.args.get('a', 0)
            self.goPath()
        elif self.opt == "getCurrentPathProperty":
            self.getCurrentPathProperty()
        elif self.opt == "odo":
            self.odo()
        elif self.opt == "getLM":
            self.getLM()
        else:
            Module.set_status(ScriptStatus.FAILED)

    def load(self):
        log.info("load start")
        log.info("load: ", ConfigParams.jack_motor_name, self.height, ConfigParams.jack_motor_speed,
                 ConfigParams.jack_up_di)
        log.info("setMotorPosition(): ",
                 Motor.setMotorPosition(ConfigParams.jack_motor_name, self.height, ConfigParams.jack_motor_speed,
                                        ConfigParams.jack_up_di))
        if Di.get_di(ConfigParams.jack_up_di) or Motor.isMotorReached(ConfigParams.jack_motor_name):
            log.info("load finish")
            Module.set_status(ScriptStatus.FINISHED)

    def unload(self):
        log.info("unload start")
        log.info("unload: ", ConfigParams.jack_motor_name, ConfigParams.jack_lift_zero, ConfigParams.jack_motor_speed,
                 ConfigParams.jack_zero_di)
        # result = Motor.setMotorPosition(ConfigParams.jack_motor_name,
        #                                 ConfigParams.jack_lift_zero,
        #                                 ConfigParams.jack_motor_speed,
        #                                 ConfigParams.jack_zero_di)
        # 控制加速度
        result = Motor.setMotorPositionAdv(ConfigParams.jack_motor_name, ConfigParams.jack_lift_zero, maxAcc=0.001,
                                           stopDI=ConfigParams.jack_zero_di)
        log.info("setMotorPosition(): ", result)
        if Di.get_di(ConfigParams.jack_zero_di) or Motor.isMotorReached(ConfigParams.jack_motor_name):
            log.info("unload finish")
            Module.set_status(ScriptStatus.FINISHED)

    def spin(self):
        log.info("spin: ", self.spin_angle)
        log.info("setRobotSpinAngle(): ", Navigation.setRobotSpinAngle(self.spin_angle, 0))
        finished = Navigation.spinRun()
        if finished:
            log.debug("spin finish")
            Module.set_status(ScriptStatus.FINISHED)
        return Module.get_status()

    def goPath(self):
        if self.init_path:
            log.debug("init_path****************************************")
            self.init_path = False
            Navigation.resetPath()
            Navigation.setPathOnRobot([0, self.go_path_x], [0, self.go_path_y], self.go_path_a)
        Navigation.goPathParam({"test": 123})
        finished = Navigation.isPathReached()
        log.debug("goPath: ", self.go_path_x, self.go_path_y, self.go_path_a, finished)
        if finished:
            log.debug("goPath finish")
            Module.set_status(ScriptStatus.FINISHED)

    def getCurrentPathProperty(self):
        log.debug("getCurrentPathProperty ==============================================")
        # result = Navigation.getCurrentPathProperty()
        # log.debug("getCurrentPathProperty", result)
        if self.count == 100:
            Module.set_status(ScriptStatus.FINISHED)

    def getLM(self):
        self.count += 1
        log.info("getLM ==============================================")
        result = Navigation.getLM("LM7", True)
        self.report_info["getLM"] = result
        log.info("getLM", result)
        if self.count == 20:
            Module.set_status(ScriptStatus.FINISHED)
        return Module.get_status()

    def odo(self):
        if self.init_odo:
            log.info("init_odo****************************************")
            self.init_odo = False
            Navigation.resetOdoMove()
        status = Navigation.runOdoMove({"move_dist": 1.0, "speed_x": 0.5})
        finished = status == 3
        log.debug("===========================runOdoMove: ", status, finished)
        if finished:
            log.debug("!!!!!!!!!!!!!!!!!!!!!!!!!!runOdoMove finish")
            Module.set_status(ScriptStatus.FINISHED)

    def print_info(self):
        # 打印当前任务id、任务状态、任务指令
        Trace.log(f"task_id={Module.get_task_id()}, status={Module.get_status()}, args={self.args}")
        Module.report_info(self.report_info)

    def suspend(self):
        Module.set_status(ScriptStatus.SUSPENDED)
        log.info("suspend")

    def resume(self):
        if Module.get_status() == ScriptStatus.SUSPENDED:
            Module.set_status(ScriptStatus.RUNNING)
        log.info("resume")

    def cancel(self):
        # 恢复初始状态
        # reset()
        Module.set_status(ScriptStatus.FAILED)
        log.info("cancel")

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
        """
        从Modbus读取参数并解析
        """
        print("modbus___________ 读取Modbus数据")
        args = {}
        # 1. 读取操作码
        op_data = NetProtocol.getModbusData("4x", 201, 1)
        if op_data:
            operation_code = parse_modbus(op_data, 'uint16')
            print(f"   操作码: {operation_code}")
            # 根据操作码构建参数
            if operation_code == 1:
                args["operation"] = "load"
                # 读取高度参数
                height_data = NetProtocol.getModbusData("4x", 202, 2)
                if len(height_data) >= 2:
                    height = parse_modbus(height_data, 'float')
                    print(f"   读取高度参数寄存器值: [{height_data[0]}, {height_data[1]}]")
                    print(f"   解析后高度值: {height:.4f}m")
                    # 限制在有效范围内
                    args["height"] = max(0.0, min(0.06, height))
                    print(f"   设置高度: {args['height']:.4f}m")
            elif operation_code == 2:
                args["operation"] = "unload"
            elif operation_code == 3:
                args["operation"] = "spin"
                # 3. 读取浮点型参数
                print("读取浮点型参数:")
                # 读取角度参数
                angle_data = NetProtocol.getModbusData("4x", 202, 1)
                if angle_data:
                    angle_raw = parse_modbus(angle_data, 'int16')
                    args["spinAngle"] = angle_raw / 100.0  # 转换为度
                    print(f"   设置角度: {args['spinAngle']:.2f}度")
                else:
                    args["spinAngle"] = 90.0  # 默认角度
                    print("   使用默认角度")

            elif operation_code == 4:
                args["operation"] = "getCurrentPathProperty"
                # 4. 读取字符串参数
                print("读取字符串参数:")
                str_data = NetProtocol.getModbusData("4x", 202, 4)
                if str_data:
                    # 使用parse_modbus函数解析字符串
                    device_name = parse_modbus(str_data, 'string', 0, len(str_data))
                    if device_name:
                        args["device"] = device_name
                        print(f"   设备名称: {device_name}")

            print(f"   操作类型: {args.get('operation', 'unknown')}")
        return args


def main():
    Module.init()
    print("main")
    j = Jack()
    validator = ParamValidator(InputParams.builder.to_dict())
    modbus_args = None

    while True:
        # 脚本任务状态管理
        status = Module.get_status()
        print("status", status)
        j.report_info["status"] = status
        j.print_info()
        if j.event_safe_move_check:
            j.safe_move_check()
        if j.event_modbus:
            modbus_args = j.modbus()
            j.event_modbus = False
        if status == ScriptStatus.RUNNING:
            args = modbus_args or Module.get_task_args()
            try:
                # 验证参数
                args = validator.validate(args)
                print("check ok, args:", json.dumps(args, indent=2))
            except ValueError as e:
                print("check error:", e)
            j.run(args)
        time.sleep(0.1)

if __name__ == '__main__':
    main()
