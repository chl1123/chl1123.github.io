import typing
from typing import List
from syspy.code_scanner import CodeScannerInterface

class CodeScannerV3(CodeScannerInterface):
    """PGV类"""

    _TOPIC = "rbk.protocol.msgCodeScanner"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgCodeScanner, msgCodeScannerDMT
        data: msgCodeScanner = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgCodeScanner
            cls._MODEL_CLASS = msgCodeScanner

    def getCodeScanners(self) -> List["msgCodeScannerDMT"]:
        """获取msgPGV_DMT对象列表

        Returns:
            msgPGV_DMT对象列表
        """
        if self.update():
            return self.data.codeScanners
