from typing import Optional

from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy.v4.lib.rbk import datapool
from syspy.v4.protobuf.message.messageV4_battery_pb2 import MessageV4_Battery


class BatteryV4(Message):
    """版本4电池实现"""

    def __init__(self):
        super().__init__("/BatteryInfo/", "")
        self.is_publish = False

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            cls._MODEL_CLASS = MessageV4_Battery

    def getPercentage(self, *, topic: str = "Battery-000") -> Optional[float]:
        """获取电池电量百分比

        Returns:
            (Optional[float]): 返回电池电量百分比数值
        """
        if self.update(topic):
            return self._topic_data[topic].percetage

    def getChargeCurrent(self, *, topic: str = "Battery-000") -> Optional[float]:
        """获取充电电流

        Returns:
            (Optional[float]): 返回充电电流数值
        """
        if self.update(topic):
            return self._topic_data[topic].charge_current

    def getChargeVoltage(self, *, topic: str = "Battery-000") -> Optional[float]:
        """获取充电电压

        Returns:
            (float): 返回充电电压数值
        """
        if self.update(topic):
            return self._topic_data[topic].charge_voltage

    def getIsCharging(self, *, topic: str = "Battery-000") -> Optional[bool]:
        """获取是否正在充电状态

        Returns:
            (Optional[bool]): True表示正在充电，False表示未充电
        """
        if self.update(topic):
            return self._topic_data[topic].is_charging

    def getTemperature(self, *, topic: str = "Battery-000") -> Optional[float]:
        """获取电池温度

        Returns:
            (Optional[float]): 返回电池温度数值
        """
        if self.update(topic):
            return self._topic_data[topic].temperature

    def getCycle(self, *, topic: str = "Battery-000") -> Optional[int]:
        """获取电池循环次数

        Returns:
            (Optional[int]): 返回电池循环次数数值
        """
        if self.update(topic):
            return self._topic_data[topic].cycle

    def getMaxChargeCurrent(self, *, topic: str = "Battery-000") -> Optional[float]:
        """获取最大充电电流

        Returns:
            (float): 返回最大充电电流数值
        """
        if self.update(topic):
            return self._topic_data[topic].max_charge_current

    def getMaxChargeVoltage(self, *, topic: str = "Battery-000") -> Optional[float]:
        """获取最大充电电压

        Returns:
            (Optional[float]): 返回最大充电电压数值
        """
        if self.update(topic):
            return self._topic_data[topic].max_charge_voltage

    def getExtra(self, *, topic: str = "Battery-000") -> Optional[str]:
        """获取额外信息

        Returns:
            (Optional[str]): 返回额外信息字符串
        """
        if self.update(topic):
            return self._topic_data[topic].extra

    def getIsManuallyConnected(self, *, topic: str = "Battery-000") -> bool:
        """获取是否手动连接状态

        Returns:
            (Optional[bool]): True表示手动连接，False表示非手动连接
        """
        raise RBKVersionError()

    def getUserData(self, *, topic: str = "Battery-000") -> Optional[bytes]:
        """获取用户数据

        Returns:
            (Optional[bytes]): 返回用户数据字节流
        """
        if self.update(topic):
            return self._topic_data[topic].user_data

    def getSoh(self, *, topic: str = "Battery-000") -> int:
        """获取电池健康度

        Returns:
            (Optional[int]): 健康度。-1 表示无效。
        """
        raise RBKVersionError()

    def publish(self, battery_msg: "MessageV4_Battery", *, topic: str = "Battery-000"):
        """发布电池信息

        Args:
            battery_msg ("MessageV4_Battery"): MessageV4_Battery对象
            topic (str): 电池消息channel后缀，同电池key
        """
        if not self.is_publish:
            datapool.publish("/BatteryInfo/" + topic, MessageV4_Battery)
            self.is_publish = True
        datapool.put("/BatteryInfo/" + topic, battery_msg)

    def getCanPort(self, *, topic: str = "Battery-000") -> str:
        """获取CAN端口

        Returns:
            (int): CAN端口
        """
        # todo RBK4
        return self.client().call_service("DSPChassis", "getBatteryCanPort", topic=topic)
