import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_Bin(_message.Message):
    __slots__ = ["binId", "filled", "status"]
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    BINID_FIELD_NUMBER: ClassVar[int]
    Connect: Message_Bin.Status
    DisConnect: Message_Bin.Status
    FILLED_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    binId: str
    filled: bool
    status: Message_Bin.Status
    def __init__(self, binId: Optional[str] = ..., filled: bool = ..., status: Optional[Union[Message_Bin.Status, str]] = ...) -> None: ...

class Message_Bins(_message.Message):
    __slots__ = ["bins", "header"]
    BINS_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    bins: _containers.RepeatedCompositeFieldContainer[Message_Bin]
    header: _message_header_pb2.Message_Header
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., bins: Optional[Iterable[Union[Message_Bin, Mapping]]] = ...) -> None: ...
