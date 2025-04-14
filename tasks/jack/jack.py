# -*- coding: utf-8 -*-
# @Date: 2024/12/08
# @Project: 3.5版本脚本示例
# @Coding:
# @Update:

import time

start_time = time.time()
import syspy
from syspy import Di, Motor, Navigation, ScriptStatus
from syspy.lib.logger import Logger
from syspy.utils.param_server import ParamServer

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


class Module(syspy.TaskModule):
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
        self.set_status(ScriptStatus.RUNNING)
        self.opt = self.get_task_args('operation', None)
        self.height = self.get_task_args('height', None)
        log.info("opt = ", self.opt, "+++++++++++++++++++++++++++++++++")
        if self.opt == "load":
            self.load()
        elif self.opt == "unload":
            self.unload()
        elif self.opt == "spin":
            self.spin_angle = self.get_task_args('spinAngle', None)
            self.spin()
        elif self.opt == "goPath":
            self.go_path_x = self.get_task_args('x', 0)
            self.go_path_y = self.get_task_args('y', 0)
            self.go_path_a = self.get_task_args('a', 0)
            self.goPath()
        elif self.opt == "getCurrentPathProperty":
            self.getCurrentPathProperty()
        elif self.opt == "odo":
            self.odo()
        elif self.opt == "getLM":
            self.getLM()
        else:
            self.set_status(ScriptStatus.FAILED)

    def load(self):
        log.debug("load: ", ConfigParams.jack_motor_name, self.height, ConfigParams.jack_motor_speed,
                  ConfigParams.jack_up_di)
        log.debug("setMotorPosition(): ",
                  Motor.setMotorPosition(ConfigParams.jack_motor_name, self.height, ConfigParams.jack_motor_speed,
                                         ConfigParams.jack_up_di))
        if Di.get_di(ConfigParams.jack_up_di) or Motor.isMotorReached(ConfigParams.jack_motor_name):
            log.debug("load finish")
            self.set_status(ScriptStatus.FINISHED)

    def unload(self):
        log.debug("unload: ", ConfigParams.jack_motor_name, ConfigParams.jack_lift_zero, ConfigParams.jack_motor_speed,
                  ConfigParams.jack_zero_di)
        log.debug("setMotorPosition(): ",
                  Motor.setMotorPosition(ConfigParams.jack_motor_name,
                                         ConfigParams.jack_lift_zero,
                                         ConfigParams.jack_motor_speed,
                                         ConfigParams.jack_zero_di))
        if Di.get_di(ConfigParams.jack_zero_di) or Motor.isMotorReached(ConfigParams.jack_motor_name):
            log.debug("unload finish")
            self.set_status(ScriptStatus.FINISHED)

    def spin(self):
        log.debug("spin: ", self.spin_angle)
        log.debug("setRobotSpinAngle(): ", Navigation.setRobotSpinAngle(self.spin_angle, 0))
        finished = Navigation.spinRun()
        if finished:
            log.debug("spin finish")
            self.set_status(ScriptStatus.FINISHED)

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
            self.set_status(ScriptStatus.FINISHED)

    def getCurrentPathProperty(self):
        log.debug("getCurrentPathProperty ==============================================")
        result = Navigation.getCurrentPathProperty()
        log.debug("getCurrentPathProperty", result)
        self.set_status(ScriptStatus.FINISHED)

    def getLM(self):
        log.info("getLM ==============================================")
        result = Navigation.getLM("LM7", True)
        log.info("getLM", result)
        self.set_status(ScriptStatus.FINISHED)

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
            self.set_status(ScriptStatus.FINISHED)

    def print_info(self):
        time.sleep(0.05)
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.info(f"{self.get_tasks_list()=}")
        log.info(f"{self.get_task_args()=}")
        log.info(f"{self.get_task_id()=}")
        log.info(f"{self.get_status()=}", )


if __name__ == '__main__':
    module = Module()
    module.main()
