from google.protobuf import wrappers_pb2 as _wrappers_pb2
from . import message_motorinfos_pb2 as _message_motorinfos_pb2
from . import message_error_pb2 as _message_error_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgContainer(_message.Message):
    __slots__ = ["containerName", "desc", "goodsId", "hasGoods"]
    CONTAINERNAME_FIELD_NUMBER: _ClassVar[int]
    DESC_FIELD_NUMBER: _ClassVar[int]
    GOODSID_FIELD_NUMBER: _ClassVar[int]
    HASGOODS_FIELD_NUMBER: _ClassVar[int]
    containerName: str
    desc: str
    goodsId: str
    hasGoods: bool
    def __init__(self, containerName: _Optional[str] = ..., goodsId: _Optional[str] = ..., hasGoods: bool = ..., desc: _Optional[str] = ...) -> None: ...

class msgDualRobot(_message.Message):
    __slots__ = ["connectToFollower", "connectToLeader", "dtuStatusOk", "followerHasError", "followerId", "leaderId", "missFollower", "type"]
    class dualRobotType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    CONNECTTOFOLLOWER_FIELD_NUMBER: _ClassVar[int]
    CONNECTTOLEADER_FIELD_NUMBER: _ClassVar[int]
    DTUSTATUSOK_FIELD_NUMBER: _ClassVar[int]
    FOLLOWERHASERROR_FIELD_NUMBER: _ClassVar[int]
    FOLLOWERID_FIELD_NUMBER: _ClassVar[int]
    LEADERID_FIELD_NUMBER: _ClassVar[int]
    MISSFOLLOWER_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    connectToFollower: bool
    connectToLeader: bool
    dtuStatusOk: bool
    follower: msgDualRobot.dualRobotType
    followerHasError: bool
    followerId: str
    leader: msgDualRobot.dualRobotType
    leaderId: str
    missFollower: bool
    none: msgDualRobot.dualRobotType
    type: msgDualRobot.dualRobotType
    def __init__(self, type: _Optional[_Union[msgDualRobot.dualRobotType, str]] = ..., connectToLeader: bool = ..., connectToFollower: bool = ..., dtuStatusOk: bool = ..., missFollower: bool = ..., followerHasError: bool = ..., leaderId: _Optional[str] = ..., followerId: _Optional[str] = ...) -> None: ...

class msgMateRobot(_message.Message):
    __slots__ = ["futurePath", "robotShape"]
    FUTUREPATH_FIELD_NUMBER: _ClassVar[int]
    ROBOTSHAPE_FIELD_NUMBER: _ClassVar[int]
    futurePath: _containers.RepeatedCompositeFieldContainer[msgMovePose]
    robotShape: msgRobotShape
    def __init__(self, robotShape: _Optional[_Union[msgRobotShape, _Mapping]] = ..., futurePath: _Optional[_Iterable[_Union[msgMovePose, _Mapping]]] = ...) -> None: ...

class msgMates(_message.Message):
    __slots__ = ["matesList"]
    MATESLIST_FIELD_NUMBER: _ClassVar[int]
    matesList: _containers.RepeatedCompositeFieldContainer[msgMateRobot]
    def __init__(self, matesList: _Optional[_Iterable[_Union[msgMateRobot, _Mapping]]] = ...) -> None: ...

class msgModule(_message.Message):
    __slots__ = ["actionBody", "cargoStatus", "moduleName", "motors", "status"]
    class moduleStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ACTIONBODY_FIELD_NUMBER: _ClassVar[int]
    CARGOSTATUS_FIELD_NUMBER: _ClassVar[int]
    MODULENAME_FIELD_NUMBER: _ClassVar[int]
    MOTORS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    actionBody: str
    canceled: msgModule.moduleStatus
    cargoStatus: bool
    completed: msgModule.moduleStatus
    failed: msgModule.moduleStatus
    moduleName: str
    motors: _containers.RepeatedCompositeFieldContainer[_message_motorinfos_pb2.msgMotorInfo]
    none: msgModule.moduleStatus
    running: msgModule.moduleStatus
    status: msgModule.moduleStatus
    suspended: msgModule.moduleStatus
    def __init__(self, moduleName: _Optional[str] = ..., status: _Optional[_Union[msgModule.moduleStatus, str]] = ..., actionBody: _Optional[str] = ..., cargoStatus: bool = ..., motors: _Optional[_Iterable[_Union[_message_motorinfos_pb2.msgMotorInfo, _Mapping]]] = ...) -> None: ...

