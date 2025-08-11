import typing
from typing import Union, List

from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import rbk_version

if typing.TYPE_CHECKING:
    if rbk_version == 3:
        from syspy.v3.protobuf import Message_MotorInfo
    elif rbk_version == 4:
        from v4.include.protocol.messageV4_movetask_pb2 import MessageV4_MInfo as Message_MotorInfo

class MotorInterface(ABC, Message):
    """电机类"""

    @staticmethod
    def get_motor_infos() -> List["Message_MotorInfo"]:
        """获取电机信息列表

        Returns:
            List[Message_MotorInfo]: 返回电机信息列表，列表内元素为Message_Odometer对象
        """
        raise RBKVersionError()

    @staticmethod
    def get_motor_pos(motor_name: str) -> Union[float, int]:
        """获取指定电机的当前位置

        Args:
            motor_name (str): 电机名称

        Returns:
            Union[float, int]: 返回电机的当前位置，若电机不存在返回 -1
        """
        raise RBKVersionError()

    @staticmethod
    def get_motor_speed(motor_name: str) -> Union[float, int]:
        """获取指定电机的当前速度

        Args:
            motor_name (str): 电机名称

        Returns:
            Union[float, int]: 返回电机的当前速度，若电机不存在返回 -1
        """
        raise RBKVersionError()

    @classmethod
    def setMotorSpeed(cls, name: str, vel: float, stopDI: int) -> bool:
        """让电机以某个速度运行，比如滚筒电机

        Args:
            name (str): 电机名称
            vel (float): 电机速度
            stopDI (int): 到位DI

        Returns:
            bool: 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def setMotorPosition(cls, motor_name: str, pos: float, maxVel: float, stopDI: int) -> bool:
        """控制线性电机到特定位置

        Args:
            motor_name (str): 模型文件中的电机名称
            pos (float): 发送目标点位置也可能是角度
            maxVel (float): 运行过程中的最大速度不能超过模型文件中的最大速度
            stopDI (int): 如果这个StopDI触发则表示运动到位

        Returns:
            bool: 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def setMotorPositionAdv(cls, name: str, pos: float, maxSpeed: float = None, maxAcc: float = None,
                            maxDec: float = None, jerk: float = None, stopDI: int = None) -> bool:
        """控制线性电机到特定位置（可控制加速度）

        Args:
            name (str): 模型文件中的电机名称
            pos (float): 目标点位置
            maxSpeed (float): 最大速度
            maxAcc (float): 最大加速度
            maxDec (float): 最大减速度
            jerk (float): 最大加加速度
            stopDI (int): 停止DI。该DI触发则表示运动到位

        Returns:
            bool: 如果不存在这个电机，则返回False
        """
        raise RBKVersionError()

    @classmethod
    def stopMotor(cls):
        """停止所有非行走的电机"""
        raise RBKVersionError()

    @classmethod
    def resetMotor(cls, motor_name: str) -> bool:
        """将电机重置为不启用状态

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果不存在这个电机则报错
        """
        raise RBKVersionError()

    @classmethod
    def isMotorReached(cls, motor_name: str) -> bool:
        """查看电机是否到位，需要在setMotorPosition或者setMotorSpeed后使用

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果到位则返回True
        """
        raise RBKVersionError()

    @classmethod
    def isMotorPositionReached(cls, motor_name: str, pos: float, stopDI: int) -> bool:
        """电机是否到达特定位置

        Args:
            motor_name (str): 电机名称
            pos (float): 位置
            stopDI (int): 到位DI

        Returns:
            bool: 如果到位则返回True
        """
        raise RBKVersionError()

    @classmethod
    def isMotorStop(cls, motor_name: str) -> bool:
        """查询电机是否停止

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果电机不存在则返回False
        """
        raise RBKVersionError()

    @classmethod
    def disableMotor(cls, name: str):
        """电机去使能

        Args:
            name (str): 电机名称
        """
        raise RBKVersionError()

    @classmethod
    def enableMotor(cls, name: str):
        """电机使能

        Args:
            name (str): 电机名称
        """
        raise RBKVersionError()

    @classmethod
    def motorCalib(cls, m: str):
        """电机标零

        Args:
            m (str):
        """
        raise RBKVersionError()

    @classmethod
    def motorForceCalib(cls, m: str):
        """

        Args:
            m (str):
        """
        raise RBKVersionError()


from syspy.config import rbk_version
if rbk_version == 3:
    from syspy.v3.motor import MotorV3
    Motor: MotorInterface = MotorV3()
elif rbk_version == 4:
    from syspy.v4.motor import MotorV4
    Motor: MotorInterface = MotorV4()
else:
    raise ValueError(f"Unsupported RBK version: {rbk_version}")
