from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.lib.can_frame import CanInterface

@default_plugin("DSPChassis")
class CanV3(CanInterface):
    """CAN协议"""

    _TOPIC = "CanFrame"
    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from ..protobuf import CanFrame
            cls._MODEL_CLASS = CanFrame

    @classmethod
    @call_service(func_name="sendPassThroughCanFrame")
    def sendPassThroughCanFrame(cls, channel: int, can_id: int, dlc: int, extend: bool, can_string: str):
        pass

    @classmethod
    @call_service(func_name="sendCanFrame")
    def sendCanFrame(cls, channel: int, can_id: int, dlc: int, extend: bool, can_string: str):
        pass

    @classmethod
    @call_service(func_name="canPassThroughRxId")
    def canPassThroughRxId(cls, channel: int, id_nums: int, can_id1: int, can_id2: int, can_id3: int, can_id4: int,
                           can_id5: int) -> int:
        pass
