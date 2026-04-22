# -*- coding: utf-8 -*-
# @Date : 2026/04/10
# @Author : codex
# @Coding : none
# @Update : 简化为纯类工具，不含状态机、参数系统和main
# @Project: CKY-DG RS485 称重功能封装

import time
from typing import Dict, List, Optional, Tuple

from standard.modbusRtuProto import ModbusRtuProto


class CkyDgScale:
    """
    CKY-DG RS485(Modbus-RTU) 称重设备工具类

    功能：
    - 读取重量（单次/多次采样）
    - 去皮/清除去皮/清零
    - 读写寄存器（调试用途）
    """

    # 寄存器地址（文档地址减 40001）
    REG_DISPLAY_VALUE = 0x00  # 40001
    REG_DECIMAL_POINT = 0x01  # 40002
    REG_UNIT = 0x02  # 40003
    REG_TARE = 0x11  # 40018
    REG_ZERO = 0x16  # 40023

    UNIT_MAP = {
        1: "MPa",
        2: "Kg",
        3: "T",
        4: "g",
        5: "N",
        6: "KN",
    }

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        timeout: float = 1.0,
        slave_id: int = 1,
    ):
        self.slave_id = int(slave_id)
        self.modbus = ModbusRtuProto(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout,
            verbose=False,
            auto_open=False,
        )
        # 简化调用方：实例化后默认直接可用
        self.modbus.open()

    def __del__(self):
        self.close()

    def open(self):
        """打开串口连接"""
        self.modbus.open()

    def close(self):
        """关闭串口连接"""
        try:
            self.modbus.close()
        except Exception:
            pass

    def set_slave_id(self, slave_id: int):
        """设置默认从站 ID"""
        self.slave_id = int(slave_id)

    def _slave(self, slave_id: Optional[int] = None) -> int:
        """获取实际使用的从站 ID"""
        return self.slave_id if slave_id is None else int(slave_id)

    # ------------------------ 调试通用接口（私有） ------------------------
    def _read_registers(self, address: int, count: int = 1, slave_id: Optional[int] = None) -> Tuple[int, ...]:
        """读取保持寄存器"""
        return self.modbus.read_holding_registers(int(address), int(count), self._slave(slave_id))

    def _write_register(self, address: int, value: int, slave_id: Optional[int] = None) -> Tuple[int, int]:
        """写单个保持寄存器"""
        return self.modbus.write_single_register(int(address), int(value), self._slave(slave_id))

    def _read_all(self, slave_id: Optional[int] = None) -> Tuple[int, ...]:
        """读取 0x00~0x17 共 24 个保持寄存器"""
        return self._read_registers(0x00, 0x18, slave_id)

    # ------------------------ 称重业务接口 ------------------------
    def read_weight_once(self, slave_id: Optional[int] = None) -> Dict:
        """
        读取一次重量信息：
        - 0x00：原始值（16位有符号）
        - 0x01：小数点位
        - 0x02：单位编码
        """
        regs = self._read_registers(self.REG_DISPLAY_VALUE, 3, slave_id)
        raw = ModbusRtuProto.u16_to_i16(regs[0])
        decimal_point = int(regs[1])
        unit_code = int(regs[2])
        value = raw / (10 ** decimal_point) if decimal_point >= 0 else float(raw)
        return {
            "raw": raw,
            "decimalPoint": decimal_point,
            "value": value,
            "unitCode": unit_code,
            "unit": self.UNIT_MAP.get(unit_code, f"unknown({unit_code})"),
        }

    def read_weight_samples(
        self,
        sample_count: int = 10,
        sample_interval: float = 0.1,
        slave_id: Optional[int] = None,
    ) -> Dict:
        """多次采样读取重量，并返回均值和样本"""
        sample_count = int(sample_count)
        if sample_count <= 0:
            raise ValueError("sample_count must > 0")

        samples: List[Dict] = []
        for i in range(sample_count):
            samples.append(self.read_weight_once(slave_id))
            if i < sample_count - 1 and sample_interval > 0:
                time.sleep(float(sample_interval))

        average_value = sum(s["value"] for s in samples) / len(samples)
        return {
            "sampleCount": len(samples),
            "averageValue": average_value,
            "last": samples[-1],
            "samples": samples,
        }

    def tare(self, slave_id: Optional[int] = None) -> Tuple[int, int]:
        """去皮：写 0x11 = 1"""
        return self._write_register(self.REG_TARE, 1, slave_id)

    def clear_tare(self, slave_id: Optional[int] = None) -> Tuple[int, int]:
        """清除去皮：写 0x11 = 2"""
        return self._write_register(self.REG_TARE, 2, slave_id)

    def zero(self, slave_id: Optional[int] = None) -> Tuple[int, int]:
        """清零：写 0x16 = 0x0011"""
        return self._write_register(self.REG_ZERO, 0x0011, slave_id)