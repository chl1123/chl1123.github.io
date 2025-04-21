# -*- coding: utf-8 -*-
# @Date: 2024/12/08
# @Project: 3.5版本脚本示例
# @Coding:
# @Update:

import time

start_time = time.time()
from syspy import Module, ParamServer, Logger, Di, Motor, Navigation, ScriptStatus

log = Logger("jack")


class ConfigParams:
    param_server = ParamServer(__file__)
    jack_motor_name = param_server.loadParam("jack_motor_name", type="str", default="Motor-003", comment="顶升电机名称")
    jack_motor_speed = param_server.loadParam("jack_motor_speed", type="float", default=0.015,
                                              comment="顶升电机升降速度")
    jack_lift_zero = param_server.loadParam("jack_lift_zero", type="float", default=0.000, comment="顶升升降零位")

    jack_up_di = param_server.loadParam("jack_up_di", type="int", default=6, comment="顶升机构上极限DI")
    jack_zero_di = param_server.loadParam("jack_zero_di", type="int", default=3, comment="顶升机构零位DI")
    log.debug("jack create config params")


class Jack:
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

    def reset(self):
        self.spin_angle = 0
        self.init_path = True
        self.init_odo = True
        self.go_path_x = 0
        self.go_path_y = 0
        self.go_path_a = 0

    def run(self):
        Module.set_status(ScriptStatus.RUNNING)
        args = Module.get_task_args()
        Module.report_info(args)
        self.opt = Module.get_task_args('operation', None)
        self.height = Module.get_task_args('height', None)
        log.info("opt = ", self.opt, "+++++++++++++++++++++++++++++++++")
        if self.opt == "load":
            self.load()
        elif self.opt == "unload":
            self.unload()
        elif self.opt == "spin":
            self.spin_angle = Module.get_task_args('spinAngle', None)
            self.spin()
        elif self.opt == "goPath":
            self.go_path_x = Module.get_task_args('x', 0)
            self.go_path_y = Module.get_task_args('y', 0)
            self.go_path_a = Module.get_task_args('a', 0)
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
        log.info("setMotorPosition(): ",
                 Motor.setMotorPosition(ConfigParams.jack_motor_name,
                                        ConfigParams.jack_lift_zero,
                                        ConfigParams.jack_motor_speed,
                                        ConfigParams.jack_zero_di))
        if Di.get_di(ConfigParams.jack_zero_di) or Motor.isMotorReached(ConfigParams.jack_motor_name):
            log.info("unload finish")
            Module.set_status(ScriptStatus.FINISHED)

    def spin(self):
        log.debug("spin: ", self.spin_angle)
        log.debug("setRobotSpinAngle(): ", Navigation.setRobotSpinAngle(self.spin_angle, 0))
        finished = Navigation.spinRun()
        if finished:
            log.debug("spin finish")
            Module.set_status(ScriptStatus.FINISHED)

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
        result = Navigation.getCurrentPathProperty()
        log.debug("getCurrentPathProperty", result)
        Module.set_status(ScriptStatus.FINISHED)

    def getLM(self):
        log.info("getLM ==============================================")
        result = Navigation.getLM("LM7", True)
        log.info("getLM", result)
        Module.set_status(ScriptStatus.FINISHED)

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
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.info(f"{Module.get_task_args()=}")
        log.info(f"{Module.get_task_id()=}")
        log.info(f"{Module.get_status()=}")

    def main(self):
        while True:
            # 脚本任务状态管理
            status = Module.get_status()
            if status is ScriptStatus.RUNNING:
                self.run()
            elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
                return
            self.print_info()
            time.sleep(0.1)


if __name__ == '__main__':
    Module.init()
    j = Jack()
    j.main()
