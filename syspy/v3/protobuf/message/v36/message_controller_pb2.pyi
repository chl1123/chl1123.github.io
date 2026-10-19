from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class msgController(_message.Message):
    __slots__ = ["autoCharge", "brake", "driverEmc", "electric", "emc", "humi", "isExternalControl", "isIMUCalibrating", "manualCharge", "softEMC", "temp", "voltage", "voltagebyAdc"]
    AUTOCHARGE_FIELD_NUMBER: _ClassVar[int]
    BRAKE_FIELD_NUMBER: _ClassVar[int]
    DRIVEREMC_FIELD_NUMBER: _ClassVar[int]
    ELECTRIC_FIELD_NUMBER: _ClassVar[int]
    EMC_FIELD_NUMBER: _ClassVar[int]
    HUMI_FIELD_NUMBER: _ClassVar[int]
    ISEXTERNALCONTROL_FIELD_NUMBER: _ClassVar[int]
    ISIMUCALIBRATING_FIELD_NUMBER: _ClassVar[int]
    MANUALCHARGE_FIELD_NUMBER: _ClassVar[int]
    SOFTEMC_FIELD_NUMBER: _ClassVar[int]
    TEMP_FIELD_NUMBER: _ClassVar[int]
    VOLTAGEBYADC_FIELD_NUMBER: _ClassVar[int]
    VOLTAGE_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, temp: _Optional[float] = ..., humi: _Optional[float] = ..., voltage: _Optional[float] = ..., emc: bool = ..., brake: bool = ..., driverEmc: bool = ..., manualCharge: bool = ..., autoCharge: bool = ..., electric: bool = ..., softEMC: bool = ..., isExternalControl: bool = ..., isIMUCalibrating: bool = ..., voltagebyAdc: _Optional[float] = ...) -> None: ...
