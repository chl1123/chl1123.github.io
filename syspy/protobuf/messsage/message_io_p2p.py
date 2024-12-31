# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class Message_DINode(BaseModel):
    id: int = Field(default=0)
    status: bool = Field(default=False)
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    func: str = Field(default="")
    type: str = Field(default="")
    source: str = Field(default="")
    shape: str = Field(default="")
    mindist: float = Field(default=0.0)
    maxdist: float = Field(default=0.0)
    range: float = Field(default=0.0)
    posx: typing.List[float] = Field(default_factory=list)
    posy: typing.List[float] = Field(default_factory=list)
    forbidden: bool = Field(default=False)


class Message_DI(BaseModel):
    node: typing.List[Message_DINode] = Field(default_factory=list)
    max_node: int = Field(default=0)


class Message_DONode(BaseModel):
    id: int = Field(default=0)
    status: bool = Field(default=False)
    source: str = Field(default="")
    func: str = Field(default="")


class Message_DO(BaseModel):
    node: typing.List[Message_DONode] = Field(default_factory=list)
    max_node: int = Field(default=0)


class Message_Astern(BaseModel):
    status: int = Field(default=0)
