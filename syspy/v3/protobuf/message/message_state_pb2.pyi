from google.protobuf import struct_pb2 as _struct_pb2
import message_calibstatus_pb2 as _message_calibstatus_pb2
import message_map_pb2 as _message_map_pb2
import message_gnss_pb2 as _message_gnss_pb2
import message_error_pb2 as _message_error_pb2
import message_devicestatus_pb2 as _message_devicestatus_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgPushAbnormalInfo(_message.Message):
    __slots__ = ["abnormalSize", "abnormals"]
    ABNORMALSIZE_FIELD_NUMBER: ClassVar[int]
    ABNORMALS_FIELD_NUMBER: ClassVar[int]
    abnormalSize: int
    abnormals: _struct_pb2.Struct
    def __init__(self, abnormals: Optional[Union[_struct_pb2.Struct, Mapping]] = ..., abnormalSize: Optional[int] = ...) -> None: ...

class msgPushBatteryInfo(_message.Message):
    __slots__ = ["SOH", "autoCharge", "charging", "current", "cycle", "extra", "lastFullChargeStamp", "level", "manualCharge", "maxChargeCurrent", "maxChargeVoltage", "needFullCharge", "temperature", "userData", "voltage"]
    AUTOCHARGE_FIELD_NUMBER: ClassVar[int]
    CHARGING_FIELD_NUMBER: ClassVar[int]
    CURRENT_FIELD_NUMBER: ClassVar[int]
    CYCLE_FIELD_NUMBER: ClassVar[int]
    EXTRA_FIELD_NUMBER: ClassVar[int]
    LASTFULLCHARGESTAMP_FIELD_NUMBER: ClassVar[int]
    LEVEL_FIELD_NUMBER: ClassVar[int]
    MANUALCHARGE_FIELD_NUMBER: ClassVar[int]
    MAXCHARGECURRENT_FIELD_NUMBER: ClassVar[int]
    MAXCHARGEVOLTAGE_FIELD_NUMBER: ClassVar[int]
    NEEDFULLCHARGE_FIELD_NUMBER: ClassVar[int]
    SOH: int
    SOH_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    USERDATA_FIELD_NUMBER: ClassVar[int]
    VOLTAGE_FIELD_NUMBER: ClassVar[int]
    autoCharge: bool
    charging: bool
    current: float
    cycle: int
    extra: str
    lastFullChargeStamp: int
    level: float
    manualCharge: bool
    maxChargeCurrent: float
    maxChargeVoltage: float
    needFullCharge: bool
    temperature: float
    userData: bytes
    voltage: float
    def __init__(self, level: Optional[float] = ..., temperature: Optional[float] = ..., userData: Optional[bytes] = ..., charging: bool = ..., voltage: Optional[float] = ..., current: Optional[float] = ..., maxChargeVoltage: Optional[float] = ..., maxChargeCurrent: Optional[float] = ..., cycle: Optional[int] = ..., manualCharge: bool = ..., autoCharge: bool = ..., extra: Optional[str] = ..., SOH: Optional[int] = ..., needFullCharge: bool = ..., lastFullChargeStamp: Optional[int] = ...) -> None: ...

class msgPushCalibStatus(_message.Message):
    __slots__ = ["calibTypes", "desc", "status"]
    class calibStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CALIBTYPES_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    calibTypes: _containers.RepeatedCompositeFieldContainer[_message_calibstatus_pb2.msgCalibType]
    completed: msgPushCalibStatus.calibStatus
    desc: str
    failed: msgPushCalibStatus.calibStatus
    none: msgPushCalibStatus.calibStatus
    running: msgPushCalibStatus.calibStatus
    status: msgPushCalibStatus.calibStatus
    waiting: msgPushCalibStatus.calibStatus
    def __init__(self, status: Optional[Union[msgPushCalibStatus.calibStatus, str]] = ..., desc: Optional[str] = ..., calibTypes: Optional[Iterable[Union[_message_calibstatus_pb2.msgCalibType, Mapping]]] = ...) -> None: ...

class msgPushChassisInfo(_message.Message):
    __slots__ = ["isStop", "vx", "vxCommand", "vy", "vyCommand", "w", "wCommand"]
    ISSTOP_FIELD_NUMBER: ClassVar[int]
    VXCOMMAND_FIELD_NUMBER: ClassVar[int]
    VX_FIELD_NUMBER: ClassVar[int]
    VYCOMMAND_FIELD_NUMBER: ClassVar[int]
    VY_FIELD_NUMBER: ClassVar[int]
    WCOMMAND_FIELD_NUMBER: ClassVar[int]
    W_FIELD_NUMBER: ClassVar[int]
    isStop: bool
    vx: float
    vxCommand: float
    vy: float
    vyCommand: float
    w: float
    wCommand: float
    def __init__(self, vx: Optional[float] = ..., vy: Optional[float] = ..., w: Optional[float] = ..., vxCommand: Optional[float] = ..., vyCommand: Optional[float] = ..., wCommand: Optional[float] = ..., isStop: bool = ...) -> None: ...

class msgPushCodeScannerInfoItem(_message.Message):
    __slots__ = ["coordinate", "func", "isUpside", "key", "pitch", "roll", "x", "y", "yaw", "z"]
    COORDINATE_FIELD_NUMBER: ClassVar[int]
    FUNC_FIELD_NUMBER: ClassVar[int]
    ISUPSIDE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    PITCH_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, key: Optional[str] = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., yaw: Optional[float] = ..., pitch: Optional[float] = ..., roll: Optional[float] = ..., func: Optional[str] = ..., coordinate: Optional[str] = ..., isUpside: bool = ...) -> None: ...

