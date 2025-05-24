import json
import math
import time
from enum import IntEnum
from threading import Lock
from typing import Union, Optional

from ..utils import ScriptType


class ScriptStatus(IntEnum):
    NONE = 0
    RUNNING = 1
    NEARTOGOAL = 2
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


class CollisionType(IntEnum):
    Ultrasonic = 0
    Laser = 1
    Fallingdown = 2
    Collision = 3
    Infrared = 4
    VirtualPoint = 5
    APIObstacle = 6
    ReservedPoint = 7
    DiUltrasonic = 8
    DepthCamera = 9
    ReservedDepthCamera = 10
    DistanceNode = 11


def normalize_theta(theta):
    if theta >= -math.pi and theta < math.pi:
        return theta
    multiplier = math.floor(theta / (2 * math.pi))
    theta = theta - multiplier * 2 * math.pi
    if theta >= math.pi:
        theta = theta - 2 * math.pi
    if theta < -math.pi:
        theta = theta + 2 * math.pi
    return theta


def Pos2World(pos2base, base2world) -> list:
    """将位姿转换为世界坐标系

    Args:
        pos2base ([3]): 被转换的位姿，基于base. 0:x, 1:y, 2: theta
        base2world ([3]): 基准位姿. 0:x, 1:y, 2: theta

    Returns:
        list: 世界坐标系
    """
    pos2world = [0., 0., 0.]
    x = pos2base[0] * math.cos(base2world[2]) - pos2base[1] * math.sin(base2world[2])
    y = pos2base[0] * math.sin(base2world[2]) + pos2base[1] * math.cos(base2world[2])
    pos2world[0] = x + base2world[0]
    pos2world[1] = y + base2world[1]
    pos2world[2] = normalize_theta(pos2base[2] + base2world[2])
    return pos2world


def Pos2Base(pos2world, base2world):
    """将基于世界坐标系的两个位姿，转换为基于base的位姿

    Args:
        pos2world ([3]): 被转换的位姿，基于世界坐标系,0:x, 1:y, 2: theta
        base2world ([3]): 基准，基于世界坐标系,0:x, 1:y, 2: theta
    Returns:
        [3]: pos2base
    """
    pos2base = [0., 0., 0.]
    x = pos2world[0] - base2world[0]
    y = pos2world[1] - base2world[1]
    pos2base[0] = x * math.cos(base2world[2]) + y * math.sin(base2world[2])
    pos2base[1] = -x * math.sin(base2world[2]) + y * math.cos(base2world[2])
    pos2base[2] = normalize_theta(pos2world[2] - base2world[2])
    return pos2base


class Module:
    script_name = None
    __lock = Lock()
    __run_status = ScriptStatus.NONE
    __task_id = None
    __rpc_client = None
    __task = None

    @classmethod
    def init(cls):
        from inspect import stack
        caller_frame = stack()[1]
        caller_file = caller_frame.filename
        from ..utils import SCRIPTS_DIR
        # 获取脚本相对路径
        cls.script_name = caller_file.split(SCRIPTS_DIR + "/")[-1]
        print("script_name: ", cls.script_name)
        args = cls.__get_args()
        if args != {}:
            cls.__task = args
            cls.__init_task_args()
        cls.__register()

    # 获取脚本启动参数
    @classmethod
    def __get_args(cls):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("args", nargs='?', type=str, default="{}", help="脚本参数")
        args = parser.parse_args()
        if args.args not in ('', '{}'):
            try:
                args = json.loads(args.args)
            except Exception as e:
                return {}
            return args
        return {}

    @classmethod
    def __init_task_args(cls):
        if cls.__task is not None:
            cls.__set_task_id(cls.__task.get("taskId", None))
            with cls.__lock:
                cls.__run_status = ScriptStatus.RUNNING

    @classmethod
    def __register(cls):
        from .rpc.server import RpcServer
        rpc_server = RpcServer(cls.script_name, ScriptType.TASK)
        rpc_server.registerFunction(cls.__update_cmd, "update_cmd")
        rpc_server.registerFunction(cls.__suspend, "suspend")
        rpc_server.registerFunction(cls.__resume, "resume")
        rpc_server.registerFunction(cls.__cancel, "cancel")
        rpc_server.start()

    def __del__(self):
        if self.__rpc_client:
            self.__rpc_client.close()

    @classmethod
    def __update_cmd(cls, args, script_mode="instead"):
        cls.__task = args
        cls.__init_task_args()
        cls.set_status(ScriptStatus.RUNNING)

    @classmethod
    def __cancel(cls):
        cls.set_status(ScriptStatus.FINISHED)

    @classmethod
    def __suspend(cls):
        if cls.get_status() == ScriptStatus.RUNNING:
            cls.set_status(ScriptStatus.SUSPENDED)

    @classmethod
    def __resume(cls):
        if cls.get_status() == ScriptStatus.SUSPENDED:
            cls.set_status(ScriptStatus.RUNNING)

    @classmethod
    def __report_data(cls, status: Optional[ScriptStatus] = None):
        if cls.__task_id is None:
            return
        if status is None:
            status = cls.__run_status
        data = {
            "moveStatus": status.value,
            "taskId": cls.__task_id
        }
        if cls.script_name:
            if cls.__rpc_client is None:
                from .rpc.client import RpcClient
                cls.__rpc_client = RpcClient()
            cls.__rpc_client.report(cls.script_name, data)

    @classmethod
    def __set_task_id(cls, task_id):
        with cls.__lock:
            cls.__task_id = task_id

    @classmethod
    def get_task_args(cls, name: str = "", default=None):
        if name:
            if cls.__task is not None:
                return cls.__task.get(name, default)
        else:
            return cls.__task

    @classmethod
    def get_task_id(cls):
        with cls.__lock:
            return cls.__task_id

    @classmethod
    def get_status(cls) -> ScriptStatus:
        with cls.__lock:
            return cls.__run_status

    @classmethod
    def set_status(cls, status: ScriptStatus):
        with cls.__lock:
            cls.__run_status = status
            cls.__report_data()
            # 脚本FINISHED状态后，需主动上报状态为NONE，因为MF不清除FINISHED
            if cls.__run_status == ScriptStatus.FINISHED:
                # tips: 多次设置脚本状态的时间都在MF的单个控制周期内（20ms-50ms），前面设置的状态可能会不生效
                time.sleep(0.3)
                cls.__report_data(ScriptStatus.NONE)

    @classmethod
    def report_info(cls, info: Union[dict, list]):
        with cls.__lock:
            if cls.__rpc_client is None:
                from .rpc.client import RpcClient
                cls.__rpc_client = RpcClient()
            cls.__rpc_client.set_info(json.dumps(info))
