from typing import List, TYPE_CHECKING

from .lib.py_rpc import Message

if TYPE_CHECKING:
    from .protobuf import Message_Bin  # IDE类型提示


class Bin(Message["Message_Bins"]):
    """库位类"""

    _TOPIC = "rbk.protocol.Message_Bins"
    _PLUGIN = "RecoFactory"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Bins
            cls._MODEL_CLASS = Message_Bins

    @classmethod
    def get_bins(cls) -> List["Message_Bin"]:
        if cls.update():
            return cls.data.bins
