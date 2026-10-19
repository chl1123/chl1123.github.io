from . import message_header_pb2 as _message_header_pb2
from . import message_keyframe_pb2 as _message_keyframe_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgAllLasers(_message.Message):
    __slots__ = ["laser"]
    LASER_FIELD_NUMBER: _ClassVar[int]
    laser: _containers.RepeatedCompositeFieldContainer[msgLaser]
    def __init__(self, laser: _Optional[_Iterable[_Union[msgLaser, _Mapping]]] = ...) -> None: ...

class msgCostMap(_message.Message):
    __slots__ = ["grids", "originX", "originY", "resolution", "sizeX", "sizeY"]
    GRIDS_FIELD_NUMBER: _ClassVar[int]
    ORIGINX_FIELD_NUMBER: _ClassVar[int]
    ORIGINY_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    SIZEX_FIELD_NUMBER: _ClassVar[int]
    SIZEY_FIELD_NUMBER: _ClassVar[int]
    grids: _containers.RepeatedCompositeFieldContainer[msgGrid]
    originX: float
    originY: float
    resolution: int
    sizeX: int
    sizeY: int
    def __init__(self, resolution: _Optional[int] = ..., grids: _Optional[_Iterable[_Union[msgGrid, _Mapping]]] = ..., sizeX: _Optional[int] = ..., sizeY: _Optional[int] = ..., originX: _Optional[float] = ..., originY: _Optional[float] = ...) -> None: ...

class msgGrid(_message.Message):
    __slots__ = ["index", "value", "x", "y"]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    index: int
    value: int
    x: int
    y: int
    def __init__(self, value: _Optional[int] = ..., x: _Optional[int] = ..., y: _Optional[int] = ..., index: _Optional[int] = ...) -> None: ...

class msgLaser(_message.Message):
    __slots__ = ["beams", "beamsNotUse", "deviceInfo", "header", "installInfo"]
    BEAMSNOTUSE_FIELD_NUMBER: _ClassVar[int]
    BEAMS_FIELD_NUMBER: _ClassVar[int]
    DEVICEINFO_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: _ClassVar[int]
    beams: _containers.RepeatedCompositeFieldContainer[msgLaserBeam]
    beamsNotUse: _containers.RepeatedCompositeFieldContainer[msgLaserBeam]
    deviceInfo: msgLaserDeviceInfo
    header: _message_header_pb2.msgHeader
    installInfo: msgLaserInstallInfo
    def __init__(self, deviceInfo: _Optional[_Union[msgLaserDeviceInfo, _Mapping]] = ..., installInfo: _Optional[_Union[msgLaserInstallInfo, _Mapping]] = ..., header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., beams: _Optional[_Iterable[_Union[msgLaserBeam, _Mapping]]] = ..., beamsNotUse: _Optional[_Iterable[_Union[msgLaserBeam, _Mapping]]] = ...) -> None: ...

class msgLaser3d(_message.Message):
    __slots__ = ["deviceInfo", "header", "installInfo", "pcData"]
    DEVICEINFO_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: _ClassVar[int]
    PCDATA_FIELD_NUMBER: _ClassVar[int]
    deviceInfo: msgLaserDeviceInfo
    header: _message_header_pb2.msgHeader
    installInfo: msgLaserInstallInfo
    pcData: _message_keyframe_pb2.msgPointCloudData
    def __init__(self, deviceInfo: _Optional[_Union[msgLaserDeviceInfo, _Mapping]] = ..., installInfo: _Optional[_Union[msgLaserInstallInfo, _Mapping]] = ..., header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., pcData: _Optional[_Union[_message_keyframe_pb2.msgPointCloudData, _Mapping]] = ...) -> None: ...

class msgLaserBeam(_message.Message):
    __slots__ = ["angle", "dist", "header", "isObstacle", "isVirtual", "rssi", "valid", "x", "y"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    DIST_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ISOBSTACLE_FIELD_NUMBER: _ClassVar[int]
    ISVIRTUAL_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    VALID_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    dist: float
    header: _message_header_pb2.msgHeader
    isObstacle: bool
    isVirtual: bool
    rssi: float
    valid: bool
    x: float
    y: float
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., angle: _Optional[float] = ..., dist: _Optional[float] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., rssi: _Optional[float] = ..., valid: bool = ..., isVirtual: bool = ..., isObstacle: bool = ...) -> None: ...

