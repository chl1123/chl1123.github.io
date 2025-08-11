import typing
from typing import List
from syspy.pgv import PgvInterface

class PgvV3(PgvInterface):
    """PGV类"""

    _TOPIC = "rbk.protocol.Message_PGV"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import Message_PGV
        data: Message_PGV = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_PGV
            cls._MODEL_CLASS = Message_PGV

    def get_pgvs(self) -> List["Message_PGV_DMT"]:
        """获取Message_PGV_DMT对象列表

        Returns:
            Message_PGV_DMT对象列表
        """
        if self.update():
            return self.data.pgvs
