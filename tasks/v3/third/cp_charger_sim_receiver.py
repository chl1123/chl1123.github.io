# -*- coding: utf-8 -*-
# @Date : 2026/05/13
# @Author : codex
# @Project: CP Charger Modbus-TCP 模拟接收端

import argparse
import json
import logging
import signal
import struct
import threading
import time
from dataclasses import dataclass
from typing import Dict, List

import modbus_tk.defines as cst
import modbus_tk.hooks as hooks
import modbus_tk.modbus_tcp as modbus_tcp


LOG_MODULE = "CP_CHARGER_SIM_RECEIVER"
LOGGER = logging.getLogger(LOG_MODULE)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 502
DEFAULT_FALLBACK_PORT = 1502
DEFAULT_SLAVE_ID = 1
DEFAULT_RETRACT_DELAY_S = 0.5
DEFAULT_VERBOSE = False


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _hr_name(addr: int) -> str:
    return f"4x{int(addr) + 1}"


def _ir_name(addr: int) -> str:
    return f"3x{int(addr) + 1}"


def _coil_name(addr: int) -> str:
    return f"0x{int(addr) + 1:02d}"


@dataclass
class SimConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    fallback_port: int = DEFAULT_FALLBACK_PORT
    slave_id: int = DEFAULT_SLAVE_ID
    retract_delay_s: float = DEFAULT_RETRACT_DELAY_S
    verbose: bool = DEFAULT_VERBOSE


