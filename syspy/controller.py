from .lib.py_rpc import Message


class Controller(Message["Message_Controller"]):
    """控制器类"""

    _TOPIC = "rbk.protocol.Message_Controller"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Controller
            cls._MODEL_CLASS = Message_Controller

    @classmethod
    def get_temperature(cls) -> float:
        """获取温度值

        Returns:
            float: 温度数值
        """
        if cls.update():
            return cls.data.temp

    @classmethod
    def get_humidity(cls) -> float:
        """获取湿度值

        Returns:
            float: 湿度数值
        """
        if cls.update():
            return cls.data.humi

    @classmethod
    def get_voltage(cls) -> float:
        """获取电压值

        Returns:
            float: 电压数值
        """
        if cls.update():
            return cls.data.voltage

    @classmethod
    def get_emc(cls) -> bool:
        """获取EMC状态

        Returns:
            bool: EMC状态，True或False
        """
        if cls.update():
            return cls.data.emc

    @classmethod
    def get_brake(cls) -> bool:
        """获取制动状态

        Returns:
            bool: 制动状态，True或False
        """
        if cls.update():
            return cls.data.brake

    @classmethod
    def get_driver_EMC(cls) -> bool:
        """获取驱动EMC状态

        Returns:
            bool: 驱动EMC状态，True或False
        """
        if cls.update():
            return cls.data.driverEmc

    @classmethod
    def get_manual_charge(cls) -> bool:
        """获取手动充电状态

        Returns:
            bool: 手动充电状态，True或False
        """
        if cls.update():
            return cls.data.manualCharge

    @classmethod
    def get_auto_charge(cls) -> bool:
        """获取自动充电状态

        Returns:
            bool: 自动充电状态，True或False
        """
        if cls.update():
            return cls.data.autoCharge

    @classmethod
    def get_electric(cls) -> bool:
        """获取电动状态

        Returns:
            bool: 电动状态，True或False
        """
        if cls.update():
            return cls.data.electric

    @classmethod
    def get_soft_EMC(cls) -> bool:
        """获取软EMC状态

        Returns:
            bool: 软EMC状态，True或False
        """
        if cls.update():
            return cls.data.softEMC

    @classmethod
    def get_is_external_control(cls) -> bool:
        """获取是否为外部控制状态

        Returns:
            bool: 是否为外部控制状态，True或False
        """
        if cls.update():
            return cls.data.isExternalControl

    @classmethod
    def get_is_IMU_calibrating(cls) -> bool:
        """获取IMU是否正在校准状态

        Returns:
            bool: IMU是否正在校准状态，True或False
        """
        if cls.update():
            return cls.data.isIMUCalibrating

    @classmethod
    def get_ADC_voltage(cls) -> float:
        """获取通过ADC检测到的外部电压值

        Returns:
            float: 通过ADC检测到的外部电压数值
        """
        if cls.update():
            return cls.data.voltagebyAdc
