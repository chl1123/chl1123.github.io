import typing
from syspy.magnetic import MagneticInterface


class MagneticV3(MagneticInterface):
    """磁传感器类"""

    _TOPIC = "rbk.protocol.Message_Magnetic"
    _PLUGIN = "MagneticSensor"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
        from .protobuf import Message_Magnetic
        data: Message_Magnetic = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Magnetic
            cls._MODEL_CLASS = Message_Magnetic

    def get_magnetics(self) -> typing.List["Message_MagneticNode"]:
        """获取磁节点列表

        Returns:
            typing.List[Message_MagneticNode]: 包含所有磁节点信息的列表
        """
        if self.update():
            return self.data.magnetic_nodes
