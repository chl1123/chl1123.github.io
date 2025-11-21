from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.lib.can_frame import CanInterface

@default_plugin("DSPChassis")  # todo RBK4
class CanV4(CanInterface):
    """CAN协议"""

    _TOPIC = "CanFrame"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            # todo from ..include.protocol.xxx import CanFrame
            cls._MODEL_CLASS = None

    @classmethod
    @call_service(func_name="sendPassThroughCanFrame")
    def sendPassThroughCanFrame(cls, channel: int, can_id: int, dlc: int, extend: bool, can_string: str):
        """发送CAN帧

        Args:
            channel (int):
            can_id (int):
            dlc (int):
            extend (bool):
            can_string (str):
        """
        pass

    @classmethod
    @call_service(func_name="sendCanFrame")
    def sendCanFrame(cls, channel: int, can_id: int, dlc: int, extend: bool, can_string: str):
        """发送CAN帧

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
        """检查CAN ID是否可以通过指定通道

        Args:
            channel (int):
            id_nums (int):
            can_id1 (int):
            can_id2 (int):
            can_id3 (int):
            can_id4 (int):
            can_id5 (int):

        Returns:
            (int):
        """
        pass
