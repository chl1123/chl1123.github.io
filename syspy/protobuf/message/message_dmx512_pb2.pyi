from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Message_Dmx512(_message.Message):
    __slots__ = ["battery", "color_b", "color_g", "color_r", "color_w", "turn_left_or_right", "type"]
    BATTERY_FIELD_NUMBER: ClassVar[int]
    COLOR_B_FIELD_NUMBER: ClassVar[int]
    COLOR_G_FIELD_NUMBER: ClassVar[int]
    COLOR_R_FIELD_NUMBER: ClassVar[int]
    COLOR_W_FIELD_NUMBER: ClassVar[int]
    TURN_LEFT_OR_RIGHT_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    battery: int
    color_b: int
    color_g: int
    color_r: int
    color_w: int
    turn_left_or_right: int
    type: int
    def __init__(self, type: Optional[int] = ..., battery: Optional[int] = ..., color_r: Optional[int] = ..., color_g: Optional[int] = ..., color_b: Optional[int] = ..., color_w: Optional[int] = ..., turn_left_or_right: Optional[int] = ...) -> None: ...
