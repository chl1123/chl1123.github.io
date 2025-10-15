import message_header_pb2 as _message_header_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msg2DCamInfo(_message.Message):
    __slots__ = ["cameraName", "distortionModel", "header", "isExtrinsicsCaib", "isIntrinsicsCaib", "mCx", "mCy", "mFx", "mFy", "mInfrared", "mK1", "mK2", "mK3", "mK4", "mK5", "mK6", "mP1", "mP2", "mSeertagFamilyID", "mSeertagSize", "modelType", "pitch", "roll", "x", "y", "yaw", "z"]
    CAMERANAME_FIELD_NUMBER: ClassVar[int]
    DISTORTIONMODEL_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    ISEXTRINSICSCAIB_FIELD_NUMBER: ClassVar[int]
    ISINTRINSICSCAIB_FIELD_NUMBER: ClassVar[int]
    MCX_FIELD_NUMBER: ClassVar[int]
    MCY_FIELD_NUMBER: ClassVar[int]
    MFX_FIELD_NUMBER: ClassVar[int]
    MFY_FIELD_NUMBER: ClassVar[int]
    MINFRARED_FIELD_NUMBER: ClassVar[int]
    MK1_FIELD_NUMBER: ClassVar[int]
    MK2_FIELD_NUMBER: ClassVar[int]
    MK3_FIELD_NUMBER: ClassVar[int]
    MK4_FIELD_NUMBER: ClassVar[int]
    MK5_FIELD_NUMBER: ClassVar[int]
    MK6_FIELD_NUMBER: ClassVar[int]
    MODELTYPE_FIELD_NUMBER: ClassVar[int]
    MP1_FIELD_NUMBER: ClassVar[int]
    MP2_FIELD_NUMBER: ClassVar[int]
    MSEERTAGFAMILYID_FIELD_NUMBER: ClassVar[int]
    MSEERTAGSIZE_FIELD_NUMBER: ClassVar[int]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., cameraName: Optional[str] = ..., mInfrared: Optional[float] = ..., mSeertagSize: Optional[float] = ..., mSeertagFamilyID: Optional[float] = ..., modelType: Optional[str] = ..., distortionModel: Optional[str] = ..., isIntrinsicsCaib: bool = ..., isExtrinsicsCaib: bool = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., roll: Optional[float] = ..., pitch: Optional[float] = ..., yaw: Optional[float] = ..., mFx: Optional[float] = ..., mFy: Optional[float] = ..., mCx: Optional[float] = ..., mCy: Optional[float] = ..., mK1: Optional[float] = ..., mK2: Optional[float] = ..., mK3: Optional[float] = ..., mK4: Optional[float] = ..., mK5: Optional[float] = ..., mK6: Optional[float] = ..., mP1: Optional[float] = ..., mP2: Optional[float] = ...) -> None: ...

class msg3DPose(_message.Message):
    __slots__ = ["extraData", "header", "qW", "qX", "qY", "qZ", "x", "y", "z"]
    EXTRADATA_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    QW_FIELD_NUMBER: ClassVar[int]
    QX_FIELD_NUMBER: ClassVar[int]
    QY_FIELD_NUMBER: ClassVar[int]
    QZ_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    extraData: str
    header: _message_header_pb2.msgHeader
    qW: float
    qX: float
    qY: float
    qZ: float
    x: float
    y: float
    z: float
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., qW: Optional[float] = ..., qX: Optional[float] = ..., qY: Optional[float] = ..., qZ: Optional[float] = ..., extraData: Optional[str] = ...) -> None: ...

class msgLocFinished(_message.Message):
    __slots__ = ["value"]
    VALUE_FIELD_NUMBER: ClassVar[int]
    value: bool
    def __init__(self, value: bool = ...) -> None: ...

class msgLocalization(_message.Message):
    __slots__ = ["angle", "confidence", "header", "locMethod", "locState", "pitch", "roll", "x", "y", "z"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    LOCMETHOD_FIELD_NUMBER: ClassVar[int]
    LOCSTATE_FIELD_NUMBER: ClassVar[int]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    angle: float
    confidence: float
    header: _message_header_pb2.msgHeader
    locMethod: int
    locState: int
    pitch: float
    roll: float
    x: float
    y: float
    z: float
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., angle: Optional[float] = ..., roll: Optional[float] = ..., pitch: Optional[float] = ..., confidence: Optional[float] = ..., locState: Optional[int] = ..., locMethod: Optional[int] = ...) -> None: ...
