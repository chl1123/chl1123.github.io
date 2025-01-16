from ..protobuf.messsage import CanFrame
from .py_rpc import Message, default_plugin, call_service


@default_plugin("DSPChassis")
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

    @classmethod
    @call_service(func_name="sendPassThroughCanFrame")
    def sendPassThroughCanFrame(cls, channel: int, can_id: int, dlc: int, extend: bool, can_string: str):
        """
        Args:
            channel (int):
            can_id (int):
            dlc (int):
            extend (bool):
            can_string (str):

        Returns:
            bool:
        """
        pass

    @classmethod
    @call_service(func_name="sendCanFrame")
    def sendCanFrame(cls, channel: int, can_id: int, dlc: int, extend: bool, can_string: str):
        """
        Args:
            channel (int):
            can_id (int):
            dlc (int):
            extend (bool):
            can_string (str):
        """
        pass

    @classmethod
    @call_service(func_name="canPassThroughRxId")
    def canPassThroughRxId(cls, channel: int, id_nums: int, can_id1: int, can_id2: int, can_id3: int, can_id4: int,
                           can_id5: int) -> int:
        """
        Args:
            channel (int):
            id_nums (int):
            can_id1 (int):
            can_id2 (int):
            can_id3 (int):
            can_id4 (int):
            can_id5 (int):

        Returns:
            int:
        """
        pass
