from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Message_Battery(_message.Message):
    __slots__ = ["charge_current", "charge_voltage", "cycle", "errorCode", "extra", "is_charging", "is_manually_connected", "max_charge_current", "max_charge_voltage", "percetage", "temperature", "user_data"]
    CHARGE_CURRENT_FIELD_NUMBER: ClassVar[int]
    CHARGE_VOLTAGE_FIELD_NUMBER: ClassVar[int]
    CYCLE_FIELD_NUMBER: ClassVar[int]
    ERRORCODE_FIELD_NUMBER: ClassVar[int]
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
    errorCode: int
    extra: str
    is_charging: bool
    is_manually_connected: bool
    max_charge_current: float
    max_charge_voltage: float
    percetage: float
    temperature: float
    user_data: bytes
    def __init__(self, percetage: Optional[float] = ..., charge_current: Optional[float] = ..., charge_voltage: Optional[float] = ..., is_charging: bool = ..., temperature: Optional[float] = ..., cycle: Optional[int] = ..., max_charge_current: Optional[float] = ..., max_charge_voltage: Optional[float] = ..., extra: Optional[str] = ..., is_manually_connected: bool = ..., errorCode: Optional[int] = ..., user_data: Optional[bytes] = ...) -> None: ...
