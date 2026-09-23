from __future__ import annotations

import math
from typing import List, Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.core.rbk_rpc import call_service, Message

if TYPE_CHECKING:
    from .protobuf.message.message_laser_pb2 import msgAllLasers, msgAllLasers3D, msgLaser3D


class LaserV3(Message):
    """激光类"""

    data: msgAllLasers = None

    _TOPIC = "rbk.protocol.msgAllLasers"
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


class Laser3DV3(Message):
    """激光类"""

    data: msgAllLasers3D = None

    _TOPIC = "rbk.protocol.msgAllLasers3D"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_laser_pb2 import msgAllLasers3D
            cls._MODEL_CLASS = msgAllLasers3D

    def getLasers3d(self) -> Optional[RepeatedCompositeFieldContainer["msgLaser3D"]]:
        if self.update():
            return self.data.lasers3D
