# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_header_p2p import Message_Header
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class Message_DistanceNode(BaseModel):
    header: typing.Optional[Message_Header] = None
    name: str = Field(default="")  # 设备名
    id: int = Field(default=0)  # 设备id
    dist: float = Field(default=0.0)  # 距离，单位m
    valid: bool = Field(default=False)  # 数据是否有效
    pos_x: float = Field(default=0.0)
    pos_y: float = Field(default=0.0)
    pos_angle: float = Field(default=0.0)  # 安装角度
    aperture: float = Field(default=0.0)  # 扇形范围
    forbidden: bool = Field(default=False)  # 是否禁用
    can_router: int = Field(default=0)  # can端口号
    rs485: int = Field(default=0)  # rs485端口号
    RSSI: int = Field(default=0)  # 强度


class Message_DistanceSensor(BaseModel):
    node: typing.List[Message_DistanceNode] = Field(default_factory=list)
