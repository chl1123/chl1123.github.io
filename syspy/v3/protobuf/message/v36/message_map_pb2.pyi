from google.protobuf import struct_pb2 as _struct_pb2
from . import message_header_pb2 as _message_header_pb2
from . import message_imu_pb2 as _message_imu_pb2
from . import message_gnss_pb2 as _message_gnss_pb2
from . import message_localization_pb2 as _message_localization_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgAdvancedArea(_message.Message):
    __slots__ = ["attribute", "className", "desc", "dir", "instanceName", "posGroup", "property"]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    DIR_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    POSGROUP_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    dir: float
    instanceName: str
    posGroup: _containers.RepeatedCompositeFieldContainer[msgMapPos]
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., posGroup: _Optional[_Iterable[_Union[msgMapPos, _Mapping]]] = ..., dir: _Optional[float] = ..., property: _Optional[_Iterable[_Union[msgMapProperty, _Mapping]]] = ..., desc: _Optional[bytes] = ..., attribute: _Optional[_Union[msgMapAttribute, _Mapping]] = ...) -> None: ...

class msgAdvancedCurve(_message.Message):
    __slots__ = ["attribute", "className", "controlPos1", "controlPos2", "controlPos3", "controlPos4", "desc", "endPos", "instanceName", "property", "startPos"]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    CONTROLPOS1_FIELD_NUMBER: _ClassVar[int]
    CONTROLPOS2_FIELD_NUMBER: _ClassVar[int]
    CONTROLPOS3_FIELD_NUMBER: _ClassVar[int]
    CONTROLPOS4_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    ENDPOS_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    STARTPOS_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., startPos: _Optional[str] = ..., endPos: _Optional[str] = ..., controlPos1: _Optional[_Union[msgMapPos, _Mapping]] = ..., controlPos2: _Optional[_Union[msgMapPos, _Mapping]] = ..., property: _Optional[_Iterable[_Union[msgMapProperty, _Mapping]]] = ..., desc: _Optional[bytes] = ..., controlPos3: _Optional[_Union[msgMapPos, _Mapping]] = ..., controlPos4: _Optional[_Union[msgMapPos, _Mapping]] = ..., attribute: _Optional[_Union[msgMapAttribute, _Mapping]] = ...) -> None: ...

class msgAdvancedLine(_message.Message):
    __slots__ = ["attribute", "className", "desc", "instanceName", "line", "property"]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    LINE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    instanceName: str
    line: msgMapLine
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., line: _Optional[_Union[msgMapLine, _Mapping]] = ..., property: _Optional[_Iterable[_Union[msgMapProperty, _Mapping]]] = ..., desc: _Optional[bytes] = ..., attribute: _Optional[_Union[msgMapAttribute, _Mapping]] = ...) -> None: ...

class msgAdvancedPoint(_message.Message):
    __slots__ = ["attribute", "className", "desc", "dir", "ignoreDir", "instanceName", "pos", "property"]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    DIR_FIELD_NUMBER: _ClassVar[int]
    IGNOREDIR_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    dir: float
    ignoreDir: bool
    instanceName: str
    pos: msgMapPos
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., pos: _Optional[_Union[msgMapPos, _Mapping]] = ..., dir: _Optional[float] = ..., property: _Optional[_Iterable[_Union[msgMapProperty, _Mapping]]] = ..., ignoreDir: bool = ..., desc: _Optional[bytes] = ..., attribute: _Optional[_Union[msgMapAttribute, _Mapping]] = ...) -> None: ...

