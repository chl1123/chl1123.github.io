# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_header_p2p import Message_Header
from enum import IntEnum
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class Message_Bin(BaseModel):
    class Status(IntEnum):
        Connect = 0
        DisConnect = 1

    binId: str = Field(default="")
    filled: bool = Field(default=False)
    status: "Message_Bin.Status" = Field(default=0)


class Message_Bins(BaseModel):
    header: typing.Optional[Message_Header] = None
    bins: typing.List[Message_Bin] = Field(default_factory=list)
