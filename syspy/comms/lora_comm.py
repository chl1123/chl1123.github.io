import json
import logging
import os
import queue
import struct
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional

import serial

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoraFrame:
    command: int
    destination: int
    source: int
    message_type: int
    message_attr: int
    data: bytes


class LoraFrameCodec:
    HEADER = b"\xAA\xA1"
    FIXED_SIZE = 11

    @classmethod
    def encode(cls, frame: LoraFrame) -> bytes:
        if len(frame.data) > 0xFF:
            raise ValueError("LoRa frame data exceeds 255 bytes")
        packet = cls.HEADER + struct.pack(
            "<HBBBBB",
            frame.command,
            frame.destination,
            frame.source,
            frame.message_type,
            frame.message_attr,
            len(frame.data),
        ) + frame.data
        return packet + struct.pack("<H", sum(packet) & 0xFFFF)

    @classmethod
    def decode(cls, raw: bytes) -> LoraFrame:
        if len(raw) < cls.FIXED_SIZE or raw[:2] != cls.HEADER:
            raise ValueError("invalid LoRa frame header or length")
        data_length = raw[8]
        if len(raw) != cls.FIXED_SIZE + data_length:
            raise ValueError("invalid LoRa frame length")
        expected = struct.unpack("<H", raw[-2:])[0]
        actual = sum(raw[:-2]) & 0xFFFF
        if expected != actual:
            raise ValueError("LoRa frame checksum mismatch")
        return LoraFrame(
            command=struct.unpack("<H", raw[2:4])[0],
            destination=raw[4],
            source=raw[5],
            message_type=raw[6],
            message_attr=raw[7],
            data=raw[9:-2],
        )


class LoraFrameStream:
    def __init__(self):
        self._buffer = bytearray()

    def clear(self) -> None:
        self._buffer.clear()

    def feed(self, chunk: bytes) -> List[bytes]:
        self._buffer.extend(chunk)
        frames = []
        while True:
            header_index = self._buffer.find(LoraFrameCodec.HEADER)
            if header_index < 0:
                if self._buffer.endswith(LoraFrameCodec.HEADER[:1]):
                    self._buffer[:] = LoraFrameCodec.HEADER[:1]
                else:
                    self._buffer.clear()
                return frames
            if header_index:
                del self._buffer[:header_index]
            if len(self._buffer) < 9:
                return frames
            frame_length = LoraFrameCodec.FIXED_SIZE + self._buffer[8]
            if len(self._buffer) < frame_length:
                return frames
            frames.append(bytes(self._buffer[:frame_length]))
            del self._buffer[:frame_length]


class LoraTransportError(RuntimeError):
    pass


class LoraResponseTimeout(LoraTransportError):
    pass


class LoraOperation(str, Enum):
    """Behav LoRa 事务的调度类型。"""

    QUERY = "QUERY"
    CONTROL = "CONTROL"
    KEEP_ALIVE = "KEEP_ALIVE"
    RELEASE = "RELEASE"
    ACK = "ACK"


@dataclass(frozen=True)
class LoraReceivedFrame:
    """Behav RX topic 发布的一帧 LoRa 主动上报数据。

    字段：
        frame: 解码后的 LoRa 帧。
        device: 发布该事件的逻辑 LoRa 设备名。
        sequence: Behav 为当前设备世代分配的单调递增事件序号。
        device_generation: LoRa 设备配置世代；串口绑定重配后会变化。
        received_monotonic_ms: Behav 收到帧时的单调时钟毫秒值，仅用于诊断，
            不能直接与墙上时钟时间戳比较。
    """

    frame: LoraFrame
    device: Optional[str] = None
    sequence: Optional[int] = None
    device_generation: Optional[int] = None
    received_monotonic_ms: Optional[int] = None


