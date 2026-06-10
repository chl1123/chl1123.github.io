from typing import Optional

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.code_scanner import CodeScannerInterface


class CodeScannerV4(CodeScannerInterface):
    """扫码器类"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_pgv_pb2 import MessageV4_PGV
            cls._MODEL_CLASS = MessageV4_PGV

    def getCodeScanners(self) -> Optional[RepeatedCompositeFieldContainer["MessageV4_PGV_DMT"]]:
        if self.update():
            return self.data.pgvs
