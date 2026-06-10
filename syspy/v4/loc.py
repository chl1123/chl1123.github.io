import math
from typing import Optional, Dict
from syspy.loc import LocInterface

class LocV4(LocInterface):
    """定位类"""

    _TOPIC = "Localization/Info"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.message_localization_pb2 import Message_Localization  # 延迟导入
            cls._MODEL_CLASS = Message_Localization

    def get_pose(self) -> Optional[Dict[str, float]]:
        if self.update():
            return {
                "x": self.data.x,
                "y": self.data.y,
                "z": self.data.z,
                "yaw": math.degrees(self.data.angle),
                "roll": math.degrees(self.data.roll),
                "pitch": math.degrees(self.data.pitch),
            }

    def get_confidence(self) -> Optional[float]:
        if self.update():
            return self.data.confidence

    def get_loc_state(self) -> Optional[int]:
        if self.update():
            return self.data.loc_state

    def get_loc_method(self) -> Optional[int]:
        if self.update():
            return self.data.loc_method
