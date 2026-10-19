import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgBin(_message.Message):
    __slots__ = ["binId", "binStatus", "filled"]
    class status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    BINID_FIELD_NUMBER: ClassVar[int]
    BINSTATUS_FIELD_NUMBER: ClassVar[int]
    FILLED_FIELD_NUMBER: ClassVar[int]
    binId: str
    binStatus: msgBin.status
    connect: msgBin.status
    disConnect: msgBin.status
    filled: bool
    def __init__(self, binId: Optional[str] = ..., filled: bool = ..., binStatus: Optional[Union[msgBin.status, str]] = ...) -> None: ...

class msgBins(_message.Message):
    __slots__ = ["bins", "header"]
    BINS_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    bins: _containers.RepeatedCompositeFieldContainer[msgBin]
    header: _message_header_pb2.msgHeader
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., bins: Optional[Iterable[Union[msgBin, Mapping]]] = ...) -> None: ...