class msgPushCodeScannerItem(_message.Message):
    __slots__ = ["codeScannerInfo", "errorCode", "isBarCode", "isDMTDetected", "tagDiffAngle", "tagDiffX", "tagDiffY", "tagValue", "warningCode"]
    CODESCANNERINFO_FIELD_NUMBER: ClassVar[int]
    ERRORCODE_FIELD_NUMBER: ClassVar[int]
    ISBARCODE_FIELD_NUMBER: ClassVar[int]
    ISDMTDETECTED_FIELD_NUMBER: ClassVar[int]
    TAGDIFFANGLE_FIELD_NUMBER: ClassVar[int]
    TAGDIFFX_FIELD_NUMBER: ClassVar[int]
    TAGDIFFY_FIELD_NUMBER: ClassVar[int]
    TAGVALUE_FIELD_NUMBER: ClassVar[int]
    WARNINGCODE_FIELD_NUMBER: ClassVar[int]
    codeScannerInfo: msgPushCodeScannerInfoItem
    errorCode: int
    isBarCode: bool
    isDMTDetected: bool
    tagDiffAngle: float
    tagDiffX: float
    tagDiffY: float
    tagValue: int
    warningCode: int
    def __init__(self, tagDiffX: Optional[float] = ..., tagDiffY: Optional[float] = ..., tagDiffAngle: Optional[float] = ..., tagValue: Optional[int] = ..., warningCode: Optional[int] = ..., isDMTDetected: bool = ..., errorCode: Optional[int] = ..., codeScannerInfo: Optional[Union[msgPushCodeScannerInfoItem, Mapping]] = ..., isBarCode: bool = ...) -> None: ...

class msgPushControlHistoryItem(_message.Message):
    __slots__ = ["desc", "ip", "nickname", "port", "timeT", "timeTUnlock", "type"]
    DESC_FIELD_NUMBER: ClassVar[int]
    IP_FIELD_NUMBER: ClassVar[int]
    NICKNAME_FIELD_NUMBER: ClassVar[int]
    PORT_FIELD_NUMBER: ClassVar[int]
    TIMETUNLOCK_FIELD_NUMBER: ClassVar[int]
    TIMET_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    desc: str
    ip: str
    nickname: str
    port: int
    timeT: int
    timeTUnlock: int
    type: int
    def __init__(self, ip: Optional[str] = ..., port: Optional[int] = ..., type: Optional[int] = ..., nickname: Optional[str] = ..., timeT: Optional[int] = ..., desc: Optional[str] = ..., timeTUnlock: Optional[int] = ...) -> None: ...

class msgPushControlInfo(_message.Message):
    __slots__ = ["desc", "ip", "locked", "nickname", "port", "srcRelease", "timeT", "type"]
    DESC_FIELD_NUMBER: ClassVar[int]
    IP_FIELD_NUMBER: ClassVar[int]
    LOCKED_FIELD_NUMBER: ClassVar[int]
    NICKNAME_FIELD_NUMBER: ClassVar[int]
    PORT_FIELD_NUMBER: ClassVar[int]
    SRCRELEASE_FIELD_NUMBER: ClassVar[int]
    TIMET_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    desc: str
    ip: str
    locked: bool
    nickname: str
    port: int
    srcRelease: bool
    timeT: int
    type: int
    def __init__(self, locked: bool = ..., ip: Optional[str] = ..., port: Optional[int] = ..., type: Optional[int] = ..., nickname: Optional[str] = ..., timeT: Optional[int] = ..., desc: Optional[str] = ..., srcRelease: bool = ...) -> None: ...

class msgPushControllerInfo(_message.Message):
    __slots__ = ["driverEmc", "electric", "emergency", "humidity", "softEmc", "temperature", "voltage"]
    DRIVEREMC_FIELD_NUMBER: ClassVar[int]
    ELECTRIC_FIELD_NUMBER: ClassVar[int]
    EMERGENCY_FIELD_NUMBER: ClassVar[int]
    HUMIDITY_FIELD_NUMBER: ClassVar[int]
    SOFTEMC_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    VOLTAGE_FIELD_NUMBER: ClassVar[int]
    driverEmc: bool
    electric: bool
    emergency: bool
    humidity: float
    softEmc: bool
    temperature: float
    voltage: float
    def __init__(self, temperature: Optional[float] = ..., humidity: Optional[float] = ..., voltage: Optional[float] = ..., emergency: bool = ..., driverEmc: bool = ..., electric: bool = ..., softEmc: bool = ...) -> None: ...

class msgPushDIInfo(_message.Message):
    __slots__ = ["diMaxNode", "node"]
    DIMAXNODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    diMaxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgPushDINodeItem]
    def __init__(self, node: Optional[Iterable[Union[msgPushDINodeItem, Mapping]]] = ..., diMaxNode: Optional[int] = ...) -> None: ...

