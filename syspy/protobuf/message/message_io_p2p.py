# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field


class Message_DINode(BaseModel):
    """
    表示数字输入节点的相关信息。

    Attributes:
        id (int): 节点的唯一标识符，默认为 0。
        status (bool): 节点的状态，默认为 False。
        x (float): 节点的 x 坐标，默认为 0.0。
        y (float): 节点的 y 坐标，默认为 0.0。
        z (float): 节点的 z 坐标，默认为 0.0。
        yaw (float): 节点的偏航角，默认为 0.0。
        func (str): 节点的功能描述，默认为空字符串。
        type (str): 节点的类型，默认为空字符串。
        source (str): 节点的来源，默认为空字符串。
        shape (str): 节点的形状，默认为空字符串。
        mindist (float): 最小距离，默认为 0.0。
        maxdist (float): 最大距离，默认为 0.0。
        range (float): 范围，默认为 0.0。
        posx (typing.List[float]): x 坐标的列表，默认为空列表。
        posy (typing.List[float]): y 坐标的列表，默认为空列表。
        forbidden (bool): 是否禁止，默认为 False。
    """
    id: int = Field(default=0)
    status: bool = Field(default=False)
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    func: str = Field(default="")
    type: str = Field(default="")
    source: str = Field(default="")
    shape: str = Field(default="")
    mindist: float = Field(default=0.0)
    maxdist: float = Field(default=0.0)
    range: float = Field(default=0.0)
    posx: typing.List[float] = Field(default_factory=list)
    posy: typing.List[float] = Field(default_factory=list)
    forbidden: bool = Field(default=False)


class Message_DI(BaseModel):
    """
    表示数字输入相关的消息。

    Attributes:
        node (typing.List[Message_DINode]): 数字输入节点的列表，默认为空列表。
        max_node (int): 最大节点数，默认为 0。
    """
    node: typing.List[Message_DINode] = Field(default_factory=list)
    max_node: int = Field(default=0)


class Message_DONode(BaseModel):
    """
    表示数字输出节点的相关信息。

    Attributes:
        id (int): 节点的唯一标识符，默认为 0。
        status (bool): 节点的状态，默认为 False。
        source (str): 节点的来源，默认为空字符串。
        func (str): 节点的功能描述，默认为空字符串。
    """
    id: int = Field(default=0)
    status: bool = Field(default=False)
    source: str = Field(default="")
    func: str = Field(default="")


class Message_DO(BaseModel):
    """
    表示数字输出相关的消息。

    Attributes:
        node (typing.List[Message_DONode]): 数字输出节点的列表，默认为空列表。
        max_node (int): 最大节点数，默认为 0。
    """
    node: typing.List[Message_DONode] = Field(default_factory=list)
    max_node: int = Field(default=0)


class Message_Astern(BaseModel):
    """Astern

    Attributes:
        status (int): 状态值，默认为 0。
    """
    status: int = Field(default=0)
    """状态值，默认值为0。"""
