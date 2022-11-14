# -*- coding: utf-8 -*-
# @Date : 2022/01/01
# @Author : zhong
# @File :template.py
# @Version : 1.0
# @Project :
# @Update :

import json
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer

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
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            pass

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
        pass
        r.logInfo(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        pass
        r.logInfo(f"suspend task")
        self.status = MoveStatus.SUSPENDED


if __name__ == '__main__':  # 本地运行测试
    r = SimModule()
    args = {}
    m = Module(r, args)
    run_counter = 0
    r.setMotorPosition("", 5, 0.3)
    while m.status is not MoveStatus.FAILED and m.status is not MoveStatus.FINISHED:
        m.run(r, args)
        if run_counter > 10:
            break
        else:
            run_counter += 1
