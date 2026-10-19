from . import message_calibstatus_pb2 as _message_calibstatus_pb2
from . import message_map_pb2 as _message_map_pb2
from . import message_gnss_pb2 as _message_gnss_pb2
from . import message_error_pb2 as _message_error_pb2
from . import message_devicestatus_pb2 as _message_devicestatus_pb2
from . import message_io_pb2 as _message_io_pb2
from . import message_movetask_pb2 as _message_movetask_pb2
from . import message_script_pb2 as _message_script_pb2
from . import message_motorinfos_pb2 as _message_motorinfos_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgJsonArray(_message.Message):
    __slots__ = ["value"]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: _containers.RepeatedCompositeFieldContainer[msgJsonValue]
    def __init__(self, value: _Optional[_Iterable[_Union[msgJsonValue, _Mapping]]] = ...) -> None: ...

class msgJsonObject(_message.Message):
    __slots__ = ["field"]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    field: _containers.RepeatedCompositeFieldContainer[msgJsonObjectField]
    def __init__(self, field: _Optional[_Iterable[_Union[msgJsonObjectField, _Mapping]]] = ...) -> None: ...

class msgJsonObjectField(_message.Message):
    __slots__ = ["key", "value"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: msgJsonValue
    def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[msgJsonValue, _Mapping]] = ...) -> None: ...

class msgJsonValue(_message.Message):
    __slots__ = ["arrayValue", "boolValue", "nullValue", "numberValue", "objectValue", "stringValue"]
    ARRAYVALUE_FIELD_NUMBER: _ClassVar[int]
    BOOLVALUE_FIELD_NUMBER: _ClassVar[int]
    NULLVALUE_FIELD_NUMBER: _ClassVar[int]
    NUMBERVALUE_FIELD_NUMBER: _ClassVar[int]
    OBJECTVALUE_FIELD_NUMBER: _ClassVar[int]
    STRINGVALUE_FIELD_NUMBER: _ClassVar[int]
    arrayValue: msgJsonArray
    boolValue: bool
    nullValue: bool
    numberValue: float
    objectValue: msgJsonObject
    stringValue: str
    def __init__(self, nullValue: bool = ..., numberValue: _Optional[float] = ..., stringValue: _Optional[str] = ..., boolValue: bool = ..., objectValue: _Optional[_Union[msgJsonObject, _Mapping]] = ..., arrayValue: _Optional[_Union[msgJsonArray, _Mapping]] = ...) -> None: ...

class msgPushAbnormalInfo(_message.Message):
    __slots__ = ["abnormalSize", "abnormals"]
    ABNORMALSIZE_FIELD_NUMBER: _ClassVar[int]
    ABNORMALS_FIELD_NUMBER: _ClassVar[int]
    abnormalSize: int
    abnormals: msgJsonObject
    def __init__(self, abnormals: _Optional[_Union[msgJsonObject, _Mapping]] = ..., abnormalSize: _Optional[int] = ...) -> None: ...

class msgPushBatteryInfo(_message.Message):
    __slots__ = ["SOH", "autoCharge", "charging", "current", "cycle", "extra", "lastFullChargeStamp", "level", "manualCharge", "maxChargeCurrent", "maxChargeVoltage", "needFullCharge", "temperature", "userData", "voltage"]
    AUTOCHARGE_FIELD_NUMBER: _ClassVar[int]
    CHARGING_FIELD_NUMBER: _ClassVar[int]
    CURRENT_FIELD_NUMBER: _ClassVar[int]
    CYCLE_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    LASTFULLCHARGESTAMP_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    MANUALCHARGE_FIELD_NUMBER: _ClassVar[int]
    MAXCHARGECURRENT_FIELD_NUMBER: _ClassVar[int]
    MAXCHARGEVOLTAGE_FIELD_NUMBER: _ClassVar[int]
    NEEDFULLCHARGE_FIELD_NUMBER: _ClassVar[int]
    SOH: int
    SOH_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    USERDATA_FIELD_NUMBER: _ClassVar[int]
    VOLTAGE_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, level: _Optional[float] = ..., temperature: _Optional[float] = ..., userData: _Optional[bytes] = ..., charging: bool = ..., voltage: _Optional[float] = ..., current: _Optional[float] = ..., maxChargeVoltage: _Optional[float] = ..., maxChargeCurrent: _Optional[float] = ..., cycle: _Optional[int] = ..., manualCharge: bool = ..., autoCharge: bool = ..., extra: _Optional[str] = ..., SOH: _Optional[int] = ..., needFullCharge: bool = ..., lastFullChargeStamp: _Optional[int] = ...) -> None: ...

class msgPushCalibStatus(_message.Message):
    __slots__ = ["calibTypes", "desc", "status"]
    class calibStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CALIBTYPES_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    calibTypes: _containers.RepeatedCompositeFieldContainer[_message_calibstatus_pb2.msgCalibType]
    completed: msgPushCalibStatus.calibStatus
    desc: str
    failed: msgPushCalibStatus.calibStatus
    none: msgPushCalibStatus.calibStatus
    running: msgPushCalibStatus.calibStatus
    status: int
    waiting: msgPushCalibStatus.calibStatus
    def __init__(self, status: _Optional[int] = ..., desc: _Optional[str] = ..., calibTypes: _Optional[_Iterable[_Union[_message_calibstatus_pb2.msgCalibType, _Mapping]]] = ...) -> None: ...

