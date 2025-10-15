from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgCalibStatus(_message.Message):
    __slots__ = ["desc", "status"]
    class calibStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    DESC_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    completed: msgCalibStatus.calibStatus
    desc: str
    failed: msgCalibStatus.calibStatus
    none: msgCalibStatus.calibStatus
    running: msgCalibStatus.calibStatus
    status: msgCalibStatus.calibStatus
    def __init__(self, status: Optional[Union[msgCalibStatus.calibStatus, str]] = ..., desc: Optional[str] = ...) -> None: ...
