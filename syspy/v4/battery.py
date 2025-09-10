from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy.v4.include.rbk import datapool
from syspy.v4.include.protocol.messageV4_battery_pb2 import MessageV4_Battery

class BatteryV4(Message):
    """版本4电池实现"""

    def __init__(self):
        super().__init__("/BatteryInfo/", "")
        self.is_publish = False

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            cls._MODEL_CLASS = MessageV4_Battery

    def get_percentage(self, *, topic: str = "Battery-000") -> float:
        """获取电池电量百分比

        Returns:
            float: 返回电池电量百分比数值
        """
        if self.update(topic):
            return self._topic_data[topic].percetage

    def get_charge_current(self, *, topic: str = "Battery-000") -> float:
        """获取充电电流

        Returns:
            float: 返回充电电流数值
        """
        if self.update(topic):
            return self._topic_data[topic].charge_current

    def get_charge_voltage(self, *, topic: str = "Battery-000") -> float:
        """获取充电电压

        Returns:
            float: 返回充电电压数值
        """
        if self.update(topic):
            return self._topic_data[topic].charge_voltage

    def get_is_charging(self, *, topic: str = "Battery-000") -> bool:
        """获取是否正在充电状态

        Returns:
            bool: True表示正在充电，False表示未充电
        """
        if self.update(topic):
            return self._topic_data[topic].is_charging

    def get_temperature(self, *, topic: str = "Battery-000") -> float:
        """获取电池温度

        Returns:
            float: 返回电池温度数值
        """
        if self.update(topic):
            return self._topic_data[topic].temperature

    def get_cycle(self, *, topic: str = "Battery-000") -> int:
        """获取电池循环次数

        Returns:
            int: 返回电池循环次数数值
        """
        if self.update(topic):
            return self._topic_data[topic].cycle

    def get_max_charge_current(self, *, topic: str = "Battery-000") -> float:
        """获取最大充电电流

        Returns:
            float: 返回最大充电电流数值
        """
        if self.update(topic):
            return self._topic_data[topic].max_charge_current

    def get_max_charge_voltage(self, *, topic: str = "Battery-000") -> float:
        """获取最大充电电压

        Returns:
            float: 返回最大充电电压数值
        """
        if self.update(topic):
            return self._topic_data[topic].max_charge_voltage

    def get_extra(self, *, topic: str = "Battery-000") -> str:
        """获取额外信息

        Returns:
            str: 返回额外信息字符串
        """
        if self.update(topic):
            return self._topic_data[topic].extra

    def get_is_manually_connected(self, *, topic: str = "Battery-000") -> bool:
        """获取是否手动连接状态

        Returns:
            bool: True表示手动连接，False表示非手动连接
        """
        raise RBKVersionError()

    def get_user_data(self, *, topic: str = "Battery-000") -> bytes:
        """获取用户数据

        Returns:
            bytes: 返回用户数据字节流
        """
        if self.update(topic):
            return self._topic_data[topic].user_data

    def getAlarmPercentage(self, *, topic: str = "Battery-000") -> int:
        """获取配置项中电池告警、电池错误和关掉电池的百分比的最大值

        Returns:
            int:
        """
        # todo RBK4
        return self.client().call_service("DSPChassis", "getBatteryMaxPercentage", topic=topic)

    def publish(self, battery_info: "MessageV4_Battery", *, topic: str = "Battery-000"):
        """发布电池信息

        Args:
            battery_info ("MessageV4_Battery"): json字符串, message_battery_pb2.Message_Battery类型转化的json字符串
            topic (str): 电池消息channel后缀，同电池key
        """
        if not self.is_publish:
            datapool.publish("/BatteryInfo/" + topic, MessageV4_Battery)
            self.is_publish = True
        datapool.put("/BatteryInfo/" + topic, battery_info)

    def getCanPort(self, *, topic: str = "Battery-000") -> int:
        """获取CAN端口

        Returns:
            int: CAN端口
        """
        # todo RBK4
        return self.client().call_service("DSPChassis", "getBatteryCanPort", topic=topic)