class msgPushChassisInfo(_message.Message):
    __slots__ = ["isStop", "vx", "vxCommand", "vy", "vyCommand", "w", "wCommand"]
    ISSTOP_FIELD_NUMBER: _ClassVar[int]
    VXCOMMAND_FIELD_NUMBER: _ClassVar[int]
    VX_FIELD_NUMBER: _ClassVar[int]
    VYCOMMAND_FIELD_NUMBER: _ClassVar[int]
    VY_FIELD_NUMBER: _ClassVar[int]
    WCOMMAND_FIELD_NUMBER: _ClassVar[int]
    W_FIELD_NUMBER: _ClassVar[int]
    isStop: bool
    vx: float
    vxCommand: float
    vy: float
    vyCommand: float
    w: float
    wCommand: float
    def __init__(self, vx: _Optional[float] = ..., vy: _Optional[float] = ..., w: _Optional[float] = ..., vxCommand: _Optional[float] = ..., vyCommand: _Optional[float] = ..., wCommand: _Optional[float] = ..., isStop: bool = ...) -> None: ...

class msgPushCodeScannerInfoItem(_message.Message):
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

class msgPushCodeScannerItem(_message.Message):
    __slots__ = ["codeScannerInfo", "errorCode", "isBarCode", "isDMTDetected", "tagDiffAngle", "tagDiffX", "tagDiffY", "tagValue", "warningCode"]
    CODESCANNERINFO_FIELD_NUMBER: _ClassVar[int]
    ERRORCODE_FIELD_NUMBER: _ClassVar[int]
    ISBARCODE_FIELD_NUMBER: _ClassVar[int]
    ISDMTDETECTED_FIELD_NUMBER: _ClassVar[int]
    TAGDIFFANGLE_FIELD_NUMBER: _ClassVar[int]
    TAGDIFFX_FIELD_NUMBER: _ClassVar[int]
    TAGDIFFY_FIELD_NUMBER: _ClassVar[int]
    TAGVALUE_FIELD_NUMBER: _ClassVar[int]
    WARNINGCODE_FIELD_NUMBER: _ClassVar[int]
    codeScannerInfo: msgPushCodeScannerInfoItem
    errorCode: int
    isBarCode: bool
    isDMTDetected: bool
    tagDiffAngle: float
    tagDiffX: float
    tagDiffY: float
    tagValue: int
    warningCode: int
    def __init__(self, tagDiffX: _Optional[float] = ..., tagDiffY: _Optional[float] = ..., tagDiffAngle: _Optional[float] = ..., tagValue: _Optional[int] = ..., warningCode: _Optional[int] = ..., isDMTDetected: bool = ..., errorCode: _Optional[int] = ..., codeScannerInfo: _Optional[_Union[msgPushCodeScannerInfoItem, _Mapping]] = ..., isBarCode: bool = ...) -> None: ...

class msgPushControlHistoryItem(_message.Message):
    __slots__ = ["desc", "ip", "nickname", "port", "timeT", "timeTUnlock", "type"]
    DESC_FIELD_NUMBER: _ClassVar[int]
    IP_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    TIMETUNLOCK_FIELD_NUMBER: _ClassVar[int]
    TIMET_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    desc: str
    ip: str
    nickname: str
    port: int
    timeT: int
    timeTUnlock: int
    type: int
    def __init__(self, ip: _Optional[str] = ..., port: _Optional[int] = ..., type: _Optional[int] = ..., nickname: _Optional[str] = ..., timeT: _Optional[int] = ..., desc: _Optional[str] = ..., timeTUnlock: _Optional[int] = ...) -> None: ...

class msgPushControlInfo(_message.Message):
    __slots__ = ["desc", "ip", "locked", "nickname", "port", "srcRelease", "timeT", "type"]
    DESC_FIELD_NUMBER: _ClassVar[int]
    IP_FIELD_NUMBER: _ClassVar[int]
    LOCKED_FIELD_NUMBER: _ClassVar[int]
    NICKNAME_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    SRCRELEASE_FIELD_NUMBER: _ClassVar[int]
    TIMET_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    desc: str
    ip: str
    locked: bool
    nickname: str
    port: int
    srcRelease: bool
    timeT: int
    type: int
    def __init__(self, locked: bool = ..., ip: _Optional[str] = ..., port: _Optional[int] = ..., type: _Optional[int] = ..., nickname: _Optional[str] = ..., timeT: _Optional[int] = ..., desc: _Optional[str] = ..., srcRelease: bool = ...) -> None: ...

class msgPushControllerInfo(_message.Message):
    __slots__ = ["driverEmc", "electric", "emergency", "humidity", "softEmc", "temperature", "voltage"]
    DRIVEREMC_FIELD_NUMBER: _ClassVar[int]
    ELECTRIC_FIELD_NUMBER: _ClassVar[int]
    EMERGENCY_FIELD_NUMBER: _ClassVar[int]
    HUMIDITY_FIELD_NUMBER: _ClassVar[int]
    SOFTEMC_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    VOLTAGE_FIELD_NUMBER: _ClassVar[int]
    driverEmc: bool
    electric: bool
    emergency: bool
    humidity: float
    softEmc: bool
    temperature: float
    voltage: float
    def __init__(self, temperature: _Optional[float] = ..., humidity: _Optional[float] = ..., voltage: _Optional[float] = ..., emergency: bool = ..., driverEmc: bool = ..., electric: bool = ..., softEmc: bool = ...) -> None: ...

class msgPushDIInfo(_message.Message):
    __slots__ = ["diMaxNode", "node"]
    DIMAXNODE_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    diMaxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgPushDINodeItem]
    def __init__(self, node: _Optional[_Iterable[_Union[msgPushDINodeItem, _Mapping]]] = ..., diMaxNode: _Optional[int] = ...) -> None: ...

