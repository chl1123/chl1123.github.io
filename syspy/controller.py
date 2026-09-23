from abc import ABC
from typing import Optional
from syspy.core.rbk_rpc import Message, RBKVersionError


class ControllerInterface(ABC, Message):
    """控制器类"""

    def getTemperature(self) -> Optional[float]:
        """获取温度值

        Returns:
            (Optional[float]): 控制器温度，单位 ℃。
        """
        raise RBKVersionError()

    def getHumidity(self) -> Optional[float]:
        """获取湿度值

        Returns:
            (Optional[float]): 控制器湿度，单位 %。
        """
        raise RBKVersionError()

    def getVoltage(self) -> Optional[float]:
        """获取电压值

        Returns:
            (Optional[float]): 控制器电压，单位 V。
        """
        raise RBKVersionError()

    def getEmc(self) -> Optional[bool]:
        """获取EMC状态

        Returns:
            (bool): EMC状态，True或False
        """
        raise RBKVersionError()

    def getBrake(self) -> Optional[bool]:
        """获取制动状态

        Returns:
            (bool): 制动状态，True或False
        """
        raise RBKVersionError()

    def getDriverEmc(self) -> Optional[bool]:
        """获取驱动EMC状态

        Returns:
            (Optional[bool]): 驱动EMC状态，True或False
        """
        raise RBKVersionError()

    def getManualCharge(self) -> Optional[bool]:
        """获取手动充电状态

        Returns:
            (bool): 手动充电状态，True或False
        """
        raise RBKVersionError()

    def getAutoCharge(self) -> Optional[bool]:
        """获取自动充电状态

        Returns:
            (Optional[bool]): 自动充电状态，True或False
        """
        raise RBKVersionError()

    def getElectric(self) -> Optional[bool]:
        """获取电动状态

        Returns:
            (Optional[bool]): 电动状态，True或False
        """
        raise RBKVersionError()

    def getSoftEmc(self) -> Optional[bool]:
        """获取软EMC状态

        Returns:
            (Optional[bool]): 软EMC状态，True或False
        """
        raise RBKVersionError()

    def getIsExternalControl(self) -> Optional[bool]:
        """获取是否为外部控制状态

        Returns:
            (Optional[bool]): 是否为外部控制状态，True或False
        """
        raise RBKVersionError()

    def getIsImuCalibrating(self) -> Optional[bool]:
        """获取IMU是否正在校准状态

        Returns:
            (Optional[bool]): IMU是否正在校准状态，True或False
        """
        raise RBKVersionError()

    def getAdcVoltage(self) -> Optional[float]:
        """获取通过ADC检测到的外部电压值

        Returns:
            (Optional[float]): 通过 ADC 检测到的外部电压，单位 V。
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
