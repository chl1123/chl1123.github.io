import typing
from typing import List
from syspy.pgv import PgvInterface

class PgvV3(PgvInterface):
    """PGV类"""

    _TOPIC = "rbk.protocol.msgCodeScanner"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgCodeScanner, msgCodeScannerDMT
        data: msgCodeScanner = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgCodeScanner
            cls._MODEL_CLASS = msgCodeScanner

    def get_pgvs(self) -> List["msgCodeScannerDMT"]:
        """获取msgPGV_DMT对象列表

        Returns:
            msgPGV_DMT对象列表
        """
        if self.update():
            return self.data.codeScanners
