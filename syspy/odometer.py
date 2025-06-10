import math
import typing
from typing import List, Tuple

from .lib.py_rpc import Message

if typing.TYPE_CHECKING:
    from .protobuf import Message_MotorInfo


class Odometer(Message["Message_Odometer"]):
    """里程类"""

    _TOPIC = "rbk.protocol.Message_Odometer"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Odometer
            cls._MODEL_CLASS = Message_Odometer

    @classmethod
    def get_cycle(cls) -> int:
        """获取周期计数

        Returns:
            int: 返回周期计数值
        """
        if cls.update():
            return cls.data.cycle

    @classmethod
    def get_position(cls) -> typing.Tuple[float, float, float]:
        """获取位置，x坐标、y坐标、角度

        Returns:
            float: 返回x坐标值，单位为米
            float: 返回y坐标值，单位为米
            float: 返回角度值，单位为角度
        """
        if cls.update():
            return cls.data.x, cls.data.y, math.degrees(cls.data.angle)

    @classmethod
    def get_speeds(cls) -> Tuple[float, float, float]:
        """获取x、y、旋转方向速度

        Returns:
            float: 返回x方向速度值，单位为米每秒
            float: 返回y方向速度值，单位为米每秒
            float: 返回旋转速度值，单位为弧度每秒
        """
        if cls.update():
            return cls.data.vel_x, cls.data.vel_y, cls.data.vel_rotate

    @classmethod
    def get_is_stop(cls) -> bool:
        """获取是否停止状态

        Returns:
            bool: True表示停止，False表示未停止
        """
        if cls.update():
            return cls.data.is_stop

    @classmethod
    def get_detect_skid(cls) -> bool:
        """获取是否检测到打滑

        Returns:
            bool: True表示检测到打滑，False表示未检测到
        """
        if cls.update():
            return cls.data.detect_skid

    @classmethod
    def get_motor_infos(cls) -> List["Message_MotorInfo"]:
        """获取电机信息列表

        Returns:
            List[Message_MotorInfo]: 返回电机信息列表，列表内元素为Message_Odometer对象
        """
        if cls.update():
            return cls.data.motor_info

    @classmethod
    def get_follow_err(cls) -> bool:
        """获取是否有电机跟随错误

        Returns:
            bool: True表示有电机跟随错误，False表示无
        """
        if cls.update():
            return cls.data.follow_err
