import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgAllLasers(_message.Message):
    __slots__ = ["laser"]
    LASER_FIELD_NUMBER: ClassVar[int]
    laser: _containers.RepeatedCompositeFieldContainer[msgLaser]
    def __init__(self, laser: Optional[Iterable[Union[msgLaser, Mapping]]] = ...) -> None: ...

class msgAllLasers3D(_message.Message):
    __slots__ = ["lasers3D"]
    LASERS3D_FIELD_NUMBER: ClassVar[int]
    lasers3D: _containers.RepeatedCompositeFieldContainer[msgLaser3D]
    def __init__(self, lasers3D: Optional[Iterable[Union[msgLaser3D, Mapping]]] = ...) -> None: ...

class msgCostMap(_message.Message):
    __slots__ = ["grids", "resolution"]
    GRIDS_FIELD_NUMBER: ClassVar[int]
    RESOLUTION_FIELD_NUMBER: ClassVar[int]
    grids: _containers.RepeatedCompositeFieldContainer[msgGrid]
    resolution: int
    def __init__(self, resolution: Optional[int] = ..., grids: Optional[Iterable[Union[msgGrid, Mapping]]] = ...) -> None: ...

class msgGrid(_message.Message):
    __slots__ = ["value", "x", "y"]
    VALUE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    value: int
    x: int
    y: int
    def __init__(self, value: Optional[int] = ..., x: Optional[int] = ..., y: Optional[int] = ...) -> None: ...

class msgLaser(_message.Message):
    __slots__ = ["beams", "beamsNotUse", "deviceInfo", "header", "installInfo", "is3DLocalization", "useForBinDetection", "useForLoc"]
    BEAMSNOTUSE_FIELD_NUMBER: ClassVar[int]
    BEAMS_FIELD_NUMBER: ClassVar[int]
    DEVICEINFO_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: ClassVar[int]
    IS3DLOCALIZATION_FIELD_NUMBER: ClassVar[int]
    USEFORBINDETECTION_FIELD_NUMBER: ClassVar[int]
    USEFORLOC_FIELD_NUMBER: ClassVar[int]
    beams: _containers.RepeatedCompositeFieldContainer[msgLaserBeam]
    beamsNotUse: _containers.RepeatedCompositeFieldContainer[msgLaserBeam]
    deviceInfo: msgLaserDeviceInfo
    header: _message_header_pb2.msgHeader
    installInfo: msgLaserInstallInfo
    is3DLocalization: bool
    useForBinDetection: bool
    useForLoc: bool
    def __init__(self, deviceInfo: Optional[Union[msgLaserDeviceInfo, Mapping]] = ..., installInfo: Optional[Union[msgLaserInstallInfo, Mapping]] = ..., header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., beams: Optional[Iterable[Union[msgLaserBeam, Mapping]]] = ..., useForLoc: bool = ..., beamsNotUse: Optional[Iterable[Union[msgLaserBeam, Mapping]]] = ..., is3DLocalization: bool = ..., useForBinDetection: bool = ...) -> None: ...