class msgPushDINodeItem(_message.Message):
    __slots__ = ["forbidden", "id", "ioType", "key", "name", "status"]
    FORBIDDEN_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    IOTYPE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    NAME_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    forbidden: bool
    id: int
    ioType: int
    key: str
    name: str
    status: int
    def __init__(self, id: Optional[int] = ..., status: Optional[int] = ..., forbidden: bool = ..., ioType: Optional[int] = ..., key: Optional[str] = ..., name: Optional[str] = ...) -> None: ...

class msgPushDOInfo(_message.Message):
    __slots__ = ["doMaxNode", "node"]
    DOMAXNODE_FIELD_NUMBER: ClassVar[int]
    NODE_FIELD_NUMBER: ClassVar[int]
    doMaxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgPushDONodeItem]
    def __init__(self, node: Optional[Iterable[Union[msgPushDONodeItem, Mapping]]] = ..., doMaxNode: Optional[int] = ...) -> None: ...

class msgPushDONodeItem(_message.Message):
    __slots__ = ["id", "ioType", "key", "lock", "name", "status"]
    ID_FIELD_NUMBER: ClassVar[int]
    IOTYPE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    LOCK_FIELD_NUMBER: ClassVar[int]
    NAME_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    id: int
    ioType: int
    key: str
    lock: bool
    name: str
    status: int
    def __init__(self, id: Optional[int] = ..., status: Optional[int] = ..., ioType: Optional[int] = ..., lock: bool = ..., key: Optional[str] = ..., name: Optional[str] = ...) -> None: ...

class msgPushFunctionalSafetyInfo(_message.Message):
    __slots__ = ["ossdRegion", "safeCuttingsId"]
    OSSDREGION_FIELD_NUMBER: ClassVar[int]
    SAFECUTTINGSID_FIELD_NUMBER: ClassVar[int]
    ossdRegion: int
    safeCuttingsId: int
    def __init__(self, safeCuttingsId: Optional[int] = ..., ossdRegion: Optional[int] = ...) -> None: ...

class msgPushImuHeader(_message.Message):
    __slots__ = ["dataNsec", "frameID", "pubNsec", "seq"]
    DATANSEC_FIELD_NUMBER: ClassVar[int]
    FRAMEID_FIELD_NUMBER: ClassVar[int]
    PUBNSEC_FIELD_NUMBER: ClassVar[int]
    SEQ_FIELD_NUMBER: ClassVar[int]
    dataNsec: int
    frameID: str
    pubNsec: int
    seq: int
    def __init__(self, pubNsec: Optional[int] = ..., dataNsec: Optional[int] = ..., seq: Optional[int] = ..., frameID: Optional[str] = ...) -> None: ...

class msgPushImuInfo(_message.Message):
    __slots__ = ["accX", "accY", "accZ", "imuHeader", "pitch", "qw", "qx", "qy", "qz", "roll", "rotOffX", "rotOffY", "rotOffZ", "rotX", "rotY", "rotZ", "yaw"]
    ACCX_FIELD_NUMBER: ClassVar[int]
    ACCY_FIELD_NUMBER: ClassVar[int]
    ACCZ_FIELD_NUMBER: ClassVar[int]
    IMUHEADER_FIELD_NUMBER: ClassVar[int]
    PITCH_FIELD_NUMBER: ClassVar[int]
    QW_FIELD_NUMBER: ClassVar[int]
    QX_FIELD_NUMBER: ClassVar[int]
    QY_FIELD_NUMBER: ClassVar[int]
    QZ_FIELD_NUMBER: ClassVar[int]
    ROLL_FIELD_NUMBER: ClassVar[int]
    ROTOFFX_FIELD_NUMBER: ClassVar[int]
    ROTOFFY_FIELD_NUMBER: ClassVar[int]
    ROTOFFZ_FIELD_NUMBER: ClassVar[int]
    ROTX_FIELD_NUMBER: ClassVar[int]
    ROTY_FIELD_NUMBER: ClassVar[int]
    ROTZ_FIELD_NUMBER: ClassVar[int]
    YAW_FIELD_NUMBER: ClassVar[int]
    accX: float
    accY: float
    accZ: float
    imuHeader: msgPushImuHeader
    pitch: float
    qw: float
    qx: float
    qy: float
    qz: float
    roll: float
    rotOffX: float
    rotOffY: float
    rotOffZ: float
    rotX: float
    rotY: float
    rotZ: float
    yaw: float
    def __init__(self, imuHeader: Optional[Union[msgPushImuHeader, Mapping]] = ..., yaw: Optional[float] = ..., roll: Optional[float] = ..., pitch: Optional[float] = ..., accX: Optional[float] = ..., accY: Optional[float] = ..., accZ: Optional[float] = ..., rotX: Optional[float] = ..., rotY: Optional[float] = ..., rotZ: Optional[float] = ..., rotOffX: Optional[float] = ..., rotOffY: Optional[float] = ..., rotOffZ: Optional[float] = ..., qx: Optional[float] = ..., qy: Optional[float] = ..., qz: Optional[float] = ..., qw: Optional[float] = ...) -> None: ...

class msgPushLocalTag(_message.Message):
    __slots__ = ["angle", "confidence", "distanceNotFindTag", "groupName", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: ClassVar[int]
    DISTANCENOTFINDTAG_FIELD_NUMBER: ClassVar[int]
    GROUPNAME_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    confidence: float
    distanceNotFindTag: float
    groupName: str
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ..., confidence: Optional[float] = ..., distanceNotFindTag: Optional[float] = ..., groupName: Optional[str] = ...) -> None: ...

