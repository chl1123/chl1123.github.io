from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

ACKNOWLEDGEMENT_ERROR: ERROR_TYPE
BIT_DOMINANT_ERROR: ERROR_TYPE
BIT_RECESSIVE_ERROR: ERROR_TYPE
CRC_ERROR: ERROR_TYPE
DESCRIPTOR: _descriptor.FileDescriptor
FORM_ERROR: ERROR_TYPE
RX: DIRE_ENUM
STUFF_ERROR: ERROR_TYPE
TX: DIRE_ENUM

class CanErrorRecord(_message.Message):
    __slots__ = ["errorcount", "errortype"]
    ERRORCOUNT_FIELD_NUMBER: _ClassVar[int]
    ERRORTYPE_FIELD_NUMBER: _ClassVar[int]
    errorcount: int
    errortype: int
    def __init__(self, errortype: _Optional[int] = ..., errorcount: _Optional[int] = ...) -> None: ...

class CanFrame(_message.Message):
    __slots__ = ["canError", "channel", "data", "direction", "dlc", "extended", "id", "remote", "timestamp"]
    CANERROR_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    DLC_FIELD_NUMBER: _ClassVar[int]
    EXTENDED_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    REMOTE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    canError: _containers.RepeatedCompositeFieldContainer[CanErrorRecord]
    channel: int
    data: bytes
    direction: bool
    dlc: int
    extended: bool
    id: int
    remote: bool
    timestamp: int
    def __init__(self, id: _Optional[int] = ..., extended: bool = ..., remote: bool = ..., dlc: _Optional[int] = ..., data: _Optional[bytes] = ..., channel: _Optional[int] = ..., timestamp: _Optional[int] = ..., direction: bool = ..., canError: _Optional[_Iterable[_Union[CanErrorRecord, _Mapping]]] = ...) -> None: ...

class DIRE_ENUM(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class ERROR_TYPE(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
