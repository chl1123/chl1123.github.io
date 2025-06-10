from typing import List, TYPE_CHECKING

from .lib.py_rpc import Message

if TYPE_CHECKING:
    from .protobuf import Message_PGV


class Pgv(Message["Message_PGV"]):
    """PGV类"""

    _TOPIC = "rbk.protocol.Message_PGV"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_PGV
            cls._MODEL_CLASS = Message_PGV

    @classmethod
    def get_pgvs(cls) -> List["Message_PGV"]:
        """获取PGV_DMT对象列表

        Returns:
            PGV_DMT对象列表
        """
        if cls.update():
            return cls.data.pgvs
