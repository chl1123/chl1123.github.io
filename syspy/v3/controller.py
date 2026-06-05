import typing
from typing import Optional

from syspy.controller import ControllerInterface


class ControllerV3(ControllerInterface):
    """控制器类"""

    _TOPIC = "rbk.protocol.msgController"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    if typing.TYPE_CHECKING:
        from .protobuf import msgController
        data: msgController = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgController
            cls._MODEL_CLASS = msgController

    def getTemperature(self) -> Optional[float]:
        """获取温度值

        Returns:
            (Optional[float]): 温度数值
        """
        if self.update():
            return self.data.temp

    def getHumidity(self) -> Optional[float]:
        """获取湿度值

        Returns:
            (Optional[float]): 湿度数值
        """
        if self.update():
            return self.data.humi

    def getVoltage(self) -> Optional[float]:
        """获取电压值

        Returns:
            (Optional[float]): 电压数值
        """
        if self.update():
            return self.data.voltage

    def getEmc(self) -> Optional[bool]:
        """获取EMC状态

        Returns:
            (Optional[bool]): EMC状态，True或False
        """
        if self.update():
            return self.data.emc

    def getBrake(self) -> Optional[bool]:
        """获取制动状态

        Returns:
            (Optional[bool]): 制动状态，True或False
        """
        if self.update():
            return self.data.brake

    def getDriverEmc(self) -> Optional[bool]:
        """获取驱动EMC状态

        Returns:
            (Optional[bool]): 驱动EMC状态，True或False
        """
        if self.update():
            return self.data.driverEmc

    def getManualCharge(self) -> Optional[bool]:
        """获取手动充电状态

        Returns:
            (Optional[bool]): 手动充电状态，True或False
        """
        if self.update():
            return self.data.manualCharge

    def getAutoCharge(self) -> Optional[bool]:
        """获取自动充电状态

        Returns:
            (Optional[bool]): 自动充电状态，True或False
        """
        if self.update():
            return self.data.autoCharge

    def getElectric(self) -> Optional[bool]:
        """获取电动状态

        Returns:
            (Optional[bool]): 电动状态，True或False
        """
        if self.update():
            return self.data.electric

    def getSoftEmc(self) -> Optional[bool]:
        """获取软EMC状态

        Returns:
            (Optional[bool]): 软EMC状态，True或False
        """
        if self.update():
            return self.data.softEMC

    def getIsExternalControl(self) -> Optional[bool]:
        """获取是否为外部控制状态

        Returns:
            (Optional[bool]): 是否为外部控制状态，True或False
        """
        if self.update():
            return self.data.isExternalControl

    def getIsImuCalibrating(self) -> Optional[bool]:
        """获取IMU是否正在校准状态

        Returns:
            (Optional[bool]): IMU是否正在校准状态，True或False
        """
        if self.update():
            return self.data.isIMUCalibrating

    def getAdcVoltage(self) -> Optional[float]:
        """获取通过ADC检测到的外部电压值

        Returns:
            (Optional[float]): 通过ADC检测到的外部电压数值
        """
        if self.update():
            return self.data.voltagebyAdc