from abc import ABC
from typing import Optional
from syspy.core.rbk_rpc import Message, RBKVersionError


class ControllerInterface(ABC, Message):
    """控制器类"""

    @classmethod
    def getTemperature(cls) -> Optional[float]:
        """获取温度值

        Returns:
            (Optional[float]): 温度数值
        """
        raise RBKVersionError()

    @classmethod
    def getHumidity(cls) -> Optional[float]:
        """获取湿度值

        Returns:
            (Optional[float]): 湿度数值
        """
        raise RBKVersionError()

    @classmethod
    def getVoltage(cls) -> Optional[float]:
        """获取电压值

        Returns:
            (Optional[float]): 电压数值
        """
        raise RBKVersionError()

    @classmethod
    def getEmc(cls) -> Optional[bool]:
        """获取EMC状态

        Returns:
            (bool): EMC状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getBrake(cls) -> Optional[bool]:
        """获取制动状态

        Returns:
            (bool): 制动状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getDriverEmc(cls) -> Optional[bool]:
        """获取驱动EMC状态

        Returns:
            (Optional[bool]): 驱动EMC状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getManualCharge(cls) -> Optional[bool]:
        """获取手动充电状态

        Returns:
            (bool): 手动充电状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getAutoCharge(cls) -> Optional[bool]:
        """获取自动充电状态

        Returns:
            (Optional[bool]): 自动充电状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getElectric(cls) -> Optional[bool]:
        """获取电动状态

        Returns:
            (Optional[bool]): 电动状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getSoftEmc(cls) -> Optional[bool]:
        """获取软EMC状态

        Returns:
            (Optional[bool]): 软EMC状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getIsExternalControl(cls) -> Optional[bool]:
        """获取是否为外部控制状态

        Returns:
            (Optional[bool]): 是否为外部控制状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getIsImuCalibrating(cls) -> Optional[bool]:
        """获取IMU是否正在校准状态

        Returns:
            (Optional[bool]): IMU是否正在校准状态，True或False
        """
        raise RBKVersionError()

    @classmethod
    def getAdcVoltage(cls) -> Optional[float]:
        """获取通过ADC检测到的外部电压值

        Returns:
            (Optional[float]): 通过ADC检测到的外部电压数值
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.controller import ControllerV3
    Controller: ControllerInterface = ControllerV3()
elif RBK_VERSION == 4:
    from syspy.v4.controller import ControllerV4
    Controller: ControllerInterface = ControllerV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
