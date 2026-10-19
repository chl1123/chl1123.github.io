import message_header_pb2 as _message_header_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgIMU(_message.Message):
    __slots__ = ["accX", "accY", "accZ", "header", "installInfo", "pitch", "qW", "qX", "qY", "qZ", "roll", "rotOffX", "rotOffY", "rotOffZ", "rotX", "rotY", "rotZ", "yaw"]
    ACCX_FIELD_NUMBER: ClassVar[int]
    ACCY_FIELD_NUMBER: ClassVar[int]
    ACCZ_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: ClassVar[int]
    PITCH_FIELD_NUMBER: ClassVar[int]
    QW_FIELD_NUMBER: ClassVar[int]
    QX_FIELD_NUMBER: ClassVar[int]
    QY_FIELD_NUMBER: ClassVar[int]
    QZ_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    ROTOFFX_FIELD_NUMBER: ClassVar[int]
    ROTOFFY_FIELD_NUMBER: ClassVar[int]
    ROTOFFZ_FIELD_NUMBER: ClassVar[int]
    ROTX_FIELD_NUMBER: ClassVar[int]
    ROTY_FIELD_NUMBER: ClassVar[int]
    ROTZ_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., yaw: Optional[float] = ..., roll: Optional[float] = ..., pitch: Optional[float] = ..., accX: Optional[float] = ..., accY: Optional[float] = ..., accZ: Optional[float] = ..., rotX: Optional[float] = ..., rotY: Optional[float] = ..., rotZ: Optional[float] = ..., rotOffX: Optional[int] = ..., rotOffY: Optional[int] = ..., rotOffZ: Optional[int] = ..., qX: Optional[float] = ..., qY: Optional[float] = ..., qZ: Optional[float] = ..., qW: Optional[float] = ..., installInfo: Optional[Union[msgImuInstallInfo, Mapping]] = ...) -> None: ...

class msgImuInstallInfo(_message.Message):
    __slots__ = ["SSF", "qw", "qx", "qy", "qz", "x", "y", "z"]
    QW_FIELD_NUMBER: ClassVar[int]
    QX_FIELD_NUMBER: ClassVar[int]
    QY_FIELD_NUMBER: ClassVar[int]
    QZ_FIELD_NUMBER: ClassVar[int]
    SSF: float
    SSF_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    qw: float
    qx: float
    qy: float
    qz: float
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., qx: Optional[float] = ..., qy: Optional[float] = ..., qz: Optional[float] = ..., qw: Optional[float] = ..., SSF: Optional[float] = ...) -> None: ...
