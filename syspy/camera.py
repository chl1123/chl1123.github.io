from .protobuf.messsage import Message_AllCameraCloud
from .py_ipc import Message


class Camera(Message[Message_AllCameraCloud]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_AllCameraCloud"
    _PLUGIN = "MultiDcamera"
    _MODEL_CLASS = Message_AllCameraCloud