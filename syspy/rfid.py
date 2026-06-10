from typing import Optional, TYPE_CHECKING
from abc import ABC

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import RBK_VERSION

if TYPE_CHECKING:
    if RBK_VERSION == 3:
        from .v3.protobuf.message.message_rfid_pb2 import msgRFIDNode as msgRFIDNode
    elif RBK_VERSION == 4:
        from .v4.protobuf.message.messageV4_rfid_pb2 import MessageV4_RFIDNode as msgRFIDNode
        pass


class RfidInterface(ABC, Message):
    """RFID类"""

    @classmethod
    def getRfids(cls) -> Optional[RepeatedCompositeFieldContainer["msgRFIDNode"]]:
        """获取RFID节点列表

        Returns:
            (Optional[RepeatedCompositeFieldContainer["msgRFIDNode"]]): 返回包含RFID节点信息的列表
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.rfid import RfidV3
    Rfid: RfidInterface = RfidV3()
elif RBK_VERSION == 4:
    from syspy.v4.rfid import RfidV4
    Rfid: RfidInterface = RfidV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
