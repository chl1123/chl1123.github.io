from typing import List, Optional, TYPE_CHECKING
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import RBK_VERSION

if TYPE_CHECKING:
    if RBK_VERSION == 3:
        from syspy.v3.protobuf import msgMagneticNode
    elif RBK_VERSION == 4:
        pass


class MagneticInterface(ABC, Message):
    """磁传感器类"""

    @classmethod
    def getMagnetics(cls) -> Optional[List["msgMagneticNode"]]:
        """获取磁节点列表

        Returns:
            (Optional[List[msgMagneticNode]]): 包含所有磁节点信息的列表
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.magnetic import MagneticV3
    Magnetic: MagneticInterface = MagneticV3()
elif RBK_VERSION == 4:
    from syspy.v4.magnetic import MagneticV4
    Magnetic: MagneticInterface = MagneticV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")