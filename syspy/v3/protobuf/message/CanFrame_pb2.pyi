from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

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
    ERRORCOUNT_FIELD_NUMBER: ClassVar[int]
    ERRORTYPE_FIELD_NUMBER: ClassVar[int]
    errorcount: int
    errortype: int
    def __init__(self, errortype: Optional[int] = ..., errorcount: Optional[int] = ...) -> None: ...

class CanFrame(_message.Message):
    __slots__ = ["DLC", "ID", "canError", "channel", "data", "direction", "extended", "remote", "timestamp"]
    CANERROR_FIELD_NUMBER: ClassVar[int]
    CHANNEL_FIELD_NUMBER: ClassVar[int]
    DATA_FIELD_NUMBER: ClassVar[int]
    DIRECTION_FIELD_NUMBER: ClassVar[int]
    DLC: int
    DLC_FIELD_NUMBER: ClassVar[int]
    EXTENDED_FIELD_NUMBER: ClassVar[int]
    ID: int
    ID_FIELD_NUMBER: ClassVar[int]
    REMOTE_FIELD_NUMBER: ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: ClassVar[int]
    canError: _containers.RepeatedCompositeFieldContainer[CanErrorRecord]
    channel: int
    data: bytes
    direction: bool
    extended: bool
    remote: bool
    timestamp: int
    def __init__(self, ID: Optional[int] = ..., extended: bool = ..., remote: bool = ..., DLC: Optional[int] = ..., data: Optional[bytes] = ..., channel: Optional[int] = ..., timestamp: Optional[int] = ..., direction: bool = ..., canError: Optional[Iterable[Union[CanErrorRecord, Mapping]]] = ...) -> None: ...

class DIRE_ENUM(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class ERROR_TYPE(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
