# -*- coding: utf-8 -*-
# @Time : 2022/7/15
# @Author : qian, zhong
# @Version : V1.2 - 20220715
# @Project: 【罡宜机电】AMB车上层滚筒设备
# @Update :  1. 新增任务运行超时报错； 2. 新增任务完成延时结束；3. 新增复位操作

import time
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "",
        "default_value":["unload","load", "reset"],
        "tips": "运行模式",
        "type": "complex"
    },
    "direction":{
        "value": "",
        "default_value":["left","right"],
        "tips": "进料/出料方向",
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
        self.DO2 = p.loadParam("DO_SemiSpeed", type="int", default=2, comment="皮带半速")
        self.DO3 = p.loadParam("DO_BeltReverse", type="int", default=3, comment="皮带反转")
        self.DO4 = p.loadParam("DO_LeftGoUp", type="int", default=18, comment="左侧挡板升起")
        self.DO5 = p.loadParam("DO_LeftGoDown", type="int", default=19, comment="左侧挡板下降")
        self.DO6 = p.loadParam("DO_RightGoUp", type="int", default=20, comment="右侧挡板升起")
        self.DO7 = p.loadParam("DO_RightGoDown", type="int", default=21, comment="右侧挡板下降")
        self.DI1 = p.loadParam("DI_LeftUpLimit", type="int", default=19, comment="左侧挡板高位")
        self.DI2 = p.loadParam("DI_LeftDownLimit", type="int", default=20, comment="左侧挡板低位")
        self.DI3 = p.loadParam("DI_RightUpLimit", type="int", default=21, comment="右侧挡板高位")
        self.DI4 = p.loadParam("DI_RightDownLimit", type="int", default=22, comment="右侧挡板低位")
        self.DI5 = p.loadParam("DI_LeftSensor", type="int", default=23, comment="左侧物料检测光电")
        self.DI6 = p.loadParam("DI_MiddleSensor", type="int", default=24, comment="中间物料检测光电")
        self.DI7 = p.loadParam("DI_RightSensor", type="int", default=25, comment="右侧物料检测光电")
        self.DI8 = p.loadParam("DI_BeltFault", type="int", default=1, comment="皮带故障")
        self.overtime = p.loadParam("Overtime", type="int", default=60, comment="超时时间")
        self.delay_time = p.loadParam("DelayTime", type="int", default=2, comment="动作延时时间")
        self.delay_flag = None
        self.start_time = time.time()
        self.status = MoveStatus.NONE
        self.report_info = dict()
        r.logInfo(f"init args: {args}")
        self.init = True
        self.init1 = True

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            args_error = False
            if "operation" in args:
                if "direction" not in args and args["operation"] != "reset":
                    r.setError(f"Pls choose load/unload direction")
                    args_error = True
            else:
                r.setError(f"Pls choose operation mode")
                args_error = True
            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED

        if time.time() - self.start_time > self.overtime:
            # self.status = MoveStatus.FAILED
            self.reset(r)
            r.setError(f"task timeout!")
            return self.status

        if args["operation"] == "load" and args["direction"] == "left":
            self.left_load(r)
        elif args["operation"] == "load" and args["direction"] == "right":
            self.right_load(r)
        elif args["operation"] == "unload" and args["direction"] == "left":
            self.left_unload(r)
        elif args["operation"] == "unload" and args["direction"] == "right":
            self.right_unload(r)
        elif args["operation"] == "reset":
            self.reset(r)
        self.report_info["args"] = args
        self.report_info["status"] = self.status

        return self.status

    def left_load(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.DO6, True)  # 右侧挡板上升
            r.setDO(self.DO5, True)  # 左侧挡板下降
            r.setDO(self.DO1, True)  # 皮带转动指令
        if self.check_DI(r, self.DI2):  # 左侧挡板低位的时候
            r.setDO(self.DO5, False)  # 复位左侧挡板下降
            if self.check_DI(r, self.DI3):  # 右侧挡板高位的时候
                r.setDO(self.DO6, False)  # 复位右侧挡板上升
                if self.check_DI(r, self.DI6):  # 中间位光电信号动作时
                    r.setDO(self.DO2, True)  # 皮带半速运行
                if self.check_DI(r, self.DI7):  # 右侧光电信号动作时
                    r.setDO(self.DO2, False)  # 复位皮带半速指令
                    r.setDO(self.DO1, False)  # 复位皮带转动指令
                    r.setDO(self.DO4, True)  # 左侧挡板上升
        if self.check_DI(r, self.DI1) and self.check_DO(r, self.DO4):  # 左侧挡板高位的时候
            if self.delay(self.delay_time):
                r.setDO(self.DO4, False)  # 复位左侧挡板上升
                self.status = MoveStatus.FINISHED

    def right_load(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.DO4, True)  # 左侧挡板上升
            r.setDO(self.DO7, True)  # 右侧挡板下降
            r.setDO(self.DO1, True)  # 皮带转动指令
            r.setDO(self.DO3, True)  # 皮带反转指令
        if self.check_DI(r, self.DI4):  # 右侧挡板低位的时候
            r.setDO(self.DO7, False)  # 复位右侧挡板下降
            if self.check_DI(r, self.DI1):  # 左侧挡板高位的时候
                r.setDO(self.DO4, False)  # 复位左侧挡板上升
                if self.check_DI(r, self.DI6):  # 中间位光电信号动作时
                    r.setDO(self.DO2, True)  # 皮带半速运行
                if self.check_DI(r, self.DI5):  # 左侧光电信号动作时
                    r.setDO(self.DO2, False)  # 复位皮带半速指令
                    r.setDO(self.DO1, False)  # 复位皮带转动指令
                    r.setDO(self.DO3, False)  # 复位皮带反转指令
                    r.setDO(self.DO6, True)  # 右侧挡板上升
        if self.check_DI(r, self.DI3) and self.check_DO(r, self.DO6):  # 右侧挡板高位的时候
            if self.delay(self.delay_time):
                r.setDO(self.DO6, False)  # 复位右侧挡板上升
                self.status = MoveStatus.FINISHED

    def left_unload(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.DO5, True)  # 左侧挡板下降
            r.setDO(self.DO3, True)  # 皮带反转指令
            r.setDO(self.DO1, True)  # 皮带转动指令
        if self.check_DI(r, self.DI2):  # 左侧挡板低位的时候
            r.setDO(self.DO5, False)  # 复位左侧挡板下降
            if not self.check_DI(r, self.DI5) and not self.check_DI(r, self.DI6) and \
                    not self.check_DI(r, self.DI7):  # 左侧光电信号动作时
                r.setDO(self.DO1, False)  # 停皮带机
                r.setDO(self.DO3, False)  # 停反转指令
                r.setDO(self.DO4, True)  # 左侧挡板上升
        if self.check_DI(r, self.DI1) and self.check_DO(r, self.DO4):  # 左侧挡板高位的时候
            if self.delay(self.delay_time):
                r.setDO(self.DO4, False)  # 复位左侧挡板上升
                self.status = MoveStatus.FINISHED

    def right_unload(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.DO7, True)  # 右侧挡板下降
            r.setDO(self.DO1, True)  # 皮带转动指令
        if self.check_DI(r, self.DI4):  # 右侧挡板低位的时候
            r.setDO(self.DO7, False)  # 复位右侧挡板下降
            if not self.check_DI(r, self.DI5) and not self.check_DI(r, self.DI6) and \
                    not self.check_DI(r, self.DI7):  # 左侧光电信号动作时
                r.setDO(self.DO1, False)  # 停皮带机
                r.setDO(self.DO6, True)  # 右侧挡板上升
        if self.check_DI(r, self.DI3) and self.check_DO(r, self.DO6):  # 右侧挡板高位的时候
            if self.delay(self.delay_time):
                r.setDO(self.DO6, False)  # 复位左侧挡板上升
                self.status = MoveStatus.FINISHED

    def reset(self, r: SimModule):
        r.setDO(self.DO1, False)
        r.setDO(self.DO2, False)
        r.setDO(self.DO3, False)
        r.setDO(self.DO4, True)
        r.setDO(self.DO6, True)
        if self.check_DI(r, self.DI1):
            r.setDO(self.DO4, False)
        if self.check_DI(r, self.DI3):
            r.setDO(self.DO6, False)
        if self.check_DI(r, self.DI1) and self.check_DI(r, self.DI3):
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
