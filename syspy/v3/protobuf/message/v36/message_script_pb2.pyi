from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgScript(_message.Message):
    __slots__ = ["scriptData"]
    class ScriptDataEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SCRIPTDATA_FIELD_NUMBER: _ClassVar[int]
    scriptData: _containers.ScalarMap[str, str]
    def __init__(self, scriptData: _Optional[_Mapping[str, str]] = ...) -> None: ...

class msgScriptStatus(_message.Message):
    __slots__ = ["res", "status"]
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    Canceled: msgScriptStatus.Status
    Completed: msgScriptStatus.Status
    Failed: msgScriptStatus.Status
    OverTime: msgScriptStatus.Status
    RES_FIELD_NUMBER: _ClassVar[int]
    Running: msgScriptStatus.Status
    STATUS_FIELD_NUMBER: _ClassVar[int]
    StatusNone: msgScriptStatus.Status
    Suspended: msgScriptStatus.Status
    Waiting: msgScriptStatus.Status
    res: str
    status: msgScriptStatus.Status
    def __init__(self, status: _Optional[_Union[msgScriptStatus.Status, str]] = ..., res: _Optional[str] = ...) -> None: ...
