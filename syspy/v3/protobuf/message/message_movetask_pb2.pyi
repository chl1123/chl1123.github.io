from google.protobuf import wrappers_pb2 as _wrappers_pb2
import message_motorinfos_pb2 as _message_motorinfos_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar, Iterable, Mapping, Optional, Union

DESCRIPTOR: _descriptor.FileDescriptor

class msgContainer(_message.Message):
    __slots__ = ["containerName", "desc", "goodsId", "hasGoods"]
    CONTAINERNAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    GOODSID_FIELD_NUMBER: ClassVar[int]
    HASGOODS_FIELD_NUMBER: ClassVar[int]
    containerName: str
    desc: str
    goodsId: str
    hasGoods: bool
    def __init__(self, containerName: Optional[str] = ..., goodsId: Optional[str] = ..., hasGoods: bool = ..., desc: Optional[str] = ...) -> None: ...

class msgMateRobot(_message.Message):
    __slots__ = ["futurePath", "robotShape"]
    FUTUREPATH_FIELD_NUMBER: ClassVar[int]
    ROBOTSHAPE_FIELD_NUMBER: ClassVar[int]
    futurePath: _containers.RepeatedCompositeFieldContainer[msgMovePose]
    robotShape: msgRobotShape
    def __init__(self, robotShape: Optional[Union[msgRobotShape, Mapping]] = ..., futurePath: Optional[Iterable[Union[msgMovePose, Mapping]]] = ...) -> None: ...

class msgMates(_message.Message):
    __slots__ = ["matesList"]
    MATESLIST_FIELD_NUMBER: ClassVar[int]
    matesList: _containers.RepeatedCompositeFieldContainer[msgMateRobot]
    def __init__(self, matesList: Optional[Iterable[Union[msgMateRobot, Mapping]]] = ...) -> None: ...

class msgModule(_message.Message):
    __slots__ = ["actionBody", "cargoStatus", "moduleName", "motors", "status"]
    class moduleStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ACTIONBODY_FIELD_NUMBER: ClassVar[int]
    CARGOSTATUS_FIELD_NUMBER: ClassVar[int]
    MODULENAME_FIELD_NUMBER: ClassVar[int]
    MOTORS_FIELD_NUMBER: ClassVar[int]
    STATUS_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, moduleName: Optional[str] = ..., status: Optional[Union[msgModule.moduleStatus, str]] = ..., actionBody: Optional[str] = ..., cargoStatus: bool = ..., motors: Optional[Iterable[Union[_message_motorinfos_pb2.msgMotorInfo, Mapping]]] = ...) -> None: ...

class msgMoveParam(_message.Message):
    __slots__ = ["boolValue", "bytesValue", "doubleValue", "floatValue", "int32Value", "int64Value", "key", "stringValue", "uint32Value", "uint64Value"]
    BOOLVALUE_FIELD_NUMBER: ClassVar[int]
    BYTESVALUE_FIELD_NUMBER: ClassVar[int]
    DOUBLEVALUE_FIELD_NUMBER: ClassVar[int]
    FLOATVALUE_FIELD_NUMBER: ClassVar[int]
    INT32VALUE_FIELD_NUMBER: ClassVar[int]
    INT64VALUE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    STRINGVALUE_FIELD_NUMBER: ClassVar[int]
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
    uint32Value: int
    uint64Value: int
    def __init__(self, key: Optional[str] = ..., stringValue: Optional[str] = ..., boolValue: bool = ..., int32Value: Optional[int] = ..., uint32Value: Optional[int] = ..., int64Value: Optional[int] = ..., uint64Value: Optional[int] = ..., floatValue: Optional[float] = ..., doubleValue: Optional[float] = ..., bytesValue: Optional[bytes] = ...) -> None: ...

