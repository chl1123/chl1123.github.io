from __future__ import annotations
import math
from typing import Optional, Dict, TYPE_CHECKING

from syspy.loc import LocInterface
if TYPE_CHECKING:
    from .protobuf.message.message_localization_pb2 import msgLocalization

class LocV3(LocInterface):
    """定位类"""

    data: msgLocalization = None

    _TOPIC = "rbk.protocol.msgLocalization"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_localization_pb2 import msgLocalization  # 延迟导入
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

    def getConfidence(self) -> Optional[float]:
        if self.update():
            return self.data.confidence

    def getLocState(self) -> Optional[int]:
        if self.update():
            return self.data.locState

    def getLocMethod(self) -> Optional[int]:
        if self.update():
            return self.data.locMethod