from typing import List, TYPE_CHECKING
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import rbk_version

if TYPE_CHECKING:
    if rbk_version == 3:
        from .protobuf import Message_PGV_DMT as Message_PGV_DMT
        pass
    elif rbk_version == 4:
        from ..include.protocol.messageV4_pgv_pb2 import MessageV4_PGV_DMT as Message_PGV_DMT


class PgvInterface(ABC, Message):
    """PGV类"""

    @classmethod
    def get_pgvs(cls) -> List["Message_PGV_DMT"]:
        """获取Message_PGV_DMT对象列表

        Returns:
            Message_PGV_DMT对象列表
        """
        raise RBKVersionError()


from syspy.config import rbk_version
if rbk_version == 3:
    from syspy.v3.pgv import PgvV3
    Pgv: PgvInterface = PgvV3()
elif rbk_version == 4:
    from syspy.v4.pgv import PgvV4
    Pgv: PgvInterface = PgvV4()
else:
    raise ValueError(f"Unsupported RBK version: {rbk_version}")