class msgPushDINodeItem(_message.Message):
    __slots__ = ["forbidden", "id", "ioType", "key", "name", "status"]
    FORBIDDEN_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    IOTYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    forbidden: bool
    id: int
    ioType: int
    key: str
    name: str
    status: bool
    def __init__(self, id: _Optional[int] = ..., status: bool = ..., forbidden: bool = ..., ioType: _Optional[int] = ..., key: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class msgPushDOInfo(_message.Message):
    __slots__ = ["doMaxNode", "node"]
    DOMAXNODE_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    doMaxNode: int
    node: _containers.RepeatedCompositeFieldContainer[msgPushDONodeItem]
    def __init__(self, node: _Optional[_Iterable[_Union[msgPushDONodeItem, _Mapping]]] = ..., doMaxNode: _Optional[int] = ...) -> None: ...

class msgPushDONodeItem(_message.Message):
    __slots__ = ["id", "ioType", "key", "lock", "name", "status"]
    ID_FIELD_NUMBER: _ClassVar[int]
    IOTYPE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    LOCK_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    id: int
    ioType: int
    key: str
    lock: bool
    name: str
    status: bool
    def __init__(self, id: _Optional[int] = ..., status: bool = ..., ioType: _Optional[int] = ..., lock: bool = ..., key: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class msgPushDataChannelInfo(_message.Message):
    __slots__ = ["channels"]
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    channels: _containers.RepeatedCompositeFieldContainer[msgPushDataChannelItem]
    def __init__(self, channels: _Optional[_Iterable[_Union[msgPushDataChannelItem, _Mapping]]] = ...) -> None: ...

class msgPushDataChannelItem(_message.Message):
    __slots__ = ["name", "tags"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    name: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, name: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ...) -> None: ...

class msgPushFunctionalSafetyInfo(_message.Message):
    __slots__ = ["isEmc", "isMaintenance", "isMuting", "ossdRegion", "safeCuttingsId"]
    ISEMC_FIELD_NUMBER: _ClassVar[int]
    ISMAINTENANCE_FIELD_NUMBER: _ClassVar[int]
    ISMUTING_FIELD_NUMBER: _ClassVar[int]
    OSSDREGION_FIELD_NUMBER: _ClassVar[int]
    SAFECUTTINGSID_FIELD_NUMBER: _ClassVar[int]
    isEmc: bool
    isMaintenance: bool
    isMuting: bool
    ossdRegion: int
    safeCuttingsId: int
    def __init__(self, safeCuttingsId: _Optional[int] = ..., ossdRegion: _Optional[int] = ..., isEmc: bool = ..., isMuting: bool = ..., isMaintenance: bool = ...) -> None: ...

class msgPushImuHeader(_message.Message):
    __slots__ = ["dataNsec", "frameID", "pubNsec", "seq"]
    DATANSEC_FIELD_NUMBER: _ClassVar[int]
    FRAMEID_FIELD_NUMBER: _ClassVar[int]
    PUBNSEC_FIELD_NUMBER: _ClassVar[int]
    SEQ_FIELD_NUMBER: _ClassVar[int]
    dataNsec: int
    frameID: str
    pubNsec: int
    seq: int
    def __init__(self, pubNsec: _Optional[int] = ..., dataNsec: _Optional[int] = ..., seq: _Optional[int] = ..., frameID: _Optional[str] = ...) -> None: ...

class msgPushImuInfo(_message.Message):
    __slots__ = ["accX", "accY", "accZ", "imuHeader", "pitch", "qw", "qx", "qy", "qz", "roll", "rotOffX", "rotOffY", "rotOffZ", "rotX", "rotY", "rotZ", "yaw"]
    ACCX_FIELD_NUMBER: _ClassVar[int]
    ACCY_FIELD_NUMBER: _ClassVar[int]
    ACCZ_FIELD_NUMBER: _ClassVar[int]
    IMUHEADER_FIELD_NUMBER: _ClassVar[int]
    PITCH_FIELD_NUMBER: _ClassVar[int]
    QW_FIELD_NUMBER: _ClassVar[int]
    QX_FIELD_NUMBER: _ClassVar[int]
    QY_FIELD_NUMBER: _ClassVar[int]
    QZ_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    ROTOFFX_FIELD_NUMBER: _ClassVar[int]
    ROTOFFY_FIELD_NUMBER: _ClassVar[int]
    ROTOFFZ_FIELD_NUMBER: _ClassVar[int]
    ROTX_FIELD_NUMBER: _ClassVar[int]
    ROTY_FIELD_NUMBER: _ClassVar[int]
    ROTZ_FIELD_NUMBER: _ClassVar[int]
    YAW_FIELD_NUMBER: _ClassVar[int]
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
    rotOffX: int
    rotOffY: int
    rotOffZ: int
    rotX: float
    rotY: float
    rotZ: float
    yaw: float
    def __init__(self, imuHeader: _Optional[_Union[msgPushImuHeader, _Mapping]] = ..., yaw: _Optional[float] = ..., roll: _Optional[float] = ..., pitch: _Optional[float] = ..., accX: _Optional[float] = ..., accY: _Optional[float] = ..., accZ: _Optional[float] = ..., rotX: _Optional[float] = ..., rotY: _Optional[float] = ..., rotZ: _Optional[float] = ..., rotOffX: _Optional[int] = ..., rotOffY: _Optional[int] = ..., rotOffZ: _Optional[int] = ..., qx: _Optional[float] = ..., qy: _Optional[float] = ..., qz: _Optional[float] = ..., qw: _Optional[float] = ...) -> None: ...

class msgPushJoystick(_message.Message):
    __slots__ = ["status"]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: int
    def __init__(self, status: _Optional[int] = ...) -> None: ...

class msgPushLocalTag(_message.Message):
    __slots__ = ["angle", "confidence", "distanceNotFindTag", "groupName", "x", "y"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    DISTANCENOTFINDTAG_FIELD_NUMBER: _ClassVar[int]
    GROUPNAME_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    confidence: float
    distanceNotFindTag: float
    groupName: str
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ..., confidence: _Optional[float] = ..., distanceNotFindTag: _Optional[float] = ..., groupName: _Optional[str] = ...) -> None: ...

class msgPushLocationInfo(_message.Message):
    __slots__ = ["angle", "areaIds", "confidence", "currentStation", "errors", "lastStation", "locNotify", "locStatus", "localTag", "method", "x", "y"]
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_error_pb2.msgError, _Mapping]] = ...) -> None: ...
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    AREAIDS_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    CURRENTSTATION_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    LASTSTATION_FIELD_NUMBER: _ClassVar[int]
    LOCALTAG_FIELD_NUMBER: _ClassVar[int]
    LOCNOTIFY_FIELD_NUMBER: _ClassVar[int]
    LOCSTATUS_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    areaIds: _containers.RepeatedScalarFieldContainer[str]
    confidence: float
    currentStation: str
    errors: _containers.MessageMap[str, _message_error_pb2.msgError]
    lastStation: str
    locNotify: str
    locStatus: int
    localTag: msgPushLocalTag
    method: int
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ..., confidence: _Optional[float] = ..., method: _Optional[int] = ..., locNotify: _Optional[str] = ..., currentStation: _Optional[str] = ..., areaIds: _Optional[_Iterable[str]] = ..., lastStation: _Optional[str] = ..., locStatus: _Optional[int] = ..., localTag: _Optional[_Union[msgPushLocalTag, _Mapping]] = ..., errors: _Optional[_Mapping[str, _message_error_pb2.msgError]] = ...) -> None: ...

