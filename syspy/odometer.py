from abc import ABC

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.core.rbk_rpc import Message, RBKVersionError
from typing import Optional, Tuple, TYPE_CHECKING
from syspy import RBK_VERSION

if TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf.message.message_motorinfos_pb2 import msgMotorInfo


class OdometerInterface(ABC, Message):
    """里程类"""

    def getCycle(self) -> Optional[int]:
        """获取周期计数

        Returns:
            (Optional[int]): 周期计数，单位 次。
        """
        raise RBKVersionError()

    def getPosition(self) -> Optional[Tuple[float, float, float]]:
        """获取位置，x坐标、y坐标、角度

        Returns:
            (Optional[Tuple[float, float, float]]): (x 坐标, y 坐标, 角度)，
                x/y 单位 m，角度单位 °。
        """
        raise RBKVersionError()

    def getSpeeds(self) -> Optional[Tuple[float, float, float]]:
        """获取x、y、旋转方向速度

        Returns:
            (Optional[Tuple[float, float, float]]): (x 方向速度, y 方向速度, 旋转角速度)，
                x/y 单位 m/s，旋转角速度单位 rad/s。
        """
        raise RBKVersionError()

    def getIsStop(self) -> Optional[bool]:
        """获取是否停止状态

        Returns:
            (Optional[bool]): True 表示停止，False 表示未停止。
        """
        raise RBKVersionError()

    def getMotorInfos(self) -> Optional[RepeatedCompositeFieldContainer["msgMotorInfo"]]:
        """获取电机信息列表

        Returns:
            (Optional[RepeatedCompositeFieldContainer[msgMotorInfo]]): 电机信息列表，列表内元素为 msgMotorInfo 对象。
                每个元素主要字段的单位：

                - position (float): 电机位置，单位 m
                - speed (float): 电机速度，单位 m/s
                - current (float): 电流，单位 A
                - voltage (float): 电压，单位 V

        Examples:
        ```python
        from syspy import Odometer
        motor_infos = Odometer.getMotorInfos()
        for motor_info in motor_infos:  # motor_info为msgMotorInfo的对象
            print(motor_info.key)
            print(motor_info.position)
        ```
        """
        raise RBKVersionError()
