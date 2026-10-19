from . import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgRFID(_message.Message):
    __slots__ = ["rfidNodes"]
    RFIDNODES_FIELD_NUMBER: _ClassVar[int]
    rfidNodes: _containers.RepeatedCompositeFieldContainer[msgRFIDNode]
    def __init__(self, rfidNodes: _Optional[_Iterable[_Union[msgRFIDNode, _Mapping]]] = ...) -> None: ...

class msgRFIDNode(_message.Message):
    __slots__ = ["count", "header", "id", "key", "strength"]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    STRENGTH_FIELD_NUMBER: _ClassVar[int]
    count: int
    header: _message_header_pb2.msgHeader
    id: int
    key: str
    strength: int
    def __init__(self, id: _Optional[int] = ..., count: _Optional[int] = ..., header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., strength: _Optional[int] = ..., key: _Optional[str] = ...) -> None: ...
