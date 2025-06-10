from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

import message_header_pb2 as _message_header_pb2

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Magnetic(_message.Message):
    """表示磁相关的消息。

    Attributes:
        magnetic_nodes (typing.List[Message_MagneticNode]): 磁节点列表，存储多个磁节点的信息，默认初始化为空列表。
    """
    __slots__ = ["magnetic_nodes"]
    MAGNETIC_NODES_FIELD_NUMBER: ClassVar[int]
    magnetic_nodes: _containers.RepeatedCompositeFieldContainer[Message_MagneticNode]

    def __init__(self, magnetic_nodes: Optional[Iterable[Union[Message_MagneticNode, Mapping]]] = ...) -> None: ...


class Message_MagneticNode(_message.Message):
    """表示磁节点相关信息。

    Attributes:
        id (int): 节点的标识符，默认值为0。
        value (typing.List[bool]): 布尔值列表，用于存储磁节点的某些状态信息，默认初始化为空列表。
        x (float): 磁节点的x坐标值，默认值为0.0。
        y (float): 磁节点的y坐标值，默认值为0.0。
        yaw (float): 磁节点的偏航角，代表其朝向，默认值为0.0。
        step (float): 磁节点相关的步长，默认值为0.0。
        resolution (int): 磁节点的分辨率，默认值为0。
        header (typing.Optional[Message_Header]): 消息头，包含消息的元数据，可选类型，默认为None。
    """
    __slots__ = ["header", "id", "resolution", "step", "value", "x", "y", "yaw"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    RESOLUTION_FIELD_NUMBER: ClassVar[int]
    STEP_FIELD_NUMBER: ClassVar[int]
    VALUE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.Message_Header
    id: int
    resolution: int
    step: float
    value: _containers.RepeatedScalarFieldContainer[bool]
    x: float
    y: float
    yaw: float

    def __init__(self, id: Optional[int] = ..., value: Optional[Iterable[bool]] = ..., x: Optional[float] = ...,
                 y: Optional[float] = ..., yaw: Optional[float] = ..., step: Optional[float] = ...,
                 resolution: Optional[int] = ...,
                 header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...) -> None: ...
