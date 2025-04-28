import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_RFID(_message.Message):
    __slots__ = ["rfid_nodes"]
    RFID_NODES_FIELD_NUMBER: ClassVar[int]
    rfid_nodes: _containers.RepeatedCompositeFieldContainer[Message_RFIDNode]
    def __init__(self, rfid_nodes: Optional[Iterable[Union[Message_RFIDNode, Mapping]]] = ...) -> None: ...

class Message_RFIDNode(_message.Message):
    __slots__ = ["count", "header", "id", "strength"]
    COUNT_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    STRENGTH_FIELD_NUMBER: ClassVar[int]
    count: int
    header: _message_header_pb2.Message_Header
    id: int
    strength: int
    def __init__(self, id: Optional[int] = ..., count: Optional[int] = ..., header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., strength: Optional[int] = ...) -> None: ...
