import Hairou
import json
import time
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule
####BEGIN DEFAULT ARGS####
{
    "object": {
        "value": "",
        "tips": "recfile",
        "type": "string"
    }
}
####END DEFAULT ARGS####

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.status = MoveStatus.RUNNING
        self.h = Hairou.Hairou("192.168.192.20",4172)
        if self.h.connect():
            self.h.initDevice()
    def run(self, r:SimModule,args):
        if self.status is not MoveStatus.FINISHED:
            state = self.h.getReport()
            print(state)
            r.setInfo(json.dumps(state))
            self.status = MoveStatus.RUNNING
        return self.status.value
    def cancel(self, r:SimModule):
        r.logInfo("script cancel")
        self.h.disconnect()
        self.status = MoveStatus.NONE