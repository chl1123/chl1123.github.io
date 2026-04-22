# -*- coding: utf-8 -*-
# @Date : 2026/04/10
# @Author : codex
# @Coding : none
# @Project: CKY-DG 称重设备 Modbus-RTU 模拟发送端

import os
import pty
import select
import threading
import time

import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

DEFAULT_SLAVE_ID = 1 # 默认 Modbus 从站 ID
DEFAULT_RAW_WEIGHT = 1234 # 默认重量
DEFAULT_DECIMAL_POINT = 2 # 默认小数点位置（即显示重量 = raw_weight / (10 ** decimal_point)），例如 1234 和 2 则显示 12.34
DEFAULT_UNIT_CODE = 2 # 默认单位代码（2=Kg)


class PtyMasterSerial:
    """
    将 pty 的 master fd 适配为 modbus_tk.RtuServer 可用的 serial 对象。
    """

    def __init__(self, master_fd: int, baudrate: int = 9600, timeout: float = 0.02):
        self.fd = master_fd
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)
        self.inter_byte_timeout = 0.0
        self.name = f"pty-master-{master_fd}"
        self.is_open = True

    def open(self):
        self.is_open = True

    def close(self):
        if self.is_open:
            os.close(self.fd)
            self.is_open = False

    @property
    def in_waiting(self):
        r, _, _ = select.select([self.fd], [], [], 0)
        return 1 if r else 0

    def read(self, size=1):
        if not self.is_open:
            return b""
        r, _, _ = select.select([self.fd], [], [], self.timeout)
        if not r:
            return b""
        return os.read(self.fd, size)

    def write(self, data):
        return os.write(self.fd, data)

    def flush(self):
        return None

    def cancel_read(self):
        return None


class ScaleModbusSimulator:
    """
    CKY-DG 简化模拟设备：
    - 持有寄存器 0x00~0x3F
    - 支持接收去皮/清零命令并更新显示值
    """

    REG_DISPLAY_VALUE = 0x00
    REG_DECIMAL_POINT = 0x01
    REG_UNIT = 0x02
    REG_TARE = 0x11
    REG_ZERO = 0x16

    def __init__(self, slave_id: int = 1, raw_weight: int = 1234, decimal_point: int = 2, unit_code: int = 2):
        self.slave_id = int(slave_id)
        self.base_raw_weight = int(raw_weight)
        self.decimal_point = int(decimal_point)
        self.unit_code = int(unit_code)
        self.tare_active = False
        self.stop_event = threading.Event()
        self.thread = None

        master_fd, self.slave_fd = pty.openpty()
        self.slave_port = os.ttyname(self.slave_fd)
        self.master_serial = PtyMasterSerial(master_fd=master_fd)
        self.server = modbus_rtu.RtuServer(self.master_serial)

        self.slave = self.server.add_slave(self.slave_id)
        self.slave.add_block("hr", cst.HOLDING_REGISTERS, 0, 64)
        self._init_registers()

    def _init_registers(self):
        self.slave.set_values("hr", self.REG_DISPLAY_VALUE, [self.base_raw_weight])
        self.slave.set_values("hr", self.REG_DECIMAL_POINT, [self.decimal_point])
        self.slave.set_values("hr", self.REG_UNIT, [self.unit_code])
        self.slave.set_values("hr", self.REG_TARE, [2])
        self.slave.set_values("hr", self.REG_ZERO, [0])

    def _apply_business_logic(self):
        tare_val = self.slave.get_values("hr", self.REG_TARE, 1)[0]
        zero_val = self.slave.get_values("hr", self.REG_ZERO, 1)[0]

        if tare_val == 1:
            self.tare_active = True
            self.slave.set_values("hr", self.REG_DISPLAY_VALUE, [0])
        elif tare_val == 2:
            self.tare_active = False
            self.slave.set_values("hr", self.REG_DISPLAY_VALUE, [self.base_raw_weight])

        if zero_val == 0x0011:
            self.base_raw_weight = 0
            self.slave.set_values("hr", self.REG_DISPLAY_VALUE, [0])
            self.slave.set_values("hr", self.REG_ZERO, [0])

    def _run(self):
        self.server._do_init()
        self.server._block_on_first_byte = False
        while not self.stop_event.is_set():
            self.server._do_run()
            self._apply_business_logic()
        self.server._do_exit()

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if self.slave_fd is not None:
            os.close(self.slave_fd)
            self.slave_fd = None


def main():
    sim = ScaleModbusSimulator(
        slave_id=DEFAULT_SLAVE_ID,
        raw_weight=DEFAULT_RAW_WEIGHT,
        decimal_point=DEFAULT_DECIMAL_POINT,
        unit_code=DEFAULT_UNIT_CODE,
    )
    sim.start()

    print(
        "[sender] started "
        f"port={sim.slave_port}, slave_id={DEFAULT_SLAVE_ID}, "
        f"raw_weight={DEFAULT_RAW_WEIGHT}, decimal_point={DEFAULT_DECIMAL_POINT}, "
        f"unit_code={DEFAULT_UNIT_CODE}"
    )
    print("[sender] press Ctrl+C to stop")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[sender] stopping...")
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
