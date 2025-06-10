from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

import message_header_pb2 as _message_header_pb2

DESCRIPTOR: _descriptor.FileDescriptor


class Message_MotorInfo(_message.Message):
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
    __slots__ = ["calib", "can_id", "can_router", "current", "emc", "encoder", "err", "error_code", "follow_err",
                 "header", "motor_name", "passive", "position", "raw_position", "speed", "stop", "temperature", "type",
                 "voltage"]

    class MotorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        """电机类型的枚举类。

        Attributes:
            WALK (0): 行走电机类型
            STEER (1): 转向电机类型
            SPIN (2): 旋转电机类型
            LINEAR (3): 线性电机类型
            ROTATION (4): 回转电机类型
            DO (5): 数字输出电机类型
        """
        __slots__ = []

    CALIB_FIELD_NUMBER: ClassVar[int]
    CAN_ID_FIELD_NUMBER: ClassVar[int]
    CAN_ROUTER_FIELD_NUMBER: ClassVar[int]
    CURRENT_FIELD_NUMBER: ClassVar[int]
    DO: Message_MotorInfo.MotorType
    EMC_FIELD_NUMBER: ClassVar[int]
    ENCODER_FIELD_NUMBER: ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: ClassVar[int]
    ERR_FIELD_NUMBER: ClassVar[int]
    FOLLOW_ERR_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    LINEAR: Message_MotorInfo.MotorType
    MOTOR_NAME_FIELD_NUMBER: ClassVar[int]
    PASSIVE_FIELD_NUMBER: ClassVar[int]
    POSITION_FIELD_NUMBER: ClassVar[int]
    RAW_POSITION_FIELD_NUMBER: ClassVar[int]
    ROTATION: Message_MotorInfo.MotorType
    SPEED_FIELD_NUMBER: ClassVar[int]
    SPIN: Message_MotorInfo.MotorType
    STEER: Message_MotorInfo.MotorType
    STOP_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    VOLTAGE_FIELD_NUMBER: ClassVar[int]
    WALK: Message_MotorInfo.MotorType
    calib: bool
    can_id: int
    can_router: int
    current: float
    emc: bool
    encoder: int
    err: bool
    error_code: int
    follow_err: bool
    header: _message_header_pb2.Message_Header
    motor_name: str
    passive: bool
    position: float
    raw_position: float
    speed: float
    stop: bool
    temperature: float
    type: Message_MotorInfo.MotorType
    voltage: float

    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 motor_name: Optional[str] = ..., can_router: Optional[int] = ..., can_id: Optional[int] = ...,
                 position: Optional[float] = ..., speed: Optional[float] = ..., current: Optional[float] = ...,
                 voltage: Optional[float] = ..., stop: bool = ..., error_code: Optional[int] = ..., err: bool = ...,
                 emc: bool = ..., temperature: Optional[float] = ..., encoder: Optional[int] = ...,
                 type: Optional[Union[Message_MotorInfo.MotorType, str]] = ..., passive: bool = ..., calib: bool = ...,
                 follow_err: bool = ..., raw_position: Optional[float] = ...) -> None: ...


class Message_MotorInfos(_message.Message):
    """表示多个电机信息集合的模型类。

    Attributes:
        motor_info (typing.List[Message_MotorInfo]): 电机信息列表，存储多个电机的信息，默认初始化为空列表。
    """
    __slots__ = ["motor_info"]
    MOTOR_INFO_FIELD_NUMBER: ClassVar[int]
    motor_info: _containers.RepeatedCompositeFieldContainer[Message_MotorInfo]

    def __init__(self, motor_info: Optional[Iterable[Union[Message_MotorInfo, Mapping]]] = ...) -> None: ...
