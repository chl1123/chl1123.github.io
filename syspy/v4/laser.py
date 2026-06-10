import math
from typing import List, Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.core.rbk_rpc import call_service, Message

if TYPE_CHECKING:
    from syspy.v4.protobuf.message.messageV4_laser_pb2 import MessageV4_Laser, MessageV4_Laser3D


class LaserV4(Message):
    """激光类"""

    _MODEL_CLASS = None

    def __init__(self, topic=None):
        self._TOPIC = topic

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            cls._MODEL_CLASS = MessageV4_Laser

    @classmethod
    @call_service(plugin_name="SensorFuser")  # todo RBK4 App名
    def set2DLaserWidth(cls, device_name: str, width: float):
        pass

    @classmethod
    @call_service(plugin_name="SensorFuser")  # todo RBK4 App名
    def clear2DLaserWidth(cls, device_list: List[str]):
        pass

    @classmethod
    def set2DLaserAngle(cls, device_name: str, min_angle: float, max_angle: float):
        # todo RBK4 App名
        cls.client().call_service("SensorFuser", "set2DLaserAngle",
                                  device_name=device_name, min_angle=math.radians(min_angle), max_angle=math.radians(max_angle))

    @classmethod
    @call_service(plugin_name="SensorFuser")  # todo RBK4 App名
    def clear2DLaserAngle(cls, device_list: List[str]):
        pass

    #----------------------------------------------------#

    @classmethod
    @call_service(plugin_name="MoveFactory")  # todo RBK4 App名
    def getNearestLaserPoint(cls, laser_key: str) -> List[float]:
        pass

    @classmethod
    @call_service(plugin_name="DSPChassis")  # todo RBK4 App名
    def safeLaserMuteStatus(cls, laser_key: str) -> int:
        pass

    @classmethod
    @call_service(plugin_name="MoveFactory")  # todo RBK4 App名
    def setSafeLaserMute(cls, laser_key: str, enable: bool):
        pass


class Laser3DV4(Message):
    """激光类"""

    _MODEL_CLASS = None
    def __init__(self, topic=None):
        self._TOPIC = topic

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            cls._MODEL_CLASS = MessageV4_Laser3D

    def getLasers3d(self) -> Optional[RepeatedCompositeFieldContainer["MessageV4_Laser3D"]]:
        if self.update():
            return self.data.lasers3d