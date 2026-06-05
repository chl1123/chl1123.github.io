from typing import Optional, TYPE_CHECKING
from google.protobuf.json_format import MessageToJson
from syspy.core.rbk_rpc import default_plugin, Message


@default_plugin("DSPChassis")
class BatteryV3(Message):
    """RBK3电池实现"""
    _TOPIC = "rbk.protocol.msgBattery"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgBattery
        data: msgBattery = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgBattery
            cls._MODEL_CLASS = msgBattery

    def getPercentage(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update():
            return self.data.percentage

    def getChargeCurrent(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update():
            return self.data.chargeCurrent

    def getChargeVoltage(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update():
            return self.data.chargeVoltage

    def getIsCharging(self, *, topic: str = "Battery-000") -> Optional[bool]:
        if self.update():
            return self.data.isCharging

    def getTemperature(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update():
            return self.data.temperature

    def getCycle(self, *, topic: str = "Battery-000") -> Optional[int]:
        if self.update():
            return self.data.cycle

    def getMaxChargeCurrent(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update():
            return self.data.maxChargeCurrent

    def getMaxChargeVoltage(self, *, topic: str = "Battery-000") -> Optional[float]:
        if self.update():
            return self.data.maxChargeVoltage

    def getExtra(self, *, topic: str = "Battery-000") -> Optional[str]:
        if self.update():
            return self.data.extra

    def getIsManuallyConnected(self, *, topic: str = "Battery-000") -> Optional[bool]:
        if self.update():
            return self.data.isManuallyConnected

    def getUserData(self, *, topic: str = "Battery-000") -> Optional[bytes]:
        if self.update():
            return self.data.userData

    def getSoh(self, *, topic: str = "Battery-000") -> Optional[int]:
        if self.update():
            return self.data.SOH

    def publish(self, battery_msg: "msgBattery", *, topic: str = "Battery-000") -> int:
        return self.client().call_service("DSPChassis", "publishBattery", MessageToJson(battery_msg))

    def getCanPort(self, *, topic: str = "Battery-000") -> str:
        return self.client().call_service("DSPChassis", "getBatteryCanPort")