class msgPushLocationInfo(_message.Message):
    __slots__ = ["angle", "areaIds", "confidence", "currentStation", "errors", "lastStation", "locNotify", "localTag", "method", "relocStatus", "x", "y"]
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: Optional[str] = ..., value: Optional[Union[_message_error_pb2.msgError, Mapping]] = ...) -> None: ...
    ANGLE_FIELD_NUMBER: ClassVar[int]
    AREAIDS_FIELD_NUMBER: ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: ClassVar[int]
    CURRENTSTATION_FIELD_NUMBER: ClassVar[int]
    ERRORS_FIELD_NUMBER: ClassVar[int]
    LASTSTATION_FIELD_NUMBER: ClassVar[int]
    LOCALTAG_FIELD_NUMBER: ClassVar[int]
    LOCNOTIFY_FIELD_NUMBER: ClassVar[int]
    METHOD_FIELD_NUMBER: ClassVar[int]
    RELOCSTATUS_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    areaIds: _containers.RepeatedScalarFieldContainer[str]
    confidence: float
    currentStation: str
    errors: _containers.MessageMap[str, _message_error_pb2.msgError]
    lastStation: str
    locNotify: str
    localTag: msgPushLocalTag
    method: int
    relocStatus: int
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ..., confidence: Optional[float] = ..., method: Optional[int] = ..., locNotify: Optional[str] = ..., currentStation: Optional[str] = ..., areaIds: Optional[Iterable[str]] = ..., lastStation: Optional[str] = ..., relocStatus: Optional[int] = ..., localTag: Optional[Union[msgPushLocalTag, Mapping]] = ..., errors: Optional[Mapping[str, _message_error_pb2.msgError]] = ...) -> None: ...

class msgPushMapInfo(_message.Message):
    __slots__ = ["currentMap", "currentMapEntries", "currentMapMd5", "currentTopoMd5", "loadMapStatus"]
    CURRENTMAPENTRIES_FIELD_NUMBER: ClassVar[int]
    CURRENTMAPMD5_FIELD_NUMBER: ClassVar[int]
    CURRENTMAP_FIELD_NUMBER: ClassVar[int]
    CURRENTTOPOMD5_FIELD_NUMBER: ClassVar[int]
    LOADMAPSTATUS_FIELD_NUMBER: ClassVar[int]
    currentMap: str
    currentMapEntries: _containers.RepeatedCompositeFieldContainer[_message_map_pb2.msgMapFileMd5]
    currentMapMd5: str
    currentTopoMd5: str
    loadMapStatus: int
    def __init__(self, currentMap: Optional[str] = ..., currentMapEntries: Optional[Iterable[Union[_message_map_pb2.msgMapFileMd5, Mapping]]] = ..., currentMapMd5: Optional[str] = ..., currentTopoMd5: Optional[str] = ..., loadMapStatus: Optional[int] = ...) -> None: ...

class msgPushMappingInfo(_message.Message):
    __slots__ = ["slamStatus"]
    SLAMSTATUS_FIELD_NUMBER: ClassVar[int]
    slamStatus: int
    def __init__(self, slamStatus: Optional[int] = ...) -> None: ...

class msgPushMotorInfo(_message.Message):
    __slots__ = ["motorInfo", "motorMotion"]
    MOTORINFO_FIELD_NUMBER: ClassVar[int]
    MOTORMOTION_FIELD_NUMBER: ClassVar[int]
    motorInfo: _containers.RepeatedCompositeFieldContainer[msgPushMotorInfoItem]
    motorMotion: msgPushMotorMotionInfo
    def __init__(self, motorMotion: Optional[Union[msgPushMotorMotionInfo, Mapping]] = ..., motorInfo: Optional[Iterable[Union[msgPushMotorInfoItem, Mapping]]] = ...) -> None: ...

class msgPushMotorInfoItem(_message.Message):
    __slots__ = ["calib", "canId", "canRouter", "current", "emc", "encoder", "err", "errorCode", "followErr", "key", "passive", "position", "rawPosition", "speed", "stop", "temperature", "torque", "type", "voltage"]
    CALIB_FIELD_NUMBER: ClassVar[int]
    CANID_FIELD_NUMBER: ClassVar[int]
    CANROUTER_FIELD_NUMBER: ClassVar[int]
    CURRENT_FIELD_NUMBER: ClassVar[int]
    EMC_FIELD_NUMBER: ClassVar[int]
    ENCODER_FIELD_NUMBER: ClassVar[int]
    ERRORCODE_FIELD_NUMBER: ClassVar[int]
    ERR_FIELD_NUMBER: ClassVar[int]
    FOLLOWERR_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    PASSIVE_FIELD_NUMBER: ClassVar[int]
    POSITION_FIELD_NUMBER: ClassVar[int]
    RAWPOSITION_FIELD_NUMBER: ClassVar[int]
    SPEED_FIELD_NUMBER: ClassVar[int]
    STOP_FIELD_NUMBER: ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: ClassVar[int]
    TORQUE_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    VOLTAGE_FIELD_NUMBER: ClassVar[int]
    calib: bool
    canId: int
    canRouter: int
    current: float
    emc: bool
    encoder: int
    err: bool
    errorCode: int
    followErr: float
    key: str
    passive: bool
    position: float
    rawPosition: float
    speed: float
    stop: bool
    temperature: float
    torque: float
    type: int
    voltage: float
    def __init__(self, key: Optional[str] = ..., canRouter: Optional[int] = ..., canId: Optional[int] = ..., position: Optional[float] = ..., rawPosition: Optional[float] = ..., speed: Optional[float] = ..., current: Optional[float] = ..., voltage: Optional[float] = ..., stop: bool = ..., errorCode: Optional[int] = ..., err: bool = ..., emc: bool = ..., temperature: Optional[float] = ..., encoder: Optional[int] = ..., type: Optional[int] = ..., passive: bool = ..., calib: bool = ..., followErr: Optional[float] = ..., torque: Optional[float] = ...) -> None: ...

