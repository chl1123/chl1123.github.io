from typing import List

from .protobuf.messsage import Message_Bins
from .lib.py_rpc import Message
from .protobuf.messsage.message_bin_p2p import Message_Bin


class Bin(Message[Message_Bins]):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """

    _TOPIC = "rbk.protocol.Message_Bins"
    _PLUGIN = "RecoFactory"
    _MODEL_CLASS = Message_Bins

    @classmethod
    def get_bins(cls) -> List[Message_Bin]:
        if cls.update():
            return cls.data.bins