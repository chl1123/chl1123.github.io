from typing import List
from syspy.code_scanner import CodeScannerInterface

class CodeScannerV4(CodeScannerInterface):
    """PGV类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_pgv_pb2 import MessageV4_PGV
            cls._MODEL_CLASS = MessageV4_PGV

    def get_code_scanners(self) -> List["MessageV4_PGV_DMT"]:
        """获取Message_PGV_DMT对象列表

        Returns:
            Message_PGV_DMT对象列表
        """
        if self.update():
            return self.data.pgvs
