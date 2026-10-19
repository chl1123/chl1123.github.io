from . import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgBin(_message.Message):
    __slots__ = ["binId", "binStatus", "filled"]
    class status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    BINID_FIELD_NUMBER: _ClassVar[int]
    BINSTATUS_FIELD_NUMBER: _ClassVar[int]
    FILLED_FIELD_NUMBER: _ClassVar[int]
    binId: str
    binStatus: msgBin.status
    connect: msgBin.status
    disConnect: msgBin.status
    filled: bool
    def __init__(self, binId: _Optional[str] = ..., filled: bool = ..., binStatus: _Optional[_Union[msgBin.status, str]] = ...) -> None: ...

class msgBins(_message.Message):
    __slots__ = ["bins", "header"]
    BINS_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    bins: _containers.RepeatedCompositeFieldContainer[msgBin]
    header: _message_header_pb2.msgHeader
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., bins: _Optional[_Iterable[_Union[msgBin, _Mapping]]] = ...) -> None: ...
