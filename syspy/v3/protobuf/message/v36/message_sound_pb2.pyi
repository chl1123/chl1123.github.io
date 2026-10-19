from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgSound(_message.Message):
    __slots__ = ["count", "loop", "soundName", "status", "volume"]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    LOOP_FIELD_NUMBER: _ClassVar[int]
    SOUNDNAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    count: int
    loop: bool
    soundName: str
    status: int
    volume: int
    def __init__(self, status: _Optional[int] = ..., soundName: _Optional[str] = ..., loop: bool = ..., count: _Optional[int] = ..., volume: _Optional[int] = ...) -> None: ...
