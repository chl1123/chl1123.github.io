from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

import message_header_pb2 as _message_header_pb2

DESCRIPTOR: _descriptor.FileDescriptor


class Message_RFID(_message.Message):
    """表示多个RFID节点信息集合的模型类。

    Attributes:
        rfid_nodes (typing.List[Message_RFIDNode]): RFID节点信息列表，存储多个RFID节点的信息，默认初始化为空列表。
    """
    __slots__ = ["rfid_nodes"]
    RFID_NODES_FIELD_NUMBER: ClassVar[int]
    rfid_nodes: _containers.RepeatedCompositeFieldContainer[Message_RFIDNode]

    def __init__(self, rfid_nodes: Optional[Iterable[Union[Message_RFIDNode, Mapping]]] = ...) -> None: ...


class Message_RFIDNode(_message.Message):
    """表示RFID节点信息的模型类。

    Attributes:
        id (int): RFID节点的ID，默认值为0。
        count (int): RFID节点的计数，默认值为0。
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认为None，包含消息的元数据。
        strength (int): RFID信号强度，默认值为0。
    """
    __slots__ = ["count", "header", "id", "strength"]
    COUNT_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    STRENGTH_FIELD_NUMBER: ClassVar[int]
    count: int
    header: _message_header_pb2.Message_Header
    id: int
    strength: int

    def __init__(self, id: Optional[int] = ..., count: Optional[int] = ...,
                 header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 strength: Optional[int] = ...) -> None: ...
