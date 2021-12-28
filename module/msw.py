# -*- coding: utf-8 -*-
# @Date : 2021/12/28 16:03
# @Author : zhong
# @File :msw.py
# @Version : 1.0
# @Project : 迈斯维

import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value": [
            "RollerLoad", "RollerUnLoad", "RollerStop"
        ],
        "tips": "tips",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


def check_di(r: SimModule, di: int):
    DI = r.Di()
    nodes = DI.get('node', list())
    for node in nodes:
        if node['id'] == di:
            return node['status']
    return False


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        # 辊筒检测光电
        self.di1 = p.loadParam("di1", type="int", default=2, maxValue=100, minValue=0, comment="inside di")  # inside
        self.di2 = p.loadParam("di2", type="int", default=5, maxValue=100, minValue=0, comment="outside di")  # outside
        self.di3 = p.loadParam("di3", type="int", default=4, maxValue=100, minValue=0, comment="signal di")  # signal di 4
        self.do2 = p.loadParam("do2", type="int", default=2, maxValue=100, minValue=0, comment="signal do")  # signal do 2
        # 辊筒 正转 / 反转
        self.roller_positive = p.loadParam("roller_positive", type="int", default=1, maxValue=100, minValue=0, comment="do id")  # 正转
        self.roller_reversal = p.loadParam("roller_reversal", type="int", default=4, maxValue=100, minValue=0, comment="do id")  # 反转
        self.over_time = p.loadParam("over_time", type="float", default=120.0, maxValue=3600.0, minValue=0.0, unit="s", comment="time")
        self.preload_time = p.loadParam("preload_time", type="float", default=5.0, maxValue=3600.0, minValue=0.0, unit="s", comment="time")
        self.state = dict()
        self.init = True
        self.load_goods = False
        self.unload_goods = False
        self.start_time = time.time()
        self.status = MoveStatus.NONE
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        run_time = time.time() - self.start_time
        if self.init:
            self.init = False
            r.setDO(self.do2, True)
        if run_time > self.over_time:   # 运行超时
            r.setError(f"Running time out")
            self.status = MoveStatus.FAILED
        if "operation" in args:
            opt = args.get("operation", False)
            if opt == "RollerLoad":
                self.load(r)
            elif opt == "RollerUnLoad":
                self.unload(r)
            elif opt == "RollerStop":
                self.stop(r)
            elif opt == "RollerPreLoad":
                self.preload(r)
            else:
                r.setError(f"args error: {args}")
                self.status = MoveStatus.FAILED
        if not r.publishSpeed():
            self.status = MoveStatus.FAILED
        self.state["status"] = self.status
        self.state["args"] = args
        r.setInfo(json.dumps(self.state))
        r.logDebug(json.dumps(self.state))
        return self.status

    def load(self, r):
        # if check_di(r, self.di3) and not check_di(r, self.di1):
        if check_di(r, self.di3):
            self.load_goods = True
            r.setDO(self.roller_reversal, True)
        if check_di(r, self.di1) and self.load_goods:
            r.setDO(self.roller_reversal, False)
            r.setDO(self.do2, False)
            self.status = MoveStatus.FINISHED

    def preload(self, r):
        r.setDO(self.roller_reversal, True)
        run_time = time.time() - self.start_time
        if run_time > self.preload_time:
            r.setDO(self.roller_reversal, False)
            self.status = MoveStatus.FINISHED

    def unload(self, r):
        if check_di(r, self.di3) and check_di(r, self.di1):
            r.setDO(self.roller_positive, True)
            self.unload_goods = True
        if not check_di(r, self.di1) and not check_di(r, self.di2) and not check_di(r, self.di3):
            if self.unload_goods:
                r.setDO(self.roller_positive, False)
                r.setDO(self.do2, False)
                self.status = MoveStatus.FINISHED
        #if not self.unload_goods and not check_di(r, self.di1):
        #    r.setError(f"No material")
        #    self.status = MoveStatus.FAILED

    def stop(self, r):
        r.setDO(self.roller_reversal, False)
        r.setDO(self.roller_positive, False)
        r.setDO(self.do2, False)
        self.status = MoveStatus.FINISHED


if __name__ == '__main__':
    pass
