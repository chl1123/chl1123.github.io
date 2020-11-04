
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

####BEGIN DEFAULT ARGS####
{
    "do": {
        "value": "",
        "tips": "DO列表",
        "unit": "",
        "type": "string"
    },
    "status":{
        "value":1,
        "tips": "1: open, 0: close",
        "type": "int"
    }
}
####END DEFAULT ARGS####

class Module(BasicModule):
    """让音乐响起来,默认只播放一遍
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.init = True    
        self.id = []        
        self.id_status = True
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
            if "do" in args:
                self.id = args["do"]
            if "status" in args:
                self.id_status = bool(args['status'])
            self.init = False
        for id in self.id:
            r.setDO(id, self.id_status)
        self.status = MoveStatus.FINISHED
        return self.status

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["do"] = [1,2,3,4]
    data["status"] = 2
    print(m.run(r, data))