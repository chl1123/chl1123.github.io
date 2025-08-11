# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Dmx512(BaseModel):
    """
    表示 DMX512 相关消息的模型。

    Attributes:
        type (int): 消息类型，默认为 0。
        battery (int): 电池电量，默认为 0。
        color_r (int): 红色阈值，默认为 0。
        color_g (int): 绿色阈值，默认为 0。
        color_b (int): 蓝色阈值，默认为 0。
        color_w (int): 白色阈值，默认为 0。
        turn_left_or_right (int): 左右转向相关标识，默认为 0。
    """
    type: int = Field(default=0)
    battery: int = Field(default=0)
    color_r: int = Field(default=0)
    color_g: int = Field(default=0)
    color_b: int = Field(default=0)
    color_w: int = Field(default=0)
    turn_left_or_right: int = Field(default=0)
