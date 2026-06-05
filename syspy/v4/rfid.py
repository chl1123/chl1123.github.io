import typing
from typing import Optional, List
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

    def getRfids(self) -> Optional[List["MessageV4_RFIDNode"]]:
        """获取RFID节点列表

        Returns:
            (Optional[List["MessageV4_RFIDNode"]]): 返回包含RFID节点信息的列表
        """
        if self.update():
            return self.data.rfid_nodes
