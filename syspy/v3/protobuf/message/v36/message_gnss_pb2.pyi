from . import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgAllGnss(_message.Message):
    __slots__ = ["gnss"]
    GNSS_FIELD_NUMBER: _ClassVar[int]
    gnss: _containers.RepeatedCompositeFieldContainer[msgGnss]
    def __init__(self, gnss: _Optional[_Iterable[_Union[msgGnss, _Mapping]]] = ...) -> None: ...

class msgGnss(_message.Message):
    __slots__ = ["altitude", "enuX", "enuY", "header", "heading", "headingAcc", "installInfo", "latitude", "longitude", "refInfo", "status", "ubx2DAccH", "ubx2DAccV", "ubx3DAcc", "x", "y", "z"]
    ALTITUDE_FIELD_NUMBER: _ClassVar[int]
    ENUX_FIELD_NUMBER: _ClassVar[int]
    ENUY_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    HEADINGACC_FIELD_NUMBER: _ClassVar[int]
    HEADING_FIELD_NUMBER: _ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    REFINFO_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    UBX2DACCH_FIELD_NUMBER: _ClassVar[int]
    UBX2DACCV_FIELD_NUMBER: _ClassVar[int]
    UBX3DACC_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    altitude: float
    enuX: float
    enuY: float
    header: _message_header_pb2.msgHeader
    heading: float
    headingAcc: float
    installInfo: msgGnssInstallInfo
    latitude: float
    longitude: float
    refInfo: msgGnssRefInfo
    status: int
    ubx2DAccH: float
    ubx2DAccV: float
    ubx3DAcc: float
    x: float
    y: float
    z: float
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., status: _Optional[int] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., ubx2DAccH: _Optional[float] = ..., ubx2DAccV: _Optional[float] = ..., ubx3DAcc: _Optional[float] = ..., longitude: _Optional[float] = ..., latitude: _Optional[float] = ..., altitude: _Optional[float] = ..., installInfo: _Optional[_Union[msgGnssInstallInfo, _Mapping]] = ..., refInfo: _Optional[_Union[msgGnssRefInfo, _Mapping]] = ..., enuX: _Optional[float] = ..., enuY: _Optional[float] = ..., heading: _Optional[float] = ..., headingAcc: _Optional[float] = ...) -> None: ...

class msgGnssInstallInfo(_message.Message):
    __slots__ = ["x", "y", "yaw", "z"]
    X_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., yaw: _Optional[float] = ...) -> None: ...

class msgGnssRefInfo(_message.Message):
    __slots__ = ["altitude", "latitude", "longitude"]
    ALTITUDE_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    altitude: float
    latitude: float
    longitude: float
    def __init__(self, longitude: _Optional[float] = ..., latitude: _Optional[float] = ..., altitude: _Optional[float] = ...) -> None: ...
