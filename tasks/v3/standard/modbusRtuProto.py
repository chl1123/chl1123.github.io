#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Date: 2026/04/10
# @Project: Modbus RTU / RS485 通用协议层

import struct
from typing import Iterable, Tuple, Union

import modbus_tk.defines as cst
import modbus_tk.modbus_rtu as modbus_rtu
import serial


# ============================================================================
# Modbus RTU 通用协议封装
# ============================================================================
class ModbusRtuProto:
    """
    通用 Modbus-RTU 协议封装（基于 modbus_tk）
    只提供连接、标准功能码读写和基础数据转换，不承载业务寄存器语义。
    """

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: Union[int, float] = 1,
        timeout: float = 1.0,
        verbose: bool = False,
        auto_open: bool = True,
    ):
        self.port = port
        self.serial = serial.Serial(
            port=port,
            baudrate=int(baudrate),
            bytesize=int(bytesize),
            parity=self._normalize_parity(parity),
            stopbits=self._normalize_stopbits(stopbits),
            timeout=float(timeout),
            xonxoff=0,
        )
        self.master = modbus_rtu.RtuMaster(self.serial)
        self.master.set_timeout(float(timeout))
        self.master.set_verbose(bool(verbose))
        if auto_open:
            self.open()

    def __del__(self):
        self.close()

    @staticmethod
    def _normalize_parity(parity: str) -> str:
        parity = str(parity).upper()
        if parity not in ("N", "E", "O"):
            raise ValueError("parity must be one of: N/E/O")
        return parity

    @staticmethod
    def _normalize_stopbits(stopbits: Union[int, float]) -> Union[int, float]:
        if stopbits in (1, 1.0):
            return 1
        if stopbits in (2, 2.0):
            return 2
        raise ValueError("stopbits must be 1 or 2")

    @staticmethod
    def u16_to_i16(value: int) -> int:
        return struct.unpack(">h", struct.pack(">H", value & 0xFFFF))[0]

    @staticmethod
    def i16_to_u16(value: int) -> int:
        return value & 0xFFFF

    @staticmethod
    def check_range(name: str, value: int, min_value: int, max_value: int):
        if not (min_value <= value <= max_value):
            raise ValueError(f"{name} out of range: {value}, expect [{min_value}, {max_value}]")

    def open(self):
        self.master.open()

    def close(self):
        try:
            self.master.close()
        except Exception:
            pass

    def execute(self, slave: int, function_code: int, start_addr: int, num: int = 0, output_value=0):
        return self.master.execute(slave, function_code, start_addr, num, output_value=output_value)

    # 4x
    def read_holding_registers(self, start_addr: int, num: int, slave: int = 1) -> Tuple[int, ...]:
        """读取保持寄存器"""
        self.check_range("num", int(num), 1, 125)
        return self.master.execute(slave, cst.READ_HOLDING_REGISTERS, start_addr, num)

    def write_single_register(self, addr: int, value: int, slave: int = 1) -> Tuple[int, int]:
        """写单个保持寄存器"""
        return self.master.execute(slave, cst.WRITE_SINGLE_REGISTER, addr, output_value=value)

    def write_multiple_registers(self, start_addr: int, values: Iterable[int], slave: int = 1) -> Tuple[int, int]:
        """写多个保持寄存器"""
        value_list = list(values)
        self.check_range("len(values)", len(value_list), 1, 123)
        return self.master.execute(slave, cst.WRITE_MULTIPLE_REGISTERS, start_addr, output_value=value_list)

    # 0x
    def read_coils(self, start_addr: int, num: int, slave: int = 1) -> Tuple[int, ...]:
        """读取线圈状态"""
        self.check_range("num", int(num), 1, 2000)
        return self.master.execute(slave, cst.READ_COILS, start_addr, num)

    def write_single_coil(self, addr: int, value: int, slave: int = 1) -> Tuple[int, int]:
        """写单个线圈"""
        coil_value = 1 if int(value) else 0
        return self.master.execute(slave, cst.WRITE_SINGLE_COIL, addr, output_value=coil_value)

    def write_multiple_coils(self, start_addr: int, values: Iterable[int], slave: int = 1) -> Tuple[int, int]:
        """写多个线圈"""
        value_list = [1 if int(v) else 0 for v in values]
        self.check_range("len(values)", len(value_list), 1, 1968)
        return self.master.execute(slave, cst.WRITE_MULTIPLE_COILS, start_addr, output_value=value_list)

    # 3x
    def read_input_registers(self, start_addr: int, num: int, slave: int = 1) -> Tuple[int, ...]:
        """读取输入寄存器"""
        self.check_range("num", int(num), 1, 125)
        return self.master.execute(slave, cst.READ_INPUT_REGISTERS, start_addr, num)

    # 1x
    def read_discrete_inputs(self, start_addr: int, num: int, slave: int = 1) -> Tuple[int, ...]:
        """读取离散输入"""
        self.check_range("num", int(num), 1, 2000)
        return self.master.execute(slave, cst.READ_DISCRETE_INPUTS, start_addr, num)
