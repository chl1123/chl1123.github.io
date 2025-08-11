from typing import ClassVar, Optional

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Header(_message.Message):
    """
    表示消息头的模型，包含消息发布时间、数据时间、序列号和帧ID等信息。

    Attributes:
        pub_nsec (int): 消息发布的纳秒时间戳，默认为 0。
        data_nsec (int): 数据对应的纳秒时间戳，默认为 0。
        seq (int): 消息序列号，默认为 0。
        frame_id (str): 消息所属的帧 ID，默认为空字符串。
    """
    __slots__ = ["data_nsec", "frame_id", "pub_nsec", "seq"]
    DATA_NSEC_FIELD_NUMBER: ClassVar[int]
    FRAME_ID_FIELD_NUMBER: ClassVar[int]
    PUB_NSEC_FIELD_NUMBER: ClassVar[int]
    SEQ_FIELD_NUMBER: ClassVar[int]
    data_nsec: int
    frame_id: str
    pub_nsec: int
    seq: int

    def __init__(self, pub_nsec: Optional[int] = ..., data_nsec: Optional[int] = ..., seq: Optional[int] = ...,
                 frame_id: Optional[str] = ...) -> None: ...