class msgAutoGate(_message.Message):
    __slots__ = ["className", "desc", "dir", "height", "instanceName", "isEnabled", "jsonObject", "length", "pointNames", "width", "x", "y"]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    DIR_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    ISENABLED_FIELD_NUMBER: _ClassVar[int]
    JSONOBJECT_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    POINTNAMES_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., pointNames: _Optional[_Iterable[str]] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., dir: _Optional[float] = ..., width: _Optional[float] = ..., length: _Optional[float] = ..., height: _Optional[float] = ..., isEnabled: bool = ..., desc: _Optional[bytes] = ..., jsonObject: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class msgBinLocation(_message.Message):
    __slots__ = ["bindPoints", "className", "desc", "dir", "fleetExtra", "instanceName", "length", "recognitionFile", "width", "x", "y", "z"]
    BINDPOINTS_FIELD_NUMBER: _ClassVar[int]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    DIR_FIELD_NUMBER: _ClassVar[int]
    FLEETEXTRA_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    RECOGNITIONFILE_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    bindPoints: _containers.RepeatedCompositeFieldContainer[msgBindPoints]
    className: str
    desc: bytes
    dir: float
    fleetExtra: str
    instanceName: str
    length: float
    recognitionFile: str
    width: float
    x: float
    y: float
    z: float
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., recognitionFile: _Optional[str] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., dir: _Optional[float] = ..., width: _Optional[float] = ..., length: _Optional[float] = ..., bindPoints: _Optional[_Iterable[_Union[msgBindPoints, _Mapping]]] = ..., desc: _Optional[bytes] = ..., fleetExtra: _Optional[str] = ...) -> None: ...

class msgBinLocations(_message.Message):
    __slots__ = ["bin"]
    BIN_FIELD_NUMBER: _ClassVar[int]
    bin: _containers.RepeatedCompositeFieldContainer[msgBinLocation]
    def __init__(self, bin: _Optional[_Iterable[_Union[msgBinLocation, _Mapping]]] = ...) -> None: ...

class msgBindPoints(_message.Message):
    __slots__ = ["binTasks", "pointName", "recognitionSide"]
    BINTASKS_FIELD_NUMBER: _ClassVar[int]
    POINTNAME_FIELD_NUMBER: _ClassVar[int]
    RECOGNITIONSIDE_FIELD_NUMBER: _ClassVar[int]
    binTasks: _containers.RepeatedScalarFieldContainer[str]
    pointName: str
    recognitionSide: str
    def __init__(self, pointName: _Optional[str] = ..., binTasks: _Optional[_Iterable[str]] = ..., recognitionSide: _Optional[str] = ...) -> None: ...

class msgCallButton(_message.Message):
    __slots__ = ["className", "desc", "instanceName", "jsonObject", "loraAddress", "loraChannel", "pointName", "x", "y"]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    JSONOBJECT_FIELD_NUMBER: _ClassVar[int]
    LORAADDRESS_FIELD_NUMBER: _ClassVar[int]
    LORACHANNEL_FIELD_NUMBER: _ClassVar[int]
    POINTNAME_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    className: str
    desc: bytes
    instanceName: str
    jsonObject: _struct_pb2.Struct
    loraAddress: int
    loraChannel: int
    pointName: str
    x: float
    y: float
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., pointName: _Optional[str] = ..., loraAddress: _Optional[int] = ..., loraChannel: _Optional[int] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., desc: _Optional[bytes] = ..., jsonObject: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class msgCharger(_message.Message):
    __slots__ = ["className", "desc", "dir", "height", "instanceName", "jsonObject", "length", "pointName", "width", "x", "y"]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    DIR_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    JSONOBJECT_FIELD_NUMBER: _ClassVar[int]
    LENGTH_FIELD_NUMBER: _ClassVar[int]
    POINTNAME_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., pointName: _Optional[str] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., dir: _Optional[float] = ..., width: _Optional[float] = ..., length: _Optional[float] = ..., height: _Optional[float] = ..., desc: _Optional[bytes] = ..., jsonObject: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class msgCurrentMapInfo(_message.Message):
    __slots__ = ["currentMap", "currentMapEntries", "currentMapMd5", "currentTopoMd5", "workspaceTopoMd5"]
    CURRENTMAPENTRIES_FIELD_NUMBER: _ClassVar[int]
    CURRENTMAPMD5_FIELD_NUMBER: _ClassVar[int]
    CURRENTMAP_FIELD_NUMBER: _ClassVar[int]
    CURRENTTOPOMD5_FIELD_NUMBER: _ClassVar[int]
    WORKSPACETOPOMD5_FIELD_NUMBER: _ClassVar[int]
    currentMap: str
    currentMapEntries: _containers.RepeatedCompositeFieldContainer[msgMapFileMd5]
    currentMapMd5: str
    currentTopoMd5: str
    workspaceTopoMd5: str
    def __init__(self, currentMap: _Optional[str] = ..., currentMapEntries: _Optional[_Iterable[_Union[msgMapFileMd5, _Mapping]]] = ..., currentMapMd5: _Optional[str] = ..., currentTopoMd5: _Optional[str] = ..., workspaceTopoMd5: _Optional[str] = ...) -> None: ...

