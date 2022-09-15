# -*- coding: utf-8 -*-
# @Date : 2022/8/9 
# @Author : zhong
# @File :san_roller.py
# @Version : 1.0
# @Project : https://seer-group.coding.net/p/issue_pool/requirements/issues/3457/detail
# @Support :
# @Update : 

import json
import time

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import Motor, MotorType, ModuleTool, Robot

SCRIPT_VERSION = "V1.0_2022-8-9"

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "",
        "default_value":["RollerLoad", "RollerUnload","RollerStop"],
        "tips": "操作",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args: dict):
        super().__init__()
        p = ParamServer(__file__)
        self.goods_check_di1 = p.loadParam("goods_check_di1", type="int", default=29, comment="物料1检测DI")
        self.goods_check_di2 = p.loadParam("goods_check_di2", type="int", default=20, comment="物料2检测DI")
        self.goods_check_di3 = p.loadParam("goods_check_di3", type="int", default=21, comment="物料3检测DI")
        self.goods_check_di4 = p.loadParam("goods_check_di4", type="int", default=22, comment="物料4检测DI")

        self.left_block_up_do = p.loadParam("left_block_up_do", type="int", default=3, comment="左挡板上升DO")
        self.left_block_down_do = p.loadParam("left_block_down_do", type="int", default=4, comment="左挡板下降DO")
        self.left_block_up_di = p.loadParam("left_block_up_di", type="int", default=24, comment="左挡板上升到位DI ")
        self.left_block_down_di = p.loadParam("left_block_down_di", type="int", default=23, comment="左挡板下降到位DI")

        self.right_block_up_do = p.loadParam("right_block_up_do", type="int", default=1, comment="右挡板上升DO")
        self.right_block_down_do = p.loadParam("right_block_down_do", type="int", default=2, comment="右挡板下降DO")
        self.right_block_up_di = p.loadParam("right_block_up_di", type="int", default=26, comment="右挡板上升到位DI")
        self.right_block_down_di = p.loadParam("right_block_down_di", type="int", default=25, comment="右挡板下降到位DI")

        self.load_condition_di1 = p.loadParam("load_condition_di1", type="int", default=19, comment="上料充要条件DI1")
        self.unload_condition_di1 = p.loadParam("unload_condition_di1", type="int", default=19, comment="下料充要条件DI1")

        self.signal_do = p.loadParam("signal_do", type="int", default=7, comment="对射光电发射 DO")
        self.roller_motor_name = p.loadParam("Motor-Roller", type="str", default="roller", comment="线性辊筒电机名称")
        self.fast_speed = p.loadParam("fast_speed", type="float", default=0.3, comment="辊筒高速")
        self.slow_speed = p.loadParam("slow_speed", type="float", default=0.1, comment="辊筒低速")

        self.roller_motor = None
        self.robot = None
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.check_di = ModuleTool.check_DI
        self.opt = None
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args: dict):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.opt = args.get("operation", None)
            self.roller_motor = Motor(r, MotorType.ROLLER_MOTOR, self.roller_motor_name, -1)
            self.robot = Robot(r)
            self.init = False

        if self.opt == "RollerLoad":
            self.RollerLoad(r)
        elif self.opt == "RollerUnload":
            self.RollerUnload(r)
        elif self.opt == "RollerStop":
            self.RollerStop(r)
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED

        r.publishSpeed()
        self.report_info["script-version"] = SCRIPT_VERSION
        self.report_info["args"] = args
        r.setInfo(json.dumps(self.report_info))
        return self.status

    def RollerLoad(self, r: SimModule):
        r.setDO(self.signal_do, True)
        r.setDO(self.left_block_up_do, True)
        r.setDO(self.left_block_down_do, True)  # 左挡板下降
        r.setDO(self.right_block_up_do, True)     # 右挡板上升
        if self.check_di(r, self.load_condition_di1) and self.check_di(r, self.load_condition_di2):
            if self.check_di(r, self.left_block_down_di) and self.check_di(r, self.right_block_up_di):
                self.robot.roller(self.roller_motor, self.fast_speed)
                if self.check_di(r, self.goods_check_di2):
                    self.robot.roller(self.roller_motor, self.slow_speed)
                if self.check_di(r, self.goods_check_di1):
                    self.robot.roller(self.roller_motor, 0.)
                    r.setDO(self.left_block_down_do, False)
        if self.check_di(r, self.goods_check_di1) and self.check_di(r, self.left_block_up_di):
            r.setDO(self.signal_do, False)
            self.status = MoveStatus.FINISHED
        self.report_info["roller load"] = self.robot.state

    def RollerUnload(self, r: SimModule):
        r.setDO(self.signal_do, True)
        r.setDO(self.left_block_up_do, True)
        r.setDO(self.right_block_up_do, True)
        if self.check_di(r, self.unload_condition_di1) and self.check_di(r, self.unload_condition_di2):
            r.setDO(self.left_block_down_do, True)  # 左挡板下降
            if self.check_di(r, self.left_block_down_di):
                self.robot.roller(self.roller_motor, -self.fast_speed)
            if self.check_di(r, self.goods_check_di1) and self.check_di(r, self.goods_check_di2) \
                    and self.check_di(r, self.goods_check_di3) and self.check_di(r, self.goods_check_di4):
                if ModuleTool.delay(2.0):
                    self.robot.roller(self.roller_motor, 0.)
                    r.setDO(self.left_block_down_do, False)
                if self.check_di(r, self.left_block_up_di):
                    r.setDO(self.signal_do, False)
                    self.status = MoveStatus.FINISHED
        self.report_info["roller unload"] = self.robot.state

    def RollerStop(self, r: SimModule):
        r.setDO(self.left_block_up_do, False)
        r.setDO(self.left_block_down_do, False)
        r.setDO(self.signal_do, False)      #guanbi对射光电
        self.robot.roller(self.roller_motor, 0.)        #滚筒电机停止运行
        self.status = MoveStatus.FINISHED
        self.report_info["roller stop"] = self.robot.state

if __name__ == '__main__':
    args = {"operation": "unload"}
    r = SimModule()
    m = Module(r, args)
    m.run(r, args)
