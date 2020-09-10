import json
import time
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule
####BEGIN DEFAULT ARGS####
{
    "x": {
      "value": 1,
      "tips":"x",
      "type":"double",
      "unit": "m"
      },
    "y": {
      "value": 1,
      "tips":"x",
      "type":"double",
      "unit": "m"
    },
    "theta": {
      "value": 1,
      "tips":"x",
      "type":"double",
      "unit": "rad"
    },
    "reachAngle": {
      "value": 3.14,
      "tips":"x",
      "type":"double",
      "unit": "rad"
    },
    "reachDist": {
      "value": 0.005,
      "tips":"x",
      "type":"double",
      "unit": "m"
    },
    "useOdo": {
      "value": 1,
      "type":"int"
    },
    "backMode":{
      "value": 1,
      "type":"int"
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
            r.resetPath()
            if "x" in args and "y" in args and "theta" in args:
                if "x" in args:
                    self.goal[0] = float(args["x"])
                if "y" in args:
                    self.goal[1] = float(args["y"])
                if "theta" in args:
                    self.goal[2] = float(args["theta"])
                if "reachAngle" in args:
                    r.setPathReachAngle(float(args["reachAngle"]))
                if "reachDist" in args:
                    r.setPathReachDist(float(args["reachDist"]))
                if "useOdo" in args:
                    r.setPathUseOdo(bool(int(args["useOdo"])))
                if "backMode" in args:
                    r.setPathBackMode(bool(int(args["backMode"])))
                r.logInfo("goal: " + str(self.goal))
                r.setPathOnRobot([0,self.goal[0]], [0, self.goal[1]], self.goal[2])
            else:
                r.setError("args error: {}".format(json.dumps(args)))
                self.status = MoveStatus.FAILED
        if self.status != MoveStatus.FAILED:
            r.goPath()
            if r.isPathReached():
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING
        r.setInfo(json.dumps(args))
        return self.status.value
    def reset(self):
        self.status = MoveStatus.NONE
        self.init = False
