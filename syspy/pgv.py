from typing import List, TYPE_CHECKING
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import RBK_VERSION

if TYPE_CHECKING:
    if RBK_VERSION == 3:
        from .v3.protobuf import msgPGV_DMT as msgPGV_DMT
        pass
    elif RBK_VERSION == 4:
        from .v4.protobuf.message.messageV4_pgv_pb2 import MessageV4_PGV_DMT as msgPGV_DMT


class PgvInterface(ABC, Message):
    """PGV类"""

    @classmethod
    def get_pgvs(cls) -> List["msgPGV_DMT"]:
        """获取msgPGV_DMT对象列表

        Returns:
            msgPGV_DMT对象列表
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.pgv import PgvV3
    Pgv: PgvInterface = PgvV3()
elif RBK_VERSION == 4:
    from syspy.v4.pgv import PgvV4
    Pgv: PgvInterface = PgvV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
