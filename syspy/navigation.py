from .protobuf.messsage import Message_NavSpeed
from .py_ipc import Message

class NavSpeed(Message[Message_NavSpeed]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_NavSpeed"
    _PLUGIN = "MoveFactory"
    _MODEL_CLASS = Message_NavSpeed