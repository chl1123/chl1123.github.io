from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.rfid import RfidInterface

if TYPE_CHECKING:
    from .protobuf.message.message_rfid_pb2 import msgRFID, msgRFIDNode


class RfidV3(RfidInterface):
    """RFID类"""

    data: msgRFID = None

    _TOPIC = "rbk.protocol.msgRFID"
    _PLUGIN = "RFIDSensor"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_rfid_pb2 import msgRFID
            cls._MODEL_CLASS = msgRFID

    def getRfids(self) -> Optional[RepeatedCompositeFieldContainer["msgRFIDNode"]]:
        if self.update():
            return self.data.rfidNodes
