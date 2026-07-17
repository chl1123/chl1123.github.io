from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgDmx512(_message.Message):
    __slots__ = ["battery", "colorBlue", "colorGreen", "colorRed", "colorWhite", "ledIdxMask", "period", "turnLeftOrRight", "type"]
    BATTERY_FIELD_NUMBER: ClassVar[int]
    COLORBLUE_FIELD_NUMBER: ClassVar[int]
    COLORGREEN_FIELD_NUMBER: ClassVar[int]
    COLORRED_FIELD_NUMBER: ClassVar[int]
    COLORWHITE_FIELD_NUMBER: ClassVar[int]
    LEDIDXMASK_FIELD_NUMBER: ClassVar[int]
    PERIOD_FIELD_NUMBER: ClassVar[int]
    TURNLEFTORRIGHT_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    battery: int
    colorBlue: int
    colorGreen: int
    colorRed: int
    colorWhite: int
    ledIdxMask: int
    period: int
    turnLeftOrRight: int
    type: int
    def __init__(self, type: Optional[int] = ..., battery: Optional[int] = ..., colorRed: Optional[int] = ..., colorGreen: Optional[int] = ..., colorBlue: Optional[int] = ..., colorWhite: Optional[int] = ..., turnLeftOrRight: Optional[int] = ..., period: Optional[int] = ..., ledIdxMask: Optional[int] = ...) -> None: ...
