# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field

from .message_header_p2p import Message_Header


class Message_MagneticNode(BaseModel):
    """表示磁节点相关信息。

    Attributes:
        id (int): 节点的标识符，默认值为0。
        value (typing.List[bool]): 布尔值列表，用于存储磁节点的某些状态信息，默认初始化为空列表。
        x (float): 磁节点的x坐标值，默认值为0.0。
        y (float): 磁节点的y坐标值，默认值为0.0。
        yaw (float): 磁节点的偏航角，代表其朝向，默认值为0.0。
        step (float): 磁节点相关的步长，默认值为0.0。
        resolution (int): 磁节点的分辨率，默认值为0。
        header (typing.Optional[Message_Header]): 消息头，包含消息的元数据，可选类型，默认为None。
    """
    id: int = Field(default=0)
    value: typing.List[bool] = Field(default_factory=list)
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    step: float = Field(default=0.0)
    resolution: int = Field(default=0)
    header: typing.Optional[Message_Header] = None


class Message_Magnetic(BaseModel):
    """表示磁相关的消息。

    Attributes:
        magnetic_nodes (typing.List[Message_MagneticNode]): 磁节点列表，存储多个磁节点的信息，默认初始化为空列表。
    """
    magnetic_nodes: typing.List[Message_MagneticNode] = Field(default_factory=list)
