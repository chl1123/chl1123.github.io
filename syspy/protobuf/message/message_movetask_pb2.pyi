from typing import ClassVar, Iterable, Mapping, Optional, Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import wrappers_pb2 as _wrappers_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

import message_motorinfos_pb2 as _message_motorinfos_pb2

DESCRIPTOR: _descriptor.FileDescriptor


class Message_Container(_message.Message):
    __slots__ = ["container_name", "desc", "goods_id", "has_goods"]
    CONTAINER_NAME_FIELD_NUMBER: ClassVar[int]
    DESC_FIELD_NUMBER: ClassVar[int]
    GOODS_ID_FIELD_NUMBER: ClassVar[int]
    HAS_GOODS_FIELD_NUMBER: ClassVar[int]
    container_name: str
    desc: str
    goods_id: str
    has_goods: bool

    def __init__(self, container_name: Optional[str] = ..., goods_id: Optional[str] = ..., has_goods: bool = ...,
                 desc: Optional[str] = ...) -> None: ...


class Message_Module(_message.Message):
    __slots__ = ["action_body", "cargo_status", "module_name", "module_status", "motors"]

    class ModuleStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    ACTION_BODY_FIELD_NUMBER: ClassVar[int]
    CARGO_STATUS_FIELD_NUMBER: ClassVar[int]
    Canceled: Message_Module.ModuleStatus
    Completed: Message_Module.ModuleStatus
    Failed: Message_Module.ModuleStatus
    MODULE_NAME_FIELD_NUMBER: ClassVar[int]
    MODULE_STATUS_FIELD_NUMBER: ClassVar[int]
    MOTORS_FIELD_NUMBER: ClassVar[int]
    NONE: Message_Module.ModuleStatus
    Running: Message_Module.ModuleStatus
    Suspended: Message_Module.ModuleStatus
    action_body: str
    cargo_status: bool
    module_name: str
    module_status: Message_Module.ModuleStatus
    motors: _containers.RepeatedCompositeFieldContainer[_message_motorinfos_pb2.Message_MotorInfo]

    def __init__(self, module_name: Optional[str] = ...,
                 module_status: Optional[Union[Message_Module.ModuleStatus, str]] = ...,
                 action_body: Optional[str] = ..., cargo_status: bool = ..., motors: Optional[
                Iterable[Union[_message_motorinfos_pb2.Message_MotorInfo, Mapping]]] = ...) -> None: ...


class Message_MoveParam(_message.Message):
    __slots__ = ["bool_value", "bytes_value", "double_value", "float_value", "int32_value", "int64_value", "key",
                 "string_value", "uint32_value", "uint64_value"]
    BOOL_VALUE_FIELD_NUMBER: ClassVar[int]
    BYTES_VALUE_FIELD_NUMBER: ClassVar[int]
    DOUBLE_VALUE_FIELD_NUMBER: ClassVar[int]
    FLOAT_VALUE_FIELD_NUMBER: ClassVar[int]
    INT32_VALUE_FIELD_NUMBER: ClassVar[int]
    INT64_VALUE_FIELD_NUMBER: ClassVar[int]
    KEY_FIELD_NUMBER: ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: ClassVar[int]
    UINT32_VALUE_FIELD_NUMBER: ClassVar[int]
    UINT64_VALUE_FIELD_NUMBER: ClassVar[int]
    bool_value: bool
    bytes_value: bytes
    double_value: float
    float_value: float
    int32_value: int
    int64_value: int
    key: str
    string_value: str
    uint32_value: int
    uint64_value: int

    def __init__(self, key: Optional[str] = ..., string_value: Optional[str] = ..., bool_value: bool = ...,
                 int32_value: Optional[int] = ..., uint32_value: Optional[int] = ..., int64_value: Optional[int] = ...,
                 uint64_value: Optional[int] = ..., float_value: Optional[float] = ...,
                 double_value: Optional[float] = ..., bytes_value: Optional[bytes] = ...) -> None: ...


