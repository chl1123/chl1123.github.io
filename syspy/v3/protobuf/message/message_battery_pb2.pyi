from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgBattery(_message.Message):
    __slots__ = ["SOH", "chargeCurrent", "chargeVoltage", "cycle", "errorCode", "extra", "isCharging", "isManuallyConnected", "lastFullChargeStamp", "maxChargeCurrent", "maxChargeVoltage", "needFullCharge", "percentage", "temperature", "userData"]
    CHARGECURRENT_FIELD_NUMBER: ClassVar[int]
    CHARGEVOLTAGE_FIELD_NUMBER: ClassVar[int]
    CYCLE_FIELD_NUMBER: ClassVar[int]
    ERRORCODE_FIELD_NUMBER: ClassVar[int]
    EXTRA_FIELD_NUMBER: ClassVar[int]
    ISCHARGING_FIELD_NUMBER: ClassVar[int]
    ISMANUALLYCONNECTED_FIELD_NUMBER: ClassVar[int]
    LASTFULLCHARGESTAMP_FIELD_NUMBER: ClassVar[int]
    MAXCHARGECURRENT_FIELD_NUMBER: ClassVar[int]
    MAXCHARGEVOLTAGE_FIELD_NUMBER: ClassVar[int]
    NEEDFULLCHARGE_FIELD_NUMBER: ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: ClassVar[int]
    SOH: int
    SOH_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    USERDATA_FIELD_NUMBER: ClassVar[int]
    chargeCurrent: float
    chargeVoltage: float
    cycle: int
    errorCode: int
    extra: str
    isCharging: bool
    isManuallyConnected: bool
    lastFullChargeStamp: int
    maxChargeCurrent: float
    maxChargeVoltage: float
    needFullCharge: bool
    percentage: float
    temperature: float
    userData: bytes
    def __init__(self, percentage: Optional[float] = ..., chargeCurrent: Optional[float] = ..., chargeVoltage: Optional[float] = ..., isCharging: bool = ..., temperature: Optional[float] = ..., cycle: Optional[int] = ..., maxChargeCurrent: Optional[float] = ..., maxChargeVoltage: Optional[float] = ..., extra: Optional[str] = ..., isManuallyConnected: bool = ..., errorCode: Optional[int] = ..., SOH: Optional[int] = ..., needFullCharge: bool = ..., lastFullChargeStamp: Optional[int] = ..., userData: Optional[bytes] = ...) -> None: ...
