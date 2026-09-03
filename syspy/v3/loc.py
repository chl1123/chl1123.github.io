from __future__ import annotations
import math
import json
from typing import Optional, Dict, List, TYPE_CHECKING

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

    @classmethod
    def relocService(cls, center_x: float, center_y: float, length: float,
                     initial_angle: float, angle_scatter: float) -> str:
        params = {
            "center_x": center_x,
            "center_y": center_y,
            "length": length,
            "initial_angle": initial_angle,
            "angle_scatter": angle_scatter,
        }
        return cls.client().call_service("MCLoc", "RelocServiceScript", json.dumps(params))

    @classmethod
    def relocServiceFromPose(cls, home_list: List[str]) -> str:
        params = {"home_list": home_list}
        return cls.client().call_service("MCLoc", "RelocServiceFromPoseScript", json.dumps(params))

    @classmethod
    def autoRelocService(cls, use_pos: bool, x: float, y: float) -> str:
        params = {"use_pos": use_pos, "x": x, "y": y}
        return cls.client().call_service("MCLoc", "AutoRelocServiceScript", json.dumps(params))

    @classmethod
    def cancelReloc(cls):
        return cls.client().call_service("MCLoc", "CancelRelocScript")