class Message_MovePath(_message.Message):
    __slots__ = ["find_path", "pose", "skill_name", "speed"]
    FIND_PATH_FIELD_NUMBER: ClassVar[int]
    POSE_FIELD_NUMBER: ClassVar[int]
    SKILL_NAME_FIELD_NUMBER: ClassVar[int]
    SPEED_FIELD_NUMBER: ClassVar[int]
    find_path: bool
    pose: _containers.RepeatedCompositeFieldContainer[Message_MovePose]
    skill_name: str
    speed: _containers.RepeatedCompositeFieldContainer[Message_MoveSpeed]

    def __init__(self, skill_name: Optional[str] = ...,
                 pose: Optional[Iterable[Union[Message_MovePose, Mapping]]] = ...,
                 speed: Optional[Iterable[Union[Message_MoveSpeed, Mapping]]] = ..., find_path: bool = ...) -> None: ...


class Message_MovePolygon(_message.Message):
    __slots__ = ["name", "point"]
    NAME_FIELD_NUMBER: ClassVar[int]
    POINT_FIELD_NUMBER: ClassVar[int]
    name: str
    point: _containers.RepeatedCompositeFieldContainer[Message_MovePolygonPoint]

    def __init__(self, point: Optional[Iterable[Union[Message_MovePolygonPoint, Mapping]]] = ...,
                 name: Optional[str] = ...) -> None: ...


class Message_MovePolygonPoint(_message.Message):
    __slots__ = ["x", "y"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float

    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ...) -> None: ...


class Message_MovePose(_message.Message):
    __slots__ = ["angle", "x", "y"]
    ANGLE_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    angle: float
    x: float
    y: float

    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., angle: Optional[float] = ...) -> None: ...


class Message_MoveSpeed(_message.Message):
    __slots__ = ["w", "x", "y"]
    W_FIELD_NUMBER: ClassVar[int]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    w: float
    x: float
    y: float

    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ..., w: Optional[float] = ...) -> None: ...


