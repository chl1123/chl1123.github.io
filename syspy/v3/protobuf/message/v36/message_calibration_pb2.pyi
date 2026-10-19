from google.protobuf import wrappers_pb2 as _wrappers_pb2
from . import message_header_pb2 as _message_header_pb2
from . import message_calibstatus_pb2 as _message_calibstatus_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgCalibProperties(_message.Message):
    __slots__ = ["actionName", "propertyList"]
    ACTIONNAME_FIELD_NUMBER: _ClassVar[int]
    PROPERTYLIST_FIELD_NUMBER: _ClassVar[int]
    actionName: str
    propertyList: _containers.RepeatedCompositeFieldContainer[msgCalibProperty]
    def __init__(self, actionName: _Optional[str] = ..., propertyList: _Optional[_Iterable[_Union[msgCalibProperty, _Mapping]]] = ...) -> None: ...

class msgCalibProperty(_message.Message):
    __slots__ = ["boolValue", "bytesValue", "doubleValue", "floatValue", "int32Value", "int64Value", "key", "stringValue", "tag", "type", "uint32Value", "uint64Value"]
    BOOLVALUE_FIELD_NUMBER: _ClassVar[int]
    BYTESVALUE_FIELD_NUMBER: _ClassVar[int]
    DOUBLEVALUE_FIELD_NUMBER: _ClassVar[int]
    FLOATVALUE_FIELD_NUMBER: _ClassVar[int]
    INT32VALUE_FIELD_NUMBER: _ClassVar[int]
    INT64VALUE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    STRINGVALUE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    UINT32VALUE_FIELD_NUMBER: _ClassVar[int]
    UINT64VALUE_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, key: _Optional[str] = ..., type: _Optional[str] = ..., stringValue: _Optional[str] = ..., boolValue: bool = ..., int32Value: _Optional[int] = ..., uint32Value: _Optional[int] = ..., int64Value: _Optional[int] = ..., uint64Value: _Optional[int] = ..., floatValue: _Optional[float] = ..., doubleValue: _Optional[float] = ..., bytesValue: _Optional[bytes] = ..., tag: _Optional[str] = ...) -> None: ...

class msgCalibration(_message.Message):
    __slots__ = ["calibType", "data", "deviceName", "deviceType", "propertiesList", "status", "taskId"]
    CALIBTYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    DEVICENAME_FIELD_NUMBER: _ClassVar[int]
    DEVICETYPE_FIELD_NUMBER: _ClassVar[int]
    PROPERTIESLIST_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    calibType: str
    data: bytes
    deviceName: str
    deviceType: str
    propertiesList: _containers.RepeatedCompositeFieldContainer[msgCalibProperties]
    status: _message_calibstatus_pb2.msgCalibStatus
    taskId: str
    def __init__(self, deviceType: _Optional[str] = ..., deviceName: _Optional[str] = ..., calibType: _Optional[str] = ..., status: _Optional[_Union[_message_calibstatus_pb2.msgCalibStatus, _Mapping]] = ..., data: _Optional[bytes] = ..., taskId: _Optional[str] = ..., propertiesList: _Optional[_Iterable[_Union[msgCalibProperties, _Mapping]]] = ...) -> None: ...

class msgChessBoard(_message.Message):
    __slots__ = ["image", "imageCornerList", "imgHeight", "imgWidth", "objectPointsList", "rpy", "xyz"]
    IMAGECORNERLIST_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    IMGHEIGHT_FIELD_NUMBER: _ClassVar[int]
    IMGWIDTH_FIELD_NUMBER: _ClassVar[int]
    OBJECTPOINTSLIST_FIELD_NUMBER: _ClassVar[int]
    RPY_FIELD_NUMBER: _ClassVar[int]
    XYZ_FIELD_NUMBER: _ClassVar[int]
    image: msgImage
    imageCornerList: _containers.RepeatedCompositeFieldContainer[msgTagCorner]
    imgHeight: int
    imgWidth: int
    objectPointsList: _containers.RepeatedCompositeFieldContainer[msgTagXYZ]
    rpy: msgTagRPY
    xyz: msgTagXYZ
    def __init__(self, rpy: _Optional[_Union[msgTagRPY, _Mapping]] = ..., xyz: _Optional[_Union[msgTagXYZ, _Mapping]] = ..., image: _Optional[_Union[msgImage, _Mapping]] = ..., imageCornerList: _Optional[_Iterable[_Union[msgTagCorner, _Mapping]]] = ..., objectPointsList: _Optional[_Iterable[_Union[msgTagXYZ, _Mapping]]] = ..., imgWidth: _Optional[int] = ..., imgHeight: _Optional[int] = ...) -> None: ...

class msgImage(_message.Message):
    __slots__ = ["data", "header", "height", "type", "width"]
    DATA_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    header: _message_header_pb2.msgHeader
    height: int
    type: int
    width: int
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., width: _Optional[int] = ..., height: _Optional[int] = ..., type: _Optional[int] = ..., data: _Optional[bytes] = ...) -> None: ...

class msgTagCorner(_message.Message):
    __slots__ = ["pixelX", "pixelY"]
    PIXELX_FIELD_NUMBER: _ClassVar[int]
    PIXELY_FIELD_NUMBER: _ClassVar[int]
    pixelX: float
    pixelY: float
    def __init__(self, pixelX: _Optional[float] = ..., pixelY: _Optional[float] = ...) -> None: ...

class msgTagRPY(_message.Message):
    __slots__ = ["pitch", "roll", "yaw"]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    pitch: float
    roll: float
    yaw: float
    def __init__(self, roll: _Optional[float] = ..., pitch: _Optional[float] = ..., yaw: _Optional[float] = ...) -> None: ...

class msgTagXYZ(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...
