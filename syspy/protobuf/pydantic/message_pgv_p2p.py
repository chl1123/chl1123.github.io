# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field

from .message_header_p2p import Message_Header


class Message_PGV_Info(BaseModel):
    """用于表示数据矩阵标签相关信息的消息。

    Attributes:
        x (float): x坐标值，默认值为0.0。
        y (float): y坐标值，默认值为0.0。
        z (float): z坐标值，默认值为0.0。
        yaw (float): 偏航角，默认值为0.0。
        func (str): 功能描述，默认值为空字符串。
        coordinate (str): 坐标类型，如'pgv'或'code'，默认值为空字符串。
        xunit (float): x坐标的单位值，默认值为0.0。
        yunit (float): y坐标的单位值，默认值为0.0。
        angle_unit (float): 角度的单位值，默认值为0.0。
        is_upside (bool): 是否倒置的标志，默认值为False，表示未倒置。
        xrange (float): x坐标的范围值，默认值为0.0。
        yrange (float): y坐标的范围值，默认值为0.0。
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
    """用于表示PGV（可能是某种视觉系统）的数据矩阵标签相关信息的消息。

    Attributes:
        tag_diff_x (float): 标签在x方向的差值，单位为米，默认值为0.0。
        tag_diff_y (float): 标签在y方向的差值，单位为米，默认值为0.0。
        tag_diff_angle (float): 标签角度的差值，单位为弧度，默认值为0.0。
        tag_value (int): 标签所携带的数据，默认值为0。
        warning_code (int): 警告报警码，默认值为0，表示无警告。
        device_address (int): 设备地址（ID），默认值为0。
        is_DMT_detected (bool): 是否检测到数据矩阵的标志，默认值为False，表示未检测到。
        error_code (int): 错误报警码，默认值为0，表示无错误。
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认为None，包含消息的元数据。
        pgv_info (typing.Optional[Message_PGV_Info]): PGV的详细信息，可选字段，默认为None。
        is_bar_code (bool): 是否为条形码（一维）的标志，默认值为False，表示不是条形码。
    """
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
    """用于表示标签位置信息的消息。

    Attributes:
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认为None，包含消息的元数据。
        x (float): 标签的x坐标值，默认值为0.0。
        y (float): 标签的y坐标值，默认值为0.0。
        angle (float): 标签的角度值，默认值为0.0。
        tag_value (int): 标签所携带的数据，默认值为0。
        is_DMT_detected (bool): 是否检测到数据矩阵的标志，默认值为False，表示未检测到。
        is_in_QR_area (bool): 标签是否在二维码区域内的标志，默认值为False，表示不在。
    """
    header: typing.Optional[Message_Header] = None
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    angle: float = Field(default=0.0)
    tag_value: int = Field(default=0)
    is_DMT_detected: bool = Field(default=False)
    is_in_QR_area: bool = Field(default=False)


class Message_PGV(BaseModel):
    """表示多个PGV相机消息。

    Attributes:
        pgvs (typing.List[Message_PGV_DMT]): PGV数据矩阵标签信息列表，默认初始化为空列表。
    """
    pgvs: typing.List[Message_PGV_DMT] = Field(default_factory=list)
