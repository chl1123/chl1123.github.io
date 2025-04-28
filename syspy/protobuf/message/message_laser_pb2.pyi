import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_AllLasers(_message.Message):
    __slots__ = ["laser"]
    LASER_FIELD_NUMBER: ClassVar[int]
    laser: _containers.RepeatedCompositeFieldContainer[Message_Laser]
    def __init__(self, laser: Optional[Iterable[Union[Message_Laser, Mapping]]] = ...) -> None: ...

class Message_AllLasers3D(_message.Message):
    __slots__ = ["lasers3d"]
    LASERS3D_FIELD_NUMBER: ClassVar[int]
    lasers3d: _containers.RepeatedCompositeFieldContainer[Message_Laser3D]
    def __init__(self, lasers3d: Optional[Iterable[Union[Message_Laser3D, Mapping]]] = ...) -> None: ...

class Message_CostMap(_message.Message):
    __slots__ = ["grids", "resolution"]
    GRIDS_FIELD_NUMBER: ClassVar[int]
    RESOLUTION_FIELD_NUMBER: ClassVar[int]
    grids: _containers.RepeatedCompositeFieldContainer[Message_Grid]
    resolution: int
    def __init__(self, resolution: Optional[int] = ..., grids: Optional[Iterable[Union[Message_Grid, Mapping]]] = ...) -> None: ...

class Message_Grid(_message.Message):
    __slots__ = ["value", "x", "y"]
    VALUE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    value: int
    x: int
    y: int
    def __init__(self, value: Optional[int] = ..., x: Optional[int] = ..., y: Optional[int] = ...) -> None: ...

class Message_Laser(_message.Message):
    __slots__ = ["beams", "beams_not_use", "device_info", "header", "install_info", "is3DLocalization", "use_forBinDetection", "use_forLoc"]
    BEAMS_FIELD_NUMBER: ClassVar[int]
    BEAMS_NOT_USE_FIELD_NUMBER: ClassVar[int]
    DEVICE_INFO_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INSTALL_INFO_FIELD_NUMBER: ClassVar[int]
    IS3DLOCALIZATION_FIELD_NUMBER: ClassVar[int]
    USE_FORBINDETECTION_FIELD_NUMBER: ClassVar[int]
    USE_FORLOC_FIELD_NUMBER: ClassVar[int]
    beams: _containers.RepeatedCompositeFieldContainer[Message_LaserBeam]
    beams_not_use: _containers.RepeatedCompositeFieldContainer[Message_LaserBeam]
    device_info: Message_LaserDeviceInfo
    header: _message_header_pb2.Message_Header
    install_info: Message_LaserInstallInfo
    is3DLocalization: bool
    use_forBinDetection: bool
    use_forLoc: bool
    def __init__(self, device_info: Optional[Union[Message_LaserDeviceInfo, Mapping]] = ..., install_info: Optional[Union[Message_LaserInstallInfo, Mapping]] = ..., header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., beams: Optional[Iterable[Union[Message_LaserBeam, Mapping]]] = ..., use_forLoc: bool = ..., beams_not_use: Optional[Iterable[Union[Message_LaserBeam, Mapping]]] = ..., is3DLocalization: bool = ..., use_forBinDetection: bool = ...) -> None: ...