class CpChargerModbusSimServer:
    """模拟 CP 充电站 Modbus TCP 从站，供 cpCharger.py 直接连接测试。"""

    REG_CHARGE_VOLTAGE = 23  # 4x24，0.1V/bit
    REG_CHARGE_CURRENT = 24  # 4x25，0.1A/bit
    REG_END_CURRENT = 26  # 4x27，0.1A/bit
    REG_CHARGE_TIME = 31  # 4x32，秒

    REG_INPUT_SIGS = 12  # 3x13
    REG_OUTPUT_SIGS = 13  # 3x14
    REG_EVENT = 17  # 3x18
    REG_ERRORS = 19  # 3x20

    COIL_START = 3  # 0x04 启动
    COIL_STOP = 6  # 0x07 停止
    COIL_RESET = 7  # 0x08 复位

    INPUT_SIG_RETRACTED_BIT = 3
    OUTPUT_SIG_WORKING_BIT = 4

    EVENT_IDLE = 0
    EVENT_CHARGING = 21
    EVENT_STOP_BY_USER = 47

    BLOCK_COILS = "coils"
    BLOCK_HOLDING = "holding"
    BLOCK_INPUT = "input"

    def __init__(self, config: SimConfig):
        self.config = config
        self.server = None
        self.slave = None
        self.actual_port = None
        self._serve_thread = None
        self._stop_event = threading.Event()
        self._pending_retract_at = None
        self._hooks = []
        self._state_lock = threading.RLock()
        self.trace: List[Dict] = []

    @staticmethod
    def _set_bit(value: int, bit_index: int, enabled: bool) -> int:
        if enabled:
            return int(value) | (1 << int(bit_index))
        return int(value) & ~(1 << int(bit_index))

    def _add_trace(self, kind: str, addr: int, value: int) -> None:
        self.trace.append(
            {
                "time": round(time.time(), 3),
                "kind": str(kind),
                "addr": int(addr),
                "value": int(value),
            }
        )

    def _get_ir(self, addr: int) -> int:
        return int(self.slave.get_values(self.BLOCK_INPUT, int(addr), 1)[0])

    def _set_ir(self, addr: int, value: int) -> None:
        self.slave.set_values(self.BLOCK_INPUT, int(addr), [int(value)])

    def _get_hr(self, addr: int) -> int:
        return int(self.slave.get_values(self.BLOCK_HOLDING, int(addr), 1)[0])

    def _get_coil(self, addr: int) -> int:
        return int(self.slave.get_values(self.BLOCK_COILS, int(addr), 1)[0])

    def _set_initial_values(self) -> None:
        self.slave.set_values(self.BLOCK_COILS, 0, [0] * 16)
        self.slave.set_values(self.BLOCK_HOLDING, 0, [0] * 64)
        self.slave.set_values(self.BLOCK_INPUT, 0, [0] * 64)

        input_sigs = self._set_bit(0, self.INPUT_SIG_RETRACTED_BIT, True)
        self._set_ir(self.REG_INPUT_SIGS, input_sigs)
        self._set_ir(self.REG_OUTPUT_SIGS, 0)
        self._set_ir(self.REG_EVENT, self.EVENT_IDLE)
        self._set_ir(self.REG_ERRORS, 0)

    def _build_server(self, port: int) -> None:
        server = modbus_tcp.TcpServer(port=int(port), address=self.config.host, timeout_in_sec=1)
        slave = server.add_slave(int(self.config.slave_id))
        slave.add_block(self.BLOCK_COILS, cst.COILS, 0, 16)
        slave.add_block(self.BLOCK_HOLDING, cst.HOLDING_REGISTERS, 0, 64)
        slave.add_block(self.BLOCK_INPUT, cst.ANALOG_INPUTS, 0, 64)

        self.server = server
        self.slave = slave
        self._set_initial_values()

    def _install_hook(self, name: str, fn) -> None:
        hooks.install_hook(name, fn) 
        self._hooks.append((name, fn))

    def _install_hooks(self) -> None:
        self._install_hook("modbus.Slave.handle_write_single_register_request", self._on_write_single_register)
        self._install_hook("modbus.Slave.handle_write_single_coil_request", self._on_write_single_coil)
        self._install_hook("modbus.Slave.handle_read_input_registers_request", self._on_read_input_registers)

    def _uninstall_hooks(self) -> None:
        while self._hooks:
            name, fn = self._hooks.pop()
            try:
                hooks.uninstall_hook(name, fn)
            except Exception:
                pass

    def _is_own_slave(self, slave) -> bool:
        return slave is self.slave

    def _refresh_timed_state(self) -> None:
        with self._state_lock:
            if self._pending_retract_at is None:
                return
            if time.time() < self._pending_retract_at:
                return

            input_sigs = self._get_ir(self.REG_INPUT_SIGS)
            input_sigs = self._set_bit(input_sigs, self.INPUT_SIG_RETRACTED_BIT, True)
            self._set_ir(self.REG_INPUT_SIGS, input_sigs)
            self._pending_retract_at = None
            LOGGER.info("retract reached, set %s bit%d=1", _ir_name(self.REG_INPUT_SIGS), self.INPUT_SIG_RETRACTED_BIT)

    def _on_read_input_registers(self, args):
        slave, _request_pdu = args
        if not self._is_own_slave(slave):
            return None
        self._refresh_timed_state()
        return None

    def _on_write_single_register(self, args):
        slave, request_pdu = args
        if not self._is_own_slave(slave):
            return None

        address, value = struct.unpack(">HH", request_pdu[1:5])
        self._add_trace("holding_register", address, value)

        if address == self.REG_CHARGE_VOLTAGE:
            LOGGER.info("recv write %s addr=%d raw=%d %.1fV", _hr_name(address), address, value, value / 10.0)
        elif address == self.REG_CHARGE_CURRENT:
            LOGGER.info("recv write %s addr=%d raw=%d %.1fA", _hr_name(address), address, value, value / 10.0)
        elif address == self.REG_END_CURRENT:
            LOGGER.info("recv write %s addr=%d raw=%d %.1fA", _hr_name(address), address, value, value / 10.0)
        elif address == self.REG_CHARGE_TIME:
            LOGGER.info("recv write %s addr=%d raw=%d %ss", _hr_name(address), address, value, value)
        else:
            LOGGER.info("recv write %s addr=%d raw=%d", _hr_name(address), address, value)
        return None

    def _set_working(self, enabled: bool) -> None:
        output_sigs = self._get_ir(self.REG_OUTPUT_SIGS)
        output_sigs = self._set_bit(output_sigs, self.OUTPUT_SIG_WORKING_BIT, enabled)
        self._set_ir(self.REG_OUTPUT_SIGS, output_sigs)

    def _set_retracted(self, enabled: bool) -> None:
        input_sigs = self._get_ir(self.REG_INPUT_SIGS)
        input_sigs = self._set_bit(input_sigs, self.INPUT_SIG_RETRACTED_BIT, enabled)
        self._set_ir(self.REG_INPUT_SIGS, input_sigs)

    def _apply_start_action(self) -> None:
        with self._state_lock:
            self._pending_retract_at = None
            self._set_retracted(False)
            self._set_working(True)
            self._set_ir(self.REG_EVENT, self.EVENT_CHARGING)

            LOGGER.info(
                "recv start %s addr=%d charge=%.1fV %.1fA end=%.1fA time=%ss",
                _coil_name(self.COIL_START),
                self.COIL_START,
                self._get_hr(self.REG_CHARGE_VOLTAGE) / 10.0,
                self._get_hr(self.REG_CHARGE_CURRENT) / 10.0,
                self._get_hr(self.REG_END_CURRENT) / 10.0,
                self._get_hr(self.REG_CHARGE_TIME),
            )

    def _apply_stop_action(self) -> None:
        with self._state_lock:
            self._set_working(False)
            self._set_ir(self.REG_EVENT, self.EVENT_STOP_BY_USER)
            self._pending_retract_at = time.time() + float(self.config.retract_delay_s)

            LOGGER.info(
                "recv stop %s addr=%d retract_delay=%.3fs",
                _coil_name(self.COIL_STOP),
                self.COIL_STOP,
                self.config.retract_delay_s,
            )

    def _apply_reset_action(self) -> None:
        with self._state_lock:
            self._pending_retract_at = None
            self._set_retracted(True)
            self._set_working(False)
            self._set_ir(self.REG_EVENT, self.EVENT_IDLE)
            self._set_ir(self.REG_ERRORS, 0)

            LOGGER.info("recv reset %s addr=%d", _coil_name(self.COIL_RESET), self.COIL_RESET)

    def _on_write_single_coil(self, args):
        slave, request_pdu = args
        if not self._is_own_slave(slave):
            return None

        address, raw_value = struct.unpack(">HH", request_pdu[1:5])
        value = 1 if raw_value == 0xFF00 else 0
        self._add_trace("coil", address, value)
        LOGGER.info("recv write %s addr=%d value=%d", _coil_name(address), address, value)

        if value == 1 and address == self.COIL_START:
            self._apply_start_action()
        elif value == 1 and address == self.COIL_STOP:
            self._apply_stop_action()
        elif value == 1 and address == self.COIL_RESET:
            self._apply_reset_action()
        return None

    def _candidate_ports(self) -> List[int]:
        candidates = [int(self.config.port)]
        fallback = int(self.config.fallback_port)
        if fallback not in candidates:
            candidates.append(fallback)
        return candidates

    def start(self) -> int:
        last_error = None
        for port in self._candidate_ports():
            try:
                self._build_server(port)
                self._install_hooks()
                self.server._do_init()
                self.actual_port = int(port)
                break
            except Exception as exc:
                last_error = exc
                LOGGER.warning("bind %s:%s failed: %r", self.config.host, port, exc)
                self._uninstall_hooks()
                self._safe_close_server()
                self.server = None
                self.slave = None
                self.actual_port = None

        if self.actual_port is None:
            raise RuntimeError(f"failed to start modbus tcp simulator: {last_error!r}")

        self._stop_event.clear()
        self._serve_thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._serve_thread.start()

        LOGGER.info(
            "sim server started host=%s port=%s slave_id=%s",
            self.config.host,
            self.actual_port,
            self.config.slave_id,
        )
        LOGGER.info("initial snapshot=%s", json.dumps(self.snapshot(), ensure_ascii=False))
        return self.actual_port

    def _serve_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                self.server._do_run()
                self._refresh_timed_state()
        finally:
            self._safe_close_server()

    def _safe_close_server(self) -> None:
        if self.server is not None:
            try:
                self.server._do_exit()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop_event.set()
        if self._serve_thread is not None:
            self._serve_thread.join(timeout=2.0)
            self._serve_thread = None
        self._uninstall_hooks()
        LOGGER.info("sim server stopped")

    def snapshot(self) -> Dict:
        with self._state_lock:
            if self.slave is None:
                return {
                    "host": self.config.host,
                    "port": self.actual_port,
                    "slaveId": self.config.slave_id,
                    "running": False,
                }

            input_sigs = self._get_ir(self.REG_INPUT_SIGS)
            output_sigs = self._get_ir(self.REG_OUTPUT_SIGS)
            voltage_raw = self._get_hr(self.REG_CHARGE_VOLTAGE)
            current_raw = self._get_hr(self.REG_CHARGE_CURRENT)
            end_current_raw = self._get_hr(self.REG_END_CURRENT)
            charge_time_s = self._get_hr(self.REG_CHARGE_TIME)

            return {
                "host": self.config.host,
                "port": self.actual_port,
                "slaveId": self.config.slave_id,
                "running": not self._stop_event.is_set(),
                "retractDelayS": self.config.retract_delay_s,
                "inputSignals": input_sigs,
                "outputSignals": output_sigs,
                "event": self._get_ir(self.REG_EVENT),
                "errors": self._get_ir(self.REG_ERRORS),
                "isRetracted": bool((input_sigs >> self.INPUT_SIG_RETRACTED_BIT) & 0x01),
                "isWorking": bool((output_sigs >> self.OUTPUT_SIG_WORKING_BIT) & 0x01),
                "chargeVoltageRaw": voltage_raw,
                "chargeCurrentRaw": current_raw,
                "endCurrentRaw": end_current_raw,
                "chargeTimeS": charge_time_s,
                "chargeVoltageV": voltage_raw / 10.0,
                "chargeCurrentA": current_raw / 10.0,
                "endCurrentA": end_current_raw / 10.0,
                "coils": {
                    _coil_name(self.COIL_START): self._get_coil(self.COIL_START),
                    _coil_name(self.COIL_STOP): self._get_coil(self.COIL_STOP),
                    _coil_name(self.COIL_RESET): self._get_coil(self.COIL_RESET),
                },
                "lastTrace": self.trace[-10:],
            }


