import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgMagnetic(_message.Message):
    __slots__ = ["magneticNodes"]
    MAGNETICNODES_FIELD_NUMBER: ClassVar[int]
    magneticNodes: _containers.RepeatedCompositeFieldContainer[msgMagneticNode]
    def __init__(self, magneticNodes: Optional[Iterable[Union[msgMagneticNode, Mapping]]] = ...) -> None: ...

class msgMagneticNode(_message.Message):
    __slots__ = ["header", "id", "resolution", "step", "value", "x", "y", "yaw"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    RESOLUTION_FIELD_NUMBER: ClassVar[int]
    STEP_FIELD_NUMBER: ClassVar[int]
    VALUE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    id: int
    resolution: int
    step: float
    value: _containers.RepeatedScalarFieldContainer[bool]
    x: float
    y: float
    yaw: float
    def __init__(self, id: Optional[int] = ..., value: Optional[Iterable[bool]] = ..., x: Optional[float] = ..., y: Optional[float] = ..., yaw: Optional[float] = ..., step: Optional[float] = ..., resolution: Optional[int] = ..., header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ...) -> None: ...