class msgExternalDevice(_message.Message):
    __slots__ = ["attribute", "className", "desc", "instanceName", "isEnabled", "property"]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    ISENABLED_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    instanceName: str
    isEnabled: bool
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., isEnabled: bool = ..., property: _Optional[_Iterable[_Union[msgMapProperty, _Mapping]]] = ..., desc: _Optional[bytes] = ..., attribute: _Optional[_Union[msgMapAttribute, _Mapping]] = ...) -> None: ...

class msgLiveRefPos(_message.Message):
    __slots__ = ["refPos"]
    REFPOS_FIELD_NUMBER: _ClassVar[int]
    refPos: _containers.RepeatedCompositeFieldContainer[msgReflectorPos]
    def __init__(self, refPos: _Optional[_Iterable[_Union[msgReflectorPos, _Mapping]]] = ...) -> None: ...

class msgMap(_message.Message):
    __slots__ = ["advancedAreaList", "advancedCurveList", "advancedLineList", "advancedPointList", "autoGateList", "bins", "callButtonList", "chargerList", "externalDeviceList", "header", "reflectorPosList", "tagGroupList", "topoAreaList"]
    ADVANCEDAREALIST_FIELD_NUMBER: _ClassVar[int]
    ADVANCEDCURVELIST_FIELD_NUMBER: _ClassVar[int]
    ADVANCEDLINELIST_FIELD_NUMBER: _ClassVar[int]
    ADVANCEDPOINTLIST_FIELD_NUMBER: _ClassVar[int]
    AUTOGATELIST_FIELD_NUMBER: _ClassVar[int]
    BINS_FIELD_NUMBER: _ClassVar[int]
    CALLBUTTONLIST_FIELD_NUMBER: _ClassVar[int]
    CHARGERLIST_FIELD_NUMBER: _ClassVar[int]
    EXTERNALDEVICELIST_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    REFLECTORPOSLIST_FIELD_NUMBER: _ClassVar[int]
    TAGGROUPLIST_FIELD_NUMBER: _ClassVar[int]
    TOPOAREALIST_FIELD_NUMBER: _ClassVar[int]
    advancedAreaList: _containers.RepeatedCompositeFieldContainer[msgAdvancedArea]
    advancedCurveList: _containers.RepeatedCompositeFieldContainer[msgAdvancedCurve]
    advancedLineList: _containers.RepeatedCompositeFieldContainer[msgAdvancedLine]
    advancedPointList: _containers.RepeatedCompositeFieldContainer[msgAdvancedPoint]
    autoGateList: _containers.RepeatedCompositeFieldContainer[msgAutoGate]
    bins: _containers.RepeatedCompositeFieldContainer[msgBinLocations]
    callButtonList: _containers.RepeatedCompositeFieldContainer[msgCallButton]
    chargerList: _containers.RepeatedCompositeFieldContainer[msgCharger]
    externalDeviceList: _containers.RepeatedCompositeFieldContainer[msgExternalDevice]
    header: msgMapHeader
    reflectorPosList: _containers.RepeatedCompositeFieldContainer[msgReflectorPos]
    tagGroupList: _containers.RepeatedCompositeFieldContainer[msgTagGroup]
    topoAreaList: _containers.RepeatedCompositeFieldContainer[msgTopoArea]
    def __init__(self, header: _Optional[_Union[msgMapHeader, _Mapping]] = ..., advancedPointList: _Optional[_Iterable[_Union[msgAdvancedPoint, _Mapping]]] = ..., advancedLineList: _Optional[_Iterable[_Union[msgAdvancedLine, _Mapping]]] = ..., advancedCurveList: _Optional[_Iterable[_Union[msgAdvancedCurve, _Mapping]]] = ..., advancedAreaList: _Optional[_Iterable[_Union[msgAdvancedArea, _Mapping]]] = ..., reflectorPosList: _Optional[_Iterable[_Union[msgReflectorPos, _Mapping]]] = ..., tagGroupList: _Optional[_Iterable[_Union[msgTagGroup, _Mapping]]] = ..., externalDeviceList: _Optional[_Iterable[_Union[msgExternalDevice, _Mapping]]] = ..., bins: _Optional[_Iterable[_Union[msgBinLocations, _Mapping]]] = ..., topoAreaList: _Optional[_Iterable[_Union[msgTopoArea, _Mapping]]] = ..., chargerList: _Optional[_Iterable[_Union[msgCharger, _Mapping]]] = ..., autoGateList: _Optional[_Iterable[_Union[msgAutoGate, _Mapping]]] = ..., callButtonList: _Optional[_Iterable[_Union[msgCallButton, _Mapping]]] = ...) -> None: ...