class msgLaserCluster(_message.Message):
    __slots__ = ["beams", "deviceInfo", "features", "header", "installInfo"]
    BEAMS_FIELD_NUMBER: _ClassVar[int]
    DEVICEINFO_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: _ClassVar[int]
    beams: _containers.RepeatedCompositeFieldContainer[msgLaserBeam]
    deviceInfo: msgLaserDeviceInfo
    features: msgLaserClusterFeature
    header: _message_header_pb2.msgHeader
    installInfo: msgLaserInstallInfo
    def __init__(self, deviceInfo: _Optional[_Union[msgLaserDeviceInfo, _Mapping]] = ..., installInfo: _Optional[_Union[msgLaserInstallInfo, _Mapping]] = ..., header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., beams: _Optional[_Iterable[_Union[msgLaserBeam, _Mapping]]] = ..., features: _Optional[_Union[msgLaserClusterFeature, _Mapping]] = ...) -> None: ...

class msgLaserClusterFeature(_message.Message):
    __slots__ = ["angDiff", "avgMedianDev", "avgRssi", "boundaryLength", "boundaryRegularity", "circularity", "iav", "linearity", "meanCurvature", "nextJump", "numPoints", "prevJump", "radius", "std", "stdIav", "width"]
    ANGDIFF_FIELD_NUMBER: _ClassVar[int]
    AVGMEDIANDEV_FIELD_NUMBER: _ClassVar[int]
    AVGRSSI_FIELD_NUMBER: _ClassVar[int]
    BOUNDARYLENGTH_FIELD_NUMBER: _ClassVar[int]
    BOUNDARYREGULARITY_FIELD_NUMBER: _ClassVar[int]
    CIRCULARITY_FIELD_NUMBER: _ClassVar[int]
    IAV_FIELD_NUMBER: _ClassVar[int]
    LINEARITY_FIELD_NUMBER: _ClassVar[int]
    MEANCURVATURE_FIELD_NUMBER: _ClassVar[int]
    NEXTJUMP_FIELD_NUMBER: _ClassVar[int]
    NUMPOINTS_FIELD_NUMBER: _ClassVar[int]
    PREVJUMP_FIELD_NUMBER: _ClassVar[int]
    RADIUS_FIELD_NUMBER: _ClassVar[int]
    STDIAV_FIELD_NUMBER: _ClassVar[int]
    STD_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    angDiff: float
    avgMedianDev: float
    avgRssi: float
    boundaryLength: float
    boundaryRegularity: float
    circularity: float
    iav: float
    linearity: float
    meanCurvature: float
    nextJump: float
    numPoints: float
    prevJump: float
    radius: float
    std: float
    stdIav: float
    width: float
    def __init__(self, avgRssi: _Optional[float] = ..., numPoints: _Optional[float] = ..., std: _Optional[float] = ..., avgMedianDev: _Optional[float] = ..., prevJump: _Optional[float] = ..., nextJump: _Optional[float] = ..., width: _Optional[float] = ..., linearity: _Optional[float] = ..., circularity: _Optional[float] = ..., radius: _Optional[float] = ..., boundaryLength: _Optional[float] = ..., angDiff: _Optional[float] = ..., meanCurvature: _Optional[float] = ..., boundaryRegularity: _Optional[float] = ..., iav: _Optional[float] = ..., stdIav: _Optional[float] = ...) -> None: ...

class msgLaserDeviceInfo(_message.Message):
    __slots__ = ["has_2d_data", "has_3d_data", "has_imu_data", "isClockWise", "key", "laserType", "maxAngle", "maxRange", "minAngle", "minRange", "pubStep", "realStep", "scanFreq", "timeIncrement"]
    HAS_2D_DATA_FIELD_NUMBER: _ClassVar[int]
    HAS_3D_DATA_FIELD_NUMBER: _ClassVar[int]
    HAS_IMU_DATA_FIELD_NUMBER: _ClassVar[int]
    ISCLOCKWISE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    LASERTYPE_FIELD_NUMBER: _ClassVar[int]
    MAXANGLE_FIELD_NUMBER: _ClassVar[int]
    MAXRANGE_FIELD_NUMBER: _ClassVar[int]
    MINANGLE_FIELD_NUMBER: _ClassVar[int]
    MINRANGE_FIELD_NUMBER: _ClassVar[int]
    PUBSTEP_FIELD_NUMBER: _ClassVar[int]
    REALSTEP_FIELD_NUMBER: _ClassVar[int]
    SCANFREQ_FIELD_NUMBER: _ClassVar[int]
    TIMEINCREMENT_FIELD_NUMBER: _ClassVar[int]
    has_2d_data: bool
    has_3d_data: bool
    has_imu_data: bool
    isClockWise: bool
    key: str
    laserType: int
    maxAngle: float
    maxRange: float
    minAngle: float
    minRange: float
    pubStep: float
    realStep: float
    scanFreq: float
    timeIncrement: float
    def __init__(self, key: _Optional[str] = ..., minRange: _Optional[float] = ..., maxRange: _Optional[float] = ..., minAngle: _Optional[float] = ..., maxAngle: _Optional[float] = ..., realStep: _Optional[float] = ..., pubStep: _Optional[float] = ..., timeIncrement: _Optional[float] = ..., scanFreq: _Optional[float] = ..., isClockWise: bool = ..., has_2d_data: bool = ..., has_3d_data: bool = ..., has_imu_data: bool = ..., laserType: _Optional[int] = ...) -> None: ...

