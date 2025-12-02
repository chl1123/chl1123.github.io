import typing
from typing import Union, List

from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import RBK_VERSION

if typing.TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf import msgMotorInfo
    elif RBK_VERSION == 4:
        from v4.protobuf.message.messageV4_movetask_pb2 import MessageV4_MInfo as msgMotorInfo

class MotorInterface(ABC, Message):
    """电机类"""

    @staticmethod
    def getMotorInfos() -> List["msgMotorInfo"]:
        """获取电机信息列表

        Returns:
            (List[msgMotorInfo]): 返回电机信息列表，列表内元素为msgMotorInfo对象

        Examples:
        ```python
        from syspy import Motor
        motorInfos = Motor.getMotorInfos()
        for motorInfo in motorInfos:  # motorInfo为msgMotorInfo的对象
            print(motorInfo.key)
            print(motorInfo.position)
        ```
        """
        raise RBKVersionError()

    @staticmethod
    def getMotorPos(key: str) -> Union[float, int]:
        """获取指定电机的当前位置

        Args:
            key (str): 电机设备的key

        Returns:
            Union[float, int]: 返回电机的当前位置，若电机不存在返回 -1
        """
        raise RBKVersionError()

    @staticmethod
    def getMotorSpeed(key: str) -> Union[float, int]:
        """获取指定电机的当前速度

        Args:
            key (str): 电机设备的key

        Returns:
            Union[float, int]: 返回电机的当前速度，若电机不存在返回 -1
        """
        raise RBKVersionError()

    @classmethod
    def setMotorSpeed(cls, key: str, vel: float, stopDI: str = "") -> bool:
        """让电机以某个速度运行，比如滚筒电机

        Args:
            key (str): 电机设备的key
            vel (float): 电机速度
            stopDI (str): 到位DI。缺省或传""表示没有。

        Returns:
            (bool): 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def setMotorPosition(cls, key: str, pos: float, maxVel: float, stopDI: str = "") -> bool:
        """控制线性电机到特定位置

        Args:
            key (str): 电机设备的key
            pos (float): 发送目标点位置也可能是角度
            maxVel (float): 运行过程中的最大速度不能超过模型文件中的最大速度
            stopDI (str): 如果这个StopDI触发则表示运动到位。缺省或传""表示没有。

        Returns:
            (bool): 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def setMotorPositionAdv(cls, name: str, pos: float, maxSpeed: float = None, maxAcc: float = None,
                            maxDec: float = None, jerk: float = None, stopDI: str = "") -> bool:
        """控制线性电机到特定位置（可控制加速度）

        Args:
            key (str): 电机设备的key
            pos (float): 目标点位置
            maxSpeed (float): 最大速度
            maxAcc (float): 最大加速度
            maxDec (float): 最大减速度
            jerk (float): 最大加加速度
            stopDI (str): 停止DI的key。该DI触发则表示运动到位。缺省或传""表示没有。

        Returns:
            (bool): 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def stopMotor(cls):
        """停止所有非行走的电机"""
        raise RBKVersionError()

    @classmethod
    def resetMotor(cls, key: str) -> bool:
        """将电机重置为不启用状态

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果不存在这个电机则报错
        """
        raise RBKVersionError()

    @classmethod
    def isMotorReached(cls, key: str) -> bool:
        """查看电机是否到位，需要在setMotorPosition或者setMotorSpeed后使用

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果到位则返回True
        """
        raise RBKVersionError()

    @classmethod
    def isMotorPositionReached(cls, key: str, pos: float, stopDI: str = "") -> bool:
        """电机是否到达特定位置

        Args:
            key (str): 电机设备的key
            pos (float): 位置
            stopDI (str): 到位DI。缺省或传""表示没有。

        Returns:
            (bool): 如果到位则返回True
        """
        raise RBKVersionError()

    @classmethod
    def isMotorStop(cls, key: str) -> bool:
        """查询电机是否停止

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果电机不存在则返回False
        """
        raise RBKVersionError()

    @classmethod
    def disableMotor(cls, key: str):
        """电机去使能

        Args:
            key (str): 电机设备的key
        """
        raise RBKVersionError()

    @classmethod
    def enableMotor(cls, key: str):
        """电机使能

        Args:
            key (str): 电机设备的key
        """
        raise RBKVersionError()

    @classmethod
    def motorCalib(cls, key: str):
        """电机标零

        Args:
            key (str): 电机设备的key
        """
        raise RBKVersionError()

    @classmethod
    def motorForceCalib(cls, key: str):
        """

        Args:
            key (str): 电机设备的key
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.motor import MotorV3
    Motor: MotorInterface = MotorV3()
elif RBK_VERSION == 4:
    from syspy.v4.motor import MotorV4
    Motor: MotorInterface = MotorV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