@dataclass(frozen=True)
class LoraMatchSpec:
    """直连和 RPC transport 共用的可序列化响应匹配条件。

    字段：
        command: 期望的 LoRa 命令字；为 ``None`` 时不校验。
        destination: 期望的帧目的模块地址。
        source: 期望的帧源模块地址。
        address: 厂家协议存放在 ``data[1:3]`` 中的目标地址。
        channel: 厂家协议存放在 ``data[3]`` 中的目标信道；必须与
            ``address`` 同时设置。
        data_equals: 帧 data 区域需要匹配的前缀。
        data_mask: 应用于 ``data_equals`` 的可选字节掩码；为空时每个字节
            均按 ``0xFF`` 比较。
        operation: 事务调度类型，必须使用 :class:`LoraOperation`。
        operation_key: 稳定的逻辑操作键，Behav 可用它合并同类排队请求，
            避免状态轮询积压。
    """

    command: Optional[int] = None
    destination: Optional[int] = None
    source: Optional[int] = None
    address: Optional[int] = None
    channel: Optional[int] = None
    data_equals: bytes = b""
    data_mask: bytes = b""
    operation: LoraOperation = LoraOperation.QUERY
    operation_key: str = ""

    def __post_init__(self):
        if not isinstance(self.operation, LoraOperation):
            raise TypeError("operation must be a LoraOperation")
        if (self.address is None) != (self.channel is None):
            raise ValueError("address and channel must be provided together")
        if self.data_mask and len(self.data_mask) != len(self.data_equals):
            raise ValueError("data_mask must have the same length as data_equals")

    def __call__(self, frame: LoraFrame) -> bool:
        if self.command is not None and frame.command != self.command:
            return False
        if self.destination is not None and frame.destination != self.destination:
            return False
        if self.source is not None and frame.source != self.source:
            return False
        if self.address is not None:
            if len(frame.data) < 4:
                return False
            if struct.unpack("<H", frame.data[1:3])[0] != self.address:
                return False
            if frame.data[3] != self.channel:
                return False
        if self.data_equals:
            if len(frame.data) < len(self.data_equals):
                return False
            for index, expected in enumerate(self.data_equals):
                mask = self.data_mask[index] if self.data_mask else 0xFF
                if frame.data[index] & mask != expected & mask:
                    return False
        return True

    def to_rpc_dict(self):
        result = {}
        for key in ("command", "destination", "source", "address", "channel"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        if self.data_equals:
            result["dataEqualsHex"] = self.data_equals.hex()
        if self.data_mask:
            result["dataMaskHex"] = self.data_mask.hex()
        return result


@dataclass(frozen=True)
class LoraRxFilter:
    """过滤包含两个厂家 endpoint 的 RX topic 主动上报帧。

    悦帆呼叫器在 ``data[1:4]`` 中携带呼叫器 endpoint，在 ``data[4:7]``
    中携带目标机器人 endpoint。该过滤器与 :class:`LoraMatchSpec` 分开：
    后者面向请求/响应协议，通用 ``address/channel`` 只匹配 ``data[1:4]``。
    """

    command: Optional[int] = None
    destination: Optional[int] = None
    source: Optional[int] = None
    caller_address: Optional[int] = None
    caller_channel: Optional[int] = None
    robot_address: Optional[int] = None
    robot_channel: Optional[int] = None

    def __call__(self, frame: LoraFrame) -> bool:
        if self.command is not None and frame.command != self.command:
            return False
        if self.destination is not None and frame.destination != self.destination:
            return False
        if self.source is not None and frame.source != self.source:
            return False
        if len(frame.data) < 7:
            return False
        if self.caller_address is not None:
            if struct.unpack("<H", frame.data[1:3])[0] != self.caller_address:
                return False
        if self.caller_channel is not None and frame.data[3] != self.caller_channel:
            return False
        if self.robot_address is not None:
            if struct.unpack("<H", frame.data[4:6])[0] != self.robot_address:
                return False
        if self.robot_channel is not None and frame.data[6] != self.robot_channel:
            return False
        return True

    def to_topic_dict(self):
        """返回可用于 topic 注册或诊断日志的 JSON 安全字典。"""
        return {
            key: value for key, value in {
                "command": self.command,
                "destination": self.destination,
                "source": self.source,
                "callerAddress": self.caller_address,
                "callerChannel": self.caller_channel,
                "robotAddress": self.robot_address,
                "robotChannel": self.robot_channel,
            }.items() if value is not None
        }


class LoraSerialTransport:
    def __init__(
        self,
        port: Optional[str] = None,
        timeout: float = 2.0,
        retries: int = 3,
        serial_port=None,
        clock: Callable[[], float] = time.monotonic,
        frame_logger: Optional[Callable[[str, bytes], None]] = None,
    ):
        if serial_port is None and not port:
            raise ValueError("port is required when serial_port is not provided")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if retries < 1:
            raise ValueError("retries must be at least 1")
        self.port = port
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.serial = serial_port
        self._owns_serial = serial_port is None
        self._clock = clock
        self._frame_logger = frame_logger
        self._stream = LoraFrameStream()
        self._lock = threading.Lock()

    def _log_frame(self, direction: str, raw: bytes) -> None:
        if self._frame_logger is None:
            return
        try:
            self._frame_logger(direction, raw)
        except Exception:
            # 诊断日志不得影响协议请求链路。
            pass

    def open(self) -> None:
        if self.serial is not None and self.serial.is_open:
            return
        self.serial = serial.Serial(
            port=self.port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05,
            write_timeout=self.timeout,
        )
        self._enable_rs485_if_required()

    def _enable_rs485_if_required(self) -> None:
        if os.name != "posix" or self.serial is None:
            return
        try:
            platform = subprocess.check_output(
                ["cat", "/etc/srcname"], timeout=1.0
            ).decode().strip()
            if platform in ("SRC800", "SRC3000"):
                import fcntl
                fcntl.ioctl(self.serial.fileno(), 0)
        except (OSError, subprocess.SubprocessError):
            pass

    def close(self) -> None:
        if self._owns_serial and self.serial is not None:
            self.serial.close()
            self.serial = None

    def _read_matching(self, matcher: Callable[[LoraFrame], bool]) -> LoraFrame:
        deadline = self._clock() + self.timeout
        last_invalid = None
        while self._clock() < deadline:
            waiting = self.serial.in_waiting
            chunk = self.serial.read(waiting if waiting else 1)
            if not chunk:
                continue
            for raw in self._stream.feed(chunk):
                self._log_frame("RX", raw)
                try:
                    frame = LoraFrameCodec.decode(raw)
                except ValueError as error:
                    last_invalid = error
                    continue
                if matcher(frame):
                    return frame
        detail = f": {last_invalid}" if last_invalid is not None else ""
        raise LoraResponseTimeout(f"LoRa response timeout{detail}")

    def transact(
        self,
        request: LoraFrame,
        matcher: Callable[[LoraFrame], bool],
    ) -> LoraFrame:
        with self._lock:
            self.open()
            last_error = None
            for _attempt in range(self.retries):
                try:
                    self._stream.clear()
                    raw_request = LoraFrameCodec.encode(request)
                    self._log_frame("TX", raw_request)
                    self.serial.write(raw_request)
                    self.serial.flush()
                    return self._read_matching(matcher)
                except (OSError, serial.SerialException, LoraResponseTimeout) as error:
                    last_error = error
            raise LoraTransportError(
                f"LoRa request failed after {self.retries} attempts: {last_error}"
            )


class LoraRpcTransport:
    """基于 BehavFactory eCAL service 和 RX topic 的 LoRa transport。"""

    _PENDING_STATUSES = frozenset(("QUEUED", "RUNNING"))

    def __init__(
        self,
        device="Lora-000",
        timeout=2.0,
        retries=3,
        ecal_rpc=None,
        queue_timeout=2.0,
        retry_backoff=0.1,
        poll_interval=0.05,
        submission_retries=3,
        clock=time.monotonic,
        sleep=time.sleep,
        request_id_factory=None,
        frame_logger=None,
    ):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if not 1 <= int(retries) <= 10:
            raise ValueError("retries must be in range 1..10")
        if queue_timeout <= 0:
            raise ValueError("queue_timeout must be positive")
        if retry_backoff < 0:
            raise ValueError("retry_backoff must not be negative")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        if int(submission_retries) < 1:
            raise ValueError("submission_retries must be at least 1")

        if ecal_rpc is None:
            from syspy.behavs.ecal_rpc import get_ecal_rpc
            ecal_rpc = get_ecal_rpc()
        self.device = str(device or "Lora-000")
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.queue_timeout = float(queue_timeout)
        self.retry_backoff = float(retry_backoff)
        self.poll_interval = float(poll_interval)
        self.submission_retries = int(submission_retries)
        self._rpc = ecal_rpc
        self._clock = clock
        self._sleep = sleep
        self._request_id_factory = request_id_factory or self._new_request_id
        self._frame_logger = frame_logger
        self._lock = threading.Lock()
        self._active_request_id = None

    @staticmethod
    def _new_request_id():
        return "lora-{}-{}".format(os.getpid(), uuid.uuid4().hex)

    def _log_frame(self, direction, raw):
        if self._frame_logger is None:
            return
        try:
            self._frame_logger(direction, raw)
        except Exception:
            pass

    def _call(self, method, *args):
        try:
            return self._rpc.call(method, *args)
        except Exception as error:
            raise LoraTransportError(
                "BehavFactory RPC {} failed: {}".format(method, error)
            ) from error

    @staticmethod
    def _require_response(method, response):
        if response is None:
            raise LoraTransportError(
                "BehavFactory RPC {} returned no response".format(method)
            )
        if not isinstance(response, dict):
            raise LoraTransportError(
                "BehavFactory RPC {} returned an invalid response".format(method)
            )
        return response

    @staticmethod
    def _raise_terminal(response):
        status = str(response.get("status") or "INTERNAL_ERROR")
        error = str(response.get("error") or status)
        if status == "RESPONSE_TIMEOUT":
            raise LoraResponseTimeout(error)
        raise LoraTransportError("{}: {}".format(status, error))

    def _decode_terminal(self, response, matcher):
        if str(response.get("status")) != "OK" or not response.get("ok"):
            self._raise_terminal(response)
        if matcher is None:
            return None
        response_hex = response.get("responseFrameHex") or response.get("data")
        if not isinstance(response_hex, str) or not response_hex:
            raise LoraTransportError("BehavFactory returned an empty LoRa response")
        try:
            raw = bytes.fromhex(response_hex)
            frame = LoraFrameCodec.decode(raw)
        except (TypeError, ValueError) as error:
            raise LoraTransportError(
                "BehavFactory returned an invalid LoRa frame: {}".format(error)
            ) from error
        if not matcher(frame):
            raise LoraTransportError("BehavFactory returned an unmatched LoRa frame")
        self._log_frame("RX", raw)
        return frame

    def get_state(self):
        return self._require_response("getLoraState", self._call("getLoraState"))

    def cancel(self, request_id=None):
        request_id = request_id or self._active_request_id
        if not request_id:
            return False
        return bool(self._call("loraCancel", request_id))

    def close(self):
        self.cancel()

    def _submit_and_wait(self, submit_method, payload, matcher, timeout_label):
        request_id = str(payload["requestId"])
        with self._lock:
            self._active_request_id = request_id
            terminal = False
            submitted = False
            try:
                submitted = True
                request_json = json.dumps(payload, separators=(",", ":"))
                submission = None
                for attempt in range(self.submission_retries):
                    submission = self._call(submit_method, request_json)
                    if submission is None:
                        submission = self._call(
                            "getLoraResultByClient", request_id
                        )
                    if submission is None:
                        if attempt + 1 < self.submission_retries:
                            self._sleep(self.poll_interval)
                            continue
                        break
                    submission = self._require_response(
                        submit_method, submission
                    )
                    if (
                        str(submission.get("status")) == "NOT_FOUND"
                        and attempt + 1 < self.submission_retries
                    ):
                        self._sleep(self.poll_interval)
                        continue
                    break
                submission = self._require_response(
                    submit_method, submission
                )
                if submission.get("done"):
                    terminal = True
                    return self._decode_terminal(submission, matcher), submission
                if (
                    not submission.get("ok")
                    or submission.get("status") not in self._PENDING_STATUSES
                ):
                    terminal = True
                    self._raise_terminal(submission)

                total_timeout_ms = int(payload["totalTimeoutMs"])
                deadline = self._clock() + total_timeout_ms / 1000.0 + 2.0
                not_found_retries = self.submission_retries
                while self._clock() < deadline:
                    response = self._call(
                        "getLoraResultByClient", request_id
                    )
                    if response is None:
                        self._sleep(self.poll_interval)
                        continue
                    response = self._require_response(
                        "getLoraResultByClient", response
                    )
                    status = str(response.get("status") or "")
                    if status == "NOT_FOUND" and not_found_retries > 0:
                        not_found_retries -= 1
                        self._sleep(self.poll_interval)
                        continue
                    if status in self._PENDING_STATUSES and not response.get("done"):
                        self._sleep(self.poll_interval)
                        continue
                    terminal = True
                    return self._decode_terminal(response, matcher), response
                raise LoraResponseTimeout(
                    "LoRa RPC {} timeout for request {}".format(
                        timeout_label, request_id
                    )
                )
            finally:
                if submitted and not terminal:
                    try:
                        self.cancel(request_id)
                    except Exception:
                        pass
                self._active_request_id = None

    def subscribe_rx(
        self,
        *,
        client_id: str,
        filter: Callable[[LoraFrame], bool],
        stop_event,
        topic: str = "/rbk/behav/lora/rx",
        timeout: float = 1.0,
        after_generation: Optional[int] = None,
        after_sequence: Optional[int] = None,
    ):
        """订阅 Behav RX topic，并持续产出属于当前客户端的主动上报帧。

        该接口只持有 eCAL subscriber，不提交 RPC 读请求，也不占用串口
        worker。串口始终由 BehavFactory 独占管理。

        参数：
            client_id: 稳定的逻辑客户端标识，仅用于日志与游标诊断，不是
                安全凭证，也不会写入 LoRa 帧。
            filter: 帧过滤器；呼叫器应使用 :class:`LoraRxFilter`，同时匹配
                命令字、模块地址、呼叫器 endpoint 和机器人 endpoint。
            stop_event: 提供 ``is_set()`` 的生命周期停止事件。
            topic: RX topic 名称，当前固定为 ``/rbk/behav/lora/rx``。
            timeout: 等待本地事件队列的超时时间，用于及时响应停止事件。
            after_generation: 已持久化的上一设备配置世代，必须与
                ``after_sequence`` 同时设置。
            after_sequence: 已持久化的上一事件序号，用于过滤同一设备世代
                内的重复事件；topic 当前不提供历史帧补拉。

        返回：
            持续产出 :class:`LoraReceivedFrame` 的生成器。
        """
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError("client_id must be a non-empty string")
        if not callable(filter):
            raise TypeError("RX topic filter must be callable")
        if not callable(getattr(stop_event, "is_set", None)):
            raise TypeError("stop_event must provide is_set()")
        if timeout <= 0:
            raise ValueError("RX topic timeout must be positive")
        if (after_generation is None) != (after_sequence is None):
            raise ValueError(
                "after_generation and after_sequence must be provided together"
            )
        expected_topic = getattr(
            self._rpc, "LORA_RX_TOPIC_NAME", "/rbk/behav/lora/rx"
        )
        if topic != expected_topic:
            raise ValueError(
                "unsupported LoRa RX topic: {}; expected {}".format(
                    topic, expected_topic
                )
            )
        events = queue.Queue(maxsize=256)

        def on_payload(payload):
            if payload.get("version") != 1:
                return
            if payload.get("event") != "rx":
                return
            if payload.get("device") != self.device:
                return
            try:
                raw = bytes.fromhex(payload.get("frameHex") or "")
                frame = LoraFrameCodec.decode(raw)
            except (TypeError, ValueError):
                return
            event = LoraReceivedFrame(
                frame=frame,
                device=payload.get("device"),
                sequence=payload.get("sequence"),
                device_generation=payload.get("deviceGeneration"),
                received_monotonic_ms=payload.get("receivedMonotonicMs"),
            )
            matched = filter(frame)
            try:
                events.put_nowait((event, matched))
            except queue.Full:
                try:
                    events.get_nowait()
                    events.put_nowait((event, matched))
                    log.warning(
                        "LoRa RX 本地队列已满，丢弃客户端 %s 的最旧事件",
                        client_id,
                    )
                except queue.Empty:
                    pass

        subscriber = self._rpc.subscribe_lora_rx(on_payload)
        if subscriber is None:
            raise LoraTransportError("BehavFactory LoRa RX topic is unavailable")
        cursor = after_sequence
        generation = after_generation
        try:
            while not stop_event.is_set():
                try:
                    result, matched = events.get(
                        timeout=max(0.01, float(timeout))
                    )
                except queue.Empty:
                    continue
                if result.device_generation is not None:
                    if generation is None:
                        generation = result.device_generation
                    elif generation != result.device_generation:
                        cursor = None
                        generation = result.device_generation
                if (
                    cursor is not None
                    and result.sequence is not None
                    and generation == result.device_generation
                    and result.sequence <= cursor
                ):
                    continue
                if result.sequence is not None:
                    if (
                        cursor is not None
                        and generation == result.device_generation
                        and result.sequence > cursor + 1
                    ):
                        log.warning(
                            "LoRa RX 序号跳变：client=%s，上一序号=%s，当前序号=%s",
                            client_id,
                            cursor,
                            result.sequence,
                        )
                    if cursor is None or result.sequence > cursor:
                        cursor = result.sequence
                if not matched:
                    continue
                yield result
        finally:
            self._rpc.unsubscribe_lora_rx(subscriber)

    def _send_payload(self, request, request_id, operation):
        if not isinstance(operation, LoraOperation):
            raise TypeError("operation must be LoraOperation")
        if request_id is None:
            request_id = str(self._request_id_factory())
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a non-empty string")
        raw = LoraFrameCodec.encode(request)
        write_timeout_ms = max(1, min(30000, int(round(self.timeout * 1000))))
        queue_timeout_ms = max(1, min(30000, int(round(self.queue_timeout * 1000))))
        payload = {
            "version": 1,
            "requestId": request_id,
            "device": self.device,
            "operation": operation.value,
            "requestFrameHex": raw.hex(),
            "expectResponse": False,
            "responseTimeoutMs": write_timeout_ms,
            "maxAttempts": 1,
            "retryMode": "NO_RETRY",
            "queueTimeoutMs": queue_timeout_ms,
            "totalTimeoutMs": queue_timeout_ms + write_timeout_ms + 500,
        }
        self._log_frame("TX", raw)
        return payload

    def send(self, request: LoraFrame, *, request_id=None,
             operation=LoraOperation.ACK):
        """等待本地串口写入完成，返回结果字典；不等待对端回复、不自动重发。

        request_id 可由收到事件的设备世代和 sequence 构造，供幂等去重。
        OK 仅表示本地写入成功，不表示对端已收到。
        """
        payload = self._send_payload(request, request_id, operation)
        _, result = self._submit_and_wait(
            "loraTransactRequest", payload, None, "write"
        )
        return result

    def submit_send(self, request: LoraFrame, *, request_id=None,
                    operation=LoraOperation.ACK):
        """只提交单向发送，返回客户端 requestId，不轮询也不持有事务锁。

        返回 ID 仅表示已接受；可通过 getLoraResultByClient 查询或 cancel(ID)
        取消。调用方负责异步请求生命周期。提交响应丢失时仍可能已入队，
        应使用相同 request_id 重试。close() 不取消这些异步请求。
        """
        payload = self._send_payload(request, request_id, operation)
        request_json = json.dumps(payload, separators=(",", ":"))
        submission = None
        for attempt in range(self.submission_retries):
            submission = self._call("loraTransactRequest", request_json)
            if submission is not None:
                break
            if attempt + 1 < self.submission_retries:
                self._sleep(self.poll_interval)
        submission = self._require_response("loraTransactRequest", submission)
        if submission.get("done"):
            self._decode_terminal(submission, None)
        elif (not submission.get("ok")
              or submission.get("status") not in self._PENDING_STATUSES):
            self._raise_terminal(submission)
        return payload["requestId"]

    def transact(self, request: LoraFrame, matcher: Callable[[LoraFrame], bool]):
        if not isinstance(matcher, LoraMatchSpec):
            raise TypeError("RPC LoRa transactions require LoraMatchSpec")

        response_timeout_ms = max(1, min(30000, int(round(self.timeout * 1000))))
        queue_timeout_ms = max(
            1, min(30000, int(round(self.queue_timeout * 1000)))
        )
        retry_backoff_ms = max(
            0, min(30000, int(round(self.retry_backoff * 1000)))
        )
        total_timeout_ms = min(
            120000,
            queue_timeout_ms
            + self.retries * response_timeout_ms
            + (self.retries - 1) * retry_backoff_ms
            + 500,
        )
        request_id = str(self._request_id_factory())
        raw_request = LoraFrameCodec.encode(request)
        payload = {
            "version": 1,
            "requestId": request_id,
            "device": self.device,
            "operation": matcher.operation.value,
            "requestFrameHex": raw_request.hex(),
            "match": matcher.to_rpc_dict(),
            "responseTimeoutMs": response_timeout_ms,
            "maxAttempts": self.retries,
            "retryBackoffMs": retry_backoff_ms,
            "queueTimeoutMs": queue_timeout_ms,
            "totalTimeoutMs": total_timeout_ms,
            "retryMode": "SAFE_RETRY" if self.retries > 1 else "NO_RETRY",
        }
        if matcher.operation_key:
            payload["operationKey"] = matcher.operation_key

        self._log_frame("TX", raw_request)
        frame, _response = self._submit_and_wait(
            "loraTransactRequest", payload, matcher, "result"
        )
        return frame
