# -*- coding: utf-8 -*-
# @Date: 2023/03/20
# @Author: zhong,CXN
# @File: modbus_comm.py
# @Version: 1.1
# @Project:
# @Coding:
# @Update: 增加读取预期值

import json
import time
# import serial
import sys
sys.path.append("../modbus_tk")
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule

try:
    import modbus_tk.defines as cst
    from modbus_tk import modbus_tcp, modbus_rtu
except ImportError:
    import os
    os.system("pip install modbus_tk")
    SimModule.setError(SimModule(), f"modbus_tk needs to be installed")
    os.system("pip install modbus_tk -i https://pypi.tuna.tsinghua.edu.cn/simple")
    import modbus_tk.defines as cst
    from modbus_tk import modbus_tcp, modbus_rtu


# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "read",
        "default_value":["read_coils", "read_registers", "write_coils", "write_registers", "tasks_list"],
        "type": "complex"   
    },
    "st_addr":{
        "value": 0,
        "type": "int"
    }, 
    "length": {
        "value": 1,
        "type": "int"
    },
    "expected_value":{
        "value": "",
        "tips": "读取期望值, 示例: [1] 或 [1, 2, 3]",
        "type": "json"
    },
    "write_value":{
        "value": "",
        "tips": "写入值, 如 [1, 2, 3, 4, 5]",
        "type": "json"
    },
    "slave_id": {
        "value": 1,
        "type": "int"
    },
    "task_data":{
        "value": "",
        "type": "json"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.timeout = 60
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.tasks = None
        self.opt = None
        self.st_addr = 0
        self.length = 1
        self.result = None
        self.value = None
        self.expected_value = None
        self.modbus_tcp = ModbusTCP(ip="192.168.8.47", port=502, timeout=3)
        self.slave_id = 1    # 默认从机ID
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            self.opt = args.get("operation", None)
            self.st_addr = args.get("st_addr", 0)
            self.length = args.get("length", 1)
            self.tasks = args.get("task_data", None)
            self.value = args.get("write_value", None)
            self.slave_id = args.get("slave_id", self.slave_id)
            self.expected_value = args.get("expected_value", None)

        # 超时判断
        if time.time() - self.start_time > self.timeout:
            r.setError(f"script running timeout")
            self.status = MoveStatus.FAILED

        # =====处理业务逻辑=====
        if self.opt == "read_coils":
            self.read_coils(r)
        elif self.opt == "read_registers":
            self.read_registers(r)
        elif self.opt == "write_coils":
            self.write_coils(r)
        elif self.opt == "write_registers":
            self.write_registers(r)
        elif self.opt == "tasks_list":
            self.execute_tasks(r)
        if self.status == MoveStatus.FINISHED or self.status == MoveStatus.FAILED:
            self.modbus_tcp.close()
        # =====数据上报及日志打印=====
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        self.report_info['execute_result'] = self.result
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def read_coils(self, r: SimModule):
        self.result = self.modbus_tcp.read_coils(self.slave_id, self.st_addr, self.length)
        if self.result is not None:
            if self.expected_value:
                if tuple(self.expected_value) == self.result:
                    self.status = MoveStatus.FINISHED
                else:
                    r.setError(f"unexpected value: {self.result}")
                    self.status = MoveStatus.FAILED
            else:
                self.status = MoveStatus.FINISHED

    def write_coils(self, r: SimModule):
        self.modbus_tcp.write_multi_coils(self.slave_id, self.st_addr, self.value)
        self.result = self.modbus_tcp.read_coils(self.slave_id, self.st_addr, len(self.value))
        if self.result is not None:
            self.status = MoveStatus.FINISHED

    def read_registers(self, r: SimModule):
        self.result = self.modbus_tcp.read_holding_registers(self.slave_id, self.st_addr, self.length)
        if self.result is not None:
            if self.expected_value:
                if tuple(self.expected_value) == self.result:
                    self.status = MoveStatus.FINISHED
                else:
                    r.setError(f"unexpected value: {self.result}")
                    self.status = MoveStatus.FAILED
            else:
                self.status = MoveStatus.FINISHED

    def write_registers(self, r: SimModule):
        self.modbus_tcp.write_multi_registers(self.slave_id, self.st_addr, self.value)
        self.result = self.modbus_tcp.read_holding_registers(self.slave_id, self.st_addr, len(self.value))
        if self.result is not None:
            self.status = MoveStatus.FINISHED

    def execute_tasks(self, r):
        self.result = []
        for task in self.tasks:
            try:
                if len(task.get('write_value', [])) == 1:
                    value = task['write_value'][0]
                else:
                    value = task.get('write_value', 0)
                ret = self.modbus_tcp.tcp_master.execute(task['slave_id'], task['func_code'], task['st_addr'],
                                                         quantity_of_x=task.get('length', 0),
                                                         output_value=value)
                self.result.append(ret)

                # 读操作结果对比
                if "expected_value" in task:
                    if ret != tuple(task['expected_value']):
                        r.setError(f"unexpected read result: {ret}, expected_value: {tuple(task['expected_value'])}")
                        self.status = MoveStatus.FAILED
                        break

            except Exception as e:
                r.setError(f"execute_tasks error: {e}")
                self.status = MoveStatus.FAILED
                break

        if len(self.result) == len(self.tasks):
            self.status = MoveStatus.FINISHED

    def cancel(self, r):
        # =====处理任务取消时的业务=====
        r.setNotice(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        r.setNotice(f"suspend task")
        self.status = MoveStatus.SUSPENDED


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

    def close(self):
        self.tcp_master.close()


# class ModbusRTU:
#     def __init__(self, port, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=0, timeout=1.0):
#         """
#         Modbus-RTU协议串口通信
#         @param port: 串口
#         @param baudrate: 波特率
#         @param bytesize: 字节大小
#         @param parity: 校验位
#         @param stopbits: 停止位
#         @param xonxoff: 读超时
#         @param timeout: 写超时
#         """
#         self.rtu_master = modbus_rtu.RtuMaster(serial.Serial(port=port, baudrate=baudrate, bytesize=bytesize,
#                                                              parity=parity, stopbits=stopbits, xonxoff=xonxoff))
#         self.rtu_master.set_timeout(timeout)
#
#     @staticmethod
#     def rtu_master_func_demo():
#         master = modbus_rtu.RtuMaster(serial.Serial(port=502, baudrate=9600,
#                                                     bytesize=8, parity='N', stopbits=1, xonxoff=0))
#         master.set_timeout(1.0)
#         res1 = master.execute(1, cst.READ_COILS, 0, 10)
#         res2 = master.execute(2, cst.READ_DISCRETE_INPUTS, 0, 8)
#         res3 = master.execute(3, cst.READ_INPUT_REGISTERS, 100, 3)
#         res4 = master.execute(4, cst.READ_HOLDING_REGISTERS, 100, 12)
#         res5 = master.execute(5, cst.WRITE_SINGLE_COIL, 7, output_value=1)
#         res6 = master.execute(6, cst.WRITE_SINGLE_REGISTER, 100, output_value=8)
#         res7 = master.execute(7, cst.WRITE_MULTIPLE_COILS, 0, output_value=[1, 1, 0, 1, 1])
#         res8 = master.execute(8, cst.WRITE_MULTIPLE_REGISTERS, 100, output_value=[1, 2, 3, 4, 5])
#         print(f"{res1}-{res2}-{res3}-{res4}-{res5}-{res6}-{res7}-{res8}")


if __name__ == '__main__':  # 本地运行测试
    task1 = [
        {
            "slave": 1,
            "func_code": 3,
            "st_addr": 1,
            "length": 1,
            "expected_value": [5]
        }
    ]
    # args1 = {"operation": "tasks_list", "st_addr": 0, "length": 10, "write_value": [1] * 10}
    # args1 = {"slave_id": 2, "operation": "write_registers", "st_addr": 0, "length": 10, "write_value": [6]*10}
    args1 = {"operation": "read_registers", "st_addr": 0, "length": 2}

    r1 = SimModule()
    m = Module(r1, args1)
    m.run(r1, args1)

    """ 
    md = ModbusTCP(ip='127.0.0.1', port=502, timeout=1.0)
    try:
        res1 = md.write_multi_registers(1, 0, list(range(3, 33, 3)))
        res2 = md.write_single_register(1, 3, 6666)
        ret1 = md.read_holding_registers(1, 0, 10)
        ret2 = md.read_holding_registers(1, 6, 1)

    except Exception as e:
        print(f"exception: {e}")
    else:
        print(f"{ret1}")
        print(f"{ret2}")
    """
