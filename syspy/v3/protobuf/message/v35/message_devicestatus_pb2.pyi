import message_header_pb2 as _message_header_pb2
import message_error_pb2 as _message_error_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgDeviceStatus(_message.Message):
    __slots__ = ["deviceStatus", "header"]
    class DeviceStatusEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: msgDeviceStatusNode
        def __init__(self, key: Optional[str] = ..., value: Optional[Union[msgDeviceStatusNode, Mapping]] = ...) -> None: ...
    DEVICESTATUS_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    deviceStatus: _containers.MessageMap[str, msgDeviceStatusNode]
    header: _message_header_pb2.msgHeader
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., deviceStatus: Optional[Mapping[str, msgDeviceStatusNode]] = ...) -> None: ...

class msgDeviceStatusNode(_message.Message):
    __slots__ = ["errors", "header", "statusCategory"]
    class StatusCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: Optional[str] = ..., value: Optional[Union[_message_error_pb2.msgError, Mapping]] = ...) -> None: ...
    CONNECT_ERROR: msgDeviceStatusNode.StatusCategory
    DATA_ERROR: msgDeviceStatusNode.StatusCategory
    DEVICE_ERROR: msgDeviceStatusNode.StatusCategory
    ERRORS_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INIT: msgDeviceStatusNode.StatusCategory
    RUNNING: msgDeviceStatusNode.StatusCategory
    STATUSCATEGORY_FIELD_NUMBER: ClassVar[int]
    errors: _containers.MessageMap[str, _message_error_pb2.msgError]
    header: _message_header_pb2.msgHeader
    statusCategory: msgDeviceStatusNode.StatusCategory
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., statusCategory: Optional[Union[msgDeviceStatusNode.StatusCategory, str]] = ..., errors: Optional[Mapping[str, _message_error_pb2.msgError]] = ...) -> None: ...
