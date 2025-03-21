import math
import typing

from .lib.py_rpc import Message
from .protobuf.message import Message_Localization


class Loc(Message[Message_Localization]):
    """定位类"""

    _TOPIC = "rbk.protocol.Message_Localization"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = Message_Localization

    @classmethod
    def get_position(cls) -> typing.Tuple[float, float, float]:
        """获取位置，x坐标、y坐标、角度

        Returns:
            float: 返回x坐标值
            float: 返回y坐标值
            float: 返回角度值
        """
        if cls.update():
            return cls.data.x, cls.data.y, math.degrees(cls.data.angle)

    @classmethod
    def get_confidence(cls) -> float:
        """获取定位置信度

        Returns:
            float: 返回定位置信度数值
        """
        if cls.update():
            return cls.data.confidence

    @classmethod
    def get_correction_errs(cls) -> typing.List[float]:
        """获取校正误差列表

        Returns:
            typing.List[float]: 返回校正误差列表
        """
        if cls.update():
            return cls.data.correction_errs

    @classmethod
    def get_reliabilities(cls) -> typing.List[float]:
        """获取可靠性列表

        Returns:
            typing.List[float]: 返回可靠性列表
        """
        if cls.update():
            return cls.data.reliabilities

    @classmethod
    def get_in_forbidden_area(cls) -> bool:
        """获取是否在禁入区域

        Returns:
            bool: True表示在禁入区域，False表示不在
        """
        if cls.update():
            return cls.data.in_forbidden_area

    @classmethod
    def get_update_reason(cls) -> "Message_Localization.UpdateReason":
        """获取更新原因

        Returns:
            Message_Localization.UpdateReason: 返回更新原因枚举值
        """
        if cls.update():
            return cls.data.update_reason

    @classmethod
    def get_loc_state(cls) -> "Message_Localization.LocState":
        """获取定位状态

        Returns:
            Message_Localization.LocState: 返回定位状态枚举值
        """
        if cls.update():
            return cls.data.loc_state

    @classmethod
    def get_similarity(cls) -> float:
        """获取相似度

        Returns:
            float: 返回相似度数值
        """
        if cls.update():
            return cls.data.similarity