class msgPushMapInfo(_message.Message):
    __slots__ = ["currentMap", "currentMapEntries", "currentMapMd5", "currentTopoMd5", "loadMapStatus", "workspaceTopoMd5"]
    CURRENTMAPENTRIES_FIELD_NUMBER: _ClassVar[int]
    CURRENTMAPMD5_FIELD_NUMBER: _ClassVar[int]
    CURRENTMAP_FIELD_NUMBER: _ClassVar[int]
    CURRENTTOPOMD5_FIELD_NUMBER: _ClassVar[int]
    LOADMAPSTATUS_FIELD_NUMBER: _ClassVar[int]
    WORKSPACETOPOMD5_FIELD_NUMBER: _ClassVar[int]
    currentMap: str
    currentMapEntries: _containers.RepeatedCompositeFieldContainer[_message_map_pb2.msgMapFileMd5]
    currentMapMd5: str
    currentTopoMd5: str
    loadMapStatus: int
    workspaceTopoMd5: str
    def __init__(self, currentMap: _Optional[str] = ..., currentMapEntries: _Optional[_Iterable[_Union[_message_map_pb2.msgMapFileMd5, _Mapping]]] = ..., currentMapMd5: _Optional[str] = ..., currentTopoMd5: _Optional[str] = ..., loadMapStatus: _Optional[int] = ..., workspaceTopoMd5: _Optional[str] = ...) -> None: ...

class msgPushMappingInfo(_message.Message):
    __slots__ = ["slamStatus"]
    SLAMSTATUS_FIELD_NUMBER: _ClassVar[int]
    slamStatus: int
    def __init__(self, slamStatus: _Optional[int] = ...) -> None: ...

class msgPushMotorInfo(_message.Message):
    __slots__ = ["motorInfo", "motorMotion"]
    MOTORINFO_FIELD_NUMBER: _ClassVar[int]
    MOTORMOTION_FIELD_NUMBER: _ClassVar[int]
    motorInfo: _containers.RepeatedCompositeFieldContainer[msgPushMotorInfoItem]
    motorMotion: msgPushMotorMotionInfo
    def __init__(self, motorMotion: _Optional[_Union[msgPushMotorMotionInfo, _Mapping]] = ..., motorInfo: _Optional[_Iterable[_Union[msgPushMotorInfoItem, _Mapping]]] = ...) -> None: ...

