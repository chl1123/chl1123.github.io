import json
import os
import struct
import sys
import time
from dataclasses import asdict

from syspy import Module, RobotParam, ScriptParam, ScriptStatus, Trace
from syspy.script_data import ScriptData
from syspy.comms.lora_comm import LoraFrame, LoraSerialTransport, LoraTransportError
from syspy.utils.param_server import ParamType

try:
    from .base import DoorProtocol, DoorProtocolResult, ProtocolRejected, ProtocolUnavailable
except (ImportError, ValueError):
    # RBK also starts protocol files directly to generate their input descriptor.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from third.door_protocol.base import (
        DoorProtocol,
        DoorProtocolResult,
        ProtocolRejected,
        ProtocolUnavailable,
    )


DEFAULT_SERIAL_PORT = "/dev/RS485_3"

script_param = ScriptParam(__file__)


def _add_debug_door_controls(builder):
    with builder.CHILD(key="action", name="Door action", desc="Open or close the door"):
        builder.TYPE(ParamType.COMBO_BOX)
        builder.REQUIRED(True)
        builder.DEFAULTVALUE("open")
        with builder.CHILDREN():
            with builder.CHILD(key="open", name="Open", desc="Request the door to open"):
                builder.TYPE(ParamType.ARRAY)
            with builder.CHILD(key="close", name="Close", desc="Release the door control"):
                builder.TYPE(ParamType.ARRAY)
    with builder.CHILD(key="sourceSide", name="Door side", desc="Side used for opening"):
        builder.TYPE(ParamType.COMBO_BOX)
        builder.REQUIRED(False)
        builder.DEFAULTVALUE("sideA")
        with builder.CHILDREN():
            with builder.CHILD(key="sideA", name="Side A", desc="Open from side A"):
                builder.TYPE(ParamType.ARRAY)
            with builder.CHILD(key="sideB", name="Side B", desc="Open from side B"):
                builder.TYPE(ParamType.ARRAY)


class ConfigParams:
    """越凡门控实例配置，随门设备绑定而不是随单次操作下发。"""

    builder = script_param.builderConfig()
    with builder.GROUPS():
        with builder.GROUP(key="protocol", name="Protocol", desc="Yuefan door instance configuration"):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                with builder.CHILD(key="port", name="Serial interface", desc="SerialInterface device binding"):
                    builder.TYPE(ParamType.BIND_TYPE)
                    builder.ADD_FIELD("bind_type", "device:SerialInterface")
                    builder.TAG("protocol:instance")
                    builder.REQUIRED(True)
                with builder.CHILD(key="address", name="LoRa address", desc="Gate module address"):
                    builder.TYPE(ParamType.INT)
                    builder.TAG("protocol:instance")
                    builder.REQUIRED(True)
                    builder.DEFAULTVALUE(0, min_value=0, max_value=0xFFFF)
                with builder.CHILD(key="channel", name="LoRa channel", desc="Gate module channel"):
                    builder.TYPE(ParamType.INT)
                    builder.TAG("protocol:instance")
                    builder.REQUIRED(True)
                    builder.DEFAULTVALUE(0, min_value=0, max_value=0xFF)
                with builder.CHILD(
                        key="openDelayTime", name="Open delay",
                        desc="Delay between acquiring control and opening the gate"):
                    builder.TYPE(ParamType.FLOAT)
                    builder.TAG("protocol:instance")
                    builder.DEFAULTVALUE(0.0, min_value=0.0, max_value=120.0)
                    builder.UNIT("s")
                for side, default_mode in (("sideA", "inside"), ("sideB", "outside")):
                    with builder.CHILD(
                        key=side, name=side,
                        desc="Open direction when entering from {}".format(side)):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            with builder.CHILD(
                                    key="idMask", name="Open direction",
                                    desc="Yuefan gate control mode"):
                                builder.TYPE(ParamType.COMBO_BOX)
                                builder.TAG("protocol:instance")
                                builder.DEFAULTVALUE(default_mode)
                                with builder.CHILDREN():
                                    with builder.CHILD(
                                            key="inside", name="Inside open",
                                            desc="Use idMask 1"):
                                        builder.TYPE(ParamType.ARRAY)
                                    with builder.CHILD(
                                            key="outside", name="Outside open",
                                            desc="Use idMask 2"):
                                        builder.TYPE(ParamType.ARRAY)
    builder.save(merge=True)


