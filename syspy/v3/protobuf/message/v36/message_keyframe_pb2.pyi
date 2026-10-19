from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class keyFrame(_message.Message):
    __slots__ = ["localPose", "pointCloud", "time"]
    LOCALPOSE_FIELD_NUMBER: _ClassVar[int]
    POINTCLOUD_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    localPose: pose2d
    pointCloud: pointCloudXYZ
    time: int
    def __init__(self, time: _Optional[int] = ..., localPose: _Optional[_Union[pose2d, _Mapping]] = ..., pointCloud: _Optional[_Union[pointCloudXYZ, _Mapping]] = ...) -> None: ...

class msg3DKeyframe(_message.Message):
    __slots__ = ["pointCloud", "pose"]
    POINTCLOUD_FIELD_NUMBER: _ClassVar[int]
    POSE_FIELD_NUMBER: _ClassVar[int]
    pointCloud: msgPointCloudData
    pose: msgPose6DOFWithTime
    def __init__(self, pose: _Optional[_Union[msgPose6DOFWithTime, _Mapping]] = ..., pointCloud: _Optional[_Union[msgPointCloudData, _Mapping]] = ...) -> None: ...

class msgKeyFrameLog(_message.Message):
    __slots__ = ["keyFrame", "roughGlobalPoseInBegin"]
    KEYFRAME_FIELD_NUMBER: _ClassVar[int]
    ROUGHGLOBALPOSEINBEGIN_FIELD_NUMBER: _ClassVar[int]
    keyFrame: _containers.RepeatedCompositeFieldContainer[keyFrame]
    roughGlobalPoseInBegin: pose2d
    def __init__(self, keyFrame: _Optional[_Iterable[_Union[keyFrame, _Mapping]]] = ..., roughGlobalPoseInBegin: _Optional[_Union[pose2d, _Mapping]] = ...) -> None: ...

class msgPointCloudData(_message.Message):
    __slots__ = ["data", "type"]
    DATA_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    data: bytes
    type: int
    def __init__(self, type: _Optional[int] = ..., data: _Optional[bytes] = ...) -> None: ...

class msgPose6DOFWithTime(_message.Message):
    __slots__ = ["pitch", "roll", "timestamp", "x", "y", "yaw", "z"]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    pitch: float
    roll: float
    timestamp: float
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., roll: _Optional[float] = ..., pitch: _Optional[float] = ..., yaw: _Optional[float] = ..., timestamp: _Optional[float] = ...) -> None: ...

class pointCloudXYZ(_message.Message):
    __slots__ = ["point"]
    POINT_FIELD_NUMBER: _ClassVar[int]
    point: _containers.RepeatedCompositeFieldContainer[pointXYZ]
    def __init__(self, point: _Optional[_Iterable[_Union[pointXYZ, _Mapping]]] = ...) -> None: ...

class pointXYZ(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class pose2d(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ...) -> None: ...
