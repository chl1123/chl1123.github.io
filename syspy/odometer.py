from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
import typing
from typing import List, Tuple
from syspy import RBK_VERSION

if typing.TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf import msgMotorInfo


class OdometerInterface(ABC, Message):
    """里程类"""

    @classmethod
    def get_cycle(cls) -> int:
        """获取周期计数

        Returns:
            (int): 返回周期计数值
        """
        raise RBKVersionError()

    @classmethod
    def get_position(cls) -> typing.Tuple[float, float, float]:
        """获取位置，x坐标、y坐标、角度

        Returns:
            (float): 返回x坐标值，单位为米
            float: 返回y坐标值，单位为米
            float: 返回角度值，单位为角度
        """
        raise RBKVersionError()

    @classmethod
    def get_speeds(cls) -> Tuple[float, float, float]:
        """获取x、y、旋转方向速度

        Returns:
            (float): 返回x方向速度值，单位为米每秒
            float: 返回y方向速度值，单位为米每秒
            float: 返回旋转速度值，单位为弧度每秒
        """
        raise RBKVersionError()

    @classmethod
    def get_is_stop(cls) -> bool:
        """获取是否停止状态

        Returns:
            (bool): True表示停止，False表示未停止
        """
        raise RBKVersionError()

    @classmethod
    def get_detect_skid(cls) -> bool:
        """获取是否检测到打滑

        Returns:
            (bool): True表示检测到打滑，False表示未检测到
        """
        raise RBKVersionError()

    @classmethod
    def get_motor_infos(cls) -> List["msgMotorInfo"]:
        """获取电机信息列表

        Returns:
            (List[msgMotorInfo]): 返回电机信息列表，列表内元素为msgMotorInfo对象

        Examples:
        ```python
        from syspy import Motor
        motor_infos = Motor.get_motor_infos()
        for motor_info in motor_infos:  # motor_info为msgMotorInfo的对象
            print(motor_info.name)
            print(motor_info.position)
        ```
        """
        raise RBKVersionError()
