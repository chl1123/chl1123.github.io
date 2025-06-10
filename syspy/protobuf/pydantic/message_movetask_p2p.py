# This is an automatically generated file, please do not change
# gen by protobuf_to_pydantic[v0.3.0.3](https://github.com/so1n/protobuf_to_pydantic)
# Protobuf Version: 5.29.2
# Pydantic Version: 2.10.4
from .message_motorinfos_p2p import Message_MotorInfo
from enum import IntEnum
from google.protobuf.message import Message  # type: ignore
from google.protobuf.wrappers_pb2 import DoubleValue  # type: ignore
from google.protobuf.wrappers_pb2 import StringValue  # type: ignore
from protobuf_to_pydantic.customer_validator import check_one_of
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator
import typing


class Message_MoveParam(BaseModel):
    _one_of_dict = {
        "Message_MoveParam.oneof_value": {
            "fields": {
                "bool_value",
                "bytes_value",
                "double_value",
                "float_value",
                "int32_value",
                "int64_value",
                "string_value",
                "uint32_value",
                "uint64_value",
            }
        }
    }
    one_of_validator = model_validator(mode="before")(check_one_of)
    key: str = Field(default="")
    string_value: str = Field(default="")
    bool_value: bool = Field(default=False)
    int32_value: int = Field(default=0)
    uint32_value: int = Field(default=0)
    int64_value: int = Field(default=0)
    uint64_value: int = Field(default=0)
    float_value: float = Field(default=0.0)
    double_value: float = Field(default=0.0)
    bytes_value: bytes = Field(default=b"")


class Message_MoveTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    skill_name: str = Field(default="")
    target_x: DoubleValue = Field(default_factory=DoubleValue)
    target_y: DoubleValue = Field(default_factory=DoubleValue)
    target_angle: DoubleValue = Field(default_factory=DoubleValue)
    target_name: StringValue = Field(default_factory=StringValue)
    reach_dist: DoubleValue = Field(default_factory=DoubleValue)
    reach_angle: DoubleValue = Field(default_factory=DoubleValue)
    reach_method: StringValue = Field(default_factory=StringValue)
    reach_vel_x: DoubleValue = Field(default_factory=DoubleValue)
    reach_vel_y: DoubleValue = Field(default_factory=DoubleValue)
    reach_vel_w: DoubleValue = Field(default_factory=DoubleValue)
    speed_x: DoubleValue = Field(default_factory=DoubleValue)
    speed_y: DoubleValue = Field(default_factory=DoubleValue)
    speed_w: DoubleValue = Field(default_factory=DoubleValue)
    max_speed: DoubleValue = Field(default_factory=DoubleValue)
    max_acc: DoubleValue = Field(default_factory=DoubleValue)
    max_rot: DoubleValue = Field(default_factory=DoubleValue)
    max_rot_acc: DoubleValue = Field(default_factory=DoubleValue)
    slowdown_dist: DoubleValue = Field(default_factory=DoubleValue)
    block_dist: DoubleValue = Field(default_factory=DoubleValue)
    move_dist: DoubleValue = Field(default_factory=DoubleValue)
    move_angle: DoubleValue = Field(default_factory=DoubleValue)
    move_time: DoubleValue = Field(default_factory=DoubleValue)
    params: typing.List[Message_MoveParam] = Field(default_factory=list)
    task_id: StringValue = Field(default_factory=StringValue)
    max_dec: DoubleValue = Field(default_factory=DoubleValue)
    max_rot_dec: DoubleValue = Field(default_factory=DoubleValue)
    obs_stop_dist: DoubleValue = Field(default_factory=DoubleValue)
    obs_dec_dist: DoubleValue = Field(default_factory=DoubleValue)
    obs_dec_speed: DoubleValue = Field(default_factory=DoubleValue)
    obs_expansion: DoubleValue = Field(default_factory=DoubleValue)
    dec_obs_expansion: DoubleValue = Field(default_factory=DoubleValue)
    source_name: StringValue = Field(default_factory=StringValue)


class Message_MoveTaskList(BaseModel):
    move_task_list: typing.List[Message_MoveTask] = Field(default_factory=list)


class Message_MovePolygonPoint(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)


class Message_MovePolygon(BaseModel):
    point: typing.List[Message_MovePolygonPoint] = Field(default_factory=list)
    name: str = Field(default="")


class Message_RobotShape(BaseModel):
    shape: int = Field(default=0)
    head: float = Field(default=0.0)
    tail: float = Field(default=0.0)
    width: float = Field(default=0.0)
    radius: float = Field(default=0.0)


class Message_NearestObs(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)


class Message_Container(BaseModel):
    container_name: str = Field(default="")
    goods_id: str = Field(default="")
    has_goods: bool = Field(default=False)
    desc: str = Field(default="")


