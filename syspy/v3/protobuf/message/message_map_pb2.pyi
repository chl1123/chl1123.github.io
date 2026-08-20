from google.protobuf import struct_pb2 as _struct_pb2
import message_header_pb2 as _message_header_pb2
import message_imu_pb2 as _message_imu_pb2
import message_gnss_pb2 as _message_gnss_pb2
import message_localization_pb2 as _message_localization_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgAdvancedArea(_message.Message):
    __slots__ = ["attribute", "className", "desc", "dir", "instanceName", "posGroup", "property"]
    ATTRIBUTE_FIELD_NUMBER: ClassVar[int]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    DIR_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    POSGROUP_FIELD_NUMBER: ClassVar[int]
    PROPERTY_FIELD_NUMBER: ClassVar[int]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    dir: float
    instanceName: str
    posGroup: _containers.RepeatedCompositeFieldContainer[msgMapPos]
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., posGroup: Optional[Iterable[Union[msgMapPos, Mapping]]] = ..., dir: Optional[float] = ..., property: Optional[Iterable[Union[msgMapProperty, Mapping]]] = ..., desc: Optional[bytes] = ..., attribute: Optional[Union[msgMapAttribute, Mapping]] = ...) -> None: ...

class msgAdvancedCurve(_message.Message):
    __slots__ = ["attribute", "className", "controlPos1", "controlPos2", "controlPos3", "controlPos4", "desc", "endPos", "instanceName", "property", "startPos"]
    ATTRIBUTE_FIELD_NUMBER: ClassVar[int]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    CONTROLPOS1_FIELD_NUMBER: ClassVar[int]
    CONTROLPOS2_FIELD_NUMBER: ClassVar[int]
    CONTROLPOS3_FIELD_NUMBER: ClassVar[int]
    CONTROLPOS4_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    ENDPOS_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    PROPERTY_FIELD_NUMBER: ClassVar[int]
    STARTPOS_FIELD_NUMBER: ClassVar[int]
    attribute: msgMapAttribute
    className: str
    controlPos1: msgMapPos
    controlPos2: msgMapPos
    controlPos3: msgMapPos
    controlPos4: msgMapPos
    desc: bytes
    endPos: str
    instanceName: str
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    startPos: str
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., startPos: Optional[str] = ..., endPos: Optional[str] = ..., controlPos1: Optional[Union[msgMapPos, Mapping]] = ..., controlPos2: Optional[Union[msgMapPos, Mapping]] = ..., property: Optional[Iterable[Union[msgMapProperty, Mapping]]] = ..., desc: Optional[bytes] = ..., controlPos3: Optional[Union[msgMapPos, Mapping]] = ..., controlPos4: Optional[Union[msgMapPos, Mapping]] = ..., attribute: Optional[Union[msgMapAttribute, Mapping]] = ...) -> None: ...

class msgAdvancedLine(_message.Message):
    __slots__ = ["attribute", "className", "desc", "instanceName", "line", "property"]
    ATTRIBUTE_FIELD_NUMBER: ClassVar[int]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    LINE_FIELD_NUMBER: ClassVar[int]
    PROPERTY_FIELD_NUMBER: ClassVar[int]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    instanceName: str
    line: msgMapLine
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., line: Optional[Union[msgMapLine, Mapping]] = ..., property: Optional[Iterable[Union[msgMapProperty, Mapping]]] = ..., desc: Optional[bytes] = ..., attribute: Optional[Union[msgMapAttribute, Mapping]] = ...) -> None: ...

class msgAdvancedPoint(_message.Message):
    __slots__ = ["attribute", "className", "desc", "dir", "ignoreDir", "instanceName", "pos", "property"]
    ATTRIBUTE_FIELD_NUMBER: ClassVar[int]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    DIR_FIELD_NUMBER: ClassVar[int]
    IGNOREDIR_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    POS_FIELD_NUMBER: ClassVar[int]
    PROPERTY_FIELD_NUMBER: ClassVar[int]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    dir: float
    ignoreDir: bool
    instanceName: str
    pos: msgMapPos
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., pos: Optional[Union[msgMapPos, Mapping]] = ..., dir: Optional[float] = ..., property: Optional[Iterable[Union[msgMapProperty, Mapping]]] = ..., ignoreDir: bool = ..., desc: Optional[bytes] = ..., attribute: Optional[Union[msgMapAttribute, Mapping]] = ...) -> None: ...

