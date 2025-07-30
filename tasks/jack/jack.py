# -*- coding: utf-8 -*-
# @Date: 2024/12/08
# @Project: 3.5版本脚本示例
# @Coding:
# @Update:

import time

start_time = time.time()
from syspy import Module, ParamServer, Logger, Di, Motor, Navigation, ScriptStatus
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


class Jack(ModuleBase):
    def __init__(self, args):
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
        self.args = args
        Module.set_status(ScriptStatus.NONE)
        print("init Jack", args)

    def reset(self):
        self.spin_angle = 0
        self.init_path = True
        self.init_odo = True
        self.go_path_x = 0
        self.go_path_y = 0
        self.go_path_a = 0

    def run(self):
        self.count += 1
        Module.set_status(ScriptStatus.RUNNING)
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
        if self.count == 2:
            Module.set_status(ScriptStatus.FINISHED)

    def getLM(self):
        log.info("getLM ==============================================")
        result = Navigation.getLM("LM7", True)
        self.report_info["getLM"] = result
        log.info("getLM", result)
        if self.count == 2:
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
        # 打印当前任务id、任务状态、任务指令
        log.info(f"{Module.get_task_id()=}, {Module.get_status()=}, {Module.get_task_args()=}")
        Module.report_info(self.report_info)

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


def main():
    Module.init()

    params = {
        "operation": "load",
        "height": 0.1
    }
    j = Jack(params)
    while not Module.stop_flag:
        # 脚本任务状态管理
        status = Module.get_status()
        print("status", status)
        j.report_info["status"] = status
        j.print_info()
        if status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            return
        if status in (ScriptStatus.NONE, ScriptStatus.RUNNING):
            j.run()
        time.sleep(0.1)

if __name__ == '__main__':
    main()
