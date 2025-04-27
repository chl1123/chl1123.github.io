import typing

from .lib.py_rpc import Message

if typing.TYPE_CHECKING:
    from .protobuf import Message_MagneticNode


class Magnetic(Message["Message_Magnetic"]):
    """磁传感器类"""

    _TOPIC = "rbk.protocol.Message_Magnetic"
    _PLUGIN = "MagneticSensor"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Magnetic
            cls._MODEL_CLASS = Message_Magnetic

    @classmethod
    def get_magnetics(cls) -> typing.List["Message_MagneticNode"]:
        """获取磁节点列表

        Returns:
            typing.List[Message_MagneticNode]: 包含所有磁节点信息的列表
        """
        if cls.update():
            return cls.data.magnetic_nodes