class msgMoveParam(_message.Message):
    __slots__ = ["boolValue", "bytesValue", "doubleValue", "floatValue", "int32Value", "int64Value", "key", "stringValue", "uint32Value", "uint64Value"]
    BOOLVALUE_FIELD_NUMBER: _ClassVar[int]
    BYTESVALUE_FIELD_NUMBER: _ClassVar[int]
    DOUBLEVALUE_FIELD_NUMBER: _ClassVar[int]
    FLOATVALUE_FIELD_NUMBER: _ClassVar[int]
    INT32VALUE_FIELD_NUMBER: _ClassVar[int]
    INT64VALUE_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    STRINGVALUE_FIELD_NUMBER: _ClassVar[int]
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
    uint32Value: int
    uint64Value: int
    def __init__(self, key: _Optional[str] = ..., stringValue: _Optional[str] = ..., boolValue: bool = ..., int32Value: _Optional[int] = ..., uint32Value: _Optional[int] = ..., int64Value: _Optional[int] = ..., uint64Value: _Optional[int] = ..., floatValue: _Optional[float] = ..., doubleValue: _Optional[float] = ..., bytesValue: _Optional[bytes] = ...) -> None: ...

class msgMovePath(_message.Message):
    __slots__ = ["findPath", "pose", "skillName", "speed"]
    FINDPATH_FIELD_NUMBER: _ClassVar[int]
    POSE_FIELD_NUMBER: _ClassVar[int]
    SKILLNAME_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    findPath: bool
    pose: _containers.RepeatedCompositeFieldContainer[msgMovePose]
    skillName: str
    speed: _containers.RepeatedCompositeFieldContainer[msgMoveSpeed]
    def __init__(self, skillName: _Optional[str] = ..., pose: _Optional[_Iterable[_Union[msgMovePose, _Mapping]]] = ..., speed: _Optional[_Iterable[_Union[msgMoveSpeed, _Mapping]]] = ..., findPath: bool = ...) -> None: ...

class msgMovePolygon(_message.Message):
    __slots__ = ["name", "point"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    POINT_FIELD_NUMBER: _ClassVar[int]
    name: str
    point: _containers.RepeatedCompositeFieldContainer[msgMovePolygonPoint]
    def __init__(self, point: _Optional[_Iterable[_Union[msgMovePolygonPoint, _Mapping]]] = ..., name: _Optional[str] = ...) -> None: ...

class msgMovePolygonPoint(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ...) -> None: ...

class msgMovePose(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    angle: float
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., angle: _Optional[float] = ...) -> None: ...

class msgMoveSpeed(_message.Message):
    __slots__ = ["w", "x", "y"]
    W_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    w: float
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., w: _Optional[float] = ...) -> None: ...

