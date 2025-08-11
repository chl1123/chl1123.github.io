from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Message_Sound(_message.Message):
    __slots__ = ["count", "loop", "sound_name", "status"]
    COUNT_FIELD_NUMBER: ClassVar[int]
    LOOP_FIELD_NUMBER: ClassVar[int]
    SOUND_NAME_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    count: int
    loop: bool
    sound_name: str
    status: int
    def __init__(self, status: Optional[int] = ..., sound_name: Optional[str] = ..., loop: bool = ..., count: Optional[int] = ...) -> None: ...
