from . import message_header_pb2 as _message_header_pb2
from . import message_calibration_pb2 as _message_calibration_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor
POINT_XYZ: msgCloudType
POINT_XYZI: msgCloudType
POINT_XYZRGB: msgCloudType
POINT_XYZRGBA: msgCloudType

class msgPoint(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class msgPointCloud(_message.Message):
    __slots__ = ["data", "header", "height", "isDense", "type", "width"]
    DATA_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    ISDENSE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    header: _message_header_pb2.msgHeader
    height: int
    isDense: bool
    type: msgCloudType
    width: int
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., width: _Optional[int] = ..., height: _Optional[int] = ..., isDense: bool = ..., type: _Optional[_Union[msgCloudType, str]] = ..., data: _Optional[bytes] = ...) -> None: ...

class msgPolygon(_message.Message):
    __slots__ = ["points"]
    POINTS_FIELD_NUMBER: _ClassVar[int]
    points: _containers.RepeatedCompositeFieldContainer[msgPoint]
    def __init__(self, points: _Optional[_Iterable[_Union[msgPoint, _Mapping]]] = ...) -> None: ...

class msgRecognizeResult(_message.Message):
    __slots__ = ["header", "info", "objectMessage", "obstaclePolygon", "palletWidth", "resultImg", "robotResult", "trackerId", "type", "valid", "worldResult"]
    CLASS_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    OBJECTMESSAGE_FIELD_NUMBER: _ClassVar[int]
    OBSTACLEPOLYGON_FIELD_NUMBER: _ClassVar[int]
    PALLETWIDTH_FIELD_NUMBER: _ClassVar[int]
    RESULTIMG_FIELD_NUMBER: _ClassVar[int]
    ROBOTRESULT_FIELD_NUMBER: _ClassVar[int]
    TRACKERID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VALID_FIELD_NUMBER: _ClassVar[int]
    WORLDRESULT_FIELD_NUMBER: _ClassVar[int]
    header: _message_header_pb2.msgHeader
    info: str
    objectMessage: str
    obstaclePolygon: _containers.RepeatedCompositeFieldContainer[msgPolygon]
    palletWidth: float
    resultImg: str
    robotResult: msgRecognizeSpatialResult
    trackerId: str
    type: str
    valid: bool
    worldResult: msgRecognizeSpatialResult
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., valid: bool = ..., type: _Optional[str] = ..., resultImg: _Optional[str] = ..., palletWidth: _Optional[float] = ..., objectMessage: _Optional[str] = ..., obstaclePolygon: _Optional[_Iterable[_Union[msgPolygon, _Mapping]]] = ..., trackerId: _Optional[str] = ..., info: _Optional[str] = ..., robotResult: _Optional[_Union[msgRecognizeSpatialResult, _Mapping]] = ..., worldResult: _Optional[_Union[msgRecognizeSpatialResult, _Mapping]] = ..., **kwargs) -> None: ...

class msgRecognizeResultList(_message.Message):
    __slots__ = ["error", "img", "irImg", "logMsg", "pointCloud", "recoFileContentJson", "recoList", "recoStatus", "taskId"]
    class errorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ERROR_FIELD_NUMBER: _ClassVar[int]
    IMG_FIELD_NUMBER: _ClassVar[int]
    IRIMG_FIELD_NUMBER: _ClassVar[int]
    LOGMSG_FIELD_NUMBER: _ClassVar[int]
    POINTCLOUD_FIELD_NUMBER: _ClassVar[int]
    RECOFILECONTENTJSON_FIELD_NUMBER: _ClassVar[int]
    RECOLIST_FIELD_NUMBER: _ClassVar[int]
    RECOSTATUS_FIELD_NUMBER: _ClassVar[int]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    dataEmpty: msgRecognizeResultList.errorType
    error: msgRecognizeResultList.errorType
    errorNone: msgRecognizeResultList.errorType
    failed: msgRecognizeResultList.status
    img: _message_calibration_pb2.msgImage
    irImg: _message_calibration_pb2.msgImage
    logMsg: str
    modelEmpty: msgRecognizeResultList.errorType
    none: msgRecognizeResultList.status
    other: msgRecognizeResultList.errorType
    pointCloud: msgPointCloud
    recFileEmpty: msgRecognizeResultList.errorType
    recoFileContentJson: str
    recoList: _containers.RepeatedCompositeFieldContainer[msgRecognizeResult]
    recoStatus: msgRecognizeResultList.status
    resultEmpty: msgRecognizeResultList.errorType
    running: msgRecognizeResultList.status
    success: msgRecognizeResultList.status
    taskId: str
    def __init__(self, recoList: _Optional[_Iterable[_Union[msgRecognizeResult, _Mapping]]] = ..., recoStatus: _Optional[_Union[msgRecognizeResultList.status, str]] = ..., taskId: _Optional[str] = ..., img: _Optional[_Union[_message_calibration_pb2.msgImage, _Mapping]] = ..., irImg: _Optional[_Union[_message_calibration_pb2.msgImage, _Mapping]] = ..., pointCloud: _Optional[_Union[msgPointCloud, _Mapping]] = ..., logMsg: _Optional[str] = ..., error: _Optional[_Union[msgRecognizeResultList.errorType, str]] = ..., recoFileContentJson: _Optional[str] = ...) -> None: ...

class msgRecognizeSpatialResult(_message.Message):
    __slots__ = ["qx", "qy", "qz", "w", "x", "y", "yaw", "z"]
    QX_FIELD_NUMBER: _ClassVar[int]
    QY_FIELD_NUMBER: _ClassVar[int]
    QZ_FIELD_NUMBER: _ClassVar[int]
    W_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    qx: float
    qy: float
    qz: float
    w: float
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., qx: _Optional[float] = ..., qy: _Optional[float] = ..., qz: _Optional[float] = ..., w: _Optional[float] = ..., yaw: _Optional[float] = ...) -> None: ...

class msgCloudType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
