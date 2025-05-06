from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

import message_header_pb2 as _message_header_pb2

DESCRIPTOR: _descriptor.FileDescriptor


class Message_DistanceNode(_message.Message):
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
    __slots__ = ["RSSI", "aperture", "can_router", "dist", "forbidden", "header", "id", "name", "pos_angle", "pos_x",
                 "pos_y", "rs485", "valid"]
    APERTURE_FIELD_NUMBER: ClassVar[int]
    CAN_ROUTER_FIELD_NUMBER: ClassVar[int]
    DIST_FIELD_NUMBER: ClassVar[int]
    FORBIDDEN_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    NAME_FIELD_NUMBER: ClassVar[int]
    POS_ANGLE_FIELD_NUMBER: ClassVar[int]
    POS_X_FIELD_NUMBER: ClassVar[int]
    POS_Y_FIELD_NUMBER: ClassVar[int]
    RS485_FIELD_NUMBER: ClassVar[int]
    RSSI: int
    RSSI_FIELD_NUMBER: ClassVar[int]
    VALID_FIELD_NUMBER: ClassVar[int]
    aperture: float
    can_router: int
    dist: float
    forbidden: bool
    header: _message_header_pb2.Message_Header
    id: int
    name: str
    pos_angle: float
    pos_x: float
    pos_y: float
    rs485: int
    valid: bool

    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 name: Optional[str] = ..., id: Optional[int] = ..., dist: Optional[float] = ..., valid: bool = ...,
                 pos_x: Optional[float] = ..., pos_y: Optional[float] = ..., pos_angle: Optional[float] = ...,
                 aperture: Optional[float] = ..., forbidden: bool = ..., can_router: Optional[int] = ...,
                 rs485: Optional[int] = ..., RSSI: Optional[int] = ...) -> None: ...


class Message_DistanceSensor(_message.Message):
    """
    表示距离传感器的消息模型。

    Attributes:
        node (typing.List[Message_DistanceNode]): 距离节点列表，默认为空列表。
    """
    __slots__ = ["node"]
    NODE_FIELD_NUMBER: ClassVar[int]
    node: _containers.RepeatedCompositeFieldContainer[Message_DistanceNode]

    def __init__(self, node: Optional[Iterable[Union[Message_DistanceNode, Mapping]]] = ...) -> None: ...
