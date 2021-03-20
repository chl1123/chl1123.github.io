
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{
    "task": {
        "value": "",
        "tips": "任务",
        "unit": "",
        "type": "string"
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
        self.status = MoveStatus.NONE
        self.task = ""
    def run(self, r:SimModule,args):
        """主函数，每个运行周期都会执行run函数

        Args:
            r (SimModule): 是MoveFactory的类，包含了基本的电机控制，状态查询，消息查询的功能
            args ([type]): 输入参数，是个json类

        Returns:
            [type]: 返回运行状态，MoveStatus,用于表明脚本的运行状态
        """
        if self.status == MoveStatus.FINISHED:
            return self.status
        self.status = MoveStatus.RUNNING
        if self.init:
            self.task = args.get("task","")
            self.init = False
        if type(self.task) == str:
            r.logDebug('str')
            r.addMoveTask(str(self.task))
        elif type(self.task) == dict:
            r.logDebug('dict')
            r.addMoveTask(json.dumps(self.task))
        else:
            r.setError('args error {}'.format(json.dumps(args)))
        self.status = MoveStatus.FINISHED
        return self.status

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = {"task":{"id":"LM1"}}
    print(m.run(r, data))