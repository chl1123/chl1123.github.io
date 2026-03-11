from typing import Union, List

from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.motor import MotorInterface


@default_plugin("MoveFactory")
class MotorV3(MotorInterface):
    """电机类"""

    @staticmethod
    def getMotorInfos() -> List["msgMotorInfo"]:
        """获取电机信息列表

        Returns:
            List[msgMotorInfo]: 返回电机信息列表，列表内元素为msgOdometer对象
        """
        from syspy import Odometer
        return Odometer.data.motorInfo

    @staticmethod
    def getMotorPos(key: str) -> Union[float, int]:
        """获取指定电机的当前位置

        Args:
            key (str): 电机设备的key

        Returns:
            Union[float, int]: 返回电机的当前位置，若电机不存在返回 -1
        """
        from syspy import Odometer
        motor_pos = -1
        if Odometer.update():
            for motor in Odometer.data.motorInfo:
                if motor.key == key:
                    motor_pos = motor.position
        return motor_pos

    @staticmethod
    def getMotorSpeed(key: str) -> Union[float, int]:
        """获取指定电机的当前速度

        Args:
            key (str): 电机设备的key

        Returns:
            Union[float, int]: 返回电机的当前速度，若电机不存在返回 -1
        """
        from syspy import NavSpeed
        motor_speed = -1
        if NavSpeed.update():
            for motor in NavSpeed.data.motorCmd:
                if motor.key == key:
                    motor_speed = motor.value
        return motor_speed

    @classmethod
    @call_service()
    def setMotorSpeed(cls, key: str, vel: float, stopDI: str = "") -> bool:
        """让电机以某个速度运行，比如滚筒电机

        Args:
            key (str): 电机设备的key
            vel (float): 电机速度
            stopDI (str): 到位DI。缺省或传""表示没有。

        Returns:
            (bool): 如果不存在这个电机，则返回False
        """
        pass

    @classmethod
    @call_service()
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
        pass

    @classmethod
    def setMotorPositionAdv(cls, key: str, pos: float, maxSpeed: float = None, maxAcc: float = None,
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
        params = {"key": key, "position": pos}
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
    def resetMotor(cls, key: str) -> bool:
        """将电机重置为不启用状态

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果不存在这个电机则报错
        """
        pass

    @classmethod
    @call_service()
    def isMotorReached(cls, key: str) -> bool:
        """查看电机是否到位，需要在setMotorPosition或者setMotorSpeed后使用

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果到位则返回True
        """
        pass

    @classmethod
    @call_service()
    def isMotorPositionReached(cls, key: str, pos: float, stopDI: str = "") -> bool:
        """电机是否到达特定位置

        Args:
            key (str): 电机设备的key
            pos (float): 位置
            stopDI (str): 到位DI。缺省或传""表示没有。

        Returns:
            (bool): 如果到位则返回True
        """
        pass

    @classmethod
    @call_service()
    def isMotorStop(cls, key: str) -> bool:
        """查询电机是否停止

        Args:
            key (str): 电机设备的key

        Returns:
            (bool): 如果电机不存在则返回False
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def disableMotor(cls, key: str):
        """电机去使能

        Args:
            key (str): 电机设备的key
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def enableMotor(cls, key: str):
        """电机使能

        Args:
            key (str): 电机设备的key
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def motorCalib(cls, key: str):
        """电机标零

        Args:
            key (str): 电机设备的key
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def motorForceCalib(cls, key: str):
        """

        Args:
            key (str): 电机设备的key
        """
        pass
    
    @classmethod
    @call_service(plugin_name="DSPChassis")
    def clearMotorEncoder(cls, key: str):
        """

        Args:
            key (str): 电机设备的key
        """
        pass
    
    @classmethod
    @call_service(plugin_name="DSPChassis")
    def clearMotorFault(cls, key: str):
        """

        Args:
            key (str): 电机设备的key
        """
        pass
    
    @classmethod
    @call_service(plugin_name="DSPChassis")
    def setMotorSpeed(cls, canId:int, type: str, speed: float):
        """

        Args:
            canId    (int): CAN ID
            type (str): 电机类型 walk,steer
            speed (float): 速度
        """
        pass
    
    @classmethod
    @call_service(plugin_name="DSPChassis")
    def setMotorPosition(cls, canId:int, type: str, position: float):
        """

        Args:
            canId    (int): CAN ID
            type (str): 电机类型 walk,steer
            position (float): 位置
        """
        pass