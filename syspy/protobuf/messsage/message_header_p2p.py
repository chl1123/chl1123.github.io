# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Header(BaseModel):
    pub_nsec: int = Field(default=0)
    data_nsec: int = Field(default=0)
    seq: int = Field(default=0)
    frame_id: str = Field(default="")
