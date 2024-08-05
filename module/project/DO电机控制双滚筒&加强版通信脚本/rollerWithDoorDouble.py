# -*- coding: utf-8 -*-
# @Date: 2023/07/5
# @Author: CXN
# @File: comm.py
# @Version: 1.0
# @Project:
# @Coding:https://seer-group.coding.net/p/order_issue_pool/requirements/issues/3311/detail
# @Update: 皮带，门控

import json
import sys
import time

sys.path.append("../syspy")
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.rbkSim import SimModule
from syspy.robot import ModuleTool

"""
####BEGIN DEFAULT ARGS####
{
    "before": {
        "value": "zero",
        "default_value": ["load","unload","after_load", "after_unload"],
        "tips": "操作类型",
        "type": "complex"
    },
    "after": {
        "value": "zero",
        "default_value": ["load","unload","after_load", "after_unload"],
        "tips": "操作类型",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.task_list = []
        self.task_id = 0
        self.init = True
        p = ParamServer(__file__)
        # 后皮带
        self.before = None
        self.after = None
        self.after_DI4 = p.loadParam("after_DI4", type="int", default=4, comment="后皮带传感器1")
        self.after_DI6 = p.loadParam("after_DI6", type="int", default=6, comment="后皮带传感器2")
        self.after_door_ctr_DI1 = p.loadParam("after_door_ctr_DI1", type="int", default=1, comment="后门控传感器-开")
        self.after_door_ctr_DI5 = p.loadParam("after_door_ctr_DI5", type="int", default=5, comment="后门控传感器-关")
        self.after_door_ctr_DO21 = p.loadParam("after_door_ctr_DO21", type="int", default=21, comment="后门控电机")
        self.after_door_ctr_DO20 = p.loadParam("after_door_ctr_DO20", type="int", default=20, comment="后门控电机")
        self.after_pd_ctr_DO4 = p.loadParam("after_pd_ctr_DO4", type="int", default=4, comment="后皮带电机")
        self.after_pd_ctr_DO1 = p.loadParam("after_pd_ctr_DO1", type="int", default=1, comment="后皮带电机")
        # 前皮带
        self.before_DI0 = p.loadParam("before_DI0", type="int", default=0, comment="前皮带传感器1")
        self.before_DI2 = p.loadParam("before_DI2", type="int", default=2, comment="前皮带传感器2")
        self.before_door_ctr_DI7 = p.loadParam("before_door_ctr_DI7", type="int", default=7, comment="前门控传感器-开")
        self.before_door_ctr_DI8 = p.loadParam("before_door_ctr_DI8", type="int", default=8, comment="前门控传感器-关")
        self.before_door_ctr_DO18 = p.loadParam("before_door_ctr_DO18", type="int", default=18, comment="前门控电机")
        self.before_door_ctr_DO19 = p.loadParam("before_door_ctr_DO19", type="int", default=19, comment="前门控电机")
        self.before_pd_ctr_DO2 = p.loadParam("before_pd_ctr_DO2", type="int", default=2, comment="前皮带电机")
        self.before_pd_ctr_DO3 = p.loadParam("before_pd_ctr_DO3", type="int", default=3, comment="前皮带电机")
        self.delay_time_unload = 5
        self.operation = None
        self.start_time = time.time()
        self.timeout = 60
        self.status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.tool = ModuleTool
        if "after" in args:
            self.after = args.get("after", None)
        if "before" in args:
            self.before = args.get("before", None)
        if not (self.after or self.before):
            r.setError(f"input args error : {args}")
            self.status = MoveStatus.FAILED

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if time.time() - self.start_time > 60:
            self.status = MoveStatus.FAILED
            r.setError(f"run time out {self.timeout}s")
        if self.after:
            if self.after == "load":
                self.after_load(r)
            if self.after == "unload":
                self.after_unload(r)
        if self.before:
            if self.before == "load":
                self.before_load(r)
            if self.before == "unload":
                self.after_unload(r)
        self.status = self.operation_status
        return self.status

    def before_unload(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if self.tool.check_DI(r, self.before_DI0) or self.tool.check_DI(r, self.before_DI2):
                self.task_list = [
                    OpenDO([self.before_door_ctr_DO19]),
                    CloseDO([self.before_door_ctr_DO18]),
                    WaitDI([self.before_door_ctr_DI8], True),
                    CloseDO([self.before_door_ctr_DO19]),
                    OpenDO([self.before_pd_ctr_DO3]),
                    WaitDI([self.before_DI2], True),
                    WaitDI([self.before_DI0], False),
                    CloseDO([self.before_pd_ctr_DO3])
                ]
        else:
            task = dict()
            task["before_unload"] = self.task_list
            self.run_tak_list(r)

    def before_load(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if not self.tool.check_DI(r, self.before_DI0) and not self.tool.check_DI(r, self.before_DI2):
                self.task_list = [
                    OpenDO([self.before_door_ctr_DO19]),
                    WaitDI([self.before_door_ctr_DI8], True),
                    CloseDO([self.before_door_ctr_DO19]),
                    OpenDO([self.before_pd_ctr_DO2]),
                    WaitDI([self.before_DI2], True),
                    WaitDI([self.before_DI0], False),
                    CloseDO([self.before_pd_ctr_DO2]),
                    OpenDO([self.before_door_ctr_DO18]),
                    WaitDI([self.before_door_ctr_DI7], True),
                    CloseDO([self.before_door_ctr_DO18])
                ]
            else:
                self.task_list = [
                    OpenDO([self.before_door_ctr_DO18]),
                    WaitDI([self.before_door_ctr_DI7], True),
                    CloseDO([self.before_door_ctr_DO18])
                ]
        else:
            task = dict()
            task["before_load"] = self.task_list
            self.run_tak_list(r)

    def after_load(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if not self.tool.check_DI(r, self.after_DI4) and not self.tool.check_DI(r, self.after_DI6):
                self.task_list = [
                    OpenDO([self.after_door_ctr_DO21]),
                    CloseDO([self.after_door_ctr_DO20]),
                    WaitDI([self.after_door_ctr_DI1], True),
                    CloseDO([self.after_door_ctr_DO21, self.after_door_ctr_DO20]),
                    OpenDO([self.after_pd_ctr_DO1]),
                    CloseDO([self.after_pd_ctr_DO4]),
                    WaitDI([self.after_DI4, self.after_DI6], False),
                    CloseDO([self.after_pd_ctr_DO4, self.after_pd_ctr_DO1]),
                    OpenDO([self.after_door_ctr_DO20]),
                    CloseDO([self.after_door_ctr_DO21]),
                    WaitDI([self.after_door_ctr_DI5], True),
                    CloseDO([self.after_door_ctr_DO21, self.after_door_ctr_DO20])
                ]
        else:
            task = dict()
            task["after_unload"] = self.task_list
            self.run_tak_list(r)

    def after_unload(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if self.tool.check_DI(r, self.after_DI4) or self.tool.check_DI(r, self.after_DI6):
                self.task_list = [
                    OpenDO([self.after_door_ctr_DO21]),
                    WaitDI([self.after_door_ctr_DI1], True),
                    CloseDO([self.after_door_ctr_DO21]),
                    OpenDO([self.after_pd_ctr_DO4]),
                    WaitDI([self.after_DI4, self.after_DI6], False),
                    CloseDO([self.after_pd_ctr_DO4]),
                    DelayTime(self.delay_time_unload)
                ]
            else:
                self.task_list = [
                    OpenDO([self.after_door_ctr_DO21]),
                    WaitDI([self.after_door_ctr_DI1], True),
                    CloseDO([self.after_door_ctr_DO21])
                ]
        else:
            task = dict()
            task["after_unload"] = self.task_list
            self.run_tak_list(r)

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


class OpenDO:
    def __init__(self, task: list):
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            for i, t in enumerate(self.task):
                r.setDO(t, True)
                self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        task_state["operation"] = "OpenDO"
        r.logDebug(json.dumps(task_state))


class CloseDO:
    def __init__(self, task: list):
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            for i, t in enumerate(self.task):
                r.setDO(t, False)
                self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        task_state["operation"] = "CloseDO"
        r.logDebug(json.dumps(task_state))


class WaitDI:
    def __init__(self, task: list, mode: bool):
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)
        self.mode = mode

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            if self.mode:
                for i, t in enumerate(self.task):
                    if m.tool.check_DI(r, t):
                        self.opt[i] = True
            else:
                for i, t in enumerate(self.task):
                    if not m.tool.check_DI(r, t):
                        self.opt[i] = True
        if all(self.opt):
            if ModuleTool.delay(1):
                self.status = MoveStatus.FINISHED
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        task_state["operation"] = "WaitDI"
        r.logDebug(json.dumps(task_state))


class DelayTime:
    def __init__(self, time_delay: int):
        self.status = MoveStatus.NONE
        self.time_delay = time_delay

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if ModuleTool.delay(self.time_delay):
            self.status = MoveStatus.FINISHED
        task_state["time"] = self.time_delay
        task_state["status"] = self.status
        r.logDebug(json.dumps(task_state))