class msgAutogate(_message.Message):
    __slots__ = ["className", "desc", "dir", "height", "instanceName", "isEnabled", "jsonObject", "length", "pointNames", "width", "x", "y"]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    DIR_FIELD_NUMBER: ClassVar[int]
    HEIGHT_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    ISENABLED_FIELD_NUMBER: ClassVar[int]
    JSONOBJECT_FIELD_NUMBER: ClassVar[int]
    LENGTH_FIELD_NUMBER: ClassVar[int]
    POINTNAMES_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    className: str
    desc: bytes
    dir: float
    height: float
    instanceName: str
    isEnabled: bool
    jsonObject: _struct_pb2.Struct
    length: float
    pointNames: _containers.RepeatedScalarFieldContainer[str]
    width: float
    x: float
    y: float
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., pointNames: Optional[Iterable[str]] = ..., x: Optional[float] = ..., y: Optional[float] = ..., dir: Optional[float] = ..., width: Optional[float] = ..., length: Optional[float] = ..., height: Optional[float] = ..., isEnabled: bool = ..., desc: Optional[bytes] = ..., jsonObject: Optional[Union[_struct_pb2.Struct, Mapping]] = ...) -> None: ...

class msgBinLocation(_message.Message):
    __slots__ = ["bindPoints", "className", "desc", "dir", "instanceName", "length", "recognitionFile", "width", "x", "y", "z"]
    BINDPOINTS_FIELD_NUMBER: ClassVar[int]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    DIR_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    LENGTH_FIELD_NUMBER: ClassVar[int]
    RECOGNITIONFILE_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    bindPoints: _containers.RepeatedCompositeFieldContainer[msgBindPoints]
    className: str
    desc: bytes
    dir: float
    instanceName: str
    length: float
    recognitionFile: str
    width: float
    x: float
    y: float
    z: float
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., recognitionFile: Optional[str] = ..., x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ..., dir: Optional[float] = ..., width: Optional[float] = ..., length: Optional[float] = ..., bindPoints: Optional[Iterable[Union[msgBindPoints, Mapping]]] = ..., desc: Optional[bytes] = ...) -> None: ...

class msgBinLocations(_message.Message):
    __slots__ = ["bin"]
    BIN_FIELD_NUMBER: ClassVar[int]
    bin: _containers.RepeatedCompositeFieldContainer[msgBinLocation]
    def __init__(self, bin: Optional[Iterable[Union[msgBinLocation, Mapping]]] = ...) -> None: ...

class msgBindPoints(_message.Message):
    __slots__ = ["binTasks", "pointName", "recognitionSide"]
    BINTASKS_FIELD_NUMBER: ClassVar[int]
    POINTNAME_FIELD_NUMBER: ClassVar[int]
    RECOGNITIONSIDE_FIELD_NUMBER: ClassVar[int]
    binTasks: _containers.RepeatedScalarFieldContainer[str]
    pointName: str
    recognitionSide: str
    def __init__(self, pointName: Optional[str] = ..., binTasks: Optional[Iterable[str]] = ..., recognitionSide: Optional[str] = ...) -> None: ...

class msgCharger(_message.Message):
    __slots__ = ["className", "desc", "dir", "height", "instanceName", "jsonObject", "length", "pointName", "width", "x", "y"]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    DIR_FIELD_NUMBER: ClassVar[int]
    HEIGHT_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    JSONOBJECT_FIELD_NUMBER: ClassVar[int]
    LENGTH_FIELD_NUMBER: ClassVar[int]
    POINTNAME_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    className: str
    desc: bytes
    dir: float
    height: float
    instanceName: str
    jsonObject: _struct_pb2.Struct
    length: float
    pointName: str
    width: float
    x: float
    y: float
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., pointName: Optional[str] = ..., x: Optional[float] = ..., y: Optional[float] = ..., dir: Optional[float] = ..., width: Optional[float] = ..., length: Optional[float] = ..., height: Optional[float] = ..., desc: Optional[bytes] = ..., jsonObject: Optional[Union[_struct_pb2.Struct, Mapping]] = ...) -> None: ...