class Message_MoveStatus(_message.Message):
    """表示导航状态信息的模型类。

    Attributes:
        actual_reach_angle (float): 实际到达的角度，默认值为0.0。
        actual_reach_dist (float): 实际到达的距离，默认值为0.0。
        advance_regions (RepeatedCompositeFieldContainer[Message_MovePolygon]): 提前区域列表。
        area_name (RepeatedScalarFieldContainer[str]): 区域名称列表。
        block_id (int): 阻挡ID，默认值为0。
        block_reason (Message_MoveStatus.Reason): 阻挡原因。
        block_x (float): 阻挡点的x坐标，默认值为0.0。
        block_y (float): 阻挡点的y坐标，默认值为0.0。
        blocked (bool): 是否被阻挡，默认值为False。
        closest_label (str): 最近标签，默认为空字符串。
        closest_target (str): 最近目标，默认为空字符串。
        containers (RepeatedCompositeFieldContainer[Message_Container]): 容器列表。
        dist2goal (float): 到目标的距离，默认值为0.0。
        finished_path_name (RepeatedScalarFieldContainer[str]): 已完成路径名称列表。
        goods_region (Message_MovePolygon): 货物区域。
        info (str): 信息，默认为空字符串。
        modules (RepeatedCompositeFieldContainer[Message_Module]): 模块列表。
        nearest_obstacles (RepeatedCompositeFieldContainer[Message_NearestObs]): 最近障碍物列表。
        removed_regions (RepeatedCompositeFieldContainer[Message_MovePolygon]): 移除区域列表。
        robot_region (Message_MovePolygon): 机器人区域。
        robot_shape (Message_RobotShape): 机器人形状。
        running_status (Message_MoveStatus.RunningStatus): 运行状态。
        slow_id (int): 减速ID，默认值为0。
        slow_path (Message_MovePolygon): 减速路径。
        slow_reason (Message_MoveStatus.Reason): 减速原因。
        slow_x (float): 减速点的x坐标，默认值为0.0。
        slow_y (float): 减速点的y坐标，默认值为0.0。
        slowed (bool): 是否减速，默认值为False。
        stop_path (Message_MovePolygon): 停止路径。
        target_angle (float): 目标角度，默认值为0.0。
        target_dist (float): 到目标的距离，默认值为0.0。
        target_label (str): 目标标签，默认为空字符串。
        target_name (str): 目标名称，默认为空字符串。
        target_x (float): 目标点的x坐标，默认值为0.0。
        target_y (float): 目标点的y坐标，默认值为0.0。
        task_id (str): 任务ID，默认为空字符串。
        task_status (Message_MoveStatus.TaskStatus): 任务状态。
        task_status_package (Message_TaskStatusPackage): 任务状态包。
        task_type (Message_MoveStatus.TaskType): 任务类型。
        unfinished_path_name (RepeatedScalarFieldContainer[str]): 未完成路径名称列表。
    """
    __slots__ = ["actual_reach_angle", "actual_reach_dist", "advance_regions", "area_name", "block_id", "block_reason",
                 "block_x", "block_y", "blocked", "closest_label", "closest_target", "containers", "dist2goal",
                 "finished_path_name", "goods_region", "info", "modules", "nearest_obstacles", "removed_regions",
                 "robot_region", "robot_shape", "running_status", "slow_id", "slow_path", "slow_reason", "slow_x",
                 "slow_y", "slowed", "stop_path", "target_angle", "target_dist", "target_label", "target_name",
                 "target_x", "target_y", "task_id", "task_status", "task_status_package", "task_type",
                 "unfinished_path_name"]

    class Reason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        """表示障碍物检测原因的枚举类。

        Attributes:
            Ultrasonic (int): 超声波传感器检测到障碍物。
            Laser (int): 激光传感器检测到障碍物。
            Fallingdown (int): 下降检测到障碍物。
            Collision (int): 碰撞检测到障碍物。
            Infrared (int): 红外传感器检测到障碍物。
            Lock (int): 锁定检测到障碍物。
            APIObstacle (int): 通过API检测到障碍物。
            VirtualPoint (int): 虚拟点检测到障碍物。
            DepthCamera (int): 深度摄像头检测到障碍物。
            DistanceNode (int): 距离节点检测到障碍物。
            DiUltrasonic (int): 双超声波传感器检测到障碍物。
        """
        __slots__ = []

    class RunningStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []

    class TaskStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        """表示任务状态的枚举类。

        Attributes:
            StatusNone (int): 无状态。
            Waiting (int): 等待中。
            Running (int): 运行中。
            Suspended (int): 暂停中。
            Completed (int): 已完成。
            Failed (int): 失败。
            Canceled (int): 已取消。
            OverTime (int): 超时。
        """
        __slots__ = []

    class TaskType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        """表示任务类型的枚举类。

        Attributes:
            TypeNone (int): 无类型。
            GoPoint (int): 前往指定点。
            GoPointId (int): 前往指定点ID。
            GoId (int): 前往指定ID。
            Patrol (int): 巡逻。
            GoIntoShelf (int): 进入货架。
            TargetTracking (int): 目标跟踪。
            GoByOdometer (int): 通过里程计前往。
            GoAlongMagstripe (int): 沿磁条前往。
            Other (int): 其他类型。
        """
        __slots__ = []

    ACTUAL_REACH_ANGLE_FIELD_NUMBER: ClassVar[int]
    ACTUAL_REACH_DIST_FIELD_NUMBER: ClassVar[int]
    ADVANCE_REGIONS_FIELD_NUMBER: ClassVar[int]
    APIObstacle: Message_MoveStatus.Reason
    AREA_NAME_FIELD_NUMBER: ClassVar[int]
    BLOCKED_FIELD_NUMBER: ClassVar[int]
    BLOCK_ID_FIELD_NUMBER: ClassVar[int]
    BLOCK_REASON_FIELD_NUMBER: ClassVar[int]
    BLOCK_X_FIELD_NUMBER: ClassVar[int]
    BLOCK_Y_FIELD_NUMBER: ClassVar[int]
    CLOSEST_LABEL_FIELD_NUMBER: ClassVar[int]
    CLOSEST_TARGET_FIELD_NUMBER: ClassVar[int]
    CONTAINERS_FIELD_NUMBER: ClassVar[int]
    Canceled: Message_MoveStatus.TaskStatus
    Collision: Message_MoveStatus.Reason
    Completed: Message_MoveStatus.TaskStatus
    DIST2GOAL_FIELD_NUMBER: ClassVar[int]
    DepthCamera: Message_MoveStatus.Reason
    DiUltrasonic: Message_MoveStatus.Reason
    DistanceNode: Message_MoveStatus.Reason
    FINISHED_PATH_NAME_FIELD_NUMBER: ClassVar[int]
    Failed: Message_MoveStatus.TaskStatus
    Fallingdown: Message_MoveStatus.Reason
    GOODS_REGION_FIELD_NUMBER: ClassVar[int]
    GoAlongMagstripe: Message_MoveStatus.TaskType
    GoByOdometer: Message_MoveStatus.TaskType
    GoId: Message_MoveStatus.TaskType
    GoIntoShelf: Message_MoveStatus.TaskType
    GoPoint: Message_MoveStatus.TaskType
    GoPointId: Message_MoveStatus.TaskType
    INFO_FIELD_NUMBER: ClassVar[int]
    Infrared: Message_MoveStatus.Reason
    Laser: Message_MoveStatus.Reason
    Lock: Message_MoveStatus.Reason
    MODULES_FIELD_NUMBER: ClassVar[int]
    NEAREST_OBSTACLES_FIELD_NUMBER: ClassVar[int]
    Other: Message_MoveStatus.TaskType
    OverTime: Message_MoveStatus.TaskStatus
    Patrol: Message_MoveStatus.TaskType
    REMOVED_REGIONS_FIELD_NUMBER: ClassVar[int]
    RFailed: Message_MoveStatus.RunningStatus
    RFinished: Message_MoveStatus.RunningStatus
    RNearToGoal: Message_MoveStatus.RunningStatus
    RNone: Message_MoveStatus.RunningStatus
    ROBOT_REGION_FIELD_NUMBER: ClassVar[int]
    ROBOT_SHAPE_FIELD_NUMBER: ClassVar[int]
    RRunning: Message_MoveStatus.RunningStatus
    RUNNING_STATUS_FIELD_NUMBER: ClassVar[int]
    Running: Message_MoveStatus.TaskStatus
    SLOWED_FIELD_NUMBER: ClassVar[int]
    SLOW_ID_FIELD_NUMBER: ClassVar[int]
    SLOW_PATH_FIELD_NUMBER: ClassVar[int]
    SLOW_REASON_FIELD_NUMBER: ClassVar[int]
    SLOW_X_FIELD_NUMBER: ClassVar[int]
    SLOW_Y_FIELD_NUMBER: ClassVar[int]
    STOP_PATH_FIELD_NUMBER: ClassVar[int]
    StatusNone: Message_MoveStatus.TaskStatus
    Suspended: Message_MoveStatus.TaskStatus
    TARGET_ANGLE_FIELD_NUMBER: ClassVar[int]
    TARGET_DIST_FIELD_NUMBER: ClassVar[int]
    TARGET_LABEL_FIELD_NUMBER: ClassVar[int]
    TARGET_NAME_FIELD_NUMBER: ClassVar[int]
    TARGET_X_FIELD_NUMBER: ClassVar[int]
    TARGET_Y_FIELD_NUMBER: ClassVar[int]
    TASK_ID_FIELD_NUMBER: ClassVar[int]
    TASK_STATUS_FIELD_NUMBER: ClassVar[int]
    TASK_STATUS_PACKAGE_FIELD_NUMBER: ClassVar[int]
    TASK_TYPE_FIELD_NUMBER: ClassVar[int]
    TargetTracking: Message_MoveStatus.TaskType
    TypeNone: Message_MoveStatus.TaskType
    UNFINISHED_PATH_NAME_FIELD_NUMBER: ClassVar[int]
    Ultrasonic: Message_MoveStatus.Reason
    VirtualPoint: Message_MoveStatus.Reason
    Waiting: Message_MoveStatus.TaskStatus
    actual_reach_angle: float
    actual_reach_dist: float
    advance_regions: _containers.RepeatedCompositeFieldContainer[Message_MovePolygon]
    area_name: _containers.RepeatedScalarFieldContainer[str]
    block_id: int
    block_reason: Message_MoveStatus.Reason
    block_x: float
    block_y: float
    blocked: bool
    closest_label: str
    closest_target: str
    containers: _containers.RepeatedCompositeFieldContainer[Message_Container]
    dist2goal: float
    finished_path_name: _containers.RepeatedScalarFieldContainer[str]
    goods_region: Message_MovePolygon
    info: str
    modules: _containers.RepeatedCompositeFieldContainer[Message_Module]
    nearest_obstacles: _containers.RepeatedCompositeFieldContainer[Message_NearestObs]
    removed_regions: _containers.RepeatedCompositeFieldContainer[Message_MovePolygon]
    robot_region: Message_MovePolygon
    robot_shape: Message_RobotShape
    running_status: Message_MoveStatus.RunningStatus
    slow_id: int
    slow_path: Message_MovePolygon
    slow_reason: Message_MoveStatus.Reason
    slow_x: float
    slow_y: float
    slowed: bool
    stop_path: Message_MovePolygon
    target_angle: float
    target_dist: float
    target_label: str
    target_name: str
    target_x: float
    target_y: float
    task_id: str
    task_status: Message_MoveStatus.TaskStatus
    task_status_package: Message_TaskStatusPackage
    task_type: Message_MoveStatus.TaskType
    unfinished_path_name: _containers.RepeatedScalarFieldContainer[str]

    def __init__(self, blocked: bool = ..., block_x: Optional[float] = ..., block_y: Optional[float] = ...,
                 block_reason: Optional[Union[Message_MoveStatus.Reason, str]] = ..., target_name: Optional[str] = ...,
                 target_x: Optional[float] = ..., target_y: Optional[float] = ..., target_angle: Optional[float] = ...,
                 task_status: Optional[Union[Message_MoveStatus.TaskStatus, str]] = ...,
                 task_type: Optional[Union[Message_MoveStatus.TaskType, str]] = ...,
                 area_name: Optional[Iterable[str]] = ..., finished_path_name: Optional[Iterable[str]] = ...,
                 unfinished_path_name: Optional[Iterable[str]] = ..., block_id: Optional[int] = ...,
                 task_id: Optional[str] = ..., robot_region: Optional[Union[Message_MovePolygon, Mapping]] = ...,
                 goods_region: Optional[Union[Message_MovePolygon, Mapping]] = ...,
                 removed_regions: Optional[Iterable[Union[Message_MovePolygon, Mapping]]] = ...,
                 running_status: Optional[Union[Message_MoveStatus.RunningStatus, str]] = ...,
                 closest_target: Optional[str] = ..., actual_reach_dist: Optional[float] = ...,
                 actual_reach_angle: Optional[float] = ...,
                 robot_shape: Optional[Union[Message_RobotShape, Mapping]] = ..., slowed: bool = ...,
                 slow_x: Optional[float] = ..., slow_y: Optional[float] = ...,
                 slow_reason: Optional[Union[Message_MoveStatus.Reason, str]] = ..., slow_id: Optional[int] = ...,
                 stop_path: Optional[Union[Message_MovePolygon, Mapping]] = ...,
                 slow_path: Optional[Union[Message_MovePolygon, Mapping]] = ...,
                 modules: Optional[Iterable[Union[Message_Module, Mapping]]] = ...,
                 advance_regions: Optional[Iterable[Union[Message_MovePolygon, Mapping]]] = ...,
                 info: Optional[str] = ..., target_dist: Optional[float] = ...,
                 task_status_package: Optional[Union[Message_TaskStatusPackage, Mapping]] = ...,
                 target_label: Optional[str] = ..., closest_label: Optional[str] = ...,
                 nearest_obstacles: Optional[Iterable[Union[Message_NearestObs, Mapping]]] = ...,
                 containers: Optional[Iterable[Union[Message_Container, Mapping]]] = ...,
                 dist2goal: Optional[float] = ...) -> None: ...


