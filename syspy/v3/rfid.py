import typing
from syspy.rfid import RFIDInterface


class RFIDV3(RFIDInterface):
    """RFID类"""

    _TOPIC = "rbk.protocol.msgRFID"
    _PLUGIN = "RFIDSensor"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgRFID
        data: msgRFID = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgRFID
            cls._MODEL_CLASS = msgRFID

    def getRfids(self) -> typing.List["msgRFIDNode"]:
        """获取RFID节点列表

        Returns:
            返回包含RFID节点信息的列表
        """
        if self.update():
            return self.data.rfid_nodes
