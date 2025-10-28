from typing import List, TYPE_CHECKING
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import RBK_VERSION

if TYPE_CHECKING:
    if RBK_VERSION == 3:
        from .v3.protobuf import msgCodeScannerDMT as msgCodeScannerDMT
        pass
    elif RBK_VERSION == 4:
        from .v4.protobuf.message.messageV4_pgv_pb2 import MessageV4_PGV_DMT as msgCodeScannerDMT


class CodeScannerInterface(ABC, Message):
    """PGV类"""

    @classmethod
    def get_code_scanners(cls) -> List["msgCodeScannerDMT"]:
        """获取msgCodeScannerDMT对象列表

        Returns:
            msgCodeScannerDMT对象列表

        Examples:
        ```python
        from syspy import CodeScanner
        code_scanners = CodeScanner.get_code_scanners()
        for code_scanner in code_scanners:  # code_scanner为msgCodeScannerDMT的对象
            print(code_scanner.codeScannerInfo.codeScannerName)
            print(code_scanner.tagValue)
        ```
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.code_scanner import CodeScannerV3
    CodeScanner: CodeScannerInterface = CodeScannerV3()
elif RBK_VERSION == 4:
    from syspy.v4.code_scanner import CodeScannerV4
    CodeScanner: CodeScannerInterface = CodeScannerV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