class msgPushMotorInfoItem(_message.Message):
    __slots__ = ["calib", "canId", "canRouter", "current", "emc", "encoder", "err", "errorCode", "followErr", "key", "passive", "position", "rawPosition", "speed", "stop", "temperature", "torque", "type", "voltage"]
    CALIB_FIELD_NUMBER: _ClassVar[int]
    CANID_FIELD_NUMBER: _ClassVar[int]
    CANROUTER_FIELD_NUMBER: _ClassVar[int]
    CURRENT_FIELD_NUMBER: _ClassVar[int]
    EMC_FIELD_NUMBER: _ClassVar[int]
    ENCODER_FIELD_NUMBER: _ClassVar[int]
    ERRORCODE_FIELD_NUMBER: _ClassVar[int]
    ERR_FIELD_NUMBER: _ClassVar[int]
    FOLLOWERR_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    PASSIVE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    RAWPOSITION_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    STOP_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TORQUE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VOLTAGE_FIELD_NUMBER: _ClassVar[int]
    calib: _message_motorinfos_pb2.msgMotorInfo.calibStatus
    canId: int
    canRouter: int
    current: float
    emc: bool
    encoder: int
    err: bool
    errorCode: int
    followErr: bool
    key: str
    passive: bool
    position: float
    rawPosition: float
    speed: float
    stop: bool
    temperature: float
    torque: float
    type: _message_motorinfos_pb2.msgMotorInfo.motorType
    voltage: float
    def __init__(self, key: _Optional[str] = ..., canRouter: _Optional[int] = ..., canId: _Optional[int] = ..., position: _Optional[float] = ..., rawPosition: _Optional[float] = ..., speed: _Optional[float] = ..., current: _Optional[float] = ..., voltage: _Optional[float] = ..., stop: bool = ..., errorCode: _Optional[int] = ..., err: bool = ..., emc: bool = ..., temperature: _Optional[float] = ..., encoder: _Optional[int] = ..., type: _Optional[_Union[_message_motorinfos_pb2.msgMotorInfo.motorType, str]] = ..., passive: bool = ..., calib: _Optional[_Union[_message_motorinfos_pb2.msgMotorInfo.calibStatus, str]] = ..., followErr: bool = ..., torque: _Optional[float] = ...) -> None: ...

class msgPushMotorMotionInfo(_message.Message):
    __slots__ = ["isStop", "motorSteerAngles", "spinAngle", "spinVelocityCommand", "steerAngle", "steerAngleCommand", "steerAngles", "steerAnglesCommand"]
    ISSTOP_FIELD_NUMBER: _ClassVar[int]
    MOTORSTEERANGLES_FIELD_NUMBER: _ClassVar[int]
    SPINANGLE_FIELD_NUMBER: _ClassVar[int]
    SPINVELOCITYCOMMAND_FIELD_NUMBER: _ClassVar[int]
    STEERANGLECOMMAND_FIELD_NUMBER: _ClassVar[int]
    STEERANGLESCOMMAND_FIELD_NUMBER: _ClassVar[int]
    STEERANGLES_FIELD_NUMBER: _ClassVar[int]
    STEERANGLE_FIELD_NUMBER: _ClassVar[int]
    isStop: bool
    motorSteerAngles: _containers.RepeatedCompositeFieldContainer[msgPushMotorSteerAngleItem]
    spinAngle: float
    spinVelocityCommand: float
    steerAngle: float
    steerAngleCommand: float
    steerAngles: _containers.RepeatedScalarFieldContainer[float]
    steerAnglesCommand: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, steerAngle: _Optional[float] = ..., spinAngle: _Optional[float] = ..., steerAngleCommand: _Optional[float] = ..., spinVelocityCommand: _Optional[float] = ..., steerAngles: _Optional[_Iterable[float]] = ..., steerAnglesCommand: _Optional[_Iterable[float]] = ..., motorSteerAngles: _Optional[_Iterable[_Union[msgPushMotorSteerAngleItem, _Mapping]]] = ..., isStop: bool = ...) -> None: ...

class msgPushMotorSteerAngleItem(_message.Message):
    __slots__ = ["motorKey", "value"]
    MOTORKEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    motorKey: str
    value: float
    def __init__(self, motorKey: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...

class msgPushNavigationInfo(_message.Message):
    __slots__ = ["errors", "finishedPath", "mates", "moveStatusInfo", "multiPath", "runningStatus", "targetDist", "targetId", "targetLabel", "targetPoint", "taskId", "taskStatus", "taskStatusPackage", "type", "unfinishedPath"]
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_error_pb2.msgError, _Mapping]] = ...) -> None: ...
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    FINISHEDPATH_FIELD_NUMBER: _ClassVar[int]
    MATES_FIELD_NUMBER: _ClassVar[int]
    MOVESTATUSINFO_FIELD_NUMBER: _ClassVar[int]
    MULTIPATH_FIELD_NUMBER: _ClassVar[int]
    RUNNINGSTATUS_FIELD_NUMBER: _ClassVar[int]
    TARGETDIST_FIELD_NUMBER: _ClassVar[int]
    TARGETID_FIELD_NUMBER: _ClassVar[int]
    TARGETLABEL_FIELD_NUMBER: _ClassVar[int]
    TARGETPOINT_FIELD_NUMBER: _ClassVar[int]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    TASKSTATUSPACKAGE_FIELD_NUMBER: _ClassVar[int]
    TASKSTATUS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    UNFINISHEDPATH_FIELD_NUMBER: _ClassVar[int]
    errors: _containers.MessageMap[str, _message_error_pb2.msgError]
    finishedPath: _containers.RepeatedScalarFieldContainer[str]
    mates: str
    moveStatusInfo: str
    multiPath: _containers.RepeatedCompositeFieldContainer[msgJsonArray]
    runningStatus: int
    targetDist: float
    targetId: str
    targetLabel: str
    targetPoint: _containers.RepeatedScalarFieldContainer[float]
    taskId: str
    taskStatus: _message_movetask_pb2.msgMoveStatus.status
    taskStatusPackage: _message_movetask_pb2.msgTaskStatusPackage
    type: _message_movetask_pb2.msgMoveStatus.type
    unfinishedPath: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, taskId: _Optional[str] = ..., taskStatus: _Optional[_Union[_message_movetask_pb2.msgMoveStatus.status, str]] = ..., runningStatus: _Optional[int] = ..., type: _Optional[_Union[_message_movetask_pb2.msgMoveStatus.type, str]] = ..., targetDist: _Optional[float] = ..., moveStatusInfo: _Optional[str] = ..., targetId: _Optional[str] = ..., targetLabel: _Optional[str] = ..., targetPoint: _Optional[_Iterable[float]] = ..., multiPath: _Optional[_Iterable[_Union[msgJsonArray, _Mapping]]] = ..., finishedPath: _Optional[_Iterable[str]] = ..., unfinishedPath: _Optional[_Iterable[str]] = ..., mates: _Optional[str] = ..., taskStatusPackage: _Optional[_Union[_message_movetask_pb2.msgTaskStatusPackage, _Mapping]] = ..., errors: _Optional[_Mapping[str, _message_error_pb2.msgError]] = ...) -> None: ...

