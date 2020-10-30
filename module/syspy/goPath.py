import json
import time
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule
import math
####BEGIN DEFAULT ARGS####
{
    "x": {
      "value": 1,
      "tips":"x 必填",
      "type":"double",
      "unit": "m"
      },
    "y": {
      "value": 1,
      "tips":"y 必填",
      "type":"double",
      "unit": "m"
    },
    "theta": {
      "value": 1,
      "tips":"世界坐标系下的朝向",
      "type":"double",
      "unit": "rad"
    },
    "reachAngle": {
      "value": 3.14,
      "tips":"到点角度精度",
      "type":"double",
      "unit": "rad"
    },
    "reachDist": {
      "value": 0.005,
      "tips":"到点距离精度",
      "type":"double",
      "unit": "m"
    },
    "useOdo": {
      "value": 1,
      "tips":"是否使用里程定位，默认为否",
      "type":"int"
    },
    "backMode":{
      "value": 1,
      "tips":"是否倒走",
      "type":"int"
    },
    "coordinate":{
      "value": "robot",
      "default_value":[
      "robot","world"
      ],
      "tips": "目标点的坐标系，必填",
      "type": "complex"  
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
        if r.errorExits(52111):
            self.status = MoveStatus.FAILED
            return self.status.value
        if not self.init:
            self.init = True
            r.resetPath()
            if "x" in args and "y" in args and "coordinate" in args:
                if "x" in args:
                    self.goal[0] = float(args["x"])
                if "y" in args:
                    self.goal[1] = float(args["y"])
                if "theta" in args:
                    self.goal[2] = float(args["theta"])
                    if "reachAngle" in args:
                        r.setPathReachAngle(float(args["reachAngle"]))
                else:
                    r.setPathReachAngle(math.pi)
                if "reachAngle" in args:
                    r.setPathReachAngle(float(args["reachAngle"]))
                if "reachDist" in args:
                    r.setPathReachDist(float(args["reachDist"]))
                if "useOdo" in args:
                    r.setPathUseOdo(bool(int(args["useOdo"])))
                if "backMode" in args:
                    r.setPathBackMode(bool(int(args["backMode"])))
                r.logInfo("goal: " + str(self.goal))
                if args["coordinate"] == "robot":
                    r.setPathOnRobot([0,self.goal[0]], [0, self.goal[1]], self.goal[2])
                elif args["coordinate"] == "world":
                    r.setPathOnWorld([0,self.goal[0]], [0, self.goal[1]], self.goal[2])
                else:
                    r.setError("coordinate only support robot and world. Input is {}".format(args["coordinate"]))
                    self.status = MoveStatus.FAILED
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
