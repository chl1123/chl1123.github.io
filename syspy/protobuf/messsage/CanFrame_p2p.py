# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from enum import IntEnum
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class DIRE_ENUM(IntEnum):
    RX = 0
    TX = 1


class ERROR_TYPE(IntEnum):
    STUFF_ERROR = 0
    FORM_ERROR = 1
    ACKNOWLEDGEMENT_ERROR = 2
    BIT_RECESSIVE_ERROR = 3
    BIT_DOMINANT_ERROR = 4
    CRC_ERROR = 5


class CanErrorRecord(BaseModel):
    Errortype: int = Field(default=0)
    Errorcount: int = Field(default=0)


class CanFrame(BaseModel):
    ID: int = Field(default=0)
    Extended: bool = Field(default=False)
    Remote: bool = Field(default=False)
    DLC: int = Field(default=0)
    Data: bytes = Field(default=b"")
    Channel: int = Field(default=0)
    Timestamp: int = Field(default=0)
    Direction: bool = Field(default=False)
    Canerror: typing.List[CanErrorRecord] = Field(default_factory=list)
