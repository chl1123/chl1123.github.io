import typing
from syspy.magnetic import MagneticInterface


class MagneticV3(MagneticInterface):
    """磁传感器类"""

    _TOPIC = "rbk.protocol.msgMagnetic"
    _PLUGIN = "MagneticSensor"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import msgMagnetic, msgMagneticNode
        data: msgMagnetic = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgMagnetic
            cls._MODEL_CLASS = msgMagnetic

    def getMagnetics(self) -> typing.List["msgMagneticNode"]:
        """获取磁节点列表

        Returns:
            typing.List[msgMagneticNode]: 包含所有磁节点信息的列表
        """
        if self.update():
            return self.data.magneticNodes