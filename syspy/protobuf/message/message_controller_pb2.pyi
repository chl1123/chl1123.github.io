from typing import ClassVar, Optional

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Controller(_message.Message):
    """
    表示控制器相关信息的模型类。

    Attributes:
        temp (float): 控制器的温度，默认值为 0.0。
        humi (float): 控制器的湿度，默认值为 0.0。
        voltage (float): 控制器的电压，默认值为 0.0。
        emc (bool): 急停标志，默认值为 False，表示未急停。
        brake (bool): 刹车状态标志，默认值为 False，表示刹车未启动。
        driverEmc (bool): 电机驱动器标志，默认值为 False，表示电机驱动器未急停。
        manualCharge (bool): 手动充电状态标志，默认值为 False，表示未处于手动充电状态。
        autoCharge (bool): 自动充电状态标志，默认值为 False，表示未处于自动充电状态。
        electric (bool): 通电状态标志，默认值为 False，表示未通电。
        softEMC (bool): 软急停标志，默认值为 False，表示通过软件的方式控制机器人控制器不输出急停信号。
        isExternalControl (bool): 是否处于外部控制状态的标志，默认值为 False，表示未处于外部控制状态。
        isIMUCalibrating (bool): IMU（惯性测量单元）是否正在校准的标志，默认值为 False，表示 IMU 未处于校准状态。
        voltagebyAdc (float): 通过 ADC 检测到的外部电压，默认值为 0.0。
    """
    __slots__ = ["autoCharge", "brake", "driverEmc", "electric", "emc", "humi", "isExternalControl", "isIMUCalibrating",
                 "manualCharge", "softEMC", "temp", "voltage", "voltagebyAdc"]
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

    def __init__(self, temp: Optional[float] = ..., humi: Optional[float] = ..., voltage: Optional[float] = ...,
                 emc: bool = ..., brake: bool = ..., driverEmc: bool = ..., manualCharge: bool = ...,
                 autoCharge: bool = ..., electric: bool = ..., softEMC: bool = ..., isExternalControl: bool = ...,
                 isIMUCalibrating: bool = ..., voltagebyAdc: Optional[float] = ...) -> None: ...
