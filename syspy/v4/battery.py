from syspy.core.rbk_rpc import call_service, Message
from syspy.core.rbk_rpc import RBKVersionError

class BatteryV4(Message):
    """版本4电池实现"""

    def __init__(self, topic=None):
        self._TOPIC = topic

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.include.protocol.messageV4_battery_pb2 import MessageV4_Battery
            cls._MODEL_CLASS = MessageV4_Battery

    def get_percentage(self) -> float:
        """获取电池电量百分比

        Returns:
            float: 返回电池电量百分比数值
        """
        if self.update():
            return self.data.percetage

    def get_charge_current(self) -> float:
        """获取充电电流

        Returns:
            float: 返回充电电流数值
        """
        if self.update():
            return self.data.charge_current

    def get_charge_voltage(self) -> float:
        """获取充电电压

        Returns:
            float: 返回充电电压数值
        """
        if self.update():
            return self.data.charge_voltage

    def get_is_charging(self) -> bool:
        """获取是否正在充电状态

        Returns:
            bool: True表示正在充电，False表示未充电
        """
        if self.update():
            return self.data.is_charging

    def get_temperature(self) -> float:
        """获取电池温度

        Returns:
            float: 返回电池温度数值
        """
        if self.update():
            return self.data.temperature

    def get_cycle(self) -> int:
        """获取电池循环次数

        Returns:
            int: 返回电池循环次数数值
        """
        if self.update():
            return self.data.cycle

    def get_max_charge_current(self) -> float:
        """获取最大充电电流

        Returns:
            float: 返回最大充电电流数值
        """
        if self.update():
            return self.data.max_charge_current

    def get_max_charge_voltage(self) -> float:
        """获取最大充电电压

        Returns:
            float: 返回最大充电电压数值
        """
        if self.update():
            return self.data.max_charge_voltage

    def get_extra(self) -> str:
        """获取额外信息

        Returns:
            str: 返回额外信息字符串
        """
        if self.update():
            return self.data.extra

    def get_is_manually_connected(self) -> bool:
        """获取是否手动连接状态

        Returns:
            bool: True表示手动连接，False表示非手动连接
        """
        raise RBKVersionError()

    def get_user_data(self) -> bytes:
        """获取用户数据

        Returns:
            bytes: 返回用户数据字节流
        """
        if self.update():
            return self.data.user_data

    @call_service(func_name="getBatteryMaxPercentage")
    def getAlarmPercentage(self) -> int:
        """获取配置项中电池告警、电池错误和关掉电池的百分比的最大值

        Returns:
            int:
        """
        pass

    @call_service(func_name="publishBattery")
    def publish(self, battery_info: str) -> int:
        """发布电池信息

        Args:
            battery_info (str): json字符串, message_battery_pb2.Message_Battery类型转化的json字符串

        Returns:
            int: -1: 发布失败; 0: 发布成功
        """
        pass

    @call_service(func_name="getBatteryCanPort")
    def getCanPort(self) -> int:
        """获取CAN端口

        Returns:
            int: CAN端口
        """
        pass
