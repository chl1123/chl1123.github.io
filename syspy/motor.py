from .lib.py_rpc import Service, default_plugin, call_service


@default_plugin("MoveFactory")
class Motor(Service):
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
    def isAllMotorsReached(cls) -> bool:
        """所有电机是否到位

        Returns:
            bool: 如果所有电机到位则为True
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
    def disableMotor(cls, name: str) -> bool:
        """电机去使能
        Args:
            name (str): 电机名称
        Returns:
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def enableMotor(cls, name: str):
        """电机使能
        Args:
            name (str): 电机名称
        Returns:
        """
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def motorCalib(cls, m: str):
        """
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
