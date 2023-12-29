# -*- coding: utf-8 -*-
# @Date: 2023/07/5
# @Author: CXN
# @File: comm.py
# @Version: 1.0
# @Project:【造车】【立诺】【对射型充电桩-开发需求】
# @Coding:https://seer-group.coding.net/p/issue_pool/requirements/issues/3835/detail
# @Update:

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
    "operation": {
        "value": "load",
        "default_value": ["start","end"],
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
        self.DO1 = p.loadParam("DO1", type="int", default=1, comment="车载光电发射端")
        self.DI2 = p.loadParam("DI2", type="int", default=2, comment="车载光电接受端")
        self.DO3 = p.loadParam("DI3", type="int", default=3, comment="电池干接电")
        self.operation = None
        self.start_time = time.time()
        self.timeout = 60
        self.status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.tool = ModuleTool
        self.init = False
        self.report_data = {}
        r.logDebug(f"init args:{args}")

    def periodRun(self, r: SimModule) -> bool:
        battery_data = r.battery()
        self.report_data["battery"] = battery_data
        if "percetage" in battery_data:
            if battery_data["percetage"] >= 1 and self.tool.check_DI(r, self.DI2):
                if self.operation_status != MoveStatus.FINISHED:
                    self.end(r)
        r.setInfo(json.dumps(self.report_data))
        r.logInfo(json.dumps(self.report_data))
        return True

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING

        if not self.init:
            if "operation" in args:
                self.operation = args["operation"]
        if self.status != MoveStatus.FINISHED or self.status != MoveStatus.FAILED:
            self.handle(r)
        if self.status == MoveStatus.FAILED:
            pass
        self.status = self.operation_status
        self.report_data["battery"] = r.battery()
        r.setInfo(json.dumps(self.report_data))
        r.logInfo(json.dumps(self.report_data))
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

    def start(self, r: SimModule):
        """上料"""
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                OpenDO([self.DO1]),  # 打开发射端
                WaitDI([self.DI2], True),  # 接受信号
                OpenDO([self.DO3]),  # 干节点
            ]
        else:
            task = dict()
            task["start"] = self.task_list
            self.run_tak_list(r)

    def end(self, r):
        """下料"""
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                CloseDO([self.DO1]),  # 关闭发射端
                DelayTime(2),
                CloseDO([self.DO3]),  # 断开干节点
                DelayTime(2),
                WaitDI([self.DI2], False)  #
            ]
        else:
            task = dict()
            task["end"] = self.task_list
            self.run_tak_list(r)

    def handle(self, r):
        if time.time() - self.start_time > 60:
            self.status = MoveStatus.FAILED
            r.setError(f"run time out {self.timeout}s")
            return
        if self.operation == "start":
            self.start(r)
        elif self.operation == "end":
            self.end(r)
        else:
            r.setError(f"输入参数错误，请输入正确的 operation：load 或者 unload")
            self.status = MoveStatus.FAILED


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
    def __init__(self, task: list, mode: bool, delay_time=0):
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)
        self.mode = mode
        self.delay_time = delay_time
        if self.delay_time:
            self.start_time = time.time()

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
            if ModuleTool.delay(self.delay_time):
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