class InputParams:
    """越凡协议调试操作输入。实例参数由 ConfigParams 管理。"""

    builder = script_param.builderInput()
    with builder.GROUPS():
        with builder.GROUP(key="operation", name="Operation", desc="Door protocol debug operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            with builder.CHILDREN():
                with builder.CHILD(
                        key="queryStatus", name="Query door status",
                        desc="Query one door and publish the result to ScriptData"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILD(
                            key="openClose", name="Open or close door",
                            desc="Send an open or release command to one door"):
                        builder.TYPE(ParamType.ARRAY)
                        with builder.CHILDREN():
                            _add_debug_door_controls(builder)
    builder.save()


def _lookup(data, key, default=None):
    if not isinstance(data, dict):
        return default
    if key in data:
        return data[key]
    value = data
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def _protocol_args(config):
    config = dict(config or {})
    site = config.get("protocolSite") or {}
    if not site and isinstance(config.get("jsonObject"), dict):
        site = config
    data = site.get("jsonObject", site) if isinstance(site, dict) else {}
    if not isinstance(data, dict):
        data = {}
    flat = config

    def value(*keys, default=None):
        for key in keys:
            candidate = _lookup(flat, key, None)
            if candidate not in (None, ""):
                return candidate
            candidate = _lookup(data, key, None)
            if candidate not in (None, ""):
                return candidate
        return default

    protocol_name = value("communicationProtocol", default="yuefan")
    if protocol_name and str(protocol_name).lower() != "yuefan":
        raise ValueError("unsupported door communication protocol: {}".format(protocol_name))
    script_name = value(
        "communicationProtocol.yuefan.name",
        "communicationProtocol.yuefan.script.name",
        default="",
    )
    if script_name and not str(script_name).replace("\\", "/").endswith("/yuefan.py"):
        raise ValueError("unsupported Yuefan door protocol script: {}".format(script_name))
    prefix = "communicationProtocol.yuefan.args."
    legacy_prefix = "communicationProtocol.yuefan.script.args."
    address = value("address", prefix + "address", legacy_prefix + "address", "protocol.address")
    channel = value("channel", prefix + "channel", legacy_prefix + "channel", "protocol.channel")
    serial_interface = value(
        "port", prefix + "port", legacy_prefix + "port", "protocol.port",
        default=DEFAULT_SERIAL_PORT,
    )
    if address is None or channel is None:
        raise ValueError("Yuefan door protocol requires address and channel")
    return serial_interface, int(address), int(channel)


def _resolve_port(serial_interface):
    port = str(serial_interface or "").strip()
    if not port or port.startswith("/"):
        return port or DEFAULT_SERIAL_PORT

    def device_path(value):
        value = str(value or "").strip()
        return value if value.startswith("/") else "/dev/{}".format(value)

    try:
        resolved = str(RobotParam.getConfig(
            "SerialInterface", "{}.portName".format(port)
        ) or "").strip()
    except Exception:
        resolved = ""
    if resolved:
        return device_path(resolved)
    for field in ("portName", "basic.portName", "devName", "basic.devName"):
        try:
            resolved = str(RobotParam.getDevice(port, field) or "").strip()
        except Exception:
            resolved = ""
        if resolved:
            return device_path(resolved)
    raise ValueError("Yuefan door SerialInterface {} has no portName".format(port))


def create_protocol(config, port=None, timeout=2.0, retries=3):
    """Create a Yuefan door protocol from a map device configuration."""
    transport = None
    if hasattr(config, "transact") and isinstance(port, dict):
        # Compatibility form: create_protocol(transport, config).
        transport, config, port = config, port, DEFAULT_SERIAL_PORT
    serial_interface, address, channel = _protocol_args(config)
    port = _resolve_port(port or serial_interface)
    if transport is None:
        transport = LoraSerialTransport(port=port, timeout=timeout, retries=retries)
    return YuefanDoorProtocol(transport, address, channel)


class YuefanDoorProtocol(DoorProtocol):
    PROTOCOL_VERSION = 0x03
    ROBOT_ADDRESS = 0x96
    MODULE_ADDRESS = 0x84
    MESSAGE_TYPE = 0x05
    CMD_QUERY = 0x0940
    CMD_CONTROL = 0x0942
    CMD_END = 0x0945

    def __init__(self, transport: LoraSerialTransport, address: int, channel: int):
        if not 0 <= address <= 0xFFFF:
            raise ValueError("address must be in range 0..65535")
        if not 0 <= channel <= 0xFF:
            raise ValueError("channel must be in range 0..255")
        self.transport = transport
        self.address = int(address)
        self.channel = int(channel)

    def _common_data(self, instance_args=None) -> bytes:
        address, channel = self._resolve_instance(instance_args)
        return struct.pack("<BHBHB", self.PROTOCOL_VERSION, address, channel, 0, 0)

    @staticmethod
    def _lookup(instance_args, suffix, default=None):
        instance_args = instance_args or {}
        if suffix in instance_args:
            return instance_args[suffix]
        value = instance_args
        for part in suffix.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if value is not None:
            return value
        for key, value in instance_args.items():
            if str(key).endswith(suffix):
                return value
        return default

    def _resolve_instance(self, instance_args):
        address = self._lookup(instance_args, "address", self.address)
        channel = self._lookup(instance_args, "channel", self.channel)
        if not 0 <= int(address) <= 0xFFFF:
            raise ValueError("address must be in range 0..65535")
        if not 0 <= int(channel) <= 0xFF:
            raise ValueError("channel must be in range 0..255")
        return int(address), int(channel)

    def _resolve_open_mode(self, source_side, instance_args):
        # Keep the old integer mode as a compatibility path for existing fakes.
        if isinstance(source_side, int):
            open_mode = source_side
        elif source_side in ("sideA", "sideB"):
            suffix = "sideA.idMask" if source_side == "sideA" else "sideB.idMask"
            default = 1 if source_side == "sideA" else 2
            open_mode = self._lookup(instance_args, suffix, default)
        else:
            raise ValueError("source_side must be sideA or sideB")
        open_mode = {
            "inside": 1,
            "outside": 2,
            "inner": 1,
            "outer": 2,
        }.get(str(open_mode).strip().lower(), open_mode)
        if int(open_mode) not in (0, 1, 2):
            raise ValueError("source side mask must be 0, 1, or 2")
        return int(open_mode)

    def _request(self, command: int, data: bytes, control_state: str,
                 instance_args=None) -> DoorProtocolResult:
        address, channel = self._resolve_instance(instance_args)
        request = LoraFrame(
            command=command,
            destination=self.MODULE_ADDRESS,
            source=self.ROBOT_ADDRESS,
            message_type=self.MESSAGE_TYPE,
            message_attr=0,
            data=data,
        )

        def matches(frame: LoraFrame) -> bool:
            return (
                frame.command == command
                and frame.destination == self.ROBOT_ADDRESS
                and frame.source == self.MODULE_ADDRESS
                and len(frame.data) >= 4
                and struct.unpack("<H", frame.data[1:3])[0] == address
                and frame.data[3] == channel
            )

        try:
            response = self.transport.transact(request, matches)
        except LoraTransportError as error:
            raise ProtocolUnavailable(str(error)) from error
        if response.message_attr:
            raise ProtocolRejected(
                f"Yuefan door rejected command 0x{command:04X}: error=0x{response.message_attr:02X}"
            )
        if len(response.data) < 9:
            raise ProtocolUnavailable("Yuefan door response data is too short")
        door_state = response.data[7]
        return DoorProtocolResult(
            accepted=True,
            control_state=control_state,
            passage_state="OPEN" if door_state == 1 else "NOT_OPEN",
        )

    def query_status(self) -> DoorProtocolResult:
        return self._request(self.CMD_QUERY, self._common_data(), "UNKNOWN")

    def acquire_control(self, instance_args=None, active_time=30) -> DoorProtocolResult:
        if not 2 <= int(active_time) <= 0xFF:
            raise ValueError("active_time must be in range 2..255")
        data = self._common_data(instance_args)
        data += struct.pack("<BBB", 0, 0, int(active_time))
        return self._request(
            self.CMD_CONTROL, data, "OWNED_BY_SELF", instance_args
        )

    def request_open(self, source_side=None, instance_args=None, active_time=None,
                    **legacy_kwargs) -> DoorProtocolResult:
        if source_side is None and "open_mode" in legacy_kwargs:
            source_side = legacy_kwargs["open_mode"]
        if active_time is None:
            active_time = instance_args
            instance_args = {}
        open_mode = self._resolve_open_mode(source_side, instance_args)
        if not 2 <= active_time <= 0xFF:
            raise ValueError("active_time must be in range 2..255")
        address, channel = self._resolve_instance(instance_args)
        data = struct.pack("<BHBHB", self.PROTOCOL_VERSION, address, channel, 0, 0)
        data += struct.pack("<BBB", open_mode, 0, active_time)
        return self._request(self.CMD_CONTROL, data, "OWNED_BY_SELF", instance_args)

    def keep_alive(self, source_side=None, instance_args=None, active_time=None,
                   **legacy_kwargs) -> DoorProtocolResult:
        if source_side is None and "open_mode" in legacy_kwargs:
            source_side = legacy_kwargs["open_mode"]
        return self.request_open(source_side, instance_args, active_time)

    def release(self, instance_args=None) -> DoorProtocolResult:
        return self._request(
            self.CMD_END, self._common_data(instance_args), "FREE", instance_args
        )


script_param.addAction(
    action_name="Query door status",
    policy={},
    args={"operation": "queryStatus"},
    config={},
)
script_param.addAction(
    action_name="Open or close door",
    policy={},
    args={"operation": "openClose", "operation.openClose.action": "open",
          "operation.openClose.sourceSide": "sideA"},
    config={},
)
script_param.saveAction()


def _json_object(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    if not isinstance(value, dict):
        return {}
    nested = value.get("jsonObject")
    return nested if isinstance(nested, dict) else value


def _instance_config(args):
    """Find the saved protocol instance; topology is intentionally ignored."""
    args = args if isinstance(args, dict) else {}
    candidates = [
        args.get("protocol.instance"),
        args.get("protocolInstance"),
        args.get("protocolSite"),
        args.get("config"),
    ]
    try:
        candidates.append(Module.getTaskConfig())
    except Exception:
        pass
    for candidate in candidates:
        data = _json_object(candidate)
        if data and (
                "communicationProtocol" in data
                or "address" in data
                or "communicationProtocol.yuefan.args.address" in data):
            return data
    return args


def _with_instance_fields(args):
    result = dict(args or {})
    data = _instance_config(result)
    for field in ("port", "address", "channel", "openDelayTime"):
        value = _lookup(data, field)
        if value in (None, ""):
            value = _lookup(data, "communicationProtocol.yuefan.args." + field)
        if value not in (None, ""):
            result.setdefault(field, value)
    return result


def _operation_value(args, key, default=None):
    value = _lookup(args, "operation.openClose." + key)
    if value is None and isinstance(args, dict):
        value = args.get(key, default)
    return default if value in (None, "") else value


def _publish_result(result, operation, action=None, source_side=None):
    payload = asdict(result)
    payload.update({
        "operation": operation,
        "action": action or "query",
        "sourceSide": source_side or "",
    })
    ScriptData.set("doorState", payload)


def _run_debug_operation(raw_args):
    args = script_param.loadInput(_with_instance_fields(raw_args))
    operation = str(args.get("operation", "")).strip()
    if operation not in ("queryStatus", "openClose"):
        raise ValueError("unsupported door debug operation: {}".format(operation))
    instance = _instance_config(args)
    protocol = create_protocol(instance)
    if operation == "queryStatus":
        result = protocol.query_status()
        _publish_result(result, operation)
        return
    action = str(_operation_value(args, "action", "open")).strip().lower()
    source_side = str(_operation_value(args, "sourceSide", "sideA")).strip()
    if action not in ("open", "close"):
        raise ValueError("action must be open or close")
    if source_side not in ("sideA", "sideB"):
        raise ValueError("sourceSide must be sideA or sideB")
    instance_args = instance.get("jsonObject", instance) if isinstance(instance, dict) else {}
    if action == "open":
        result = protocol.request_open(source_side, instance_args, 30)
    else:
        result = protocol.release(instance_args)
    _publish_result(result, operation, action, source_side)


def main():
    """Run the protocol-only debug task; no map or topology is loaded."""
    Module.init()
    while True:
        try:
            status = Module.getStatus()
            if status in (ScriptStatus.NONE, ScriptStatus.RUNNING):
                raw_args = Module.getTaskArgs()
                if raw_args:
                    try:
                        _run_debug_operation(raw_args)
                        Module.setStatus(ScriptStatus.FINISHED)
                    except Exception as error:
                        Trace.log({"event": "doorProtocolDebugFailed", "error": str(error)},
                                  name="door_protocol.err")
                        Module.setStatus(ScriptStatus.FAILED)
            elif status in (ScriptStatus.FINISHED, ScriptStatus.FAILED):
                Module.setStatus(ScriptStatus.NONE)
        except Exception as error:
            Trace.log({"event": "doorProtocolDebugLifecycleFailed", "error": str(error)},
                      name="door_protocol.err")
            Module.setStatus(ScriptStatus.FAILED)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
