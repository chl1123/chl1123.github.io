from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.code_scanner import CodeScannerInterface

if TYPE_CHECKING:
    from .protobuf.message.message_codescanner_pb2 import msgCodeScanner, msgCodeScannerDMT


class CodeScannerV3(CodeScannerInterface):
    """扫码器类"""

    data: msgCodeScanner = None

    _TOPIC = "rbk.protocol.msgCodeScanner"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_codescanner_pb2 import msgCodeScanner
            cls._MODEL_CLASS = msgCodeScanner

    def getCodeScanners(self) -> Optional[RepeatedCompositeFieldContainer["msgCodeScannerDMT"]]:
        if self.update():
            return self.data.codeScanners
