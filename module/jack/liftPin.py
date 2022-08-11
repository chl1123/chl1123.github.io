# -*- coding: utf-8 -*-
# @Date : 2022/2/10 17:03
# @Author : zhong
# @File :liftPin.py
# @Version : 1.0
# @Project : 天津中汽（五菱工业）issue_pool#2105 https://seer-group.coding.net/p/issue_pool/requirements/issues/2105/detail


import json

from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
from robot import ModuleTool


""" 
####BEGIN DEFAULT ARGS####
{
    "JackOperation": {
        "value": "",
        "default_value": ["JackLoad", "JackUnload"],
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        # 以下DO、DI参数按项目实际情况进行修改，脚本生成的json配置文件也需要同步修改
        self.DO1 = p.loadParam("DO_Head", type="int", default=2, comment="前升降销DO")
        self.DI1 = p.loadParam("DI_HeadUp", type="int", default=1, comment="前升降销上升到位DI")
        self.DI2 = p.loadParam("DI_HeadDown", type="int", default=2, comment="前升降销下降到位DI")
        self.DO2 = p.loadParam("DO_Tail", type="int", default=5, comment="后升降销DO")
        self.DI3 = p.loadParam("DI_TailUp", type="int", default=4, comment="后升降销上升到位DI")
        self.DI4 = p.loadParam("DI_TailDown", type="int", default=5, comment="后升降销下降到位DI")
        self.init = True
        self.status = MoveStatus.NONE
        self.operation = None
        self.state = dict()


    def run(self, r: SimModule, args):
        if self.init:
            pass
        self.status = MoveStatus.RUNNING
        if args.get("JackOperation", None) == "JackLoad":
            self.jack_load(r)
        elif args.get("JackOperation", None) == "JackUnload":
            self.jack_unload(r)
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED
        self.state["args"] = args
        self.state["status"] = self.status
        r.setInfo(json.dumps(self.state))
        return self.status

    def jack_load(self, r: SimModule):
        r.setDO(self.DO1, True)
        r.setDO(self.DO2, True)
        if ModuleTool.check_DI(r, self.DI1):
            r.setDO(self.DO1, False)
        if ModuleTool.check_DI(r, self.DI3):
            r.setDO(self.DO2, False)
        if ModuleTool.check_DI(r, self.DI1) and ModuleTool.check_DI(r, self.DI3):
            self.status = MoveStatus.FINISHED

    def jack_unload(self, r: SimModule):
        r.setDO(self.DO1, True)
        r.setDO(self.DO2, True)
        if ModuleTool.check_DI(r, self.DI2):
            r.setDO(self.DO1, False)
        if ModuleTool.check_DI(r, self.DI4):
            r.setDO(self.DO2, False)
        if ModuleTool.check_DI(r, self.DI2) and ModuleTool.check_DI(r, self.DI4):
            self.status = MoveStatus.FINISHED


if __name__ == '__main__':
    pass
