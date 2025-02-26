import typing

from .lib.py_rpc import Message
from .protobuf.message import Message_RFID, Message_RFIDNode


class RFID(Message[Message_RFID]):
    """RFID类"""

    _TOPIC = "rbk.protocol.Message_RFID"
    _PLUGIN = "RFIDSensor"
    _MODEL_CLASS = Message_RFID

    @classmethod
    def get_rfids(cls) -> typing.List["Message_RFIDNode"]:
        """获取RFID节点列表

        Returns:
            返回包含RFID节点信息的列表
        """
        if cls.update():
            return cls.data.rfid_nodes