class msgMovePath(_message.Message):
    __slots__ = ["findPath", "pose", "skillName", "speed"]
    FINDPATH_FIELD_NUMBER: ClassVar[int]
    POSE_FIELD_NUMBER: ClassVar[int]
    SKILLNAME_FIELD_NUMBER: ClassVar[int]
    SPEED_FIELD_NUMBER: ClassVar[int]
    findPath: bool
    pose: _containers.RepeatedCompositeFieldContainer[msgMovePose]
    skillName: str
    speed: _containers.RepeatedCompositeFieldContainer[msgMoveSpeed]
    def __init__(self, skillName: Optional[str] = ..., pose: Optional[Iterable[Union[msgMovePose, Mapping]]] = ..., speed: Optional[Iterable[Union[msgMoveSpeed, Mapping]]] = ..., findPath: bool = ...) -> None: ...

class msgMovePolygon(_message.Message):
    __slots__ = ["name", "point"]
    NAME_FIELD_NUMBER: ClassVar[int]
    POINT_FIELD_NUMBER: ClassVar[int]
    name: str
    point: _containers.RepeatedCompositeFieldContainer[msgMovePolygonPoint]
    def __init__(self, point: Optional[Iterable[Union[msgMovePolygonPoint, Mapping]]] = ..., name: Optional[str] = ...) -> None: ...

class msgMovePolygonPoint(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ...) -> None: ...

class msgMovePose(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ...) -> None: ...

class msgMoveSpeed(_message.Message):
    __slots__ = ["w", "x", "y"]
    W_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    w: float
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., w: Optional[float] = ...) -> None: ...

