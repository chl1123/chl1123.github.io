from .protobuf.messsage import Message_Bins
from .py_ipc import Message


class Bin(Message[Message_Bins]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_Bins"
    _PLUGIN = "RecoFactory"
    _MODEL_CLASS = Message_Bins