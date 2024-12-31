# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Battery(BaseModel):
    percetage: float = Field(default=0.0)
    charge_current: float = Field(default=0.0)
    charge_voltage: float = Field(default=0.0)
    is_charging: bool = Field(default=False)
    temperature: float = Field(default=0.0)
    cycle: int = Field(default=0)
    max_charge_current: float = Field(default=0.0)
    max_charge_voltage: float = Field(default=0.0)
    extra: str = Field(default="")
    is_manually_connected: bool = Field(default=False)
    user_data: bytes = Field(default=b"")
