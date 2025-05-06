from typing import ClassVar, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message

import message_header_pb2 as _message_header_pb2

DESCRIPTOR: _descriptor.FileDescriptor


class Message_2D_CamInfo(_message.Message):
    __slots__ = ["camera_name", "distortion_modle", "header", "is_extrinsics_caib", "is_intrinsics_caib", "m_cx_",
                 "m_cy_", "m_fx_", "m_fy_", "m_infrared", "m_k1_", "m_k2_", "m_k3_", "m_k4_", "m_k5_", "m_k6_", "m_p1_",
                 "m_p2_", "m_seertag_family_id", "m_seertag_size", "model_type", "pitch", "roll", "x", "y", "yaw", "z"]
    CAMERA_NAME_FIELD_NUMBER: ClassVar[int]
    DISTORTION_MODLE_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    IS_EXTRINSICS_CAIB_FIELD_NUMBER: ClassVar[int]
    IS_INTRINSICS_CAIB_FIELD_NUMBER: ClassVar[int]
    MODEL_TYPE_FIELD_NUMBER: ClassVar[int]
    M_CX__FIELD_NUMBER: ClassVar[int]
    M_CY__FIELD_NUMBER: ClassVar[int]
    M_FX__FIELD_NUMBER: ClassVar[int]
    M_FY__FIELD_NUMBER: ClassVar[int]
    M_INFRARED_FIELD_NUMBER: ClassVar[int]
    M_K1__FIELD_NUMBER: ClassVar[int]
    M_K2__FIELD_NUMBER: ClassVar[int]
    M_K3__FIELD_NUMBER: ClassVar[int]
    M_K4__FIELD_NUMBER: ClassVar[int]
    M_K5__FIELD_NUMBER: ClassVar[int]
    M_K6__FIELD_NUMBER: ClassVar[int]
    M_P1__FIELD_NUMBER: ClassVar[int]
    M_P2__FIELD_NUMBER: ClassVar[int]
    M_SEERTAG_FAMILY_ID_FIELD_NUMBER: ClassVar[int]
    M_SEERTAG_SIZE_FIELD_NUMBER: ClassVar[int]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    camera_name: str
    distortion_modle: str
    header: _message_header_pb2.Message_Header
    is_extrinsics_caib: bool
    is_intrinsics_caib: bool
    m_cx_: float
    m_cy_: float
    m_fx_: float
    m_fy_: float
    m_infrared: float
    m_k1_: float
    m_k2_: float
    m_k3_: float
    m_k4_: float
    m_k5_: float
    m_k6_: float
    m_p1_: float
    m_p2_: float
    m_seertag_family_id: float
    m_seertag_size: float
    model_type: str
    pitch: float
    roll: float
    x: float
    y: float
    yaw: float
    z: float

    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 camera_name: Optional[str] = ..., m_infrared: Optional[float] = ...,
                 m_seertag_size: Optional[float] = ..., m_seertag_family_id: Optional[float] = ...,
                 model_type: Optional[str] = ..., distortion_modle: Optional[str] = ..., is_intrinsics_caib: bool = ...,
                 is_extrinsics_caib: bool = ..., x: Optional[float] = ..., y: Optional[float] = ...,
                 z: Optional[float] = ..., roll: Optional[float] = ..., pitch: Optional[float] = ...,
                 yaw: Optional[float] = ..., m_fx_: Optional[float] = ..., m_fy_: Optional[float] = ...,
                 m_cx_: Optional[float] = ..., m_cy_: Optional[float] = ..., m_k1_: Optional[float] = ...,
                 m_k2_: Optional[float] = ..., m_k3_: Optional[float] = ..., m_k4_: Optional[float] = ...,
                 m_k5_: Optional[float] = ..., m_k6_: Optional[float] = ..., m_p1_: Optional[float] = ...,
                 m_p2_: Optional[float] = ...) -> None: ...


class Message_3DPose(_message.Message):
    __slots__ = ["extra_data", "header", "q_w", "q_x", "q_y", "q_z", "x", "y", "z"]
    EXTRA_DATA_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    Q_W_FIELD_NUMBER: ClassVar[int]
    Q_X_FIELD_NUMBER: ClassVar[int]
    Q_Y_FIELD_NUMBER: ClassVar[int]
    Q_Z_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    extra_data: str
    header: _message_header_pb2.Message_Header
    q_w: float
    q_x: float
    q_y: float
    q_z: float
    x: float
    y: float
    z: float

    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...,
                 q_w: Optional[float] = ..., q_x: Optional[float] = ..., q_y: Optional[float] = ...,
                 q_z: Optional[float] = ..., extra_data: Optional[str] = ...) -> None: ...


class Message_IRCAMPose(_message.Message):
    __slots__ = ["pose"]
    POSE_FIELD_NUMBER: ClassVar[int]
    pose: Message_3DPose

    def __init__(self, pose: Optional[Union[Message_3DPose, Mapping]] = ...) -> None: ...


class Message_LocFinished(_message.Message):
    __slots__ = ["value"]
    VALUE_FIELD_NUMBER: ClassVar[int]
    value: bool

    def __init__(self, value: bool = ...) -> None: ...


class Message_Localization(_message.Message):
    """表示本地化消息的模型类。

    Attributes:
        header (typing.Optional[Message_Header]): 消息头，默认为None。
        x (float): 定位的x坐标，默认值为0.0。
        y (float): 定位的y坐标，默认值为0.0。
        z (float): 定位的z坐标，默认值为0.0。
        angle (float): 车体相对于水平面的偏航角，单位为弧度，默认值为0.0。
        confidence (float): 定位的置信度，默认值为0.0。
        loc_state (Message_Localization.LocState): 定位状态，默认值为0（即Normal）。
        loc_method (Message_Localization.LocMethod): 定位方法，默认值为0（即PF_LASER_2D）。
        roll (float): 车体相对于水平面的翻滚角，单位为弧度，默认值为0.0。
        pitch (float): 车体相对于水平面的俯仰角，单位为弧度，默认值为0.0。
    """
    __slots__ = ["angle", "confidence", "header", "loc_method", "loc_state", "pitch", "roll", "x", "y", "z"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    LOC_METHOD_FIELD_NUMBER: ClassVar[int]
    LOC_STATE_FIELD_NUMBER: ClassVar[int]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    angle: float
    confidence: float
    header: _message_header_pb2.Message_Header
    loc_method: int
    loc_state: int
    pitch: float
    roll: float
    x: float
    y: float
    z: float

    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...,
                 angle: Optional[float] = ..., roll: Optional[float] = ..., pitch: Optional[float] = ...,
                 confidence: Optional[float] = ..., loc_state: Optional[int] = ...,
                 loc_method: Optional[int] = ...) -> None: ...
