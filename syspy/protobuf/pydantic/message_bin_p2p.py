# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing
from enum import IntEnum

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field

from .message_header_p2p import Message_Header


class Message_Bin(BaseModel):
    """
    表示库位相关信息。

    Attributes:
        binId (str): 库位的唯一标识符，默认为空字符串。
        filled (bool): 表示库位是否已被占用，默认未占用。
        status (Message_Bin.Status): 库位的状态，默认为连接状态。
    """

    class Status(IntEnum):
        """
        库位状态枚举类。

        Attributes:
            Connect: 值为 0，表示库位已连接的状态。
            DisConnect: 值为 1，表示库位未连接的状态。
        """
        Connect = 0
        DisConnect = 1

    binId: str = Field(default="")
    filled: bool = Field(default=False)
    status: "Message_Bin.Status" = Field(default=Status.Connect)


class Message_Bins(BaseModel):
    """
    表示多个库位的消息集合。

    Attributes:
        header (typing.Optional[Message_Header]): 消息头，可选，默认为 None。
        bins (typing.List[Message_Bin]): 库位列表，默认为空列表。
    """
    header: typing.Optional[Message_Header] = None
    bins: typing.List[Message_Bin] = Field(default_factory=list)