class msgLaser3D(_message.Message):
    __slots__ = ["azimuthCorrection", "beams3D", "beamsNotUse", "deviceInfo", "factor", "header", "installInfo", "is3DLocalization", "is3DobstacleDetection", "laserType", "useForLoc", "verticalCorrection"]
    AZIMUTHCORRECTION_FIELD_NUMBER: ClassVar[int]
    BEAMS3D_FIELD_NUMBER: ClassVar[int]
    BEAMSNOTUSE_FIELD_NUMBER: ClassVar[int]
    DEVICEINFO_FIELD_NUMBER: ClassVar[int]
    FACTOR_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: ClassVar[int]
    IS3DLOCALIZATION_FIELD_NUMBER: ClassVar[int]
    IS3DOBSTACLEDETECTION_FIELD_NUMBER: ClassVar[int]
    LASERTYPE_FIELD_NUMBER: ClassVar[int]
    USEFORLOC_FIELD_NUMBER: ClassVar[int]
    VERTICALCORRECTION_FIELD_NUMBER: ClassVar[int]
    azimuthCorrection: _containers.RepeatedScalarFieldContainer[float]
    beams3D: _containers.RepeatedCompositeFieldContainer[msgLaserBeam3D]
    beamsNotUse: _containers.RepeatedCompositeFieldContainer[msgLaserBeam]
    deviceInfo: msgLaserDeviceInfo
    factor: float
    header: _message_header_pb2.msgHeader
    installInfo: msgLaserInstallInfo
    is3DLocalization: bool
    is3DobstacleDetection: bool
    laserType: int
    useForLoc: bool
    verticalCorrection: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, deviceInfo: Optional[Union[msgLaserDeviceInfo, Mapping]] = ..., installInfo: Optional[Union[msgLaserInstallInfo, Mapping]] = ..., header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., beams3D: Optional[Iterable[Union[msgLaserBeam3D, Mapping]]] = ..., useForLoc: bool = ..., beamsNotUse: Optional[Iterable[Union[msgLaserBeam, Mapping]]] = ..., is3DLocalization: bool = ..., laserType: Optional[int] = ..., factor: Optional[float] = ..., azimuthCorrection: Optional[Iterable[float]] = ..., verticalCorrection: Optional[Iterable[float]] = ..., is3DobstacleDetection: bool = ...) -> None: ...

class msgLaserBeam(_message.Message):
    __slots__ = ["angle", "dist", "header", "isObstacle", "isVirtual", "rssi", "valid", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    DIST_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ISOBSTACLE_FIELD_NUMBER: ClassVar[int]
    ISVIRTUAL_FIELD_NUMBER: ClassVar[int]
    RSSI_FIELD_NUMBER: ClassVar[int]
    VALID_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    dist: float
    header: _message_header_pb2.msgHeader
    isObstacle: bool
    isVirtual: bool
    rssi: float
    valid: bool
    x: float
    y: float
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., angle: Optional[float] = ..., dist: Optional[float] = ..., x: Optional[float] = ..., y: Optional[float] = ..., rssi: Optional[float] = ..., valid: bool = ..., isVirtual: bool = ..., isObstacle: bool = ...) -> None: ...

class msgLaserBeam3D(_message.Message):
    __slots__ = ["data", "firstAzimuth", "id", "intensity", "ring", "secondAzimuth", "timestamp", "x", "y", "z"]
    DATA_FIELD_NUMBER: ClassVar[int]
    FIRSTAZIMUTH_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    INTENSITY_FIELD_NUMBER: ClassVar[int]
    RING_FIELD_NUMBER: ClassVar[int]
    SECONDAZIMUTH_FIELD_NUMBER: ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    data: bytes
    firstAzimuth: float
    id: int
    intensity: int
    ring: int
    secondAzimuth: float
    timestamp: int
    x: float
    y: float
    z: float
    def __init__(self, id: Optional[int] = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., intensity: Optional[int] = ..., ring: Optional[int] = ..., timestamp: Optional[int] = ..., data: Optional[bytes] = ..., firstAzimuth: Optional[float] = ..., secondAzimuth: Optional[float] = ...) -> None: ...

class msgLaserCluster(_message.Message):
    __slots__ = ["beams", "deviceInfo", "features", "header", "installInfo"]
    BEAMS_FIELD_NUMBER: ClassVar[int]
    DEVICEINFO_FIELD_NUMBER: ClassVar[int]
    FEATURES_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INSTALLINFO_FIELD_NUMBER: ClassVar[int]
    beams: _containers.RepeatedCompositeFieldContainer[msgLaserBeam]
    deviceInfo: msgLaserDeviceInfo
    features: msgLaserClusterFeature
    header: _message_header_pb2.msgHeader
    installInfo: msgLaserInstallInfo
    def __init__(self, deviceInfo: Optional[Union[msgLaserDeviceInfo, Mapping]] = ..., installInfo: Optional[Union[msgLaserInstallInfo, Mapping]] = ..., header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., beams: Optional[Iterable[Union[msgLaserBeam, Mapping]]] = ..., features: Optional[Union[msgLaserClusterFeature, Mapping]] = ...) -> None: ...

