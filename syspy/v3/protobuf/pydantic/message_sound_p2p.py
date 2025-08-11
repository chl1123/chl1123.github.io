# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_Sound(BaseModel):
    status: int = Field(
        default=0
    )  # 0 = Stopped = Sound is not playing; 1 = Paused = Sound is paused; 2 = Playing = Sound is playing
    sound_name: str = Field(default="")  # with suffix
    loop: bool = Field(default=False)
    count: int = Field(default=0)
