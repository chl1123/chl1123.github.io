from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.magnetic import MagneticInterface

if TYPE_CHECKING:
    from .protobuf.message.message_magnetic_pb2 import msgMagnetic, msgMagneticNode


class MagneticV3(MagneticInterface):
    """磁传感器类"""

    data: msgMagnetic = None

    _TOPIC = "rbk.protocol.msgMagnetic"
    _PLUGIN = "MagneticSensor"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_magnetic_pb2 import msgMagnetic
            cls._MODEL_CLASS = msgMagnetic

    def getMagnetics(self) -> Optional[RepeatedCompositeFieldContainer["msgMagneticNode"]]:
        if self.update():
            return self.data.magneticNodes
