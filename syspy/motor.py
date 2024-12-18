from .lib.rpc_client import rpcClient
from .service_utils import check, get_function_name


class Motor:
    rpc_client = rpcClient()


    @classmethod
    @check
    def setMotorSpeed(cls, name: str, vel: float, stopDI: int) -> bool:
        """让电机以某个速度运行，比如滚筒电机
        Args:
            name (str): 电机名称
            vel (float): 电机速度
            stopDI (int): 到位DI

        Returns:
            bool: 如果不存在这个电机，则返回False
        """
        return cls.rpc_client.setMotorSpeed(name, vel, stopDI)

    @classmethod
    @check
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
        print("func: {0} name: {1}  pos: {2} maxVel: {3} stopDI: {4}".format(get_function_name(), motor_name, pos, maxVel,
                                                                           stopDI))
        return cls.rpc_client.setMotorPosition(motor_name, pos, maxVel, stopDI)

    @classmethod
    @check
    def resetMotor(cls, motor_name: str) -> bool:
        """将电机重置为不启用状态

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果不存在这个电机则报错
        """
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return cls.rpc_client.resetMotor(motor_name)

    @classmethod
    @check
    def isAllMotorsReached(cls) -> bool:
        """所有电机是否到位

        Returns:
            bool: 如果所有电机到位则为True
        """
        print("func: {0}".format(get_function_name()))
        return cls.rpc_client.isAllMotorsReached()

    @classmethod
    @check
    def isMotorReached(cls, motor_name: str) -> bool:
        """查看电机是否到位，需要在setMotorPosition或者setMotorSpeed后使用

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果到位则返回True
        """
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return cls.rpc_client.isMotorReached(motor_name)

    @classmethod
    @check
    def isMotorPositionReached(cls, motor_name: str, pos: float, stopDI: int) -> bool:
        """电机是否到达特定位置

        Args:
            motor_name (str): 电机名称
            pos (float): 位置
            stopDI (int): 到位DI

        Returns:
            bool: 如果到位则返回True
        """
        print("func: {0} name: {1}  pos: {2} stopDI: {3}".format(get_function_name(), motor_name, pos, stopDI))
        return cls.rpc_client.isMotorPositionReached(motor_name, pos, stopDI)

    @classmethod
    @check
    def isMotorStop(cls, motor_name: str) -> bool:
        """查询电机是否停止

        Args:
            motor_name (str): 电机名称

        Returns:
            bool: 如果电机不存在则返回False
        """
        print("func: {0} motor_name: {1}".format(get_function_name(), motor_name))
        return cls.rpc_client.isMotorStop(motor_name)

    @classmethod
    @check
    def publishSpeed(cls) -> bool:
        """将当前电机控制方案，进行速度规划然后下发

        Returns:
            bool: 如果规划电机速度失败则返回False
        """
        print("func: {0}".format(get_function_name()))
        return cls.rpc_client.publishSpeed()
