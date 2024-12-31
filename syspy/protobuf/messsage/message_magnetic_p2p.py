# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_header_p2p import Message_Header
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class Message_MagneticNode(BaseModel):
    id: int = Field(default=0)
    value: typing.List[bool] = Field(default_factory=list)
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    step: float = Field(default=0.0)
    resolution: int = Field(default=0)
    header: typing.Optional[Message_Header] = None


class Message_Magnetic(BaseModel):
    magnetic_nodes: typing.List[Message_MagneticNode] = Field(default_factory=list)