class msgLaserClusterFeature(_message.Message):
    __slots__ = ["angDiff", "avgMedianDev", "avgRssi", "boundaryLength", "boundaryRegularity", "circularity", "iav", "linearity", "meanCurvature", "nextJump", "numPoints", "prevJump", "radius", "std", "stdIav", "width"]
    ANGDIFF_FIELD_NUMBER: ClassVar[int]
    AVGMEDIANDEV_FIELD_NUMBER: ClassVar[int]
    AVGRSSI_FIELD_NUMBER: ClassVar[int]
    BOUNDARYLENGTH_FIELD_NUMBER: ClassVar[int]
    BOUNDARYREGULARITY_FIELD_NUMBER: ClassVar[int]
    CIRCULARITY_FIELD_NUMBER: ClassVar[int]
    IAV_FIELD_NUMBER: ClassVar[int]
    LINEARITY_FIELD_NUMBER: ClassVar[int]
    MEANCURVATURE_FIELD_NUMBER: ClassVar[int]
    NEXTJUMP_FIELD_NUMBER: ClassVar[int]
    NUMPOINTS_FIELD_NUMBER: ClassVar[int]
    PREVJUMP_FIELD_NUMBER: ClassVar[int]
    RADIUS_FIELD_NUMBER: ClassVar[int]
    STDIAV_FIELD_NUMBER: ClassVar[int]
    STD_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, avgRssi: Optional[float] = ..., numPoints: Optional[float] = ..., std: Optional[float] = ..., avgMedianDev: Optional[float] = ..., prevJump: Optional[float] = ..., nextJump: Optional[float] = ..., width: Optional[float] = ..., linearity: Optional[float] = ..., circularity: Optional[float] = ..., radius: Optional[float] = ..., boundaryLength: Optional[float] = ..., angDiff: Optional[float] = ..., meanCurvature: Optional[float] = ..., boundaryRegularity: Optional[float] = ..., iav: Optional[float] = ..., stdIav: Optional[float] = ...) -> None: ...

class msgLaserDeviceInfo(_message.Message):
    __slots__ = ["deviceName", "id", "isClockWise", "maxAngle", "maxRange", "minAngle", "minRange", "pubStep", "realStep", "scanFreq", "timeIncrement"]
    DEVICENAME_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    ISCLOCKWISE_FIELD_NUMBER: ClassVar[int]
    MAXANGLE_FIELD_NUMBER: ClassVar[int]
    MAXRANGE_FIELD_NUMBER: ClassVar[int]
    MINANGLE_FIELD_NUMBER: ClassVar[int]
    MINRANGE_FIELD_NUMBER: ClassVar[int]
    PUBSTEP_FIELD_NUMBER: ClassVar[int]
    REALSTEP_FIELD_NUMBER: ClassVar[int]
    SCANFREQ_FIELD_NUMBER: ClassVar[int]
    TIMEINCREMENT_FIELD_NUMBER: ClassVar[int]
    deviceName: str
    id: int
    isClockWise: bool
    maxAngle: float
    maxRange: float
    minAngle: float
    minRange: float
    pubStep: float
    realStep: float
    scanFreq: float
    timeIncrement: float
    def __init__(self, deviceName: Optional[str] = ..., minRange: Optional[float] = ..., maxRange: Optional[float] = ..., minAngle: Optional[float] = ..., maxAngle: Optional[float] = ..., realStep: Optional[float] = ..., pubStep: Optional[float] = ..., timeIncrement: Optional[float] = ..., scanFreq: Optional[float] = ..., id: Optional[int] = ..., isClockWise: bool = ...) -> None: ...

class msgLaserInstallInfo(_message.Message):
    __slots__ = ["pitch", "roll", "x", "y", "yaw", "z"]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    pitch: float
    roll: float
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., roll: Optional[float] = ..., pitch: Optional[float] = ..., yaw: Optional[float] = ...) -> None: ...

