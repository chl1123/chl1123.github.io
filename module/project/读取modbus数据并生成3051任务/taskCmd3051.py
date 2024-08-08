# -*- coding: utf-8 -*-
# @Date: 2023/11/17
# @Author: CXN
# @File: taskCmd3051.py
# @Version: 1.0
# @Project: 【需求】【烟台创鑫】【modbus api】
# @Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/4120/detail
# @Update: 脚本调用 3051
import enum
import json
import math
import time
import uuid
from typing import List

import sys

from syspy import goPath

sys.path.append("../modbus_tk")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.robot import NetHandle, ModuleTool, Robot
from syspy.goPath import Module as go

try:
    import modbus_tk.defines as cst
    from modbus_tk import modbus_tcp, modbus_rtu
except ImportError:
    import os

    os.system("pip install modbus_tk")
    SimModule.setError(SimModule(), f"modbus_tk needs to be installed")
    os.system("pip install modbus_tk -i https://pypi.tuna.tsinghua.edu.cn/simple")
    import modbus_tk.defines as cst
    from modbus_tk import modbus_tcp

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "JackLoad",
        "default_value": ["JackLoad", "GoPGV","JackUnload","Read"],
        "tips": "操作类型",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.source_id_type = 0
        self.id_type = 0

        self.point_type = 0  # 站点类型，0：AP,1 LM，2：库位
        self.jack_height = 0.04
        self.id = 0
        self.source_id = 0
        self.recognize = False
        self.report_data = dict()
        self.use_down_pgv = False
        self.use_pgv = False
        self.modbus_tcp = None
        self.task_list = []
        self.task_id = 0
        self.init = True
        p = ParamServer(__file__)
        self.addr = p.loadParam("addr", type="int", default=1, comment="起始地址")
        self.rec_file = p.loadParam("rec_file", type="str", default="multi/m0002.multi", comment="识别文件")
        self.ip = p.loadParam("ip", type="str", default="127.0.0.1", comment="PLC的ip地址")
        self.port = p.loadParam("port", type="int", default=505, comment="PLC的端口")
        self.slave_id = p.loadParam("slave_id", type="int", default=1, comment="PLC的 id")
        self.timeout = p.loadParam("timeout", type="int", default=180, comment="整个任务的超时时间")
        self.operation = None
        self.start_time = time.time()
        self.status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.tool = ModuleTool

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.operation = args.get("operation", None)
            self.modbus_tcp = modbus_tcp.TcpMaster(host=self.ip, port=self.port, timeout_in_sec=5.0)
        if time.time() - self.start_time > self.timeout:
            self.status = MoveStatus.FAILED
            r.setError(f"run time out {self.timeout}s")
        if self.status != MoveStatus.FINISHED and not self.init:
            self.handle(r)
        self.status = self.operation_status
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

    def handle(self, r:SimModule):
        if self.operation =="GoPGV":
            self.go_PGV(r)
        elif self.operation =="JackLoad":
            self.jack_load(r)
        elif self.operation =="JackUnload":
            self.jack_unload(r)
        elif self.operation =="Read":
            self.read(r)
        else:
            r.setError(f"请输入正确的 operation：JackLoad、JackUnload、GoPGV，而不是{self.operation}")

    def go_PGV(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                GetModbusValue(),
                GoPGV()
            ]
        else:
            task = dict()
            self.run_tak_list(r)

    def jack_load(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                GetModbusValue(),
                Jack(self.operation)
            ]
        else:
            task = dict()
            self.run_tak_list(r)
    def jack_unload(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                GetModbusValue(),
                Jack(self.operation)
            ]
        else:
            task = dict()
            self.run_tak_list(r)

    def read_modbus(self,r:SimModule):
        status = self.modbus_tcp.execute(self.slave_id, cst.READ_HOLDING_REGISTERS, self.addr, 7)
        self.id_type = status[0]
        self.source_id_type = status[1]
        if status[0] ==0 and status[2] != 0:
            self.id = "AP"+str(status[2])
        elif status[0] ==1 and status[2] != 0:
            self.id = "LM"+str(status[2])
        else :
            self.id = "SELF_POSITION"
        if status[1] ==0 and status[3] != 0:
            self.source_id = "AP"+str(status[3])
        elif status[1] == 1 and status[3] != 0:
            self.source_id = "LM"+str(status[3])
        else:
            self.source_id = "SELF_POSITION"
        if status[3] !=0 and status[2]==0:
            self.status = MoveStatus.FAILED
            r.setError(f"起点为非 0 而终点为0，{status[3]}，{status[2]}")
        self.use_pgv = bool(status[4])
        self.use_down_pgv = bool(status[5])
        self.recognize = bool(status[6])
        self.report_data["MODBUS"] = status
        self.report_data["read_modbus"] = {
            "id_type":self.id_type,
            "source_id_type":self.source_id_type,
            "id":self.id,
            "source_id":self.source_id,
            "use_pgv":self.use_pgv,
            "use_down_pgv":self.use_down_pgv,
            "recognize":self.recognize
        }
        r.logInfo(json.dumps(self.report_data))
        r.setInfo(json.dumps(self.report_data))
        return True

    def read(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                GetModbusValue()
            ]
        else:
            task = dict()
            #task["task_list"] = self.task_list
            task["status"] = self.status
            self.report_data["read"] = task
            self.run_tak_list(r)


class GoPGV:
    """移动到指定站点
    {
"id": "SELF_POSITION",
"operation": "GoPGV",
"source_id": "SELF_POSITION",
"task_id": "1234",
"use_pgv": false,
"use_down_pgv": true
}

    """

    def __init__(self):
        self.status = MoveStatus.NONE
        self.init = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
        self.status = MoveStatus.RUNNING
        if self.status != MoveStatus.FINISHED:
            task = {
                "id": m.id,
                "operation": "GoPGV",
                "source_id": m.source_id,
                "task_id": str(uuid.uuid1()),
                "use_pgv": m.use_pgv,
                "use_down_pgv": m.use_down_pgv
            }
            task_state["task"] = task
            r.logInfo(json.dumps(m.report_data))
            r.setInfo(json.dumps(m.report_data))
            r.addMoveTask(json.dumps(task))
        task_state["status"] = self.status
        m.report_data["GoPGV"] = task_state



class Jack:
    """移动到指定站点
"id": "AP1",
"source_id": "LM2",
"task_id": "12344321",
"operation": "JackLoad",
"jack_height": 0.04,
"recognize": true,
"use_pgv": true
}
    """

    def __init__(self,operation):
        self.operation = operation
        self.status = MoveStatus.NONE
        self.init = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
        self.status = MoveStatus.RUNNING
        if self.status != MoveStatus.FINISHED:
            task = {
                "id": m.id,
                "source_id": m.source_id,
                "task_id": str(uuid.uuid1()),
                "operation": self.operation,
                "jack_height": m.jack_height,
                "recognize": m.recognize,
                "use_pgv": m.use_pgv,
                "use_down_pgv": m.use_down_pgv,
            }
            task_state["task"] = task
            r.addMoveTask(json.dumps(task))

        task_state["status"] = self.status
        m.report_data[f"Jack-{self.operation}"] = task_state

class GetModbusValue:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.init = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
        self.status = MoveStatus.RUNNING
        if self.status != MoveStatus.FINISHED:
            if m.read_modbus(r):
                self.status = MoveStatus.FINISHED
        self.status = MoveStatus.FINISHED
        task_state["status"] = self.status
        m.report_data["GetModbusValue"] = task_state
