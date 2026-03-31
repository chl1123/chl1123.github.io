import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgMotorInfo(_message.Message):
    __slots__ = ["calib", "canId", "canRouter", "current", "emc", "encoder", "err", "errorCode", "followErr", "header", "key", "passive", "position", "rawPosition", "speed", "stop", "temperature", "torque", "type", "voltage"]
    class calibStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class motorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CALIB_FIELD_NUMBER: ClassVar[int]
    CANID_FIELD_NUMBER: ClassVar[int]
    CANROUTER_FIELD_NUMBER: ClassVar[int]
    CURRENT_FIELD_NUMBER: ClassVar[int]
    EMC_FIELD_NUMBER: ClassVar[int]
    ENCODER_FIELD_NUMBER: ClassVar[int]
    ERRORCODE_FIELD_NUMBER: ClassVar[int]
    ERR_FIELD_NUMBER: ClassVar[int]
    FOLLOWERR_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    PASSIVE_FIELD_NUMBER: ClassVar[int]
    POSITION_FIELD_NUMBER: ClassVar[int]
    RAWPOSITION_FIELD_NUMBER: ClassVar[int]
    SPEED_FIELD_NUMBER: ClassVar[int]
    STOP_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    TORQUE_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    VOLTAGE_FIELD_NUMBER: ClassVar[int]
    calib: msgMotorInfo.calibStatus
    calibed: msgMotorInfo.calibStatus
    calibing: msgMotorInfo.calibStatus
    canId: int
    canRouter: int
    current: float
    do: msgMotorInfo.motorType
    emc: bool
    encoder: int
    err: bool
    errorCode: int
    followErr: bool
    header: _message_header_pb2.msgHeader
    key: str
    linear: msgMotorInfo.motorType
    notClibed: msgMotorInfo.calibStatus
    passive: bool
    position: float
    rawPosition: float
    rotation: msgMotorInfo.motorType
    speed: float
    spin: msgMotorInfo.motorType
    steer: msgMotorInfo.motorType
    stop: bool
    temperature: float
    torque: float
    type: msgMotorInfo.motorType
    voltage: float
    walk: msgMotorInfo.motorType
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., key: Optional[str] = ..., canRouter: Optional[int] = ..., canId: Optional[int] = ..., position: Optional[float] = ..., speed: Optional[float] = ..., current: Optional[float] = ..., voltage: Optional[float] = ..., stop: bool = ..., errorCode: Optional[int] = ..., err: bool = ..., emc: bool = ..., temperature: Optional[float] = ..., encoder: Optional[int] = ..., type: Optional[Union[msgMotorInfo.motorType, str]] = ..., passive: bool = ..., calib: Optional[Union[msgMotorInfo.calibStatus, str]] = ..., followErr: bool = ..., rawPosition: Optional[float] = ..., torque: Optional[float] = ...) -> None: ...

class msgMotorInfos(_message.Message):
    __slots__ = ["motorInfo"]
    MOTORINFO_FIELD_NUMBER: ClassVar[int]
    motorInfo: _containers.RepeatedCompositeFieldContainer[msgMotorInfo]
    def __init__(self, motorInfo: Optional[Iterable[Union[msgMotorInfo, Mapping]]] = ...) -> None: ...
