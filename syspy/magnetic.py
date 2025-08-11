import typing
from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError
from syspy import rbk_version

if typing.TYPE_CHECKING:
    if rbk_version == 3:
        from syspy.v3.protobuf import Message_MagneticNode
    elif rbk_version == 4:
        pass


class MagneticInterface(ABC, Message):
    """磁传感器类"""

    @classmethod
    def get_magnetics(cls) -> typing.List["Message_MagneticNode"]:
        """获取磁节点列表

        Returns:
            typing.List[Message_MagneticNode]: 包含所有磁节点信息的列表
        """
        raise RBKVersionError()


from syspy.config import rbk_version
if rbk_version == 3:
    from syspy.v3.magnetic import MagneticV3
    Magnetic: MagneticInterface = MagneticV3()
elif rbk_version == 4:
    from syspy.v4.magnetic import MagneticV4
    Magnetic: MagneticInterface = MagneticV4()
else:
    raise ValueError(f"Unsupported RBK version: {rbk_version}")
