from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

import message_header_pb2 as _message_header_pb2

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Bin(_message.Message):
    """
    表示库位相关信息。

    Attributes:
        binId (str): 库位的唯一标识符，默认为空字符串。
        filled (bool): 表示库位是否已被占用，默认未占用。
        status (Message_Bin.Status): 库位的状态，默认为连接状态。
    """

    __slots__ = ["binId", "filled", "status"]

    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        """
        库位状态枚举类。

        Attributes:
            Connect: 值为 0，表示库位已连接的状态。
            DisConnect: 值为 1，表示库位未连接的状态。
        """
        __slots__ = []

    BINID_FIELD_NUMBER: ClassVar[int]
    Connect: Message_Bin.Status
    DisConnect: Message_Bin.Status
    FILLED_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    binId: str
    filled: bool
    status: Message_Bin.Status

    def __init__(self, binId: Optional[str] = ..., filled: bool = ...,
                 status: Optional[Union[Message_Bin.Status, str]] = ...) -> None: ...


class Message_Bins(_message.Message):
    """
    表示多个库位的消息集合。

    Attributes:
        header (typing.Optional[Message_Header]): 消息头，可选，默认为 None。
        bins (typing.List[Message_Bin]): 库位列表，默认为空列表。
    """
    __slots__ = ["bins", "header"]
    BINS_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    bins: _containers.RepeatedCompositeFieldContainer[Message_Bin]
    header: _message_header_pb2.Message_Header

    def __init__(self, header: Optional[Union[_message_header_pb2.Message_Header, Mapping]] = ...,
                 bins: Optional[Iterable[Union[Message_Bin, Mapping]]] = ...) -> None: ...
