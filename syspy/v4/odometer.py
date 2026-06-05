import math
import typing
from typing import List, Tuple, Optional

from syspy.core.rbk_rpc import RBKVersionError
from syspy.odometer import OdometerInterface


class OdometerV4(OdometerInterface):
    """里程类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_odometer_pb2 import MessageV4_Odometer
            cls._MODEL_CLASS = MessageV4_Odometer

    def getCycle(self) -> int:
        """获取周期计数

        Returns:
            (Optional[int]): 返回周期计数值
        """
        if self.update():
            return self.data.cycle

    def getPosition(self) -> Optional[Tuple[float, float, float]]:
        """获取位置，x坐标、y坐标、角度

        Returns:
            (Optional[Tuple[float, float, float]]): 返回位置信息
        """
        if self.update():
            return self.data.x, self.data.y, math.degrees(self.data.angle)

    def getSpeeds(self) -> Optional[Tuple[float, float, float]]:
        """获取x、y、旋转方向速度

        Returns:
            (Optional[float]): 返回x方向速度值，单位为米每秒
            (Optional[float]): 返回y方向速度值，单位为米每秒
            (Optional[float]): 返回旋转速度值，单位为弧度每秒
        """
        if self.update():
            return self.data.vel_x, self.data.vel_y, self.data.vel_rotate

    def getIsStop(self) -> Optional[bool]:
        """获取是否停止状态

        Returns:
            (Optional[bool]): True表示停止，False表示未停止
        """
        if self.update():
            return self.data.is_stop

    def getMotorInfos(self) -> List["MessageV4_MotorInfo"]:
        raise RBKVersionError()
