# -*- coding: utf-8 -*-
# @Time : 2022/8/31
# @Author : qian, zhong
# @project ： 艾斯达克双滚筒车
# @File :double.py
# @Version: 1.9
# @Update：增加卸货时辊筒停转延时时间，可配置
import time
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer


"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value":"",
        "default_value":[
            "load",
            "unload"
        ],
        "tips":"操作",
        "type":"complex"
    },
    "direction":{
        "value":"",
        "default_value":[
            "left",
            "right"
        ],
        "tips":"进/出料方向",
        "type":"complex"
    },
    "position":{
        "value":"",
        "default_value":[
            "front",
            "rear"
        ],
        "tips":"前后辊筒选择",
        "type":"complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super().__init__()
        p = ParamServer(__file__)
        self.di1 = p.loadParam("front_roller_left_detect", type="int", default=19, comment="前辊筒左侧检测光电")
        self.di2 = p.loadParam("front_roller_middle_detect", type="int", default=20, comment="前辊筒中间检测光电")
        self.di3 = p.loadParam("front_roller_right_detect", type="int", default=21, comment="前辊筒右侧检测光电")
        self.di4 = p.loadParam("rear_roller_left_detect", type="int", default=22, comment="后辊筒左侧检测光电")
        self.di5 = p.loadParam("rear_roller_middle_detect", type="int", default=23, comment="后辊筒中间检测光电")
        self.di6 = p.loadParam("rear_roller_right_detect", type="int", default=24, comment="后辊筒右侧检测光电")
        self.di7 = p.loadParam("front_roller_fault", type="int", default=4, comment="前滚筒故障")
        self.di8 = p.loadParam("rear_roller_fault", type="int", default=5, comment="后滚筒故障")
        self.di9 = None
        self.di10 = None
        self.di11 = p.loadParam("front_damper_left_limitH", type="int", default=35, comment="前辊筒左侧挡板高位")
        self.di12 = p.loadParam("front_damper_left_limitL", type="int", default=36, comment="前辊筒左侧挡板低位")
        self.di13 = p.loadParam("front_damper_right_limitH", type="int", default=37, comment="前辊筒右侧挡板高位")
        self.di14 = p.loadParam("front_damper_right_limitL", type="int", default=38, comment="前辊筒右侧挡板低位")
        self.di15 = p.loadParam("rear_damper_left_limitH", type="int", default=39, comment="后辊筒左侧挡板高位")
        self.di16 = p.loadParam("rear_damper_left_limitL", type="int", default=40, comment="后辊筒左侧挡板低位")
        self.di17 = p.loadParam("rear_damper_right_limitH", type="int", default=41, comment="后辊筒右侧挡板高位")
        self.di18 = p.loadParam("rear_damper_right_limitL", type="int", default=42, comment="后辊筒右侧挡板低位")
        self.do1 = p.loadParam("front_roller_roll_Fast", type="int", default=18, comment="前滚筒转动快速")
        self.do2 = p.loadParam("front_roller_roll_slow", type="int", default=19, comment="前滚筒转动慢速")
        self.do3 = p.loadParam("rear_roller_roll_Fast", type="int", default=21, comment="后滚筒转动快速")
        self.do4 = p.loadParam("rear_roller_roll_slow", type="int", default=20, comment="后滚筒转动慢速")
        self.do5 = p.loadParam("front_roller_roll_reverse", type="int", default=2, comment="前滚筒反转")
        self.do6 = p.loadParam("rear_roller_roll_reverse", type="int", default=1, comment="后滚筒反转")
        self.do7 = p.loadParam("front_damper_left_up", type="int", default=34, comment="前滚筒左侧挡板升起")
        self.do8 = p.loadParam("front_damper_left_down", type="int", default=35, comment="前滚筒左侧挡板下降")
        self.do9 = p.loadParam("front_damper_right_up", type="int", default=36, comment="前滚筒右侧挡板升起")
        self.do10 = p.loadParam("front_damper_right_down", type="int", default=37, comment="前滚筒右侧挡板下降")
        self.do11 = p.loadParam("rear_damper_left_up", type="int", default=38, comment="后滚筒左侧挡板升起")
        self.do12 = p.loadParam("rear_damper_left_down", type="int", default=39, comment="后滚筒左侧挡板下降")
        self.do13 = p.loadParam("rear_damper_right_up", type="int", default=40, comment="后滚筒右侧挡板升起")
        self.do14 = p.loadParam("rear_damper_right_down", type="int", default=41, comment="后滚筒右侧挡板下降")
        self.unload_delay_time = p.loadParam("unload_delay_time", type="float", default=5.0, comment="卸货时辊筒停转延时时间")
        r.logInfo(f"init args: {args}")
        self.state = dict()
        self.status = MoveStatus.NONE
        self.init = True
        self.init1 = True
        self.current_time = 0
        self.delay_flag = None

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            args_error = False
            if "operation" in args:
                if "direction" not in args:
                    r.setError(f"Pls select load/unload direction")
                    args_error = True
                if "position" not in args:
                    r.setError(f"Pls select load/unload position")
                    args_error = True
                if args["operation"] == "load" and args["position"] == "front":
                    if self.check_DI(r, self.di1) or self.check_DI(r, self.di2) or self.check_DI(r,
                                                                                                 self.di3) or self.check_DI(
                            r, self.di7):
                        r.setError(f"can't load bcs front roller has goods or belt fault")
                        args_error = True
                elif args["operation"] == "load" and args["position"] == "rear":
                    if self.check_DI(r, self.di4) or self.check_DI(r, self.di5) or self.check_DI(r,
                                                                                                 self.di6) or self.check_DI(
                            r, self.di8):
                        r.setError(f"can't load bcs rear roller has goods or belt fault")
                        args_error = True
                elif args["operation"] == "unload" and args["position"] == "front":
                    if not self.check_DI(r, self.di1) and not self.check_DI(r, self.di2) and not self.check_DI(r,
                                                                                                               self.di3) or self.check_DI(
                            r, self.di7):
                        r.setError(f"can't unload bcs front roller has no goods")
                        args_error = True
                elif args["operation"] == "unload" and args["position"] == "rear":
                    if not self.check_DI(r, self.di4) and not self.check_DI(r, self.di5) and not self.check_DI(r,
                                                                                                               self.di6) or self.check_DI(
                            r, self.di8):
                        r.setError(f"can't unload bcs rear roller has no goods")
                        args_error = True
            else:
                r.setError(f"Pls select operation mode")
                args_error = True
            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED
        if args["operation"] == "load" and args["position"] == "front" and args["direction"] == "left":
            self.front_left_load(r)
        elif args["operation"] == "load" and args["position"] == "front" and args["direction"] == "right":
            self.front_right_load(r)
        elif args["operation"] == "unload" and args["position"] == "front" and args["direction"] == "left":
            self.front_left_unload(r)
        elif args["operation"] == "unload" and args["position"] == "front" and args["direction"] == "right":
            self.front_right_unload(r)
        elif args["operation"] == "load" and args["position"] == "rear" and args["direction"] == "left":
            self.rear_left_load(r)
        elif args["operation"] == "load" and args["position"] == "rear" and args["direction"] == "right":
            self.rear_right_load(r)
        elif args["operation"] == "unload" and args["position"] == "rear" and args["direction"] == "left":
            self.rear_left_unload(r)
        elif args["operation"] == "unload" and args["position"] == "rear" and args["direction"] == "right":
            self.rear_right_unload(r)
        # if self.status == MoveStatus.FINISHED:
        # self.reset(r)
        return self.status

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

    def front_left_load(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.do9, True)  # 右侧挡板上升
            r.setDO(self.do8, True)  # 左侧挡板下降
            r.setDO(self.do2, True)  # 皮带转动指令
            self.current_time = time.time()
        if time.time() - self.current_time > 2:
            if self.check_DI(r, self.di12):  # 左侧挡板低位的时候
                r.setDO(self.do8, False)  # 复位左侧挡板下降
                if self.check_DI(r, self.di13):  # 右侧挡板高位的时候
                    r.setDO(self.do9, False)  # 复位右侧挡板上升
                    if self.check_DI(r, self.di3):  # 右侧光电信号动作时
                        r.setDO(self.do2, False)  # 复位皮带转动指令
                        r.setDO(self.do7, True)  # 左侧挡板上升
                        # self.status = MoveStatus.FINISHED
            elif self.check_DI(r, self.di11):  # 左侧挡板高位的时候
                r.setDO(self.do7, False)  # 复位左侧挡板上升
                self.status = MoveStatus.FINISHED

    def front_right_load(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.do7, True)  # 左侧挡板上升
            r.setDO(self.do10, True)  # 右侧挡板下降
            r.setDO(self.do2, True)  # 皮带转动指令
            r.setDO(self.do5, True)  # 皮带反转指令
            self.current_time = time.time()
        if time.time() - self.current_time > 2:
            if self.check_DI(r, self.di14):  # 右侧挡板低位的时候
                r.setDO(self.do10, False)  # 复位右侧挡板下降
                if self.check_DI(r, self.di11):  # 左侧挡板高位的时候
                    r.setDO(self.do7, False)  # 复位左侧挡板上升
                    if self.check_DI(r, self.di1):  # 左侧光电信号动作时
                        r.setDO(self.do2, False)  # 复位皮带转动指令
                        r.setDO(self.do5, False)  # 复位皮带反转指令
                        r.setDO(self.do9, True)  # 右侧挡板上升
            elif self.check_DI(r, self.di13):  # 右侧挡板高位的时候
                r.setDO(self.do9, False)  # 复位右侧挡板上升
                self.status = MoveStatus.FINISHED

    def front_left_unload(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.do8, True)  # 左侧挡板下降
            self.current_time = time.time()
        if time.time() - self.current_time > 2:
            if self.check_DI(r, self.di12):  # 左侧挡板低位的时候
                r.setDO(self.do2, True)  # 皮带转动指令
                r.setDO(self.do5, True)  # 皮带反转指令
                r.setDO(self.do8, False)  # 复位左侧挡板下降
                if not self.check_DI(r, self.di1) and not self.check_DI(r, self.di2) and not self.check_DI(r, self.di3):  # 无光电检测时
                    if self.delay(self.unload_delay_time):
                        r.setDO(self.do7, True)  # 左侧挡板上升
            elif self.check_DI(r, self.di11):  # 左侧挡板高位的时候
                r.setDO(self.do7, False)  # 复位左侧挡板上升
                r.setDO(self.do2, False)  # 停皮带机
                r.setDO(self.do5, False)  # 停反转指令
                self.status = MoveStatus.FINISHED

    def front_right_unload(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.do10, True)  # 右侧挡板下降
            self.current_time = time.time()
        if time.time() - self.current_time > 2:
            if self.check_DI(r, self.di14):  # 右侧挡板低位的时候
                r.setDO(self.do10, False)  # 复位右侧挡板下降
                r.setDO(self.do2, True)  # 皮带转动指令
                if not self.check_DI(r, self.di1) and not self.check_DI(r, self.di2) and not self.check_DI(r, self.di3):  # 无光电检测时
                    if self.delay(self.unload_delay_time):
                        r.setDO(self.do9, True)  # 右侧挡板上升
            elif self.check_DI(r, self.di13):  # 右侧挡板高位的时候
                r.setDO(self.do9, False)  # 复位右侧挡板上升
                r.setDO(self.do2, False)  # 停皮带机
                self.status = MoveStatus.FINISHED

    def rear_left_load(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.do13, True)  # 右侧挡板上升
            r.setDO(self.do12, True)  # 左侧挡板下降
            r.setDO(self.do4, True)  # 皮带转动指令
            r.setDO(self.do6, True)  # 皮带转动指令
            self.current_time = time.time()
        if time.time() - self.current_time > 2:
            if self.check_DI(r, self.di16):  # 左侧挡板低位的时候
                r.setDO(self.do12, False)  # 复位左侧挡板下降
                if self.check_DI(r, self.di17):  # 右侧挡板高位的时候
                    r.setDO(self.do13, False)  # 复位右侧挡板上升
                    if self.check_DI(r, self.di6):  # 右侧光电信号动作时
                        r.setDO(self.do4, False)  # 复位皮带转动指令
                        r.setDO(self.do6, False)  # 停反转指令
                        r.setDO(self.do11, True)  # 左侧挡板上升
            elif self.check_DI(r, self.di15):  # 左侧挡板高位的时候
                r.setDO(self.do11, False)  # 复位左侧挡板上升
                self.status = MoveStatus.FINISHED

    def rear_right_load(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.do11, True)  # 左侧挡板上升
            r.setDO(self.do14, True)  # 右侧挡板下降
            r.setDO(self.do4, True)  # 皮带转动指令
            # r.setDO(self.do6, True)  # 皮带反转指令
            self.current_time = time.time()
        if time.time() - self.current_time > 2:
            if self.check_DI(r, self.di18):  # 右侧挡板低位的时候
                r.setDO(self.do14, False)  # 复位右侧挡板下降
                if self.check_DI(r, self.di15):  # 左侧挡板高位的时候
                    r.setDO(self.do11, False)  # 复位左侧挡板上升
                    if self.check_DI(r, self.di4):  # 左侧光电信号动作时
                        r.setDO(self.do4, False)  # 复位皮带转动指令
                        # r.setDO(self.do6, False)  # 复位皮带反转指令
                        r.setDO(self.do13, True)  # 右侧挡板上升
            elif self.check_DI(r, self.di17):  # 右侧挡板高位的时候
                r.setDO(self.do13, False)  # 复位右侧挡板上升
                self.status = MoveStatus.FINISHED

    def rear_left_unload(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.do12, True)  # 左侧挡板下降
            self.current_time = time.time()
        if time.time() - self.current_time > 2:
            if self.check_DI(r, self.di16):  # 左侧挡板低位的时候
                r.setDO(self.do4, True)  # 皮带转动指令
                r.setDO(self.do12, False)  # 复位左侧挡板下降
                if not self.check_DI(r, self.di4) and not self.check_DI(r, self.di5) and not self.check_DI(r, self.di6):  # 无光电检测时
                    if self.delay(self.unload_delay_time):
                        r.setDO(self.do11, True)  # 左侧挡板上升
            elif self.check_DI(r, self.di15):  # 左侧挡板高位的时候
                r.setDO(self.do11, False)  # 复位左侧挡板上升
                r.setDO(self.do4, False)  # 停皮带机
                r.setDO(self.do6, False)  # 停反转指令
                self.status = MoveStatus.FINISHED

    def rear_right_unload(self, r: SimModule):
        if self.init1:
            self.init1 = False
            r.setDO(self.do14, True)  # 右侧挡板下降
            self.current_time = time.time()
        if time.time() - self.current_time > 2:
            if self.check_DI(r, self.di18):  # 右侧挡板低位的时候
                r.setDO(self.do4, True)  # 皮带转动指令
                r.setDO(self.do6, True)  # 反转指令
                r.setDO(self.do14, False)  # 复位右侧挡板下降
                if not self.check_DI(r, self.di4) and not self.check_DI(r, self.di5) and not self.check_DI(r, self.di6):  # 无光电检测时
                    if self.delay(self.unload_delay_time):
                        r.setDO(self.do13, True)  # 右侧挡板上升
            elif self.check_DI(r, self.di17):  # 右侧挡板高位的时候
                r.setDO(self.do13, False)  # 复位右侧挡板上升
                r.setDO(self.do4, False)  # 停皮带机
                r.setDO(self.do6, False)  # 停反转指令
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
    args = {"operation": "unload", "position": "front"}
    r = SimModule()
    m = Module(r, args)
    m.run(r, args)

