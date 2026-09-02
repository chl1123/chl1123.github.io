import os
import struct
import subprocess
import threading
import time
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