class msgMoveStatus(_message.Message):
    __slots__ = ["actualReachAngle", "actualReachDist", "advanceRegions", "areaName", "blockDevice", "blockReason", "blockX", "blockY", "blocked", "closestLabel", "closestTarget", "containers", "dist2goal", "dualRobot", "errors", "finishedPathName", "goodsRegion", "info", "mates", "modules", "moveTasks", "nearestObstacles", "removedRegions", "requestSpace", "robotRegion", "robotShape", "runningStatus", "safeCuttingsId", "slowDevice", "slowPath", "slowReason", "slowX", "slowY", "slowed", "stopPath", "targetAngle", "targetDist", "targetLabel", "targetName", "targetX", "targetY", "taskId", "taskStatus", "taskStatusPackage", "taskType", "unfinishedPathName"]
    class rStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class reason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class ErrorsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: _message_error_pb2.msgError
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[_message_error_pb2.msgError, _Mapping]] = ...) -> None: ...
    ACTUALREACHANGLE_FIELD_NUMBER: _ClassVar[int]
    ACTUALREACHDIST_FIELD_NUMBER: _ClassVar[int]
    ADVANCEREGIONS_FIELD_NUMBER: _ClassVar[int]
    AREANAME_FIELD_NUMBER: _ClassVar[int]
    BLOCKDEVICE_FIELD_NUMBER: _ClassVar[int]
    BLOCKED_FIELD_NUMBER: _ClassVar[int]
    BLOCKREASON_FIELD_NUMBER: _ClassVar[int]
    BLOCKX_FIELD_NUMBER: _ClassVar[int]
    BLOCKY_FIELD_NUMBER: _ClassVar[int]
    CLOSESTLABEL_FIELD_NUMBER: _ClassVar[int]
    CLOSESTTARGET_FIELD_NUMBER: _ClassVar[int]
    CONTAINERS_FIELD_NUMBER: _ClassVar[int]
    DIST2GOAL_FIELD_NUMBER: _ClassVar[int]
    DUALROBOT_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    FINISHEDPATHNAME_FIELD_NUMBER: _ClassVar[int]
    GOODSREGION_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    MATES_FIELD_NUMBER: _ClassVar[int]
    MODULES_FIELD_NUMBER: _ClassVar[int]
    MOVETASKS_FIELD_NUMBER: _ClassVar[int]
    NEARESTOBSTACLES_FIELD_NUMBER: _ClassVar[int]
    REMOVEDREGIONS_FIELD_NUMBER: _ClassVar[int]
    REQUESTSPACE_FIELD_NUMBER: _ClassVar[int]
    ROBOTREGION_FIELD_NUMBER: _ClassVar[int]
    ROBOTSHAPE_FIELD_NUMBER: _ClassVar[int]
    RUNNINGSTATUS_FIELD_NUMBER: _ClassVar[int]
    SAFECUTTINGSID_FIELD_NUMBER: _ClassVar[int]
    SLOWDEVICE_FIELD_NUMBER: _ClassVar[int]
    SLOWED_FIELD_NUMBER: _ClassVar[int]
    SLOWPATH_FIELD_NUMBER: _ClassVar[int]
    SLOWREASON_FIELD_NUMBER: _ClassVar[int]
    SLOWX_FIELD_NUMBER: _ClassVar[int]
    SLOWY_FIELD_NUMBER: _ClassVar[int]
    STOPPATH_FIELD_NUMBER: _ClassVar[int]
    TARGETANGLE_FIELD_NUMBER: _ClassVar[int]
    TARGETDIST_FIELD_NUMBER: _ClassVar[int]
    TARGETLABEL_FIELD_NUMBER: _ClassVar[int]
    TARGETNAME_FIELD_NUMBER: _ClassVar[int]
    TARGETX_FIELD_NUMBER: _ClassVar[int]
    TARGETY_FIELD_NUMBER: _ClassVar[int]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    TASKSTATUSPACKAGE_FIELD_NUMBER: _ClassVar[int]
    TASKSTATUS_FIELD_NUMBER: _ClassVar[int]
    TASKTYPE_FIELD_NUMBER: _ClassVar[int]
    UNFINISHEDPATHNAME_FIELD_NUMBER: _ClassVar[int]
    actualReachAngle: float
    actualReachDist: float
    advanceRegions: _containers.RepeatedCompositeFieldContainer[msgMovePolygon]
    apiObstacle: msgMoveStatus.reason
    areaName: _containers.RepeatedScalarFieldContainer[str]
    blockDevice: str
    blockReason: msgMoveStatus.reason
    blockX: float
    blockY: float
    blocked: bool
    closestLabel: str
    closestTarget: str
    collision: msgMoveStatus.reason
    completed: msgMoveStatus.status
    containers: _containers.RepeatedCompositeFieldContainer[msgContainer]
    depthCamera: msgMoveStatus.reason
    diSensor: msgMoveStatus.reason
    diUltrasonic: msgMoveStatus.reason
    dist2goal: float
    distanceNode: msgMoveStatus.reason
    dualRobot: msgDualRobot
    errors: _containers.MessageMap[str, _message_error_pb2.msgError]
    failed: msgMoveStatus.status
    finishedPathName: _containers.RepeatedScalarFieldContainer[str]
    goAlongMagstripe: msgMoveStatus.type
    goByOdometer: msgMoveStatus.type
    goId: msgMoveStatus.type
    goIntoShelf: msgMoveStatus.type
    goPoint: msgMoveStatus.type
    goPointId: msgMoveStatus.type
    goodsRegion: msgMovePolygon
    info: str
    laser: msgMoveStatus.reason
    lock: msgMoveStatus.reason
    mates: msgMates
    modules: _containers.RepeatedCompositeFieldContainer[msgModule]
    moveTasks: msgMoveTask
    nearestObstacles: _containers.RepeatedCompositeFieldContainer[msgPoint2d]
    other: msgMoveStatus.type
    patrol: msgMoveStatus.type
    rFailed: msgMoveStatus.rStatus
    rFinished: msgMoveStatus.rStatus
    rNearToGoal: msgMoveStatus.rStatus
    rNone: msgMoveStatus.rStatus
    rRunning: msgMoveStatus.rStatus
    removedRegions: _containers.RepeatedCompositeFieldContainer[msgMovePolygon]
    requestSpace: msgRequestSpace
    robotRegion: msgMovePolygon
    robotShape: msgRobotShape
    running: msgMoveStatus.status
    runningStatus: msgMoveStatus.rStatus
    safeCuttingsId: int
    slowDevice: str
    slowPath: msgMovePolygon
    slowReason: msgMoveStatus.reason
    slowX: float
    slowY: float
    slowed: bool
    statusNone: msgMoveStatus.status
    stopPath: msgMovePolygon
    suspended: msgMoveStatus.status
    targetAngle: float
    targetDist: float
    targetLabel: str
    targetName: str
    targetTracking: msgMoveStatus.type
    targetX: float
    targetY: float
    taskId: str
    taskStatus: msgMoveStatus.status
    taskStatusPackage: msgTaskStatusPackage
    taskType: msgMoveStatus.type
    typeNone: msgMoveStatus.type
    ultrasonic: msgMoveStatus.reason
    unfinishedPathName: _containers.RepeatedScalarFieldContainer[str]
    virtualPoint: msgMoveStatus.reason
    waiting: msgMoveStatus.status
    def __init__(self, blocked: bool = ..., blockX: _Optional[float] = ..., blockY: _Optional[float] = ..., blockReason: _Optional[_Union[msgMoveStatus.reason, str]] = ..., targetName: _Optional[str] = ..., targetX: _Optional[float] = ..., targetY: _Optional[float] = ..., targetAngle: _Optional[float] = ..., taskStatus: _Optional[_Union[msgMoveStatus.status, str]] = ..., taskType: _Optional[_Union[msgMoveStatus.type, str]] = ..., areaName: _Optional[_Iterable[str]] = ..., finishedPathName: _Optional[_Iterable[str]] = ..., unfinishedPathName: _Optional[_Iterable[str]] = ..., blockDevice: _Optional[str] = ..., taskId: _Optional[str] = ..., robotRegion: _Optional[_Union[msgMovePolygon, _Mapping]] = ..., goodsRegion: _Optional[_Union[msgMovePolygon, _Mapping]] = ..., removedRegions: _Optional[_Iterable[_Union[msgMovePolygon, _Mapping]]] = ..., runningStatus: _Optional[_Union[msgMoveStatus.rStatus, str]] = ..., closestTarget: _Optional[str] = ..., actualReachDist: _Optional[float] = ..., actualReachAngle: _Optional[float] = ..., robotShape: _Optional[_Union[msgRobotShape, _Mapping]] = ..., slowed: bool = ..., slowX: _Optional[float] = ..., slowY: _Optional[float] = ..., slowReason: _Optional[_Union[msgMoveStatus.reason, str]] = ..., slowDevice: _Optional[str] = ..., stopPath: _Optional[_Union[msgMovePolygon, _Mapping]] = ..., slowPath: _Optional[_Union[msgMovePolygon, _Mapping]] = ..., modules: _Optional[_Iterable[_Union[msgModule, _Mapping]]] = ..., advanceRegions: _Optional[_Iterable[_Union[msgMovePolygon, _Mapping]]] = ..., info: _Optional[str] = ..., targetDist: _Optional[float] = ..., taskStatusPackage: _Optional[_Union[msgTaskStatusPackage, _Mapping]] = ..., targetLabel: _Optional[str] = ..., closestLabel: _Optional[str] = ..., nearestObstacles: _Optional[_Iterable[_Union[msgPoint2d, _Mapping]]] = ..., containers: _Optional[_Iterable[_Union[msgContainer, _Mapping]]] = ..., dist2goal: _Optional[float] = ..., safeCuttingsId: _Optional[int] = ..., mates: _Optional[_Union[msgMates, _Mapping]] = ..., moveTasks: _Optional[_Union[msgMoveTask, _Mapping]] = ..., errors: _Optional[_Mapping[str, _message_error_pb2.msgError]] = ..., dualRobot: _Optional[_Union[msgDualRobot, _Mapping]] = ..., requestSpace: _Optional[_Union[msgRequestSpace, _Mapping]] = ...) -> None: ...

