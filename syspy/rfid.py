from .protobuf.messsage import Message_RFID
from .py_ipc import Message


class RFID(Message[Message_RFID]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_RFID"
    _PLUGIN = "RFIDSensor"
    _MODEL_CLASS = Message_RFID