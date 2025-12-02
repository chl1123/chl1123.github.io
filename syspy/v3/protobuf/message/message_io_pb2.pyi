from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgDI(_message.Message):
    __slots__ = ["maxNode", "node"]
    MAXNODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    maxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgDINode]
    def __init__(self, node: Optional[Iterable[Union[msgDINode, Mapping]]] = ..., maxNode: Optional[int] = ...) -> None: ...

class msgDINode(_message.Message):
    __slots__ = ["forbidden", "func", "id", "key", "maxDist", "minDist", "posX", "posY", "range", "shape", "source", "status", "type", "x", "y", "yaw", "z"]
    FORBIDDEN_FIELD_NUMBER: ClassVar[int]
    FUNC_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
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
    key: str
    maxDist: float
    minDist: float
    posX: _containers.RepeatedScalarFieldContainer[float]
    posY: _containers.RepeatedScalarFieldContainer[float]
    range: float
    shape: str
    source: str
    status: bool
    type: str
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, id: Optional[int] = ..., status: bool = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., yaw: Optional[float] = ..., func: Optional[str] = ..., type: Optional[str] = ..., source: Optional[str] = ..., shape: Optional[str] = ..., minDist: Optional[float] = ..., maxDist: Optional[float] = ..., range: Optional[float] = ..., posX: Optional[Iterable[float]] = ..., posY: Optional[Iterable[float]] = ..., forbidden: bool = ..., key: Optional[str] = ...) -> None: ...

class msgDO(_message.Message):
    __slots__ = ["maxNode", "node"]
    MAXNODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    maxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgDONode]
    def __init__(self, node: Optional[Iterable[Union[msgDONode, Mapping]]] = ..., maxNode: Optional[int] = ...) -> None: ...

class msgDONode(_message.Message):
    __slots__ = ["id", "key", "lock", "source", "status"]
    ID_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    LOCK_FIELD_NUMBER: ClassVar[int]
    SOURCE_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    id: int
    key: str
    lock: bool
    source: str
    status: bool
    def __init__(self, id: Optional[int] = ..., status: bool = ..., source: Optional[str] = ..., lock: bool = ..., key: Optional[str] = ...) -> None: ...
