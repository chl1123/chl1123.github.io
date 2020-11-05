
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

class Module(BasicModule):
    """让音乐响起来,默认只播放一遍
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.init = True    
        self.id = []        
        self.id_status = []
        self.timeout = None
        self.start = time.time()
        self.status = MoveStatus.NONE
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
            for key in args.keys():
                if key is not "timeout":
                    self.id.append(int(key))
                    self.id_status.append(args.get(key,True))
                else:
                    self.timeout = args.get("timeout")
            self.start = time.time()
            self.init = False
        dis = r.Di()
        wait_flag = False
        for tmp_id, tmp_v in zip(self.id, self.id_status):
            for di in dis:
                if tmp_id == di.get('id') and tmp_v == di.get('status', True):
                    wait_flag = True
                    break
        if not wait_flag:
            self.status = MoveStatus.FINISHED
        else:
            if self.timeout is not None:
                dt = time.time() - self.start_time
                if dt > self.timeout:
                    self.status = MoveStatus.FINISHED
        return self.status

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = {"6":True,"8":False}
    print(m.run(r, data))