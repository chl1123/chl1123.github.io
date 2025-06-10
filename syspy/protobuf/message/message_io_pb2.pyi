from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Astern(_message.Message):
    """Astern

    Attributes:
        status (int): 状态值，默认为 0。
    """
    __slots__ = ["status"]
    STATUS_FIELD_NUMBER: ClassVar[int]
    status: int

    def __init__(self, status: Optional[int] = ...) -> None: ...


class Message_DI(_message.Message):
    """
    表示数字输入相关的消息。

    Attributes:
        node (typing.List[Message_DINode]): 数字输入节点的列表，默认为空列表。
        max_node (int): 最大节点数，默认为 0。
    """
    __slots__ = ["max_node", "node"]
    MAX_NODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    max_node: int
    node: _containers.RepeatedCompositeFieldContainer[Message_DINode]

    def __init__(self, node: Optional[Iterable[Union[Message_DINode, Mapping]]] = ...,
                 max_node: Optional[int] = ...) -> None: ...


class Message_DINode(_message.Message):
    """
    表示数字输入节点的相关信息。

    Attributes:
        id (int): 节点的唯一标识符，默认为 0。
        status (bool): 节点的状态，默认为 False。
        x (float): 节点的 x 坐标，默认为 0.0。
        y (float): 节点的 y 坐标，默认为 0.0。
        z (float): 节点的 z 坐标，默认为 0.0。
        yaw (float): 节点的偏航角，默认为 0.0。
        func (str): 节点的功能描述，默认为空字符串。
        type (str): 节点的类型，默认为空字符串。
        source (str): 节点的来源，默认为空字符串。
        shape (str): 节点的形状，默认为空字符串。
        mindist (float): 最小距离，默认为 0.0。
        maxdist (float): 最大距离，默认为 0.0。
        range (float): 范围，默认为 0.0。
        posx (typing.List[float]): x 坐标的列表，默认为空列表。
        posy (typing.List[float]): y 坐标的列表，默认为空列表。
        forbidden (bool): 是否禁止，默认为 False。
    """
    __slots__ = ["forbidden", "func", "id", "maxdist", "mindist", "posx", "posy", "range", "shape", "source", "status",
                 "type", "x", "y", "yaw", "z"]
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

    def __init__(self, id: Optional[int] = ..., status: bool = ..., x: Optional[float] = ..., y: Optional[float] = ...,
                 z: Optional[float] = ..., yaw: Optional[float] = ..., func: Optional[str] = ...,
                 type: Optional[str] = ..., source: Optional[str] = ..., shape: Optional[str] = ...,
                 mindist: Optional[float] = ..., maxdist: Optional[float] = ..., range: Optional[float] = ...,
                 posx: Optional[Iterable[float]] = ..., posy: Optional[Iterable[float]] = ...,
                 forbidden: bool = ...) -> None: ...


class Message_DO(_message.Message):
    """
    表示数字输出相关的消息。

    Attributes:
        node (typing.List[Message_DONode]): 数字输出节点的列表，默认为空列表。
        max_node (int): 最大节点数，默认为 0。
    """
    __slots__ = ["max_node", "node"]
    MAX_NODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    max_node: int
    node: _containers.RepeatedCompositeFieldContainer[Message_DONode]

    def __init__(self, node: Optional[Iterable[Union[Message_DONode, Mapping]]] = ...,
                 max_node: Optional[int] = ...) -> None: ...


class Message_DONode(_message.Message):
    """
    表示数字输出节点的相关信息。

    Attributes:
        id (int): 节点的唯一标识符，默认为 0。
        status (bool): 节点的状态，默认为 False。
        source (str): 节点的来源，默认为空字符串。
        func (str): 节点的功能描述，默认为空字符串。
    """
    __slots__ = ["func", "id", "source", "status"]
    FUNC_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    SOURCE_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    func: str
    id: int
    source: str
    status: bool

    def __init__(self, id: Optional[int] = ..., status: bool = ..., source: Optional[str] = ...,
                 func: Optional[str] = ...) -> None: ...
