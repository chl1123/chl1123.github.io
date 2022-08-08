# -*- coding: utf-8 -*-

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
import time

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "",
        "default_value":[
        "unload","load"
        ],
        "tips": "tips",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        # 以下DO、DI参数按项目实际情况进行修改，脚本生成的json配置文件也需要同步修改
        self.DO1 = p.loadParam("DO_BeltGo", type="int", default=1, comment="皮带正转")
        self.DO2 = p.loadParam("DO_LeftGoUp", type="int", default=20, comment="左侧挡板升起")
        self.DO3 = p.loadParam("DO_LeftGoDown", type="int", default=21, comment="左侧挡板下降")
        self.DO4 = p.loadParam("DO_RightGoUp", type="int", default=18, comment="右侧挡板升起")
        self.DO5 = p.loadParam("DO_RightGoDown", type="int", default=19, comment="右侧挡板下降")
        self.DI1 = p.loadParam("DI_LeftUpLimit", type="int", default=21, comment="左侧挡板高位")
        self.DI2 = p.loadParam("DI_LeftDownLimit", type="int", default=22, comment="左侧挡板低位")
        self.DI3 = p.loadParam("DI_RightUpLimit", type="int", default=19, comment="右侧挡板高位")
        self.DI4 = p.loadParam("DI_RightDownLimit", type="int", default=20, comment="右侧挡板低位")
        self.DI5 = p.loadParam("DI_LeftSensor", type="int", default=25, comment="左侧物料检测光电")
        self.DI6 = p.loadParam("DI_MiddleSensor", type="int", default=24, comment="中间物料检测光电")
        self.DI7 = p.loadParam("DI_RightSensor", type="int", default=23, comment="右侧物料检测光电")
        self.DI8 = p.loadParam("DI_BeltFault", type="int", default=2, comment="皮带故障")
        self.delay_time = p.loadParam("Delay_time", type="int", default=1, comment="等待时间")
        self.status = MoveStatus.NONE
        self.run_time = 0

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.check_DI(r, self.DI8):
            r.setError(f"belt error: {self.DI8}")
            self.status = MoveStatus.FAILED
        args_error = False
        if "operation" in args:
            if args["operation"] == "unload":
                self.unload(r)
            elif args["operation"] == "load":
                self.load(r)
            else:
                args_error = True
        if args_error:
            if not r.errorExits(53000):
                r.setError(f"args error: {args}")
                self.status = MoveStatus.FAILED

    def load(self, r: SimModule):
        r.setDO(self.DO2, True)                    #左侧挡板上升
        r.setDO(self.DO5, True)                     #右侧挡板下降
        r.setDO(self.DO1, True)                     #皮带转动指令
        r.setNotice(f"DI4: {self.check_DI(r, self.DI4)} --- DI1: {self.check_DI(r, self.DI1)} --- DI6: {self.check_DI(r, self.DI6)}")
        if self.check_DI(r, self.DI4):              #右侧挡板低位的时候
            r.setDO(self.DO5, False)                #复位右侧挡板下降
        if self.check_DI(r, self.DI1):              #左侧侧挡板低位的时候
            r.setDO(self.DO2, False)                #复位左侧挡板下降
        if self.check_DI(r, self.DI6):             #中间位光电信号动作时
            r.setDO(self.DO1, False)            #停皮带机
            r.setDO(self.DO4, True)             #右侧挡板上升
            if self.check_DI(r, self.DI3):          #右侧挡板高位的时候
                r.setDO(self.DO4, False)            #复位右侧挡板上升
                self.status = MoveStatus.FINISHED

    def unload(self, r: SimModule):
        r.setDO(self.DO3, True)                     #左侧挡板下降
        r.setDO(self.DO1, True)                 #皮带转动指令
        if self.check_DI(r, self.DI2):              #左侧挡板低位的时候
            r.setDO(self.DO3, False)                #复位左侧挡板下降
            if not self.check_DI(r, self.DI5):              #左侧光电信号动作时
            #self.run_time = time.time()
            #wait_time = time.time() - self.run_time
            #if wait_time > self.delay_time:
                r.setDO(self.DO1, False)            #停皮带机
                r.setDO(self.DO2, True)             #左侧挡板上升
                if self.check_DI(r, self.DI1):          #左侧挡板高位的时候
                    r.setDO(self.DO2, False)            #复位左侧挡板上升
                    self.status = MoveStatus.FINISHED

    @staticmethod
    def check_DI(r: SimModule, di: int):
        """
        检测单个DI是否被触发
        :param r: SimModule类对象
        :param di: 需要检测的DI
        :return: 返回指定DI的状态，若DI不存在返回False
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node['id'] == di:
                return node['status']
        return False


if __name__ == '__main__':
    pass
