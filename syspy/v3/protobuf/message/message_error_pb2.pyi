from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgConfigError(_message.Message):
    __slots__ = ["appType", "fileName", "param"]
    APPTYPE_FIELD_NUMBER: ClassVar[int]
    FILENAME_FIELD_NUMBER: ClassVar[int]
    PARAM_FIELD_NUMBER: ClassVar[int]
    appType: str
    fileName: str
    param: str
    def __init__(self, fileName: Optional[str] = ..., appType: Optional[str] = ..., param: Optional[str] = ...) -> None: ...

class msgDeviceError(_message.Message):
    __slots__ = ["deviceKey", "deviceType", "errorCode", "fileName", "param"]
    DEVICEKEY_FIELD_NUMBER: ClassVar[int]
    DEVICETYPE_FIELD_NUMBER: ClassVar[int]
    ERRORCODE_FIELD_NUMBER: ClassVar[int]
    FILENAME_FIELD_NUMBER: ClassVar[int]
    PARAM_FIELD_NUMBER: ClassVar[int]
    deviceKey: str
    deviceType: str
    errorCode: int
    fileName: str
    param: str
    def __init__(self, fileName: Optional[str] = ..., deviceType: Optional[str] = ..., deviceKey: Optional[str] = ..., param: Optional[str] = ..., errorCode: Optional[int] = ...) -> None: ...

class msgError(_message.Message):
    __slots__ = ["configError", "desc", "deviceError", "licenseError", "manual", "mapError", "taskError"]
    CONFIGERROR_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    DEVICEERROR_FIELD_NUMBER: ClassVar[int]
    LICENSEERROR_FIELD_NUMBER: ClassVar[int]
    MANUAL_FIELD_NUMBER: ClassVar[int]
    MAPERROR_FIELD_NUMBER: ClassVar[int]
    TASKERROR_FIELD_NUMBER: ClassVar[int]
    configError: msgConfigError
    desc: str
    deviceError: msgDeviceError
    licenseError: msgLicenseError
    manual: bool
    mapError: msgMapError
    taskError: msgTaskError
    def __init__(self, deviceError: Optional[Union[msgDeviceError, Mapping]] = ..., configError: Optional[Union[msgConfigError, Mapping]] = ..., mapError: Optional[Union[msgMapError, Mapping]] = ..., licenseError: Optional[Union[msgLicenseError, Mapping]] = ..., taskError: Optional[Union[msgTaskError, Mapping]] = ..., desc: Optional[str] = ..., manual: bool = ...) -> None: ...

class msgLicenseError(_message.Message):
    __slots__ = ["licenseType"]
    LICENSETYPE_FIELD_NUMBER: ClassVar[int]
    licenseType: str
    def __init__(self, licenseType: Optional[str] = ...) -> None: ...

class msgMapError(_message.Message):
    __slots__ = ["elementName", "elementType", "mapName", "mapType"]
    ELEMENTNAME_FIELD_NUMBER: ClassVar[int]
    ELEMENTTYPE_FIELD_NUMBER: ClassVar[int]
    MAPNAME_FIELD_NUMBER: ClassVar[int]
    MAPTYPE_FIELD_NUMBER: ClassVar[int]
    elementName: str
    elementType: str
    mapName: str
    mapType: str
    def __init__(self, mapType: Optional[str] = ..., mapName: Optional[str] = ..., elementType: Optional[str] = ..., elementName: Optional[str] = ...) -> None: ...

class msgSystemStatus(_message.Message):
    __slots__ = ["errors", "status"]
    class systemStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: msgError
        def __init__(self, key: Optional[str] = ..., value: Optional[Union[msgError, Mapping]] = ...) -> None: ...
    ERRORS_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    crashed: msgSystemStatus.systemStatus
    error: msgSystemStatus.systemStatus
    errors: _containers.MessageMap[str, msgError]
    running: msgSystemStatus.systemStatus
    starting: msgSystemStatus.systemStatus
    status: msgSystemStatus.systemStatus
    def __init__(self, status: Optional[Union[msgSystemStatus.systemStatus, str]] = ..., errors: Optional[Mapping[str, msgError]] = ...) -> None: ...

class msgTaskError(_message.Message):
    __slots__ = ["task"]
    TASK_FIELD_NUMBER: ClassVar[int]
    task: str
    def __init__(self, task: Optional[str] = ...) -> None: ...
