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
    from .base import ElevatorProtocol, ElevatorProtocolResult, ProtocolRejected, ProtocolUnavailable
except (ImportError, ValueError):
    # RBK also starts protocol files directly to generate their input descriptor.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from third.elevator_protocol.base import (
        ElevatorProtocol,
        ElevatorProtocolResult,
        ProtocolRejected,
        ProtocolUnavailable,
    )


DEFAULT_SERIAL_PORT = "/dev/RS485_3"

script_param = ScriptParam(__file__)


def _add_debug_floor_fields(builder, required):
    """Add only protocol-level inputs to a debug operation."""
    with builder.CHILD(key="floorNum", name="Floor number", desc="Yuefan floor number"):
        builder.TYPE(ParamType.INT)
        builder.TAG("protocol:floor")
        builder.REQUIRED(required)
        builder.DEFAULTVALUE(1, min_value=-128, max_value=127)
    with builder.CHILD(
            key="floorDirection", name="Floor door direction",
            desc="0: both sides, 1: left side, 2: right side"):
        builder.TYPE(ParamType.INT)
        builder.TAG("protocol:entry")
        builder.REQUIRED(required)
        builder.DEFAULTVALUE(0, min_value=0, max_value=2)


class ConfigParams:
    """越凡梯控实例配置，随电梯设备绑定而不是随单次操作下发。"""

    builder = script_param.builderConfig()
    with builder.GROUPS():
        with builder.GROUP(key="protocol", name="Protocol", desc="Yuefan elevator instance configuration"):
            builder.TYPE(ParamType.ARRAY)
            with builder.CHILDREN():
                with builder.CHILD(key="port", name="Serial interface", desc="SerialInterface device binding"):
                    builder.TYPE(ParamType.BIND_TYPE)
                    builder.ADD_FIELD("bind_type", "device:SerialInterface")
                    builder.TAG("protocol:instance")
                    builder.REQUIRED(True)
                with builder.CHILD(key="address", name="LoRa address", desc="Elevator module address"):
                    builder.TYPE(ParamType.INT)
                    builder.TAG("protocol:instance")
                    builder.REQUIRED(True)
                    builder.DEFAULTVALUE(0, min_value=0, max_value=0xFFFF)
                with builder.CHILD(key="channel", name="LoRa channel", desc="Elevator module channel"):
                    builder.TYPE(ParamType.INT)
                    builder.TAG("protocol:instance")
                    builder.REQUIRED(True)
                    builder.DEFAULTVALUE(0, min_value=0, max_value=0xFF)
                with builder.CHILD(key="timeout", name="Response timeout", desc="LoRa response timeout"):
                    builder.TYPE(ParamType.FLOAT)
                    builder.TAG("protocol:instance")
                    builder.DEFAULTVALUE(2.0, min_value=0.1, max_value=30.0)
                    builder.UNIT("s")
                with builder.CHILD(key="retries", name="Request retries", desc="LoRa request retry count"):
                    builder.TYPE(ParamType.INT)
                    builder.TAG("protocol:instance")
                    builder.DEFAULTVALUE(3, min_value=1, max_value=10)
    builder.save(merge=True)


