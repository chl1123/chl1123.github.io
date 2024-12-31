from .protobuf.messsage import Message_Localization
from .py_ipc import Message


class Loc(Message[Message_Localization]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_Localization"
    _PLUGIN = "MCLoc"
    _MODEL_CLASS = Message_Localization
