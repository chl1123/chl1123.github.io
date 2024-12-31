from .protobuf.messsage import Message_AllLasers
from .py_ipc import Message


class Laser(Message[Message_AllLasers]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_AllLasers"
    _PLUGIN = "MultiLaser"
    _MODEL_CLASS = Message_AllLasers