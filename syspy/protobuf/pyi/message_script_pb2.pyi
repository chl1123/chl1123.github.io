from typing import ClassVar, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Script(_message.Message):
    """存储所有脚本的消息

    Attributes:
        script_data: (dict) key是脚本名称或标识，value是用户自定义的 JSON 数据
    """
    __slots__ = ["script_data"]

    class ScriptDataEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: str

        def __init__(self, key: Optional[str] = ..., value: Optional[str] = ...) -> None: ...

    SCRIPT_DATA_FIELD_NUMBER: ClassVar[int]
    script_data: _containers.ScalarMap[str, str]

    def __init__(self, script_data: Optional[Mapping[str, str]] = ...) -> None: ...


class Message_ScriptStatus(_message.Message):
    __slots__ = ["res", "status"]

    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    Canceled: Message_ScriptStatus.Status
    Completed: Message_ScriptStatus.Status
    Failed: Message_ScriptStatus.Status
    OverTime: Message_ScriptStatus.Status
    RES_FIELD_NUMBER: ClassVar[int]
    Running: Message_ScriptStatus.Status
    STATUS_FIELD_NUMBER: ClassVar[int]
    StatusNone: Message_ScriptStatus.Status
    Suspended: Message_ScriptStatus.Status
    Waiting: Message_ScriptStatus.Status
    res: str
    status: Message_ScriptStatus.Status

    def __init__(self, status: Optional[Union[Message_ScriptStatus.Status, str]] = ...,
                 res: Optional[str] = ...) -> None: ...
