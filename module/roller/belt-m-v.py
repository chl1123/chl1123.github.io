# -*- coding: utf-8 -*-
# @Time : 2022/7/15
# @Author :  zhong
# @Version : V1.3 - 20220729
# @Project: 【柯林】AMB车上层滚筒设备
# @Update :  1. 新增任务完成延时结束

import time
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "",
        "default_value":["unload","load"],
        "tips": "运行模式",
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
        self.DO1 = p.loadParam("DO_BeltGo", type="int", default=5, comment="皮带前转")
        self.DO2 = p.loadParam("DO_BeltConverse", type="int", default=6, comment="皮带反向")
        self.DO3 = p.loadParam("DO_InGoUp", type="int", default=3, comment="内侧挡板升起")
        self.DO4 = p.loadParam("DO_ExGoUp", type="int", default=7, comment="外侧挡板升起")
        self.DI5 = p.loadParam("DI_LeftSensor", type="int", default=0, comment="尾侧物料检测光电")
        self.DI6 = p.loadParam("DI_MiddleSensor", type="int", default=1, comment="中间物料检测光电")
        self.DI7 = p.loadParam("DI_RightSensor", type="int", default=5, comment="前侧物料检测光电")
        self.status = MoveStatus.NONE
        self.delay_flag = None
        self.init = True
        self.init1 = True
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            args_error = False
            if "operation" in args:
                if args["operation"] == "load":
                    if self.check_DI(r, self.DI5) or self.check_DI(r, self.DI6) or self.check_DI(r, self.DI7):
                        r.setError(f"can't load bcs agv has goods")
                        args_error = True
                elif args["operation"] == "unload":
                    if not self.check_DI(r, self.DI5) and not self.check_DI(r, self.DI6):
                        r.setError(f"can't unload bcs agv has no goods")
                        args_error = True
            else:
                r.setError(f"Pls choose operation mode")
                args_error = True
            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED
        if args["operation"] == "load":
            self.load(r)
        elif args["operation"] == "unload":
            self.unload(r)
        return self.status

    def load(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.DO3, False)  # 内侧挡板下降
            r.setDO(self.DO4, False)  # 外侧挡板下降
            r.setDO(self.DO2, True)  # 皮带转动指令
            r.setDO(self.DO1, True)  # 皮带转动指令
        if self.check_DI(r, self.DI6) and self.check_DI(r, self.DI5):  # 右侧位光电信号动作时
            r.setDO(self.DO2, False)  # 复位皮带转动
            r.setDO(self.DO1, False)  # 复位皮带转动
            r.setDO(self.DO3, True)  # 内侧挡板上升
            r.setDO(self.DO4, True)  # 外侧挡板上升
            r.setGoodsShape(0, 0, 0)
            self.status = MoveStatus.FINISHED

    def unload(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.DO3, False)  # 内侧挡板下降
            r.setDO(self.DO4, False)  # 外侧挡板下降
            r.setDO(self.DO2, True)  # 皮带fan转动指令
            r.setDO(self.DO1, False)  # 皮带fan转动指令
        if not self.check_DI(r, self.DI7) and not self.check_DI(r, self.DI6) and not self.check_DI(r, self.DI5):  # 检测无光电动作时
            r.clearGoodsShape()
            if self.delay(2):
                r.setDO(self.DO1, False)  # 复位皮带反转动
                r.setDO(self.DO2, False)  # 复位皮带转动指令
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

    @staticmethod
    def check_DO(r: SimModule, do: int):
        """
        检测单个DO是否被触发
        :param r: SimModule类对象
        :param do: 需要检测的DO
        :return: 返回指定DO的状态，若DO不存在返回False
        """
        DO = r.Do()
        nodes = DO.get('node', list())
        for node in nodes:
            if node['id'] == do:
                return node['status']
        return False

    def delay(self, second):
        """
        延时 second 秒
        :param second:
        :return: 延时完成返回True
        """
        if self.delay_flag is None:
            self.delay_flag = time.time()
        if time.time() - self.delay_flag > second:
            self.delay_flag = None
            return True
        return False


if __name__ == '__main__':
    pass
