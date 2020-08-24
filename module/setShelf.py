import json
import time
from rbk import MoveStatus, BasicModule

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
    def __init__(self, r, args):
        super(Module, self).__init__()
    def run(self, r,args):
        if "object" in args:
            r.setLocalShelfArea(args["object"]["value"])
            self.status = MoveStatus.FINISHED
        else:
            r.setError(53000, "args doesn't have object")
            self.status = MoveStatus.FAILED
        return self.status.value

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["object"] = dict()
    data["object"]["value"] = "hello"
    m.run(r, data)