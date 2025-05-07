from typing import Union

from .lib.py_rpc import Service, default_plugin, call_service
from .navigation import NavSpeed
from .odometer import Odometer


@default_plugin("MoveFactory")
class Motor(Service):
    """电机类"""

    @staticmethod
    def get_motor_pos(motor_name: str) -> Union[float, int]:
        """获取指定电机的当前位置

        Args:
            motor_name (str): 电机名称

        Returns:
            Union[float, int]: 返回电机的当前位置，若电机不存在返回 -1
        """
        motor_pos = -1
        if Odometer.update():
            for motor in Odometer.data.motor_info:
                if motor.motor_name == motor_name:
                    motor_pos = motor.position
        return motor_pos

    @staticmethod
    def get_motor_speed(motor_name: str) -> Union[float, int]:
        """获取指定电机的当前速度

        Args:
            motor_name (str): 电机名称

        Returns:
            Union[float, int]: 返回电机的当前速度，若电机不存在返回 -1
        """
        motor_speed = -1
        if NavSpeed.update():
            for motor in NavSpeed.data.motor_cmd:
                if motor.motor_name == motor_name:
                    motor_speed = motor.value
        return motor_speed

    @classmethod
    @call_service()
    def setMotorSpeed(cls, name: str, vel: float, stopDI: int) -> bool:
        """让电机以某个速度运行，比如滚筒电机

        Args:
            name (str): 电机名称
            vel (float): 电机速度
            stopDI (int): 到位DI

        Returns:
            bool: 如果不存在这个电机，则返回False
        """
        pass

    @classmethod
    @call_service()
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
        pass

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
        params = {"name": name, "position": pos}
        if maxSpeed is not None:
            params["maxSpeed"] = maxSpeed
        if maxAcc is not None:
            params["maxAcc"] = maxAcc
        if maxDec is not None:
            params["maxDec"] = maxDec
        if jerk is not None:
            params["jerk"] = jerk
        if stopDI is not None:
            params["stopDI"] = stopDI
        return cls.client().call_service("MoveFactory", "setMotorPositionAdv", params)

    @classmethod
    @call_service()
    def stopMotor(cls):
        """停止所有非行走的电机"""
        pass

    @classmethod
    @call_service()
    def resetMotor(cls, motor_name: str) -> bool:
        """将电机重置为不启用状态

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果不存在这个电机则报错
        """
        pass

    @classmethod
    @call_service()
    def isMotorReached(cls, motor_name: str) -> bool:
        """查看电机是否到位，需要在setMotorPosition或者setMotorSpeed后使用

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果到位则返回True
        """
        pass

    @classmethod
    @call_service()
    def isMotorPositionReached(cls, motor_name: str, pos: float, stopDI: int) -> bool:
        """电机是否到达特定位置

        Args:
            motor_name (str): 电机名称
            pos (float): 位置
            stopDI (int): 到位DI

        Returns:
            bool: 如果到位则返回True
        """
        pass

    @classmethod
    @call_service()
    def isMotorStop(cls, motor_name: str) -> bool:
        """查询电机是否停止

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果电机不存在则返回False
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def disableMotor(cls, name: str):
        """电机去使能

        Args:
            name (str): 电机名称
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def enableMotor(cls, name: str):
        """电机使能

        Args:
            name (str): 电机名称
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def motorCalib(cls, m: str):
        """电机标零

        Args:
            m (str):
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def motorForceCalib(cls, m: str):
        """

        Args:
            m (str):
        """
        pass
