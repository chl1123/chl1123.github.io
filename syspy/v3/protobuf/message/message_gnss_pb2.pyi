import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgAllGnss(_message.Message):
    __slots__ = ["gnss"]
    GNSS_FIELD_NUMBER: ClassVar[int]
    gnss: _containers.RepeatedCompositeFieldContainer[msgGnss]
    def __init__(self, gnss: Optional[Iterable[Union[msgGnss, Mapping]]] = ...) -> None: ...

class msgGnss(_message.Message):
    __slots__ = ["altitude", "enuX", "enuY", "header", "heading", "headingAcc", "installInfo", "latitude", "longitude", "refInfo", "status", "ubx2DAccH", "ubx2DAccV", "ubx3DAcc", "x", "y", "z"]
    ALTITUDE_FIELD_NUMBER: ClassVar[int]
    ENUX_FIELD_NUMBER: ClassVar[int]
    ENUY_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    HEADINGACC_FIELD_NUMBER: ClassVar[int]
    HEADING_FIELD_NUMBER: ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: ClassVar[int]
    LATITUDE_FIELD_NUMBER: ClassVar[int]
    LONGITUDE_FIELD_NUMBER: ClassVar[int]
    REFINFO_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    UBX2DACCH_FIELD_NUMBER: ClassVar[int]
    UBX2DACCV_FIELD_NUMBER: ClassVar[int]
    UBX3DACC_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., status: Optional[int] = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., ubx2DAccH: Optional[float] = ..., ubx2DAccV: Optional[float] = ..., ubx3DAcc: Optional[float] = ..., longitude: Optional[float] = ..., latitude: Optional[float] = ..., altitude: Optional[float] = ..., installInfo: Optional[Union[msgGnssInstallInfo, Mapping]] = ..., refInfo: Optional[Union[msgGnssRefInfo, Mapping]] = ..., enuX: Optional[float] = ..., enuY: Optional[float] = ..., heading: Optional[float] = ..., headingAcc: Optional[float] = ...) -> None: ...

class msgGnssInstallInfo(_message.Message):
    __slots__ = ["x", "y", "yaw", "z"]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., yaw: Optional[float] = ...) -> None: ...

class msgGnssRefInfo(_message.Message):
    __slots__ = ["altitude", "latitude", "longitude"]
    ALTITUDE_FIELD_NUMBER: ClassVar[int]
    LATITUDE_FIELD_NUMBER: ClassVar[int]
    LONGITUDE_FIELD_NUMBER: ClassVar[int]
    altitude: float
    latitude: float
    longitude: float
    def __init__(self, longitude: Optional[float] = ..., latitude: Optional[float] = ..., altitude: Optional[float] = ...) -> None: ...
