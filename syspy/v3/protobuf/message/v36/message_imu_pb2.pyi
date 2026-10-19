from . import message_header_pb2 as _message_header_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgIMU(_message.Message):
    __slots__ = ["accX", "accY", "accZ", "header", "installInfo", "pitch", "qW", "qX", "qY", "qZ", "roll", "rotOffX", "rotOffY", "rotOffZ", "rotX", "rotY", "rotZ", "yaw"]
    ACCX_FIELD_NUMBER: _ClassVar[int]
    ACCY_FIELD_NUMBER: _ClassVar[int]
    ACCZ_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: _ClassVar[int]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    QW_FIELD_NUMBER: _ClassVar[int]
    QX_FIELD_NUMBER: _ClassVar[int]
    QY_FIELD_NUMBER: _ClassVar[int]
    QZ_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    ROTOFFX_FIELD_NUMBER: _ClassVar[int]
    ROTOFFY_FIELD_NUMBER: _ClassVar[int]
    ROTOFFZ_FIELD_NUMBER: _ClassVar[int]
    ROTX_FIELD_NUMBER: _ClassVar[int]
    ROTY_FIELD_NUMBER: _ClassVar[int]
    ROTZ_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    accX: float
    accY: float
    accZ: float
    header: _message_header_pb2.msgHeader
    installInfo: msgImuInstallInfo
    pitch: float
    qW: float
    qX: float
    qY: float
    qZ: float
    roll: float
    rotOffX: int
    rotOffY: int
    rotOffZ: int
    rotX: float
    rotY: float
    rotZ: float
    yaw: float
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., yaw: _Optional[float] = ..., roll: _Optional[float] = ..., pitch: _Optional[float] = ..., accX: _Optional[float] = ..., accY: _Optional[float] = ..., accZ: _Optional[float] = ..., rotX: _Optional[float] = ..., rotY: _Optional[float] = ..., rotZ: _Optional[float] = ..., rotOffX: _Optional[int] = ..., rotOffY: _Optional[int] = ..., rotOffZ: _Optional[int] = ..., qX: _Optional[float] = ..., qY: _Optional[float] = ..., qZ: _Optional[float] = ..., qW: _Optional[float] = ..., installInfo: _Optional[_Union[msgImuInstallInfo, _Mapping]] = ...) -> None: ...

class msgImuInstallInfo(_message.Message):
    __slots__ = ["SSF", "qw", "qx", "qy", "qz", "x", "y", "z"]
    QW_FIELD_NUMBER: _ClassVar[int]
    QX_FIELD_NUMBER: _ClassVar[int]
    QY_FIELD_NUMBER: _ClassVar[int]
    QZ_FIELD_NUMBER: _ClassVar[int]
    SSF: float
    SSF_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    qw: float
    qx: float
    qy: float
    qz: float
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., qx: _Optional[float] = ..., qy: _Optional[float] = ..., qz: _Optional[float] = ..., qw: _Optional[float] = ..., SSF: _Optional[float] = ...) -> None: ...
