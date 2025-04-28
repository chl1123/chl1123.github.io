from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_Astern(_message.Message):
    __slots__ = ["status"]
    STATUS_FIELD_NUMBER: ClassVar[int]
    status: int
    def __init__(self, status: Optional[int] = ...) -> None: ...

class Message_DI(_message.Message):
    __slots__ = ["max_node", "node"]
    MAX_NODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    max_node: int
    node: _containers.RepeatedCompositeFieldContainer[Message_DINode]
    def __init__(self, node: Optional[Iterable[Union[Message_DINode, Mapping]]] = ..., max_node: Optional[int] = ...) -> None: ...

class Message_DINode(_message.Message):
    __slots__ = ["forbidden", "func", "id", "maxdist", "mindist", "posx", "posy", "range", "shape", "source", "status", "type", "x", "y", "yaw", "z"]
    FORBIDDEN_FIELD_NUMBER: ClassVar[int]
    FUNC_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    MAXDIST_FIELD_NUMBER: ClassVar[int]
    MINDIST_FIELD_NUMBER: ClassVar[int]
    POSX_FIELD_NUMBER: ClassVar[int]
    POSY_FIELD_NUMBER: ClassVar[int]
    RANGE_FIELD_NUMBER: ClassVar[int]
    SHAPE_FIELD_NUMBER: ClassVar[int]
    SOURCE_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    forbidden: bool
    func: str
    id: int
    maxdist: float
    mindist: float
    posx: _containers.RepeatedScalarFieldContainer[float]
    posy: _containers.RepeatedScalarFieldContainer[float]
    range: float
    shape: str
    source: str
    status: bool
    type: str
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, id: Optional[int] = ..., status: bool = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., yaw: Optional[float] = ..., func: Optional[str] = ..., type: Optional[str] = ..., source: Optional[str] = ..., shape: Optional[str] = ..., mindist: Optional[float] = ..., maxdist: Optional[float] = ..., range: Optional[float] = ..., posx: Optional[Iterable[float]] = ..., posy: Optional[Iterable[float]] = ..., forbidden: bool = ...) -> None: ...

class Message_DO(_message.Message):
    __slots__ = ["max_node", "node"]
    MAX_NODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    max_node: int
    node: _containers.RepeatedCompositeFieldContainer[Message_DONode]
    def __init__(self, node: Optional[Iterable[Union[Message_DONode, Mapping]]] = ..., max_node: Optional[int] = ...) -> None: ...

class Message_DONode(_message.Message):
    __slots__ = ["func", "id", "source", "status"]
    FUNC_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    SOURCE_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    func: str
    id: int
    source: str
    status: bool
    def __init__(self, id: Optional[int] = ..., status: bool = ..., source: Optional[str] = ..., func: Optional[str] = ...) -> None: ...
