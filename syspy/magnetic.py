from .protobuf.messsage import Message_Magnetic
from .py_ipc import Message


class Magnetic(Message[Message_Magnetic]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_Magnetic"
    _PLUGIN = "MagneticSensor"
    _MODEL_CLASS = Message_Magnetic