class msgMoveTask(_message.Message):
    __slots__ = ["blockDist", "decObsExpansion", "maxAcc", "maxDec", "maxRot", "maxRotAcc", "maxRotDec", "maxSpeed", "moveAngle", "moveDist", "moveTime", "obsDecDist", "obsDecSpeed", "obsExpansion", "obsStopDist", "params", "reachAngle", "reachDist", "reachMethod", "reachVelW", "reachVelX", "reachVelY", "skillName", "slowdownDist", "sourceName", "speedW", "speedX", "speedY", "targetAngle", "targetName", "targetX", "targetY", "taskId"]
    BLOCKDIST_FIELD_NUMBER: _ClassVar[int]
    DECOBSEXPANSION_FIELD_NUMBER: _ClassVar[int]
    MAXACC_FIELD_NUMBER: _ClassVar[int]
    MAXDEC_FIELD_NUMBER: _ClassVar[int]
    MAXROTACC_FIELD_NUMBER: _ClassVar[int]
    MAXROTDEC_FIELD_NUMBER: _ClassVar[int]
    MAXROT_FIELD_NUMBER: _ClassVar[int]
    MAXSPEED_FIELD_NUMBER: _ClassVar[int]
    MOVEANGLE_FIELD_NUMBER: _ClassVar[int]
    MOVEDIST_FIELD_NUMBER: _ClassVar[int]
    MOVETIME_FIELD_NUMBER: _ClassVar[int]
    OBSDECDIST_FIELD_NUMBER: _ClassVar[int]
    OBSDECSPEED_FIELD_NUMBER: _ClassVar[int]
    OBSEXPANSION_FIELD_NUMBER: _ClassVar[int]
    OBSSTOPDIST_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    REACHANGLE_FIELD_NUMBER: _ClassVar[int]
    REACHDIST_FIELD_NUMBER: _ClassVar[int]
    REACHMETHOD_FIELD_NUMBER: _ClassVar[int]
    REACHVELW_FIELD_NUMBER: _ClassVar[int]
    REACHVELX_FIELD_NUMBER: _ClassVar[int]
    REACHVELY_FIELD_NUMBER: _ClassVar[int]
    SKILLNAME_FIELD_NUMBER: _ClassVar[int]
    SLOWDOWNDIST_FIELD_NUMBER: _ClassVar[int]
    SOURCENAME_FIELD_NUMBER: _ClassVar[int]
    SPEEDW_FIELD_NUMBER: _ClassVar[int]
    SPEEDX_FIELD_NUMBER: _ClassVar[int]
    SPEEDY_FIELD_NUMBER: _ClassVar[int]
    TARGETANGLE_FIELD_NUMBER: _ClassVar[int]
    TARGETNAME_FIELD_NUMBER: _ClassVar[int]
    TARGETX_FIELD_NUMBER: _ClassVar[int]
    TARGETY_FIELD_NUMBER: _ClassVar[int]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    blockDist: _wrappers_pb2.DoubleValue
    decObsExpansion: _wrappers_pb2.DoubleValue
    maxAcc: _wrappers_pb2.DoubleValue
    maxDec: _wrappers_pb2.DoubleValue
    maxRot: _wrappers_pb2.DoubleValue
    maxRotAcc: _wrappers_pb2.DoubleValue
    maxRotDec: _wrappers_pb2.DoubleValue
    maxSpeed: _wrappers_pb2.DoubleValue
    moveAngle: _wrappers_pb2.DoubleValue
    moveDist: _wrappers_pb2.DoubleValue
    moveTime: _wrappers_pb2.DoubleValue
    obsDecDist: _wrappers_pb2.DoubleValue
    obsDecSpeed: _wrappers_pb2.DoubleValue
    obsExpansion: _wrappers_pb2.DoubleValue
    obsStopDist: _wrappers_pb2.DoubleValue
    params: _containers.RepeatedCompositeFieldContainer[msgMoveParam]
    reachAngle: _wrappers_pb2.DoubleValue
    reachDist: _wrappers_pb2.DoubleValue
    reachMethod: _wrappers_pb2.StringValue
    reachVelW: _wrappers_pb2.DoubleValue
    reachVelX: _wrappers_pb2.DoubleValue
    reachVelY: _wrappers_pb2.DoubleValue
    skillName: str
    slowdownDist: _wrappers_pb2.DoubleValue
    sourceName: _wrappers_pb2.StringValue
    speedW: _wrappers_pb2.DoubleValue
    speedX: _wrappers_pb2.DoubleValue
    speedY: _wrappers_pb2.DoubleValue
    targetAngle: _wrappers_pb2.DoubleValue
    targetName: _wrappers_pb2.StringValue
    targetX: _wrappers_pb2.DoubleValue
    targetY: _wrappers_pb2.DoubleValue
    taskId: _wrappers_pb2.StringValue
    def __init__(self, skillName: _Optional[str] = ..., targetX: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., targetY: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., targetAngle: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., targetName: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., reachDist: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., reachAngle: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., reachMethod: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., reachVelX: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., reachVelY: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., reachVelW: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., speedX: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., speedY: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., speedW: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., maxSpeed: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., maxAcc: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., maxRot: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., maxRotAcc: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., slowdownDist: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., blockDist: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., moveDist: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., moveAngle: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., moveTime: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., params: _Optional[_Iterable[_Union[msgMoveParam, _Mapping]]] = ..., taskId: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., maxDec: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., maxRotDec: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., obsStopDist: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., obsDecDist: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., obsDecSpeed: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., obsExpansion: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., decObsExpansion: _Optional[_Union[_wrappers_pb2.DoubleValue, _Mapping]] = ..., sourceName: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ...) -> None: ...

