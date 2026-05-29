# -*- coding: utf-8 -*-
# @Date : 2026/05/12
# @Author : mazj
# @Project: CP 点充电站标准任务脚本

import json
import time
from typing import Callable, Dict

start_time = time.time()

import modbus_tk.hooks as modbus_hooks

from syspy import Battery, Module, ModuleBase, ScriptParam, ScriptStatus, Trace
from syspy.utils.param_server import ParamType

from syspy.comms.modbus import ModbusTcpProto


script_param = ScriptParam(__file__)
BATTERY_TOPIC = "Battery-000"
LOG_MODULE = "CP_CHARGER"


def _trace_log(text: str, name: str = LOG_MODULE) -> None:
    """Emit trace logs with channel name."""
    Trace.log(f"[{name}] {text}", name=name)


def _hex_bytes(data: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


class ConfigParams:
    """脚本配置参数"""

    host = None
    port = None
    timeout = None
    slave_id = None

    end_current = None
    charge_time_s = None

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="network", name="Network", desc="Modbus TCP network config"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="host", name="Host", desc="CP charger Modbus TCP host"):
                        builder.TYPE(ParamType.IP)
                        builder.DEFAULTVALUE("192.168.192.5")

                    with builder.CHILD(key="port", name="Port", desc="CP charger Modbus TCP port"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(502, min_value=1, max_value=65535)

                    with builder.CHILD(key="timeout", name="Timeout", desc="Modbus TCP timeout"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(3.0, min_value=0.1, max_value=30.0)
                        builder.UNIT("s")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="slaveId", name="Slave ID", desc="Modbus slave id"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=1, max_value=247)

            with builder.GROUP(key="chargeConfig", name="Charge Config", desc="Charge action config"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="endCurrent", name="End Current", desc="Charge end current"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(10.0, min_value=0.1, max_value=500.0)
                        builder.UNIT("A")
                        builder.SINGLESTEP(0.1)

                    with builder.CHILD(key="chargeTimeS", name="Charge Time", desc="Charge time"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(3600, min_value=1, max_value=86400)
                        builder.UNIT("s")

        builder.save(merge=True)
        cls.load_config()

    @classmethod
    def load_config(cls):
        config = script_param.loadConfig()
        _trace_log(f"Loaded cp charger config: {config}")
        cls.host = config.get("host")
        cls.port = int(config.get("port"))
        cls.timeout = float(config.get("timeout"))
        cls.slave_id = int(config.get("slaveId"))

        cls.end_current = float(config.get("endCurrent"))
        cls.charge_time_s = int(config.get("chargeTimeS"))


ConfigParams.init()


def script_config_callback():
    _trace_log("cpCharger script_config_callback()")
    ConfigParams.load_config()


class InputParams:
    """脚本输入参数"""

    builder = script_param.builderInput()

    with builder.GROUPS():
        with builder.GROUP(key="operation", name="Operation", desc="CP charger operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)

            with builder.CHILDREN():
                with builder.CHILD(key="charge", name="Charge", desc="Set charge params and start charging"):
                    builder.TYPE(ParamType.ARRAY)

                with builder.CHILD(key="stop", name="Stop", desc="Stop charging and reset charger"):
                    builder.TYPE(ParamType.ARRAY)

    builder.save()


script_param.addAction(
    action_name="charge",
    policy={},
    args={
        "operation": "charge",
    },
    config={},
)

script_param.addAction(
    action_name="stop",
    policy={},
    args={
        "operation": "stop",
    },
    config={},
)

script_param.saveAction()


class _CpChargerClient:
    """CP 充电站 Modbus-TCP 客户端"""

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

    INPUT_SIG_RETRACTED_BIT = 3  # 3x13 Bit3: 缩到位

    def __init__(self, host: str, port: int, timeout: float, slave_id: int):
        self.slave_id = int(slave_id)
        self.modbus = ModbusTcpProto(host=host, port=port, timeout=timeout)
        self._send_hook = self._before_send

    def close(self):
        try:
            modbus_hooks.uninstall_hook("modbus_tcp.TcpMaster.before_send", self._send_hook)
        except Exception:
            pass
        self.modbus.close()

    def _before_send(self, args):
        master, request = args
        if master is self.modbus.master:
            _trace_log(f"modbus tx: { _hex_bytes(request) }")
        return None

    def _install_send_hook(self):
        try:
            modbus_hooks.uninstall_hook("modbus_tcp.TcpMaster.before_send", self._send_hook)
        except Exception:
            pass
        modbus_hooks.install_hook("modbus_tcp.TcpMaster.before_send", self._send_hook)

    def _write_register(self, address: int, value: int):
        _trace_log(f"write register addr=0x{int(address):04X} value=0x{int(value):04X}")
        return self.modbus.write_single_register(int(address), int(value), self.slave_id)

    def _read_input_register(self, address: int) -> int:
        return self.modbus.read_input_registers(int(address), 1, self.slave_id)[0]

    def _pulse_coil(self, address: int, release: bool = True):
        _trace_log(f"pulse coil addr=0x{int(address):04X} value=0xFF00")
        self.modbus.write_single_coil(int(address), 1, self.slave_id)
        if release:
            _trace_log(f"pulse coil addr=0x{int(address):04X} value=0x0000")
            self.modbus.write_single_coil(int(address), 0, self.slave_id)

    @staticmethod
    def _to_scaled_u16(name: str, value: float, scale: int = 10) -> int:
        scaled = int(round(float(value) * scale))
        if not (0 <= scaled <= 0xFFFF):
            raise ValueError(f"{name} out of range: {value}")
        return scaled

    @staticmethod
    def _bit(value: int, bit_index: int) -> int:
        return (int(value) >> int(bit_index)) & 0x01

    def read_status(self) -> Dict:
        input_sigs = self._read_input_register(self.REG_INPUT_SIGS)
        output_sigs = self._read_input_register(self.REG_OUTPUT_SIGS)
        event_code = self._read_input_register(self.REG_EVENT)
        errors = self._read_input_register(self.REG_ERRORS)
        return {
            "inputSignals": input_sigs,
            "outputSignals": output_sigs,
            "event": event_code,
            "errors": errors,
            "isRetracted": bool(self._bit(input_sigs, self.INPUT_SIG_RETRACTED_BIT)),
        }

    def is_retracted(self) -> bool:
        input_sigs = self._read_input_register(self.REG_INPUT_SIGS)
        return bool(self._bit(input_sigs, self.INPUT_SIG_RETRACTED_BIT))

    def charge(
        self,
        voltage: float,
        current: float,
        end_current: float,
        charge_time_s: int,
        start_retry_timeout_s: float,
        start_retry_interval_s: float,
        started_predicate: Callable[[], bool],
    ) -> Dict:
        self._install_send_hook()
        voltage_raw = self._to_scaled_u16("voltage", voltage, 10)
        current_raw = self._to_scaled_u16("current", current, 10)
        end_current_raw = self._to_scaled_u16("end_current", end_current, 10)
        charge_time_s = int(charge_time_s)
        if not (0 <= charge_time_s <= 0xFFFF):
            raise ValueError(f"charge_time_s out of range: {charge_time_s}")

        self._write_register(self.REG_CHARGE_CURRENT, current_raw)
        self._write_register(self.REG_CHARGE_VOLTAGE, voltage_raw)
        self._write_register(self.REG_END_CURRENT, end_current_raw)
        self._write_register(self.REG_CHARGE_TIME, charge_time_s)
        start_time_local = time.time()
        start_attempts = 0
        last_status = {}

        while True:
            start_attempts += 1
            _trace_log(
                f"send start coil continuously: attempt={start_attempts}, "
                f"elapsed={round(time.time() - start_time_local, 3)}s"
            )
            self._pulse_coil(self.COIL_START, release=False)
            last_status = self.read_status()
            if started_predicate():
                break
            if time.time() - start_time_local > float(start_retry_timeout_s):
                raise TimeoutError(
                    f"wait charger extend timeout: {start_retry_timeout_s}s, last_status={last_status}"
                )
            time.sleep(float(start_retry_interval_s))

        return {
            "voltage": float(voltage),
            "current": float(current),
            "endCurrent": float(end_current),
            "chargeTimeS": charge_time_s,
            "startRetryTimeoutS": float(start_retry_timeout_s),
            "startRetryIntervalS": float(start_retry_interval_s),
            "startAttempts": int(start_attempts),
            "status": last_status,
        }

    def stop(
        self,
        retract_timeout_s: float,
        poll_interval_s: float,
    ) -> Dict:
        self._install_send_hook()
        self._pulse_coil(self.COIL_STOP)

        start_time_local = time.time()
        while True:
            if self.is_retracted():
                break
            if time.time() - start_time_local > float(retract_timeout_s):
                raise TimeoutError("wait charger retract timeout")
            time.sleep(float(poll_interval_s))

        self._pulse_coil(self.COIL_RESET)
        return {
            "waitRetractSeconds": round(time.time() - start_time_local, 3),
            "status": self.read_status(),
        }


class CpChargerTask(ModuleBase):
    """CP 充电站标准任务脚本"""

    DEFAULT_START_RETRY_TIMEOUT_S = 120.0  # 连续发送启动报文的默认超时时间，单位秒
    DEFAULT_START_RETRY_INTERVAL_S = 0.2  # 连续发送启动报文的默认周期，单位秒
    DEFAULT_RETRACT_TIMEOUT_S = 30.0  # 等待机械臂缩到位的默认超时时间，单位秒
    DEFAULT_POLL_INTERVAL_S = 0.2  # 轮询缩到位信号的默认周期，单位秒

    def __init__(self):
        super().__init__()
        self.status = ScriptStatus.NONE
        self.args = {}
        self.report_info = {}

    def init_args(self, args: Dict):
        self.args = args or {}
        self.report_info["args"] = self.args
        if self.args:
            self.status = ScriptStatus.RUNNING

    def reset(self):
        self.args = {}

    def update_report_info(self):
        self.report_info["taskId"] = Module.getTaskId()
        self.report_info["status"] = self.status
        self.report_info["taskTime"] = round(time.time() - start_time, 2)

    @staticmethod
    def _is_positive_number(value) -> bool:
        try:
            return float(value) != 0 # 只要不为0(默认值)就认为数据有效
        except Exception:
            return False

    def _get_battery_max_charge_values(self):
        # voltage = Battery.getMaxChargeVoltage(topic=BATTERY_TOPIC)
        # current = Battery.getMaxChargeCurrent(topic=BATTERY_TOPIC)
        voltage = 90.0
        current = 200.0

        if not self._is_positive_number(voltage) or not self._is_positive_number(current):
            _trace_log(
                f"[WARN] invalid battery max charge values: voltage={voltage}, current={current}, "
                f"使用模拟数据： 充电电压voltage={83.4}, 充电电流current={100.0}"
            )
            voltage = 83.4
            current = 100.0

        return float(voltage), float(current)

    def _resolve_float_arg(self, key: str, default_value: float) -> float:
        if key in self.args:
            return float(self.args.get(key))
        return float(default_value)

    def _resolve_int_arg(self, key: str, default_value: int) -> int:
        if key in self.args:
            return int(self.args.get(key))
        return int(default_value)

    def _build_client(self) -> _CpChargerClient:
        return _CpChargerClient(
            host=ConfigParams.host,
            port=ConfigParams.port,
            timeout=ConfigParams.timeout,
            slave_id=ConfigParams.slave_id,
        )

    def _is_charge_started(self) -> bool:
        charge_current = float(Battery.getChargeCurrent(topic=BATTERY_TOPIC) or 0.0)
        is_charging = bool(Battery.getIsCharging(topic=BATTERY_TOPIC))
        self.report_info["chargeDetect"] = {
            "chargeCurrent": charge_current,
            "isCharging": is_charging,
        }
        _trace_log(
            f"charge detect: charge_current={charge_current}A, is_charging={is_charging}"
        )
        return charge_current > 0.0 or is_charging

    def _run_charge(self):
        battery_max_voltage, battery_max_current = self._get_battery_max_charge_values()
        voltage = battery_max_voltage
        current = battery_max_current
        end_current = self._resolve_float_arg("endCurrent", ConfigParams.end_current)
        charge_time_s = self._resolve_int_arg("chargeTimeS", ConfigParams.charge_time_s)
        start_retry_timeout_s = self._resolve_float_arg("startRetryTimeoutS", self.DEFAULT_START_RETRY_TIMEOUT_S)
        start_retry_interval_s = self._resolve_float_arg("startRetryIntervalS", self.DEFAULT_START_RETRY_INTERVAL_S)
        client = self._build_client()
        try:
            _trace_log(
                f"start cp charger charge: voltage={voltage}V, current={current}A, "
                f"end_current={end_current}A, charge_time_s={charge_time_s}s, "
                f"start_retry_timeout_s={start_retry_timeout_s}s, "
                f"start_retry_interval_s={start_retry_interval_s}s"
            )
            result = client.charge(
                voltage=voltage,
                current=current,
                end_current=end_current,
                charge_time_s=charge_time_s,
                start_retry_timeout_s=start_retry_timeout_s,
                start_retry_interval_s=start_retry_interval_s,
                started_predicate=self._is_charge_started,
            )
        finally:
            client.close()

        self.report_info["chargeSource"] = "battery.max"
        self.report_info["chargeConfig"] = {
            "host": ConfigParams.host,
            "port": ConfigParams.port,
            "slaveId": ConfigParams.slave_id,
            "batteryTopic": BATTERY_TOPIC,
            "batteryMaxVoltage": battery_max_voltage,
            "batteryMaxCurrent": battery_max_current,
            "chargeVoltage": voltage,
            "chargeCurrent": current,
            "endCurrent": end_current,
            "chargeTimeS": charge_time_s,
            "startRetryTimeoutS": start_retry_timeout_s,
            "startRetryIntervalS": start_retry_interval_s,
        }
        return result

    def _run_stop(self):
        retract_timeout_s = self._resolve_float_arg("retractTimeoutS", self.DEFAULT_RETRACT_TIMEOUT_S)
        poll_interval_s = self._resolve_float_arg("pollIntervalS", self.DEFAULT_POLL_INTERVAL_S)
        stop_config = {
            "retractTimeoutS": retract_timeout_s,
            "pollIntervalS": poll_interval_s,
        }

        client = self._build_client()
        try:
            _trace_log(f"start cp charger stop: retract_timeout_s={retract_timeout_s}s, poll_interval_s={poll_interval_s}s")
            result = client.stop(
                retract_timeout_s=retract_timeout_s,
                poll_interval_s=poll_interval_s,
            )
            _trace_log(f"cp charger stop result: {result}")
            result["stopConfig"] = stop_config
            return result
        except Exception as e:
            result = {
                "error": str(e),
                "stopConfig": stop_config,
            }
            try:
                result["status"] = client.read_status()
            except Exception as read_err:
                result["statusError"] = str(read_err)
            return result
        finally:
            client.close()

    def run(self):
        operation = self.args.get("operation")
        self.report_info["operation"] = operation

        try:
            if operation == "charge":
                result = self._run_charge()
            elif operation == "stop":
                result = self._run_stop()
            else:
                raise ValueError(f"unsupported operation: {operation}")

            self.report_info["result"] = result
            if isinstance(result, dict) and result.get("error"):
                self.report_info["error"] = result.get("error")
                self.status = ScriptStatus.FAILED
                _trace_log(f"[ERROR] cp charger {operation} failed: {result}")
            else:
                self.status = ScriptStatus.FINISHED
                _trace_log(f"cp charger {operation} finished: {result}")
        except Exception as e:
            self.report_info["error"] = str(e)
            self.status = ScriptStatus.FAILED
            _trace_log(f"[ERROR] cp charger {operation} failed: {e}")

    def suspend(self):
        if self.status == ScriptStatus.RUNNING:
            self.status = ScriptStatus.SUSPENDED
        _trace_log("cpCharger suspend")

    def resume(self):
        if self.status == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        _trace_log("cpCharger resume")

    def cancel(self):
        self.status = ScriptStatus.FAILED
        _trace_log("cpCharger cancel")


def main():
    ScriptParam.setConfigChangeCallBack(script_config_callback)

    Module.init()
    task = CpChargerTask()

    while True:
        status = task.status
        Module.setStatus(status)
        task.update_report_info()
        Module.reportInfo(task.report_info)

        if status == ScriptStatus.NONE:
            args = Module.getTaskArgs()
            if args:
                try:
                    args = script_param.loadInput(args)
                    task.init_args(args)
                except ValueError as e:
                    task.report_info["error"] = str(e)
                    _trace_log(f"[ERROR] cp charger input error: {e}")
        elif status == ScriptStatus.RUNNING:
            task.run()
        elif status == ScriptStatus.SUSPENDED:
            task.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            _trace_log(f"cp charger task finished with status: {status}", name=f"{LOG_MODULE}.status")
            task.reset()
            task.status = ScriptStatus.NONE

        time.sleep(0.1)


if __name__ == "__main__":
    main()
