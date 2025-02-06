from typing import Tuple

from .protobuf.messsage import Message_NavSpeed
from .lib.py_rpc import Message


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

    @classmethod
    def get_speed(cls) -> Tuple[float, float, float]:
        if cls.update():
            return cls.data.x, cls.data.y, cls.data.rotate