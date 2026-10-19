from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgScript(_message.Message):
    __slots__ = ["scriptData"]
    class ScriptDataEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: str
        def __init__(self, key: Optional[str] = ..., value: Optional[str] = ...) -> None: ...
    SCRIPTDATA_FIELD_NUMBER: ClassVar[int]
    scriptData: _containers.ScalarMap[str, str]
    def __init__(self, scriptData: Optional[Mapping[str, str]] = ...) -> None: ...

class msgScriptStatus(_message.Message):
    __slots__ = ["res", "status"]
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    Canceled: msgScriptStatus.Status
    Completed: msgScriptStatus.Status
    Failed: msgScriptStatus.Status
    OverTime: msgScriptStatus.Status
    RES_FIELD_NUMBER: ClassVar[int]
    Running: msgScriptStatus.Status
    STATUS_FIELD_NUMBER: ClassVar[int]
    StatusNone: msgScriptStatus.Status
    Suspended: msgScriptStatus.Status
    Waiting: msgScriptStatus.Status
    res: str
    status: msgScriptStatus.Status
    def __init__(self, status: Optional[Union[msgScriptStatus.Status, str]] = ..., res: Optional[str] = ...) -> None: ...
