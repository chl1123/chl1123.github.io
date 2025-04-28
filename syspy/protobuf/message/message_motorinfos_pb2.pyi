import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_MotorInfo(_message.Message):
    __slots__ = ["calib", "can_id", "can_router", "current", "emc", "encoder", "err", "error_code", "follow_err", "header", "motor_name", "passive", "position", "raw_position", "speed", "stop", "temperature", "type", "voltage"]
    class MotorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CALIB_FIELD_NUMBER: ClassVar[int]
    CAN_ID_FIELD_NUMBER: ClassVar[int]
    CAN_ROUTER_FIELD_NUMBER: ClassVar[int]
    CURRENT_FIELD_NUMBER: ClassVar[int]
    DO: Message_MotorInfo.MotorType
    EMC_FIELD_NUMBER: ClassVar[int]
    ENCODER_FIELD_NUMBER: ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: ClassVar[int]
    ERR_FIELD_NUMBER: ClassVar[int]
    FOLLOW_ERR_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    LINEAR: Message_MotorInfo.MotorType
    MOTOR_NAME_FIELD_NUMBER: ClassVar[int]
    PASSIVE_FIELD_NUMBER: ClassVar[int]
    POSITION_FIELD_NUMBER: ClassVar[int]
    RAW_POSITION_FIELD_NUMBER: ClassVar[int]
    ROTATION: Message_MotorInfo.MotorType
    SPEED_FIELD_NUMBER: ClassVar[int]
    SPIN: Message_MotorInfo.MotorType
    STEER: Message_MotorInfo.MotorType
    STOP_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    VOLTAGE_FIELD_NUMBER: ClassVar[int]
    WALK: Message_MotorInfo.MotorType
    calib: bool
    can_id: int
    can_router: int
    current: float
    emc: bool
    encoder: int
    err: bool
    error_code: int
    follow_err: bool
    header: _message_header_pb2.Message_Header
    motor_name: str
    passive: bool
    position: float
    raw_position: float
    speed: float
    stop: bool
    temperature: float
    type: Message_MotorInfo.MotorType
    voltage: float
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., motor_name: Optional[str] = ..., can_router: Optional[int] = ..., can_id: Optional[int] = ..., position: Optional[float] = ..., speed: Optional[float] = ..., current: Optional[float] = ..., voltage: Optional[float] = ..., stop: bool = ..., error_code: Optional[int] = ..., err: bool = ..., emc: bool = ..., temperature: Optional[float] = ..., encoder: Optional[int] = ..., type: Optional[Union[Message_MotorInfo.MotorType, str]] = ..., passive: bool = ..., calib: bool = ..., follow_err: bool = ..., raw_position: Optional[float] = ...) -> None: ...

class Message_MotorInfos(_message.Message):
    __slots__ = ["motor_info"]
    MOTOR_INFO_FIELD_NUMBER: ClassVar[int]
    motor_info: _containers.RepeatedCompositeFieldContainer[Message_MotorInfo]
    def __init__(self, motor_info: Optional[Iterable[Union[Message_MotorInfo, Mapping]]] = ...) -> None: ...
