# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Controller(BaseModel):
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
    voltagebyAdc: float = Field(default=0.0)  # 检测外部电压
