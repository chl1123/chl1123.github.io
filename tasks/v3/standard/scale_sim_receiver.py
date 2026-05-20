# -*- coding: utf-8 -*-
# @Date : 2026/04/22
# @Project: CKY-DG 称重设备只读诊断脚本（标准任务脚本）

import time
from typing import Any, Dict, Optional

from syspy import Module, ModuleBase, ScriptStatus, ScriptParam, Trace
from syspy.utils.param_server import ParamType

from standard.weighing_scale import CkyDgScale


start_time = time.time()

script_param = ScriptParam(__file__)
LOG_MODULE = "SCALE_SIM_RECEIVER"


def _trace_log(text: str, name: str) -> None:
    Trace.log(f"[{name}] {text}", name=name)


class ConfigParams:
    """脚本配置参数定义"""

    port = "/dev/ttyUSB0"
    slave_id = 1
    baudrate = 9600
    timeout = 0.2
    bytesize = 8
    parity = "N"
    stopbits = 1

    sample_count = 5
    sample_interval = 0.02
    poll_count = 20
    poll_interval = 0.5
    holding_start = 0
    holding_count = 8
    input_start = 0
    input_count = 8

    @classmethod
    def init(cls):
        builder = script_param.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="serial", name="Serial", desc="串口配置"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="port", name="Port", desc="串口设备路径"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("/dev/ttyUSB0")

                    with builder.CHILD(key="slave_id", name="Slave ID", desc="Modbus 从站ID"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=1, max_value=247)

                    with builder.CHILD(key="baudrate", name="Baudrate", desc="波特率"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(9600, min_value=1200, max_value=921600)

                    with builder.CHILD(key="timeout", name="Timeout", desc="串口超时（秒）"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.2, min_value=0.01, max_value=10.0)
                        builder.SINGLESTEP(0.01)
                        builder.UNIT("s")

                    with builder.CHILD(key="bytesize", name="Byte Size", desc="数据位"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(8, min_value=5, max_value=8)

                    with builder.CHILD(key="parity", name="Parity", desc="校验位(N/E/O)"):
                        builder.TYPE(ParamType.STRING)
                        builder.DEFAULTVALUE("N")

                    with builder.CHILD(key="stopbits", name="Stop Bits", desc="停止位"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(1, min_value=1, max_value=2)

            with builder.GROUP(key="diag", name="Diag", desc="诊断配置"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="sample_count", name="Sample Count", desc="每轮采样次数"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(5, min_value=1, max_value=200)

                    with builder.CHILD(key="sample_interval", name="Sample Interval", desc="采样间隔（秒）"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.02, min_value=0.0, max_value=2.0)
                        builder.SINGLESTEP(0.01)
                        builder.UNIT("s")

                    with builder.CHILD(key="poll_count", name="Poll Count", desc="总轮询次数"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(20, min_value=1, max_value=10000)

                    with builder.CHILD(key="poll_interval", name="Poll Interval", desc="轮询间隔（秒）"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.5, min_value=0.0, max_value=60.0)
                        builder.SINGLESTEP(0.1)
                        builder.UNIT("s")

                    with builder.CHILD(key="holding_start", name="Holding Start", desc="保持寄存器起始地址"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(0, min_value=0, max_value=65535)

                    with builder.CHILD(key="holding_count", name="Holding Count", desc="保持寄存器读取数量，0表示禁用"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(8, min_value=0, max_value=125)

                    with builder.CHILD(key="input_start", name="Input Start", desc="输入寄存器起始地址"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(0, min_value=0, max_value=65535)

                    with builder.CHILD(key="input_count", name="Input Count", desc="输入寄存器读取数量，0表示禁用"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(8, min_value=0, max_value=125)

            builder.save(merge=True)

        cls.load_config()

    @classmethod
    def load_config(cls):
        config = script_param.loadConfig()
        cls.port = str(config.get("port", cls.port))
        cls.slave_id = int(config.get("slave_id", cls.slave_id))
        cls.baudrate = int(config.get("baudrate", cls.baudrate))
        cls.timeout = float(config.get("timeout", cls.timeout))
        cls.bytesize = int(config.get("bytesize", cls.bytesize))
        cls.parity = str(config.get("parity", cls.parity)).upper()
        cls.stopbits = int(config.get("stopbits", cls.stopbits))

        cls.sample_count = int(config.get("sample_count", cls.sample_count))
        cls.sample_interval = float(config.get("sample_interval", cls.sample_interval))
        cls.poll_count = int(config.get("poll_count", cls.poll_count))
        cls.poll_interval = float(config.get("poll_interval", cls.poll_interval))
        cls.holding_start = int(config.get("holding_start", cls.holding_start))
        cls.holding_count = int(config.get("holding_count", cls.holding_count))
        cls.input_start = int(config.get("input_start", cls.input_start))
        cls.input_count = int(config.get("input_count", cls.input_count))

        _trace_log(
            "config reload "
            f"port={cls.port} slave_id={cls.slave_id} baudrate={cls.baudrate} "
            f"timeout={cls.timeout:.3f}s bytesize={cls.bytesize} parity={cls.parity} "
            f"stopbits={cls.stopbits} sample_count={cls.sample_count} "
            f"sample_interval={cls.sample_interval:.3f}s poll_count={cls.poll_count} "
            f"poll_interval={cls.poll_interval:.3f}s holding=[{cls.holding_start}, {cls.holding_count}] "
            f"input=[{cls.input_start}, {cls.input_count}] ok=True",
            name=f"{LOG_MODULE}.cfg",
        )


ConfigParams.init()


def script_config_callback():
    """脚本配置参数修改回调"""
    _trace_log("script config callback reload=True", name=f"{LOG_MODULE}.cfg")
    ConfigParams.load_config()


class ScaleSimReceiver(ModuleBase):
    def __init__(self):
        super().__init__()
        self.status = ScriptStatus.NONE
        self.report_info: Dict[str, Any] = {}
        self.args: Dict[str, Any] = {}

    def init_args(self, args):
        self.args = args or {}
        self.status = ScriptStatus.RUNNING

    @staticmethod
    def _to_kg(value: Any, unit: Any) -> Optional[float]:
        if value is None or unit is None:
            return None

        unit_text = str(unit).strip().lower()
        numeric_value = float(value)
        if unit_text == "kg":
            return numeric_value
        if unit_text == "g":
            return numeric_value / 1000.0
        if unit_text == "t":
            return numeric_value * 1000.0
        return None

    @classmethod
    def _format_weight_text(cls, data: Dict[str, Any], label: str = "实际重量") -> str:
        if not isinstance(data, dict):
            return str(data)

        parts = []
        if data.get("raw") is not None:
            parts.append(f"原始值={data.get('raw')}")
        if data.get("decimalPoint") is not None:
            parts.append(f"小数位={data.get('decimalPoint')}")
        if data.get("unitCode") is not None:
            parts.append(f"单位码={data.get('unitCode')}")
        if data.get("unit") is not None:
            parts.append(f"单位={data.get('unit')}")

        value = data.get("value")
        unit = data.get("unit")
        weight_kg = cls._to_kg(value, unit)
        if weight_kg is not None:
            parts.append(f"{label}={weight_kg:.3f} kg")
        elif value is not None and unit is not None:
            parts.append(f"{label}={value} {unit}")

        return ", ".join(parts) if parts else str(data)

    @classmethod
    def _format_average_text(cls, value: Any, unit: Any) -> str:
        weight_kg = cls._to_kg(value, unit)
        if weight_kg is not None:
            return f"平均重量={weight_kg:.3f} kg"
        if value is not None and unit is not None:
            return f"平均重量={value} {unit}"
        return "平均重量=unknown"

    @staticmethod
    def _read_register_block(scale: CkyDgScale, kind: str, start: int, count: int) -> Dict[str, Any]:
        block = {
            "kind": kind,
            "start": int(start),
            "count": int(count),
            "enabled": int(count) > 0,
        }
        if int(count) <= 0:
            return block

        try:
            if kind == "holding":
                values = scale.modbus.read_holding_registers(int(start), int(count), scale.slave_id)
            else:
                values = scale.modbus.read_input_registers(int(start), int(count), scale.slave_id)
            block["values"] = list(values)
        except Exception as e:
            block["error"] = repr(e)
        return block

    @staticmethod
    def _format_register_block(block: Dict[str, Any]) -> str:
        kind = block.get("kind", "regs")
        if not block.get("enabled", False):
            return f"{kind}=disabled"
        if block.get("error"):
            return (
                f"{kind}[{block.get('start')}:{block.get('start', 0) + block.get('count', 0) - 1}] "
                f"error={block.get('error')}"
            )
        return (
            f"{kind}[{block.get('start')}:{block.get('start', 0) + block.get('count', 0) - 1}]="
            f"{block.get('values', [])}"
        )

    @classmethod
    def _log_poll(cls, poll_idx: int, poll: Dict[str, Any]):
        last = poll.get("last", {}) or {}
        avg_text = cls._format_average_text(poll.get("averageValue"), last.get("unit"))
        parts = [
            f"poll={poll_idx}",
            cls._format_weight_text(last),
            avg_text,
            cls._format_register_block(poll.get("holding", {})),
            cls._format_register_block(poll.get("input", {})),
        ]
        _trace_log(", ".join(parts), name=LOG_MODULE)

    def run_once(self) -> bool:
        all_ok = True
        polls = []

        scale = CkyDgScale(
            port=ConfigParams.port,
            baudrate=ConfigParams.baudrate,
            bytesize=ConfigParams.bytesize,
            parity=ConfigParams.parity,
            stopbits=ConfigParams.stopbits,
            timeout=ConfigParams.timeout,
            slave_id=ConfigParams.slave_id,
        )

        try:
            total_polls = max(1, int(ConfigParams.poll_count))
            for poll_idx in range(total_polls):
                samples = scale.read_weight_samples(
                    sample_count=max(1, int(ConfigParams.sample_count)),
                    sample_interval=max(0.0, float(ConfigParams.sample_interval)),
                )
                last = samples.get("last", {}) or {}
                holding = self._read_register_block(
                    scale,
                    "holding",
                    ConfigParams.holding_start,
                    ConfigParams.holding_count,
                )
                input_regs = self._read_register_block(
                    scale,
                    "input",
                    ConfigParams.input_start,
                    ConfigParams.input_count,
                )

                poll = {
                    "index": poll_idx,
                    "sampleCount": samples.get("sampleCount"),
                    "averageValue": samples.get("averageValue"),
                    "last": last,
                    "holding": holding,
                    "input": input_regs,
                }
                polls.append(poll)
                self._log_poll(poll_idx, poll)

                ok = bool(last) and samples.get("sampleCount") == max(1, int(ConfigParams.sample_count))
                if holding.get("enabled") and holding.get("error"):
                    ok = False
                if input_regs.get("enabled") and input_regs.get("error"):
                    ok = False
                if not ok:
                    all_ok = False

                if poll_idx < total_polls - 1 and ConfigParams.poll_interval > 0:
                    time.sleep(float(ConfigParams.poll_interval))
        finally:
            scale.close()

        self.report_info["polls"] = polls
        self.report_info["poll_count"] = len(polls)
        return all_ok

    def run(self):
        self.status = ScriptStatus.RUNNING
        self.report_info["taskId"] = Module.getTaskId()
        self.report_info["args"] = self.args
        self.report_info["taskTime"] = round(time.time() - start_time, 2)

        try:
            ok = self.run_once()
            self.status = ScriptStatus.FINISHED if ok else ScriptStatus.FAILED
        except Exception as e:
            self.report_info["error"] = str(e)
            _trace_log(f"run exception err={e!r}", name=f"{LOG_MODULE}.err")
            self.status = ScriptStatus.FAILED

    def suspend(self):
        if Module.getStatus() == ScriptStatus.RUNNING:
            self.status = ScriptStatus.SUSPENDED
        _trace_log("task suspend", name=f"{LOG_MODULE}.state")

    def resume(self):
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        _trace_log("task resume", name=f"{LOG_MODULE}.state")

    def cancel(self):
        self.status = ScriptStatus.FAILED
        _trace_log("task cancel", name=f"{LOG_MODULE}.state")


def main():
    ScriptParam.setConfigChangeCallBack(script_config_callback)
    Module.init()

    receiver = ScaleSimReceiver()

    while True:
        status = receiver.status
        Module.setStatus(status)
        receiver.report_info["status"] = status
        receiver.report_info["totalTime"] = round(time.time() - start_time, 2)
        Module.reportInfo(receiver.report_info)

        if status == ScriptStatus.NONE:
            args = Module.getTaskArgs()
            if args is not None:
                receiver.init_args(args)
        elif status == ScriptStatus.RUNNING:
            receiver.run()
        elif status == ScriptStatus.SUSPENDED:
            receiver.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            receiver.status = ScriptStatus.NONE

        time.sleep(0.1)


if __name__ == "__main__":
    main()
