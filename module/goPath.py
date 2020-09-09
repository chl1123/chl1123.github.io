import json
import time
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule
####BEGIN DEFAULT ARGS####
{
    "x": {
      "value": 1,
	  "tips":"x",
      "type":"double"
	  },
	"y": {
      "value": 1,
	  "tips":"x",
      "type":"double"
    },
	"theta": {
      "value": 1,
	  "tips":"x",
      "type":"double"
 }
}
####END DEFAULT ARGS####
class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.goal = [0,0,0]
        self.init = False
        self.status = MoveStatus.NONE
    def run(self, r:SimModule,args):
        self.status = MoveStatus.RUNNING
        if not self.init:
            self.init = True
            if "x" in args:
                self.goal[0] = float(args["x"])
            if "y" in args:
                self.goal[1] = float(args["y"])
            if "theta" in args:
                self.goal[2] = float(args["theta"])
            r.logInfo("goal: " + str(self.goal))
            r.resetPath()
            r.setPathOnRobot([0,self.goal[0]], [0, self.goal[1]], self.goal[2])
        r.goPath()
        if r.isPathReached():
            self.status = MoveStatus.FINISHED
        else:
            self.status = MoveStatus.RUNNING
        return self.status.value
    def reset(self):
        self.status = MoveStatus.NONE
        self.init = False
