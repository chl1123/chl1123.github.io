# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# c Version: 2.10.4

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Battery(BaseModel):
    """
    表示电池相关信息的模型类。

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
    percetage: float = Field(default=0.0, description="电池电量百分比，默认值为0.0。")
    charge_current: float = Field(default=0.0, description="电池充电电流，默认值为0.0。")
    charge_voltage: float = Field(default=0.0)
    is_charging: bool = Field(default=False)
    temperature: float = Field(default=0.0)
    cycle: int = Field(default=0)
    max_charge_current: float = Field(default=0.0)
    max_charge_voltage: float = Field(default=0.0)
    extra: str = Field(default="")
    is_manually_connected: bool = Field(default=False)
    user_data: bytes = Field(default=b"")
