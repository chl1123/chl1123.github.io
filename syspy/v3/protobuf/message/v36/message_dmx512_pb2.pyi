from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgDmx512(_message.Message):
    __slots__ = ["battery", "colorBlue", "colorGreen", "colorRed", "colorWhite", "ledIdxMask", "period", "turnLeftOrRight", "type"]
    BATTERY_FIELD_NUMBER: _ClassVar[int]
    COLORBLUE_FIELD_NUMBER: _ClassVar[int]
    COLORGREEN_FIELD_NUMBER: _ClassVar[int]
    COLORRED_FIELD_NUMBER: _ClassVar[int]
    COLORWHITE_FIELD_NUMBER: _ClassVar[int]
    LEDIDXMASK_FIELD_NUMBER: _ClassVar[int]
    PERIOD_FIELD_NUMBER: _ClassVar[int]
    TURNLEFTORRIGHT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    battery: int
    colorBlue: int
    colorGreen: int
    colorRed: int
    colorWhite: int
    ledIdxMask: int
    period: int
    turnLeftOrRight: int
    type: int
    def __init__(self, type: _Optional[int] = ..., battery: _Optional[int] = ..., colorRed: _Optional[int] = ..., colorGreen: _Optional[int] = ..., colorBlue: _Optional[int] = ..., colorWhite: _Optional[int] = ..., turnLeftOrRight: _Optional[int] = ..., period: _Optional[int] = ..., ledIdxMask: _Optional[int] = ...) -> None: ...
