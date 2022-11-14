# -*- coding: utf-8 -*-
# @Date : 2022/9/21 
# @Author : zhong
# @File :requestHandle.py
# @Version : 1.0
# @Project : 
# @Update : 

import json
import time

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
from robot import NetHandle

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value": ["getRobotStatus", "setRobotStatus", "getTerminalStatus", "setTerminalStatus"],
        "type": "complex"
    },
    "addr": {
        "value": "http://localhost:8088/getRobotStatus",
        "type": "string"
    },
    "data": {
        "value": "",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.opt = None
        self.net = NetHandle()
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.opt = args.get("operation", None)

        if time.time() - self.start_time > 60:
            r.setError(f"COMM is over the max time!")
            self.status = MoveStatus.FAILED

        if self.opt == "getRobotStatus":
            pass
        elif self.opt == "setRobotStatus":
            pass
        elif self.opt == "getTerminalStatus":
            pass
        elif self.opt == "setTerminalStatus":
            pass
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED

        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status


if __name__ == '__main__':
    r = SimModule()
    args = {}
    m = Module(r, args)
    while m.status is not MoveStatus.FAILED and m.status is not MoveStatus.FINISHED:
        m.run(r, args)
