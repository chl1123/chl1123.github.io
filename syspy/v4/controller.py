from syspy.controller import ControllerInterface


class ControllerV4(ControllerInterface):
    """控制器类"""
    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_controller_pb2 import MessageV4_Controller
            cls._MODEL_CLASS = MessageV4_Controller

    def getTemperature(self) -> float:
        """获取温度值

        Returns:
            (float): 温度数值
        """
        if self.update():
            return self.data.temp

    def getHumidity(self) -> float:
        """获取湿度值

        Returns:
            (float): 湿度数值
        """
        if self.update():
            return self.data.humi

    def getVoltage(self) -> float:
        """获取电压值

        Returns:
            (float): 电压数值
        """
        if self.update():
            return self.data.voltage

    def getEmc(self) -> bool:
        """获取EMC状态

        Returns:
            (bool): EMC状态，True或False
        """
        if self.update():
            return self.data.emc

    def getBrake(self) -> bool:
        """获取制动状态

        Returns:
            (bool): 制动状态，True或False
        """
        if self.update():
            return self.data.brake

    def getDriverEmc(self) -> bool:
        """获取驱动EMC状态

        Returns:
            (bool): 驱动EMC状态，True或False
        """
        if self.update():
            return self.data.driverEmc

    def getManualCharge(self) -> bool:
        """获取手动充电状态

        Returns:
            (bool): 手动充电状态，True或False
        """
        if self.update():
            return self.data.manualCharge

    def getAutoCharge(self) -> bool:
        """获取自动充电状态

        Returns:
            (bool): 自动充电状态，True或False
        """
        if self.update():
            return self.data.autoCharge

    def getElectric(self) -> bool:
        """获取电动状态

        Returns:
            (bool): 电动状态，True或False
        """
        if self.update():
            return self.data.electric

    def getSoftEmc(self) -> bool:
        """获取软EMC状态

        Returns:
            (bool): 软EMC状态，True或False
        """
        if self.update():
            return self.data.softEMC

    def getIsExternalControl(self) -> bool:
        """获取是否为外部控制状态

        Returns:
            (bool): 是否为外部控制状态，True或False
        """
        if self.update():
            return self.data.isExternalControl

    def getIsImuCalibrating(self) -> bool:
        """获取IMU是否正在校准状态

        Returns:
            (bool): IMU是否正在校准状态，True或False
        """
        if self.update():
            return self.data.isIMUCalibrating

    def getAdcVoltage(self) -> float:
        """获取通过ADC检测到的外部电压值

        Returns:
            (float): 通过ADC检测到的外部电压数值
        """
        if self.update():
            return self.data.voltagebyAdc