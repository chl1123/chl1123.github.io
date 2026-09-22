import json
import os
import struct
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable, List, Optional

import serial


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


@dataclass(frozen=True)
class LoraMatchSpec:
    """Serializable response matcher shared by direct and RPC transports."""

    command: Optional[int] = None
    destination: Optional[int] = None
    source: Optional[int] = None
    address: Optional[int] = None
    channel: Optional[int] = None
    data_equals: bytes = b""
    data_mask: bytes = b""
    operation: str = "QUERY"
    operation_key: str = ""

    def __post_init__(self):
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
            # Diagnostics must never change the protocol request path.
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
    """LoRa transaction transport backed by the BehavFactory eCAL service."""

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
            "operation": matcher.operation or "QUERY",
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

        with self._lock:
            self._active_request_id = request_id
            terminal = False
            submitted = False
            self._log_frame("TX", raw_request)
            try:
                submitted = True
                request_json = json.dumps(payload, separators=(",", ":"))
                submission = None
                for attempt in range(self.submission_retries):
                    submission = self._call(
                        "loraTransactRequest", request_json
                    )
                    if submission is None:
                        # The one-second eCAL response may be lost after
                        # Behav has already accepted the request. Resolve by
                        # the stable client ID instead of creating a second
                        # logical request.
                        submission = self._call(
                            "getLoraResultByClient", request_id
                        )
                    if submission is None:
                        if attempt + 1 < self.submission_retries:
                            self._sleep(self.poll_interval)
                            continue
                        break
                    submission = self._require_response(
                        "loraTransactRequest", submission
                    )
                    # A just-accepted request can briefly be absent from the
                    # client index while the manager publishes it. Re-submit
                    # with the same client ID; Behav deduplicates an existing
                    # request and creates no duplicate wire transaction.
                    if (
                        str(submission.get("status")) == "NOT_FOUND"
                        and attempt + 1 < self.submission_retries
                    ):
                        self._sleep(self.poll_interval)
                        continue
                    break
                submission = self._require_response(
                    "loraTransactRequest", submission
                )
                if submission.get("done"):
                    terminal = True
                    return self._decode_terminal(submission, matcher)
                if (
                    not submission.get("ok")
                    or submission.get("status") not in self._PENDING_STATUSES
                ):
                    terminal = True
                    self._raise_terminal(submission)

                deadline = self._clock() + total_timeout_ms / 1000.0 + 2.0
                not_found_retries = self.submission_retries
                while self._clock() < deadline:
                    response = self._call("getLoraResultByClient", request_id)
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
                    return self._decode_terminal(response, matcher)
                raise LoraResponseTimeout(
                    "LoRa RPC result timeout for request {}".format(request_id)
                )
            finally:
                if submitted and not terminal:
                    try:
                        self.cancel(request_id)
                    except Exception:
                        pass
                self._active_request_id = None
