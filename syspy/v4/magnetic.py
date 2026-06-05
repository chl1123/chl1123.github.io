from typing import Optional, List
from syspy.magnetic import MagneticInterface


class MagneticV4(MagneticInterface):
    """磁传感器类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_magnetic_pb2 import MessageV4_Magnetic
            cls._MODEL_CLASS = MessageV4_Magnetic

    def getMagnetics(self) -> Optional[List["MessageV4_MagneticNode"]]:
        if self.update():
            return self.data.magnetic_nodes