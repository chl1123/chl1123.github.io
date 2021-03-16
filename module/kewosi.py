
import json
import time
import sys
sys.path.append("syspy")
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{
    "time": {
        "value": 1,
        "tips": "time",
        "type": "double",
        "unit": "min"
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
        self.di_id = [5,6,7,8] #可修改
        self.do_id = 1 #可修改       
        self.id_status = []
        self.status = MoveStatus.NONE
        self.time = 0
        self.start_time = time.time()
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
            if "time" in args:
                self.time = args["time"]
            self.init = False
        openDO = True
        di = r.Di()
        for node in di['node']:
            if node['id'] in self.di_id:
                status = node.get('status',False)
                if status:
                    openDO = False
                    break
        r.setDO(self.do_id, openDO)
        cur_time = time.time()
        d_time = cur_time - self.start_time
        r.logDebug('kewosi|{}|{}|{}'.format(d_time, self.time,openDO))
        if d_time >= self.time * 60:
            self.status = MoveStatus.FINISHED
        else:
            self.status = MoveStatus.RUNNING
        return self.status

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = {"time": 1}
    print(m.run(r, data))