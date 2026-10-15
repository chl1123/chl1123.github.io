from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


class ProtocolUnavailable(RuntimeError):
    pass


class ProtocolRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class ReceiverInfo:
    """接收器自查询 (0x0940) 的应答: 接收器自身的地址/信道/发射功率。

    发送器必须先知道这里的 address / channel 才能发起呼叫。
    """

    address: int
    channel: int
    tx_power: int
    tx_power_name: str
    protocol_version: int = 0x03

    def as_dict(self):
        return {
            "address": self.address,
            "channel": self.channel,
            "txPower": self.tx_power,
            "txPowerName": self.tx_power_name,
            "protocolVersion": self.protocol_version,
        }


@dataclass(frozen=True)
class CallRequest:
    """发送器呼叫指令 (0x0950) 的解析结果。"""

    sender_address: int
    sender_channel: int
    receiver_address: int
    receiver_channel: int
    call_value: int
    raw: bytes = b""
    # RX topic 订阅事件的游标字段 (仅 RPC 订阅路径有值, 串口直读为 None)。
    # 应答时拼 ack_id = f"ack:{client_id}:{device_generation}:{sequence}"
    # 要求同一事件重试时 ack_id 不变, 所以这两个字段要随 CallRequest 带到
    # reply_to_sender(), 不能只留在收帧那一层。
    sequence: Optional[int] = None
    device_generation: Optional[int] = None

    def as_dict(self):
        result = {
            "senderAddress": self.sender_address,
            "senderChannel": self.sender_channel,
            "receiverAddress": self.receiver_address,
            "receiverChannel": self.receiver_channel,
            "callValue": self.call_value,
            "raw": self.raw.hex(),
        }
        if self.sequence is not None:
            result["sequence"] = self.sequence
        if self.device_generation is not None:
            result["deviceGeneration"] = self.device_generation
        return result


class Rs485Protocol(ABC):
    @abstractmethod
    def query_self(self) -> ReceiverInfo:
        """接收器自查询, 取回自身地址与信道。"""

    @abstractmethod
    def wait_for_call(self, timeout: float) -> Optional[CallRequest]:
        """监听发送器呼叫指令。"""

    @abstractmethod
    def reply_to_sender(self, call: CallRequest) -> bytes:
        """向发送器回复应答帧。"""