class Message_Laser3D(_message.Message):
    __slots__ = ["azimuthcorrection", "beams3D", "beams_not_use", "device_info", "factor", "header", "install_info", "is3DLocalization", "is3DobstacleDetection", "lasertype", "use_forLoc", "verticalcorrection"]
    AZIMUTHCORRECTION_FIELD_NUMBER: ClassVar[int]
    BEAMS3D_FIELD_NUMBER: ClassVar[int]
    BEAMS_NOT_USE_FIELD_NUMBER: ClassVar[int]
    DEVICE_INFO_FIELD_NUMBER: ClassVar[int]
    FACTOR_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INSTALL_INFO_FIELD_NUMBER: ClassVar[int]
    IS3DLOCALIZATION_FIELD_NUMBER: ClassVar[int]
    IS3DOBSTACLEDETECTION_FIELD_NUMBER: ClassVar[int]
    LASERTYPE_FIELD_NUMBER: ClassVar[int]
    USE_FORLOC_FIELD_NUMBER: ClassVar[int]
    VERTICALCORRECTION_FIELD_NUMBER: ClassVar[int]
    azimuthcorrection: _containers.RepeatedScalarFieldContainer[float]
    beams3D: _containers.RepeatedCompositeFieldContainer[Message_LaserBeam3D]
    beams_not_use: _containers.RepeatedCompositeFieldContainer[Message_LaserBeam]
    device_info: Message_LaserDeviceInfo
    factor: float
    header: _message_header_pb2.Message_Header
    install_info: Message_LaserInstallInfo
    is3DLocalization: bool
    is3DobstacleDetection: bool
    lasertype: int
    use_forLoc: bool
    verticalcorrection: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, device_info: Optional[Union[Message_LaserDeviceInfo, Mapping]] = ..., install_info: Optional[Union[Message_LaserInstallInfo, Mapping]] = ..., header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., beams3D: Optional[Iterable[Union[Message_LaserBeam3D, Mapping]]] = ..., use_forLoc: bool = ..., beams_not_use: Optional[Iterable[Union[Message_LaserBeam, Mapping]]] = ..., is3DLocalization: bool = ..., lasertype: Optional[int] = ..., factor: Optional[float] = ..., azimuthcorrection: Optional[Iterable[float]] = ..., verticalcorrection: Optional[Iterable[float]] = ..., is3DobstacleDetection: bool = ...) -> None: ...

class Message_LaserBeam(_message.Message):
    __slots__ = ["angle", "dist", "header", "is_obstacle", "is_virtual", "rssi", "valid", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    DIST_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    IS_OBSTACLE_FIELD_NUMBER: ClassVar[int]
    IS_VIRTUAL_FIELD_NUMBER: ClassVar[int]
    RSSI_FIELD_NUMBER: ClassVar[int]
    VALID_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    dist: float
    header: _message_header_pb2.Message_Header
    is_obstacle: bool
    is_virtual: bool
    rssi: float
    valid: bool
    x: float
    y: float
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., angle: Optional[float] = ..., dist: Optional[float] = ..., x: Optional[float] = ..., y: Optional[float] = ..., rssi: Optional[float] = ..., valid: bool = ..., is_virtual: bool = ..., is_obstacle: bool = ...) -> None: ...

class Message_LaserBeam3D(_message.Message):
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

class Message_LaserCluster(_message.Message):
    __slots__ = ["beams", "device_info", "features", "header", "install_info"]
    BEAMS_FIELD_NUMBER: ClassVar[int]
    DEVICE_INFO_FIELD_NUMBER: ClassVar[int]
    FEATURES_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INSTALL_INFO_FIELD_NUMBER: ClassVar[int]
    beams: _containers.RepeatedCompositeFieldContainer[Message_LaserBeam]
    device_info: Message_LaserDeviceInfo
    features: Message_LaserClusterFeature
    header: _message_header_pb2.Message_Header
    install_info: Message_LaserInstallInfo
    def __init__(self, device_info: Optional[Union[Message_LaserDeviceInfo, Mapping]] = ..., install_info: Optional[Union[Message_LaserInstallInfo, Mapping]] = ..., header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., beams: Optional[Iterable[Union[Message_LaserBeam, Mapping]]] = ..., features: Optional[Union[Message_LaserClusterFeature, Mapping]] = ...) -> None: ...

