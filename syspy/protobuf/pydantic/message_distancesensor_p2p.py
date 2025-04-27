# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field

from .message_header_p2p import Message_Header


class Message_DistanceNode(BaseModel):
    """
    表示距离节点的消息模型。

    Attributes:
        header (typing.Optional[Message_Header]): 消息头，可选字段，默认为 None。
        name (str): 节点名称，默认为空字符串。
        id (int): 节点 ID，默认为 0。
        dist (float): 节点距离，默认为 0.0。
        valid (bool): 节点是否有效，默认为 False。
        pos_x (float): 节点的 X 坐标，默认为 0.0。
        pos_y (float): 节点的 Y 坐标，默认为 0.0。
        pos_angle (float): 节点的角度，默认为 0.0。
        aperture (float): 节点的孔径，默认为 0.0。
        forbidden (bool): 节点是否被禁止，默认为 False。
        can_router (int): CAN 路由器相关信息，默认为 0。
        rs485 (int): RS485 相关信息，默认为 0。
        RSSI (int): 接收信号强度指示，默认为 0。
    """
    header: typing.Optional[Message_Header] = None
    name: str = Field(default="")
    id: int = Field(default=0)
    dist: float = Field(default=0.0)
    valid: bool = Field(default=False)
    pos_x: float = Field(default=0.0)
    pos_y: float = Field(default=0.0)
    pos_angle: float = Field(default=0.0)
    aperture: float = Field(default=0.0)
    forbidden: bool = Field(default=False)
    can_router: int = Field(default=0)
    rs485: int = Field(default=0)
    RSSI: int = Field(default=0)


class Message_DistanceSensor(BaseModel):
    """
    表示距离传感器的消息模型。

    Attributes:
        node (typing.List[Message_DistanceNode]): 距离节点列表，默认为空列表。
    """
    node: typing.List[Message_DistanceNode] = Field(default_factory=list)
