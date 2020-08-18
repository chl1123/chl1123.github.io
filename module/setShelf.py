import json
import time
from rbk import MoveStatus, BasicModule

class Module(BasicModule):
    def __init__(self, r, args):
        super(Module, self).__init__()
    def run(self, r,args):
        if "object" in args:
            r.setLocalShelfArea(args["object"])
            self.status = MoveStatus.FINISHED
        else:
            r.setError(53000, "args doesn't have object")
            self.status = MoveStatus.FAILED
        return self.status.value
