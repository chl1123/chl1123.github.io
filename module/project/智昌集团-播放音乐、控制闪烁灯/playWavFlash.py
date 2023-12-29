# -*- coding: utf-8 -*-
# @Date : 2023/6/15 15:25
# @Author : CXN
# @File :playWavFlash.py.py
# @Version : 1.0
# @Project :  播放音乐，控制等闪烁
# @coding : https://seer-group.coding.net/p/order_issue_pool/requirements/issues/3075/detail
import json
import time

from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.rbkSim import SimModule
from syspy.robot import Motor, MotorType, Robot, ModuleTool

""" 
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value": [
            "play_flash"
        ],
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.operation_status = MoveStatus.NONE
        p = ParamServer(__file__)
        self.flash_do1 = p.loadParam("flash_do2", type="int", default=2, comment="频闪等DO")
        self.flash_do2 = p.loadParam("flash_do3", type="int", default=3, comment="频闪等DO")
        self.play_wav = p.loadParam("play_wav", type="str", default="turnleft", comment="音频文件")
        self.init = True
        self.state = dict()
        self.task_id = 0
        self.count=9999
        self.flag = 0
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        r.setSound(self.play_wav, True)
        if self.init:
            self.init = False
            if "operation" not in args:
                r.setError(f"args error: {args}")
                return MoveStatus.FAILED
            self.status = MoveStatus.RUNNING
        if args["operation"] == "play_flash":

            self.play_flash(r)
        else:
            r.setError(f"operation args error: {args}")
            self.status = MoveStatus.FAILED
        r.setSound(self.play_wav, False)
        if self.status == MoveStatus.FINISHED:
            r.stopSound(True)
        self.state["args"] = args
        self.state["operation_status"] = self.operation_status
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        self.status = self.operation_status
        return self.status

    def run_tak_list(self, r):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(self)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED

    def play_flash(self, r):
        if self.flag == 0:
            if ModuleTool.delay(5):
                r.setDO(self.flash_do1, False)
                r.setDO(self.flash_do2, True)
                self.flag = 1
                self.status = MoveStatus.RUNNING

        else:
            if ModuleTool.delay(5):
                r.setDO(self.flash_do1, False)
                r.setDO(self.flash_do2, True)
                self.flag = 0
                self.status = MoveStatus.RUNNING
#

class Flash:
    def __init__(self, do1: int = 2,do2: int = 3, c: int = 99):
        self.status = MoveStatus.NONE
        self.do1 = do1
        self.do2 = do2
        self.count = c
        self.flag = 0

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m_state = dict()
        if self.flag == 0:
            if ModuleTool.delay(5):
                r.setDO(self.do1, False)
                time.sleep(0.1)
                r.setDO(self.do2, True)
                self.flag = 1
                self.count -= 1
                self.status = MoveStatus.RUNNING

        else:
            if ModuleTool.delay(5):
                r.setDO(self.do2, False)
                time.sleep(0.1)
                r.setDO(self.do1, True)
                self.flag = 0
                self.count -= 1
                self.status = MoveStatus.RUNNING
        if self.count<1:
            self.status=MoveStatus.FINISHED
        m_state["Flash_status"] = self.status
        m_state["count"] = self.count
        m_state["flag"] = self.flag
        m.state["Flash"] = m_state