def _parse_args() -> SimConfig:
    parser = argparse.ArgumentParser(description="CP charger Modbus TCP simulator")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind host, default 0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="preferred Modbus TCP port")
    parser.add_argument(
        "--fallback-port",
        type=int,
        default=DEFAULT_FALLBACK_PORT,
        help="fallback port if preferred port is unavailable",
    )
    parser.add_argument("--slave-id", type=int, default=DEFAULT_SLAVE_ID, help="Modbus slave id")
    parser.add_argument(
        "--retract-delay",
        type=float,
        default=DEFAULT_RETRACT_DELAY_S,
        help="delay before retract signal becomes true after stop",
    )
    parser.add_argument("--verbose", action="store_true", help="enable verbose logging")
    args = parser.parse_args()
    return SimConfig(
        host=str(args.host),
        port=int(args.port),
        fallback_port=int(args.fallback_port),
        slave_id=int(args.slave_id),
        retract_delay_s=float(args.retract_delay),
        verbose=bool(args.verbose),
    )


def main() -> None:
    config = _parse_args()
    _setup_logging(config.verbose)

    server = CpChargerModbusSimServer(config)
    stop_event = threading.Event()

    def _handle_stop(signum, _frame):
        LOGGER.info("recv signal=%s, stopping server", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    server.start()

    try:
        while not stop_event.is_set():
            time.sleep(1.0)
    finally:
        LOGGER.info("final snapshot=%s", json.dumps(server.snapshot(), ensure_ascii=False))
        server.stop()


if __name__ == "__main__":
    main()
