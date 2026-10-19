from . import message_header_pb2 as _message_header_pb2
from . import message_motorinfos_pb2 as _message_motorinfos_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgOdometer(_message.Message):
    __slots__ = ["angle", "cycle", "header", "isStop", "motorInfo", "velRotate", "velX", "velY", "x", "y"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    CYCLE_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ISSTOP_FIELD_NUMBER: _ClassVar[int]
    MOTORINFO_FIELD_NUMBER: _ClassVar[int]
    VELROTATE_FIELD_NUMBER: _ClassVar[int]
    VELX_FIELD_NUMBER: _ClassVar[int]
    VELY_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    cycle: int
    header: _message_header_pb2.msgHeader
    isStop: bool
    motorInfo: _containers.RepeatedCompositeFieldContainer[_message_motorinfos_pb2.msgMotorInfo]
    velRotate: float
    velX: float
    velY: float
    x: float
    y: float
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., cycle: _Optional[int] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ..., isStop: bool = ..., velX: _Optional[float] = ..., velY: _Optional[float] = ..., velRotate: _Optional[float] = ..., motorInfo: _Optional[_Iterable[_Union[_message_motorinfos_pb2.msgMotorInfo, _Mapping]]] = ...) -> None: ...

class msgSlip(_message.Message):
    __slots__ = ["name", "slip", "slipTime"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SLIPTIME_FIELD_NUMBER: _ClassVar[int]
    SLIP_FIELD_NUMBER: _ClassVar[int]
    name: str
    slip: float
    slipTime: float
    def __init__(self, slip: _Optional[float] = ..., slipTime: _Optional[float] = ..., name: _Optional[str] = ...) -> None: ...

class msgSlipSensor(_message.Message):
    __slots__ = ["motor", "type", "vw", "vx", "vy"]
    class slipType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    MOTOR_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VW_FIELD_NUMBER: _ClassVar[int]
    VX_FIELD_NUMBER: _ClassVar[int]
    VY_FIELD_NUMBER: _ClassVar[int]
    imu: msgSlipSensor.slipType
    loc: msgSlipSensor.slipType
    motor: _containers.RepeatedCompositeFieldContainer[msgSlip]
    opt: msgSlipSensor.slipType
    type: msgSlipSensor.slipType
    vw: msgSlip
    vx: msgSlip
    vy: msgSlip
    def __init__(self, type: _Optional[_Union[msgSlipSensor.slipType, str]] = ..., vx: _Optional[_Union[msgSlip, _Mapping]] = ..., vy: _Optional[_Union[msgSlip, _Mapping]] = ..., vw: _Optional[_Union[msgSlip, _Mapping]] = ..., motor: _Optional[_Iterable[_Union[msgSlip, _Mapping]]] = ...) -> None: ...

class msgSlipSensors(_message.Message):
    __slots__ = ["slipSensors"]
    SLIPSENSORS_FIELD_NUMBER: _ClassVar[int]
    slipSensors: _containers.RepeatedCompositeFieldContainer[msgSlipSensor]
    def __init__(self, slipSensors: _Optional[_Iterable[_Union[msgSlipSensor, _Mapping]]] = ...) -> None: ...
