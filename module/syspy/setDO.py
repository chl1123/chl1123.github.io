
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{
    "DO": {
        "value": [{"id":1,"status":true}],
        "tips": "DO列表",
        "type": "json"
    }
}
####END DEFAULT ARGS####
"""
class Module(BasicModule):
    """控制多个DO的开关
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.init = True    
        self.id = []        
        self.id_status = []
        self.status = MoveStatus.NONE
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
            if type(args) is dict and "DO" in args:
                data = args["DO"]
                self.id = [int(v.get('id')) for v in data]
                self.id_status = [v.get('status') for v in data]
            else:
                r.setError(" No DO in task !!!")
                self.status = MoveStatus.FAILED
                return self.status
            self.init = False
        for id, status in zip(self.id, self.id_status):
            r.setDO(id, status)
        self.status = MoveStatus.FINISHED
        return self.status

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = {"DO": [{"id":1, "status":True},{"id":2, "status":False},{"id":3, "status":False}]}
    print(m.run(r, data))