class msgMoveTaskList(_message.Message):
    __slots__ = ["moveTaskList"]
    MOVETASKLIST_FIELD_NUMBER: _ClassVar[int]
    moveTaskList: _containers.RepeatedCompositeFieldContainer[msgMoveTask]
    def __init__(self, moveTaskList: _Optional[_Iterable[_Union[msgMoveTask, _Mapping]]] = ...) -> None: ...

class msgPoint2d(_message.Message):
    __slots__ = ["x", "y"]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ...) -> None: ...

class msgPolygon2d(_message.Message):
    __slots__ = ["points", "type"]
    class polygon2dType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    POINTS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    concave: msgPolygon2d.polygon2dType
    other: msgPolygon2d.polygon2dType
    points: _containers.RepeatedCompositeFieldContainer[msgPoint2d]
    rect: msgPolygon2d.polygon2dType
    type: msgPolygon2d.polygon2dType
    def __init__(self, points: _Optional[_Iterable[_Union[msgPoint2d, _Mapping]]] = ..., type: _Optional[_Union[msgPolygon2d.polygon2dType, str]] = ...) -> None: ...

class msgRequestSpace(_message.Message):
    __slots__ = ["reason", "spatialZones", "status", "unitId"]
    class resourcesStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    REASON_FIELD_NUMBER: _ClassVar[int]
    SPATIALZONES_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    UNITID_FIELD_NUMBER: _ClassVar[int]
    accept: msgRequestSpace.resourcesStatus
    apply: msgRequestSpace.resourcesStatus
    none: msgRequestSpace.resourcesStatus
    reason: str
    spatialZones: _containers.RepeatedCompositeFieldContainer[msgPolygon2d]
    status: msgRequestSpace.resourcesStatus
    unitId: str
    def __init__(self, status: _Optional[_Union[msgRequestSpace.resourcesStatus, str]] = ..., reason: _Optional[str] = ..., spatialZones: _Optional[_Iterable[_Union[msgPolygon2d, _Mapping]]] = ..., unitId: _Optional[str] = ...) -> None: ...

