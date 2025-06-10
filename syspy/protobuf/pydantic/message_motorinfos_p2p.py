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


class Message_MotorInfo(BaseModel):
    """表示电机信息的模型类。

    Attributes:
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认为None，包含消息的元数据。
        motor_name (str): 电机的名称，默认值为空字符串。
        can_router (int): CAN路由器的编号，默认值为0。
        can_id (int): CAN总线的ID，默认值为0。
        position (float): 电机的位置，单位为米，默认值为0.0。
        speed (float): 电机的速度，单位为米每秒，默认值为0.0。
        current (float): 电机的电流，单位为安培，默认值为0.0。
        voltage (float): 电机的电压，单位为伏特，默认值为0.0。
        stop (bool): 电机是否停止的标志，默认值为False，表示电机未停止。
        error_code (int): 电机的错误代码，默认值为0，表示无错误。
        err (bool): 电机是否出现错误的标志，默认值为False，表示无错误。
        emc (bool): 电机是否受到电磁干扰的标志，默认值为False，表示未受干扰。
        temperature (float): 电机的温度，单位为摄氏度，默认值为0.0。
        encoder (int): 电机编码器的计数值，默认值为0。
        type (Message_MotorInfo.MotorType): 电机的类型，默认值为MotorType.WALK（值为0）。
        passive (bool): 电机是否处于被动状态的标志，默认值为False，表示非被动状态。
        calib (bool): 电机是否需要校准的标志，默认值为False，表示不需要校准。
        follow_err (bool): 电机是否存在跟随误差的标志，默认值为False，表示无跟随误差。
        raw_position (float): 电机的原始位置，为不包含.cp值的转向角度，默认值为0.0。
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

    header: typing.Optional[Message_Header] = None
    motor_name: str = Field(default="")
    can_router: int = Field(default=0)
    can_id: int = Field(default=0)
    position: float = Field(default=0.0)  # m
    speed: float = Field(default=0.0)  # m/s
    current: float = Field(default=0.0)  # A
    voltage: float = Field(default=0.0)  # V
    stop: bool = Field(default=False)
    error_code: int = Field(default=0)
    err: bool = Field(default=False)
    emc: bool = Field(default=False)
    temperature: float = Field(default=0.0)  # deg
    encoder: int = Field(default=0)  # cnt
    type: "Message_MotorInfo.MotorType" = Field(default=0)
    passive: bool = Field(default=False)
    calib: bool = Field(default=False)
    follow_err: bool = Field(default=False)
    raw_position: float = Field(default=0.0)  # steer angle without .cp value


class Message_MotorInfos(BaseModel):
    """表示多个电机信息集合的模型类。

    Attributes:
        motor_info (typing.List[Message_MotorInfo]): 电机信息列表，存储多个电机的信息，默认初始化为空列表。
    """
    motor_info: typing.List[Message_MotorInfo] = Field(default_factory=list)
