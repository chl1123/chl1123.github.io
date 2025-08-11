import typing
from syspy.rfid import RFIDInterface


class RFIDV4(RFIDInterface):
    """RFID类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .include.protocol.messageV4_rfid_pb2 import MessageV4_RFID
            cls._MODEL_CLASS = MessageV4_RFID

    def get_rfids(self) -> typing.List["MessageV4_RFIDNode"]:
        """获取RFID节点列表

        Returns:
            返回包含RFID节点信息的列表
        """
        if self.update():
            return self.data.rfid_nodes
