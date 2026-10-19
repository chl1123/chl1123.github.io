from . import message_header_pb2 as _message_header_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgCodeScanner(_message.Message):
    __slots__ = ["codeScanners"]
    CODESCANNERS_FIELD_NUMBER: _ClassVar[int]
    codeScanners: _containers.RepeatedCompositeFieldContainer[msgCodeScannerDMT]
    def __init__(self, codeScanners: _Optional[_Iterable[_Union[msgCodeScannerDMT, _Mapping]]] = ...) -> None: ...

class msgCodeScannerDMT(_message.Message):
    __slots__ = ["codeScannerInfo", "errorCode", "header", "isBarCode", "isDMTDetected", "tagDiffAngle", "tagDiffX", "tagDiffY", "tagValue", "warningCode"]
    CODESCANNERINFO_FIELD_NUMBER: _ClassVar[int]
    ERRORCODE_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ISBARCODE_FIELD_NUMBER: _ClassVar[int]
    ISDMTDETECTED_FIELD_NUMBER: _ClassVar[int]
    TAGDIFFANGLE_FIELD_NUMBER: _ClassVar[int]
    TAGDIFFX_FIELD_NUMBER: _ClassVar[int]
    TAGDIFFY_FIELD_NUMBER: _ClassVar[int]
    TAGVALUE_FIELD_NUMBER: _ClassVar[int]
    WARNINGCODE_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, tagDiffX: _Optional[float] = ..., tagDiffY: _Optional[float] = ..., tagDiffAngle: _Optional[float] = ..., tagValue: _Optional[int] = ..., warningCode: _Optional[int] = ..., isDMTDetected: bool = ..., errorCode: _Optional[int] = ..., header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., codeScannerInfo: _Optional[_Union[msgCodeScannerInfo, _Mapping]] = ..., isBarCode: bool = ...) -> None: ...

class msgCodeScannerInfo(_message.Message):
    __slots__ = ["coordinate", "func", "isUpside", "key", "pitch", "roll", "x", "y", "yaw", "z"]
    COORDINATE_FIELD_NUMBER: _ClassVar[int]
    FUNC_FIELD_NUMBER: _ClassVar[int]
    ISUPSIDE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    coordinate: str
    func: str
    isUpside: bool
    key: str
    pitch: float
    roll: float
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, key: _Optional[str] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., yaw: _Optional[float] = ..., pitch: _Optional[float] = ..., roll: _Optional[float] = ..., func: _Optional[str] = ..., coordinate: _Optional[str] = ..., isUpside: bool = ...) -> None: ...
