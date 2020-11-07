import json
import time
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.rbkSim import SimModule

"""
####BEGIN DEFAULT ARGS####
{
    "height": {
        "value": 0.09,
        "tips": "货叉抬升高度",
        "unit": "m",
        "type": "double"
    }
}
####END DEFAULT ARGS##### 
"""

class Module(BasicModule):
    """控制货叉抬升到指定高度
       其中self.fork_height需要用户配置， 依据模型文件制定fork电机
       self.max_vel是指举升电机举升的最大速度
       输入是height的json
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.fork_motor = p.loadParam("fork_motor", type="str", default = "motor2", comment = "motor name") #需要配置fork电机的名称
        self.max_vel = p.loadParam("max_vel", type="float", default = 0.1, maxValue = 2.0, minValue = 0.01, unit = "m/s", comment = "fork max speed")
        self.init = True
        self.height = 0
                           
    def run(self, r:SimModule,args:dict):
        """主函数，没有运行周期都会执行run函数

        Args:
            r (SimModule): 是MoveFactory的类，包含了基本的电机控制，状态查询，消息查询的功能
            args ([type]): 输入参数，是个json类

        Returns:
            [type]: 返回运行状态，MoveStatus,用于表明脚本的运行状态
        """
        if self.status == MoveStatus.FINISHED:
            return self.status.value
        self.status = MoveStatus.RUNNING
        if self.init:
            if "height" in args:
                self.height = float(args["height"])
                r.setForkHeight(self.height)
            else:
                r.setError("params error: {}".format(json.dumps(args)))
                self.status = MoveStatus.FAILED
            self.init = False
        if self.status is not MoveStatus.FAILED:
            fork_message = r.fork()
            if "height" in fork_message and "height_in_place" in fork_message:
                if abs(fork_message["height"] - self.height) < 0.01 and fork_message["height_in_place"]:
                    self.status = MoveStatus.FINISHED
        return self.status

if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["height"] = dict()
    data["height"] = 0.4
    print(m.run(r, data))