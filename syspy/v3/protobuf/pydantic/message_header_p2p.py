# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Header(BaseModel):
    """
    表示消息头的模型，包含消息发布时间、数据时间、序列号和帧ID等信息。

    Attributes:
        pub_nsec (int): 消息发布的纳秒时间戳，默认为 0。
        data_nsec (int): 数据对应的纳秒时间戳，默认为 0。
        seq (int): 消息序列号，默认为 0。
        frame_id (str): 消息所属的帧 ID，默认为空字符串。
    """
    pub_nsec: int = Field(default=0)
    data_nsec: int = Field(default=0)
    seq: int = Field(default=0)
    frame_id: str = Field(default="")
