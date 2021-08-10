import json
import time
import sys
sys.path.append("syspy")
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.rbkSim import SimModule

class Module(BasicModule):
    """货叉测得重量
    """
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.mtime = p.loadParam("measure_time", type="float", default = 3, maxValue = 60.0, minValue = 0.01, unit = "m/s", comment = "mearsure time")
        self.init = True
        self.sum_weight = 0
        self.measure_count = 0
        self.start_time = time.time()
        self.max_weight = p.loadParam("max_weight", type="float", default = 1000, maxValue = 10000000., minValue = 0.01, unit = "kg", comment = "最大重量，超过这个重量报警")
                           
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
        if self.init:
            self.start_time = time.time()
            self.init = False
        self.status = MoveStatus.RUNNING
        weight = r.getForkPressure()
        self.sum_weight = self.sum_weight + weight
        self.measure_count = self.measure_count + 1
        dtime = time.time() - self.start_time
        mean_weight = self.sum_weight/ (self.measure_count * 1.0)
        r.logDebug("[ForkWeigth][{}|{}|{}|{}|{}|{}]".format(
                                weight,self.sum_weight,self.measure_count,dtime,mean_weight,
                                self.max_weight))
        if weight > self.max_weight:
            r.setError("{} over max weight {} kg".format(mean_weight, self.max_weight))
            self.status = MoveStatus.FAILED
        elif dtime > self.mtime:
            self.status = MoveStatus.FINISHED
        js = dict()
        js["mean_weigth"] = mean_weight
        js["weight"] = weight
        r.setInfo(json.dumps(js))
        return self.status

if __name__ == '__main__':
    import syspy.rbkSim, time
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    print(m.run(r, data))
    time.sleep(2.0)
    print(m.run(r, data))