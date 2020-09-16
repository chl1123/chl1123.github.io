
import json
import time
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule

####BEGIN DEFAULT ARGS####
{
    "heigth": {
        "value": 1.0,
        "tips": "货叉抬升高度",
        "unit": "m",
        "type": "double"
    }
}
####END DEFAULT ARGS####

class Module(BasicModule):
    """控制货叉抬升到指定高度
       其中self.fork_height需要用户配置， 依据模型文件制定fork电机
       self.max_vel是指举升电机举升的最大速度
       输入是height的json
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.fork_motor = "forkMotor" #需要配置fork电机的名称
        self.max_vel = 0.1 #货叉电机的最大速度
        self.init = True
        self.height = 0
                           
    def run(self, r:SimModule,args):
        if self.status == MoveStatus.FINISHED:
            return self.status.value
        self.status = MoveStatus.RUNNING
        if self.init:
            if "height" in args:
                self.height = float(args["height"])
            else:
                r.setError("params error: {}".format(json.dumps(args)))
                self.status = MoveStatus.FAILED
            self.init = False
        if self.status is not MoveStatus.FAILED:
            if r.isMotorPositionReached(self.fork_motor, self.height, -1):
                self.status = MoveStatus.FINISHED
            else:
                r.setMotorPosition(self.fork_motor, self.height, self.max_vel, -1)
        return self.status.value

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["height"] = dict()
    data["height"] = 0.3
    m.run(r, data)