class Message_LaserClusterFeature(_message.Message):
    __slots__ = ["ang_diff", "avg_median_dev", "avg_rssi", "boundary_length", "boundary_regularity", "circularity", "iav", "linearity", "mean_curvature", "next_jump", "num_points", "prev_jump", "radius", "std", "std_iav", "width"]
    ANG_DIFF_FIELD_NUMBER: ClassVar[int]
    AVG_MEDIAN_DEV_FIELD_NUMBER: ClassVar[int]
    AVG_RSSI_FIELD_NUMBER: ClassVar[int]
    BOUNDARY_LENGTH_FIELD_NUMBER: ClassVar[int]
    BOUNDARY_REGULARITY_FIELD_NUMBER: ClassVar[int]
    CIRCULARITY_FIELD_NUMBER: ClassVar[int]
    IAV_FIELD_NUMBER: ClassVar[int]
    LINEARITY_FIELD_NUMBER: ClassVar[int]
    MEAN_CURVATURE_FIELD_NUMBER: ClassVar[int]
    NEXT_JUMP_FIELD_NUMBER: ClassVar[int]
    NUM_POINTS_FIELD_NUMBER: ClassVar[int]
    PREV_JUMP_FIELD_NUMBER: ClassVar[int]
    RADIUS_FIELD_NUMBER: ClassVar[int]
    STD_FIELD_NUMBER: ClassVar[int]
    STD_IAV_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    ang_diff: float
    avg_median_dev: float
    avg_rssi: float
    boundary_length: float
    boundary_regularity: float
    circularity: float
    iav: float
    linearity: float
    mean_curvature: float
    next_jump: float
    num_points: float
    prev_jump: float
    radius: float
    std: float
    std_iav: float
    width: float
    def __init__(self, avg_rssi: Optional[float] = ..., num_points: Optional[float] = ..., std: Optional[float] = ..., avg_median_dev: Optional[float] = ..., prev_jump: Optional[float] = ..., next_jump: Optional[float] = ..., width: Optional[float] = ..., linearity: Optional[float] = ..., circularity: Optional[float] = ..., radius: Optional[float] = ..., boundary_length: Optional[float] = ..., ang_diff: Optional[float] = ..., mean_curvature: Optional[float] = ..., boundary_regularity: Optional[float] = ..., iav: Optional[float] = ..., std_iav: Optional[float] = ...) -> None: ...

class Message_LaserDeviceInfo(_message.Message):
    __slots__ = ["device_name", "id", "isClockWise", "max_angle", "max_range", "min_angle", "min_range", "pub_step", "real_step", "scan_freq", "time_increment"]
    DEVICE_NAME_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    ISCLOCKWISE_FIELD_NUMBER: ClassVar[int]
    MAX_ANGLE_FIELD_NUMBER: ClassVar[int]
    MAX_RANGE_FIELD_NUMBER: ClassVar[int]
    MIN_ANGLE_FIELD_NUMBER: ClassVar[int]
    MIN_RANGE_FIELD_NUMBER: ClassVar[int]
    PUB_STEP_FIELD_NUMBER: ClassVar[int]
    REAL_STEP_FIELD_NUMBER: ClassVar[int]
    SCAN_FREQ_FIELD_NUMBER: ClassVar[int]
    TIME_INCREMENT_FIELD_NUMBER: ClassVar[int]
    device_name: str
    id: int
    isClockWise: bool
    max_angle: float
    max_range: float
    min_angle: float
    min_range: float
    pub_step: float
    real_step: float
    scan_freq: float
    time_increment: float
    def __init__(self, device_name: Optional[str] = ..., min_range: Optional[float] = ..., max_range: Optional[float] = ..., min_angle: Optional[float] = ..., max_angle: Optional[float] = ..., real_step: Optional[float] = ..., pub_step: Optional[float] = ..., time_increment: Optional[float] = ..., scan_freq: Optional[float] = ..., id: Optional[int] = ..., isClockWise: bool = ...) -> None: ...

class Message_LaserInstallInfo(_message.Message):
    __slots__ = ["upside", "x", "y", "yaw", "z"]
    UPSIDE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    upside: bool
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., yaw: Optional[float] = ..., upside: bool = ...) -> None: ...

