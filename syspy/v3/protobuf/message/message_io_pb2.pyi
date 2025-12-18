from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

CANOpenSafty: IOType
DESCRIPTOR: _descriptor.FileDescriptor
DI: IODir
DO: IODir
EtherCAT: IOType
FSoE: IOType
Modbus: IOType
Normal: IOType
SaftyIO: IOType
Virtual: IOType

class msgDI(_message.Message):
    __slots__ = ["maxNode", "node"]
    MAXNODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    maxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgDINode]
    def __init__(self, node: Optional[Iterable[Union[msgDINode, Mapping]]] = ..., maxNode: Optional[int] = ...) -> None: ...

class msgDINode(_message.Message):
    __slots__ = ["forbidden", "id", "ioType", "key", "maxDist", "minDist", "posX", "posY", "range", "shape", "status", "type", "x", "y", "yaw", "z"]
    FORBIDDEN_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    IOTYPE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    MAXDIST_FIELD_NUMBER: ClassVar[int]
    MINDIST_FIELD_NUMBER: ClassVar[int]
    POSX_FIELD_NUMBER: ClassVar[int]
    POSY_FIELD_NUMBER: ClassVar[int]
    RANGE_FIELD_NUMBER: ClassVar[int]
    SHAPE_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    forbidden: bool
    id: int
    ioType: IOType
    key: str
    maxDist: float
    minDist: float
    posX: _containers.RepeatedScalarFieldContainer[float]
    posY: _containers.RepeatedScalarFieldContainer[float]
    range: float
    shape: str
    status: bool
    type: str
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, id: Optional[int] = ..., status: bool = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., yaw: Optional[float] = ..., ioType: Optional[Union[IOType, str]] = ..., type: Optional[str] = ..., shape: Optional[str] = ..., minDist: Optional[float] = ..., maxDist: Optional[float] = ..., range: Optional[float] = ..., posX: Optional[Iterable[float]] = ..., posY: Optional[Iterable[float]] = ..., forbidden: bool = ..., key: Optional[str] = ...) -> None: ...

class msgDO(_message.Message):
    __slots__ = ["maxNode", "node"]
    MAXNODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    maxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgDONode]
    def __init__(self, node: Optional[Iterable[Union[msgDONode, Mapping]]] = ..., maxNode: Optional[int] = ...) -> None: ...

class msgDONode(_message.Message):
    __slots__ = ["id", "ioType", "key", "lock", "status"]
    ID_FIELD_NUMBER: ClassVar[int]
    IOTYPE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    LOCK_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    id: int
    ioType: IOType
    key: str
    lock: bool
    status: bool
    def __init__(self, id: Optional[int] = ..., status: bool = ..., ioType: Optional[Union[IOType, str]] = ..., lock: bool = ..., key: Optional[str] = ...) -> None: ...

class msgIOConfig(_message.Message):
    __slots__ = ["node"]
    NODE_FIELD_NUMBER: ClassVar[int]
    node: _containers.RepeatedCompositeFieldContainer[msgIOConfigNode]
    def __init__(self, node: Optional[Iterable[Union[msgIOConfigNode, Mapping]]] = ...) -> None: ...

class msgIOConfigNode(_message.Message):
    __slots__ = ["dir", "ioType", "maxNode", "pair"]
    DIR_FIELD_NUMBER: ClassVar[int]
    IOTYPE_FIELD_NUMBER: ClassVar[int]
    MAXNODE_FIELD_NUMBER: ClassVar[int]
    PAIR_FIELD_NUMBER: ClassVar[int]
    dir: IODir
    ioType: IOType
    maxNode: int
    pair: _containers.RepeatedCompositeFieldContainer[msgIOPair]
    def __init__(self, dir: Optional[Union[IODir, str]] = ..., ioType: Optional[Union[IOType, str]] = ..., maxNode: Optional[int] = ..., pair: Optional[Iterable[Union[msgIOPair, Mapping]]] = ...) -> None: ...

class msgIOPair(_message.Message):
    __slots__ = ["first", "second"]
    FIRST_FIELD_NUMBER: ClassVar[int]
    SECOND_FIELD_NUMBER: ClassVar[int]
    first: int
    second: int
    def __init__(self, first: Optional[int] = ..., second: Optional[int] = ...) -> None: ...

class IOType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class IODir(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
