import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgCodeScanner(_message.Message):
    __slots__ = ["codeScanners"]
    CODESCANNERS_FIELD_NUMBER: ClassVar[int]
    codeScanners: _containers.RepeatedCompositeFieldContainer[msgCodeScannerDMT]
    def __init__(self, codeScanners: Optional[Iterable[Union[msgCodeScannerDMT, Mapping]]] = ...) -> None: ...

class msgCodeScannerDMT(_message.Message):
    __slots__ = ["codeScannerInfo", "errorCode", "header", "isBarCode", "isDMTDetected", "tagDiffAngle", "tagDiffX", "tagDiffY", "tagValue", "warningCode"]
    CODESCANNERINFO_FIELD_NUMBER: ClassVar[int]
    ERRORCODE_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ISBARCODE_FIELD_NUMBER: ClassVar[int]
    ISDMTDETECTED_FIELD_NUMBER: ClassVar[int]
    TAGDIFFANGLE_FIELD_NUMBER: ClassVar[int]
    TAGDIFFX_FIELD_NUMBER: ClassVar[int]
    TAGDIFFY_FIELD_NUMBER: ClassVar[int]
    TAGVALUE_FIELD_NUMBER: ClassVar[int]
    WARNINGCODE_FIELD_NUMBER: ClassVar[int]
    codeScannerInfo: msgCodeScannerInfo
    errorCode: int
    header: _message_header_pb2.msgHeader
    isBarCode: bool
    isDMTDetected: bool
    tagDiffAngle: float
    tagDiffX: float
    tagDiffY: float
    tagValue: int
    warningCode: int
    def __init__(self, tagDiffX: Optional[float] = ..., tagDiffY: Optional[float] = ..., tagDiffAngle: Optional[float] = ..., tagValue: Optional[int] = ..., warningCode: Optional[int] = ..., isDMTDetected: bool = ..., errorCode: Optional[int] = ..., header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., codeScannerInfo: Optional[Union[msgCodeScannerInfo, Mapping]] = ..., isBarCode: bool = ...) -> None: ...

class msgCodeScannerInfo(_message.Message):
    __slots__ = ["coordinate", "func", "isUpside", "name", "pitch", "roll", "x", "y", "yaw", "z"]
    COORDINATE_FIELD_NUMBER: ClassVar[int]
    FUNC_FIELD_NUMBER: ClassVar[int]
    ISUPSIDE_FIELD_NUMBER: ClassVar[int]
    NAME_FIELD_NUMBER: ClassVar[int]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    coordinate: str
    func: str
    isUpside: bool
    name: str
    pitch: float
    roll: float
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, name: Optional[str] = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., yaw: Optional[float] = ..., pitch: Optional[float] = ..., roll: Optional[float] = ..., func: Optional[str] = ..., coordinate: Optional[str] = ..., isUpside: bool = ...) -> None: ...
