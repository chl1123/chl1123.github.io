from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgHeader(_message.Message):
    __slots__ = ["dataNsec", "frameID", "pubNsec", "seq"]
    DATANSEC_FIELD_NUMBER: _ClassVar[int]
    FRAMEID_FIELD_NUMBER: _ClassVar[int]
    PUBNSEC_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    dataNsec: int
    frameID: str
    pubNsec: int
    seq: int
    def __init__(self, pubNsec: _Optional[int] = ..., dataNsec: _Optional[int] = ..., seq: _Optional[int] = ..., frameID: _Optional[str] = ...) -> None: ...
