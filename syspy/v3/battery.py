from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from google.protobuf.json_format import MessageToJson
from syspy.config import RBK_FULL_VERSION
from syspy.core.rbk_rpc import default_plugin, Message
from syspy.registry.channel import device
if TYPE_CHECKING:
    from .protobuf.message.message_battery_pb2 import msgBattery, msgBatteryInfos

DEFAULT_BATTERY_KEY = "Battery-000"


def _is_rbk35() -> bool:
    """是否运行在 RBK 3.5 上（3.5 无 channel，且没有 msgBatteryInfos）。"""
    parts = (RBK_FULL_VERSION or "").split(".")
    try:
        return int(parts[0]) == 3 and int(parts[1]) <= 5
    except (IndexError, ValueError):
        return False


IS_RBK35 = _is_rbk35()

#: RBK 3.5 的电池 topic。3.5.4 起与 3.6 共用同一份 ``msgBatteryInfos``
#: （多电池），只是传输方式不同：3.5 走 topic，3.6 走 channel。
TOPIC_BATTERY_INFOS = "rbk.protocol.msgBatteryInfos"


@default_plugin("DSPChassis")
class BatteryV3(Message):
    """RBK3 电池实现（3.5 / 3.6 共用 ``msgBatteryInfos``）。

    payload 为 ``msgBatteryInfos``：

    - ``batteryInfo``: repeated msgBattery，每块电池一条（带 ``key``）；
    - ``batteryCal`` : 汇总值，供业务逻辑使用；
    - ``batteryNums``: 当前模型启用的电池数量。

    两版差异只在传输方式：

    - **RBK 3.5**：topic ``rbk.protocol.msgBatteryInfos``；
    - **RBK 3.6**：channel ``/BatteryInfos``。

    读取时按 ``device_key`` 在 ``batteryInfo`` 里匹配 ``key``；为兼容未填
    ``key`` 的早期固件，只有单块电池时允许直接用它。
    """

    data: msgBatteryInfos = None

    _CHANNEL = "" if IS_RBK35 else device.TOPIC_BATTERY  # '/BatteryInfos'（不是 /BatteryInfo/）
    _TOPIC = TOPIC_BATTERY_INFOS if IS_RBK35 else ""
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_battery_pb2 import msgBatteryInfos
            cls._MODEL_CLASS = msgBatteryInfos

    def _get_battery_infos(self) -> Optional["msgBatteryInfos"]:
        """读电池汇总消息（3.5 topic / 3.6 channel），读不到返回 None。"""
        if IS_RBK35:
            if self.update():
                return self.data
            return None
        if self.update_channel(self._CHANNEL):
            return self._topic_data.get(self._CHANNEL)
        return None

    def _get_battery_msg(self, device_key: str) -> Optional["msgBattery"]:
        """在 ``batteryInfo`` 里按 key 选电池；读不到或找不到该电池都返回 None。

        部分早期固件不填 ``key``，此时若只有一块电池，则对默认电池 key
        直接采用（多电池场景一律要求 key 匹配，避免把别的电池值当成目标电池）。
        """
        infos = self._get_battery_infos()
        if infos is None:
            return None

        entries = list(infos.batteryInfo)
        for entry in entries:
            if entry.key == device_key:
                return entry

        unkeyed = [e for e in entries if not e.key]
        if len(entries) == 1 and len(unkeyed) == 1 and device_key == DEFAULT_BATTERY_KEY:
            return unkeyed[0]
        return None

    def getPercentage(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[float]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.percentage

    def getChargeCurrent(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[float]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.chargeCurrent

    def getChargeVoltage(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[float]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.chargeVoltage

    def getIsCharging(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[bool]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.isCharging

    def getTemperature(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[float]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.temperature

    def getCycle(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[int]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.cycle

    def getMaxChargeCurrent(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[float]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.maxChargeCurrent

    def getMaxChargeVoltage(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[float]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.maxChargeVoltage

    def getExtra(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[str]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.extra

    def getIsManuallyConnected(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[bool]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.isManuallyConnected

    def getUserData(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[bytes]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.userData

    def getSoh(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[int]:
        battery_msg = self._get_battery_msg(device_key)
        if battery_msg is not None:
            return battery_msg.SOH

    def publish(self, battery_info: "msgBattery", *, device_key: str = DEFAULT_BATTERY_KEY) -> int:
        return self.client().call_service("DSPChassis", "publishBattery", MessageToJson(battery_info))

    def getCanPort(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> str:
        return self.client().call_service("DSPChassis", "getBatteryCanPort")

    def getBaudrate(self, *, device_key: str = DEFAULT_BATTERY_KEY) -> Optional[int]:
        return self.client().call_service("DSPChassis", "getBatteryBaudrate")
