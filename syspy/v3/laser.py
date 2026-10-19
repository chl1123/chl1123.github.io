from __future__ import annotations

import math
from typing import List, Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.core.rbk_rpc import call_service, Message
from syspy.registry.channel import device
from .protobuf.compat import IS_RBK35, channel_or_topic

if TYPE_CHECKING:
    from .protobuf.message.message_laser_pb2 import msgAllLasers, msgLaser
    from .protobuf.compat import Laser3d as msgLaser3d


@channel_or_topic(topic="rbk.protocol.msgAllLasers",
                  channel=device.TOPIC_PREFIX_LASER_2D)
class LaserV3(Message):
    """激光类

    3.5：单个聚合 topic ``rbk.protocol.msgAllLasers``，一次拿到全部激光；
    3.6：按设备拆 channel ``/Laser2D/<key>``，需要枚举设备后逐路读取。
    """

    data: msgAllLasers = None

    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_laser_pb2 import msgAllLasers
            cls._MODEL_CLASS = msgAllLasers

    @call_service(plugin_name="SensorFuser")
    def set2DLaserWidth(self, key: str, width: float):
        pass

    @call_service(plugin_name="SensorFuser")
    def clear2DLaserWidth(self, keys: List[str]):
        pass

    def set2DLaserAngle(self, key: str, min_angle: float, max_angle: float):
        self.client().call_service("SensorFuser", "set2DLaserAngle",
                                   key, math.radians(min_angle), math.radians(max_angle))

    @call_service(plugin_name="SensorFuser")
    def clear2DLaserAngle(self, keys: List[str]):
        pass

    @call_service(plugin_name="MoveFactory")
    def getNearestLaserPoint(self, key: str) -> List[float]:
        pass

    @call_service(plugin_name="DSPChassis")
    def safeLaserMuteStatus(self, key: str) -> int:
        pass

    @call_service(plugin_name="MoveFactory")
    def setSafeLaserMute(self, key: str, enable: bool):
        pass

    def getData(self, fields: Optional[List[str]] = None, *, channel: str = None,
                device_key: str = None) -> dict:
        """读取激光数据。

        - 不传参数：3.5 读聚合 topic，3.6 按模型枚举设备逐路聚合；
        - ``channel``（仅 3.6）：直接读指定 channel；
        - ``device_key``（仅 3.6）：只读该设备，与 ``channel`` 互斥。
        """
        if IS_RBK35:
            # 3.5 只有聚合 topic，没有按设备的 channel
            if not self.update():
                return {}
            lasers = list(self.data.laser)
            data = {"laser": [self._message_to_dict(laser) for laser in lasers]}
            if fields:
                return {field: data[field] for field in fields if field in data}
            return data

        if device_key is None:
            if channel is not None:
                return self.get_channel_data(channel, self._MODEL_CLASS, fields)
            from syspy import RobotParam
            from .protobuf.message.message_laser_pb2 import msgLaser
            lasers = []
            reader = type(self)()
            for key in RobotParam.getDeviceList("Laser") or []:
                laser_channel = device.TOPIC_PREFIX_LASER_2D + key
                if reader.update_channel(laser_channel, msgLaser):
                    lasers.append(reader._topic_data[laser_channel])
            if lasers:
                data = {"laser": [reader._message_to_dict(laser) for laser in lasers]}
                if fields:
                    return {field: data[field] for field in fields if field in data}
                return data
            return {}
        if channel is not None:
            raise ValueError("channel and device_key cannot be used together")
        if not device_key or "/" in device_key:
            raise ValueError("device_key must be a device key, not a channel path")

        from .protobuf.message.message_laser_pb2 import msgLaser
        device_channel = device.TOPIC_PREFIX_LASER_2D + device_key
        return self.get_channel_data(device_channel, msgLaser, fields)


class Laser3DV3(Message):
    """激光类"""

    data: msgLaser3d = None
    _CHANNEL = device.TOPIC_PREFIX_LASER_3D
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.compat import Laser3d
            cls._MODEL_CLASS = Laser3d

    def getLasers3d(self, device_key: str = None):
        # 3D 激光消息在 3.5/3.6 里叫法不同（msgLaser3D / msgLaser3d），
        # 统一从 compat 取，实现层不需要感知版本。
        from .protobuf.compat import Laser3d
        if device_key is None:
            from syspy import RobotParam
            lasers = []
            reader = Laser3DV3()
            for key in RobotParam.getDeviceList("Laser") or []:
                channel = device.TOPIC_PREFIX_LASER_3D + key
                if reader.update_channel(channel, Laser3d):
                    lasers.append(reader._topic_data[channel])
            return lasers
        if not device_key or "/" in device_key:
            raise ValueError("device_key must be a device key, not a channel path")
        return self.get_channel_data(device.TOPIC_PREFIX_LASER_3D + device_key, Laser3d)
