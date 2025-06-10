# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_header_p2p import Message_Header
from .message_motorinfos_p2p import Message_MotorInfo
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class Message_Odometer(BaseModel):
    header: typing.Optional[Message_Header] = None
    cycle: int = Field(default=0)  # cnt
    x: float = Field(default=0.0)  # m
    y: float = Field(default=0.0)  # m
    angle: float = Field(default=0.0)  # rad
    is_stop: bool = Field(default=False)
    vel_x: float = Field(default=0.0)  # m/s
    vel_y: float = Field(default=0.0)  # m/s
    vel_rotate: float = Field(default=0.0)  # rad/s
    detect_skid: bool = Field(default=False)
    motor_info: typing.List[Message_MotorInfo] = Field(default_factory=list)
    follow_err: bool = Field(default=False)  # has motor following error(s)
