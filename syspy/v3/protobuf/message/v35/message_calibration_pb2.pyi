from google.protobuf import wrappers_pb2 as _wrappers_pb2
import message_header_pb2 as _message_header_pb2
import message_calibstatus_pb2 as _message_calibstatus_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgCalibProperties(_message.Message):
    __slots__ = ["actionName", "propertyList"]
    ACTIONNAME_FIELD_NUMBER: ClassVar[int]
    PROPERTYLIST_FIELD_NUMBER: ClassVar[int]
    actionName: str
    propertyList: _containers.RepeatedCompositeFieldContainer[msgCalibProperty]
    def __init__(self, actionName: Optional[str] = ..., propertyList: Optional[Iterable[Union[msgCalibProperty, Mapping]]] = ...) -> None: ...

class msgCalibProperty(_message.Message):
    __slots__ = ["boolValue", "bytesValue", "doubleValue", "floatValue", "int32Value", "int64Value", "key", "stringValue", "tag", "type", "uint32Value", "uint64Value"]
    BOOLVALUE_FIELD_NUMBER: ClassVar[int]
    BYTESVALUE_FIELD_NUMBER: ClassVar[int]
    DOUBLEVALUE_FIELD_NUMBER: ClassVar[int]
    FLOATVALUE_FIELD_NUMBER: ClassVar[int]
    INT32VALUE_FIELD_NUMBER: ClassVar[int]
    INT64VALUE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    STRINGVALUE_FIELD_NUMBER: ClassVar[int]
    TAG_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    UINT32VALUE_FIELD_NUMBER: ClassVar[int]
    UINT64VALUE_FIELD_NUMBER: ClassVar[int]
    boolValue: bool
    bytesValue: bytes
    doubleValue: float
    floatValue: float
    int32Value: int
    int64Value: int
    key: str
    stringValue: str
    tag: str
    type: str
    uint32Value: int
    uint64Value: int
    def __init__(self, key: Optional[str] = ..., type: Optional[str] = ..., stringValue: Optional[str] = ..., boolValue: bool = ..., int32Value: Optional[int] = ..., uint32Value: Optional[int] = ..., int64Value: Optional[int] = ..., uint64Value: Optional[int] = ..., floatValue: Optional[float] = ..., doubleValue: Optional[float] = ..., bytesValue: Optional[bytes] = ..., tag: Optional[str] = ...) -> None: ...

class msgCalibration(_message.Message):
    __slots__ = ["calibType", "data", "deviceName", "deviceType", "propertiesList", "status", "taskId"]
    CALIBTYPE_FIELD_NUMBER: ClassVar[int]
    DATA_FIELD_NUMBER: ClassVar[int]
    DEVICENAME_FIELD_NUMBER: ClassVar[int]
    DEVICETYPE_FIELD_NUMBER: ClassVar[int]
    PROPERTIESLIST_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    TASKID_FIELD_NUMBER: ClassVar[int]
    calibType: str
    data: bytes
    deviceName: str
    deviceType: str
    propertiesList: _containers.RepeatedCompositeFieldContainer[msgCalibProperties]
    status: _message_calibstatus_pb2.msgCalibStatus
    taskId: str
    def __init__(self, deviceType: Optional[str] = ..., deviceName: Optional[str] = ..., calibType: Optional[str] = ..., status: Optional[Union[_message_calibstatus_pb2.msgCalibStatus, Mapping]] = ..., data: Optional[bytes] = ..., taskId: Optional[str] = ..., propertiesList: Optional[Iterable[Union[msgCalibProperties, Mapping]]] = ...) -> None: ...

class msgChessBoard(_message.Message):
    __slots__ = ["image", "imageCornerList", "imgHeight", "imgWidth", "objectPointsList", "rpy", "xyz"]
    IMAGECORNERLIST_FIELD_NUMBER: ClassVar[int]
    IMAGE_FIELD_NUMBER: ClassVar[int]
    IMGHEIGHT_FIELD_NUMBER: ClassVar[int]
    IMGWIDTH_FIELD_NUMBER: ClassVar[int]
    OBJECTPOINTSLIST_FIELD_NUMBER: ClassVar[int]
    RPY_FIELD_NUMBER: ClassVar[int]
    XYZ_FIELD_NUMBER: ClassVar[int]
    image: msgImage
    imageCornerList: _containers.RepeatedCompositeFieldContainer[msgTagCorner]
    imgHeight: int
    imgWidth: int
    objectPointsList: _containers.RepeatedCompositeFieldContainer[msgTagXYZ]
    rpy: msgTagRPY
    xyz: msgTagXYZ
    def __init__(self, rpy: Optional[Union[msgTagRPY, Mapping]] = ..., xyz: Optional[Union[msgTagXYZ, Mapping]] = ..., image: Optional[Union[msgImage, Mapping]] = ..., imageCornerList: Optional[Iterable[Union[msgTagCorner, Mapping]]] = ..., objectPointsList: Optional[Iterable[Union[msgTagXYZ, Mapping]]] = ..., imgWidth: Optional[int] = ..., imgHeight: Optional[int] = ...) -> None: ...

class msgImage(_message.Message):
    __slots__ = ["data", "header", "height", "type", "width"]
    DATA_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    HEIGHT_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    data: bytes
    header: _message_header_pb2.msgHeader
    height: int
    type: int
    width: int
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., width: Optional[int] = ..., height: Optional[int] = ..., type: Optional[int] = ..., data: Optional[bytes] = ...) -> None: ...

class msgTagCorner(_message.Message):
    __slots__ = ["pixelX", "pixelY"]
    PIXELX_FIELD_NUMBER: ClassVar[int]
    PIXELY_FIELD_NUMBER: ClassVar[int]
    pixelX: float
    pixelY: float
    def __init__(self, pixelX: Optional[float] = ..., pixelY: Optional[float] = ...) -> None: ...

class msgTagRPY(_message.Message):
    __slots__ = ["pitch", "roll", "yaw"]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    pitch: float
    roll: float
    yaw: float
    def __init__(self, roll: Optional[float] = ..., pitch: Optional[float] = ..., yaw: Optional[float] = ...) -> None: ...

class msgTagXYZ(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...) -> None: ...