class msgPushNetworkInfo(_message.Message):
    __slots__ = ["apAddr", "externalEthMac", "ip", "rssi", "ssid", "wlanMac"]
    APADDR_FIELD_NUMBER: _ClassVar[int]
    EXTERNALETHMAC_FIELD_NUMBER: _ClassVar[int]
    IP_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    SSID_FIELD_NUMBER: _ClassVar[int]
    WLANMAC_FIELD_NUMBER: _ClassVar[int]
    apAddr: str
    externalEthMac: str
    ip: str
    rssi: int
    ssid: str
    wlanMac: str
    def __init__(self, ssid: _Optional[str] = ..., rssi: _Optional[int] = ..., apAddr: _Optional[str] = ..., ip: _Optional[str] = ..., wlanMac: _Optional[str] = ..., externalEthMac: _Optional[str] = ...) -> None: ...

class msgPushObstacleInfo(_message.Message):
    __slots__ = ["blockDevice", "blockReason", "blockX", "blockY", "blocked", "maskedDevices", "nearestObstacles", "slowDevice", "slowReason", "slowX", "slowY", "slowed"]
    class reason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    BLOCKDEVICE_FIELD_NUMBER: _ClassVar[int]
    BLOCKED_FIELD_NUMBER: _ClassVar[int]
    BLOCKREASON_FIELD_NUMBER: _ClassVar[int]
    BLOCKX_FIELD_NUMBER: _ClassVar[int]
    BLOCKY_FIELD_NUMBER: _ClassVar[int]
    MASKEDDEVICES_FIELD_NUMBER: _ClassVar[int]
    NEARESTOBSTACLES_FIELD_NUMBER: _ClassVar[int]
    SLOWDEVICE_FIELD_NUMBER: _ClassVar[int]
    SLOWED_FIELD_NUMBER: _ClassVar[int]
    SLOWREASON_FIELD_NUMBER: _ClassVar[int]
    SLOWX_FIELD_NUMBER: _ClassVar[int]
    SLOWY_FIELD_NUMBER: _ClassVar[int]
    apiObstacle: msgPushObstacleInfo.reason
    blockDevice: str
    blockReason: int
    blockX: float
    blockY: float
    blocked: bool
    collision: msgPushObstacleInfo.reason
    depthCamera: msgPushObstacleInfo.reason
    diSensor: msgPushObstacleInfo.reason
    diUltrasonic: msgPushObstacleInfo.reason
    distanceNode: msgPushObstacleInfo.reason
    laser: msgPushObstacleInfo.reason
    lock: msgPushObstacleInfo.reason
    maskedDevices: _containers.RepeatedScalarFieldContainer[str]
    nearestObstacles: _containers.RepeatedCompositeFieldContainer[msgJsonObject]
    slowDevice: str
    slowReason: int
    slowX: float
    slowY: float
    slowed: bool
    ultrasonic: msgPushObstacleInfo.reason
    virtualPoint: msgPushObstacleInfo.reason
    def __init__(self, blocked: bool = ..., blockX: _Optional[float] = ..., blockY: _Optional[float] = ..., blockReason: _Optional[int] = ..., blockDevice: _Optional[str] = ..., slowed: bool = ..., slowX: _Optional[float] = ..., slowY: _Optional[float] = ..., slowReason: _Optional[int] = ..., slowDevice: _Optional[str] = ..., nearestObstacles: _Optional[_Iterable[_Union[msgJsonObject, _Mapping]]] = ..., maskedDevices: _Optional[_Iterable[str]] = ...) -> None: ...

