from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgHeader(_message.Message):
    __slots__ = ["dataNsec", "frameID", "pubNsec", "seq"]
    DATANSEC_FIELD_NUMBER: ClassVar[int]
    FRAMEID_FIELD_NUMBER: ClassVar[int]
    PUBNSEC_FIELD_NUMBER: ClassVar[int]
    SEQ_FIELD_NUMBER: ClassVar[int]
    dataNsec: int
    frameID: str
    pubNsec: int
    seq: int
    def __init__(self, pubNsec: Optional[int] = ..., dataNsec: Optional[int] = ..., seq: Optional[int] = ..., frameID: Optional[str] = ...) -> None: ...
