# -*- coding: utf-8 -*-
# @Date: 2023/01/01
# @Author: zhong
# @File: template.py
# @Version: 1.0
# @Project:
# @Coding:
# @Update:

import json
import time

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import ModuleTool, MotorType, Motor, Robot

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{

}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                                   comment=" 运行超时时间")
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.motor1 = Motor(r, MotorType.LINEAR_MOTOR, "motor-name", -1)
        self.motor1_init_pos = ModuleTool.get_motor_pos(r, "motor-name")
        self.robot = Robot(r)
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            pass

        # 超时判断
        if time.time() - self.start_time > self.timeout:
            r.setError(f"script running timeout")

        # =====处理业务逻辑=====
        pass

        # =====数据上报及日志打印=====
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def cancel(self, r):
        # =====处理任务取消时的业务=====
        r.setNotice(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        r.setNotice(f"suspend task")
        self.status = MoveStatus.SUSPENDED


if __name__ == '__main__':  # 本地运行测试
    r1 = SimModule()
    args1 = {}
    m = Module(r1, args1)
    run_counter = 0
    while m.status is not MoveStatus.FAILED and m.status is not MoveStatus.FINISHED:
        m.run(r1, args1)
        if run_counter > 10:
            break
        else:
            run_counter += 1