class msgPushRobotInfo(_message.Message):
    __slots__ = ["appMd5", "architecture", "chassisType", "codeId", "deviceParamMd5", "deviceParamVersion", "dnnModelVersion", "dspVersion", "echoid", "errors", "features", "fleetConnect", "fleetControl", "gyroVersion", "id", "mapVersion", "modbusVersion", "model", "modelName", "netprotocolVersion", "product", "pyideVersion", "roboshopMinVersionRequired", "robotNote", "simulation", "srcName", "systemStatus", "taskRunnerVersion", "vehicleId", "version", "versionList"]
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_error_pb2.msgError, _Mapping]] = ...) -> None: ...
    APPMD5_FIELD_NUMBER: _ClassVar[int]
    ARCHITECTURE_FIELD_NUMBER: _ClassVar[int]
    CHASSISTYPE_FIELD_NUMBER: _ClassVar[int]
    CODEID_FIELD_NUMBER: _ClassVar[int]
    DEVICEPARAMMD5_FIELD_NUMBER: _ClassVar[int]
    DEVICEPARAMVERSION_FIELD_NUMBER: _ClassVar[int]
    DNNMODELVERSION_FIELD_NUMBER: _ClassVar[int]
    DSPVERSION_FIELD_NUMBER: _ClassVar[int]
    ECHOID_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    FLEETCONNECT_FIELD_NUMBER: _ClassVar[int]
    FLEETCONTROL_FIELD_NUMBER: _ClassVar[int]
    GYROVERSION_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    MAPVERSION_FIELD_NUMBER: _ClassVar[int]
    MODBUSVERSION_FIELD_NUMBER: _ClassVar[int]
    MODELNAME_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    NETPROTOCOLVERSION_FIELD_NUMBER: _ClassVar[int]
    PRODUCT_FIELD_NUMBER: _ClassVar[int]
    PYIDEVERSION_FIELD_NUMBER: _ClassVar[int]
    ROBOSHOPMINVERSIONREQUIRED_FIELD_NUMBER: _ClassVar[int]
    ROBOTNOTE_FIELD_NUMBER: _ClassVar[int]
    SIMULATION_FIELD_NUMBER: _ClassVar[int]
    SRCNAME_FIELD_NUMBER: _ClassVar[int]
    SYSTEMSTATUS_FIELD_NUMBER: _ClassVar[int]
    TASKRUNNERVERSION_FIELD_NUMBER: _ClassVar[int]
    VEHICLEID_FIELD_NUMBER: _ClassVar[int]
    VERSIONLIST_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
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
    features: msgJsonValue
    fleetConnect: bool
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
    versionList: msgJsonObject
    def __init__(self, id: _Optional[str] = ..., fleetControl: bool = ..., codeId: _Optional[str] = ..., simulation: bool = ..., echoid: _Optional[str] = ..., features: _Optional[_Union[msgJsonValue, _Mapping]] = ..., vehicleId: _Optional[str] = ..., robotNote: _Optional[str] = ..., version: _Optional[str] = ..., product: _Optional[str] = ..., model: _Optional[str] = ..., modelName: _Optional[str] = ..., deviceParamMd5: _Optional[str] = ..., appMd5: _Optional[str] = ..., chassisType: _Optional[str] = ..., dspVersion: _Optional[str] = ..., gyroVersion: _Optional[str] = ..., pyideVersion: _Optional[str] = ..., taskRunnerVersion: _Optional[str] = ..., versionList: _Optional[_Union[msgJsonObject, _Mapping]] = ..., deviceParamVersion: _Optional[str] = ..., mapVersion: _Optional[str] = ..., roboshopMinVersionRequired: _Optional[str] = ..., netprotocolVersion: _Optional[str] = ..., dnnModelVersion: _Optional[str] = ..., modbusVersion: _Optional[str] = ..., srcName: _Optional[str] = ..., architecture: _Optional[str] = ..., systemStatus: _Optional[int] = ..., errors: _Optional[_Mapping[str, _message_error_pb2.msgError]] = ..., fleetConnect: bool = ...) -> None: ...

class msgPushRobotShapeInfo(_message.Message):
    __slots__ = ["head", "radius", "shape", "tail", "width"]
    HEAD_FIELD_NUMBER: _ClassVar[int]
    RADIUS_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    TAIL_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    head: float
    radius: float
    shape: int
    tail: float
    width: float
    def __init__(self, shape: _Optional[int] = ..., head: _Optional[float] = ..., tail: _Optional[float] = ..., width: _Optional[float] = ..., radius: _Optional[float] = ...) -> None: ...

class msgPushSoundInfo(_message.Message):
    __slots__ = ["count", "loop", "soundName", "status"]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    LOOP_FIELD_NUMBER: _ClassVar[int]
    SOUNDNAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    count: int
    loop: bool
    soundName: str
    status: int
    def __init__(self, status: _Optional[int] = ..., soundName: _Optional[str] = ..., loop: bool = ..., count: _Optional[int] = ...) -> None: ...

