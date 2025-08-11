import math
import typing
from typing import List, Tuple
from syspy.odometer import OdometerInterface


class OdometerV3(OdometerInterface):
    """里程类"""

    _TOPIC = "rbk.protocol.Message_Odometer"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import Message_Odometer
        data: Message_Odometer = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Odometer
            cls._MODEL_CLASS = Message_Odometer

    def get_cycle(self) -> int:
        """获取周期计数

        Returns:
            int: 返回周期计数值
        """
        if self.update():
            return self.data.cycle

    def get_position(self) -> typing.Tuple[float, float, float]:
        """获取位置，x坐标、y坐标、角度

        Returns:
            float: 返回x坐标值，单位为米
            float: 返回y坐标值，单位为米
            float: 返回角度值，单位为角度
        """
        if self.update():
            return self.data.x, self.data.y, math.degrees(self.data.angle)

    def get_speeds(self) -> Tuple[float, float, float]:
        """获取x、y、旋转方向速度

        Returns:
            float: 返回x方向速度值，单位为米每秒
            float: 返回y方向速度值，单位为米每秒
            float: 返回旋转速度值，单位为弧度每秒
        """
        if self.update():
            return self.data.vel_x, self.data.vel_y, self.data.vel_rotate

    def get_is_stop(self) -> bool:
        """获取是否停止状态

        Returns:
            bool: True表示停止，False表示未停止
        """
        if self.update():
            return self.data.is_stop

    def get_detect_skid(self) -> bool:
        """获取是否检测到打滑

        Returns:
            bool: True表示检测到打滑，False表示未检测到
        """
        if self.update():
            return self.data.detect_skid

    def get_motor_infos(self) -> List["Message_MotorInfo"]:
        """获取电机信息列表

        Returns:
            List[Message_MotorInfo]: 返回电机信息列表，列表内元素为Message_Odometer对象
        """
        if self.update():
            return self.data.motor_info