class Message_MoveTask(_message.Message):
    __slots__ = ["block_dist", "dec_obs_expansion", "max_acc", "max_dec", "max_rot", "max_rot_acc", "max_rot_dec",
                 "max_speed", "move_angle", "move_dist", "move_time", "obs_dec_dist", "obs_dec_speed", "obs_expansion",
                 "obs_stop_dist", "params", "reach_angle", "reach_dist", "reach_method", "reach_vel_w", "reach_vel_x",
                 "reach_vel_y", "skill_name", "slowdown_dist", "source_name", "speed_w", "speed_x", "speed_y",
                 "target_angle", "target_name", "target_x", "target_y", "task_id"]
    BLOCK_DIST_FIELD_NUMBER: ClassVar[int]
    DEC_OBS_EXPANSION_FIELD_NUMBER: ClassVar[int]
    MAX_ACC_FIELD_NUMBER: ClassVar[int]
    MAX_DEC_FIELD_NUMBER: ClassVar[int]
    MAX_ROT_ACC_FIELD_NUMBER: ClassVar[int]
    MAX_ROT_DEC_FIELD_NUMBER: ClassVar[int]
    MAX_ROT_FIELD_NUMBER: ClassVar[int]
    MAX_SPEED_FIELD_NUMBER: ClassVar[int]
    MOVE_ANGLE_FIELD_NUMBER: ClassVar[int]
    MOVE_DIST_FIELD_NUMBER: ClassVar[int]
    MOVE_TIME_FIELD_NUMBER: ClassVar[int]
    OBS_DEC_DIST_FIELD_NUMBER: ClassVar[int]
    OBS_DEC_SPEED_FIELD_NUMBER: ClassVar[int]
    OBS_EXPANSION_FIELD_NUMBER: ClassVar[int]
    OBS_STOP_DIST_FIELD_NUMBER: ClassVar[int]
    PARAMS_FIELD_NUMBER: ClassVar[int]
    REACH_ANGLE_FIELD_NUMBER: ClassVar[int]
    REACH_DIST_FIELD_NUMBER: ClassVar[int]
    REACH_METHOD_FIELD_NUMBER: ClassVar[int]
    REACH_VEL_W_FIELD_NUMBER: ClassVar[int]
    REACH_VEL_X_FIELD_NUMBER: ClassVar[int]
    REACH_VEL_Y_FIELD_NUMBER: ClassVar[int]
    SKILL_NAME_FIELD_NUMBER: ClassVar[int]
    SLOWDOWN_DIST_FIELD_NUMBER: ClassVar[int]
    SOURCE_NAME_FIELD_NUMBER: ClassVar[int]
    SPEED_W_FIELD_NUMBER: ClassVar[int]
    SPEED_X_FIELD_NUMBER: ClassVar[int]
    SPEED_Y_FIELD_NUMBER: ClassVar[int]
    TARGET_ANGLE_FIELD_NUMBER: ClassVar[int]
    TARGET_NAME_FIELD_NUMBER: ClassVar[int]
    TARGET_X_FIELD_NUMBER: ClassVar[int]
    TARGET_Y_FIELD_NUMBER: ClassVar[int]
    TASK_ID_FIELD_NUMBER: ClassVar[int]
    block_dist: _wrappers_pb2.DoubleValue
    dec_obs_expansion: _wrappers_pb2.DoubleValue
    max_acc: _wrappers_pb2.DoubleValue
    max_dec: _wrappers_pb2.DoubleValue
    max_rot: _wrappers_pb2.DoubleValue
    max_rot_acc: _wrappers_pb2.DoubleValue
    max_rot_dec: _wrappers_pb2.DoubleValue
    max_speed: _wrappers_pb2.DoubleValue
    move_angle: _wrappers_pb2.DoubleValue
    move_dist: _wrappers_pb2.DoubleValue
    move_time: _wrappers_pb2.DoubleValue
    obs_dec_dist: _wrappers_pb2.DoubleValue
    obs_dec_speed: _wrappers_pb2.DoubleValue
    obs_expansion: _wrappers_pb2.DoubleValue
    obs_stop_dist: _wrappers_pb2.DoubleValue
    params: _containers.RepeatedCompositeFieldContainer[Message_MoveParam]
    reach_angle: _wrappers_pb2.DoubleValue
    reach_dist: _wrappers_pb2.DoubleValue
    reach_method: _wrappers_pb2.StringValue
    reach_vel_w: _wrappers_pb2.DoubleValue
    reach_vel_x: _wrappers_pb2.DoubleValue
    reach_vel_y: _wrappers_pb2.DoubleValue
    skill_name: str
    slowdown_dist: _wrappers_pb2.DoubleValue
    source_name: _wrappers_pb2.StringValue
    speed_w: _wrappers_pb2.DoubleValue
    speed_x: _wrappers_pb2.DoubleValue
    speed_y: _wrappers_pb2.DoubleValue
    target_angle: _wrappers_pb2.DoubleValue
    target_name: _wrappers_pb2.StringValue
    target_x: _wrappers_pb2.DoubleValue
    target_y: _wrappers_pb2.DoubleValue
    task_id: _wrappers_pb2.StringValue

    def __init__(self, skill_name: Optional[str] = ...,
                 target_x: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 target_y: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 target_angle: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 target_name: Optional[Union[_wrappers_pb2.StringValue, Mapping]] = ...,
                 reach_dist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 reach_angle: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 reach_method: Optional[Union[_wrappers_pb2.StringValue, Mapping]] = ...,
                 reach_vel_x: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 reach_vel_y: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 reach_vel_w: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 speed_x: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 speed_y: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 speed_w: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 max_speed: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 max_acc: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 max_rot: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 max_rot_acc: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 slowdown_dist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 block_dist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 move_dist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 move_angle: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 move_time: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 params: Optional[Iterable[Union[Message_MoveParam, Mapping]]] = ...,
                 task_id: Optional[Union[_wrappers_pb2.StringValue, Mapping]] = ...,
                 max_dec: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 max_rot_dec: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 obs_stop_dist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 obs_dec_dist: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 obs_dec_speed: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 obs_expansion: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 dec_obs_expansion: Optional[Union[_wrappers_pb2.DoubleValue, Mapping]] = ...,
                 source_name: Optional[Union[_wrappers_pb2.StringValue, Mapping]] = ...) -> None: ...