class msgLaserInstallInfo(_message.Message):
    __slots__ = ["pitch", "roll", "x", "y", "yaw", "z"]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    pitch: float
    roll: float
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., roll: _Optional[float] = ..., pitch: _Optional[float] = ..., yaw: _Optional[float] = ...) -> None: ...

class msgLaserPoint(_message.Message):
    __slots__ = ["dataNSec", "id", "isObstacle", "rssi", "type", "x", "y", "z"]
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    APIObstacle: msgLaserPoint.Type
    Collision: msgLaserPoint.Type
    DATANSEC_FIELD_NUMBER: _ClassVar[int]
    Fallingdown: msgLaserPoint.Type
    ID_FIELD_NUMBER: _ClassVar[int]
    ISOBSTACLE_FIELD_NUMBER: _ClassVar[int]
    Infrared: msgLaserPoint.Type
    Laser: msgLaserPoint.Type
    RSSI_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    Ultrasonic: msgLaserPoint.Type
    VirtualPoint: msgLaserPoint.Type
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    dataNSec: int
    id: str
    isObstacle: bool
    rssi: float
    type: msgLaserPoint.Type
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., type: _Optional[_Union[msgLaserPoint.Type, str]] = ..., id: _Optional[str] = ..., isObstacle: bool = ..., rssi: _Optional[float] = ..., dataNSec: _Optional[int] = ...) -> None: ...

class msgLaserPointCloud(_message.Message):
    __slots__ = ["header", "point"]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    header: _message_header_pb2.msgHeader
    point: _containers.RepeatedCompositeFieldContainer[msgLaserPoint]
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., point: _Optional[_Iterable[_Union[msgLaserPoint, _Mapping]]] = ...) -> None: ...

class msgLaserSegResult(_message.Message):
    __slots__ = ["clusters", "header"]
    CLUSTERS_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    clusters: _containers.RepeatedCompositeFieldContainer[msgLaserCluster]
    header: _message_header_pb2.msgHeader
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., clusters: _Optional[_Iterable[_Union[msgLaserCluster, _Mapping]]] = ...) -> None: ...

class msgSensorPoint(_message.Message):
    __slots__ = ["isObstacle", "rssi", "tag", "x", "y", "z"]
    ISOBSTACLE_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    isObstacle: bool
    rssi: float
    tag: str
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., isObstacle: bool = ..., rssi: _Optional[float] = ..., tag: _Optional[str] = ...) -> None: ...

class msgSensorPointCloud(_message.Message):
    __slots__ = ["globalCluster", "localCluster"]
    GLOBALCLUSTER_FIELD_NUMBER: _ClassVar[int]
    LOCALCLUSTER_FIELD_NUMBER: _ClassVar[int]
    globalCluster: _containers.RepeatedCompositeFieldContainer[msgSensorPointCluster]
    localCluster: _containers.RepeatedCompositeFieldContainer[msgSensorPointCluster]
    def __init__(self, globalCluster: _Optional[_Iterable[_Union[msgSensorPointCluster, _Mapping]]] = ..., localCluster: _Optional[_Iterable[_Union[msgSensorPointCluster, _Mapping]]] = ...) -> None: ...

class msgSensorPointCluster(_message.Message):
    __slots__ = ["className", "header", "key", "point", "type"]
    class clusterType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ADCollision: msgSensorPointCluster.clusterType
    APIObstacle: msgSensorPointCluster.clusterType
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DIUltrasonic: msgSensorPointCluster.clusterType
    HEADER_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    className: str
    collision: msgSensorPointCluster.clusterType
    depthCamera: msgSensorPointCluster.clusterType
    distanceNode: msgSensorPointCluster.clusterType
    fallingDown: msgSensorPointCluster.clusterType
    header: _message_header_pb2.msgHeader
    infrared: msgSensorPointCluster.clusterType
    key: str
    laser: msgSensorPointCluster.clusterType
    mapPoint: msgSensorPointCluster.clusterType
    point: _containers.RepeatedCompositeFieldContainer[msgSensorPoint]
    reservedDepthCamera: msgSensorPointCluster.clusterType
    reservedPoint: msgSensorPointCluster.clusterType
    type: msgSensorPointCluster.clusterType
    ultrasonic: msgSensorPointCluster.clusterType
    virtualPoint: msgSensorPointCluster.clusterType
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., type: _Optional[_Union[msgSensorPointCluster.clusterType, str]] = ..., key: _Optional[str] = ..., point: _Optional[_Iterable[_Union[msgSensorPoint, _Mapping]]] = ..., className: _Optional[str] = ...) -> None: ...
