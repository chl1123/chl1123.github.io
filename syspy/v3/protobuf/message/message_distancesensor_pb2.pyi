import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgDistanceNode(_message.Message):
    __slots__ = ["RSSI", "aperture", "canRouter", "dist", "forbidden", "header", "id", "name", "posAngle", "posX", "posY", "rs485", "valid"]
    APERTURE_FIELD_NUMBER: ClassVar[int]
    CANROUTER_FIELD_NUMBER: ClassVar[int]
    DIST_FIELD_NUMBER: ClassVar[int]
    FORBIDDEN_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    NAME_FIELD_NUMBER: ClassVar[int]
    POSANGLE_FIELD_NUMBER: ClassVar[int]
    POSX_FIELD_NUMBER: ClassVar[int]
    POSY_FIELD_NUMBER: ClassVar[int]
    RS485_FIELD_NUMBER: ClassVar[int]
    RSSI: int
    RSSI_FIELD_NUMBER: ClassVar[int]
    VALID_FIELD_NUMBER: ClassVar[int]
    aperture: float
    canRouter: int
    dist: float
    forbidden: bool
    header: _message_header_pb2.msgHeader
    id: int
    name: str
    posAngle: float
    posX: float
    posY: float
    rs485: int
    valid: bool
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., name: Optional[str] = ..., id: Optional[int] = ..., dist: Optional[float] = ..., valid: bool = ..., posX: Optional[float] = ..., posY: Optional[float] = ..., posAngle: Optional[float] = ..., aperture: Optional[float] = ..., forbidden: bool = ..., canRouter: Optional[int] = ..., rs485: Optional[int] = ..., RSSI: Optional[int] = ...) -> None: ...

class msgDistanceSensor(_message.Message):
    __slots__ = ["node"]
    NODE_FIELD_NUMBER: ClassVar[int]
    node: _containers.RepeatedCompositeFieldContainer[msgDistanceNode]
    def __init__(self, node: Optional[Iterable[Union[msgDistanceNode, Mapping]]] = ...) -> None: ...
