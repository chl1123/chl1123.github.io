# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing
from enum import IntEnum

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field

from .message_header_p2p import Message_Header


class Message_NavStatus(BaseModel):
    """表示导航状态的模型类。

    Attributes:
        blocked (bool): 表示是否被阻挡的标志，默认值为False，即未被阻挡。
    """
    blocked: bool = Field(default=False)


class Message_MotorCmd(BaseModel):
    """表示电机控制命令的模型类。

    Attributes:
        motor_name (str): 电机的名称，默认值为空字符串。
        can_router (int): CAN路由器的编号，默认值为0。
        can_id (int): CAN总线的ID，默认值为0。
        value (float): 电机控制的数值，默认值为0.0。
        io_cmd (Message_MotorCmd.IOCmd): IO命令，默认值为IOCmd.CMD_NONE（值为0）。
        type (Message_MotorCmd.MotorType): 电机类型，默认值为MotorType.WALK（值为0）。
        move_type (Message_MotorCmd.MoveType): 移动类型，默认值为MoveType.NORMAL（值为0）。
    """

    class MotorType(IntEnum):
        """电机类型的枚举类。

        Attributes:
            WALK (0): 行走电机类型
            STEER (1): 转向电机类型
            SPIN (2): 旋转电机类型
            LINEAR (3): 线性电机类型
            ROTATION (4): 回转电机类型
            DO (5): 数字输出电机类型
        """
        WALK = 0
        STEER = 1
        SPIN = 2
        LINEAR = 3
        ROTATION = 4
        DO = 5

    class IOCmd(IntEnum):
        """IO命令的枚举类。

        Attributes:
            CMD_NONE (0): 无命令
            TO_POSITIVE (1): 向正方向的命令
            TO_NEGATIVE (2): 向负方向的命令
            STOP (3): 停止命令
        """
        CMD_NONE = 0
        TO_POSITIVE = 1
        TO_NEGATIVE = 2
        STOP = 3

    class MoveType(IntEnum):
        """移动类型的枚举类。

        Attributes:
            NORMAL (0): 正常移动类型
            ACC (1): 加速移动类型
            DEC (2): 减速移动类型
        """
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
    """表示导航速度的模型类。

    Attributes:
        x (float): x方向的速度值，默认值为0.0。
        y (float): y方向的速度值，默认值为0.0。
        rotate (float): 旋转速度值，默认值为0.0。
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认为None。
        motor_cmd (typing.List[Message_MotorCmd]): 电机控制命令列表，默认初始化为空列表。
        is2move (bool): 准备移动的标志位，默认值为False，表示不准备移动。
    """
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    rotate: float = Field(default=0.0)
    header: typing.Optional[Message_Header] = None
    motor_cmd: typing.List[Message_MotorCmd] = Field(default_factory=list)
    is2move: bool = Field(default=False)


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
