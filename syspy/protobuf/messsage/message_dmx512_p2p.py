# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Dmx512(BaseModel):
    type: int = Field(default=0)  # 类型
    battery: int = Field(default=0)  # 电池电量
    color_r: int = Field(default=0)  # 红色阈值
    color_g: int = Field(default=0)  # 绿色阈值
    color_b: int = Field(default=0)  # 蓝色阈值
    color_w: int = Field(default=0)  # 白色阈值
    turn_left_or_right: int = Field(default=0)
