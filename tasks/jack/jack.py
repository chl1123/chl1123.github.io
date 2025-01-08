# -*- coding: utf-8 -*-
# @Date: 2024/12/08
# @Project: 3.5版本脚本示例
# @Coding:
# @Update:

import time
import sys
from collections import deque

sys.path.append('/opt/.data/rbk/resources/scripts/')
import syspy
from syspy import Di, Motor, MF, BasicModule, ScriptStatus


class Module(BasicModule):
    def __init__(self):
        super(Module, self).__init__()
        self.timeout = 60
        self.jack_motor_name = "Motor-003"
        self.init = True
        self.status = ScriptStatus.NONE
        self.report_info = dict()
        self.motor_speed = 0.1
        self.zero_pos = 0.0
        self.up_di = 6
        self.zero_di = 3
        self.task_queue = deque()
        self.current_task = None
        self.current_task_id = None
        self.opt = None
        self.height = 0.03
        self.spinAngle = 0
        self.init_path = True
        self.init_odo = True
        self.goPath_x = 0
        self.goPath_y = 0
        self.goPath_a = 0

        syspy.report.set_status(self.status)

    def update_cmd(self, args):
        self.task_queue.append(args)

    def cancel(self):
        self.status = ScriptStatus.NONE
        syspy.report.set_status(self.status)

    def suspend(self):
        self.status = ScriptStatus.SUSPENDED
        syspy.report.set_status(self.status)

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
            self.spinAngle = self.current_task.get('spinAngle', None)
            self.spin()
        elif self.opt == "goPath":
            self.goPath_x = self.current_task.get('x', 0)
            self.goPath_y = self.current_task.get('y', 0)
            self.goPath_a = self.current_task.get('a', 0)
            self.goPath()
        elif self.opt == "getCurrentPathProperty":
            self.getCurrentPathProperty()
        elif self.opt == "odo":
            self.odo()
        elif self.opt == "getLM":
            self.getLM()
        else:
            pass
        syspy.report.set_status(self.status)

    def reset(self):
        self.status = ScriptStatus.RUNNING
        syspy.report.set_status(self.status)
        self.spinAngle = 0
        self.init_path = True
        self.init_odo = True
        self.goPath_x = 0
        self.goPath_y = 0
        self.goPath_a = 0
        print("reset*********************************************")

    def init_task_args(self):
        print("init_task_args")
        if self.task_queue:  # 判断任务队列不为空
            print("===================================================")
            print("***********************task_queue self.current_task", self.current_task)
            self.current_task = self.task_queue.popleft()  # 取出最先入队的任务
            self.current_task_id = self.current_task.get('taskId', None)
            self.status = ScriptStatus.RUNNING
            syspy.report.set_task_id(self.current_task_id)
            syspy.report.set_status(self.status)
            self.reset()
        else:
            print("task_queue empty")
            pass

    def get_robot_info(self):
        pass

    def load(self):
        print("load: ", self.jack_motor_name, self.height, self.motor_speed, self.up_di)
        print("setMotorPosition(): ",
              Motor.setMotorPosition(self.jack_motor_name, self.height, self.motor_speed, self.up_di))
        if Di.get_di(self.up_di) or Motor.isMotorReached(self.jack_motor_name):
            print("load finish")
            self.status = ScriptStatus.FINISHED
            syspy.report.set_status(self.status)

    def unload(self):
        print("unload: ", self.jack_motor_name, self.zero_pos, self.motor_speed, self.zero_di)
        print("setMotorPosition(): ",
              Motor.setMotorPosition(self.jack_motor_name, self.zero_pos, self.motor_speed, self.zero_di))
        if Di.get_di(self.zero_di) or Motor.isMotorReached(self.jack_motor_name):
            print("unload finish")
            self.status = ScriptStatus.FINISHED
            syspy.report.set_status(self.status)

    def spin(self):
        print("spin: ", self.spinAngle)
        print("setRobotSpinAngle(): ", MF.setRobotSpinAngle(self.spinAngle, 0))
        finished = MF.spinRun()
        if finished:
            print("spin finish")
            self.status = ScriptStatus.FINISHED
            syspy.report.set_status(self.status)

    def goPath(self):
        if self.init_path:
            print("init_path****************************************")
            self.init_path = False
            MF.resetPath()
            MF.setPathOnRobot([0, self.goPath_x], [0, self.goPath_y], self.goPath_a)
        MF.goPathParam({"test": 123})
        finished = MF.isPathReached()
        print("goPath: ", self.goPath_x, self.goPath_y, self.goPath_a, finished)
        if finished:
            print("goPath finish")
            self.status = ScriptStatus.FINISHED
            syspy.report.set_status(self.status)

    def getCurrentPathProperty(self):
        print("getCurrentPathProperty ==============================================")
        result = MF.getCurrentPathProperty()
        print("getCurrentPathProperty", result)
        self.status = ScriptStatus.FINISHED
        syspy.report.set_status(self.status)

    def getLM(self):
        print("getLM ==============================================")
        result = MF.getLM("LM7", True)
        print("getLM", result)
        self.status = ScriptStatus.FINISHED
        syspy.report.set_status(self.status)

    def odo(self):
        if self.init_odo:
            print("init_odo****************************************")
            self.init_odo = False
            MF.resetOdoMove()
        status = MF.runOdoMove({"move_dist": 1.0, "speed_x": 0.5})
        finished = (status == 3)
        print("===========================runOdoMove: ", status, finished)
        if finished:
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!runOdoMove finish")
            self.status = ScriptStatus.FINISHED
            syspy.report.set_status(self.status)

    def script_task_manage(self):
        self.status = syspy.report.run_status
        self.print_info()
        if self.status is ScriptStatus.NONE:
            self.init_task_args()
        elif self.status is ScriptStatus.RUNNING:
            self.run()
        elif self.status is ScriptStatus.SUSPENDED:
            self.suspend()
        elif self.status is ScriptStatus.FAILED:
            self.cancel()
        elif self.status is ScriptStatus.FINISHED:
            self.status = ScriptStatus.NONE
            syspy.report.set_status(self.status)

    def print_info(self):
        print("current task_queue: ", self.task_queue)
        print("current task: ", self.current_task)
        print("current task id: ", self.current_task_id)
        print("current task status: ", self.status)

    def main(self):
        while True:
            self.script_task_manage()  # 脚本任务状态管理
            # syspy.report.set_status(self.status)
            # 睡眠0.5秒
            time.sleep(0.5)


if __name__ == '__main__':
    module = Module()
    syspy.init(module)
    module.main()