class msgMapAttribute(_message.Message):
    __slots__ = ["colorBrush", "colorFont", "colorPen", "description"]
    COLORBRUSH_FIELD_NUMBER: _ClassVar[int]
    COLORFONT_FIELD_NUMBER: _ClassVar[int]
    COLORPEN_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    colorBrush: int
    colorFont: int
    colorPen: int
    description: str
    def __init__(self, description: _Optional[str] = ..., colorPen: _Optional[int] = ..., colorBrush: _Optional[int] = ..., colorFont: _Optional[int] = ...) -> None: ...

class msgMapFileMd5(_message.Message):
    __slots__ = ["md5", "relativePath"]
    MD5_FIELD_NUMBER: _ClassVar[int]
    RELATIVEPATH_FIELD_NUMBER: _ClassVar[int]
    md5: str
    relativePath: str
    def __init__(self, relativePath: _Optional[str] = ..., md5: _Optional[str] = ...) -> None: ...

class msgMapHeader(_message.Message):
    __slots__ = ["mapName", "mapType", "maxPos", "minPos", "resolution", "version"]
    MAPNAME_FIELD_NUMBER: _ClassVar[int]
    MAPTYPE_FIELD_NUMBER: _ClassVar[int]
    MAXPOS_FIELD_NUMBER: _ClassVar[int]
    MINPOS_FIELD_NUMBER: _ClassVar[int]
    RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    mapName: str
    mapType: str
    maxPos: msgMapPos
    minPos: msgMapPos
    resolution: float
    version: str
    def __init__(self, mapType: _Optional[str] = ..., mapName: _Optional[str] = ..., minPos: _Optional[_Union[msgMapPos, _Mapping]] = ..., maxPos: _Optional[_Union[msgMapPos, _Mapping]] = ..., resolution: _Optional[float] = ..., version: _Optional[str] = ...) -> None: ...

class msgMapLine(_message.Message):
    __slots__ = ["endPos", "startPos"]
    ENDPOS_FIELD_NUMBER: _ClassVar[int]
    STARTPOS_FIELD_NUMBER: _ClassVar[int]
    endPos: msgMapPos
    startPos: msgMapPos
    def __init__(self, startPos: _Optional[_Union[msgMapPos, _Mapping]] = ..., endPos: _Optional[_Union[msgMapPos, _Mapping]] = ...) -> None: ...