class Message_Module(BaseModel):
    class ModuleStatus(IntEnum):
        NONE = 0
        Running = 1
        Suspended = 2
        Completed = 3
        Failed = 4
        Canceled = 5

    module_name: str = Field(default="")
    module_status: ModuleStatus = Field(default=0)
    action_body: str = Field(default="")  # 现在执行action的json
    cargo_status: bool = Field(default=False)
    motors: typing.List[Message_MotorInfo] = Field(default_factory=list)


class Message_TaskStatusInfo(BaseModel):
    task_id: str = Field(default="")
    type: "Message_MoveStatus.TaskType" = Field(default=0)
    status: "Message_MoveStatus.TaskStatus" = Field(default=0)


class Message_TaskStatusPackage(BaseModel):
    task_status_list: typing.List[Message_TaskStatusInfo] = Field(
        default_factory=list
    )  # 任务状态队列
    closest_target: str = Field(default="")  # 最近点
    source_name: str = Field(default="")  # 上个去过的点
    target_name: str = Field(default="")  # 下个要去的点
    percentage: float = Field(default=0.0)  # source_name -> target_name 的 百分比
    distance: float = Field(default=0.0)  # 车离当前线路的最近距离
    source_label: str = Field(default="")
    target_label: str = Field(default="")
    closest_label: str = Field(default="")
    info: str = Field(
        default=""
    )  # 提示说明(特殊状态改变可以加一些说明，如faild，可描述具体原因)


class Message_MoveStatus(BaseModel):
    class Reason(IntEnum):
        Ultrasonic = 0
        Laser = 1
        Fallingdown = 2
        Collision = 3
        Infrared = 4
        Lock = 5
        APIObstacle = 6
        VirtualPoint = 7
        DepthCamera = 8
        DistanceNode = 9
        DiUltrasonic = 10

    class TaskStatus(IntEnum):
        StatusNone = 0
        Waiting = 1
        Running = 2
        Suspended = 3
        Completed = 4
        Failed = 5
        Canceled = 6
        OverTime = 7

    class TaskType(IntEnum):
        TypeNone = 0
        GoPoint = 1
        GoPointId = 2
        GoId = 3
        Patrol = 4
        GoIntoShelf = 5
        TargetTracking = 6
        GoByOdometer = 7
        GoAlongMagstripe = 8
        Other = 100

    class RunningStatus(IntEnum):
        RNone = 0
        RRunning = 1
        RNearToGoal = 2
        RFinished = 3
        RFailed = 4

    blocked: bool = Field(default=False)
    block_x: float = Field(default=0.0)
    block_y: float = Field(default=0.0)
    block_reason: "Message_MoveStatus.Reason" = Field(default=0)
    target_name: str = Field(default="")
    target_x: float = Field(default=0.0)
    target_y: float = Field(default=0.0)
    target_angle: float = Field(default=0.0)
    task_status: "Message_MoveStatus.TaskStatus" = Field(default=0)
    task_type: "Message_MoveStatus.TaskType" = Field(default=0)
    area_name: typing.List[str] = Field(default_factory=list)
    finished_path_name: typing.List[str] = Field(default_factory=list)
    unfinished_path_name: typing.List[str] = Field(default_factory=list)
    block_id: int = Field(default=0)
    task_id: str = Field(default="")
    robot_region: typing.Optional[Message_MovePolygon] = None
    goods_region: typing.Optional[Message_MovePolygon] = None
    removed_regions: typing.List[Message_MovePolygon] = Field(default_factory=list)
    running_status: "Message_MoveStatus.RunningStatus" = Field(default=0)
    closest_target: str = Field(default="")
    actual_reach_dist: float = Field(default=0.0)
    actual_reach_angle: float = Field(default=0.0)
    robot_shape: typing.Optional[Message_RobotShape] = None
    slowed: bool = Field(default=False)
    slow_x: float = Field(default=0.0)
    slow_y: float = Field(default=0.0)
    slow_reason: "Message_MoveStatus.Reason" = Field(default=0)
    slow_id: int = Field(default=0)
    stop_path: typing.Optional[Message_MovePolygon] = None
    slow_path: typing.Optional[Message_MovePolygon] = None
    modules: typing.List[Message_Module] = Field(default_factory=list)
    advance_regions: typing.List[Message_MovePolygon] = Field(default_factory=list)
    info: str = Field(default="")
    target_dist: float = Field(default=0.0)
    task_status_package: typing.Optional[Message_TaskStatusPackage] = None
    target_label: str = Field(default="")
    closest_label: str = Field(default="")
    nearest_obstacles: typing.List[Message_NearestObs] = Field(default_factory=list)
    containers: typing.List[Message_Container] = Field(default_factory=list)
    dist2goal: float = Field(default=0.0)


class Message_MoveSpeed(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    w: float = Field(default=0.0)


class Message_MovePose(BaseModel):
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)
    angle: float = Field(default=0.0)


class Message_MovePath(BaseModel):
    skill_name: str = Field(default="")
    pose: typing.List[Message_MovePose] = Field(default_factory=list)
    speed: typing.List[Message_MoveSpeed] = Field(default_factory=list)
    find_path: bool = Field(default=False)
