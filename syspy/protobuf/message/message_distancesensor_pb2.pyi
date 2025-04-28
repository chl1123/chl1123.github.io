import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_DistanceNode(_message.Message):
    __slots__ = ["RSSI", "aperture", "can_router", "dist", "forbidden", "header", "id", "name", "pos_angle", "pos_x", "pos_y", "rs485", "valid"]
    APERTURE_FIELD_NUMBER: ClassVar[int]
    CAN_ROUTER_FIELD_NUMBER: ClassVar[int]
    DIST_FIELD_NUMBER: ClassVar[int]
    FORBIDDEN_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    NAME_FIELD_NUMBER: ClassVar[int]
    POS_ANGLE_FIELD_NUMBER: ClassVar[int]
    POS_X_FIELD_NUMBER: ClassVar[int]
    POS_Y_FIELD_NUMBER: ClassVar[int]
    RS485_FIELD_NUMBER: ClassVar[int]
    RSSI: int
    RSSI_FIELD_NUMBER: ClassVar[int]
    VALID_FIELD_NUMBER: ClassVar[int]
    aperture: float
    can_router: int
    dist: float
    forbidden: bool
    header: _message_header_pb2.Message_Header
    id: int
    name: str
    pos_angle: float
    pos_x: float
    pos_y: float
    rs485: int
    valid: bool
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., name: Optional[str] = ..., id: Optional[int] = ..., dist: Optional[float] = ..., valid: bool = ..., pos_x: Optional[float] = ..., pos_y: Optional[float] = ..., pos_angle: Optional[float] = ..., aperture: Optional[float] = ..., forbidden: bool = ..., can_router: Optional[int] = ..., rs485: Optional[int] = ..., RSSI: Optional[int] = ...) -> None: ...

class Message_DistanceSensor(_message.Message):
    __slots__ = ["node"]
    NODE_FIELD_NUMBER: ClassVar[int]
    node: _containers.RepeatedCompositeFieldContainer[Message_DistanceNode]
    def __init__(self, node: Optional[Iterable[Union[Message_DistanceNode, Mapping]]] = ...) -> None: ...
