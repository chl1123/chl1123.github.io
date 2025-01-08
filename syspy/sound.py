from .protobuf.messsage import Message_Sound
from .lib.py_rpc import Message


class Sound(Message[Message_Sound]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_Sound"
    _PLUGIN = "Message_Sound"
    _MODEL_CLASS = Message_Sound