class msgMoveStatus(_message.Message):
    __slots__ = ["actualReachAngle", "actualReachDist", "advanceRegions", "areaName", "blockDevice", "blockReason", "blockX", "blockY", "blocked", "closestLabel", "closestTarget", "containers", "dist2goal", "finishedPathName", "goodsRegion", "info", "mates", "modules", "moveTasks", "nearestObstacles", "removedRegions", "robotRegion", "robotShape", "runningStatus", "safeCuttingsId", "slowDevice", "slowPath", "slowReason", "slowX", "slowY", "slowed", "stopPath", "targetAngle", "targetDist", "targetLabel", "targetName", "targetX", "targetY", "taskId", "taskStatus", "taskStatusPackage", "taskType", "unfinishedPathName"]
    class rStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class reason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ACTUALREACHANGLE_FIELD_NUMBER: ClassVar[int]
    ACTUALREACHDIST_FIELD_NUMBER: ClassVar[int]
    ADVANCEREGIONS_FIELD_NUMBER: ClassVar[int]
    AREANAME_FIELD_NUMBER: ClassVar[int]
    BLOCKDEVICE_FIELD_NUMBER: ClassVar[int]
    BLOCKED_FIELD_NUMBER: ClassVar[int]
    BLOCKREASON_FIELD_NUMBER: ClassVar[int]
    BLOCKX_FIELD_NUMBER: ClassVar[int]
    BLOCKY_FIELD_NUMBER: ClassVar[int]
    CLOSESTLABEL_FIELD_NUMBER: ClassVar[int]
    CLOSESTTARGET_FIELD_NUMBER: ClassVar[int]
    CONTAINERS_FIELD_NUMBER: ClassVar[int]
    DIST2GOAL_FIELD_NUMBER: ClassVar[int]
    FINISHEDPATHNAME_FIELD_NUMBER: ClassVar[int]
    GOODSREGION_FIELD_NUMBER: ClassVar[int]
    INFO_FIELD_NUMBER: ClassVar[int]
    MATES_FIELD_NUMBER: ClassVar[int]
    MODULES_FIELD_NUMBER: ClassVar[int]
    MOVETASKS_FIELD_NUMBER: ClassVar[int]
    NEARESTOBSTACLES_FIELD_NUMBER: ClassVar[int]
    REMOVEDREGIONS_FIELD_NUMBER: ClassVar[int]
    ROBOTREGION_FIELD_NUMBER: ClassVar[int]
    ROBOTSHAPE_FIELD_NUMBER: ClassVar[int]
    RUNNINGSTATUS_FIELD_NUMBER: ClassVar[int]
    SAFECUTTINGSID_FIELD_NUMBER: ClassVar[int]
    SLOWDEVICE_FIELD_NUMBER: ClassVar[int]
    SLOWED_FIELD_NUMBER: ClassVar[int]
    SLOWPATH_FIELD_NUMBER: ClassVar[int]
    SLOWREASON_FIELD_NUMBER: ClassVar[int]
    SLOWX_FIELD_NUMBER: ClassVar[int]
    SLOWY_FIELD_NUMBER: ClassVar[int]
    STOPPATH_FIELD_NUMBER: ClassVar[int]
    TARGETANGLE_FIELD_NUMBER: ClassVar[int]
    TARGETDIST_FIELD_NUMBER: ClassVar[int]
    TARGETLABEL_FIELD_NUMBER: ClassVar[int]
    TARGETNAME_FIELD_NUMBER: ClassVar[int]
    TARGETX_FIELD_NUMBER: ClassVar[int]
    TARGETY_FIELD_NUMBER: ClassVar[int]
    TASKID_FIELD_NUMBER: ClassVar[int]
    TASKSTATUSPACKAGE_FIELD_NUMBER: ClassVar[int]
    TASKSTATUS_FIELD_NUMBER: ClassVar[int]
    TASKTYPE_FIELD_NUMBER: ClassVar[int]
    UNFINISHEDPATHNAME_FIELD_NUMBER: ClassVar[int]
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
    canceled: msgMoveStatus.status
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
    nearestObstacles: _containers.RepeatedCompositeFieldContainer[msgNearestObs]
    other: msgMoveStatus.type
    overTime: msgMoveStatus.status
    patrol: msgMoveStatus.type
    rFailed: msgMoveStatus.rStatus
    rFinished: msgMoveStatus.rStatus
    rNearToGoal: msgMoveStatus.rStatus
    rNone: msgMoveStatus.rStatus
    rRunning: msgMoveStatus.rStatus
    removedRegions: _containers.RepeatedCompositeFieldContainer[msgMovePolygon]
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
    def __init__(self, blocked: bool = ..., blockX: Optional[float] = ..., blockY: Optional[float] = ..., blockReason: Optional[Union[msgMoveStatus.reason, str]] = ..., targetName: Optional[str] = ..., targetX: Optional[float] = ..., targetY: Optional[float] = ..., targetAngle: Optional[float] = ..., taskStatus: Optional[Union[msgMoveStatus.status, str]] = ..., taskType: Optional[Union[msgMoveStatus.type, str]] = ..., areaName: Optional[Iterable[str]] = ..., finishedPathName: Optional[Iterable[str]] = ..., unfinishedPathName: Optional[Iterable[str]] = ..., blockDevice: Optional[str] = ..., taskId: Optional[str] = ..., robotRegion: Optional[Union[msgMovePolygon, Mapping]] = ..., goodsRegion: Optional[Union[msgMovePolygon, Mapping]] = ..., removedRegions: Optional[Iterable[Union[msgMovePolygon, Mapping]]] = ..., runningStatus: Optional[Union[msgMoveStatus.rStatus, str]] = ..., closestTarget: Optional[str] = ..., actualReachDist: Optional[float] = ..., actualReachAngle: Optional[float] = ..., robotShape: Optional[Union[msgRobotShape, Mapping]] = ..., slowed: bool = ..., slowX: Optional[float] = ..., slowY: Optional[float] = ..., slowReason: Optional[Union[msgMoveStatus.reason, str]] = ..., slowDevice: Optional[str] = ..., stopPath: Optional[Union[msgMovePolygon, Mapping]] = ..., slowPath: Optional[Union[msgMovePolygon, Mapping]] = ..., modules: Optional[Iterable[Union[msgModule, Mapping]]] = ..., advanceRegions: Optional[Iterable[Union[msgMovePolygon, Mapping]]] = ..., info: Optional[str] = ..., targetDist: Optional[float] = ..., taskStatusPackage: Optional[Union[msgTaskStatusPackage, Mapping]] = ..., targetLabel: Optional[str] = ..., closestLabel: Optional[str] = ..., nearestObstacles: Optional[Iterable[Union[msgNearestObs, Mapping]]] = ..., containers: Optional[Iterable[Union[msgContainer, Mapping]]] = ..., dist2goal: Optional[float] = ..., safeCuttingsId: Optional[int] = ..., mates: Optional[Union[msgMates, Mapping]] = ..., moveTasks: Optional[Union[msgMoveTask, Mapping]] = ...) -> None: ...

