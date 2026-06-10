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

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def set2DLaserWidth(cls, key: str, width: float):
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def clear2DLaserWidth(cls, keys: List[str]):
        pass

    @classmethod
    def set2DLaserAngle(cls, key: str, min_angle: float, max_angle: float):
        cls.client().call_service("SensorFuser", "set2DLaserAngle",
                                  key, math.radians(min_angle), math.radians(max_angle))

    @classmethod
    @call_service(plugin_name="SensorFuser")
    def clear2DLaserAngle(cls, keys: List[str]):
        pass

    #----------------------------------------------------#

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def getNearestLaserPoint(cls, key: str) -> List[float]:
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")
    def safeLaserMuteStatus(cls, key: str) -> int:
        pass

    @classmethod
    @call_service(plugin_name="MoveFactory")
    def setSafeLaserMute(cls, key: str, enable: bool):
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
