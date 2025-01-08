from .protobuf.messsage import Message_PGV
from .lib.py_rpc import Message


class Pgv(Message[Message_PGV]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_PGV"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = Message_PGV
