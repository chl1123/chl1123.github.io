# -*- coding: utf-8 -*-
# @Date : 2024/03/24
# @Author : zhong
# @Version : 1.0
# @Project : 西门子 IO滚筒
# @Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/5940/detail

import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
from robot import ModuleTool, Robot, Motor, MotorType

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "stop",
        "default_value": [
            "load", "unload", "lift", "stop", "init"
        ],
        "type": "complex"
    },
    "side":{
        "value": "",
        "default_value":["right","left"],
        "tips": "上下料方向",
        "type": "complex"
    },
    "lift_height": {
        "value": 0,
        "tips": "辊筒升降高度",
        "type": "float",
        "unit": "m"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        # 货物检测光电
        self.goods_check_left = 25
        self.goods_check_right = 23
        self.goods_check_mid = 24
        # 辊筒控制 正转/反转
        self.roller_do_positive = 1
        self.roller_do_negative = 2
        # 挡板控制
        self.left_block_up_do = 20
        self.left_block_down_do = 21
        self.right_block_up_do = 18
        self.right_block_down_do = 19
        # 挡板到位光电
        self.left_block_up_di = 21
        self.left_block_down_di = 22
        self.right_block_up_di = 19
        self.right_block_down_di = 20
        # 顶升电机名称
        self.lift_motor_name = "lift"
        
        self.unload_delay_time = 2  # 下料延时停止时间
        self.opt = args.get("operation", None)
        self.side = args.get("side", None)
        self.lift_height = args.get("lift_height", 0)
        self.unload_stop_start = False
        self.status = MoveStatus.NONE
        self.report_info = {}
        self.has_goods = False
        self.init = False
        self.robot = Robot(r)
        self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name)
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if not self.init:
            self.init = True
            self.close_do(r)
            if self.opt == "load" or self.opt == "init":
                self.has_goods = False
                if (self.check_di(r, self.goods_check_left) or self.check_di(r, self.goods_check_mid)
                        or self.check_di(r, self.goods_check_right)):
                    r.setError(f"The roller already has goods!")
                    self.status = MoveStatus.FAILED
            elif self.opt == "unload":
                self.has_goods = True
                if not (self.check_di(r, self.goods_check_left) or self.check_di(r, self.goods_check_mid)
                        or self.check_di(r, self.goods_check_right)):
                    r.setError(f"The roller has no goods!")
                    self.status = MoveStatus.FAILED
            
        if self.opt == "load":
            self.load(r)
        elif self.opt == "unload":
            self.unload(r)
        elif self.opt == "lift":
            self.lift(r)
        elif self.opt == "stop":
            self.stop(r)
        elif self.opt == "init":
            self.stop(r)
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED
        
        # 获取急停信号
        if r.controller().get("emc", False):
            self.close_do(r)
            self.status = MoveStatus.FAILED
            
        self.report_info["status"] = self.status
        self.report_info["args"] = args
        self.report_info["emc"] = r.controller().get("emc", "")
        r.setInfo(json.dumps(self.report_info))
        r.logDebug(json.dumps(self.report_info))
        return self.status

    def load(self, r):
        if self.side == "left":  # 左上料
            r.setDO(self.left_block_down_do, True)
            if self.check_di(r, self.left_block_down_di):
                r.setDO(self.roller_do_positive, True)
                if (self.check_di(r, self.goods_check_left) and self.check_di(r, self.goods_check_mid)
                        and self.check_di(r, self.goods_check_right)):
                    self.has_goods = True
                    r.setDO(self.roller_do_positive, False)
                    r.setDO(self.left_block_down_do, False)
                    r.setDO(self.left_block_up_do, True)
            if self.has_goods and self.check_di(r, self.left_block_up_di):
                self.status = MoveStatus.FINISHED
            
        elif self.side == "right":  # 右上料
            r.setDO(self.right_block_down_do, True)
            if self.check_di(r, self.right_block_down_di):
                r.setDO(self.roller_do_negative, True)
                if (self.check_di(r, self.goods_check_left) and self.check_di(r, self.goods_check_mid)
                        and self.check_di(r, self.goods_check_right)):
                    self.has_goods = True
                    r.setDO(self.roller_do_negative, False)
                    r.setDO(self.right_block_down_do, False)
                    r.setDO(self.right_block_up_do, True)
            if self.has_goods and self.check_di(r, self.right_block_up_di):
                self.status = MoveStatus.FINISHED
                
        else:
            r.setError(f"side args error: {self.side}")
            self.status = MoveStatus.FAILED
        
    def unload(self, r):
        if self.side == "left":  # 左下料
            r.setDO(self.left_block_down_do, True)
            if self.check_di(r, self.left_block_down_di):
                r.setDO(self.roller_do_negative, True)
                if not (self.check_di(r, self.goods_check_left) or self.check_di(r, self.goods_check_mid)
                        or self.check_di(r, self.goods_check_right)):
                    self.has_goods = False
                    r.setDO(self.roller_do_negative, False)
                    r.setDO(self.left_block_down_do, False)
                    r.setDO(self.left_block_up_do, True)
            if not self.has_goods and self.check_di(r, self.left_block_up_di):
                self.status = MoveStatus.FINISHED
                
        elif self.side == "right":  # 右下料
            r.setDO(self.right_block_down_do, True)
            if self.check_di(r, self.right_block_down_di):
                r.setDO(self.roller_do_positive, True)
                if not (self.check_di(r, self.goods_check_left) or self.check_di(r, self.goods_check_mid)
                        or self.check_di(r, self.goods_check_right)):
                    self.has_goods = False
                    r.setDO(self.roller_do_positive, False)
                    r.setDO(self.right_block_down_do, False)
                    r.setDO(self.right_block_up_do, True)
            if not self.has_goods and self.check_di(r, self.right_block_up_di):
                self.status = MoveStatus.FINISHED
                
        else:
            r.setError(f"side args error: {self.side}")
        
    def lift(self, r):
        if self.robot.lift(self.lift_motor, self.lift_height):
            self.status = MoveStatus.FINISHED

    def stop(self, r):
        r.setDO(self.roller_do_negative, False)
        r.setDO(self.roller_do_positive, False)
        r.setDO(self.left_block_down_do, False)
        r.setDO(self.right_block_down_do, False)
        r.setDO(self.left_block_up_do, True)
        r.setDO(self.right_block_up_do, True)
        if self.check_di(r, self.left_block_up_di) and self.check_di(r, self.right_block_up_di):
            r.setDO(self.left_block_up_do, False)
            r.setDO(self.right_block_up_do, False)
            self.status = MoveStatus.FINISHED
            
    def close_do(self, r):
        r.setDO(self.roller_do_negative, False)
        r.setDO(self.roller_do_positive, False)
        r.setDO(self.left_block_down_do, False)
        r.setDO(self.right_block_down_do, False)
        r.setDO(self.left_block_up_do, False)
        r.setDO(self.right_block_up_do, False)
        
    def cancel(self, r: SimModule):
        self.close_do(r)
        self.status = MoveStatus.NONE
    
    def suspend(self, r: SimModule):
        self.close_do(r)
        self.status = MoveStatus.SUSPENDED

    @staticmethod
    def check_di(r: SimModule, di: int):
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node['id'] == di:
                return node['status']
        return False
    

if __name__ == '__main__':
    pass
