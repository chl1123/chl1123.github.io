import math
from typing import List, Tuple, Optional

from syspy.core.rbk_rpc import RBKVersionError
from syspy.odometer import OdometerInterface


class OdometerV4(OdometerInterface):
    """里程类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_odometer_pb2 import MessageV4_Odometer
            cls._MODEL_CLASS = MessageV4_Odometer

    def getCycle(self) -> Optional[int]:
        if self.update():
            return self.data.cycle

    def getPosition(self) -> Optional[Tuple[float, float, float]]:
        if self.update():
            return self.data.x, self.data.y, math.degrees(self.data.angle)

    def getSpeeds(self) -> Optional[Tuple[float, float, float]]:
        if self.update():
            return self.data.vel_x, self.data.vel_y, self.data.vel_rotate

    def getIsStop(self) -> Optional[bool]:
        if self.update():
            return self.data.is_stop

    def getMotorInfos(self) -> List["MessageV4_MotorInfo"]:
        raise RBKVersionError()
