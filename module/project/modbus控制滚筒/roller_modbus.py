# -*- coding: utf-8 -*-
# @Date : 2023/7/5
# @Author : CXN
# @File :
# @Version : 1.0
# @Project : 【现场】【阿雷蒙】【滚筒脚本需求】
# @coding:https://seer-group.coding.net/p/order_issue_pool/requirements/issues/3218/detail
# @Update :
# 现场滚筒需求为，通过ModbusTcp的通讯方式与客户的PLC进行通讯。现场车体为双滚筒车，
# 客户提供8个地址位，分别是
# 前滚筒左侧上下料，右侧上下料。
# 后滚筒左侧上下料，右侧上下料。
# 我们只需要根据不同的上下料往相应的地址为里面写值，滚筒机构的上下料运行和到位检测均为客户的PLC自行判断运行。
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
    "operation":{
        "value": "before_left_load",
        "default_value":[
            "before_left_load","before_left_unload","after_left_load","after_left_unload",
            "before_right_load","before_right_unload","after_right_load","after_right_unload"
        ],
        "tips": "选择模式",
        "type": "complex"
    }, 
    "ip":{
        "value": "192.168.192.201",
        "default_value":"127.0.0.1",
        "tips": "选择地址",
        "type": "string"
    },
    "port":{
        "value": "502",
        "default_value":503,
        "tips": "选择端口",
        "type": "int"
    },
    "salve_id":{
        "value": "1",
        "default_value":1,
        "tips": "选择端口",
        "type": "int"
    } 
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.report_info = dict()
        self.state = dict()
        self.status = MoveStatus.NONE
        self.ip = args.get("ip", "127.0.0.1")
        self.port = args.get("port", 502)
        self.slave_id = args.get("salve_id", 1)
        self.operation = args.get("operation", None)
        r.setNotice(f"ip:{self.ip}")
        if self.operation is None:
            self.status = MoveStatus.FAILED
            r.setError("operation error")
        self.modbus_tcp = ModbusTCP(self.ip, self.port)
        self.addr_left_load_status = 6
        self.addr_left_unload_status = 5
        self.addr_right_load_status = 8
        self.addr_right_unload_status = 7
        self.left_load_status = 0
        self.left_unload_status = 0
        self.right_load_status = 0
        self.right_unload_status = 0
        self.addr_left_err = 0
        self.left_err = 0
        self.right_err = 0
        self.addr_right_err = 1
        self.addr_before_left_load = 10
        self.addr_before_left_unload = 11
        self.addr_after_left_load = 12
        self.addr_after_left_unload = 13
        self.addr_before_right_load = 14
        self.addr_before_right_unload = 15
        self.addr_after_right_load = 16
        self.addr_after_right_unload = 17

        self.value_before_left_load = 1
        self.value_before_left_unload = 1
        self.value_after_left_load = 1
        self.value_after_left_unload = 1
        self.value_before_right_load = 1
        self.value_before_right_unload = 1
        self.value_after_right_load = 1
        self.value_after_right_unload = 1

        self.opt = [False] * 3

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.status != MoveStatus.FINISHED:
            self.handle_err(r)
            self.handle_status(r)
        if self.operation == "before_left_load":
            self.handle(r, self.addr_before_left_load, self.left_load_status)
        if self.operation == "before_left_unload":
            self.handle(r, self.addr_before_left_unload, self.left_unload_status)
        if self.operation == "after_left_load":
            self.handle(r, self.addr_after_left_load, self.left_load_status)
        if self.operation == "after_left_unload":
            self.handle(r, self.addr_after_left_unload, self.left_unload_status)
        if self.operation == "before_right_load":
            self.handle(r, self.addr_before_right_load, self.right_load_status)
        if self.operation == "before_right_unload":
            self.handle(r, self.addr_before_right_unload, self.right_unload_status)
        if self.operation == "after_right_load":
            self.handle(r, self.addr_after_right_load, self.right_load_status)
        if self.operation == "after_right_unload":
            self.handle(r, self.addr_after_right_unload, self.right_unload_status)
        if self.status == MoveStatus.FAILED or self.status == MoveStatus.FAILED:
            self.modbus_tcp.tcp_master.close()
        status = dict()
        status["right_unload_status"] = self.right_unload_status
        status["right_load_status"] = self.right_load_status
        status["left_unload_status"] = self.left_unload_status
        status["left_load_status"] = self.left_load_status
        status["left_err"] = self.left_err
        status["right_err"] = self.right_err
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        self.report_info['status'] = status
        self.report_info['opt'] = self.opt
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def write_registers(self, addr, value):
        self.modbus_tcp.write_single_register(self.slave_id, addr, value)
        result = self.modbus_tcp.read_holding_registers(self.slave_id, addr, 1)
        if result is not None:
            return True
        return False

    def handle_err(self, r: SimModule):
        self.left_err = self.modbus_tcp.read_holding_registers(self.slave_id, self.addr_left_err, 1)[0]
        self.right_err = self.modbus_tcp.read_holding_registers(self.slave_id, self.addr_right_err, 1)[0]
        if self.left_err is not None:
            if self.left_err == 1:
                self.status = MoveStatus.FAILED
                r.setError(f"left roller error,{self.left_err}")
        if self.right_err is not None:
            if self.right_err == 1:
                self.status = MoveStatus.FAILED
                r.setError(f"left roller error,{self.right_err}")

    def handle_status(self, r):
        self.left_load_status = self.modbus_tcp.read_holding_registers(self.slave_id, self.addr_left_load_status, 1)[0]
        self.left_unload_status = \
            self.modbus_tcp.read_holding_registers(self.slave_id, self.addr_left_unload_status, 1)[0]
        self.right_load_status = self.modbus_tcp.read_holding_registers(self.slave_id, self.addr_right_load_status, 1)[
            0]
        self.right_unload_status = \
            self.modbus_tcp.read_holding_registers(self.slave_id, self.addr_right_unload_status, 1)[0]
        r.logDebug(
            f"status:{self.left_load_status}|{self.left_unload_status}|{self.right_load_status}|{self.right_unload_status}")

    def handle(self, r, write_addr, status):
        if not self.opt[0]:
            write = self.write_registers(write_addr, 1)
            if write:
                self.opt[0] = True
            if status == 1:
                self.status = MoveStatus.FINISHED
        if not self.opt[1] and self.opt[0]:
            if status == 1:
                self.opt[1] = True
        if not self.opt[2] and self.opt[1]:
            write = self.write_registers(write_addr, 0)
            if write:
                self.opt[2] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        r.setNotice(f"handle opt:{self.opt}")


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
