# -*- coding: utf-8 -*-
# @Date: 2024/12/08
# @Project: 3.5版本脚本示例
# @Coding:
# @Update:

import time
import queue
import syspy
from syspy import Di, Motor, MF, ScriptStatus


class Module(syspy.BasicModule):
    def __init__(self):
        super().__init__()
        self.opt = None
        self.jack_motor_name = "Motor-003"
        self.motor_speed = 0.1
        self.zero_pos = 0.0
        self.up_di = 6
        self.zero_di = 3
        self.height = 0.03
        self.spinAngle = 0
        self.init_path = True
        self.init_odo = True
        self.goPath_x = 0
        self.goPath_y = 0
        self.goPath_a = 0

        self.task_queue = queue.Queue()
        self.current_task = None
        self.status = ScriptStatus.NONE

    def update_cmd(self, args):
        self.task_queue.put(args)

    def cancel(self):
        self.status = ScriptStatus.NONE

    def suspend(self):
        if self.status == ScriptStatus.RUNNING:
            self.status = ScriptStatus.SUSPENDED

    def resume(self):
        if self.status == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        elif self.status != ScriptStatus.RUNNING:
            self.status = ScriptStatus.NONE

    def reset(self):
        self.spinAngle = 0
        self.init_path = True
        self.init_odo = True
        self.goPath_x = 0
        self.goPath_y = 0
        self.goPath_a = 0

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

    def init_task_args(self):
        print("init_task_args")
        print("===================================================")
        print("***********************task_queue self.current_task", self.current_task)
        try:
            self.current_task = self.task_queue.get(True, 5)  # 取出最先入队的任务
            self.task_id = self.current_task.get('taskId', None)
            self.status = ScriptStatus.RUNNING
        except queue.Empty:
            print("task_queue is empty")
            return

    def load(self):
        print("load: ", self.jack_motor_name, self.height, self.motor_speed, self.up_di)
        print("setMotorPosition(): ",
              Motor.setMotorPosition(self.jack_motor_name, self.height, self.motor_speed, self.up_di))
        if Di.get_di(self.up_di) or Motor.isMotorReached(self.jack_motor_name):
            print("load finish")
            self.status = ScriptStatus.FINISHED

    def unload(self):
        print("unload: ", self.jack_motor_name, self.zero_pos, self.motor_speed, self.zero_di)
        print("setMotorPosition(): ",
              Motor.setMotorPosition(self.jack_motor_name, self.zero_pos, self.motor_speed, self.zero_di))
        if Di.get_di(self.zero_di) or Motor.isMotorReached(self.jack_motor_name):
            print("unload finish")
            self.status = ScriptStatus.FINISHED

    def spin(self):
        print("spin: ", self.spinAngle)
        print("setRobotSpinAngle(): ", MF.setRobotSpinAngle(self.spinAngle, 0))
        finished = MF.spinRun()
        if finished:
            print("spin finish")
            self.status = ScriptStatus.FINISHED

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

    def getCurrentPathProperty(self):
        print("getCurrentPathProperty ==============================================")
        result = MF.getCurrentPathProperty()
        print("getCurrentPathProperty", result)
        self.status = ScriptStatus.FINISHED

    def getLM(self):
        print("getLM ==============================================")
        result = MF.getLM("LM7", True)
        print("getLM", result)
        self.status = ScriptStatus.FINISHED

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

    def script_task_manage(self):
        if self.status is ScriptStatus.NONE:
            self.init_task_args()
        elif self.status is ScriptStatus.RUNNING:
            self.run()
        elif self.status is ScriptStatus.SUSPENDED:
            self.suspend()
        elif self.status is ScriptStatus.FAILED:
            self.cancel()
            self.current_task = None
            self.task_id = None
        elif self.status is ScriptStatus.FINISHED:
            self.status = ScriptStatus.NONE
            self.current_task = None
            self.task_id = None

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        print("task queue: ", list(self.task_queue.queue))
        print("current task: ", self.current_task)
        print("current task id: ", self.task_id)
        print("current task status: ", self.status)

    def main(self):
        while True:
            self.script_task_manage()  # 脚本任务状态管理
            self.print_info()
            # 睡眠0.5秒
            time.sleep(0.5)


if __name__ == '__main__':
    module = Module()
    syspy.init(module)
    module.main()