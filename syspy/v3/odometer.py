import math
from typing import List, Optional, Tuple, TYPE_CHECKING
from syspy.odometer import OdometerInterface


class OdometerV3(OdometerInterface):
    """里程类"""

    _TOPIC = "rbk.protocol.msgOdometer"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgOdometer, msgMotorInfo
        data: msgOdometer = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgOdometer
            cls._MODEL_CLASS = msgOdometer

    def getCycle(self) -> int:
        if self.update():
            return self.data.cycle

    def getPosition(self) -> Tuple[float, float, float]:
        if self.update():
            return self.data.x, self.data.y, math.degrees(self.data.angle)

    def getSpeeds(self) -> Tuple[float, float, float]:
        if self.update():
            return self.data.velX, self.data.velY, self.data.velRotate

    def getIsStop(self) -> Optional[bool]:
        if self.update():
            return self.data.isStop

    def getMotorInfos(self) -> Optional[List["msgMotorInfo"]]:
        if self.update():
            return self.data.motorInfo