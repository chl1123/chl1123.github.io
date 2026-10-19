from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgCalibStatus(_message.Message):
    __slots__ = ["calibTypeList", "desc", "status"]
    class calibStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CALIBTYPELIST_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    calibTypeList: _containers.RepeatedCompositeFieldContainer[msgCalibType]
    completed: msgCalibStatus.calibStatus
    desc: str
    failed: msgCalibStatus.calibStatus
    none: msgCalibStatus.calibStatus
    running: msgCalibStatus.calibStatus
    status: msgCalibStatus.calibStatus
    waiting: msgCalibStatus.calibStatus
    def __init__(self, status: _Optional[_Union[msgCalibStatus.calibStatus, str]] = ..., desc: _Optional[str] = ..., calibTypeList: _Optional[_Iterable[_Union[msgCalibType, _Mapping]]] = ...) -> None: ...

class msgCalibType(_message.Message):
    __slots__ = ["calibType", "deviceName", "deviceType", "hasPlot", "isAutoCalib", "status"]
    class calibTypeStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CALIBTYPE_FIELD_NUMBER: _ClassVar[int]
    DEVICENAME_FIELD_NUMBER: _ClassVar[int]
    DEVICETYPE_FIELD_NUMBER: _ClassVar[int]
    HASPLOT_FIELD_NUMBER: _ClassVar[int]
    ISAUTOCALIB_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    calibCpChanged: msgCalibType.calibTypeStatus
    calibModelChanged: msgCalibType.calibTypeStatus
    calibNoPass: msgCalibType.calibTypeStatus
    calibPass: msgCalibType.calibTypeStatus
    calibType: str
    deviceName: str
    deviceType: str
    hasPlot: bool
    isAutoCalib: bool
    noCalib: msgCalibType.calibTypeStatus
    status: msgCalibType.calibTypeStatus
    unKnown: msgCalibType.calibTypeStatus
    def __init__(self, calibType: _Optional[str] = ..., deviceType: _Optional[str] = ..., deviceName: _Optional[str] = ..., isAutoCalib: bool = ..., hasPlot: bool = ..., status: _Optional[_Union[msgCalibType.calibTypeStatus, str]] = ...) -> None: ...
