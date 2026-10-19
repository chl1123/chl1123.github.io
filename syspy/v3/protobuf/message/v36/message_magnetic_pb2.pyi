from . import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgMagnetic(_message.Message):
    __slots__ = ["magneticNodes"]
    MAGNETICNODES_FIELD_NUMBER: _ClassVar[int]
    magneticNodes: _containers.RepeatedCompositeFieldContainer[msgMagneticNode]
    def __init__(self, magneticNodes: _Optional[_Iterable[_Union[msgMagneticNode, _Mapping]]] = ...) -> None: ...

class msgMagneticNode(_message.Message):
    __slots__ = ["header", "id", "key", "resolution", "step", "value", "x", "y", "yaw"]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    header: _message_header_pb2.msgHeader
    id: int
    key: str
    resolution: int
    step: float
    value: _containers.RepeatedScalarFieldContainer[bool]
    x: float
    y: float
    yaw: float
    def __init__(self, id: _Optional[int] = ..., value: _Optional[_Iterable[bool]] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., yaw: _Optional[float] = ..., step: _Optional[float] = ..., resolution: _Optional[int] = ..., header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., key: _Optional[str] = ...) -> None: ...