class msgPushMotorMotionInfo(_message.Message):
    __slots__ = ["isStop", "motorSteerAngles", "spinAngle", "spinVelocityCommand", "steerAngle", "steerAngleCommand", "steerAngles", "steerAnglesCommand"]
    ISSTOP_FIELD_NUMBER: ClassVar[int]
    MOTORSTEERANGLES_FIELD_NUMBER: ClassVar[int]
    SPINANGLE_FIELD_NUMBER: ClassVar[int]
    SPINVELOCITYCOMMAND_FIELD_NUMBER: ClassVar[int]
    STEERANGLECOMMAND_FIELD_NUMBER: ClassVar[int]
    STEERANGLESCOMMAND_FIELD_NUMBER: ClassVar[int]
    STEERANGLES_FIELD_NUMBER: ClassVar[int]
    STEERANGLE_FIELD_NUMBER: ClassVar[int]
    isStop: bool
    motorSteerAngles: _containers.RepeatedCompositeFieldContainer[msgPushMotorSteerAngleItem]
    spinAngle: float
    spinVelocityCommand: float
    steerAngle: float
    steerAngleCommand: float
    steerAngles: _containers.RepeatedScalarFieldContainer[float]
    steerAnglesCommand: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, steerAngle: Optional[float] = ..., spinAngle: Optional[float] = ..., steerAngleCommand: Optional[float] = ..., spinVelocityCommand: Optional[float] = ..., steerAngles: Optional[Iterable[float]] = ..., steerAnglesCommand: Optional[Iterable[float]] = ..., motorSteerAngles: Optional[Iterable[Union[msgPushMotorSteerAngleItem, Mapping]]] = ..., isStop: bool = ...) -> None: ...

class msgPushMotorSteerAngleItem(_message.Message):
    __slots__ = ["motorKey", "value"]
    MOTORKEY_FIELD_NUMBER: ClassVar[int]
    VALUE_FIELD_NUMBER: ClassVar[int]
    motorKey: str
    value: float
    def __init__(self, motorKey: Optional[str] = ..., value: Optional[float] = ...) -> None: ...

class msgPushNavigationInfo(_message.Message):
    __slots__ = ["errors", "finishedPath", "mates", "moveStatusInfo", "multiPath", "runningStatus", "targetDist", "targetId", "targetLabel", "targetPoint", "taskId", "taskStatus", "taskStatusPackage", "type", "unfinishedPath"]
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: Optional[str] = ..., value: Optional[Union[_message_error_pb2.msgError, Mapping]] = ...) -> None: ...
    ERRORS_FIELD_NUMBER: ClassVar[int]
    FINISHEDPATH_FIELD_NUMBER: ClassVar[int]
    MATES_FIELD_NUMBER: ClassVar[int]
    MOVESTATUSINFO_FIELD_NUMBER: ClassVar[int]
    MULTIPATH_FIELD_NUMBER: ClassVar[int]
    RUNNINGSTATUS_FIELD_NUMBER: ClassVar[int]
    TARGETDIST_FIELD_NUMBER: ClassVar[int]
    TARGETID_FIELD_NUMBER: ClassVar[int]
    TARGETLABEL_FIELD_NUMBER: ClassVar[int]
    TARGETPOINT_FIELD_NUMBER: ClassVar[int]
    TASKID_FIELD_NUMBER: ClassVar[int]
    TASKSTATUSPACKAGE_FIELD_NUMBER: ClassVar[int]
    TASKSTATUS_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    UNFINISHEDPATH_FIELD_NUMBER: ClassVar[int]
    errors: _containers.MessageMap[str, _message_error_pb2.msgError]
    finishedPath: _containers.RepeatedScalarFieldContainer[str]
    mates: str
    moveStatusInfo: str
    multiPath: _containers.RepeatedCompositeFieldContainer[_struct_pb2.ListValue]
    runningStatus: int
    targetDist: float
    targetId: str
    targetLabel: str
    targetPoint: _containers.RepeatedScalarFieldContainer[float]
    taskId: str
    taskStatus: int
    taskStatusPackage: _struct_pb2.Struct
    type: int
    unfinishedPath: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, taskId: Optional[str] = ..., taskStatus: Optional[int] = ..., runningStatus: Optional[int] = ..., type: Optional[int] = ..., targetDist: Optional[float] = ..., moveStatusInfo: Optional[str] = ..., targetId: Optional[str] = ..., targetLabel: Optional[str] = ..., targetPoint: Optional[Iterable[float]] = ..., multiPath: Optional[Iterable[Union[_struct_pb2.ListValue, Mapping]]] = ..., finishedPath: Optional[Iterable[str]] = ..., unfinishedPath: Optional[Iterable[str]] = ..., mates: Optional[str] = ..., taskStatusPackage: Optional[Union[_struct_pb2.Struct, Mapping]] = ..., errors: Optional[Mapping[str, _message_error_pb2.msgError]] = ...) -> None: ...

