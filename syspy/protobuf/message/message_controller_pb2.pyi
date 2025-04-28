from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Message_Controller(_message.Message):
    __slots__ = ["autoCharge", "brake", "driverEmc", "electric", "emc", "humi", "isExternalControl", "isIMUCalibrating", "manualCharge", "softEMC", "temp", "voltage", "voltagebyAdc"]
    AUTOCHARGE_FIELD_NUMBER: ClassVar[int]
    BRAKE_FIELD_NUMBER: ClassVar[int]
    DRIVEREMC_FIELD_NUMBER: ClassVar[int]
    ELECTRIC_FIELD_NUMBER: ClassVar[int]
    EMC_FIELD_NUMBER: ClassVar[int]
    HUMI_FIELD_NUMBER: ClassVar[int]
    ISEXTERNALCONTROL_FIELD_NUMBER: ClassVar[int]
    ISIMUCALIBRATING_FIELD_NUMBER: ClassVar[int]
    MANUALCHARGE_FIELD_NUMBER: ClassVar[int]
    SOFTEMC_FIELD_NUMBER: ClassVar[int]
    TEMP_FIELD_NUMBER: ClassVar[int]
    VOLTAGEBYADC_FIELD_NUMBER: ClassVar[int]
    VOLTAGE_FIELD_NUMBER: ClassVar[int]
    autoCharge: bool
    brake: bool
    driverEmc: bool
    electric: bool
    emc: bool
    humi: float
    isExternalControl: bool
    isIMUCalibrating: bool
    manualCharge: bool
    softEMC: bool
    temp: float
    voltage: float
    voltagebyAdc: float
    def __init__(self, temp: Optional[float] = ..., humi: Optional[float] = ..., voltage: Optional[float] = ..., emc: bool = ..., brake: bool = ..., driverEmc: bool = ..., manualCharge: bool = ..., autoCharge: bool = ..., electric: bool = ..., softEMC: bool = ..., isExternalControl: bool = ..., isIMUCalibrating: bool = ..., voltagebyAdc: Optional[float] = ...) -> None: ...