class msgState(_message.Message):
    __slots__ = ["battery", "calibStatus", "chassis", "codeScanners", "control", "controlHistory", "controller", "dataChannel", "deviceStatus", "di", "do", "dynamicObstacle", "functionalSafety", "gnss", "goodsRegion", "imu", "ioConfig", "joystick", "location", "map", "mapping", "motor", "movePolygon", "navigation", "network", "obstacle", "rfids", "robot", "robotShape", "script", "sound", "stats", "taskRunner"]
    class DeviceStatusEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_devicestatus_pb2.msgDeviceStatusNode
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_devicestatus_pb2.msgDeviceStatusNode, _Mapping]] = ...) -> None: ...
    BATTERY_FIELD_NUMBER: _ClassVar[int]
    CALIBSTATUS_FIELD_NUMBER: _ClassVar[int]
    CHASSIS_FIELD_NUMBER: _ClassVar[int]
    CODESCANNERS_FIELD_NUMBER: _ClassVar[int]
    CONTROLHISTORY_FIELD_NUMBER: _ClassVar[int]
    CONTROLLER_FIELD_NUMBER: _ClassVar[int]
    CONTROL_FIELD_NUMBER: _ClassVar[int]
    DATACHANNEL_FIELD_NUMBER: _ClassVar[int]
    DEVICESTATUS_FIELD_NUMBER: _ClassVar[int]
    DI_FIELD_NUMBER: _ClassVar[int]
    DO_FIELD_NUMBER: _ClassVar[int]
    DYNAMICOBSTACLE_FIELD_NUMBER: _ClassVar[int]
    FUNCTIONALSAFETY_FIELD_NUMBER: _ClassVar[int]
    GNSS_FIELD_NUMBER: _ClassVar[int]
    GOODSREGION_FIELD_NUMBER: _ClassVar[int]
    IMU_FIELD_NUMBER: _ClassVar[int]
    IOCONFIG_FIELD_NUMBER: _ClassVar[int]
    JOYSTICK_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    MAPPING_FIELD_NUMBER: _ClassVar[int]
    MAP_FIELD_NUMBER: _ClassVar[int]
    MOTOR_FIELD_NUMBER: _ClassVar[int]
    MOVEPOLYGON_FIELD_NUMBER: _ClassVar[int]
    NAVIGATION_FIELD_NUMBER: _ClassVar[int]
    NETWORK_FIELD_NUMBER: _ClassVar[int]
    OBSTACLE_FIELD_NUMBER: _ClassVar[int]
    RFIDS_FIELD_NUMBER: _ClassVar[int]
    ROBOTSHAPE_FIELD_NUMBER: _ClassVar[int]
    ROBOT_FIELD_NUMBER: _ClassVar[int]
    SCRIPT_FIELD_NUMBER: _ClassVar[int]
    SOUND_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    TASKRUNNER_FIELD_NUMBER: _ClassVar[int]
    battery: msgPushBatteryInfo
    calibStatus: msgPushCalibStatus
    chassis: msgPushChassisInfo
    codeScanners: _containers.RepeatedCompositeFieldContainer[msgPushCodeScannerItem]
    control: msgPushControlInfo
    controlHistory: _containers.RepeatedCompositeFieldContainer[msgPushControlHistoryItem]
    controller: msgPushControllerInfo
    dataChannel: msgPushDataChannelInfo
    deviceStatus: _containers.MessageMap[str, _message_devicestatus_pb2.msgDeviceStatusNode]
    di: msgPushDIInfo
    do: msgPushDOInfo
    dynamicObstacle: _containers.RepeatedCompositeFieldContainer[msgJsonObject]
    functionalSafety: msgPushFunctionalSafetyInfo
    gnss: _message_gnss_pb2.msgGnss
    goodsRegion: msgJsonObject
    imu: msgPushImuInfo
    ioConfig: str
    joystick: msgPushJoystick
    location: msgPushLocationInfo
    map: msgPushMapInfo
    mapping: msgPushMappingInfo
    motor: msgPushMotorInfo
    movePolygon: msgJsonObject
    navigation: msgPushNavigationInfo
    network: msgPushNetworkInfo
    obstacle: msgPushObstacleInfo
    rfids: _containers.RepeatedScalarFieldContainer[int]
    robot: msgPushRobotInfo
    robotShape: msgPushRobotShapeInfo
    script: _message_script_pb2.msgScript
    sound: msgPushSoundInfo
    stats: msgJsonObject
    taskRunner: str
    def __init__(self, stats: _Optional[_Union[msgJsonObject, _Mapping]] = ..., controller: _Optional[_Union[msgPushControllerInfo, _Mapping]] = ..., location: _Optional[_Union[msgPushLocationInfo, _Mapping]] = ..., chassis: _Optional[_Union[msgPushChassisInfo, _Mapping]] = ..., motor: _Optional[_Union[msgPushMotorInfo, _Mapping]] = ..., obstacle: _Optional[_Union[msgPushObstacleInfo, _Mapping]] = ..., battery: _Optional[_Union[msgPushBatteryInfo, _Mapping]] = ..., di: _Optional[_Union[msgPushDIInfo, _Mapping]] = ..., do: _Optional[_Union[msgPushDOInfo, _Mapping]] = ..., ioConfig: _Optional[str] = ..., navigation: _Optional[_Union[msgPushNavigationInfo, _Mapping]] = ..., mapping: _Optional[_Union[msgPushMappingInfo, _Mapping]] = ..., map: _Optional[_Union[msgPushMapInfo, _Mapping]] = ..., network: _Optional[_Union[msgPushNetworkInfo, _Mapping]] = ..., robot: _Optional[_Union[msgPushRobotInfo, _Mapping]] = ..., control: _Optional[_Union[msgPushControlInfo, _Mapping]] = ..., controlHistory: _Optional[_Iterable[_Union[msgPushControlHistoryItem, _Mapping]]] = ..., robotShape: _Optional[_Union[msgPushRobotShapeInfo, _Mapping]] = ..., sound: _Optional[_Union[msgPushSoundInfo, _Mapping]] = ..., movePolygon: _Optional[_Union[msgJsonObject, _Mapping]] = ..., imu: _Optional[_Union[msgPushImuInfo, _Mapping]] = ..., functionalSafety: _Optional[_Union[msgPushFunctionalSafetyInfo, _Mapping]] = ..., goodsRegion: _Optional[_Union[msgJsonObject, _Mapping]] = ..., dynamicObstacle: _Optional[_Iterable[_Union[msgJsonObject, _Mapping]]] = ..., calibStatus: _Optional[_Union[msgPushCalibStatus, _Mapping]] = ..., gnss: _Optional[_Union[_message_gnss_pb2.msgGnss, _Mapping]] = ..., rfids: _Optional[_Iterable[int]] = ..., codeScanners: _Optional[_Iterable[_Union[msgPushCodeScannerItem, _Mapping]]] = ..., taskRunner: _Optional[str] = ..., deviceStatus: _Optional[_Mapping[str, _message_devicestatus_pb2.msgDeviceStatusNode]] = ..., joystick: _Optional[_Union[msgPushJoystick, _Mapping]] = ..., dataChannel: _Optional[_Union[msgPushDataChannelInfo, _Mapping]] = ..., script: _Optional[_Union[_message_script_pb2.msgScript, _Mapping]] = ...) -> None: ...
