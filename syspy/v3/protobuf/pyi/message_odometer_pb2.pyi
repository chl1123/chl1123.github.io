import message_header_pb2 as _message_header_pb2
import message_motorinfos_pb2 as _message_motorinfos_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_Odometer(_message.Message):
    __slots__ = ["angle", "cycle", "detect_skid", "follow_err", "header", "is_stop", "motor_info", "vel_rotate", "vel_x", "vel_y", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    CYCLE_FIELD_NUMBER: ClassVar[int]
    DETECT_SKID_FIELD_NUMBER: ClassVar[int]
    FOLLOW_ERR_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    IS_STOP_FIELD_NUMBER: ClassVar[int]
    MOTOR_INFO_FIELD_NUMBER: ClassVar[int]
    VEL_ROTATE_FIELD_NUMBER: ClassVar[int]
    VEL_X_FIELD_NUMBER: ClassVar[int]
    VEL_Y_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    cycle: int
    detect_skid: bool
    follow_err: bool
    header: _message_header_pb2.Message_Header
    is_stop: bool
    motor_info: _containers.RepeatedCompositeFieldContainer[_message_motorinfos_pb2.Message_MotorInfo]
    vel_rotate: float
    vel_x: float
    vel_y: float
    x: float
    y: float
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., cycle: Optional[int] = ..., x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ..., is_stop: bool = ..., vel_x: Optional[float] = ..., vel_y: Optional[float] = ..., vel_rotate: Optional[float] = ..., detect_skid: bool = ..., motor_info: Optional[Iterable[Union[_message_motorinfos_pb2.Message_MotorInfo, Mapping]]] = ..., follow_err: bool = ...) -> None: ...
