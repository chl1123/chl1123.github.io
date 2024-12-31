from .protobuf.messsage import Message_DistanceSensor
from .py_ipc import Message


class Distance(Message[Message_DistanceSensor]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_DistanceSensor"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = Message_DistanceSensor
