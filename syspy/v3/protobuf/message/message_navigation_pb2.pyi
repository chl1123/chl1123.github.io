import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgManualSpeed(_message.Message):
    __slots__ = ["rotate", "steerAngles", "x", "y"]
    ROTATE_FIELD_NUMBER: ClassVar[int]
    STEERANGLES_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    rotate: float
    steerAngles: _containers.RepeatedScalarFieldContainer[float]
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., rotate: Optional[float] = ..., steerAngles: Optional[Iterable[float]] = ...) -> None: ...

class msgMotorCmd(_message.Message):
    __slots__ = ["canId", "canRouter", "ioCmd", "motorName", "moveType", "type", "value"]
    class cmd(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class mType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class motorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CANID_FIELD_NUMBER: ClassVar[int]
    CANROUTER_FIELD_NUMBER: ClassVar[int]
    IOCMD_FIELD_NUMBER: ClassVar[int]
    MOTORNAME_FIELD_NUMBER: ClassVar[int]
    MOVETYPE_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    VALUE_FIELD_NUMBER: ClassVar[int]
    acc: msgMotorCmd.mType
    canId: int
    canRouter: int
    cmdNone: msgMotorCmd.cmd
    dec: msgMotorCmd.mType
    do: msgMotorCmd.motorType
    ioCmd: msgMotorCmd.cmd
    linear: msgMotorCmd.motorType
    motorName: str
    moveType: msgMotorCmd.mType
    normal: msgMotorCmd.mType
    rotation: msgMotorCmd.motorType
    spin: msgMotorCmd.motorType
    steer: msgMotorCmd.motorType
    stop: msgMotorCmd.cmd
    toNegative: msgMotorCmd.cmd
    toPositive: msgMotorCmd.cmd
    type: msgMotorCmd.motorType
    value: float
    walk: msgMotorCmd.motorType
    def __init__(self, motorName: Optional[str] = ..., canRouter: Optional[int] = ..., canId: Optional[int] = ..., value: Optional[float] = ..., ioCmd: Optional[Union[msgMotorCmd.cmd, str]] = ..., type: Optional[Union[msgMotorCmd.motorType, str]] = ..., moveType: Optional[Union[msgMotorCmd.mType, str]] = ...) -> None: ...

class msgMultiNavPath(_message.Message):
    __slots__ = ["paths"]
    PATHS_FIELD_NUMBER: ClassVar[int]
    paths: _containers.RepeatedCompositeFieldContainer[msgNavPath]
    def __init__(self, paths: Optional[Iterable[Union[msgNavPath, Mapping]]] = ...) -> None: ...

class msgNavInfo(_message.Message):
    __slots__ = ["navCmd", "navMode", "navSpeedW", "navSpeedX", "navSpeedY", "navTargetMode", "navTargetTheta", "navTargetX", "navTargetY", "topoTargetId"]
    class cmd(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    NAVCMD_FIELD_NUMBER: ClassVar[int]
    NAVMODE_FIELD_NUMBER: ClassVar[int]
    NAVSPEEDW_FIELD_NUMBER: ClassVar[int]
    NAVSPEEDX_FIELD_NUMBER: ClassVar[int]
    NAVSPEEDY_FIELD_NUMBER: ClassVar[int]
    NAVTARGETMODE_FIELD_NUMBER: ClassVar[int]
    NAVTARGETTHETA_FIELD_NUMBER: ClassVar[int]
    NAVTARGETX_FIELD_NUMBER: ClassVar[int]
    NAVTARGETY_FIELD_NUMBER: ClassVar[int]
    TOPOTARGETID_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, navMode: Optional[Union[msgNavInfo.mode, str]] = ..., navCmd: Optional[Union[msgNavInfo.cmd, str]] = ..., navTargetX: Optional[float] = ..., navTargetY: Optional[float] = ..., navTargetTheta: Optional[float] = ..., navTargetMode: Optional[float] = ..., navSpeedX: Optional[float] = ..., navSpeedY: Optional[float] = ..., navSpeedW: Optional[float] = ..., topoTargetId: Optional[int] = ...) -> None: ...

class msgNavPath(_message.Message):
    __slots__ = ["findPath", "states"]
    FINDPATH_FIELD_NUMBER: ClassVar[int]
    STATES_FIELD_NUMBER: ClassVar[int]
    findPath: bool
    states: _containers.RepeatedCompositeFieldContainer[msgNavState]
    def __init__(self, states: Optional[Iterable[Union[msgNavState, Mapping]]] = ..., findPath: bool = ...) -> None: ...

class msgNavPose(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ...) -> None: ...

class msgNavSpeed(_message.Message):
    __slots__ = ["header", "isToMove", "motorCmd", "rotate", "x", "y"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ISTOMOVE_FIELD_NUMBER: ClassVar[int]
    MOTORCMD_FIELD_NUMBER: ClassVar[int]
    ROTATE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    isToMove: bool
    motorCmd: _containers.RepeatedCompositeFieldContainer[msgMotorCmd]
    rotate: float
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., rotate: Optional[float] = ..., header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., motorCmd: Optional[Iterable[Union[msgMotorCmd, Mapping]]] = ..., isToMove: bool = ...) -> None: ...

class msgNavState(_message.Message):
    __slots__ = ["pose", "radius", "speed"]
    POSE_FIELD_NUMBER: ClassVar[int]
    RADIUS_FIELD_NUMBER: ClassVar[int]
    SPEED_FIELD_NUMBER: ClassVar[int]
    pose: msgNavPose
    radius: float
    speed: msgNavSpeed
    def __init__(self, pose: Optional[Union[msgNavPose, Mapping]] = ..., speed: Optional[Union[msgNavSpeed, Mapping]] = ..., radius: Optional[float] = ...) -> None: ...

class msgNavStatus(_message.Message):
    __slots__ = ["blocked"]
    BLOCKED_FIELD_NUMBER: ClassVar[int]
    blocked: bool
    def __init__(self, blocked: bool = ...) -> None: ...

class msgNavTarget(_message.Message):
    __slots__ = ["angle", "runMode", "topoTargetId", "x", "y"]
    class mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ANGLE_FIELD_NUMBER: ClassVar[int]
    RUNMODE_FIELD_NUMBER: ClassVar[int]
    TOPOTARGETID_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    backMode: msgNavTarget.mode
    forwardMode: msgNavTarget.mode
    nullMode: msgNavTarget.mode
    runMode: int
    topoTargetId: int
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ..., runMode: Optional[int] = ..., topoTargetId: Optional[int] = ...) -> None: ...

class msgNavTopoPose(_message.Message):
    __slots__ = ["angle", "id"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    angle: float
    id: int
    def __init__(self, id: Optional[int] = ..., angle: Optional[float] = ...) -> None: ...
