# -*- coding: utf-8 -*-
# @Date: 2023/07/5
# @Author: CXN
# @File: comm.py
# @Version: 1.0
# @Project:
# @Coding:https://seer-group.coding.net/p/order_issue_pool/requirements/issues/4131/detail
# @Update: 【现场】【上海烟机】【两个DI任意触发一个即可结束任务】

import json
import sys
import time

sys.path.append("../syspy")
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.rbkSim import SimModule
from syspy.robot import ModuleTool

""" 
####BEGIN DEFAULT ARGS####
{
    "timeout": {
        "value": 60,
        "default_value": 60,
        "type": "int"
    }
}
####END DEFAULT ARGS####
"""

class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.DI1 = p.loadParam("DI1", type="int", default=1, comment="DI 1")
        self.DI2 = p.loadParam("DI2", type="int", default=2, comment="DI 2")
        self.start_time = time.time()
        self.timeout = 60
        self.status = MoveStatus.NONE
        self.tool = ModuleTool
        self.state = {}
        self.init = True
    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            if args.get("timeout",None):
                self.timeout = args["timeout"]
        if self.tool.check_DI(r,self.DI1) or self.tool.check_DI(r,self.DI2):
            self.status = MoveStatus.FINISHED
        self.state["status"] = self.status
        self.state["DI"] = r.Di()
        if time.time() - self.start_time > self.timeout:
            self.status = MoveStatus.FINISHED
            r.setError(f"run time out {self.timeout}s")
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        return self.status

