from syspy.lib.py_rpc import Message, default_plugin, call_service


@default_plugin("DSPChassis")
class Battery(Message["Message_Battery"]):
    """电池类"""

    _TOPIC = "rbk.protocol.Message_Battery"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Battery  # 延迟导入
            cls._MODEL_CLASS = Message_Battery

    @classmethod
    def get_percentage(cls) -> float:
        """获取电池电量百分比

        Returns:
            float: 返回电池电量百分比数值
        """
        if cls.update():
            return cls.data.percetage

    @classmethod
    def get_charge_current(cls) -> float:
        """获取充电电流

        Returns:
            float: 返回充电电流数值
        """
        if cls.update():
            return cls.data.charge_current

    @classmethod
    def get_charge_voltage(cls) -> float:
        """获取充电电压

        Returns:
            float: 返回充电电压数值
        """
        if cls.update():
            return cls.data.charge_voltage

    @classmethod
    def get_is_charging(cls) -> bool:
        """获取是否正在充电状态

        Returns:
            bool: True表示正在充电，False表示未充电
        """
        if cls.update():
            return cls.data.is_charging

    @classmethod
    def get_temperature(cls) -> float:
        """获取电池温度

        Returns:
            float: 返回电池温度数值
        """
        if cls.update():
            return cls.data.temperature

    @classmethod
    def get_cycle(cls) -> int:
        """获取电池循环次数

        Returns:
            int: 返回电池循环次数数值
        """
        if cls.update():
            return cls.data.cycle

    @classmethod
    def get_max_charge_current(cls) -> float:
        """获取最大充电电流

        Returns:
            float: 返回最大充电电流数值
        """
        if cls.update():
            return cls.data.max_charge_current

    @classmethod
    def get_max_charge_voltage(cls) -> float:
        """获取最大充电电压

        Returns:
            float: 返回最大充电电压数值
        """
        if cls.update():
            return cls.data.max_charge_voltage

    @classmethod
    def get_extra(cls) -> str:
        """获取额外信息

        Returns:
            str: 返回额外信息字符串
        """
        if cls.update():
            return cls.data.extra

    @classmethod
    def get_is_manually_connected(cls) -> bool:
        """获取是否手动连接状态

        Returns:
            bool: True表示手动连接，False表示非手动连接
        """
        if cls.update():
            return cls.data.is_manually_connected

    @classmethod
    def get_user_data(cls) -> bytes:
        """获取用户数据

        Returns:
            bytes: 返回用户数据字节流
        """
        if cls.update():
            return cls.data.user_data

    @classmethod
    @call_service(func_name="getBatteryMaxPercentage")
    def getAlarmPercentage(cls) -> int:
        """获取配置项中电池告警、电池错误和关掉电池的百分比的最大值

        Returns:
            int:
        """
        pass

    @classmethod
    @call_service(func_name="publishBattery")
    def publish(cls, battery_info: str) -> int:
        """发布电池信息

        Args:
            battery_info (str): json字符串, message_battery_pb2.Message_Battery类型转化的json字符串

        Returns:
            int: -1: 发布失败; 0: 发布成功
        """
        pass

    @classmethod
    @call_service(func_name="getBatteryCanPort")
    def getCanPort(cls) -> int:
        """获取CAN端口

        Returns:
            int: CAN端口
        """
        pass
