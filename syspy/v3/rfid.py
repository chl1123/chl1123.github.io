import typing
from syspy.rfid import RFIDInterface


class RFIDV3(RFIDInterface):
    """RFID类"""

    _TOPIC = "rbk.protocol.Message_RFID"
    _PLUGIN = "RFIDSensor"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import Message_RFID
        data: Message_RFID = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_RFID
            cls._MODEL_CLASS = Message_RFID

    def get_rfids(self) -> typing.List["Message_RFIDNode"]:
        """获取RFID节点列表

        Returns:
            返回包含RFID节点信息的列表
        """
        if self.update():
            return self.data.rfid_nodes
