import message_header_pb2 as _message_header_pb2
import message_motorinfos_pb2 as _message_motorinfos_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgOdometer(_message.Message):
    __slots__ = ["angle", "cycle", "header", "isStop", "motorInfo", "velRotate", "velX", "velY", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    CYCLE_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ISSTOP_FIELD_NUMBER: ClassVar[int]
    MOTORINFO_FIELD_NUMBER: ClassVar[int]
    VELROTATE_FIELD_NUMBER: ClassVar[int]
    VELX_FIELD_NUMBER: ClassVar[int]
    VELY_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., cycle: Optional[int] = ..., x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ..., isStop: bool = ..., velX: Optional[float] = ..., velY: Optional[float] = ..., velRotate: Optional[float] = ..., motorInfo: Optional[Iterable[Union[_message_motorinfos_pb2.msgMotorInfo, Mapping]]] = ...) -> None: ...

class msgSlip(_message.Message):
    __slots__ = ["name", "slip", "slipTime"]
    NAME_FIELD_NUMBER: ClassVar[int]
    SLIPTIME_FIELD_NUMBER: ClassVar[int]
    SLIP_FIELD_NUMBER: ClassVar[int]
    name: str
    slip: float
    slipTime: float
    def __init__(self, slip: Optional[float] = ..., slipTime: Optional[float] = ..., name: Optional[str] = ...) -> None: ...

class msgSlipSensor(_message.Message):
    __slots__ = ["motor", "type", "vw", "vx", "vy"]
    class slipType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    MOTOR_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    VW_FIELD_NUMBER: ClassVar[int]
    VX_FIELD_NUMBER: ClassVar[int]
    VY_FIELD_NUMBER: ClassVar[int]
    imu: msgSlipSensor.slipType
    loc: msgSlipSensor.slipType
    motor: _containers.RepeatedCompositeFieldContainer[msgSlip]
    opt: msgSlipSensor.slipType
    type: msgSlipSensor.slipType
    vw: msgSlip
    vx: msgSlip
    vy: msgSlip
    def __init__(self, type: Optional[Union[msgSlipSensor.slipType, str]] = ..., vx: Optional[Union[msgSlip, Mapping]] = ..., vy: Optional[Union[msgSlip, Mapping]] = ..., vw: Optional[Union[msgSlip, Mapping]] = ..., motor: Optional[Iterable[Union[msgSlip, Mapping]]] = ...) -> None: ...

class msgSlipSensors(_message.Message):
    __slots__ = ["slipSensors"]
    SLIPSENSORS_FIELD_NUMBER: ClassVar[int]
    slipSensors: _containers.RepeatedCompositeFieldContainer[msgSlipSensor]
    def __init__(self, slipSensors: Optional[Iterable[Union[msgSlipSensor, Mapping]]] = ...) -> None: ...
