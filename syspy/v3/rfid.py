from typing import List, Optional, TYPE_CHECKING
from syspy.rfid import RfidInterface


class RfidV3(RfidInterface):
    """RFID类"""

    _TOPIC = "rbk.protocol.msgRFID"
    _PLUGIN = "RFIDSensor"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgRFID, msgRFIDNode
        data: msgRFID = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgRFID
            cls._MODEL_CLASS = msgRFID

    def getRfids(self) -> Optional[List["msgRFIDNode"]]:
        if self.update():
            return self.data.rfidNodes
