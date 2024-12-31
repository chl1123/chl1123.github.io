from .protobuf.messsage import CanFrame
from .py_ipc import Message


class Can(Message[CanFrame]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "CanFrame"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = CanFrame