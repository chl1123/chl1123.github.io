# -*- coding: utf-8 -*-
# @Date: 2023/12/18
# @Author: CXN
# @File: comm.py
# @Version: 1.1
# @Project:
# @Coding:
# @Update: 多读，多写

import json
import time

import requests
import sys

sys.path.append("../modbus_tk")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule
from syspy.robot import NetHandle

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
    "mode":{
        "value": "core",
        "default_value":[
        "core","robot"
        ],
        "tips": "选择模式",
        "type": "complex"
    }, 
    "read": {
        "value": "",
        "tips": "读取期望值",
        "type": "json"
    },
    "write":{
        "value": "",
        "tips": "写取期望值",
        "type": "json"
    },
    "ip":{
        "value": "",
        "tips": "ip",
        "type": "string"
    },
    "slave_id": {
        "value": 1,
        "type": "int"
    },
    "port": {
        "value": 502,
        "type": "int"
    },
    "priority":{
        "value": "core",
        "default_value":[
                "read","write"
            ],
        "tips": "选择是先读还是先写，read，先读",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.timeout_modbus = 10
        self.priority = None
        self.write = None
        self.read = None
        self.timeout = 60
        self.init = True
        self.status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.st_addr = 0
        self.length = 1
        self.result = None
        self.value = None
        self.expected_value = None
        self.ip = None
        self.port = None
        self.slave_id = None
        self.mode = None
        self.timeout = 60
        self.start_t = time.time()
        self.modbus_tcp = None
        if args.get("mode", None) and args.get("ip", None):
            self.ip = args.get("ip")
            self.mode = args.get("mode")
        else:
            self.status = MoveStatus.FAILED
        if self.mode == "robot":
            if args.get("ip", None) and args.get("port", None) and args.get("slave_id", None):
                self.ip = args.get("ip")
                self.port = args.get("port")
                self.slave_id = args.get("slave_id")


            else:
                self.status = MoveStatus.FAILED
        r.logInfo(f"init args: {args}")
        self.task_id = 0
        self.task_list = []
        self.net_handle = NetHandle()
        self.state = {}

    def run(self, r: SimModule, args: dict):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.ip = args.get("ip", None)
            self.port = args.get("port", None)
            self.slave_id = args.get("slave_id", None)
            self.read = args.get("read", None)
            self.write = args.get("write", None)
            self.mode = args.get("mode", None)
            self.priority = args.get("priority", "read")
            self.modbus_tcp = ModbusTCP(ip=self.ip, port=self.port, timeout=self.timeout_modbus)
        if self.status != MoveStatus.FINISHED:
            if self.mode:
                if self.mode == "core":
                    self.handle_core(r)
                elif self.mode == "robot":
                    self.handle_robot(r)
            else:
                r.setError("mode error")
                self.status = MoveStatus.FAILED
        self.status = self.operation_status
        if time.time() - self.start_time > self.timeout:
            r.setError(f"run timeout {self.timeout} s")
            self.status = MoveStatus.FAILED
        if self.status == MoveStatus.FINISHED or self.status == MoveStatus.FAILED:
            self.modbus_tcp.tcp_master.close()
        self.state["status"] = self.status
        self.state["args"] = args
        r.setInfo(json.dumps(self.state))
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

    def handle_core(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if self.priority == "read":
                if self.read and isinstance(self.read, list):
                    for re in self.read:
                        self.task_list.append(ExecuteCore(re))
                if self.write and isinstance(self.write, list):
                    for wr in self.write:
                        self.task_list.append(ExecuteCore(wr))
            if self.priority == "write":
                if self.write and isinstance(self.write, list):
                    for wr in self.write:
                        self.task_list.append(ExecuteCore(wr))
                if self.read and isinstance(self.read, list):
                    for re in self.read:
                        self.task_list.append(ExecuteCore(re))
        else:
            task = dict()
            task["task_list0000"] = self.task_list
            # r.logDebug(json.dumps(task))
            self.run_tak_list(r)

    def handle_robot(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if self.priority == "read":
                if self.read and isinstance(self.read, list):
                    for re in self.read:
                        self.task_list.append(ExecuteRobot(re))
                if self.write and isinstance(self.write, list):
                    for wr in self.write:
                        self.task_list.append(ExecuteRobot(wr))
            if self.priority == "write":
                if self.write and isinstance(self.write, list):
                    for wr in self.write:
                        self.task_list.append(ExecuteRobot(wr))
                if self.read and isinstance(self.read, list):
                    for re in self.read:
                        self.task_list.append(ExecuteRobot(re))
        else:
            task = dict()
            task["task_list0000"] = self.task_list
            # r.logDebug(json.dumps(task))
            self.run_tak_list(r)


class ModbusTCP:
    """
    线圈 - 可读可写布尔量
    离散输入 - 只读布尔量
    保持寄存器 - 可读可写寄存器(16位)
    输入寄存器 - 只读寄存器(16位)

    # supported modbus functions
    READ_COILS = 1
    READ_DISCRETE_INPUTS = 2
    READ_HOLDING_REGISTERS = 3
    READ_INPUT_REGISTERS = 4
    WRITE_SINGLE_COIL = 5
    WRITE_SINGLE_REGISTER = 6
    WRITE_MULTIPLE_COILS = 15
    WRITE_MULTIPLE_REGISTERS = 16
    """

    def __init__(self, ip='127.0.0.1', port=502, timeout=3.0):
        self.tcp_master = modbus_tcp.TcpMaster(ip, port, timeout)


    def read_coils(self, slave, st_addr=0, length=1):
        """
        读取线圈
        @param slave:
        @param st_addr:
        @param length:
        @return:
        """
        return self.tcp_master.execute(slave, cst.READ_COILS, st_addr, length)

    def read_discrete_inputs(self, slave, st_addr=0, length=1):
        """
        读取离散输入
        @param slave:从机ID
        @param st_addr:起始地址
        @param length:读取长度
        @return:
        """
        return self.tcp_master.execute(slave, cst.READ_DISCRETE_INPUTS, st_addr, length)

    def read_holding_registers(self, slave, st_addr=0, length=1):
        """
        读取保持寄存器
        @param slave:
        @param st_addr:
        @param length:
        @return:
        """
        return self.tcp_master.execute(slave, cst.READ_HOLDING_REGISTERS, st_addr, length)

    def read_input_registers(self, slave, st_addr=0, length=1):
        """
        读取输入寄存器
        @param slave:
        @param st_addr:
        @param length:
        @return:
        """
        return self.tcp_master.execute(slave, cst.READ_INPUT_REGISTERS, st_addr, length)

    def write_single_coil(self, slave, st_addr, output_value):
        """
        写入单线圈
        @param slave:从机ID
        @param st_addr:起始地址
        @param output_value:待写入的数据
        @return:
        """
        return self.tcp_master.execute(slave, cst.WRITE_SINGLE_COIL, st_addr, output_value=output_value)

    def write_multi_coils(self, slave, st_addr, output_value):
        """
        写入多线圈
        @param slave:
        @param st_addr:
        @param output_value:
        @return:
        """
        return self.tcp_master.execute(slave, cst.WRITE_MULTIPLE_COILS, st_addr, output_value=output_value)

    def write_single_register(self, slave, st_addr, output_value):
        """
        写单一寄存器
        @param slave:
        @param st_addr:
        @param output_value:
        @return:
        """
        return self.tcp_master.execute(slave, cst.WRITE_SINGLE_REGISTER, st_addr, output_value=output_value)

    def write_multi_registers(self, slave, st_addr, output_value):
        """
        写多寄存器
        @param slave:
        @param st_addr:
        @param output_value:
        @return:
        """
        return self.tcp_master.execute(slave, cst.WRITE_MULTIPLE_REGISTERS, st_addr, output_value=output_value)


class ExecuteCore:
    """
    执行一个读写任务
                                                "id": "terminalName",    // 现场终端的名字
                                        "type": "writeAddr",    // 告知现场终端开始任务
                                        "value": 23,            // 写入现场终端寄存器的值
                                        "address": 3,           // 寄存器地址3
                                        "functionCode": 6
    """

    def __init__(self, task: dict):
        self.status = MoveStatus.NONE
        self.task = task
        self.http = "http://"
        self.call_ter = ":8088/callTerminal"
        self.url = ""

        self.value = self.task.get("value", None)
        self.id = self.task.get("id", None)
        self.type = self.task.get("type", None)
        self.address = self.task.get("address", None)
        self.functionCode = self.task.get("functionCode", None)
        self.typ = True if self.get_type() else False

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()

        if m.ip:
            self.url = self.http + m.ip + self.call_ter
            reach_res = self.call_terminal(r, self.url, self.task)
            r.logInfo(f"reach_res: {reach_res}")
            if reach_res:
                if self.typ:
                    v = self.value
                    if v == -1:
                        self.status = MoveStatus.FINISHED
                    elif v == reach_res.get("status"):
                        self.status = MoveStatus.FINISHED
                else:
                    v = self.value
                    if v == 1:
                        self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING
        else:
            self.status = MoveStatus.FAILED
            r.setError("pls input core ip : {}".format(m.ip))
        task_state["task"] = self.task
        task_state["status"] = self.status
        task_state["type"] = self.typ
        r.logDebug(json.dumps(task_state))

    def get_type(self):
        t = bool
        ty = self.type
        if ty == "read" or ty == "readAddr":
            t = True
        if ty == "write" or ty == "writeAddr":
            t = False
        return t

    def call_terminal(self, r: SimModule, url, data):
        """
        与终端设备交互, 使用 Core 的 callTerminal 接口
        :param r:
        :param url: "http:// Core IP:8088/callTerminal"
        :param data: json data
        :return: 成功则返回响应数据，失败返回 None
        """
        try:
            res = requests.post(url, json=data, timeout=(0.2, 0.2))
        except Exception as e:
            r.logInfo(f"post failed!!! url: {url}, data: {data}, error: {e}")
            return None
        else:
            if res.status_code == 200:
                return res.json()
            else:
                r.setWarning(f"res code: {res.status_code}, res: {res.text}")
                return None


class ExecuteRobot:
    """
    执行一个读写任务
                                            "id": "terminalName",    // 现场终端的名字
                                        "type": "writeAddr",    // 告知现场终端开始任务
                                        "value": 23,            // 写入现场终端寄存器的值
                                        "address": 3,           // 寄存器地址3
                                        "functionCode": 6
            RAW = 0
            READ_COILS = 1
            READ_DISCRETE_INPUTS = 2
            READ_HOLDING_REGISTERS = 3
            READ_INPUT_REGISTERS = 4
            WRITE_SINGLE_COIL = 5
            WRITE_SINGLE_REGISTER = 6
            READ_EXCEPTION_STATUS = 7
            DIAGNOSTIC = 8
            REPORT_SLAVE_ID = 17
            WRITE_MULTIPLE_COILS = 15
            WRITE_MULTIPLE_REGISTERS = 16
            READ_FILE_RECORD = 20
            READ_WRITE_MULTIPLE_REGISTERS = 23
            DEVICE_INFO = 43
    """

    def __init__(self, task: dict):
        self.status = MoveStatus.NONE
        self.task = task
        self.typ = True if self.get_type() else False
        self.address = self.task.get("address", None)
        self.value = self.task.get("value", None)
        self.functionCode = self.task.get("functionCode", None)

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        res = None
        if m.ip:
            if self.typ:
                m.state["address"] = self.address
                if self.address:
                    if self.functionCode == 1:
                        res = m.modbus_tcp.read_coils(m.slave_id, self.address,
                                                      len(self.value) if isinstance(self.value, list) else 1)
                    elif self.functionCode == 2:
                        res = m.modbus_tcp.read_discrete_inputs(m.slave_id, self.address,
                                                                len(self.value) if isinstance(self.value, list) else 1)
                    elif self.functionCode == 3:
                        res = m.modbus_tcp.read_holding_registers(m.slave_id, self.address,
                                                                  len(self.value) if isinstance(self.value,
                                                                                                list) else 1)
                    elif self.functionCode == 4:
                        res = m.modbus_tcp.read_input_registers(m.slave_id, self.address,
                                                                len(self.value) if isinstance(self.value, list) else 1)
                    else:
                        r.setError("function core error")
                        self.status = MoveStatus.FAILED
                    r.logDebug(f"read res :{res}")
                    m.state["res"] = res
                    if res is not None:
                        if isinstance(self.value, int):
                            if res == (self.value,):
                                self.status = MoveStatus.FINISHED
                        if isinstance(self.value, list):
                            print(self.value)
                            if res == tuple(self.value):
                                self.status = MoveStatus.FINISHED
            elif not self.typ:
                r.logDebug(f"write:{self.typ},{self.address},{self.value},{self.functionCode}")
                if self.value is not None and self.address is not None:
                    if self.functionCode == 5:
                        res = m.modbus_tcp.write_single_coil(m.slave_id, self.address, self.value)
                        if res is not None:
                            if res[1] == 1:
                                pass
                            elif self.value == 1:
                                self.value = 65280
                    elif self.functionCode == 6:
                        res = m.modbus_tcp.write_single_register(m.slave_id, self.address, self.value)
                    elif self.functionCode == 15:
                        res = m.modbus_tcp.write_multi_coils(m.slave_id, self.address, self.value)

                    elif self.functionCode == 16:
                        res = m.modbus_tcp.write_multi_registers(m.slave_id, self.address, self.value)
                    else:
                        r.setError("function core error")
                        self.status = MoveStatus.FAILED
                    r.logDebug(f"write res :{res}")
                    m.state["res"] = res
                    if res is not None:
                        if isinstance(self.value, int):
                            if res == (self.address, self.value):
                                r.logDebug(f"write res :{res},{self.address}, {self.value}")
                                self.status = MoveStatus.FINISHED
                        if isinstance(self.value, list):
                            if res == (self.address, len(self.value)):
                                self.status = MoveStatus.FINISHED
                else:
                    r.setError("没有地址值")
                    self.status = MoveStatus.FAILED
        task_state["task"] = self.status
        task_state["res_task"] = res
        r.logDebug(json.dumps(task_state))

    def get_type(self):
        t = bool
        ty = self.task.get("type", None)
        if ty == "read" or ty == "readAddr":
            t = True
        if ty == "write" or ty == "writeAddr":
            t = False
        return t
