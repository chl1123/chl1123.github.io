import typing
from typing import List, Optional
from syspy.rfid import RfidInterface


class RfidV3(RfidInterface):
    """RFID类"""

    _TOPIC = "rbk.protocol.msgRFID"
    _PLUGIN = "RFIDSensor"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgRFID, msgRFIDNode
        data: msgRFID = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgRFID
            cls._MODEL_CLASS = msgRFID

    def getRfids(self) -> Optional[List[msgRFIDNode]]:
        """获取RFID节点列表

        Returns:
            (Optional[List[msgRFIDNode]]): 返回包含RFID节点信息的列表
        """
        if self.update():
            return self.data.rfidNodes
