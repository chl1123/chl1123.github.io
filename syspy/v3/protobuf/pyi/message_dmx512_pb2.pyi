from typing import ClassVar, Optional

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Dmx512(_message.Message):
    """
    表示 DMX512 相关消息的模型。

    Attributes:
        type (int): 消息类型，默认为 0。
        battery (int): 电池电量，默认为 0。
        color_r (int): 红色阈值，默认为 0。
        color_g (int): 绿色阈值，默认为 0。
        color_b (int): 蓝色阈值，默认为 0。
        color_w (int): 白色阈值，默认为 0。
        turn_left_or_right (int): 左右转向相关标识，默认为 0。
    """
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

    def __init__(self, type: Optional[int] = ..., battery: Optional[int] = ..., color_r: Optional[int] = ...,
                 color_g: Optional[int] = ..., color_b: Optional[int] = ..., color_w: Optional[int] = ...,
                 turn_left_or_right: Optional[int] = ...) -> None: ...
