# -*- coding: utf-8 -*-
# @Date : 2022/8/5 
# @Author : zhong
# @File :moveToSite.py
# @Version : 1.0
# @Project : 传入站点名称，导航到该站点
import json

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule

"""
####BEGIN DEFAULT ARGS####
{
    "site": {
        "value": "",
        "tips": "目标站点",
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
        self.site = ""
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.site = args.get("site", "")
        if self.site:
            task = {"id": self.site}
            r.addMoveTask(json.dumps(task))
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"args error: {args}")
        return self.status


if __name__ == '__main__':
    args = {"site": "LM1"}
    r = SimModule()
    m = Module(r, args)
    m.run(r, args)
