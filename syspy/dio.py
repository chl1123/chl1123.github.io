from .protobuf.messsage import Message_DI, Message_DO
from .py_ipc import Message
from .service_utils import default_plugin, call_service


@default_plugin("DSPChassis")
class Di(Message[Message_DI]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_DI"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = Message_DI

    @classmethod
    def get_di(cls, di: int) -> bool:
        """检测单个DI状态信息
        Args:
            di (int): 需要检测的 DI

        Returns:
            bool: 返回指定DI的状态，若DI不存在返回False
        """
        cls.update()
        if cls.data:
            for node in cls.data.node:
                if node.id == di:
                    return node.status
        return False


@default_plugin("DSPChassis")
class Do(Message[Message_DO]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_DO"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = Message_DO

    @classmethod
    def get_do(cls, do: int):
        """检测单个DO状态信息
        Args:
            do (int): 需要检测的 DO

        Returns:
            bool: 返回指定DO的状态，若DO不存在返回False
        """
        cls.update()
        if cls.data:
            for node in cls.data.node:
                if node.id == do:
                    return node.status
        return False

    @classmethod
    @call_service()
    def setDO(cls, id: int, status: bool) -> bool:
        """控制DO的开关

        Args:
            id (int): DO的id
            status (bool): 是否打开这个DO

        Returns:
            bool: 如果不存在这个DO的id，返回False，而且会报错，agv也会停下来
        """
        pass