class msgPushNetworkInfo(_message.Message):
    __slots__ = ["apAddr", "ip", "mac", "rssi", "ssid", "wlanMac"]
    APADDR_FIELD_NUMBER: ClassVar[int]
    IP_FIELD_NUMBER: ClassVar[int]
    MAC_FIELD_NUMBER: ClassVar[int]
    RSSI_FIELD_NUMBER: ClassVar[int]
    SSID_FIELD_NUMBER: ClassVar[int]
    WLANMAC_FIELD_NUMBER: ClassVar[int]
    apAddr: str
    ip: str
    mac: str
    rssi: int
    ssid: str
    wlanMac: str
    def __init__(self, ssid: Optional[str] = ..., rssi: Optional[int] = ..., apAddr: Optional[str] = ..., ip: Optional[str] = ..., wlanMac: Optional[str] = ..., mac: Optional[str] = ...) -> None: ...

class msgPushObstacleInfo(_message.Message):
    __slots__ = ["blockDevice", "blockReason", "blockX", "blockY", "blocked", "nearestObstacles", "slowDevice", "slowReason", "slowX", "slowY", "slowed"]
    BLOCKDEVICE_FIELD_NUMBER: ClassVar[int]
    BLOCKED_FIELD_NUMBER: ClassVar[int]
    BLOCKREASON_FIELD_NUMBER: ClassVar[int]
    BLOCKX_FIELD_NUMBER: ClassVar[int]
    BLOCKY_FIELD_NUMBER: ClassVar[int]
    NEARESTOBSTACLES_FIELD_NUMBER: ClassVar[int]
    SLOWDEVICE_FIELD_NUMBER: ClassVar[int]
    SLOWED_FIELD_NUMBER: ClassVar[int]
    SLOWREASON_FIELD_NUMBER: ClassVar[int]
    SLOWX_FIELD_NUMBER: ClassVar[int]
    SLOWY_FIELD_NUMBER: ClassVar[int]
    blockDevice: str
    blockReason: int
    blockX: float
    blockY: float
    blocked: bool
    nearestObstacles: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    slowDevice: str
    slowReason: int
    slowX: float
    slowY: float
    slowed: bool
    def __init__(self, blocked: bool = ..., blockX: Optional[float] = ..., blockY: Optional[float] = ..., blockReason: Optional[int] = ..., blockDevice: Optional[str] = ..., slowed: bool = ..., slowX: Optional[float] = ..., slowY: Optional[float] = ..., slowReason: Optional[int] = ..., slowDevice: Optional[str] = ..., nearestObstacles: Optional[Iterable[Union[_struct_pb2.Struct, Mapping]]] = ...) -> None: ...