class msgRobotShape(_message.Message):
    __slots__ = ["head", "points", "radius", "shape", "tail", "width"]
    HEAD_FIELD_NUMBER: _ClassVar[int]
    POINTS_FIELD_NUMBER: _ClassVar[int]
    RADIUS_FIELD_NUMBER: _ClassVar[int]
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    TAIL_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    head: float
    points: _containers.RepeatedCompositeFieldContainer[msgMovePolygonPoint]
    radius: float
    shape: int
    tail: float
    width: float
    def __init__(self, shape: _Optional[int] = ..., head: _Optional[float] = ..., tail: _Optional[float] = ..., width: _Optional[float] = ..., radius: _Optional[float] = ..., points: _Optional[_Iterable[_Union[msgMovePolygonPoint, _Mapping]]] = ...) -> None: ...

class msgTaskStatusInfo(_message.Message):
    __slots__ = ["status", "taskId", "type"]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    status: msgMoveStatus.status
    taskId: str
    type: msgMoveStatus.type
    def __init__(self, taskId: _Optional[str] = ..., type: _Optional[_Union[msgMoveStatus.type, str]] = ..., status: _Optional[_Union[msgMoveStatus.status, str]] = ...) -> None: ...

class msgTaskStatusPackage(_message.Message):
    __slots__ = ["closestLabel", "closestTarget", "distance", "info", "percentage", "sourceLabel", "sourceName", "targetLabel", "targetName", "taskStatusList"]
    CLOSESTLABEL_FIELD_NUMBER: _ClassVar[int]
    CLOSESTTARGET_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    SOURCELABEL_FIELD_NUMBER: _ClassVar[int]
    SOURCENAME_FIELD_NUMBER: _ClassVar[int]
    TARGETLABEL_FIELD_NUMBER: _ClassVar[int]
    TARGETNAME_FIELD_NUMBER: _ClassVar[int]
    TASKSTATUSLIST_FIELD_NUMBER: _ClassVar[int]
    closestLabel: str
    closestTarget: str
    distance: float
    info: str
    percentage: float
    sourceLabel: str
    sourceName: str
    targetLabel: str
    targetName: str
    taskStatusList: _containers.RepeatedCompositeFieldContainer[msgTaskStatusInfo]
    def __init__(self, taskStatusList: _Optional[_Iterable[_Union[msgTaskStatusInfo, _Mapping]]] = ..., closestTarget: _Optional[str] = ..., sourceName: _Optional[str] = ..., targetName: _Optional[str] = ..., percentage: _Optional[float] = ..., distance: _Optional[float] = ..., sourceLabel: _Optional[str] = ..., targetLabel: _Optional[str] = ..., closestLabel: _Optional[str] = ..., info: _Optional[str] = ...) -> None: ...
