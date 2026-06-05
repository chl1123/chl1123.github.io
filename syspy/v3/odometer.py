import math
import typing
from typing import List, Optional, Tuple
from syspy.odometer import OdometerInterface


class OdometerV3(OdometerInterface):
    """里程类"""

    _TOPIC = "rbk.protocol.msgOdometer"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgOdometer, msgMotorInfo
        data: msgOdometer = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgOdometer
            cls._MODEL_CLASS = msgOdometer

    def getCycle(self) -> int:
        """获取周期计数

        Returns:
            (Optional[int]): 返回周期计数值
        """
        if self.update():
            return self.data.cycle

    def getPosition(self) -> Tuple[float, float, float]:
        """获取位置，x坐标、y坐标、角度

        Returns:
            (Optional[Tuple[float, float, float]]): 返回位置信息
        """
        if self.update():
            return self.data.x, self.data.y, math.degrees(self.data.angle)

    def getSpeeds(self) -> Tuple[float, float, float]:
        """获取x、y、旋转方向速度

        Returns:
            (Optional[float]): 返回x方向速度值，单位为米每秒
            (Optional[float]): 返回y方向速度值，单位为米每秒
            (Optional[float]): 返回旋转速度值，单位为弧度每秒
        """
        if self.update():
            return self.data.velX, self.data.velY, self.data.velRotate

    def getIsStop(self) -> Optional[bool]:
        """获取是否停止状态

        Returns:
            (Optional[bool]): True表示停止，False表示未停止
        """
        if self.update():
            return self.data.isStop

    def getMotorInfos(self) -> Optional[List[msgMotorInfo]]:
        """获取电机信息列表

        Returns:
            (Optional[List[msgMotorInfo]]): 返回电机信息列表，列表内元素为msgMotorInfo对象
        """
        if self.update():
            return self.data.motorInfo