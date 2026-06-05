import math
from typing import Optional, Dict, TYPE_CHECKING
from syspy.loc import LocInterface

class LocV3(LocInterface):
    """定位类"""

    _TOPIC = "rbk.protocol.msgLocalization"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgLocalization
        data: msgLocalization = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgLocalization  # 延迟导入
            cls._MODEL_CLASS = msgLocalization

    def getPose(self) -> Optional[Dict[str, float]]:
        if self.update():
            return {
                "x": self.data.x,
                "y": self.data.y,
                "z": self.data.z,
                "yaw": math.degrees(self.data.angle),
                "roll": math.degrees(self.data.roll),
                "pitch": math.degrees(self.data.pitch),
            }

    def getConfidence(self) -> float:
        if self.update():
            return self.data.confidence

    def getLocState(self) -> int:
        if self.update():
            return self.data.locState

    def getLocMethod(self) -> Optional[int]:
        if self.update():
            return self.data.locMethod