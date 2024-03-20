# -*- coding: utf-8 -*-
# @Date : 2024/03/18
# @Author : zhong
# @Version : 1.0
# @Project : 恩奈极 IO滚筒
# @Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/5803/detail

import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
from robot import ModuleTool

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "stop",
        "default_value": [
            "load", "unload", "stop"
        ],
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        # 辊筒检测光电
        self.goods_check_di1 = 3
        self.goods_check_di2 = 10
        # 辊筒控制
        self.roller_speed_do1 = 19
        self.roller_speed_do2 = 20
        self.roller_direction_do3 = 21
        # 挡板控制
        self.block_open_do = 3
        self.block_direction_do = 2
        self.block_up_di = 2
        self.block_down_di = 6
        
        self.unload_delay_time = 2  # 下料延时停止时间
        self.opt = args.get("operation", None)
        self.unload_stop_start = False
        self.status = MoveStatus.NONE
        self.report_info = {}
        self.has_trigger = False
        self.has_goods = False
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.opt == "load":
            self.load(r)
        elif self.opt == "unload":
            self.unload(r)
        elif self.opt == "stop":
            self.stop(r)
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED
            
        self.report_info["status"] = self.status
        self.report_info["args"] = args
        r.setInfo(json.dumps(self.report_info))
        r.logDebug(json.dumps(self.report_info))
        return self.status

    def load(self, r):
        if not self.has_trigger and self.check_di(r, self.goods_check_di2):
            r.setError(f"The roller already has goods")
            self.status = MoveStatus.FAILED
            return
        
        r.setDO(self.block_open_do, True)
        r.setDO(self.block_direction_do, False)
        if self.check_di(r, self.block_down_di):
            r.setDO(self.roller_speed_do1, False)
            r.setDO(self.roller_speed_do2, True)
            r.setDO(self.roller_direction_do3, False)
        if self.check_di(r, self.goods_check_di1):
            self.has_trigger = True
        if self.has_trigger and self.check_di(r, self.goods_check_di2):
            r.setDO(self.roller_speed_do2, False)
            r.setDO(self.block_direction_do, True)
            if self.check_di(r, self.block_up_di):
                r.setDO(self.block_open_do, False)
                r.setGoodsShape(0, 0, 0)
                self.status = MoveStatus.FINISHED
        
    def unload(self, r):
        if self.check_di(r, self.goods_check_di2):
            self.has_goods = True
        if not self.has_goods and not self.check_di(r, self.goods_check_di1):
            r.setError(f"The roller has no goods")
            self.status = MoveStatus.FAILED
            return
        r.setDO(self.block_open_do, True)
        r.setDO(self.block_direction_do, False)
        if self.check_di(r, self.block_down_di):
            r.setDO(self.roller_speed_do1, False)
            r.setDO(self.roller_speed_do2, True)
            r.setDO(self.roller_direction_do3, True)
        if self.check_di(r, self.goods_check_di1):
            self.has_trigger = True
            
        if self.has_trigger and not self.check_di(r, self.goods_check_di1) and (
                not self.check_di(r, self.goods_check_di2)):
            if ModuleTool.delay(self.unload_delay_time):
                self.unload_stop_start = True
                
        if self.unload_stop_start:
            r.setDO(self.roller_speed_do2, False)
            r.setDO(self.block_direction_do, True)
            if self.check_di(r, self.block_up_di):
                r.setDO(self.block_open_do, False)
                r.clearGoodsShape()
                self.status = MoveStatus.FINISHED

    def stop(self, r):
        r.setDO(self.roller_speed_do1, False)
        r.setDO(self.roller_speed_do2, False)
        r.setDO(self.block_open_do, True)
        r.setDO(self.block_direction_do, True)
        if self.check_di(r, self.block_up_di):
            r.setDO(self.block_open_do, False)
            self.status = MoveStatus.FINISHED
        
    def cancel(self, r: SimModule):
        self.stop(r)
        r.setDO(self.block_open_do, False)
        self.status = MoveStatus.NONE
    
    def suspend(self, r: SimModule):
        self.stop(r)
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