class msgMoveTask(_message.Message):
    __slots__ = ["blockDist", "decObsExpansion", "maxAcc", "maxDec", "maxRot", "maxRotAcc", "maxRotDec", "maxSpeed", "moveAngle", "moveDist", "moveTime", "obsDecDist", "obsDecSpeed", "obsExpansion", "obsStopDist", "params", "reachAngle", "reachDist", "reachMethod", "reachVelW", "reachVelX", "reachVelY", "skillName", "slowdownDist", "sourceName", "speedW", "speedX", "speedY", "targetAngle", "targetName", "targetX", "targetY", "taskId"]
    BLOCKDIST_FIELD_NUMBER: ClassVar[int]
    DECOBSEXPANSION_FIELD_NUMBER: ClassVar[int]
    MAXACC_FIELD_NUMBER: ClassVar[int]
    MAXDEC_FIELD_NUMBER: ClassVar[int]
    MAXROTACC_FIELD_NUMBER: ClassVar[int]
    MAXROTDEC_FIELD_NUMBER: ClassVar[int]
    MAXROT_FIELD_NUMBER: ClassVar[int]
    MAXSPEED_FIELD_NUMBER: ClassVar[int]
    MOVEANGLE_FIELD_NUMBER: ClassVar[int]
    MOVEDIST_FIELD_NUMBER: ClassVar[int]
    MOVETIME_FIELD_NUMBER: ClassVar[int]
    OBSDECDIST_FIELD_NUMBER: ClassVar[int]
    OBSDECSPEED_FIELD_NUMBER: ClassVar[int]
    OBSEXPANSION_FIELD_NUMBER: ClassVar[int]
    OBSSTOPDIST_FIELD_NUMBER: ClassVar[int]
    PARAMS_FIELD_NUMBER: ClassVar[int]
    REACHANGLE_FIELD_NUMBER: ClassVar[int]
    REACHDIST_FIELD_NUMBER: ClassVar[int]
    REACHMETHOD_FIELD_NUMBER: ClassVar[int]
    REACHVELW_FIELD_NUMBER: ClassVar[int]
    REACHVELX_FIELD_NUMBER: ClassVar[int]
    REACHVELY_FIELD_NUMBER: ClassVar[int]
    SKILLNAME_FIELD_NUMBER: ClassVar[int]
    SLOWDOWNDIST_FIELD_NUMBER: ClassVar[int]
    SOURCENAME_FIELD_NUMBER: ClassVar[int]
    SPEEDW_FIELD_NUMBER: ClassVar[int]
    SPEEDX_FIELD_NUMBER: ClassVar[int]
    SPEEDY_FIELD_NUMBER: ClassVar[int]
    TARGETANGLE_FIELD_NUMBER: ClassVar[int]
    TARGETNAME_FIELD_NUMBER: ClassVar[int]
    TARGETX_FIELD_NUMBER: ClassVar[int]
    TARGETY_FIELD_NUMBER: ClassVar[int]
    TASKID_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, skillName: Optional[str] = ..., targetX: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., targetY: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., targetAngle: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., targetName: Optional[Union[_wrappers_pb2.StringValue, Mapping]] = ..., reachDist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., reachAngle: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., reachMethod: Optional[Union[_wrappers_pb2.StringValue, Mapping]] = ..., reachVelX: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., reachVelY: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., reachVelW: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., speedX: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., speedY: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., speedW: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., maxSpeed: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., maxAcc: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., maxRot: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., maxRotAcc: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., slowdownDist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., blockDist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., moveDist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., moveAngle: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., moveTime: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., params: Optional[Iterable[Union[msgMoveParam, Mapping]]] = ..., taskId: Optional[Union[_wrappers_pb2.StringValue, Mapping]] = ..., maxDec: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., maxRotDec: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., obsStopDist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., obsDecDist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., obsDecSpeed: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., obsExpansion: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., decObsExpansion: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ..., sourceName: Optional[Union[_wrappers_pb2.StringValue, Mapping]] = ...) -> None: ...

