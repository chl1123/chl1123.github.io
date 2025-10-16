import message_header_pb2 as _message_header_pb2
import message_calibration_pb2 as _message_calibration_pb2
import message_geometry_pb2 as _message_geometry_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor
POINT_XYZ: msgCloudType
POINT_XYZI: msgCloudType
POINT_XYZRGB: msgCloudType
POINT_XYZRGBA: msgCloudType

class msgPointCloud(_message.Message):
    __slots__ = ["data", "height", "isDense", "type", "width"]
    DATA_FIELD_NUMBER: ClassVar[int]
    HEIGHT_FIELD_NUMBER: ClassVar[int]
    ISDENSE_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    data: bytes
    height: int
    isDense: bool
    type: msgCloudType
    width: int
    def __init__(self, width: Optional[int] = ..., height: Optional[int] = ..., isDense: bool = ..., type: Optional[Union[msgCloudType, str]] = ..., data: Optional[bytes] = ...) -> None: ...

class msgRecognizeResult(_message.Message):
    __slots__ = ["ID", "header", "info", "objectMessage", "obstaclePolygon", "palletWidth", "qx", "qy", "qz", "resultImg", "type", "valid", "w", "x", "y", "yaw", "z"]
    CLASS_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID: str
    ID_FIELD_NUMBER: ClassVar[int]
    INFO_FIELD_NUMBER: ClassVar[int]
    OBJECTMESSAGE_FIELD_NUMBER: ClassVar[int]
    OBSTACLEPOLYGON_FIELD_NUMBER: ClassVar[int]
    PALLETWIDTH_FIELD_NUMBER: ClassVar[int]
    QX_FIELD_NUMBER: ClassVar[int]
    QY_FIELD_NUMBER: ClassVar[int]
    QZ_FIELD_NUMBER: ClassVar[int]
    RESULTIMG_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    VALID_FIELD_NUMBER: ClassVar[int]
    W_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    info: str
    objectMessage: str
    obstaclePolygon: _containers.RepeatedCompositeFieldContainer[_message_geometry_pb2.msgPolygon]
    palletWidth: float
    qx: float
    qy: float
    qz: float
    resultImg: str
    type: str
    valid: bool
    w: float
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., valid: bool = ..., type: Optional[str] = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., qx: Optional[float] = ..., qy: Optional[float] = ..., qz: Optional[float] = ..., w: Optional[float] = ..., yaw: Optional[float] = ..., resultImg: Optional[str] = ..., palletWidth: Optional[float] = ..., objectMessage: Optional[str] = ..., obstaclePolygon: Optional[Iterable[Union[_message_geometry_pb2.msgPolygon, Mapping]]] = ..., ID: Optional[str] = ..., info: Optional[str] = ..., **kwargs) -> None: ...

class msgRecognizeResultList(_message.Message):
    __slots__ = ["error", "img", "irImg", "logMsg", "pointCloud", "recoList", "recoStatus", "taskID"]
    class errorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ERROR_FIELD_NUMBER: ClassVar[int]
    IMG_FIELD_NUMBER: ClassVar[int]
    IRIMG_FIELD_NUMBER: ClassVar[int]
    LOGMSG_FIELD_NUMBER: ClassVar[int]
    POINTCLOUD_FIELD_NUMBER: ClassVar[int]
    RECOLIST_FIELD_NUMBER: ClassVar[int]
    RECOSTATUS_FIELD_NUMBER: ClassVar[int]
    TASKID_FIELD_NUMBER: ClassVar[int]
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
    recoList: _containers.RepeatedCompositeFieldContainer[msgRecognizeResult]
    recoStatus: msgRecognizeResultList.status
    resultEmpty: msgRecognizeResultList.errorType
    running: msgRecognizeResultList.status
    success: msgRecognizeResultList.status
    taskID: str
    def __init__(self, recoList: Optional[Iterable[Union[msgRecognizeResult, Mapping]]] = ..., recoStatus: Optional[Union[msgRecognizeResultList.status, str]] = ..., taskID: Optional[str] = ..., img: Optional[Union[_message_calibration_pb2.msgImage, Mapping]] = ..., irImg: Optional[Union[_message_calibration_pb2.msgImage, Mapping]] = ..., pointCloud: Optional[Union[msgPointCloud, Mapping]] = ..., logMsg: Optional[str] = ..., error: Optional[Union[msgRecognizeResultList.errorType, str]] = ...) -> None: ...

class msgCloudType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