class InputParams:
    """越凡协议调试操作输入。实例参数由 ConfigParams 管理。"""

    builder = script_param.builderInput()
    with builder.GROUPS():
        with builder.GROUP(key="operation", name="Operation", desc="Elevator protocol debug operation"):
            builder.TYPE(ParamType.COMBO_BOX)
            builder.REQUIRED(True)
            with builder.CHILDREN():
                with builder.CHILD(
                        key="queryStatus", name="Query current floor",
                        desc="Query the elevator status and publish it to ScriptData"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        _add_debug_floor_fields(builder, required=False)
                with builder.CHILD(
                        key="call", name="Call elevator",
                        desc="Send a floor-call request to the elevator"):
                    builder.TYPE(ParamType.ARRAY)
                    with builder.CHILDREN():
                        _add_debug_floor_fields(builder, required=True)
    builder.save()


def _lookup(data, key, default=None):
    if not isinstance(data, dict):
        return default
    if key in data:
        return data[key]
    parts = key.split(".")
    value = data
    index = 0
    while index < len(parts):
        if not isinstance(value, dict):
            return default
        match = None
        for end in range(len(parts), index, -1):
            candidate = ".".join(parts[index:end])
            if candidate in value:
                match = end
                break
        if match is None:
            return default
        value = value[".".join(parts[index:match])]
        index = match
    return value


def _protocol_args(config):
    config = dict(config or {})
    site = config.get("protocolSite") or {}
    if not site and isinstance(config.get("jsonObject"), dict):
        site = config
    if not site:
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
        raise ValueError("unsupported elevator communication protocol: {}".format(protocol_name))
    script_name = value(
        "communicationProtocol.yuefan.name",
        "communicationProtocol.yuefan.script.name",
        default="",
    )
    if script_name and not str(script_name).replace("\\", "/").endswith("/yuefan.py"):
        raise ValueError("unsupported Yuefan elevator protocol script: {}".format(script_name))
    config_prefix = "communicationProtocol.yuefan.config.lora."
    prefix = "communicationProtocol.yuefan.args."
    legacy_prefix = "communicationProtocol.yuefan.script.args."
    address = value(
        "address", config_prefix + "address", prefix + "address",
        legacy_prefix + "address",
    )
    channel = value(
        "channel", config_prefix + "channel", prefix + "channel",
        legacy_prefix + "channel",
    )
    serial_interface = value(
        "port", config_prefix + "port", prefix + "port", legacy_prefix + "port",
        default=DEFAULT_SERIAL_PORT,
    )
    timeout = float(value(
        "timeout", config_prefix + "timeout", prefix + "timeout",
        legacy_prefix + "timeout",
        default=2.0,
    ))
    retries = int(value(
        "retries", config_prefix + "retries", prefix + "retries",
        legacy_prefix + "retries",
        default=3,
    ))
    if address is None or channel is None:
        raise ValueError("Yuefan elevator protocol requires address and channel")
    if not 0.1 <= timeout <= 30.0:
        raise ValueError("Yuefan elevator timeout must be in range 0.1..30")
    if not 1 <= retries <= 10:
        raise ValueError("Yuefan elevator retries must be in range 1..10")
    return serial_interface, int(address), int(channel), timeout, retries


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
    raise ValueError("Yuefan elevator SerialInterface {} has no portName".format(port))


def create_protocol(config, port=None, timeout=None, retries=None):
    """Create a Yuefan elevator protocol from a map device configuration."""
    transport = None
    if hasattr(config, "transact") and isinstance(port, dict):
        # Compatibility form: create_protocol(transport, config).
        transport, config, port = config, port, DEFAULT_SERIAL_PORT
    serial_interface, address, channel, configured_timeout, configured_retries = (
        _protocol_args(config)
    )
    port = _resolve_port(port or serial_interface)
    timeout = configured_timeout if timeout is None else float(timeout)
    retries = configured_retries if retries is None else int(retries)
    if transport is None:
        transport = LoraSerialTransport(port=port, timeout=timeout, retries=retries)
    return YuefanElevatorProtocol(transport, address, channel)


class YuefanElevatorProtocol(ElevatorProtocol):
    PROTOCOL_VERSION = 0x03
    ROBOT_ADDRESS = 0x96
    MODULE_ADDRESS = 0x12
    MESSAGE_TYPE = 0x05
    CMD_QUERY = 0x0940
    CMD_CONTROL = 0x0942
    CMD_END = 0x0945
    # Yuefan documents doorState as deprecated. moveState=0x05 means
    # "car arrived; it is safe to enter".
    MOVE_STATE_ARRIVED = 5

    def __init__(self, transport: LoraSerialTransport, address: int, channel: int):
        if not 0 <= address <= 0xFFFF:
            raise ValueError("address must be in range 0..65535")
        if not 0 <= channel <= 0xFF:
            raise ValueError("channel must be in range 0..255")
        self.transport = transport
        self.address = int(address)
        self.channel = int(channel)

    def _data(self, floor: int, active_time: int) -> bytes:
        if not -128 <= floor <= 127:
            raise ValueError("floor must be in range -128..127")
        if not 0 <= active_time <= 0xFF:
            raise ValueError("active_time must be in range 0..255")
        return struct.pack(
            "<BHBHBBbB",
            self.PROTOCOL_VERSION,
            self.address,
            self.channel,
            0,
            0,
            0,
            floor,
            active_time,
        )

    def _request(self, command: int, data: bytes, control_state: str) -> ElevatorProtocolResult:
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
                and struct.unpack("<H", frame.data[1:3])[0] == self.address
                and frame.data[3] == self.channel
            )

        try:
            response = self.transport.transact(request, matches)
        except LoraTransportError as error:
            raise ProtocolUnavailable(str(error)) from error
        if response.message_attr:
            raise ProtocolRejected(
                f"Yuefan elevator rejected command 0x{command:04X}: error=0x{response.message_attr:02X}"
            )
        if len(response.data) < 10:
            raise ProtocolUnavailable("Yuefan elevator response data is too short")
        move_door_state = response.data[9]
        return ElevatorProtocolResult(
            accepted=True,
            control_state=control_state,
            floor=struct.unpack("<b", response.data[8:9])[0],
            move_state=(move_door_state >> 4) & 0x0F,
            door_state=move_door_state & 0x0F,
            task_step=response.data[10] if len(response.data) >= 15 else None,
        )

    def query_status(self) -> ElevatorProtocolResult:
        return self._request(self.CMD_QUERY, self._data(0, 0), "UNKNOWN")

    def call(self, floor: int, active_time: int) -> ElevatorProtocolResult:
        if active_time < 2:
            raise ValueError("active_time must be at least 2 seconds")
        return self._request(
            self.CMD_CONTROL,
            self._data(floor, active_time),
            "OWNED_BY_SELF",
        )

    def keep_alive(self, floor: int, active_time: int) -> ElevatorProtocolResult:
        return self.call(floor, active_time)

    def release(self, active_time: int) -> ElevatorProtocolResult:
        return self._request(self.CMD_END, self._data(0, active_time), "FREE")

    def is_target_ready(self, result: ElevatorProtocolResult, target_floor: int) -> bool:
        return (
            result.floor == target_floor
            and result.move_state == self.MOVE_STATE_ARRIVED
        )