class msgMapLog(_message.Message):
    __slots__ = ["allGnssData", "azimuthCorrection", "factor", "gnssData", "imuData", "laserInstallHeight", "laserInstallPitch", "laserInstallRoll", "laserInstallYaw", "laserName", "laserPosX", "laserPosY", "laserPosZ", "laserRangeMax", "laserStep", "laserType", "localizationData", "logData", "logData3D", "odometer", "verticalCorrection"]
    ALLGNSSDATA_FIELD_NUMBER: _ClassVar[int]
    AZIMUTHCORRECTION_FIELD_NUMBER: _ClassVar[int]
    FACTOR_FIELD_NUMBER: _ClassVar[int]
    GNSSDATA_FIELD_NUMBER: _ClassVar[int]
    IMUDATA_FIELD_NUMBER: _ClassVar[int]
    LASERINSTALLHEIGHT_FIELD_NUMBER: _ClassVar[int]
    LASERINSTALLPITCH_FIELD_NUMBER: _ClassVar[int]
    LASERINSTALLROLL_FIELD_NUMBER: _ClassVar[int]
    LASERINSTALLYAW_FIELD_NUMBER: _ClassVar[int]
    LASERNAME_FIELD_NUMBER: _ClassVar[int]
    LASERPOSX_FIELD_NUMBER: _ClassVar[int]
    LASERPOSY_FIELD_NUMBER: _ClassVar[int]
    LASERPOSZ_FIELD_NUMBER: _ClassVar[int]
    LASERRANGEMAX_FIELD_NUMBER: _ClassVar[int]
    LASERSTEP_FIELD_NUMBER: _ClassVar[int]
    LASERTYPE_FIELD_NUMBER: _ClassVar[int]
    LOCALIZATIONDATA_FIELD_NUMBER: _ClassVar[int]
    LOGDATA3D_FIELD_NUMBER: _ClassVar[int]
    LOGDATA_FIELD_NUMBER: _ClassVar[int]
    ODOMETER_FIELD_NUMBER: _ClassVar[int]
    VERTICALCORRECTION_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, laserPosX: _Optional[float] = ..., laserPosY: _Optional[float] = ..., laserPosZ: _Optional[float] = ..., laserStep: _Optional[float] = ..., laserRangeMax: _Optional[float] = ..., logData: _Optional[_Iterable[_Union[msgMapLogData, _Mapping]]] = ..., laserName: _Optional[str] = ..., laserInstallHeight: _Optional[float] = ..., odometer: _Optional[_Iterable[_Union[msgMapOdo, _Mapping]]] = ..., logData3D: _Optional[_Iterable[_Union[msgMapLogData3D, _Mapping]]] = ..., laserInstallYaw: _Optional[float] = ..., laserInstallPitch: _Optional[float] = ..., laserInstallRoll: _Optional[float] = ..., imuData: _Optional[_Iterable[_Union[_message_imu_pb2.msgIMU, _Mapping]]] = ..., gnssData: _Optional[_Iterable[_Union[_message_gnss_pb2.msgGnss, _Mapping]]] = ..., laserType: _Optional[int] = ..., factor: _Optional[float] = ..., azimuthCorrection: _Optional[_Iterable[float]] = ..., verticalCorrection: _Optional[_Iterable[float]] = ..., allGnssData: _Optional[_Iterable[_Union[_message_gnss_pb2.msgAllGnss, _Mapping]]] = ..., localizationData: _Optional[_Iterable[_Union[_message_localization_pb2.msgLocalization, _Mapping]]] = ...) -> None: ...

