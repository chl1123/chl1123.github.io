from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Message_Header(_message.Message):
    __slots__ = ["data_nsec", "frame_id", "pub_nsec", "seq"]
    DATA_NSEC_FIELD_NUMBER: ClassVar[int]
    FRAME_ID_FIELD_NUMBER: ClassVar[int]
    PUB_NSEC_FIELD_NUMBER: ClassVar[int]
    SEQ_FIELD_NUMBER: ClassVar[int]
    data_nsec: int
    frame_id: str
    pub_nsec: int
    seq: int
    def __init__(self, pub_nsec: Optional[int] = ..., data_nsec: Optional[int] = ..., seq: Optional[int] = ..., frame_id: Optional[str] = ...) -> None: ...