script_param.addAction(
    action_name="Query elevator floor",
    policy={},
    args={"operation": "queryStatus", "operation.queryStatus.floorNum": 1,
          "operation.queryStatus.floorDirection": 0},
    config={},
)
script_param.addAction(
    action_name="Call elevator",
    policy={},
    args={"operation": "call", "operation.call.floorNum": 1,
          "operation.call.floorDirection": 0},
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
    """Find the saved protocol instance without interpreting map topology."""
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
                or "communicationProtocol.yuefan.args.address" in data
                or "communicationProtocol.yuefan.config.lora.address" in data
                or _lookup(data, "communicationProtocol.yuefan.config.lora.address") is not None):
            return data
    return args


def _with_instance_fields(args):
    """Make saved dotted instance JSON usable by the regular input validator."""
    result = dict(args or {})
    data = _instance_config(result)
    for field in ("port", "address", "channel", "timeout", "retries"):
        value = _lookup(data, field)
        if value in (None, ""):
            value = _lookup(data, "communicationProtocol.yuefan.config.lora." + field)
        if value in (None, ""):
            value = _lookup(data, "communicationProtocol.yuefan.args." + field)
        if value not in (None, ""):
            result.setdefault(field, value)
    return result


def _operation_value(args, operation, key, default=None):
    value = _lookup(args, "operation.{}.{}".format(operation, key))
    if value is None:
        value = args.get(key, default) if isinstance(args, dict) else default
    return default if value in (None, "") else value


def _publish_result(result, operation, requested_floor=None, floor_direction=None):
    payload = asdict(result)
    payload.update({
        "operation": operation,
        "floorNum": result.floor if requested_floor is None else int(requested_floor),
        "floorDirection": 0 if floor_direction is None else int(floor_direction),
        "floor": int(result.floor),
        "currentFloor": int(result.floor),
    })
    ScriptData.set("elevatorState", payload)


def _run_debug_operation(raw_args):
    args = script_param.loadInput(_with_instance_fields(raw_args))
    operation = str(args.get("operation", "")).strip()
    if operation not in ("queryStatus", "call"):
        raise ValueError("unsupported elevator debug operation: {}".format(operation))
    protocol = create_protocol(_instance_config(args))
    floor = int(_operation_value(args, operation, "floorNum", 1))
    direction = int(_operation_value(args, operation, "floorDirection", 0))
    if not 0 <= direction <= 2:
        raise ValueError("floorDirection must be in range 0..2")
    result = protocol.query_status() if operation == "queryStatus" else protocol.call(floor, 30)
    _publish_result(result, operation, floor, direction)


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
                        Trace.log({"event": "elevatorProtocolDebugFailed", "error": str(error)},
                                  name="elevator_protocol.err")
                        Module.setStatus(ScriptStatus.FAILED)
            elif status in (ScriptStatus.FINISHED, ScriptStatus.FAILED):
                Module.setStatus(ScriptStatus.NONE)
        except Exception as error:
            Trace.log({"event": "elevatorProtocolDebugLifecycleFailed", "error": str(error)},
                      name="elevator_protocol.err")
            Module.setStatus(ScriptStatus.FAILED)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