class msgCurrentMapInfo(_message.Message):
    __slots__ = ["currentMap", "currentMapEntries", "currentMapMd5", "currentTopoMd5"]
    CURRENTMAPENTRIES_FIELD_NUMBER: ClassVar[int]
    CURRENTMAPMD5_FIELD_NUMBER: ClassVar[int]
    CURRENTMAP_FIELD_NUMBER: ClassVar[int]
    CURRENTTOPOMD5_FIELD_NUMBER: ClassVar[int]
    currentMap: str
    currentMapEntries: _containers.RepeatedCompositeFieldContainer[msgMapFileMd5]
    currentMapMd5: str
    currentTopoMd5: str
    def __init__(self, currentMap: Optional[str] = ..., currentMapEntries: Optional[Iterable[Union[msgMapFileMd5, Mapping]]] = ..., currentMapMd5: Optional[str] = ..., currentTopoMd5: Optional[str] = ...) -> None: ...

class msgExternalDevice(_message.Message):
    __slots__ = ["attribute", "className", "desc", "instanceName", "isEnabled", "property"]
    ATTRIBUTE_FIELD_NUMBER: ClassVar[int]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    ISENABLED_FIELD_NUMBER: ClassVar[int]
    PROPERTY_FIELD_NUMBER: ClassVar[int]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    instanceName: str
    isEnabled: bool
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., isEnabled: bool = ..., property: Optional[Iterable[Union[msgMapProperty, Mapping]]] = ..., desc: Optional[bytes] = ..., attribute: Optional[Union[msgMapAttribute, Mapping]] = ...) -> None: ...

class msgLiveRefPos(_message.Message):
    __slots__ = ["refPos"]
    REFPOS_FIELD_NUMBER: ClassVar[int]
    refPos: _containers.RepeatedCompositeFieldContainer[msgReflectorPos]
    def __init__(self, refPos: Optional[Iterable[Union[msgReflectorPos, Mapping]]] = ...) -> None: ...

class msgMap(_message.Message):
    __slots__ = ["advancedAreaList", "advancedCurveList", "advancedLineList", "advancedPointList", "autogateList", "bins", "chargerList", "externalDeviceList", "header", "reflectorPosList", "tagGroupList", "topoAreaList"]
    ADVANCEDAREALIST_FIELD_NUMBER: ClassVar[int]
    ADVANCEDCURVELIST_FIELD_NUMBER: ClassVar[int]
    ADVANCEDLINELIST_FIELD_NUMBER: ClassVar[int]
    ADVANCEDPOINTLIST_FIELD_NUMBER: ClassVar[int]
    AUTOGATELIST_FIELD_NUMBER: ClassVar[int]
    BINS_FIELD_NUMBER: ClassVar[int]
    CHARGERLIST_FIELD_NUMBER: ClassVar[int]
    EXTERNALDEVICELIST_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    REFLECTORPOSLIST_FIELD_NUMBER: ClassVar[int]
    TAGGROUPLIST_FIELD_NUMBER: ClassVar[int]
    TOPOAREALIST_FIELD_NUMBER: ClassVar[int]
    advancedAreaList: _containers.RepeatedCompositeFieldContainer[msgAdvancedArea]
    advancedCurveList: _containers.RepeatedCompositeFieldContainer[msgAdvancedCurve]
    advancedLineList: _containers.RepeatedCompositeFieldContainer[msgAdvancedLine]
    advancedPointList: _containers.RepeatedCompositeFieldContainer[msgAdvancedPoint]
    autogateList: _containers.RepeatedCompositeFieldContainer[msgAutogate]
    bins: _containers.RepeatedCompositeFieldContainer[msgBinLocations]
    chargerList: _containers.RepeatedCompositeFieldContainer[msgCharger]
    externalDeviceList: _containers.RepeatedCompositeFieldContainer[msgExternalDevice]
    header: msgMapHeader
    reflectorPosList: _containers.RepeatedCompositeFieldContainer[msgReflectorPos]
    tagGroupList: _containers.RepeatedCompositeFieldContainer[msgTagGroup]
    topoAreaList: _containers.RepeatedCompositeFieldContainer[msgTopoArea]
    def __init__(self, header: Optional[Union[msgMapHeader, Mapping]] = ..., advancedPointList: Optional[Iterable[Union[msgAdvancedPoint, Mapping]]] = ..., advancedLineList: Optional[Iterable[Union[msgAdvancedLine, Mapping]]] = ..., advancedCurveList: Optional[Iterable[Union[msgAdvancedCurve, Mapping]]] = ..., advancedAreaList: Optional[Iterable[Union[msgAdvancedArea, Mapping]]] = ..., reflectorPosList: Optional[Iterable[Union[msgReflectorPos, Mapping]]] = ..., tagGroupList: Optional[Iterable[Union[msgTagGroup, Mapping]]] = ..., externalDeviceList: Optional[Iterable[Union[msgExternalDevice, Mapping]]] = ..., bins: Optional[Iterable[Union[msgBinLocations, Mapping]]] = ..., topoAreaList: Optional[Iterable[Union[msgTopoArea, Mapping]]] = ..., chargerList: Optional[Iterable[Union[msgCharger, Mapping]]] = ..., autogateList: Optional[Iterable[Union[msgAutogate, Mapping]]] = ...) -> None: ...

