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
        if self.update(topic):
            return self._topic_data[topic].percetage

    def getChargeCurrent(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update(topic):
            return self._topic_data[topic].charge_current

    def getChargeVoltage(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update(topic):
            return self._topic_data[topic].charge_voltage

    def getIsCharging(self, *, topic: str = "Battery-000") -> Optional[bool]:
        if self.update(topic):
            return self._topic_data[topic].is_charging

    def getTemperature(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update(topic):
            return self._topic_data[topic].temperature

    def getCycle(self, *, topic: str = "Battery-000") -> Optional[int]:
        if self.update(topic):
            return self._topic_data[topic].cycle

    def getMaxChargeCurrent(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update(topic):
            return self._topic_data[topic].max_charge_current

    def getMaxChargeVoltage(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update(topic):
            return self._topic_data[topic].max_charge_voltage

    def getExtra(self, *, topic: str = "Battery-000") -> Optional[str]:
        if self.update(topic):
            return self._topic_data[topic].extra

    def getIsManuallyConnected(self, *, topic: str = "Battery-000") -> bool:
        raise RBKVersionError()

    def getUserData(self, *, topic: str = "Battery-000") -> Optional[bytes]:
        if self.update(topic):
            return self._topic_data[topic].user_data

    def getSoh(self, *, topic: str = "Battery-000") -> int:
        raise RBKVersionError()

    def publish(self, battery_msg: "MessageV4_Battery", *, topic: str = "Battery-000"):
        if not self.is_publish:
            datapool.publish("/BatteryInfo/" + topic, MessageV4_Battery)
            self.is_publish = True
        datapool.put("/BatteryInfo/" + topic, battery_msg)

    def getCanPort(self, *, topic: str = "Battery-000") -> str:
        # todo RBK4
        return self.client().call_service("DSPChassis", "getBatteryCanPort", topic=topic)
