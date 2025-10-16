from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgSound(_message.Message):
    __slots__ = ["count", "loop", "soundName", "status"]
    COUNT_FIELD_NUMBER: ClassVar[int]
    LOOP_FIELD_NUMBER: ClassVar[int]
    SOUNDNAME_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    count: int
    loop: bool
    soundName: str
    status: int
    def __init__(self, status: Optional[int] = ..., soundName: Optional[str] = ..., loop: bool = ..., count: Optional[int] = ...) -> None: ...
