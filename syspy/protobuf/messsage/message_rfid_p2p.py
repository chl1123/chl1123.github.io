# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_header_p2p import Message_Header
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class Message_RFIDNode(BaseModel):
    id: int = Field(default=0)
    count: int = Field(default=0)
    header: typing.Optional[Message_Header] = None
    strength: int = Field(default=0)


class Message_RFID(BaseModel):
    rfid_nodes: typing.List[Message_RFIDNode] = Field(default_factory=list)
