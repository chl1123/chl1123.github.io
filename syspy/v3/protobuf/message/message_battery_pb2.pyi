from typing import ClassVar, Optional

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Battery(_message.Message):
    """电池相关信息的消息类。

    Attributes:
        percetage (float): 电池电量百分比，默认值为 0.0。
        charge_current (float): 电池充电电流，默认值为 0.0。
        charge_voltage (float): 电池充电电压，默认值为 0.0。
        is_charging (bool): 电池是否正在充电的标志，默认值为 False，表示未充电。
        temperature (float): 电池温度，默认值为 0.0。
        cycle (int): 电池充放电循环次数，默认值为 0。
        max_charge_current (float): 电池最大充电电流，默认值为 0.0。
        max_charge_voltage (float): 电池最大充电电压，默认值为 0.0。
        extra (str): 额外信息，以字符串形式存储，默认值为空字符串。
        is_manually_connected (bool): 电池是否为手动连接的标志，默认值为 False，表示不是手动连接。
        user_data (bytes): 用户自定义数据，以字节形式存储，默认值为空字节串。
    """
    __slots__ = ["charge_current", "charge_voltage", "cycle", "extra", "is_charging", "is_manually_connected",
                 "max_charge_current", "max_charge_voltage", "percetage", "temperature", "user_data"]
    CHARGE_CURRENT_FIELD_NUMBER: ClassVar[int]
    CHARGE_VOLTAGE_FIELD_NUMBER: ClassVar[int]
    CYCLE_FIELD_NUMBER: ClassVar[int]
    EXTRA_FIELD_NUMBER: ClassVar[int]
    IS_CHARGING_FIELD_NUMBER: ClassVar[int]
    IS_MANUALLY_CONNECTED_FIELD_NUMBER: ClassVar[int]
    MAX_CHARGE_CURRENT_FIELD_NUMBER: ClassVar[int]
    MAX_CHARGE_VOLTAGE_FIELD_NUMBER: ClassVar[int]
    PERCETAGE_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    USER_DATA_FIELD_NUMBER: ClassVar[int]
    charge_current: float
    charge_voltage: float
    cycle: int
    extra: str
    is_charging: bool
    is_manually_connected: bool
    max_charge_current: float
    max_charge_voltage: float
    percetage: float
    temperature: float
    user_data: bytes

    def __init__(self, percetage: Optional[float] = ..., charge_current: Optional[float] = ...,
                 charge_voltage: Optional[float] = ..., is_charging: bool = ..., temperature: Optional[float] = ...,
                 cycle: Optional[int] = ..., max_charge_current: Optional[float] = ...,
                 max_charge_voltage: Optional[float] = ..., extra: Optional[str] = ...,
                 is_manually_connected: bool = ..., user_data: Optional[bytes] = ...) -> None: ...