class msgPushRobotInfo(_message.Message):
    __slots__ = ["appMd5", "architecture", "chassisType", "codeId", "deviceParamMd5", "deviceParamVersion", "dnnModelVersion", "dspVersion", "echoid", "errors", "features", "fleetControl", "gyroVersion", "id", "mapVersion", "modbusVersion", "model", "modelName", "netprotocolVersion", "product", "pyideVersion", "roboshopMinVersionRequired", "robotNote", "simulation", "srcName", "systemStatus", "taskRunnerVersion", "vehicleId", "version", "versionList"]
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: Optional[str] = ..., value: Optional[Union[_message_error_pb2.msgError, Mapping]] = ...) -> None: ...
    APPMD5_FIELD_NUMBER: ClassVar[int]
    ARCHITECTURE_FIELD_NUMBER: ClassVar[int]
    CHASSISTYPE_FIELD_NUMBER: ClassVar[int]
    CODEID_FIELD_NUMBER: ClassVar[int]
    DEVICEPARAMMD5_FIELD_NUMBER: ClassVar[int]
    DEVICEPARAMVERSION_FIELD_NUMBER: ClassVar[int]
    DNNMODELVERSION_FIELD_NUMBER: ClassVar[int]
    DSPVERSION_FIELD_NUMBER: ClassVar[int]
    ECHOID_FIELD_NUMBER: ClassVar[int]
    ERRORS_FIELD_NUMBER: ClassVar[int]
    FEATURES_FIELD_NUMBER: ClassVar[int]
    FLEETCONTROL_FIELD_NUMBER: ClassVar[int]
    GYROVERSION_FIELD_NUMBER: ClassVar[int]
    ID_FIELD_NUMBER: ClassVar[int]
    MAPVERSION_FIELD_NUMBER: ClassVar[int]
    MODBUSVERSION_FIELD_NUMBER: ClassVar[int]
    MODELNAME_FIELD_NUMBER: ClassVar[int]
    MODEL_FIELD_NUMBER: ClassVar[int]
    NETPROTOCOLVERSION_FIELD_NUMBER: ClassVar[int]
    PRODUCT_FIELD_NUMBER: ClassVar[int]
    PYIDEVERSION_FIELD_NUMBER: ClassVar[int]
    ROBOSHOPMINVERSIONREQUIRED_FIELD_NUMBER: ClassVar[int]
    ROBOTNOTE_FIELD_NUMBER: ClassVar[int]
    SIMULATION_FIELD_NUMBER: ClassVar[int]
    SRCNAME_FIELD_NUMBER: ClassVar[int]
    SYSTEMSTATUS_FIELD_NUMBER: ClassVar[int]
    TASKRUNNERVERSION_FIELD_NUMBER: ClassVar[int]
    VEHICLEID_FIELD_NUMBER: ClassVar[int]
    VERSIONLIST_FIELD_NUMBER: ClassVar[int]
    VERSION_FIELD_NUMBER: ClassVar[int]
    appMd5: str
    architecture: str
    chassisType: str
    codeId: str
    deviceParamMd5: str
    deviceParamVersion: str
    dnnModelVersion: str
    dspVersion: str
    echoid: str
    errors: _containers.MessageMap[str, _message_error_pb2.msgError]
    features: _struct_pb2.Value
    fleetControl: bool
    gyroVersion: str
    id: str
    mapVersion: str
    modbusVersion: str
    model: str
    modelName: str
    netprotocolVersion: str
    product: str
    pyideVersion: str
    roboshopMinVersionRequired: str
    robotNote: str
    simulation: bool
    srcName: str
    systemStatus: int
    taskRunnerVersion: str
    vehicleId: str
    version: str
    versionList: _struct_pb2.Struct
    def __init__(self, id: Optional[str] = ..., fleetControl: bool = ..., codeId: Optional[str] = ..., simulation: bool = ..., echoid: Optional[str] = ..., features: Optional[Union[_struct_pb2.Value, Mapping]] = ..., vehicleId: Optional[str] = ..., robotNote: Optional[str] = ..., version: Optional[str] = ..., product: Optional[str] = ..., model: Optional[str] = ..., modelName: Optional[str] = ..., deviceParamMd5: Optional[str] = ..., appMd5: Optional[str] = ..., chassisType: Optional[str] = ..., dspVersion: Optional[str] = ..., gyroVersion: Optional[str] = ..., pyideVersion: Optional[str] = ..., taskRunnerVersion: Optional[str] = ..., versionList: Optional[Union[_struct_pb2.Struct, Mapping]] = ..., deviceParamVersion: Optional[str] = ..., mapVersion: Optional[str] = ..., roboshopMinVersionRequired: Optional[str] = ..., netprotocolVersion: Optional[str] = ..., dnnModelVersion: Optional[str] = ..., modbusVersion: Optional[str] = ..., srcName: Optional[str] = ..., architecture: Optional[str] = ..., systemStatus: Optional[int] = ..., errors: Optional[Mapping[str, _message_error_pb2.msgError]] = ...) -> None: ...

class msgPushRobotShapeInfo(_message.Message):
    __slots__ = ["head", "radius", "shape", "tail", "width"]
    HEAD_FIELD_NUMBER: ClassVar[int]
    RADIUS_FIELD_NUMBER: ClassVar[int]
    SHAPE_FIELD_NUMBER: ClassVar[int]
    TAIL_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    head: float
    radius: float
    shape: int
    tail: float
    width: float
    def __init__(self, shape: Optional[int] = ..., head: Optional[float] = ..., tail: Optional[float] = ..., width: Optional[float] = ..., radius: Optional[float] = ...) -> None: ...

class msgPushSoundInfo(_message.Message):
    __slots__ = ["count", "loop", "soundName", "status"]
    COUNT_FIELD_NUMBER: ClassVar[int]
    LOOP_FIELD_NUMBER: ClassVar[int]
    SOUNDNAME_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
    count: int
    loop: bool
    soundName: str
    status: int
    def __init__(self, status: Optional[int] = ..., soundName: Optional[str] = ..., loop: bool = ..., count: Optional[int] = ...) -> None: ...

