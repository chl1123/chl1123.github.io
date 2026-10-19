from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgConfigError(_message.Message):
    __slots__ = ["appType", "fileName", "param"]
    APPTYPE_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    PARAM_FIELD_NUMBER: _ClassVar[int]
    appType: str
    fileName: str
    param: str
    def __init__(self, fileName: _Optional[str] = ..., appType: _Optional[str] = ..., param: _Optional[str] = ...) -> None: ...

class msgDeviceError(_message.Message):
    __slots__ = ["deviceKey", "deviceType", "errorCode", "fileName", "param"]
    DEVICEKEY_FIELD_NUMBER: _ClassVar[int]
    DEVICETYPE_FIELD_NUMBER: _ClassVar[int]
    ERRORCODE_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    PARAM_FIELD_NUMBER: _ClassVar[int]
    deviceKey: str
    deviceType: str
    errorCode: int
    fileName: str
    param: str
    def __init__(self, fileName: _Optional[str] = ..., deviceType: _Optional[str] = ..., deviceKey: _Optional[str] = ..., param: _Optional[str] = ..., errorCode: _Optional[int] = ...) -> None: ...

class msgError(_message.Message):
    __slots__ = ["configError", "desc", "deviceError", "licenseError", "manual", "mapError", "taskError", "timeStamp"]
    CONFIGERROR_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    DEVICEERROR_FIELD_NUMBER: _ClassVar[int]
    LICENSEERROR_FIELD_NUMBER: _ClassVar[int]
    MANUAL_FIELD_NUMBER: _ClassVar[int]
    MAPERROR_FIELD_NUMBER: _ClassVar[int]
    TASKERROR_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    configError: msgConfigError
    desc: str
    deviceError: msgDeviceError
    licenseError: msgLicenseError
    manual: bool
    mapError: msgMapError
    taskError: msgTaskError
    timeStamp: int
    def __init__(self, deviceError: _Optional[_Union[msgDeviceError, _Mapping]] = ..., configError: _Optional[_Union[msgConfigError, _Mapping]] = ..., mapError: _Optional[_Union[msgMapError, _Mapping]] = ..., licenseError: _Optional[_Union[msgLicenseError, _Mapping]] = ..., taskError: _Optional[_Union[msgTaskError, _Mapping]] = ..., desc: _Optional[str] = ..., manual: bool = ..., timeStamp: _Optional[int] = ...) -> None: ...

class msgLicenseError(_message.Message):
    __slots__ = ["licenseType"]
    LICENSETYPE_FIELD_NUMBER: _ClassVar[int]
    licenseType: str
    def __init__(self, licenseType: _Optional[str] = ...) -> None: ...

class msgMapError(_message.Message):
    __slots__ = ["elementName", "elementType", "mapName", "mapType"]
    ELEMENTNAME_FIELD_NUMBER: _ClassVar[int]
    ELEMENTTYPE_FIELD_NUMBER: _ClassVar[int]
    MAPNAME_FIELD_NUMBER: _ClassVar[int]
    MAPTYPE_FIELD_NUMBER: _ClassVar[int]
    elementName: str
    elementType: str
    mapName: str
    mapType: str
    def __init__(self, mapType: _Optional[str] = ..., mapName: _Optional[str] = ..., elementType: _Optional[str] = ..., elementName: _Optional[str] = ...) -> None: ...

class msgSystemStatus(_message.Message):
    __slots__ = ["errors", "status"]
    class systemStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: msgError
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[msgError, _Mapping]] = ...) -> None: ...
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    crashed: msgSystemStatus.systemStatus
    error: msgSystemStatus.systemStatus
    errors: _containers.MessageMap[str, msgError]
    running: msgSystemStatus.systemStatus
    starting: msgSystemStatus.systemStatus
    status: msgSystemStatus.systemStatus
    def __init__(self, status: _Optional[_Union[msgSystemStatus.systemStatus, str]] = ..., errors: _Optional[_Mapping[str, msgError]] = ...) -> None: ...

class msgTaskError(_message.Message):
    __slots__ = ["task"]
    TASK_FIELD_NUMBER: _ClassVar[int]
    task: str
    def __init__(self, task: _Optional[str] = ...) -> None: ...
