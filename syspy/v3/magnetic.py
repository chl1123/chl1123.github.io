from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.magnetic import MagneticInterface
from syspy.registry.channel import device
from .protobuf.compat import IS_RBK35, channel_or_topic

if TYPE_CHECKING:
    from .protobuf.message.message_magnetic_pb2 import msgMagnetic, msgMagneticNode


@channel_or_topic(topic="rbk.protocol.msgMagnetic",
                  channel=device.TOPIC_PREFIX_MAGNETIC)
class MagneticV3(MagneticInterface):
    """磁传感器类

    3.6 改读 channel ``/Magnetic/<key>``（按设备拆分），
    3.5 读单个聚合 topic ``rbk.protocol.msgMagnetic``。
    """

    data: msgMagnetic = None

    _PLUGIN = "MagneticSensor"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_magnetic_pb2 import msgMagnetic
            cls._MODEL_CLASS = msgMagnetic

    def _read_devices(self) -> "msgMagnetic":
        from syspy import RobotParam
        from .protobuf.message.message_magnetic_pb2 import msgMagnetic, msgMagneticNode
        merged = msgMagnetic()
        for key in RobotParam.getDeviceList("MagneticSensor") or []:
            channel = device.TOPIC_PREFIX_MAGNETIC + key
            if self.update_channel(channel, msgMagneticNode):
                node = self._topic_data.get(channel)
                if node is not None:
                    merged.magneticNodes.append(node)
            elif self.update_channel(channel, msgMagnetic):
                data = self._topic_data.get(channel)
                if data is not None:
                    merged.MergeFrom(data)
        return merged

    def getMagnetics(self, device_key: str = None):
        """不传 device_key：合并全部设备（3.6）/ 读聚合 topic（3.5）；传入则只读该设备。"""
        if IS_RBK35:
            if not self.update():
                return None
            return self.data.magneticNodes
        if device_key is None:
            merged = self._read_devices()
            if not merged.ListFields():
                return None
            self.data = merged
            return merged.magneticNodes
        if not device_key or "/" in device_key:
            raise ValueError("device_key must be a device key, not a channel path")
        data = self.get_channel_data(device.TOPIC_PREFIX_MAGNETIC + device_key, self._MODEL_CLASS)
        return data or None