class Message_LaserPoint(_message.Message):
    __slots__ = ["data_nsec", "id", "is_obstacle", "rssi", "type", "x", "y", "z"]
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    APIObstacle: Message_LaserPoint.Type
    Collision: Message_LaserPoint.Type
    DATA_NSEC_FIELD_NUMBER: ClassVar[int]
    Fallingdown: Message_LaserPoint.Type
    ID_FIELD_NUMBER: ClassVar[int]
    IS_OBSTACLE_FIELD_NUMBER: ClassVar[int]
    Infrared: Message_LaserPoint.Type
    Laser: Message_LaserPoint.Type
    RSSI_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    Ultrasonic: Message_LaserPoint.Type
    VirtualPoint: Message_LaserPoint.Type
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    data_nsec: int
    id: str
    is_obstacle: bool
    rssi: float
    type: Message_LaserPoint.Type
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., type: Optional[Union[Message_LaserPoint.Type, str]] = ..., id: Optional[str] = ..., is_obstacle: bool = ..., rssi: Optional[float] = ..., data_nsec: Optional[int] = ...) -> None: ...

class Message_LaserPointCloud(_message.Message):
    __slots__ = ["header", "point"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    POINT_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.Message_Header
    point: _containers.RepeatedCompositeFieldContainer[Message_LaserPoint]
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., point: Optional[Iterable[Union[Message_LaserPoint, Mapping]]] = ...) -> None: ...

class Message_LaserSegResult(_message.Message):
    __slots__ = ["clusters", "header"]
    CLUSTERS_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    clusters: _containers.RepeatedCompositeFieldContainer[Message_LaserCluster]
    header: _message_header_pb2.Message_Header
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., clusters: Optional[Iterable[Union[Message_LaserCluster, Mapping]]] = ...) -> None: ...

class Message_SensorPoint(_message.Message):
    __slots__ = ["is_obstacle", "rssi", "tag", "x", "y", "z"]
    IS_OBSTACLE_FIELD_NUMBER: ClassVar[int]
    RSSI_FIELD_NUMBER: ClassVar[int]
    TAG_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    is_obstacle: bool
    rssi: float
    tag: str
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., is_obstacle: bool = ..., rssi: Optional[float] = ..., tag: Optional[str] = ...) -> None: ...

class Message_SensorPointCloud(_message.Message):
    __slots__ = ["global_cluster", "local_cluster"]
    GLOBAL_CLUSTER_FIELD_NUMBER: ClassVar[int]
    LOCAL_CLUSTER_FIELD_NUMBER: ClassVar[int]
    global_cluster: _containers.RepeatedCompositeFieldContainer[Message_SensorPointCluster]
    local_cluster: _containers.RepeatedCompositeFieldContainer[Message_SensorPointCluster]
    def __init__(self, global_cluster: Optional[Iterable[Union[Message_SensorPointCluster, Mapping]]] = ..., local_cluster: Optional[Iterable[Union[Message_SensorPointCluster, Mapping]]] = ...) -> None: ...

class Message_SensorPointCluster(_message.Message):
    __slots__ = ["header", "id", "point", "type"]
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ADCollision: Message_SensorPointCluster.Type
    APIObstacle: Message_SensorPointCluster.Type
    Collision: Message_SensorPointCluster.Type
    DepthCamera: Message_SensorPointCluster.Type
    DiUltrasonic: Message_SensorPointCluster.Type
    DistanceNode: Message_SensorPointCluster.Type
    Fallingdown: Message_SensorPointCluster.Type
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    Infrared: Message_SensorPointCluster.Type
    Laser: Message_SensorPointCluster.Type
    POINT_FIELD_NUMBER: ClassVar[int]
    ReservedDepthCamera: Message_SensorPointCluster.Type
    ReservedPoint: Message_SensorPointCluster.Type
    TYPE_FIELD_NUMBER: ClassVar[int]
    Ultrasonic: Message_SensorPointCluster.Type
    VirtualPoint: Message_SensorPointCluster.Type
    header: _message_header_pb2.Message_Header
    id: str
    point: _containers.RepeatedCompositeFieldContainer[Message_SensorPoint]
    type: Message_SensorPointCluster.Type
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., type: Optional[Union[Message_SensorPointCluster.Type, str]] = ..., id: Optional[str] = ..., point: Optional[Iterable[Union[Message_SensorPoint, Mapping]]] = ...) -> None: ...
