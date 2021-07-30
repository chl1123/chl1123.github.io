
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{
    "name": {
        "value": "",
        "tips": "音频名称",
        "unit": "",
        "type": "string"
    },
    "loop":{
        "value":1,
        "tips": "1: loop, 0: once",
        "type": "int"
    },
    "stop":{
        "value":1,
        "tips": "1: close, 0: none",
        "type": "int"
    }   
}
####END DEFAULT ARGS####
"""
class Module(BasicModule):
    """让音乐响起来,默认只播放一遍
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.init = True
        self.name = ""
        self.loop = False
        self.stop = False        
    def run(self, r:SimModule,args:json):
        """主函数，每个运行周期都会执行run函数

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
            if "name" in args:
                self.name = args["name"]
            if "loop" in args:
                self.loop = args["loop"] > 0
            if "stop" in args:
                self.stop = args["stop"] > 0
            self.init = False
        if self.name is not "" and self.status is not MoveStatus.FAILED:
            r.setSound(self.name, self.loop)
        else:
            r.logInfo("no sound!")
        if self.stop:
            r.stopSound(self.stop)
        self.status = MoveStatus.FINISHED
        return self.status
    def cancel(self, r: SimModule):
        r.stopSound(True)
        self.status = MoveStatus.NONE

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["name"] = "hello"
    data["loop"] = 1
    data["stop"] = 1
    print(m.run(r, data))