class msgMapAttribute(_message.Message):
    __slots__ = ["colorBrush", "colorFont", "colorPen", "description"]
    COLORBRUSH_FIELD_NUMBER: ClassVar[int]
    COLORFONT_FIELD_NUMBER: ClassVar[int]
    COLORPEN_FIELD_NUMBER: ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: ClassVar[int]
    colorBrush: int
    colorFont: int
    colorPen: int
    description: str
    def __init__(self, description: Optional[str] = ..., colorPen: Optional[int] = ..., colorBrush: Optional[int] = ..., colorFont: Optional[int] = ...) -> None: ...

class msgMapFileMd5(_message.Message):
    __slots__ = ["md5", "relativePath"]
    MD5_FIELD_NUMBER: ClassVar[int]
    RELATIVEPATH_FIELD_NUMBER: ClassVar[int]
    md5: str
    relativePath: str
    def __init__(self, relativePath: Optional[str] = ..., md5: Optional[str] = ...) -> None: ...

class msgMapHeader(_message.Message):
    __slots__ = ["mapName", "mapType", "maxPos", "minPos", "resolution", "version"]
    MAPNAME_FIELD_NUMBER: ClassVar[int]
    MAPTYPE_FIELD_NUMBER: ClassVar[int]
    MAXPOS_FIELD_NUMBER: ClassVar[int]
    MINPOS_FIELD_NUMBER: ClassVar[int]
    RESOLUTION_FIELD_NUMBER: ClassVar[int]
    VERSION_FIELD_NUMBER: ClassVar[int]
    mapName: str
    mapType: str
    maxPos: msgMapPos
    minPos: msgMapPos
    resolution: float
    version: str
    def __init__(self, mapType: Optional[str] = ..., mapName: Optional[str] = ..., minPos: Optional[Union[msgMapPos, Mapping]] = ..., maxPos: Optional[Union[msgMapPos, Mapping]] = ..., resolution: Optional[float] = ..., version: Optional[str] = ...) -> None: ...

class msgMapLine(_message.Message):
    __slots__ = ["endPos", "startPos"]
    ENDPOS_FIELD_NUMBER: ClassVar[int]
    STARTPOS_FIELD_NUMBER: ClassVar[int]
    endPos: msgMapPos
    startPos: msgMapPos
    def __init__(self, startPos: Optional[Union[msgMapPos, Mapping]] = ..., endPos: Optional[Union[msgMapPos, Mapping]] = ...) -> None: ...

