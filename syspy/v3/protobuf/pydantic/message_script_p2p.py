# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 3.20.3 
# Pydantic Version: 2.10.4 
import typing
from enum import IntEnum

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel, Field


class Message_ScriptStatus(BaseModel):
    class Status(IntEnum):
        StatusNone = 0
        Waiting = 1
        Running = 2
        Suspended = 3
        Completed = 4
        Failed = 5
        Canceled = 6
        OverTime = 7

    status: "Message_ScriptStatus.Status" = Field(default=0)
    res: str = Field(default="")

class Message_Script(BaseModel):
    """
     存储所有脚本的消息
    """

    script_data: typing.Dict[str, str] = Field(default_factory=dict)# key 是脚本名称或标识，value 是用户自定义的 JSON 数据
