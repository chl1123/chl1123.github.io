from . import message_devicestatus_pb2 as _message_devicestatus_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgBattery(_message.Message):
    __slots__ = ["SOH", "chargeCurrent", "chargeVoltage", "cycle", "extra", "isCharging", "isManuallyConnected", "lastFullChargeStamp", "maxChargeCurrent", "maxChargeVoltage", "needFullCharge", "percentage", "status", "temperature", "userData"]
    CHARGECURRENT_FIELD_NUMBER: ClassVar[int]
    CHARGEVOLTAGE_FIELD_NUMBER: ClassVar[int]
    CYCLE_FIELD_NUMBER: ClassVar[int]
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
    STATUS_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    USERDATA_FIELD_NUMBER: ClassVar[int]
    chargeCurrent: float
    chargeVoltage: float
    cycle: int
    extra: str
    isCharging: bool
    isManuallyConnected: bool
    lastFullChargeStamp: int
    maxChargeCurrent: float
    maxChargeVoltage: float
    needFullCharge: bool
    percentage: float
    status: _message_devicestatus_pb2.msgDeviceStatusNode
    temperature: float
    userData: bytes
    def __init__(self, percentage: Optional[float] = ..., chargeCurrent: Optional[float] = ..., chargeVoltage: Optional[float] = ..., isCharging: bool = ..., temperature: Optional[float] = ..., cycle: Optional[int] = ..., maxChargeCurrent: Optional[float] = ..., maxChargeVoltage: Optional[float] = ..., extra: Optional[str] = ..., isManuallyConnected: bool = ..., status: Optional[Union[_message_devicestatus_pb2.msgDeviceStatusNode, Mapping]] = ..., SOH: Optional[int] = ..., needFullCharge: bool = ..., lastFullChargeStamp: Optional[int] = ..., userData: Optional[bytes] = ...) -> None: ...
