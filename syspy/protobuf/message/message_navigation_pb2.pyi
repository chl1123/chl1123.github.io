import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_ManualSpeed(_message.Message):
    __slots__ = ["rotate", "steer_angles", "x", "y"]
    ROTATE_FIELD_NUMBER: ClassVar[int]
    STEER_ANGLES_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    rotate: float
    steer_angles: _containers.RepeatedScalarFieldContainer[float]
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., rotate: Optional[float] = ..., steer_angles: Optional[Iterable[float]] = ...) -> None: ...

class Message_MotorCmd(_message.Message):
    __slots__ = ["can_id", "can_router", "io_cmd", "motor_name", "move_type", "type", "value"]
    class IOCmd(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class MotorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class MoveType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ACC: Message_MotorCmd.MoveType
    CAN_ID_FIELD_NUMBER: ClassVar[int]
    CAN_ROUTER_FIELD_NUMBER: ClassVar[int]
    CMD_NONE: Message_MotorCmd.IOCmd
    DEC: Message_MotorCmd.MoveType
    DO: Message_MotorCmd.MotorType
    IO_CMD_FIELD_NUMBER: ClassVar[int]
    LINEAR: Message_MotorCmd.MotorType
    MOTOR_NAME_FIELD_NUMBER: ClassVar[int]
    MOVE_TYPE_FIELD_NUMBER: ClassVar[int]
    NORMAL: Message_MotorCmd.MoveType
    ROTATION: Message_MotorCmd.MotorType
    SPIN: Message_MotorCmd.MotorType
    STEER: Message_MotorCmd.MotorType
    STOP: Message_MotorCmd.IOCmd
    TO_NEGATIVE: Message_MotorCmd.IOCmd
    TO_POSITIVE: Message_MotorCmd.IOCmd
    TYPE_FIELD_NUMBER: ClassVar[int]
    VALUE_FIELD_NUMBER: ClassVar[int]
    WALK: Message_MotorCmd.MotorType
    can_id: int
    can_router: int
    io_cmd: Message_MotorCmd.IOCmd
    motor_name: str
    move_type: Message_MotorCmd.MoveType
    type: Message_MotorCmd.MotorType
    value: float
    def __init__(self, motor_name: Optional[str] = ..., can_router: Optional[int] = ..., can_id: Optional[int] = ..., value: Optional[float] = ..., io_cmd: Optional[Union[Message_MotorCmd.IOCmd, str]] = ..., type: Optional[Union[Message_MotorCmd.MotorType, str]] = ..., move_type: Optional[Union[Message_MotorCmd.MoveType, str]] = ...) -> None: ...

class Message_NavInfo(_message.Message):
    __slots__ = ["nav_cmd", "nav_mode", "nav_speed_w", "nav_speed_x", "nav_speed_y", "nav_target_mode", "nav_target_theta", "nav_target_x", "nav_target_y", "topo_target_id"]
    class NavCmd(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class NavMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    NAV_CMD_FIELD_NUMBER: ClassVar[int]
    NAV_MODE_FIELD_NUMBER: ClassVar[int]
    NAV_SPEED_W_FIELD_NUMBER: ClassVar[int]
    NAV_SPEED_X_FIELD_NUMBER: ClassVar[int]
    NAV_SPEED_Y_FIELD_NUMBER: ClassVar[int]
    NAV_TARGET_MODE_FIELD_NUMBER: ClassVar[int]
    NAV_TARGET_THETA_FIELD_NUMBER: ClassVar[int]
    NAV_TARGET_X_FIELD_NUMBER: ClassVar[int]
    NAV_TARGET_Y_FIELD_NUMBER: ClassVar[int]
    NULLNavCmd: Message_NavInfo.NavCmd
    NullNavMode: Message_NavInfo.NavMode
    SpeedControlMode: Message_NavInfo.NavMode
    TOPO_TARGET_ID_FIELD_NUMBER: ClassVar[int]
    TaskBegin: Message_NavInfo.NavCmd
    TaskCancel: Message_NavInfo.NavCmd
    TaskResume: Message_NavInfo.NavCmd
    TaskSuspend: Message_NavInfo.NavCmd
    TaskTargetReachMode: Message_NavInfo.NavMode
    TopoPosReachMode: Message_NavInfo.NavMode
    nav_cmd: int
    nav_mode: int
    nav_speed_w: float
    nav_speed_x: float
    nav_speed_y: float
    nav_target_mode: float
    nav_target_theta: float
    nav_target_x: float
    nav_target_y: float
    topo_target_id: int
    def __init__(self, nav_mode: Optional[int] = ..., nav_cmd: Optional[int] = ..., nav_target_x: Optional[float] = ..., nav_target_y: Optional[float] = ..., nav_target_theta: Optional[float] = ..., nav_target_mode: Optional[float] = ..., nav_speed_x: Optional[float] = ..., nav_speed_y: Optional[float] = ..., nav_speed_w: Optional[float] = ..., topo_target_id: Optional[int] = ...) -> None: ...

class Message_NavPath(_message.Message):
    __slots__ = ["find_path", "states"]
    FIND_PATH_FIELD_NUMBER: ClassVar[int]
    STATES_FIELD_NUMBER: ClassVar[int]
    find_path: bool
    states: _containers.RepeatedCompositeFieldContainer[Message_NavState]
    def __init__(self, states: Optional[Iterable[Union[Message_NavState, Mapping]]] = ..., find_path: bool = ...) -> None: ...

class Message_NavPose(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ...) -> None: ...

class Message_NavSpeed(_message.Message):
    __slots__ = ["header", "is2move", "motor_cmd", "rotate", "x", "y"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    IS2MOVE_FIELD_NUMBER: ClassVar[int]
    MOTOR_CMD_FIELD_NUMBER: ClassVar[int]
    ROTATE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.Message_Header
    is2move: bool
    motor_cmd: _containers.RepeatedCompositeFieldContainer[Message_MotorCmd]
    rotate: float
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., rotate: Optional[float] = ..., header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., motor_cmd: Optional[Iterable[Union[Message_MotorCmd, Mapping]]] = ..., is2move: bool = ...) -> None: ...

class Message_NavState(_message.Message):
    __slots__ = ["pose", "radius", "speed"]
    POSE_FIELD_NUMBER: ClassVar[int]
    RADIUS_FIELD_NUMBER: ClassVar[int]
    SPEED_FIELD_NUMBER: ClassVar[int]
    pose: Message_NavPose
    radius: float
    speed: Message_NavSpeed
    def __init__(self, pose: Optional[Union[Message_NavPose, Mapping]] = ..., speed: Optional[Union[Message_NavSpeed, Mapping]] = ..., radius: Optional[float] = ...) -> None: ...

class Message_NavStatus(_message.Message):
    __slots__ = ["blocked"]
    BLOCKED_FIELD_NUMBER: ClassVar[int]
    blocked: bool
    def __init__(self, blocked: bool = ...) -> None: ...

class Message_NavTarget(_message.Message):
    __slots__ = ["angle", "run_mode", "topo_target_id", "x", "y"]
    class MODE(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ANGLE_FIELD_NUMBER: ClassVar[int]
    BACK_MODE: Message_NavTarget.MODE
    FORWARD_MODE: Message_NavTarget.MODE
    NULL_MODE: Message_NavTarget.MODE
    RUN_MODE_FIELD_NUMBER: ClassVar[int]
    TOPO_TARGET_ID_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    run_mode: int
    topo_target_id: int
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ..., run_mode: Optional[int] = ..., topo_target_id: Optional[int] = ...) -> None: ...

class Message_NavTopoPose(_message.Message):
    __slots__ = ["angle", "id"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    angle: float
    id: int
    def __init__(self, id: Optional[int] = ..., angle: Optional[float] = ...) -> None: ...
