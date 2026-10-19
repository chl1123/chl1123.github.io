from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

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
    MAXNODE_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    maxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgDINode]
    def __init__(self, node: _Optional[_Iterable[_Union[msgDINode, _Mapping]]] = ..., maxNode: _Optional[int] = ...) -> None: ...

class msgDINode(_message.Message):
    __slots__ = ["forbidden", "id", "ioType", "key", "maxDist", "minDist", "posX", "posY", "range", "shape", "status", "type", "x", "y", "yaw", "z"]
    FORBIDDEN_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    IOTYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    MAXDIST_FIELD_NUMBER: _ClassVar[int]
    MINDIST_FIELD_NUMBER: _ClassVar[int]
    POSX_FIELD_NUMBER: _ClassVar[int]
    POSY_FIELD_NUMBER: _ClassVar[int]
    RANGE_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, id: _Optional[int] = ..., status: bool = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., yaw: _Optional[float] = ..., ioType: _Optional[_Union[IOType, str]] = ..., type: _Optional[str] = ..., shape: _Optional[str] = ..., minDist: _Optional[float] = ..., maxDist: _Optional[float] = ..., range: _Optional[float] = ..., posX: _Optional[_Iterable[float]] = ..., posY: _Optional[_Iterable[float]] = ..., forbidden: bool = ..., key: _Optional[str] = ...) -> None: ...

class msgDO(_message.Message):
    __slots__ = ["maxNode", "node"]
    MAXNODE_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    maxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgDONode]
    def __init__(self, node: _Optional[_Iterable[_Union[msgDONode, _Mapping]]] = ..., maxNode: _Optional[int] = ...) -> None: ...

class msgDONode(_message.Message):
    __slots__ = ["id", "ioType", "key", "lock", "status"]
    ID_FIELD_NUMBER: _ClassVar[int]
    IOTYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    LOCK_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    id: int
    ioType: IOType
    key: str
    lock: bool
    status: bool
    def __init__(self, id: _Optional[int] = ..., status: bool = ..., ioType: _Optional[_Union[IOType, str]] = ..., lock: bool = ..., key: _Optional[str] = ...) -> None: ...

class msgIOConfig(_message.Message):
    __slots__ = ["node"]
    NODE_FIELD_NUMBER: _ClassVar[int]
    node: _containers.RepeatedCompositeFieldContainer[msgIOConfigNode]
    def __init__(self, node: _Optional[_Iterable[_Union[msgIOConfigNode, _Mapping]]] = ...) -> None: ...

class msgIOConfigNode(_message.Message):
    __slots__ = ["dir", "ioType", "maxNode", "pair"]
    DIR_FIELD_NUMBER: _ClassVar[int]
    IOTYPE_FIELD_NUMBER: _ClassVar[int]
    MAXNODE_FIELD_NUMBER: _ClassVar[int]
    PAIR_FIELD_NUMBER: _ClassVar[int]
    dir: IODir
    ioType: IOType
    maxNode: int
    pair: _containers.RepeatedCompositeFieldContainer[msgIOPair]
    def __init__(self, dir: _Optional[_Union[IODir, str]] = ..., ioType: _Optional[_Union[IOType, str]] = ..., maxNode: _Optional[int] = ..., pair: _Optional[_Iterable[_Union[msgIOPair, _Mapping]]] = ...) -> None: ...

class msgIOPair(_message.Message):
    __slots__ = ["first", "second"]
    FIRST_FIELD_NUMBER: _ClassVar[int]
    SECOND_FIELD_NUMBER: _ClassVar[int]
    first: int
    second: int
    def __init__(self, first: _Optional[int] = ..., second: _Optional[int] = ...) -> None: ...

class IOType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class IODir(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
