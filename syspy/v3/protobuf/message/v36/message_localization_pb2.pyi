from . import message_header_pb2 as _message_header_pb2
from . import message_error_pb2 as _message_error_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msg2DCamInfo(_message.Message):
    __slots__ = ["cameraName", "distortionModel", "header", "isExtrinsicsCaib", "isIntrinsicsCaib", "mCx", "mCy", "mFx", "mFy", "mInfrared", "mK1", "mK2", "mK3", "mK4", "mK5", "mK6", "mP1", "mP2", "mSeertagFamilyID", "mSeertagSize", "modelType", "pitch", "roll", "x", "y", "yaw", "z"]
    CAMERANAME_FIELD_NUMBER: _ClassVar[int]
    DISTORTIONMODEL_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ISEXTRINSICSCAIB_FIELD_NUMBER: _ClassVar[int]
    ISINTRINSICSCAIB_FIELD_NUMBER: _ClassVar[int]
    MCX_FIELD_NUMBER: _ClassVar[int]
    MCY_FIELD_NUMBER: _ClassVar[int]
    MFX_FIELD_NUMBER: _ClassVar[int]
    MFY_FIELD_NUMBER: _ClassVar[int]
    MINFRARED_FIELD_NUMBER: _ClassVar[int]
    MK1_FIELD_NUMBER: _ClassVar[int]
    MK2_FIELD_NUMBER: _ClassVar[int]
    MK3_FIELD_NUMBER: _ClassVar[int]
    MK4_FIELD_NUMBER: _ClassVar[int]
    MK5_FIELD_NUMBER: _ClassVar[int]
    MK6_FIELD_NUMBER: _ClassVar[int]
    MODELTYPE_FIELD_NUMBER: _ClassVar[int]
    MP1_FIELD_NUMBER: _ClassVar[int]
    MP2_FIELD_NUMBER: _ClassVar[int]
    MSEERTAGFAMILYID_FIELD_NUMBER: _ClassVar[int]
    MSEERTAGSIZE_FIELD_NUMBER: _ClassVar[int]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    cameraName: str
    distortionModel: str
    header: _message_header_pb2.msgHeader
    isExtrinsicsCaib: bool
    isIntrinsicsCaib: bool
    mCx: float
    mCy: float
    mFx: float
    mFy: float
    mInfrared: float
    mK1: float
    mK2: float
    mK3: float
    mK4: float
    mK5: float
    mK6: float
    mP1: float
    mP2: float
    mSeertagFamilyID: float
    mSeertagSize: float
    modelType: str
    pitch: float
    roll: float
    x: float
    y: float
    yaw: float
    z: float
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., cameraName: _Optional[str] = ..., mInfrared: _Optional[float] = ..., mSeertagSize: _Optional[float] = ..., mSeertagFamilyID: _Optional[float] = ..., modelType: _Optional[str] = ..., distortionModel: _Optional[str] = ..., isIntrinsicsCaib: bool = ..., isExtrinsicsCaib: bool = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., roll: _Optional[float] = ..., pitch: _Optional[float] = ..., yaw: _Optional[float] = ..., mFx: _Optional[float] = ..., mFy: _Optional[float] = ..., mCx: _Optional[float] = ..., mCy: _Optional[float] = ..., mK1: _Optional[float] = ..., mK2: _Optional[float] = ..., mK3: _Optional[float] = ..., mK4: _Optional[float] = ..., mK5: _Optional[float] = ..., mK6: _Optional[float] = ..., mP1: _Optional[float] = ..., mP2: _Optional[float] = ...) -> None: ...

class msg3DPose(_message.Message):
    __slots__ = ["extraData", "header", "qW", "qX", "qY", "qZ", "x", "y", "z"]
    EXTRADATA_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    QW_FIELD_NUMBER: _ClassVar[int]
    QX_FIELD_NUMBER: _ClassVar[int]
    QY_FIELD_NUMBER: _ClassVar[int]
    QZ_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    extraData: str
    header: _message_header_pb2.msgHeader
    qW: float
    qX: float
    qY: float
    qZ: float
    x: float
    y: float
    z: float
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., qW: _Optional[float] = ..., qX: _Optional[float] = ..., qY: _Optional[float] = ..., qZ: _Optional[float] = ..., extraData: _Optional[str] = ...) -> None: ...

class msgLocFinished(_message.Message):
    __slots__ = ["value"]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: bool
    def __init__(self, value: bool = ...) -> None: ...

class msgLocalTagLocalization(_message.Message):
    __slots__ = ["angle", "distanceNotFindTag", "groupName", "header", "x", "y"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    DISTANCENOTFINDTAG_FIELD_NUMBER: _ClassVar[int]
    GROUPNAME_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    distanceNotFindTag: float
    groupName: str
    header: _message_header_pb2.msgHeader
    x: float
    y: float
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ..., distanceNotFindTag: _Optional[float] = ..., groupName: _Optional[str] = ...) -> None: ...

class msgLocalization(_message.Message):
    __slots__ = ["angle", "confidence", "errors", "header", "locMethod", "locState", "localTag", "pitch", "roll", "x", "y", "z"]
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_error_pb2.msgError, _Mapping]] = ...) -> None: ...
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    LOCALTAG_FIELD_NUMBER: _ClassVar[int]
    LOCMETHOD_FIELD_NUMBER: _ClassVar[int]
    LOCSTATE_FIELD_NUMBER: _ClassVar[int]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    angle: float
    confidence: float
    errors: _containers.MessageMap[str, _message_error_pb2.msgError]
    header: _message_header_pb2.msgHeader
    locMethod: int
    locState: int
    localTag: msgLocalTagLocalization
    pitch: float
    roll: float
    x: float
    y: float
    z: float
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., angle: _Optional[float] = ..., roll: _Optional[float] = ..., pitch: _Optional[float] = ..., confidence: _Optional[float] = ..., locState: _Optional[int] = ..., locMethod: _Optional[int] = ..., localTag: _Optional[_Union[msgLocalTagLocalization, _Mapping]] = ..., errors: _Optional[_Mapping[str, _message_error_pb2.msgError]] = ...) -> None: ...
