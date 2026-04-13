# -*- coding: utf-8 -*-
# @Date : 2026/04/10
# @Author : codex
# @Coding : none
# @Project: CKY-DG 称重设备 Modbus-RTU 模拟发送端

import argparse
import os
import pty
import select
import threading
import time

import modbus_tk.defines as cst
from modbus_tk import modbus_rtu


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
    parser = argparse.ArgumentParser(description="CKY-DG Modbus-RTU 模拟发送端")
    parser.add_argument("--port", type=int, default=8, help="虚拟串口号（如 8 则对应 /dev/pts/8")
    parser.add_argument("--slave-id", type=int, default=1, help="模拟设备从站ID")
    parser.add_argument("--raw-weight", type=int, default=1234, help="初始原始重量值(16位有符号)")
    parser.add_argument("--decimal-point", type=int, default=2, help="小数点位寄存器值")
    parser.add_argument("--unit-code", type=int, default=2, help="单位寄存器值(2=Kg)")
    args = parser.parse_args()

    sim = ScaleModbusSimulator(
        slave_id=args.slave_id,
        raw_weight=args.raw_weight,
        decimal_point=args.decimal_point,
        unit_code=args.unit_code,
    )
    sim.start()

    print(f"[sender] started on slave_id={args.slave_id}, port={sim.slave_port}")
    # if args.port_file:
    #     with open(args.port_file, "w", encoding="utf-8") as f:
    #         f.write(sim.slave_port)
    #     print(f"[sender] wrote port file: {args.port_file}")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[sender] stopping...")
    finally:
        sim.stop()


if __name__ == "__main__":
    main()