class msgLaserPoint(_message.Message):
    __slots__ = ["dataNSec", "id", "isObstacle", "rssi", "type", "x", "y", "z"]
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    APIObstacle: msgLaserPoint.Type
    Collision: msgLaserPoint.Type
    DATANSEC_FIELD_NUMBER: ClassVar[int]
    Fallingdown: msgLaserPoint.Type
    ID_FIELD_NUMBER: ClassVar[int]
    ISOBSTACLE_FIELD_NUMBER: ClassVar[int]
    Infrared: msgLaserPoint.Type
    Laser: msgLaserPoint.Type
    RSSI_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    Ultrasonic: msgLaserPoint.Type
    VirtualPoint: msgLaserPoint.Type
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    dataNSec: int
    id: str
    isObstacle: bool
    rssi: float
    type: msgLaserPoint.Type
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., type: Optional[Union[msgLaserPoint.Type, str]] = ..., id: Optional[str] = ..., isObstacle: bool = ..., rssi: Optional[float] = ..., dataNSec: Optional[int] = ...) -> None: ...

class msgLaserPointCloud(_message.Message):
    __slots__ = ["header", "point"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    POINT_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    point: _containers.RepeatedCompositeFieldContainer[msgLaserPoint]
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., point: Optional[Iterable[Union[msgLaserPoint, Mapping]]] = ...) -> None: ...

class msgLaserSegResult(_message.Message):
    __slots__ = ["clusters", "header"]
    CLUSTERS_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    clusters: _containers.RepeatedCompositeFieldContainer[msgLaserCluster]
    header: _message_header_pb2.msgHeader
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., clusters: Optional[Iterable[Union[msgLaserCluster, Mapping]]] = ...) -> None: ...

class msgSensorPoint(_message.Message):
    __slots__ = ["isObstacle", "rssi", "tag", "x", "y", "z"]
    ISOBSTACLE_FIELD_NUMBER: ClassVar[int]
    RSSI_FIELD_NUMBER: ClassVar[int]
    TAG_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    isObstacle: bool
    rssi: float
    tag: str
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., isObstacle: bool = ..., rssi: Optional[float] = ..., tag: Optional[str] = ...) -> None: ...

class msgSensorPointCloud(_message.Message):
    __slots__ = ["globalCluster", "localCluster"]
    GLOBALCLUSTER_FIELD_NUMBER: ClassVar[int]
    LOCALCLUSTER_FIELD_NUMBER: ClassVar[int]
    globalCluster: _containers.RepeatedCompositeFieldContainer[msgSensorPointCluster]
    localCluster: _containers.RepeatedCompositeFieldContainer[msgSensorPointCluster]
    def __init__(self, globalCluster: Optional[Iterable[Union[msgSensorPointCluster, Mapping]]] = ..., localCluster: Optional[Iterable[Union[msgSensorPointCluster, Mapping]]] = ...) -> None: ...

class msgSensorPointCluster(_message.Message):
    __slots__ = ["header", "id", "point", "type"]
    class clusterType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ADCollision: msgSensorPointCluster.clusterType
    APIObstacle: msgSensorPointCluster.clusterType
    DIUltrasonic: msgSensorPointCluster.clusterType
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    POINT_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    collision: msgSensorPointCluster.clusterType
    depthCamera: msgSensorPointCluster.clusterType
    distanceNode: msgSensorPointCluster.clusterType
    fallingDown: msgSensorPointCluster.clusterType
    header: _message_header_pb2.msgHeader
    id: str
    infrared: msgSensorPointCluster.clusterType
    laser: msgSensorPointCluster.clusterType
    point: _containers.RepeatedCompositeFieldContainer[msgSensorPoint]
    reservedDepthCamera: msgSensorPointCluster.clusterType
    reservedPoint: msgSensorPointCluster.clusterType
    type: msgSensorPointCluster.clusterType
    ultrasonic: msgSensorPointCluster.clusterType
    virtualPoint: msgSensorPointCluster.clusterType
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., type: Optional[Union[msgSensorPointCluster.clusterType, str]] = ..., id: Optional[str] = ..., point: Optional[Iterable[Union[msgSensorPoint, Mapping]]] = ...) -> None: ...
