# -*- coding: utf-8 -*-
# @Date: 2024/12/08
# @Project: 3.5版本脚本示例
# @Coding:
# @Update:

import time

import syspy
from syspy import Di, Motor, Navigation, ScriptStatus
from syspy.utils.param_server import ParamServer


class ConfigParams:
    param_server = ParamServer(__file__)
    jack_motor_name = param_server.loadParam("jack_motor_name", type="str", default="Motor-003", comment="顶升电机名称")
    jack_motor_speed = param_server.loadParam("jack_motor_speed", type="float", default=0.015,
                                              comment="顶升电机升降速度")
    jack_lift_zero = param_server.loadParam("jack_lift_zero", type="float", default=0.000, comment="顶升升降零位")

    jack_up_di = param_server.loadParam("jack_up_di", type="int", default=6, comment="顶升机构上极限DI")
    jack_zero_di = param_server.loadParam("jack_zero_di", type="int", default=3, comment="顶升机构零位DI")


class Module(syspy.BasicModule):
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

        self.current_task = None
        self.status = ScriptStatus.NONE

    def reset(self):
        self.spin_angle = 0
        self.init_path = True
        self.init_odo = True
        self.go_path_x = 0
        self.go_path_y = 0
        self.go_path_a = 0

    def run(self):
        self.status = ScriptStatus.RUNNING
        self.opt = self.current_task.get('operation', None)
        self.height = self.current_task.get('height', None)
        print("opt = ", self.opt, "+++++++++++++++++++++++++++++++++")
        if self.opt == "load":
            self.load()
        elif self.opt == "unload":
            self.unload()
        elif self.opt == "spin":
            self.spin_angle = self.current_task.get('spinAngle', None)
            self.spin()
        elif self.opt == "goPath":
            self.go_path_x = self.current_task.get('x', 0)
            self.go_path_y = self.current_task.get('y', 0)
            self.go_path_a = self.current_task.get('a', 0)
            self.goPath()
        elif self.opt == "getCurrentPathProperty":
            self.getCurrentPathProperty()
        elif self.opt == "odo":
            self.odo()
        elif self.opt == "getLM":
            self.getLM()
        else:
            pass

    def load(self):
        print("load: ", ConfigParams.jack_motor_name, self.height, ConfigParams.jack_motor_speed,
              ConfigParams.jack_up_di)
        print("setMotorPosition(): ",
              Motor.setMotorPosition(ConfigParams.jack_motor_name, self.height, ConfigParams.jack_motor_speed,
                                     ConfigParams.jack_up_di))
        if Di.get_di(ConfigParams.jack_up_di) or Motor.isMotorReached(ConfigParams.jack_motor_name):
            print("load finish")
            self.status = ScriptStatus.FINISHED

    def unload(self):
        print("unload: ", ConfigParams.jack_motor_name, ConfigParams.jack_lift_zero, ConfigParams.jack_motor_speed,
              ConfigParams.jack_zero_di)
        print("setMotorPosition(): ",
              Motor.setMotorPosition(ConfigParams.jack_motor_name,
                                     ConfigParams.jack_lift_zero,
                                     ConfigParams.jack_motor_speed,
                                     ConfigParams.jack_zero_di))
        if Di.get_di(ConfigParams.jack_zero_di) or Motor.isMotorReached(ConfigParams.jack_motor_name):
            print("unload finish")
            self.status = ScriptStatus.FINISHED

    def spin(self):
        print("spin: ", self.spin_angle)
        print("setRobotSpinAngle(): ", Navigation.setRobotSpinAngle(self.spin_angle, 0))
        finished = Navigation.spinRun()
        if finished:
            print("spin finish")
            self.status = ScriptStatus.FINISHED

    def goPath(self):
        if self.init_path:
            print("init_path****************************************")
            self.init_path = False
            Navigation.resetPath()
            Navigation.setPathOnRobot([0, self.go_path_x], [0, self.go_path_y], self.go_path_a)
        Navigation.goPathParam({"test": 123})
        finished = Navigation.isPathReached()
        print("goPath: ", self.go_path_x, self.go_path_y, self.go_path_a, finished)
        if finished:
            print("goPath finish")
            self.status = ScriptStatus.FINISHED

    def getCurrentPathProperty(self):
        print("getCurrentPathProperty ==============================================")
        result = Navigation.getCurrentPathProperty()
        print("getCurrentPathProperty", result)
        self.status = ScriptStatus.FINISHED

    def getLM(self):
        print("getLM ==============================================")
        result = Navigation.getLM("LM7", True)
        print("getLM", result)
        self.status = ScriptStatus.FINISHED

    def odo(self):
        if self.init_odo:
            print("init_odo****************************************")
            self.init_odo = False
            Navigation.resetOdoMove()
        status = Navigation.runOdoMove({"move_dist": 1.0, "speed_x": 0.5})
        finished = status == 3
        print("===========================runOdoMove: ", status, finished)
        if finished:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!runOdoMove finish")
            self.status = ScriptStatus.FINISHED

    def print_info(self):
        # 睡眠0.05秒
        time.sleep(0.05)
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        print("task queue: ", list(self.task_queue.queue))
        print("current task: ", self.current_task)
        print("current task id: ", self.task_id)
        print("current task status: ", self.status)


if __name__ == '__main__':
    module = Module()
    syspy.init(module)
    module.main()