class Message_MoveTaskList(_message.Message):
    __slots__ = ["move_task_list"]
    MOVE_TASK_LIST_FIELD_NUMBER: ClassVar[int]
    move_task_list: _containers.RepeatedCompositeFieldContainer[Message_MoveTask]

    def __init__(self, move_task_list: Optional[Iterable[Union[Message_MoveTask, Mapping]]] = ...) -> None: ...


class Message_NearestObs(_message.Message):
    __slots__ = ["x", "y"]
    X_FIELD_NUMBER: ClassVar[int]
    Y_FIELD_NUMBER: ClassVar[int]
    x: float
    y: float

    def __init__(self, x: Optional[float] = ..., y: Optional[float] = ...) -> None: ...


class Message_RobotShape(_message.Message):
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

    def __init__(self, shape: Optional[int] = ..., head: Optional[float] = ..., tail: Optional[float] = ...,
                 width: Optional[float] = ..., radius: Optional[float] = ...) -> None: ...


class Message_TaskStatusInfo(_message.Message):
    __slots__ = ["status", "task_id", "type"]
    STATUS_FIELD_NUMBER: ClassVar[int]
    TASK_ID_FIELD_NUMBER: ClassVar[int]
    TYPE_FIELD_NUMBER: ClassVar[int]
    status: Message_MoveStatus.TaskStatus
    task_id: str
    type: Message_MoveStatus.TaskType

    def __init__(self, task_id: Optional[str] = ..., type: Optional[Union[Message_MoveStatus.TaskType, str]] = ...,
                 status: Optional[Union[Message_MoveStatus.TaskStatus, str]] = ...) -> None: ...


