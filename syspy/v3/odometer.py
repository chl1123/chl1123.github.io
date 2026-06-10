from __future__ import annotations
import math
from typing import Optional, Tuple, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.odometer import OdometerInterface
if TYPE_CHECKING:
    from .protobuf.message.message_odometer_pb2 import msgOdometer
    from .protobuf.message.message_motorinfos_pb2 import msgMotorInfo

class OdometerV3(OdometerInterface):
    """里程类"""

    data: msgOdometer = None

    _TOPIC = "rbk.protocol.msgOdometer"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_odometer_pb2 import msgOdometer
            cls._MODEL_CLASS = msgOdometer

    def getCycle(self) -> Optional[int]:
        if self.update():
            return self.data.cycle

    def getPosition(self) -> Optional[Tuple[float, float, float]]:
        if self.update():
            return self.data.x, self.data.y, math.degrees(self.data.angle)

    def getSpeeds(self) -> Optional[Tuple[float, float, float]]:
        if self.update():
            return self.data.velX, self.data.velY, self.data.velRotate

    def getIsStop(self) -> Optional[bool]:
        if self.update():
            return self.data.isStop

    def getMotorInfos(self) -> Optional[RepeatedCompositeFieldContainer["msgMotorInfo"]]:
        if self.update():
            return self.data.motorInfo