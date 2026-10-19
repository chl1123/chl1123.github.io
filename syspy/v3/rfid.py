from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.rfid import RfidInterface
from syspy.registry.channel import device
from .protobuf.compat import IS_RBK35, channel_or_topic

if TYPE_CHECKING:
    from .protobuf.message.message_rfid_pb2 import msgRFID, msgRFIDNode


@channel_or_topic(topic="rbk.protocol.msgRFID", channel=device.TOPIC_PREFIX_RFID)
class RfidV3(RfidInterface):
    """RFID 类

    3.6 改读 channel ``/RFID/<key>``（按设备拆分），
    3.5 读单个聚合 topic ``rbk.protocol.msgRFID``。
    """

    data: msgRFID = None

    _PLUGIN = "RFIDSensor"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_rfid_pb2 import msgRFID
            cls._MODEL_CLASS = msgRFID

    def _read_devices(self) -> "msgRFID":
        from syspy import RobotParam
        from .protobuf.message.message_rfid_pb2 import msgRFID, msgRFIDNode
        merged = msgRFID()
        for key in RobotParam.getDeviceList("RFIDSensor") or []:
            channel = device.TOPIC_PREFIX_RFID + key
            if self.update_channel(channel, msgRFIDNode):
                node = self._topic_data.get(channel)
                if node is not None:
                    merged.rfidNodes.append(node)
            elif self.update_channel(channel, msgRFID):
                data = self._topic_data.get(channel)
                if data is not None:
                    merged.MergeFrom(data)
        return merged

    def getRfids(self, device_key: str = None):
        """不传 device_key：合并全部设备（3.6）/ 读聚合 topic（3.5）；传入则只读该设备。"""
        if IS_RBK35:
            if not self.update():
                return None
            return self.data.rfidNodes
        if device_key is None:
            merged = self._read_devices()
            if not merged.ListFields():
                return None
            self.data = merged
            return merged.rfidNodes
        if not device_key or "/" in device_key:
            raise ValueError("device_key must be a device key, not a channel path")
        data = self.get_channel_data(device.TOPIC_PREFIX_RFID + device_key, self._MODEL_CLASS)
        return data or None