class msgState(_message.Message):
    __slots__ = ["abnormal", "battery", "calibStatus", "chassis", "codeScanners", "control", "controlHistory", "controller", "deviceStatus", "di", "do", "dynamicObstacle", "functionalSafety", "gnss", "goodsRegion", "imu", "ioConfig", "location", "map", "mapping", "motor", "movePolygon", "navigation", "network", "obstacle", "rfids", "robot", "robotShape", "sound", "stats", "taskRunner"]
    class DeviceStatusEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: ClassVar[int]
        VALUE_FIELD_NUMBER: ClassVar[int]
        key: str
        value: _message_devicestatus_pb2.msgDeviceStatusNode
        def __init__(self, key: Optional[str] = ..., value: Optional[Union[_message_devicestatus_pb2.msgDeviceStatusNode, Mapping]] = ...) -> None: ...
    ABNORMAL_FIELD_NUMBER: ClassVar[int]
    BATTERY_FIELD_NUMBER: ClassVar[int]
    CALIBSTATUS_FIELD_NUMBER: ClassVar[int]
    CHASSIS_FIELD_NUMBER: ClassVar[int]
    CODESCANNERS_FIELD_NUMBER: ClassVar[int]
    CONTROLHISTORY_FIELD_NUMBER: ClassVar[int]
    CONTROLLER_FIELD_NUMBER: ClassVar[int]
    CONTROL_FIELD_NUMBER: ClassVar[int]
    DEVICESTATUS_FIELD_NUMBER: ClassVar[int]
    DI_FIELD_NUMBER: ClassVar[int]
    DO_FIELD_NUMBER: ClassVar[int]
    DYNAMICOBSTACLE_FIELD_NUMBER: ClassVar[int]
    FUNCTIONALSAFETY_FIELD_NUMBER: ClassVar[int]
    GNSS_FIELD_NUMBER: ClassVar[int]
    GOODSREGION_FIELD_NUMBER: ClassVar[int]
    IMU_FIELD_NUMBER: ClassVar[int]
    IOCONFIG_FIELD_NUMBER: ClassVar[int]
    LOCATION_FIELD_NUMBER: ClassVar[int]
    MAPPING_FIELD_NUMBER: ClassVar[int]
    MAP_FIELD_NUMBER: ClassVar[int]
    MOTOR_FIELD_NUMBER: ClassVar[int]
    MOVEPOLYGON_FIELD_NUMBER: ClassVar[int]
    NAVIGATION_FIELD_NUMBER: ClassVar[int]
    NETWORK_FIELD_NUMBER: ClassVar[int]
    OBSTACLE_FIELD_NUMBER: ClassVar[int]
    RFIDS_FIELD_NUMBER: ClassVar[int]
    ROBOTSHAPE_FIELD_NUMBER: ClassVar[int]
    ROBOT_FIELD_NUMBER: ClassVar[int]
    SOUND_FIELD_NUMBER: ClassVar[int]
    STATS_FIELD_NUMBER: ClassVar[int]
    TASKRUNNER_FIELD_NUMBER: ClassVar[int]
    abnormal: msgPushAbnormalInfo
    battery: msgPushBatteryInfo
    calibStatus: msgPushCalibStatus
    chassis: msgPushChassisInfo
    codeScanners: _containers.RepeatedCompositeFieldContainer[msgPushCodeScannerItem]
    control: msgPushControlInfo
    controlHistory: _containers.RepeatedCompositeFieldContainer[msgPushControlHistoryItem]
    controller: msgPushControllerInfo
    deviceStatus: _containers.MessageMap[str, _message_devicestatus_pb2.msgDeviceStatusNode]
    di: msgPushDIInfo
    do: msgPushDOInfo
    dynamicObstacle: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    functionalSafety: msgPushFunctionalSafetyInfo
    gnss: _message_gnss_pb2.msgGnss
    goodsRegion: _struct_pb2.Struct
    imu: msgPushImuInfo
    ioConfig: str
    location: msgPushLocationInfo
    map: msgPushMapInfo
    mapping: msgPushMappingInfo
    motor: msgPushMotorInfo
    movePolygon: _struct_pb2.Struct
    navigation: msgPushNavigationInfo
    network: msgPushNetworkInfo
    obstacle: msgPushObstacleInfo
    rfids: _containers.RepeatedScalarFieldContainer[int]
    robot: msgPushRobotInfo
    robotShape: msgPushRobotShapeInfo
    sound: msgPushSoundInfo
    stats: _struct_pb2.Struct
    taskRunner: str
    def __init__(self, stats: Optional[Union[_struct_pb2.Struct, Mapping]] = ..., controller: Optional[Union[msgPushControllerInfo, Mapping]] = ..., location: Optional[Union[msgPushLocationInfo, Mapping]] = ..., chassis: Optional[Union[msgPushChassisInfo, Mapping]] = ..., motor: Optional[Union[msgPushMotorInfo, Mapping]] = ..., obstacle: Optional[Union[msgPushObstacleInfo, Mapping]] = ..., battery: Optional[Union[msgPushBatteryInfo, Mapping]] = ..., di: Optional[Union[msgPushDIInfo, Mapping]] = ..., do: Optional[Union[msgPushDOInfo, Mapping]] = ..., ioConfig: Optional[str] = ..., navigation: Optional[Union[msgPushNavigationInfo, Mapping]] = ..., mapping: Optional[Union[msgPushMappingInfo, Mapping]] = ..., abnormal: Optional[Union[msgPushAbnormalInfo, Mapping]] = ..., map: Optional[Union[msgPushMapInfo, Mapping]] = ..., network: Optional[Union[msgPushNetworkInfo, Mapping]] = ..., robot: Optional[Union[msgPushRobotInfo, Mapping]] = ..., control: Optional[Union[msgPushControlInfo, Mapping]] = ..., controlHistory: Optional[Iterable[Union[msgPushControlHistoryItem, Mapping]]] = ..., robotShape: Optional[Union[msgPushRobotShapeInfo, Mapping]] = ..., sound: Optional[Union[msgPushSoundInfo, Mapping]] = ..., movePolygon: Optional[Union[_struct_pb2.Struct, Mapping]] = ..., imu: Optional[Union[msgPushImuInfo, Mapping]] = ..., functionalSafety: Optional[Union[msgPushFunctionalSafetyInfo, Mapping]] = ..., goodsRegion: Optional[Union[_struct_pb2.Struct, Mapping]] = ..., dynamicObstacle: Optional[Iterable[Union[_struct_pb2.Struct, Mapping]]] = ..., calibStatus: Optional[Union[msgPushCalibStatus, Mapping]] = ..., gnss: Optional[Union[_message_gnss_pb2.msgGnss, Mapping]] = ..., rfids: Optional[Iterable[int]] = ..., codeScanners: Optional[Iterable[Union[msgPushCodeScannerItem, Mapping]]] = ..., taskRunner: Optional[str] = ..., deviceStatus: Optional[Mapping[str, _message_devicestatus_pb2.msgDeviceStatusNode]] = ...) -> None: ...
