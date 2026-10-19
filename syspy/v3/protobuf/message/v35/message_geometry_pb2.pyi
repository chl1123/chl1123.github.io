import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgPoint(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...) -> None: ...

class msgPointStamped(_message.Message):
    __slots__ = ["header", "point"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    POINT_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    point: msgPoint
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., point: Optional[Union[msgPoint, Mapping]] = ...) -> None: ...

class msgPolygon(_message.Message):
    __slots__ = ["points"]
    POINTS_FIELD_NUMBER: ClassVar[int]
    points: _containers.RepeatedCompositeFieldContainer[msgPoint]
    def __init__(self, points: Optional[Iterable[Union[msgPoint, Mapping]]] = ...) -> None: ...

class msgPolygonStamped(_message.Message):
    __slots__ = ["header", "polygon"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    POLYGON_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    polygon: msgPolygon
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., polygon: Optional[Union[msgPolygon, Mapping]] = ...) -> None: ...

class msgPose(_message.Message):
    __slots__ = ["orientation", "position"]
    ORIENTATION_FIELD_NUMBER: ClassVar[int]
    POSITION_FIELD_NUMBER: ClassVar[int]
    orientation: msgQuaternion
    position: msgPoint
    def __init__(self, position: Optional[Union[msgPoint, Mapping]] = ..., orientation: Optional[Union[msgQuaternion, Mapping]] = ...) -> None: ...

class msgPoseArray(_message.Message):
    __slots__ = ["header", "poses"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    POSES_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    poses: _containers.RepeatedCompositeFieldContainer[msgPose]
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., poses: Optional[Iterable[Union[msgPose, Mapping]]] = ...) -> None: ...

class msgPoseStamped(_message.Message):
    __slots__ = ["header", "pose"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    POSE_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    pose: msgPose
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., pose: Optional[Union[msgPose, Mapping]] = ...) -> None: ...

class msgPoseWithCovariance(_message.Message):
    __slots__ = ["covariance", "pose"]
    COVARIANCE_FIELD_NUMBER: ClassVar[int]
    POSE_FIELD_NUMBER: ClassVar[int]
    covariance: _containers.RepeatedScalarFieldContainer[float]
    pose: msgPose
    def __init__(self, pose: Optional[Union[msgPose, Mapping]] = ..., covariance: Optional[Iterable[float]] = ...) -> None: ...

class msgPoseWithCovarianceStamped(_message.Message):
    __slots__ = ["header", "pose"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    POSE_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    pose: msgPoseWithCovariance
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., pose: Optional[Union[msgPoseWithCovariance, Mapping]] = ...) -> None: ...

class msgQuaternion(_message.Message):
    __slots__ = ["w", "x", "y", "z"]
    W_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    w: float
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., w: Optional[float] = ...) -> None: ...

class msgQuaternionStamped(_message.Message):
    __slots__ = ["header", "quaternion"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    QUATERNION_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    quaternion: msgQuaternion
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., quaternion: Optional[Union[msgQuaternion, Mapping]] = ...) -> None: ...

class msgTransform(_message.Message):
    __slots__ = ["rotation", "translation"]
    ROTATION_FIELD_NUMBER: ClassVar[int]
    TRANSLATION_FIELD_NUMBER: ClassVar[int]
    rotation: msgQuaternion
    translation: msgVector3
    def __init__(self, translation: Optional[Union[msgVector3, Mapping]] = ..., rotation: Optional[Union[msgQuaternion, Mapping]] = ...) -> None: ...

class msgTransformStamped(_message.Message):
    __slots__ = ["childFrameId", "header", "transform"]
    CHILDFRAMEID_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    TRANSFORM_FIELD_NUMBER: ClassVar[int]
    childFrameId: str
    header: _message_header_pb2.msgHeader
    transform: msgTransform
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., childFrameId: Optional[str] = ..., transform: Optional[Union[msgTransform, Mapping]] = ...) -> None: ...

class msgTwist(_message.Message):
    __slots__ = ["angular", "linear"]
    ANGULAR_FIELD_NUMBER: ClassVar[int]
    LINEAR_FIELD_NUMBER: ClassVar[int]
    angular: msgVector3
    linear: msgVector3
    def __init__(self, linear: Optional[Union[msgVector3, Mapping]] = ..., angular: Optional[Union[msgVector3, Mapping]] = ...) -> None: ...

class msgTwistStamped(_message.Message):
    __slots__ = ["header", "twist"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    TWIST_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    twist: msgTwist
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., twist: Optional[Union[msgTwist, Mapping]] = ...) -> None: ...

class msgTwistWithCovariance(_message.Message):
    __slots__ = ["covariance", "twist"]
    COVARIANCE_FIELD_NUMBER: ClassVar[int]
    TWIST_FIELD_NUMBER: ClassVar[int]
    covariance: _containers.RepeatedScalarFieldContainer[float]
    twist: msgTwist
    def __init__(self, twist: Optional[Union[msgTwist, Mapping]] = ..., covariance: Optional[Iterable[float]] = ...) -> None: ...

class msgTwistWithCovarianceStamped(_message.Message):
    __slots__ = ["header", "twist"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    TWIST_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    twist: msgTwistWithCovariance
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., twist: Optional[Union[msgTwistWithCovariance, Mapping]] = ...) -> None: ...

class msgVector3(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...) -> None: ...

class msgVector3Stamped(_message.Message):
    __slots__ = ["header", "vector"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    VECTOR_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    vector: msgVector3
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., vector: Optional[Union[msgVector3, Mapping]] = ...) -> None: ...
