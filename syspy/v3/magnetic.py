from typing import Optional, List, TYPE_CHECKING
from syspy.magnetic import MagneticInterface


class MagneticV3(MagneticInterface):
    """磁传感器类"""

    _TOPIC = "rbk.protocol.msgMagnetic"
    _PLUGIN = "MagneticSensor"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgMagnetic, msgMagneticNode
        data: msgMagnetic = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgMagnetic
            cls._MODEL_CLASS = msgMagnetic

    def getMagnetics(self) -> Optional[List["msgMagneticNode"]]:
        if self.update():
            return self.data.magneticNodes