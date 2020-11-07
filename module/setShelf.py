import json
import time
from syspy.rbk import MoveStatus, BasicModule
from syspy.rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{
    "object": {
        "value": "",
        "tips": "recfile",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""
class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.status = MoveStatus.RUNNING
    def run(self, r:SimModule,args):
        if self.status is not MoveStatus.FINISHED:
            if "object" in args:
                if r.setLocalShelfArea(args["object"]):
                    self.status = MoveStatus.FINISHED
                else:
                    self.status = MoveStatus.FAILED
            else:
                r.setError("args doesn't have object")
                self.status = MoveStatus.FAILED
        return self.status.value

if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["object"] = dict()
    data["object"] = "hello"
    m.run(r, data)