class msgMapLog(_message.Message):
    __slots__ = ["allGnssData", "azimuthCorrection", "factor", "gnssData", "imuData", "laserInstallHeight", "laserInstallPitch", "laserInstallRoll", "laserInstallYaw", "laserName", "laserPosX", "laserPosY", "laserPosZ", "laserRangeMax", "laserStep", "laserType", "localizationData", "logData", "logData3D", "odometer", "verticalCorrection"]
    ALLGNSSDATA_FIELD_NUMBER: ClassVar[int]
    AZIMUTHCORRECTION_FIELD_NUMBER: ClassVar[int]
    FACTOR_FIELD_NUMBER: ClassVar[int]
    GNSSDATA_FIELD_NUMBER: ClassVar[int]
    IMUDATA_FIELD_NUMBER: ClassVar[int]
    LASERINSTALLHEIGHT_FIELD_NUMBER: ClassVar[int]
    LASERINSTALLPITCH_FIELD_NUMBER: ClassVar[int]
    LASERINSTALLROLL_FIELD_NUMBER: ClassVar[int]
    LASERINSTALLYAW_FIELD_NUMBER: ClassVar[int]
    LASERNAME_FIELD_NUMBER: ClassVar[int]
    LASERPOSX_FIELD_NUMBER: ClassVar[int]
    LASERPOSY_FIELD_NUMBER: ClassVar[int]
    LASERPOSZ_FIELD_NUMBER: ClassVar[int]
    LASERRANGEMAX_FIELD_NUMBER: ClassVar[int]
    LASERSTEP_FIELD_NUMBER: ClassVar[int]
    LASERTYPE_FIELD_NUMBER: ClassVar[int]
    LOCALIZATIONDATA_FIELD_NUMBER: ClassVar[int]
    LOGDATA3D_FIELD_NUMBER: ClassVar[int]
    LOGDATA_FIELD_NUMBER: ClassVar[int]
    ODOMETER_FIELD_NUMBER: ClassVar[int]
    VERTICALCORRECTION_FIELD_NUMBER: ClassVar[int]
    allGnssData: _containers.RepeatedCompositeFieldContainer[_message_gnss_pb2.msgAllGnss]
    azimuthCorrection: _containers.RepeatedScalarFieldContainer[float]
    factor: float
    gnssData: _containers.RepeatedCompositeFieldContainer[_message_gnss_pb2.msgGnss]
    imuData: _containers.RepeatedCompositeFieldContainer[_message_imu_pb2.msgIMU]
    laserInstallHeight: float
    laserInstallPitch: float
    laserInstallRoll: float
    laserInstallYaw: float
    laserName: str
    laserPosX: float
    laserPosY: float
    laserPosZ: float
    laserRangeMax: float
    laserStep: float
    laserType: int
    localizationData: _containers.RepeatedCompositeFieldContainer[_message_localization_pb2.msgLocalization]
    logData: _containers.RepeatedCompositeFieldContainer[msgMapLogData]
    logData3D: _containers.RepeatedCompositeFieldContainer[msgMapLogData3D]
    odometer: _containers.RepeatedCompositeFieldContainer[msgMapOdo]
    verticalCorrection: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, laserPosX: Optional[float] = ..., laserPosY: Optional[float] = ..., laserPosZ: Optional[float] = ..., laserStep: Optional[float] = ..., laserRangeMax: Optional[float] = ..., logData: Optional[Iterable[Union[msgMapLogData, Mapping]]] = ..., laserName: Optional[str] = ..., laserInstallHeight: Optional[float] = ..., odometer: Optional[Iterable[Union[msgMapOdo, Mapping]]] = ..., logData3D: Optional[Iterable[Union[msgMapLogData3D, Mapping]]] = ..., laserInstallYaw: Optional[float] = ..., laserInstallPitch: Optional[float] = ..., laserInstallRoll: Optional[float] = ..., imuData: Optional[Iterable[Union[_message_imu_pb2.msgIMU, Mapping]]] = ..., gnssData: Optional[Iterable[Union[_message_gnss_pb2.msgGnss, Mapping]]] = ..., laserType: Optional[int] = ..., factor: Optional[float] = ..., azimuthCorrection: Optional[Iterable[float]] = ..., verticalCorrection: Optional[Iterable[float]] = ..., allGnssData: Optional[Iterable[Union[_message_gnss_pb2.msgAllGnss, Mapping]]] = ..., localizationData: Optional[Iterable[Union[_message_localization_pb2.msgLocalization, Mapping]]] = ...) -> None: ...

