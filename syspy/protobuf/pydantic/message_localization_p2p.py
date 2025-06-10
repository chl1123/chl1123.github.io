# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
import typing
from enum import IntEnum

from google.protobuf.message import Message  # type: ignore
from pydantic import BaseModel
from pydantic import Field

from .message_header_p2p import Message_Header


class Message_Localization(BaseModel):
    """表示本地化消息的模型类。

    Attributes:
        header (typing.Optional[Message_Header]): 消息头，默认为None。
        x (float): 定位的x坐标，默认值为0.0。
        y (float): 定位的y坐标，默认值为0.0。
        angle (float): 定位的角度，默认值为0.0。
        confidence (float): 定位的置信度，默认值为0.0。
        correction_errs (typing.List[float]): 校正误差列表，默认是空列表。
        reliabilities (typing.List[float]): 可靠性列表，默认是空列表。
        in_forbidden_area (bool): 是否在禁区内，默认值为False。
        update_reason (Message_Localization.UpdateReason): 定位更新原因，默认值为0（即NONE）。
        loc_state (Message_Localization.LocState): 定位状态，默认值为0（即Normal）。
        similarity (float): 相似度，默认值为0.0。
        loc_method (Message_Localization.LocMethod): 定位方法，默认值为0（即PF_LASER_2D）。
        roll (float): 车体相对于水平面的翻滚角，单位为度，默认值为0.0。
        pitch (float): 车体相对于水平面的俯仰角，单位为度，默认值为0.0。
    """

    class UpdateReason(IntEnum):
        """更新原因的枚举类。

        Attributes:
            NONE (int): 无更新原因
            OdoUpdate (int): 里程计更新
            LaserCorrec (int): 激光校正
            LaserThenOdo (int): 先激光校正后里程计更新
            PGVCORRECT (int): PGV校正
        """
        NONE = 0
        OdoUpdate = 1
        LaserCorrec = 2
        LaserThenOdo = 3
        PGVCORRECT = 4

    class LocState(IntEnum):
        """定位状态的枚举类。

        Attributes:
            Normal (int): 正常定位状态
            Skidding (int): 打滑定位状态
            LowConfidence (int): 低置信度定位状态
        """
        Normal = 0
        Skidding = 1
        LowConfidence = 2

    class LocMethod(IntEnum):
        """定位方法的枚举类。

        Attributes:
            PF_LASER_2D (int): 2D粒子滤波激光定位方法
            SLAM_2D (int): 2D同步定位与地图构建定位方法
            PGV (int): PGV定位方法
            REFLECTOR (int): 反射器定位方法
            LASER_3D (int): 3D激光定位方法
            BAR_CODE (int): 条形码定位方法
        """
        PF_LASER_2D = 0
        SLAM_2D = 1
        PGV = 2
        REFLECTOR = 3
        LASER_3D = 4
        BAR_CODE = 5

    header: typing.Optional[Message_Header] = None
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    angle: float = Field(default=0.0)
    confidence: float = Field(default=0.0)
    correction_errs: typing.List[float] = Field(default_factory=list)
    reliabilities: typing.List[float] = Field(default_factory=list)
    in_forbidden_area: bool = Field(default=False)
    update_reason: "Message_Localization.UpdateReason" = Field(default=0)
    loc_state: "Message_Localization.LocState" = Field(default=0)
    similarity: float = Field(default=0.0)
    loc_method: "Message_Localization.LocMethod" = Field(default=0)
    # 增加车体相对与水平面的roll和pitch
    # 单位 deg
    roll: float = Field(default=0.0)
    # 单位 deg
    pitch: float = Field(default=0.0)


class Message_LocFinished(BaseModel):
    value: bool = Field(default=False)


class Message_3DPose(BaseModel):
    header: typing.Optional[Message_Header] = None
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    q_w: float = Field(default=0.0)
    q_x: float = Field(default=0.0)
    q_y: float = Field(default=0.0)
    q_z: float = Field(default=0.0)
    extra_data: str = Field(default="")


class Message_IRCAMPose(BaseModel):
    """
    红外相机定位消息发布
    """

    pose: typing.Optional[Message_3DPose] = None


class Message_2D_CamInfo(BaseModel):
    """
    2D相机参数信息
    """

    header: typing.Optional[Message_Header] = None
    camera_name: str = Field(default="")
    m_infrared: float = Field(default=0.0)
    m_seertag_size: float = Field(default=0.0)
    m_seertag_family_id: float = Field(default=0.0)
    model_type: str = Field(default="")  # PINHOLE
    distortion_modle: str = Field(default="")
    is_intrinsics_caib: bool = Field(default=False)
    is_extrinsics_caib: bool = Field(default=False)
    # 相机外参
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    z: float = Field(default=0.0)
    roll: float = Field(default=0.0)
    pitch: float = Field(default=0.0)
    yaw: float = Field(default=0.0)
    # 相机内参
    m_fx_: float = Field(default=0.0)
    m_fy_: float = Field(default=0.0)
    m_cx_: float = Field(default=0.0)
    m_cy_: float = Field(default=0.0)
    m_k1_: float = Field(default=0.0)
    m_k2_: float = Field(default=0.0)
    m_k3_: float = Field(default=0.0)
    m_k4_: float = Field(default=0.0)
    m_k5_: float = Field(default=0.0)
    m_k6_: float = Field(default=0.0)
    m_p1_: float = Field(default=0.0)
    m_p2_: float = Field(default=0.0)
