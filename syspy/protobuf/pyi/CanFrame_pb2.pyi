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
    __slots__ = ["Errorcount", "Errortype"]
    ERRORCOUNT_FIELD_NUMBER: ClassVar[int]
    ERRORTYPE_FIELD_NUMBER: ClassVar[int]
    Errorcount: int
    Errortype: int
    def __init__(self, Errortype: Optional[int] = ..., Errorcount: Optional[int] = ...) -> None: ...

class CanFrame(_message.Message):
    __slots__ = ["Canerror", "Channel", "DLC", "Data", "Direction", "Extended", "ID", "Remote", "Timestamp"]
    CANERROR_FIELD_NUMBER: ClassVar[int]
    CHANNEL_FIELD_NUMBER: ClassVar[int]
    Canerror: _containers.RepeatedCompositeFieldContainer[CanErrorRecord]
    Channel: int
    DATA_FIELD_NUMBER: ClassVar[int]
    DIRECTION_FIELD_NUMBER: ClassVar[int]
    DLC: int
    DLC_FIELD_NUMBER: ClassVar[int]
    Data: bytes
    Direction: bool
    EXTENDED_FIELD_NUMBER: ClassVar[int]
    Extended: bool
    ID: int
    ID_FIELD_NUMBER: ClassVar[int]
    REMOTE_FIELD_NUMBER: ClassVar[int]
    Remote: bool
    TIMESTAMP_FIELD_NUMBER: ClassVar[int]
    Timestamp: int
    def __init__(self, ID: Optional[int] = ..., Extended: bool = ..., Remote: bool = ..., DLC: Optional[int] = ..., Data: Optional[bytes] = ..., Channel: Optional[int] = ..., Timestamp: Optional[int] = ..., Direction: bool = ..., Canerror: Optional[Iterable[Union[CanErrorRecord, Mapping]]] = ...) -> None: ...

class DIRE_ENUM(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class ERROR_TYPE(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