class Message_TaskStatusPackage(_message.Message):
    __slots__ = ["closest_label", "closest_target", "distance", "info", "percentage", "source_label", "source_name",
                 "target_label", "target_name", "task_status_list"]
    CLOSEST_LABEL_FIELD_NUMBER: ClassVar[int]
    CLOSEST_TARGET_FIELD_NUMBER: ClassVar[int]
    DISTANCE_FIELD_NUMBER: ClassVar[int]
    INFO_FIELD_NUMBER: ClassVar[int]
    PERCENTAGE_FIELD_NUMBER: ClassVar[int]
    SOURCE_LABEL_FIELD_NUMBER: ClassVar[int]
    SOURCE_NAME_FIELD_NUMBER: ClassVar[int]
    TARGET_LABEL_FIELD_NUMBER: ClassVar[int]
    TARGET_NAME_FIELD_NUMBER: ClassVar[int]
    TASK_STATUS_LIST_FIELD_NUMBER: ClassVar[int]
    closest_label: str
    closest_target: str
    distance: float
    info: str
    percentage: float
    source_label: str
    source_name: str
    target_label: str
    target_name: str
    task_status_list: _containers.RepeatedCompositeFieldContainer[Message_TaskStatusInfo]

    def __init__(self, task_status_list: Optional[Iterable[Union[Message_TaskStatusInfo, Mapping]]] = ...,
                 closest_target: Optional[str] = ..., source_name: Optional[str] = ...,
                 target_name: Optional[str] = ..., percentage: Optional[float] = ..., distance: Optional[float] = ...,
                 source_label: Optional[str] = ..., target_label: Optional[str] = ...,
                 closest_label: Optional[str] = ..., info: Optional[str] = ...) -> None: ...
