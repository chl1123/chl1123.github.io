import typing
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import rbk_version

if typing.TYPE_CHECKING:
    if rbk_version == 3:
        from .protobuf import Message_RFIDNode as Message_RFIDNode
    elif rbk_version == 4:
        from ..include.protocol.messageV4_rfid_pb2 import MessageV4_RFIDNode as Message_RFIDNode
        pass


class RFIDInterface(ABC, Message):
    """RFID类"""

    @classmethod
    def get_rfids(cls) -> typing.List["Message_RFIDNode"]:
        """获取RFID节点列表

        Returns:
            返回包含RFID节点信息的列表
        """
        raise RBKVersionError()


from syspy.config import rbk_version
if rbk_version == 3:
    from syspy.v3.rfid import RFIDV3
    RFID: RFIDInterface = RFIDV3()
elif rbk_version == 4:
    from syspy.v4.rfid import RFIDV4
    RFID: RFIDInterface = RFIDV4()
else:
    raise ValueError(f"Unsupported RBK version: {rbk_version}")
