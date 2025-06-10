# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Controller(BaseModel):
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
    temp: float = Field(default=0.0)
    humi: float = Field(default=0.0)
    voltage: float = Field(default=0.0)
    emc: bool = Field(default=False)
    brake: bool = Field(default=False)
    driverEmc: bool = Field(default=False)
    manualCharge: bool = Field(default=False)
    autoCharge: bool = Field(default=False)
    electric: bool = Field(default=False)
    softEMC: bool = Field(default=False)
    isExternalControl: bool = Field(default=False)
    isIMUCalibrating: bool = Field(default=False)
    voltagebyAdc: float = Field(default=0.0)