class msgMapLogData(_message.Message):
    __slots__ = ["header", "laserBeamAngle", "laserBeamDist", "robotOdoW", "robotOdoX", "robotOdoY", "rssi"]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    LASERBEAMANGLE_FIELD_NUMBER: _ClassVar[int]
    LASERBEAMDIST_FIELD_NUMBER: _ClassVar[int]
    ROBOTODOW_FIELD_NUMBER: _ClassVar[int]
    ROBOTODOX_FIELD_NUMBER: _ClassVar[int]
    ROBOTODOY_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    header: _message_header_pb2.msgHeader
    laserBeamAngle: _containers.RepeatedScalarFieldContainer[float]
    laserBeamDist: _containers.RepeatedScalarFieldContainer[float]
    robotOdoW: float
    robotOdoX: float
    robotOdoY: float
    rssi: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, robotOdoX: _Optional[float] = ..., robotOdoY: _Optional[float] = ..., robotOdoW: _Optional[float] = ..., laserBeamDist: _Optional[_Iterable[float]] = ..., laserBeamAngle: _Optional[_Iterable[float]] = ..., rssi: _Optional[_Iterable[float]] = ..., header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ...) -> None: ...

class msgMapLogData3D(_message.Message):
    __slots__ = ["data", "firstAzimuth", "header", "intensity", "ring", "secondAzimuth", "timeoffset", "x", "y", "z"]
    DATA_FIELD_NUMBER: _ClassVar[int]
    FIRSTAZIMUTH_FIELD_NUMBER: _ClassVar[int]
    HEADER_FIELD_NUMBER: _ClassVar[int]
    INTENSITY_FIELD_NUMBER: _ClassVar[int]
    RING_FIELD_NUMBER: _ClassVar[int]
    SECONDAZIMUTH_FIELD_NUMBER: _ClassVar[int]
    TIMEOFFSET_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, header: _Optional[_Union[_message_header_pb2.msgHeader, _Mapping]] = ..., x: _Optional[_Iterable[float]] = ..., y: _Optional[_Iterable[float]] = ..., z: _Optional[_Iterable[float]] = ..., intensity: _Optional[_Iterable[int]] = ..., timeoffset: _Optional[_Iterable[int]] = ..., ring: _Optional[_Iterable[int]] = ..., data: _Optional[_Iterable[bytes]] = ..., firstAzimuth: _Optional[_Iterable[float]] = ..., secondAzimuth: _Optional[_Iterable[float]] = ...) -> None: ...

class msgMapOdo(_message.Message):
    __slots__ = ["odoVw", "odoVx", "odoVy", "odoW", "odoX", "odoY", "timestamp"]
    ODOVW_FIELD_NUMBER: _ClassVar[int]
    ODOVX_FIELD_NUMBER: _ClassVar[int]
    ODOVY_FIELD_NUMBER: _ClassVar[int]
    ODOW_FIELD_NUMBER: _ClassVar[int]
    ODOX_FIELD_NUMBER: _ClassVar[int]
    ODOY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    odoVw: float
    odoVx: float
    odoVy: float
    odoW: float
    odoX: float
    odoY: float
    timestamp: float
    def __init__(self, timestamp: _Optional[float] = ..., odoX: _Optional[float] = ..., odoY: _Optional[float] = ..., odoW: _Optional[float] = ..., odoVx: _Optional[float] = ..., odoVy: _Optional[float] = ..., odoVw: _Optional[float] = ...) -> None: ...

class msgMapPos(_message.Message):
    __slots__ = ["x", "y", "z"]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class msgMapProperty(_message.Message):
    __slots__ = ["boolValue", "bytesValue", "doubleValue", "floatValue", "int32Value", "int64Value", "key", "stringValue", "tag", "type", "uint32Value", "uint64Value"]
    BOOLVALUE_FIELD_NUMBER: _ClassVar[int]
    BYTESVALUE_FIELD_NUMBER: _ClassVar[int]
    DOUBLEVALUE_FIELD_NUMBER: _ClassVar[int]
    FLOATVALUE_FIELD_NUMBER: _ClassVar[int]
    INT32VALUE_FIELD_NUMBER: _ClassVar[int]
    INT64VALUE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    STRINGVALUE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    UINT32VALUE_FIELD_NUMBER: _ClassVar[int]
    UINT64VALUE_FIELD_NUMBER: _ClassVar[int]
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
    def __init__(self, key: _Optional[str] = ..., type: _Optional[str] = ..., stringValue: _Optional[str] = ..., boolValue: bool = ..., int32Value: _Optional[int] = ..., uint32Value: _Optional[int] = ..., int64Value: _Optional[int] = ..., uint64Value: _Optional[int] = ..., floatValue: _Optional[float] = ..., doubleValue: _Optional[float] = ..., bytesValue: _Optional[bytes] = ..., tag: _Optional[str] = ...) -> None: ...

