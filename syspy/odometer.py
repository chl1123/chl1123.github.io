from .protobuf.messsage import Message_Odometer
from .lib.py_rpc import Message


class Odometer(Message[Message_Odometer]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_Odometer"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = Message_Odometer
