# -*- coding: utf-8 -*-
# @Date: 2024/12/08
# @Project: 3.5版本脚本示例
# @Coding:
# @Update:

import time
import sys
from collections import deque

sys.path.append('/opt/.data/rbk/resources/scripts/')
try:
    import syspy
    from syspy import Di, Motor, Battery
    from syspy.module import BasicModule, ScriptStatus
except:
    print("import error")

# =======脚本输入参数=======
# doc
"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "load",
        "default_value":["load", "unload"],
        "type": "complex"
    },
    "height":{
        "value": 0,
        "type": "float"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self):
        super(Module, self).__init__()
        self.timeout = 60
        self.jack_motor_name = "Motor-003"
        self.init = True
        self.status = ScriptStatus.NONE
        self.report_info = dict()
        # self.motor = Motor()
        self.motor_speed = 0.1
        self.zero_pos = 0.0
        self.up_di = 6
        self.zero_di = 3
        self.task_queue = deque()
        self.current_task = None
        self.current_task_id = None
        self.opt = None
        self.height = 0.03
        syspy.report.set_status(self.status)

    def update_cmd(self, args):
        self.task_queue.append(args)

    def cancel(self):
        self.status = ScriptStatus.FAILED
        syspy.report.set_status(self.status)



    def suspend(self):
        self.status = ScriptStatus.SUSPENDED
        syspy.report.set_status(self.status)

    def run(self):
        self.status = ScriptStatus.RUNNING
        self.opt = self.current_task.get('operation', None)
        self.height = self.current_task.get('height', None)
        if self.opt == "load":
            self.load()
        elif self.opt == "unload":
            self.unload()
        else:
            pass
        syspy.report.set_status(self.status)

    def reset(self):
        self.status = ScriptStatus.RUNNING
        syspy.report.set_status(self.status)

    def init_task_args(self):
        if self.task_queue:  # 判断任务队列不为空
            print("task_queue self.current_task", self.current_task)
            self.current_task = self.task_queue.popleft()  # 取出最先入队的任务
            self.current_task_id = self.current_task.get('taskId', None)
            self.status = ScriptStatus.RUNNING
            syspy.report.set_task_id(self.current_task_id)
            syspy.report.set_status(self.status)
        else:
            pass

    def get_robot_info(self):
        pass

    def load(self):
        print("load: ", self.jack_motor_name, self.height, self.motor_speed, self.up_di)
        print("setMotorPositionRPC(): ", Motor.setMotorPositionRPC(self.jack_motor_name, self.height, self.motor_speed, self.up_di))
        if Di.get_di(self.up_di) or Motor.isMotorReachedRPC(self.jack_motor_name):
            print("load finish")
            self.status = ScriptStatus.FINISHED

    def unload(self):
        print("unload: ", self.jack_motor_name, self.zero_pos, self.motor_speed, self.zero_di)
        print("setMotorPositionRPC(): ", Motor.setMotorPositionRPC(self.jack_motor_name, self.zero_pos, self.motor_speed, self.zero_di))
        if Di.get_di(self.zero_di) or Motor.isMotorReachedRPC(self.jack_motor_name):
            print("unload finish")
            self.status = ScriptStatus.FINISHED

    def script_task_manage(self):
        self.status = syspy.report.run_status
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

    def print_info(self):
        print("current task_queue: ", self.task_queue)
        print("current task: ", self.current_task)
        print("current task id: ", self.current_task_id)
        print("current task status: ", self.status)

    def main(self):
        while True:
            self.script_task_manage()  # 脚本任务状态管理
            self.print_info()
            # syspy.report.set_status(self.status)
            # 睡眠50毫秒
            time.sleep(0.5)


if __name__ == '__main__':
    module = Module()
    syspy.init(module)
    module.main()