class msgMoveTaskList(_message.Message):
    __slots__ = ["moveTaskList"]
    MOVETASKLIST_FIELD_NUMBER: ClassVar[int]
    moveTaskList: _containers.RepeatedCompositeFieldContainer[msgMoveTask]
    def __init__(self, moveTaskList: Optional[Iterable[Union[msgMoveTask, Mapping]]] = ...) -> None: ...

class msgNearestObs(_message.Message):
    __slots__ = ["x", "y"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float
    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ...) -> None: ...

class msgRobotShape(_message.Message):
    __slots__ = ["head", "points", "radius", "shape", "tail", "width"]
    HEAD_FIELD_NUMBER: ClassVar[int]
    POINTS_FIELD_NUMBER: ClassVar[int]
    RADIUS_FIELD_NUMBER: ClassVar[int]
    SHAPE_FIELD_NUMBER: ClassVar[int]
    TAIL_FIELD_NUMBER: ClassVar[int]
    WIDTH_FIELD_NUMBER: ClassVar[int]
    head: float
    points: _containers.RepeatedCompositeFieldContainer[msgMovePolygonPoint]
    radius: float
    shape: int
    tail: float
    width: float
    def __init__(self, shape: Optional[int] = ..., head: Optional[float] = ..., tail: Optional[float] = ..., width: Optional[float] = ..., radius: Optional[float] = ..., points: Optional[Iterable[Union[msgMovePolygonPoint, Mapping]]] = ...) -> None: ...

class msgTaskStatusInfo(_message.Message):
    __slots__ = ["status", "taskId", "type"]
    STATUS_FIELD_NUMBER: ClassVar[int]
    TASKID_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    status: msgMoveStatus.status
    taskId: str
    type: msgMoveStatus.type
    def __init__(self, taskId: Optional[str] = ..., type: Optional[Union[msgMoveStatus.type, str]] = ..., status: Optional[Union[msgMoveStatus.status, str]] = ...) -> None: ...

class msgTaskStatusPackage(_message.Message):
    __slots__ = ["closestLabel", "closestTarget", "distance", "info", "percentage", "sourceLabel", "sourceName", "targetLabel", "targetName", "taskStatusList"]
    CLOSESTLABEL_FIELD_NUMBER: ClassVar[int]
    CLOSESTTARGET_FIELD_NUMBER: ClassVar[int]
    DISTANCE_FIELD_NUMBER: ClassVar[int]
    INFO_FIELD_NUMBER: ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: ClassVar[int]
    SOURCELABEL_FIELD_NUMBER: ClassVar[int]
    SOURCENAME_FIELD_NUMBER: ClassVar[int]
    TARGETLABEL_FIELD_NUMBER: ClassVar[int]
    TARGETNAME_FIELD_NUMBER: ClassVar[int]
    TASKSTATUSLIST_FIELD_NUMBER: ClassVar[int]
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
    def __init__(self, taskStatusList: Optional[Iterable[Union[msgTaskStatusInfo, Mapping]]] = ..., closestTarget: Optional[str] = ..., sourceName: Optional[str] = ..., targetName: Optional[str] = ..., percentage: Optional[float] = ..., distance: Optional[float] = ..., sourceLabel: Optional[str] = ..., targetLabel: Optional[str] = ..., closestLabel: Optional[str] = ..., info: Optional[str] = ...) -> None: ...
