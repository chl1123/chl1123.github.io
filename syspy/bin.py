from typing import List

from .lib.py_rpc import Message
from .protobuf.message import Message_Bins
from .protobuf.message.message_bin_p2p import Message_Bin


class Bin(Message[Message_Bins]):
    """库位类"""

    _TOPIC = "rbk.protocol.Message_Bins"
    _PLUGIN = "RecoFactory"
    _MODEL_CLASS = Message_Bins

    @classmethod
    def get_bins(cls) -> List[Message_Bin]:
        if cls.update():
            return cls.data.bins
