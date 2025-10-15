import typing
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import RBK_VERSION

if typing.TYPE_CHECKING:
    if RBK_VERSION == 3:
        from .v3.protobuf import msgRFIDNode as msgRFIDNode
    elif RBK_VERSION == 4:
        from .v4.protobuf.message.messageV4_rfid_pb2 import MessageV4_RFIDNode as msgRFIDNode
        pass


class RFIDInterface(ABC, Message):
    """RFID类"""

    @classmethod
    def get_rfids(cls) -> typing.List["msgRFIDNode"]:
        """获取RFID节点列表

        Returns:
            返回包含RFID节点信息的列表
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.rfid import RFIDV3
    RFID: RFIDInterface = RFIDV3()
elif RBK_VERSION == 4:
    from syspy.v4.rfid import RFIDV4
    RFID: RFIDInterface = RFIDV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
