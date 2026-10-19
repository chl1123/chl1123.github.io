import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgRFID(_message.Message):
    __slots__ = ["rfidNodes"]
    RFIDNODES_FIELD_NUMBER: ClassVar[int]
    rfidNodes: _containers.RepeatedCompositeFieldContainer[msgRFIDNode]
    def __init__(self, rfidNodes: Optional[Iterable[Union[msgRFIDNode, Mapping]]] = ...) -> None: ...

class msgRFIDNode(_message.Message):
    __slots__ = ["count", "header", "id", "key", "strength"]
    COUNT_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    STRENGTH_FIELD_NUMBER: ClassVar[int]
    count: int
    header: _message_header_pb2.msgHeader
    id: int
    key: str
    strength: int
    def __init__(self, id: Optional[int] = ..., count: Optional[int] = ..., header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., strength: Optional[int] = ..., key: Optional[str] = ...) -> None: ...
