import typing

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
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgController
            cls._MODEL_CLASS = msgController

    def get_temperature(self) -> float:
        """获取温度值

        Returns:
            float: 温度数值
        """
        if self.update():
            return self.data.temp

    def get_humidity(self) -> float:
        """获取湿度值

        Returns:
            float: 湿度数值
        """
        if self.update():
            return self.data.humi

    def get_voltage(self) -> float:
        """获取电压值

        Returns:
            float: 电压数值
        """
        if self.update():
            return self.data.voltage

    def get_emc(self) -> bool:
        """获取EMC状态

        Returns:
            bool: EMC状态，True或False
        """
        if self.update():
            return self.data.emc

    def get_brake(self) -> bool:
        """获取制动状态

        Returns:
            bool: 制动状态，True或False
        """
        if self.update():
            return self.data.brake

    def get_driver_EMC(self) -> bool:
        """获取驱动EMC状态

        Returns:
            bool: 驱动EMC状态，True或False
        """
        if self.update():
            return self.data.driverEmc

    def get_manual_charge(self) -> bool:
        """获取手动充电状态

        Returns:
            bool: 手动充电状态，True或False
        """
        if self.update():
            return self.data.manualCharge

    def get_auto_charge(self) -> bool:
        """获取自动充电状态

        Returns:
            bool: 自动充电状态，True或False
        """
        if self.update():
            return self.data.autoCharge

    def get_electric(self) -> bool:
        """获取电动状态

        Returns:
            bool: 电动状态，True或False
        """
        if self.update():
            return self.data.electric

    def get_soft_EMC(self) -> bool:
        """获取软EMC状态

        Returns:
            bool: 软EMC状态，True或False
        """
        if self.update():
            return self.data.softEMC

    def get_is_external_control(self) -> bool:
        """获取是否为外部控制状态

        Returns:
            bool: 是否为外部控制状态，True或False
        """
        if self.update():
            return self.data.isExternalControl

    def get_is_IMU_calibrating(self) -> bool:
        """获取IMU是否正在校准状态

        Returns:
            bool: IMU是否正在校准状态，True或False
        """
        if self.update():
            return self.data.isIMUCalibrating

    def get_ADC_voltage(self) -> float:
        """获取通过ADC检测到的外部电压值

        Returns:
            float: 通过ADC检测到的外部电压数值
        """
        if self.update():
            return self.data.voltagebyAdc
