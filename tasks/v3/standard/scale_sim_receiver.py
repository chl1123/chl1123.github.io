# -*- coding: utf-8 -*-
# @Date : 2026/04/22
# @Project: CKY-DG 称重设备模拟接收端测试（标准任务脚本）

import time

start_time = time.time()

from syspy import Module, ModuleBase, ScriptStatus, ScriptParam, Trace
from syspy.utils.param_server import ParamType

from standard.weighing_scale import CkyDgScale


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

            with builder.GROUP(key="test", name="Test", desc="测试行为配置"):
                builder.TYPE(ParamType.ARRAY)
                with builder.CHILDREN():
                    with builder.CHILD(key="sample_count", name="Sample Count", desc="采样次数"):
                        builder.TYPE(ParamType.INT)
                        builder.DEFAULTVALUE(5, min_value=1, max_value=200)

                    with builder.CHILD(key="sample_interval", name="Sample Interval", desc="采样间隔（秒）"):
                        builder.TYPE(ParamType.FLOAT)
                        builder.DEFAULTVALUE(0.02, min_value=0.0, max_value=2.0)
                        builder.SINGLESTEP(0.01)
                        builder.UNIT("s")

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

        _trace_log(
            "config reload "
            f"port={cls.port} slave_id={cls.slave_id} baudrate={cls.baudrate} "
            f"timeout={cls.timeout:.3f}s bytesize={cls.bytesize} parity={cls.parity} "
            f"stopbits={cls.stopbits} sample_count={cls.sample_count} "
            f"sample_interval={cls.sample_interval:.3f}s ok=True",
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
        self.report_info = {}
        self.args = {}

    def init_args(self, args):
        self.args = args
        self.status = ScriptStatus.RUNNING

    @staticmethod
    def _to_kg(value, unit):
        if value is None or unit is None:
            return None

        unit_text = str(unit).strip().lower()
        if unit_text == "kg":
            return float(value)
        if unit_text == "g":
            return float(value) / 1000.0
        if unit_text == "t":
            return float(value) * 1000.0
        return None

    @classmethod
    def _format_weight_text(cls, data: dict, label: str = "实际重量") -> str:
        if not isinstance(data, dict):
            return str(data)

        parts = []
        raw = data.get("raw")
        if raw is not None:
            parts.append(f"原始值={raw}")

        value = data.get("value")
        unit = data.get("unit")
        weight_kg = cls._to_kg(value, unit)
        if weight_kg is not None:
            parts.append(f"{label}={weight_kg:.3f} kg")
        elif value is not None and unit is not None:
            parts.append(f"{label}={value} {unit}")

        return ", ".join(parts) if parts else str(data)

    @classmethod
    def _format_check_detail(cls, name: str, detail: dict) -> str:
        if name == "read_weight_once":
            return cls._format_weight_text(detail)

        if name == "read_weight_samples":
            parts = [f"采样次数={detail.get('sampleCount')}"]
            average_value = detail.get("averageValue")
            unit = detail.get("unit")
            average_kg = cls._to_kg(average_value, unit)
            if average_kg is not None:
                parts.append(f"平均重量={average_kg:.3f} kg")
            elif average_value is not None and unit is not None:
                parts.append(f"平均重量={average_value} {unit}")
            return ", ".join(parts)

        if name == "tare":
            return f"去皮后{cls._format_weight_text(detail, label='当前重量')}"

        if name == "clear_tare":
            baseline_raw = detail.get("baselineRaw")
            current = detail.get("current", {})
            formatted = cls._format_weight_text(current, label="当前重量")
            return f"清皮前原始值={baseline_raw}, 清皮后{formatted}"

        if name == "zero":
            return f"清零后{cls._format_weight_text(detail, label='当前重量')}"

        return str(detail)

    @staticmethod
    def _check(name: str, ok: bool, detail: dict, report: dict):
        report[name] = {"ok": bool(ok), "detail": detail}
        _trace_log(
            f"check={name}"
            f"{ScaleSimReceiver._format_check_detail(name, detail)}",
            name=f"{LOG_MODULE}",
        )

    def run_once(self) -> bool:
        all_ok = True
        checks = {}

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
            baseline = scale.read_weight_once()
            base_raw = baseline.get("raw")
            ok = ("value" in baseline) and ("unit" in baseline) and (base_raw is not None)
            self._check("read_weight_once", ok, baseline, checks)
            if not ok:
                all_ok = False

            samples = scale.read_weight_samples(
                sample_count=ConfigParams.sample_count,
                sample_interval=ConfigParams.sample_interval,
            )
            ok = samples.get("sampleCount") == ConfigParams.sample_count
            self._check(
                "read_weight_samples",
                ok,
                {
                    "sampleCount": samples.get("sampleCount"),
                    "averageValue": samples.get("averageValue"),
                    "unit": samples.get("last", {}).get("unit"),
                },
                checks,
            )
            if not ok:
                all_ok = False

            scale.tare()
            tare_read = scale.read_weight_once()
            ok = tare_read.get("raw") == 0
            self._check("tare", ok, tare_read, checks)
            if not ok:
                all_ok = False

            scale.clear_tare()
            clear_read = scale.read_weight_once()
            ok = clear_read.get("raw") == base_raw
            self._check(
                "clear_tare",
                ok,
                {"baselineRaw": base_raw, "current": clear_read},
                checks,
            )
            if not ok:
                all_ok = False

            scale.zero()
            zero_read = scale.read_weight_once()
            ok = zero_read.get("raw") == 0
            self._check("zero", ok, zero_read, checks)
            if not ok:
                all_ok = False

        finally:
            scale.close()

        self.report_info["checks"] = checks
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