class msgMapLogData(_message.Message):
    __slots__ = ["header", "laserBeamAngle", "laserBeamDist", "robotOdoW", "robotOdoX", "robotOdoY", "rssi"]
    HEADER_FIELD_NUMBER: ClassVar[int]
    LASERBEAMANGLE_FIELD_NUMBER: ClassVar[int]
    LASERBEAMDIST_FIELD_NUMBER: ClassVar[int]
    ROBOTODOW_FIELD_NUMBER: ClassVar[int]
    ROBOTODOX_FIELD_NUMBER: ClassVar[int]
    ROBOTODOY_FIELD_NUMBER: ClassVar[int]
    RSSI_FIELD_NUMBER: ClassVar[int]
    header: _message_header_pb2.msgHeader
    laserBeamAngle: _containers.RepeatedScalarFieldContainer[float]
    laserBeamDist: _containers.RepeatedScalarFieldContainer[float]
    robotOdoW: float
    robotOdoX: float
    robotOdoY: float
    rssi: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, robotOdoX: Optional[float] = ..., robotOdoY: Optional[float] = ..., robotOdoW: Optional[float] = ..., laserBeamDist: Optional[Iterable[float]] = ..., laserBeamAngle: Optional[Iterable[float]] = ..., rssi: Optional[Iterable[float]] = ..., header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ...) -> None: ...

class msgMapLogData3D(_message.Message):
    __slots__ = ["data", "firstAzimuth", "header", "intensity", "ring", "secondAzimuth", "timeoffset", "x", "y", "z"]
    DATA_FIELD_NUMBER: ClassVar[int]
    FIRSTAZIMUTH_FIELD_NUMBER: ClassVar[int]
    HEADER_FIELD_NUMBER: ClassVar[int]
    INTENSITY_FIELD_NUMBER: ClassVar[int]
    RING_FIELD_NUMBER: ClassVar[int]
    SECONDAZIMUTH_FIELD_NUMBER: ClassVar[int]
    TIMEOFFSET_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    data: _containers.RepeatedScalarFieldContainer[bytes]
    firstAzimuth: _containers.RepeatedScalarFieldContainer[float]
    header: _message_header_pb2.msgHeader
    intensity: _containers.RepeatedScalarFieldContainer[int]
    ring: _containers.RepeatedScalarFieldContainer[int]
    secondAzimuth: _containers.RepeatedScalarFieldContainer[float]
    timeoffset: _containers.RepeatedScalarFieldContainer[int]
    x: _containers.RepeatedScalarFieldContainer[float]
    y: _containers.RepeatedScalarFieldContainer[float]
    z: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, header: Optional[Union[_message_header_pb2.msgHeader, Mapping]] = ..., x: Optional[Iterable[float]] = ..., y: Optional[Iterable[float]] = ..., z: Optional[Iterable[float]] = ..., intensity: Optional[Iterable[int]] = ..., timeoffset: Optional[Iterable[int]] = ..., ring: Optional[Iterable[int]] = ..., data: Optional[Iterable[bytes]] = ..., firstAzimuth: Optional[Iterable[float]] = ..., secondAzimuth: Optional[Iterable[float]] = ...) -> None: ...

class msgMapOdo(_message.Message):
    __slots__ = ["odoVw", "odoVx", "odoVy", "odoW", "odoX", "odoY", "timestamp"]
    ODOVW_FIELD_NUMBER: ClassVar[int]
    ODOVX_FIELD_NUMBER: ClassVar[int]
    ODOVY_FIELD_NUMBER: ClassVar[int]
    ODOW_FIELD_NUMBER: ClassVar[int]
    ODOX_FIELD_NUMBER: ClassVar[int]
    ODOY_FIELD_NUMBER: ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: ClassVar[int]
    odoVw: float
    odoVx: float
    odoVy: float
    odoW: float
    odoX: float
    odoY: float
    timestamp: float
    def __init__(self, timestamp: Optional[float] = ..., odoX: Optional[float] = ..., odoY: Optional[float] = ..., odoW: Optional[float] = ..., odoVx: Optional[float] = ..., odoVy: Optional[float] = ..., odoVw: Optional[float] = ...) -> None: ...

class msgMapPos(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    Z_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., z: Optional[float] = ...) -> None: ...

