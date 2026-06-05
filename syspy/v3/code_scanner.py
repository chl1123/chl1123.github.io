from typing import Optional, List, TYPE_CHECKING
from syspy.code_scanner import CodeScannerInterface

class CodeScannerV3(CodeScannerInterface):
    """扫码器类"""

    _TOPIC = "rbk.protocol.msgCodeScanner"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgCodeScanner, msgCodeScannerDMT
        data: msgCodeScanner = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgCodeScanner
            cls._MODEL_CLASS = msgCodeScanner

    def getCodeScanners(self) -> Optional[List["msgCodeScannerDMT"]]:
        if self.update():
            return self.data.codeScanners
