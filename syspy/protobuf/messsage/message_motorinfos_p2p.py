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


class Message_MotorInfo(BaseModel):
    class MotorType(IntEnum):
        WALK = 0
        STEER = 1
        SPIN = 2
        LINEAR = 3
        ROTATION = 4
        DO = 5

    header: typing.Optional[Message_Header] = None
    motor_name: str = Field(default="")
    can_router: int = Field(default=0)
    can_id: int = Field(default=0)
    position: float = Field(default=0.0)  # m
    speed: float = Field(default=0.0)  # m/s
    current: float = Field(default=0.0)  # A
    voltage: float = Field(default=0.0)  # V
    stop: bool = Field(default=False)
    error_code: int = Field(default=0)
    err: bool = Field(default=False)
    emc: bool = Field(default=False)
    temperature: float = Field(default=0.0)  # deg
    encoder: int = Field(default=0)  # cnt
    type: "Message_MotorInfo.MotorType" = Field(default=0)
    passive: bool = Field(default=False)
    calib: bool = Field(default=False)
    follow_err: bool = Field(default=False)
    raw_position: float = Field(default=0.0)  # steer angle without .cp value


class Message_MotorInfos(BaseModel):
    motor_info: typing.List[Message_MotorInfo] = Field(default_factory=list)
