from . import message_header_pb2 as _message_header_pb2
from . import message_motorcmd_pb2 as _message_motorcmd_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgManualSpeed(_message.Message):
    __slots__ = ["rotate", "steerAngles", "x", "y"]
    ROTATE_FIELD_NUMBER: _ClassVar[int]
    STEERANGLES_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    rotate: float
    steerAngles: _containers.RepeatedScalarFieldContainer[float]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., rotate: _Optional[float] = ..., steerAngles: _Optional[_Iterable[float]] = ...) -> None: ...

class msgMultiNavPath(_message.Message):
    __slots__ = ["paths"]
    PATHS_FIELD_NUMBER: _ClassVar[int]
    paths: _containers.RepeatedCompositeFieldContainer[msgNavPath]
    def __init__(self, paths: _Optional[_Iterable[_Union[msgNavPath, _Mapping]]] = ...) -> None: ...

class msgNavInfo(_message.Message):
    __slots__ = ["navCmd", "navMode", "navSpeedW", "navSpeedX", "navSpeedY", "navTargetMode", "navTargetTheta", "navTargetX", "navTargetY", "topoTargetId"]
    class cmd(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    NAVCMD_FIELD_NUMBER: _ClassVar[int]
    NAVMODE_FIELD_NUMBER: _ClassVar[int]
    NAVSPEEDW_FIELD_NUMBER: _ClassVar[int]
    NAVSPEEDX_FIELD_NUMBER: _ClassVar[int]
    NAVSPEEDY_FIELD_NUMBER: _ClassVar[int]
    NAVTARGETMODE_FIELD_NUMBER: _ClassVar[int]
    NAVTARGETTHETA_FIELD_NUMBER: _ClassVar[int]
    NAVTARGETX_FIELD_NUMBER: _ClassVar[int]
    NAVTARGETY_FIELD_NUMBER: _ClassVar[int]
    TOPOTARGETID_FIELD_NUMBER: _ClassVar[int]
    navCmd: msgNavInfo.cmd
    navMode: msgNavInfo.mode
    navSpeedW: float
    navSpeedX: float
    navSpeedY: float
    navTargetMode: float
    navTargetTheta: float
    navTargetX: float
    navTargetY: float
    nullNavCmd: msgNavInfo.cmd
    nullNavMode: msgNavInfo.mode
    speedControlMode: msgNavInfo.mode
    taskBegin: msgNavInfo.cmd
    taskCancel: msgNavInfo.cmd
    taskResume: msgNavInfo.cmd
    taskSuspend: msgNavInfo.cmd
    taskTargetReachMode: msgNavInfo.mode
    topoPosReachMode: msgNavInfo.mode
    topoTargetId: int
    def __init__(self, navMode: _Optional[_Union[msgNavInfo.mode, str]] = ..., navCmd: _Optional[_Union[msgNavInfo.cmd, str]] = ..., navTargetX: _Optional[float] = ..., navTargetY: _Optional[float] = ..., navTargetTheta: _Optional[float] = ..., navTargetMode: _Optional[float] = ..., navSpeedX: _Optional[float] = ..., navSpeedY: _Optional[float] = ..., navSpeedW: _Optional[float] = ..., topoTargetId: _Optional[int] = ...) -> None: ...

class msgNavPath(_message.Message):
    __slots__ = ["findPath", "states"]
    FINDPATH_FIELD_NUMBER: _ClassVar[int]
    STATES_FIELD_NUMBER: _ClassVar[int]
    findPath: bool
    states: _containers.RepeatedCompositeFieldContainer[msgNavState]
    def __init__(self, states: _Optional[_Iterable[_Union[msgNavState, _Mapping]]] = ..., findPath: bool = ...) -> None: ...

class msgNavPose(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ...) -> None: ...

class msgNavSpeed(_message.Message):
    __slots__ = ["header", "isToMove", "motorCmd", "rotate", "x", "y"]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ISTOMOVE_FIELD_NUMBER: _ClassVar[int]
    MOTORCMD_FIELD_NUMBER: _ClassVar[int]
    ROTATE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    header: _message_header_pb2.msgHeader
    isToMove: bool
    motorCmd: _containers.RepeatedCompositeFieldContainer[_message_motorcmd_pb2.msgMotorCmd]
    rotate: float
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., rotate: _Optional[float] = ..., header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., motorCmd: _Optional[_Iterable[_Union[_message_motorcmd_pb2.msgMotorCmd, _Mapping]]] = ..., isToMove: bool = ...) -> None: ...

class msgNavState(_message.Message):
    __slots__ = ["pose", "radius", "speed"]
    POSE_FIELD_NUMBER: _ClassVar[int]
    RADIUS_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    pose: msgNavPose
    radius: float
    speed: msgNavSpeed
    def __init__(self, pose: _Optional[_Union[msgNavPose, _Mapping]] = ..., speed: _Optional[_Union[msgNavSpeed, _Mapping]] = ..., radius: _Optional[float] = ...) -> None: ...

class msgNavStatus(_message.Message):
    __slots__ = ["blocked"]
    BLOCKED_FIELD_NUMBER: _ClassVar[int]
    blocked: bool
    def __init__(self, blocked: bool = ...) -> None: ...

class msgNavTarget(_message.Message):
    __slots__ = ["angle", "runMode", "topoTargetId", "x", "y"]
    class mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    RUNMODE_FIELD_NUMBER: _ClassVar[int]
    TOPOTARGETID_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    backMode: msgNavTarget.mode
    forwardMode: msgNavTarget.mode
    nullMode: msgNavTarget.mode
    runMode: int
    topoTargetId: int
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ..., runMode: _Optional[int] = ..., topoTargetId: _Optional[int] = ...) -> None: ...

class msgNavTopoPose(_message.Message):
    __slots__ = ["angle", "id"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    angle: float
    id: int
    def __init__(self, id: _Optional[int] = ..., angle: _Optional[float] = ...) -> None: ...
