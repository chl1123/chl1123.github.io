from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

import message_header_pb2 as _message_header_pb2

DESCRIPTOR: _descriptor.FileDescriptor


class Message_PGV(_message.Message):
    """表示多个PGV相机消息。

    Attributes:
        pgvs (typing.List[Message_PGV_DMT]): PGV数据矩阵标签信息列表，默认初始化为空列表。
    """
    __slots__ = ["pgvs"]
    PGVS_FIELD_NUMBER: ClassVar[int]
    pgvs: _containers.RepeatedCompositeFieldContainer[Message_PGV_DMT]

    def __init__(self, pgvs: Optional[Iterable[Union[Message_PGV_DMT, Mapping]]] = ...) -> None: ...


class Message_PGV_DMT(_message.Message):
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
    __slots__ = ["device_address", "error_code", "header", "is_DMT_detected", "is_bar_code", "pgv_info",
                 "tag_diff_angle", "tag_diff_x", "tag_diff_y", "tag_value", "warning_code"]
    DEVICE_ADDRESS_FIELD_NUMBER: ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    IS_BAR_CODE_FIELD_NUMBER: ClassVar[int]
    IS_DMT_DETECTED_FIELD_NUMBER: ClassVar[int]
    PGV_INFO_FIELD_NUMBER: ClassVar[int]
    TAG_DIFF_ANGLE_FIELD_NUMBER: ClassVar[int]
    TAG_DIFF_X_FIELD_NUMBER: ClassVar[int]
    TAG_DIFF_Y_FIELD_NUMBER: ClassVar[int]
    TAG_VALUE_FIELD_NUMBER: ClassVar[int]
    WARNING_CODE_FIELD_NUMBER: ClassVar[int]
    device_address: int
    error_code: int
    header: _message_header_pb2.Message_Header
    is_DMT_detected: bool
    is_bar_code: bool
    pgv_info: Message_PGV_Info
    tag_diff_angle: float
    tag_diff_x: float
    tag_diff_y: float
    tag_value: int
    warning_code: int

    def __init__(self, tag_diff_x: Optional[float] = ..., tag_diff_y: Optional[float] = ...,
                 tag_diff_angle: Optional[float] = ..., tag_value: Optional[int] = ...,
                 warning_code: Optional[int] = ..., device_address: Optional[int] = ..., is_DMT_detected: bool = ...,
                 error_code: Optional[int] = ...,
                 header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 pgv_info: Optional[Union[Message_PGV_Info, Mapping]] = ..., is_bar_code: bool = ...) -> None: ...


class Message_PGV_Info(_message.Message):
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
    __slots__ = ["angle_unit", "coordinate", "func", "is_upside", "x", "xrange", "xunit", "y", "yaw", "yrange", "yunit",
                 "z"]
    ANGLE_UNIT_FIELD_NUMBER: ClassVar[int]
    COORDINATE_FIELD_NUMBER: ClassVar[int]
    FUNC_FIELD_NUMBER: ClassVar[int]
    IS_UPSIDE_FIELD_NUMBER: ClassVar[int]
    XRANGE_FIELD_NUMBER: ClassVar[int]
    XUNIT_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    YRANGE_FIELD_NUMBER: ClassVar[int]
    YUNIT_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    angle_unit: float
    coordinate: str
    func: str
    is_upside: bool
    x: float
    xrange: float
    xunit: float
    y: float
    yaw: float
    yrange: float
    yunit: float
    z: float

    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...,
                 yaw: Optional[float] = ..., func: Optional[str] = ..., coordinate: Optional[str] = ...,
                 xunit: Optional[float] = ..., yunit: Optional[float] = ..., angle_unit: Optional[float] = ...,
                 is_upside: bool = ..., xrange: Optional[float] = ..., yrange: Optional[float] = ...) -> None: ...


class Message_Tag_position(_message.Message):
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
    __slots__ = ["angle", "header", "is_DMT_detected", "is_in_QR_area", "tag_value", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    IS_DMT_DETECTED_FIELD_NUMBER: ClassVar[int]
    IS_IN_QR_AREA_FIELD_NUMBER: ClassVar[int]
    TAG_VALUE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    header: _message_header_pb2.Message_Header
    is_DMT_detected: bool
    is_in_QR_area: bool
    tag_value: int
    x: float
    y: float

    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ...,
                 tag_value: Optional[int] = ..., is_DMT_detected: bool = ..., is_in_QR_area: bool = ...) -> None: ...
