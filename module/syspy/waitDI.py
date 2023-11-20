
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{   
    "DI": {
        "value": [{"id":1,"status": true}],
        "tips": "DI列表",
        "type": "json"
    },
    "timeout": {
        "value": 10,
        "tips": "超时时间",
        "type": "int"
    },
    "soundName": {
        "value": "",
        "tips": "等待DI时，音频名称",
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
        self.id = []        
        self.id_status = []
        self.timeout = None
        self.start = time.time()
        self.status = MoveStatus.NONE
        self.soundName = ""
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
            dis = args.get("DI",[])
            self.id = [v.get("id") for v in dis]
            self.id_status = [v.get("status") for v in dis]
            self.timeout = args.get("timeout",None)
            self.soundName = args.get("soundName","")
            self.start = time.time()
            self.init = False
        dis = r.Di()
        wait_flag = False
        for tmp_id, tmp_v in zip(self.id, self.id_status):
            nodes = dis.get('node', [])
            for di in nodes:
                cur_id = di.get('id', None)
                cur_status = di.get('status', None)
                if cur_id is None or cur_status is None:
                    continue
                elif tmp_id == cur_id and tmp_v is not cur_status:
                    wait_flag = True
                    break
        if not wait_flag:
            self.status = MoveStatus.FINISHED
        else:
            if self.timeout is not None:
                dt = time.time() - self.start_time
                if dt > self.timeout:
                    self.status = MoveStatus.FINISHED
        if self.status is not MoveStatus.FINISHED:
            r.setSound(self.soundName, True)
        return self.status

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = {"DI": [{"id":1, "status":True},{"id":2, "status":False}]}
    print(m.run(r, data))