class msgMapProperty(_message.Message):
    __slots__ = ["boolValue", "bytesValue", "doubleValue", "floatValue", "int32Value", "int64Value", "key", "stringValue", "tag", "type", "uint32Value", "uint64Value"]
    BOOLVALUE_FIELD_NUMBER: ClassVar[int]
    BYTESVALUE_FIELD_NUMBER: ClassVar[int]
    DOUBLEVALUE_FIELD_NUMBER: ClassVar[int]
    FLOATVALUE_FIELD_NUMBER: ClassVar[int]
    INT32VALUE_FIELD_NUMBER: ClassVar[int]
    INT64VALUE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    STRINGVALUE_FIELD_NUMBER: ClassVar[int]
    TAG_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    UINT32VALUE_FIELD_NUMBER: ClassVar[int]
    UINT64VALUE_FIELD_NUMBER: ClassVar[int]
    boolValue: bool
    bytesValue: bytes
    doubleValue: float
    floatValue: float
    int32Value: int
    int64Value: int
    key: str
    stringValue: str
    tag: str
    type: str
    uint32Value: int
    uint64Value: int
    def __init__(self, key: Optional[str] = ..., type: Optional[str] = ..., stringValue: Optional[str] = ..., boolValue: bool = ..., int32Value: Optional[int] = ..., uint32Value: Optional[int] = ..., int64Value: Optional[int] = ..., uint64Value: Optional[int] = ..., floatValue: Optional[float] = ..., doubleValue: Optional[float] = ..., bytesValue: Optional[bytes] = ..., tag: Optional[str] = ...) -> None: ...

class msgMapRssiPos(_message.Message):
    __slots__ = ["x", "y"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ...) -> None: ...

class msgReflectorPos(_message.Message):
    __slots__ = ["creationMethod", "type", "width", "x", "y"]
    CREATIONMETHOD_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    creationMethod: int
    type: str
    width: float
    x: float
    y: float
    def __init__(self, type: Optional[str] = ..., width: Optional[float] = ..., x: Optional[float] = ..., y: Optional[float] = ..., creationMethod: Optional[int] = ...) -> None: ...

class msgTagGroup(_message.Message):
    __slots__ = ["angle", "instanceName", "pos", "tagPosList", "tagType"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    POS_FIELD_NUMBER: ClassVar[int]
    TAGPOSLIST_FIELD_NUMBER: ClassVar[int]
    TAGTYPE_FIELD_NUMBER: ClassVar[int]
    angle: float
    instanceName: str
    pos: msgMapPos
    tagPosList: _containers.RepeatedCompositeFieldContainer[msgTagPos]
    tagType: str
    def __init__(self, tagType: Optional[str] = ..., instanceName: Optional[str] = ..., pos: Optional[Union[msgMapPos, Mapping]] = ..., angle: Optional[float] = ..., tagPosList: Optional[Iterable[Union[msgTagPos, Mapping]]] = ...) -> None: ...

class msgTagPos(_message.Message):
    __slots__ = ["advancedPointName", "angle", "property", "tagValue", "x", "y"]
    ADVANCEDPOINTNAME_FIELD_NUMBER: ClassVar[int]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    PROPERTY_FIELD_NUMBER: ClassVar[int]
    TAGVALUE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    advancedPointName: str
    angle: float
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    tagValue: int
    x: float
    y: float
    def __init__(self, tagValue: Optional[int] = ..., x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ..., advancedPointName: Optional[str] = ..., property: Optional[Iterable[Union[msgMapProperty, Mapping]]] = ...) -> None: ...

class msgTopoArea(_message.Message):
    __slots__ = ["advancedPointNames", "attribute", "className", "desc", "entranceVertexes", "instanceName", "posGroup", "property"]
    ADVANCEDPOINTNAMES_FIELD_NUMBER: ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: ClassVar[int]
    CLASSNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    ENTRANCEVERTEXES_FIELD_NUMBER: ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: ClassVar[int]
    POSGROUP_FIELD_NUMBER: ClassVar[int]
    PROPERTY_FIELD_NUMBER: ClassVar[int]
    advancedPointNames: _containers.RepeatedScalarFieldContainer[str]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    entranceVertexes: _containers.RepeatedScalarFieldContainer[int]
    instanceName: str
    posGroup: _containers.RepeatedCompositeFieldContainer[msgMapPos]
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: Optional[str] = ..., instanceName: Optional[str] = ..., advancedPointNames: Optional[Iterable[str]] = ..., posGroup: Optional[Iterable[Union[msgMapPos, Mapping]]] = ..., property: Optional[Iterable[Union[msgMapProperty, Mapping]]] = ..., desc: Optional[bytes] = ..., entranceVertexes: Optional[Iterable[int]] = ..., attribute: Optional[Union[msgMapAttribute, Mapping]] = ...) -> None: ...
