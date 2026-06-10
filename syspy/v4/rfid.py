from typing import Optional

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.rfid import RfidInterface


class RfidV4(RfidInterface):
    """RFID类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_rfid_pb2 import MessageV4_RFID
            cls._MODEL_CLASS = MessageV4_RFID

    def getRfids(self) -> Optional[RepeatedCompositeFieldContainer["MessageV4_RFIDNode"]]:
        if self.update():
            return self.data.rfid_nodes
