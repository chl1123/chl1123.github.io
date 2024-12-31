# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_header_p2p import Message_Header
from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field
import typing


class Message_PGV_Info(BaseModel):
    """
    message for data matrix tag
    """

    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    func: str = Field(default="")
    coordinate: str = Field(default="")  # pgv, code
    xunit: float = Field(default=0.0)
    yunit: float = Field(default=0.0)
    angle_unit: float = Field(default=0.0)
    is_upside: bool = Field(default=False)
    xrange: float = Field(default=0.0)
    yrange: float = Field(default=0.0)


class Message_PGV_DMT(BaseModel):
    tag_diff_x: float = Field(default=0.0)  # m
    tag_diff_y: float = Field(default=0.0)  # m
    tag_diff_angle: float = Field(default=0.0)  # rad
    tag_value: int = Field(default=0)  # 标签的数据
    warning_code: int = Field(default=0)  # Warning 报警码
    device_address: int = Field(default=0)  # ID
    is_DMT_detected: bool = Field(
        default=False
    )  # false = 没检测到 Data Matrix, true = 检测到 Data Matrix, 我们用的都是 Data Matrix
    error_code: int = Field(default=0)  # Error 报警码
    header: typing.Optional[Message_Header] = None
    pgv_info: typing.Optional[Message_PGV_Info] = None
    is_bar_code: bool = Field(default=False)  # 是否为条形码（一维）


class Message_Tag_position(BaseModel):
    header: typing.Optional[Message_Header] = None
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    angle: float = Field(default=0.0)
    tag_value: int = Field(default=0)
    is_DMT_detected: bool = Field(default=False)
    is_in_QR_area: bool = Field(default=False)


class Message_PGV(BaseModel):
    pgvs: typing.List[Message_PGV_DMT] = Field(default_factory=list)
