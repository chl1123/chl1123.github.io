from .protobuf.messsage import Message_MoveStatus
from .lib.py_rpc import Message, default_plugin, call_service


@default_plugin("MoveFactory")
class Move(Message[Message_MoveStatus]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_MoveStatus"
    _PLUGIN = "MoveFactory"
    _MODEL_CLASS = Message_MoveStatus

    @classmethod
    @call_service("DSPChassis")
    def getChassisStop(cls) -> bool:
        """底盘是否停止（仅通过walk电机判断）

        Returns:
            bool: 如果行走电机停止则为True
        """
        pass
