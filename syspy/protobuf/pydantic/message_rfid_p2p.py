# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field

from .message_header_p2p import Message_Header


class Message_RFIDNode(BaseModel):
    """表示RFID节点信息的模型类。

    Attributes:
        id (int): RFID节点的ID，默认值为0。
        count (int): RFID节点的计数，默认值为0。
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认为None，包含消息的元数据。
        strength (int): RFID信号强度，默认值为0。
    """
    id: int = Field(default=0)
    count: int = Field(default=0)
    header: typing.Optional[Message_Header] = None
    strength: int = Field(default=0)


class Message_RFID(BaseModel):
    """表示多个RFID节点信息集合的模型类。

    Attributes:
        rfid_nodes (typing.List[Message_RFIDNode]): RFID节点信息列表，存储多个RFID节点的信息，默认初始化为空列表。
    """
    rfid_nodes: typing.List[Message_RFIDNode] = Field(default_factory=list)
