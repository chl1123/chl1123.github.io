from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from syspy.distance import DistanceInterface
from syspy.registry.channel import device
from .protobuf.compat import IS_RBK35, channel_or_topic

if TYPE_CHECKING:
    from .protobuf.message.message_distancesensor_pb2 import msgDistanceNode, msgDistanceSensor


@channel_or_topic(topic="rbk.protocol.msgDistanceSensor",
                  channel=device.TOPIC_PREFIX_DISTANCE_SENSOR)
class DistanceV3(DistanceInterface):
    """距离传感器类

    3.6 改读 channel ``/DistanceSensor/<key>``（按设备拆分），
    3.5 读单个聚合 topic ``rbk.protocol.msgDistanceSensor``。
    """

    data: msgDistanceSensor = None

    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_distancesensor_pb2 import msgDistanceSensor
            cls._MODEL_CLASS = msgDistanceSensor

    def _read_devices(self) -> "msgDistanceSensor":
        from syspy import RobotParam
        from .protobuf.message.message_distancesensor_pb2 import (
            msgDistanceNode, msgDistanceSensor,
        )
        merged = msgDistanceSensor()
        for key in RobotParam.getDeviceList("DistanceSensor") or []:
            channel = device.TOPIC_PREFIX_DISTANCE_SENSOR + key
            if self.update_channel(channel, msgDistanceNode):
                node = self._topic_data.get(channel)
                if node is not None:
                    merged.node.append(node)
            elif self.update_channel(channel, msgDistanceSensor):
                data = self._topic_data.get(channel)
                if data is not None:
                    merged.MergeFrom(data)
        return merged

    def getDistances(self, device_key: str = None) -> Optional[List["msgDistanceNode"]]:
        """距离传感器节点列表。

        - 不传 ``device_key``：合并全部设备，无数据返回 None；
        - 传 ``device_key``：只读该设备，未配置则返回 None。
        """
        if IS_RBK35:
            if not self.update():
                return None
            return list(self.data.node)
        if device_key is None:
            merged = self._read_devices()
            if not merged.ListFields():
                return None
            self.data = merged
            return list(merged.node)
        if not device_key or "/" in device_key:
            raise ValueError("device_key must be a device key, not a channel path")
        data = self.get_channel_data(
            device.TOPIC_PREFIX_DISTANCE_SENSOR + device_key, self._MODEL_CLASS
        )
        if not data:
            return None
        return list(data.get("node", []))

    def getData(self, fields=None, *, device_key: str = None) -> list:
        """兼容式读取：返回距离节点列表（无数据时为空列表）。"""
        return self.getDistances(device_key=device_key) or []
