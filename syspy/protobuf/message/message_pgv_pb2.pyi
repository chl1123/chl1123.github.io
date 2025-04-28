import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class Message_PGV(_message.Message):
    __slots__ = ["pgvs"]
    PGVS_FIELD_NUMBER: ClassVar[int]
    pgvs: _containers.RepeatedCompositeFieldContainer[Message_PGV_DMT]
    def __init__(self, pgvs: Optional[Iterable[Union[Message_PGV_DMT, Mapping]]] = ...) -> None: ...

class Message_PGV_DMT(_message.Message):
    __slots__ = ["device_address", "error_code", "header", "is_DMT_detected", "is_bar_code", "pgv_info", "tag_diff_angle", "tag_diff_x", "tag_diff_y", "tag_value", "warning_code"]
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
    def __init__(self, tag_diff_x: Optional[float] = ..., tag_diff_y: Optional[float] = ..., tag_diff_angle: Optional[float] = ..., tag_value: Optional[int] = ..., warning_code: Optional[int] = ..., device_address: Optional[int] = ..., is_DMT_detected: bool = ..., error_code: Optional[int] = ..., header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., pgv_info: Optional[Union[Message_PGV_Info, Mapping]] = ..., is_bar_code: bool = ...) -> None: ...

class Message_PGV_Info(_message.Message):
    __slots__ = ["angle_unit", "coordinate", "func", "is_upside", "x", "xrange", "xunit", "y", "yaw", "yrange", "yunit", "z"]
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
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., yaw: Optional[float] = ..., func: Optional[str] = ..., coordinate: Optional[str] = ..., xunit: Optional[float] = ..., yunit: Optional[float] = ..., angle_unit: Optional[float] = ..., is_upside: bool = ..., xrange: Optional[float] = ..., yrange: Optional[float] = ...) -> None: ...

class Message_Tag_position(_message.Message):
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
    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ..., x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ..., tag_value: Optional[int] = ..., is_DMT_detected: bool = ..., is_in_QR_area: bool = ...) -> None: ...
