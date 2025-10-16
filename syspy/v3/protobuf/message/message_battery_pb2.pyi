from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgBattery(_message.Message):
    __slots__ = ["chargeCurrent", "chargeVoltage", "cycle", "errorCode", "extra", "isCharging", "isManuallyConnected", "maxChargeCurrent", "maxChargeVoltage", "percentage", "temperature", "userData"]
    CHARGECURRENT_FIELD_NUMBER: ClassVar[int]
    CHARGEVOLTAGE_FIELD_NUMBER: ClassVar[int]
    CYCLE_FIELD_NUMBER: ClassVar[int]
    ERRORCODE_FIELD_NUMBER: ClassVar[int]
    EXTRA_FIELD_NUMBER: ClassVar[int]
    ISCHARGING_FIELD_NUMBER: ClassVar[int]
    ISMANUALLYCONNECTED_FIELD_NUMBER: ClassVar[int]
    MAXCHARGECURRENT_FIELD_NUMBER: ClassVar[int]
    MAXCHARGEVOLTAGE_FIELD_NUMBER: ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    USERDATA_FIELD_NUMBER: ClassVar[int]
    chargeCurrent: float
    chargeVoltage: float
    cycle: int
    errorCode: int
    extra: str
    isCharging: bool
    isManuallyConnected: bool
    maxChargeCurrent: float
    maxChargeVoltage: float
    percentage: float
    temperature: float
    userData: bytes
    def __init__(self, percentage: Optional[float] = ..., chargeCurrent: Optional[float] = ..., chargeVoltage: Optional[float] = ..., isCharging: bool = ..., temperature: Optional[float] = ..., cycle: Optional[int] = ..., maxChargeCurrent: Optional[float] = ..., maxChargeVoltage: Optional[float] = ..., extra: Optional[str] = ..., isManuallyConnected: bool = ..., errorCode: Optional[int] = ..., userData: Optional[bytes] = ...) -> None: ...
