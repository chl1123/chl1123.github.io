# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_header_p2p import Message_Header
from enum import IntEnum
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class Message_NavStatus(BaseModel):
    blocked: bool = Field(default=False)


class Message_MotorCmd(BaseModel):
    class MotorType(IntEnum):
        WALK = 0
        STEER = 1
        SPIN = 2
        LINEAR = 3
        ROTATION = 4
        DO = 5

    class IOCmd(IntEnum):
        CMD_NONE = 0
        TO_POSITIVE = 1
        TO_NEGATIVE = 2
        STOP = 3

    class MoveType(IntEnum):
        NORMAL = 0
        ACC = 1
        DEC = 2

    motor_name: str = Field(default="")
    can_router: int = Field(default=0)
    can_id: int = Field(default=0)
    value: float = Field(default=0.0)
    io_cmd: "Message_MotorCmd.IOCmd" = Field(default=0)
    type: "Message_MotorCmd.MotorType" = Field(default=0)
    move_type: "Message_MotorCmd.MoveType" = Field(default=0)


class Message_NavSpeed(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    rotate: float = Field(default=0.0)
    header: typing.Optional[Message_Header] = None
    motor_cmd: typing.List[Message_MotorCmd] = Field(default_factory=list)
    is2move: bool = Field(default=False)  # 准备动的标志位


class Message_ManualSpeed(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    rotate: float = Field(default=0.0)
    steer_angles: typing.List[float] = Field(default_factory=list)


class Message_NavPose(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    angle: float = Field(default=0.0)


class Message_NavTopoPose(BaseModel):
    id: int = Field(default=0)
    angle: float = Field(default=0.0)


class Message_NavState(BaseModel):
    pose: typing.Optional[Message_NavPose] = None
    speed: typing.Optional[Message_NavSpeed] = None
    radius: float = Field(default=0.0)


class Message_NavPath(BaseModel):
    states: typing.List[Message_NavState] = Field(default_factory=list)
    find_path: bool = Field(default=False)


class Message_NavTarget(BaseModel):
    class MODE(IntEnum):
        NULL_MODE = 0
        FORWARD_MODE = 1
        BACK_MODE = 2

    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    angle: float = Field(default=0.0)
    run_mode: int = Field(default=0)
    topo_target_id: int = Field(default=0)


class Message_NavInfo(BaseModel):
    class NavMode(IntEnum):
        NullNavMode = 0
        TaskTargetReachMode = 1
        SpeedControlMode = 2
        TopoPosReachMode = 3

    class NavCmd(IntEnum):
        NULLNavCmd = 0
        TaskCancel = 1
        TaskSuspend = 2
        TaskResume = 3
        TaskBegin = 4

    nav_mode: int = Field(default=0)
    nav_cmd: int = Field(default=0)
    nav_target_x: float = Field(default=0.0)
    nav_target_y: float = Field(default=0.0)
    nav_target_theta: float = Field(default=0.0)
    nav_target_mode: float = Field(default=0.0)
    nav_speed_x: float = Field(default=0.0)
    nav_speed_y: float = Field(default=0.0)
    nav_speed_w: float = Field(default=0.0)
    topo_target_id: int = Field(default=0)
