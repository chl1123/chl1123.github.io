from . import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgDistanceNode(_message.Message):
    __slots__ = ["RSSI", "aperture", "canRouter", "dist", "forbidden", "header", "id", "key", "posAngle", "posX", "posY", "rs485", "valid"]
    APERTURE_FIELD_NUMBER: _ClassVar[int]
    CANROUTER_FIELD_NUMBER: _ClassVar[int]
    DIST_FIELD_NUMBER: _ClassVar[int]
    FORBIDDEN_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    POSANGLE_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    RS485_FIELD_NUMBER: _ClassVar[int]
    RSSI: int
    RSSI_FIELD_NUMBER: _ClassVar[int]
    VALID_FIELD_NUMBER: _ClassVar[int]
    aperture: float
    canRouter: int
    dist: float
    forbidden: bool
    header: _message_header_pb2.msgHeader
    id: int
    key: str
    posAngle: float
    posX: float
    posY: float
    rs485: int
    valid: bool
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., key: _Optional[str] = ..., id: _Optional[int] = ..., dist: _Optional[float] = ..., valid: bool = ..., posX: _Optional[float] = ..., posY: _Optional[float] = ..., posAngle: _Optional[float] = ..., aperture: _Optional[float] = ..., forbidden: bool = ..., canRouter: _Optional[int] = ..., rs485: _Optional[int] = ..., RSSI: _Optional[int] = ...) -> None: ...

class msgDistanceSensor(_message.Message):
    __slots__ = ["node"]
    NODE_FIELD_NUMBER: _ClassVar[int]
    node: _containers.RepeatedCompositeFieldContainer[msgDistanceNode]
    def __init__(self, node: _Optional[_Iterable[_Union[msgDistanceNode, _Mapping]]] = ...) -> None: ...