class msgMapRssiPos(_message.Message):
    __slots__ = ["x", "y"]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ...) -> None: ...

class msgReflectorPos(_message.Message):
    __slots__ = ["creationMethod", "type", "width", "x", "y"]
    CREATIONMETHOD_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    creationMethod: int
    type: str
    width: float
    x: float
    y: float
    def __init__(self, type: _Optional[str] = ..., width: _Optional[float] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., creationMethod: _Optional[int] = ...) -> None: ...

class msgTagGroup(_message.Message):
    __slots__ = ["angle", "instanceName", "pos", "tagPosList", "tagType"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    POS_FIELD_NUMBER: _ClassVar[int]
    TAGPOSLIST_FIELD_NUMBER: _ClassVar[int]
    TAGTYPE_FIELD_NUMBER: _ClassVar[int]
    angle: float
    instanceName: str
    pos: msgMapPos
    tagPosList: _containers.RepeatedCompositeFieldContainer[msgTagPos]
    tagType: str
    def __init__(self, tagType: _Optional[str] = ..., instanceName: _Optional[str] = ..., pos: _Optional[_Union[msgMapPos, _Mapping]] = ..., angle: _Optional[float] = ..., tagPosList: _Optional[_Iterable[_Union[msgTagPos, _Mapping]]] = ...) -> None: ...

class msgTagPos(_message.Message):
    __slots__ = ["advancedPointName", "angle", "property", "tagValue", "x", "y"]
    ADVANCEDPOINTNAME_FIELD_NUMBER: _ClassVar[int]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    TAGVALUE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    advancedPointName: str
    angle: float
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    tagValue: int
    x: float
    y: float
    def __init__(self, tagValue: _Optional[int] = ..., x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ..., advancedPointName: _Optional[str] = ..., property: _Optional[_Iterable[_Union[msgMapProperty, _Mapping]]] = ...) -> None: ...

class msgTopoArea(_message.Message):
    __slots__ = ["advancedPointNames", "attribute", "className", "desc", "entranceVertexes", "instanceName", "posGroup", "property"]
    ADVANCEDPOINTNAMES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    ENTRANCEVERTEXES_FIELD_NUMBER: _ClassVar[int]
    INSTANCENAME_FIELD_NUMBER: _ClassVar[int]
    POSGROUP_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    advancedPointNames: _containers.RepeatedScalarFieldContainer[str]
    attribute: msgMapAttribute
    className: str
    desc: bytes
    entranceVertexes: _containers.RepeatedScalarFieldContainer[int]
    instanceName: str
    posGroup: _containers.RepeatedCompositeFieldContainer[msgMapPos]
    property: _containers.RepeatedCompositeFieldContainer[msgMapProperty]
    def __init__(self, className: _Optional[str] = ..., instanceName: _Optional[str] = ..., advancedPointNames: _Optional[_Iterable[str]] = ..., posGroup: _Optional[_Iterable[_Union[msgMapPos, _Mapping]]] = ..., property: _Optional[_Iterable[_Union[msgMapProperty, _Mapping]]] = ..., desc: _Optional[bytes] = ..., entranceVertexes: _Optional[_Iterable[int]] = ..., attribute: _Optional[_Union[msgMapAttribute, _Mapping]] = ...) -> None: ...
