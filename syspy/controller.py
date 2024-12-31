from .protobuf.messsage import Message_Controller
from .py_ipc import Message


class Controller(Message[Message_Controller]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_Controller"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = Message_Controller
