from . import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgMotorInfo(_message.Message):
    __slots__ = ["calib", "canId", "canRouter", "current", "emc", "encoder", "err", "errorCode", "followErr", "header", "key", "passive", "position", "rawPosition", "speed", "stop", "temperature", "torque", "type", "voltage"]
    class calibStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class motorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CALIB_FIELD_NUMBER: _ClassVar[int]
    CANID_FIELD_NUMBER: _ClassVar[int]
    CANROUTER_FIELD_NUMBER: _ClassVar[int]
    CURRENT_FIELD_NUMBER: _ClassVar[int]
    EMC_FIELD_NUMBER: _ClassVar[int]
    ENCODER_FIELD_NUMBER: _ClassVar[int]
    ERRORCODE_FIELD_NUMBER: _ClassVar[int]
    ERR_FIELD_NUMBER: _ClassVar[int]
    FOLLOWERR_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    PASSIVE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    RAWPOSITION_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    STOP_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TORQUE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VOLTAGE_FIELD_NUMBER: _ClassVar[int]
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
    joint: msgMotorInfo.motorType
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
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., key: _Optional[str] = ..., canRouter: _Optional[int] = ..., canId: _Optional[int] = ..., position: _Optional[float] = ..., speed: _Optional[float] = ..., current: _Optional[float] = ..., voltage: _Optional[float] = ..., stop: bool = ..., errorCode: _Optional[int] = ..., err: bool = ..., emc: bool = ..., temperature: _Optional[float] = ..., encoder: _Optional[int] = ..., type: _Optional[_Union[msgMotorInfo.motorType, str]] = ..., passive: bool = ..., calib: _Optional[_Union[msgMotorInfo.calibStatus, str]] = ..., followErr: bool = ..., rawPosition: _Optional[float] = ..., torque: _Optional[float] = ...) -> None: ...

class msgMotorInfos(_message.Message):
    __slots__ = ["motorInfo"]
    MOTORINFO_FIELD_NUMBER: _ClassVar[int]
    motorInfo: _containers.RepeatedCompositeFieldContainer[msgMotorInfo]
    def __init__(self, motorInfo: _Optional[_Iterable[_Union[msgMotorInfo, _Mapping]]] = ...) -> None: ...
