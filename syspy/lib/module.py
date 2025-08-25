import json
import math
from enum import IntEnum
from threading import Lock
from typing import Union, Optional, Callable, Tuple
from syspy.utils import ScriptType
from ..utils import SCRIPTS_DIR
from syspy import RBK_VERSION
from inspect import stack

class ScriptStatus(IntEnum):
    NONE = 0
    RUNNING = 1
    NEARTOGOAL = 2
    FINISHED = 3
    FAILED = 4
    SUSPENDED = 5


class SafeMoveStatus(IntEnum):
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
    stop_flag = False
    script_name = None
    __lock = Lock()
    __run_status = ScriptStatus.NONE
    __task_id = 0
    __rpc_client = None
    __task = None
    __cancel_callback = None
    __suspend_callback = None
    __resume_callback = None

    __safe_move_check_callback = None
    __safe_move_check_id = 0
    __safe_move_check_status = SafeMoveStatus.NONE
    __modbus_callback = None
    script_id = ""

    @classmethod
    def init(cls, name: str = ""):
        cls.script_id = name
        caller_frame = stack()[1]
        caller_file = caller_frame.filename
        # 获取脚本相对路径
        cls.script_name = caller_file.split(SCRIPTS_DIR + "/")[-1]
        if name == "":
            cls.script_id = cls.script_name
        if RBK_VERSION == 4:
            from syspy.v4.include.rbk import core
            core.Init(cls.script_id)
        print("script_name: ", cls.script_name)
        print("script_id", cls.script_id)
        args = cls.__get_args()
        if args != {}:
            cls.__task = args
            if cls.script_name.startswith("tasks/"):
                cls.__init_task_args()
        if cls.script_name.startswith("tasks/"):
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
        if RBK_VERSION == 3:
            from syspy.lib.rpc.server import RpcServer
            service = RpcServer(cls.script_id, ScriptType.TASK)
            service.registerFunction(cls.__update_cmd, "update_cmd")
            service.registerFunction(cls.__suspend, "suspend")
            service.registerFunction(cls.__resume, "resume")
            service.registerFunction(cls.__cancel, "cancel")

            service.registerFunction(cls.safe_move_check, "safe_move_check")
            service.registerFunction(cls.get_safe_move_check, "get_safe_move_check")
            service.registerFunction(cls.modbus, "modbus")
            service.start()
        elif RBK_VERSION == 4:
            from syspy.v4.include.rbk import core, service
            service.addService(cls.script_id, "update_cmd", cls.__update_cmd)
            service.addService(cls.script_id, "suspend", cls.__suspend)
            service.addService(cls.script_id, "resume", cls.__resume)
            service.addService(cls.script_id, "cancel", cls.__cancel)

            service.addService(cls.script_id, "safe_move_check", cls.safe_move_check)
            service.addService(cls.script_id, "get_safe_move_check", cls.get_safe_move_check)
            service.addService(cls.script_id, "modbus", cls.modbus)

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
        cls.stop_flag = True
        if cls.__cancel_callback is not None:
            cls.__cancel_callback()
        else:
            cls.set_status(ScriptStatus.FAILED)

    @classmethod
    def __suspend(cls):
        if cls.get_status() == ScriptStatus.RUNNING:
            if cls.__suspend_callback is not None:
                    cls.__suspend_callback()
            else:
                cls.set_status(ScriptStatus.SUSPENDED)

    @classmethod
    def __resume(cls):
        if cls.get_status() == ScriptStatus.SUSPENDED:
            if cls.__resume_callback is not None:
                    cls.__resume_callback()
            else:
                cls.set_status(ScriptStatus.RUNNING)

    @classmethod
    def safe_move_check(cls, task_id: int):
        """移动安全检查

        Args:
            task_id (int): 检查ID
        """
        if  task_id != cls.__safe_move_check_id:
            cls.__safe_move_check_id = task_id
            cls.__safe_move_check_callback()

    @classmethod
    def get_safe_move_check(cls) -> Tuple[int, int]:
        """获取移动安全检查状态

        Returns:
            int: 移动安全检查状态。
            int: 当前检查id（通过safe_move_check入参获取）
        """
        return cls.__safe_move_check_status.value, cls.__safe_move_check_id

    @classmethod
    def set_safe_move_check_status(cls, status: SafeMoveStatus):
        cls.__safe_move_check_status = status

    @classmethod
    def modbus(cls, task_id):
        cls.__set_task_id(task_id)
        cls.set_status(ScriptStatus.RUNNING)
        cls.__modbus_callback()

    @classmethod
    def set_safe_move_check_callback(cls, callback: Callable[[], None]):
        cls.__safe_move_check_callback = callback

    @classmethod
    def set_modbus_callback(cls, callback: Callable[[], None]):
        cls.__modbus_callback = callback

    @classmethod
    def set_cancel_callback(cls, callback: Callable[[], None]):
        cls.__cancel_callback = callback

    @classmethod
    def set_suspend_callback(cls, callback: Callable[[], None]):
        cls.__suspend_callback = callback

    @classmethod
    def set_resume_callback(cls, callback: Callable[[], None]):
        cls.__resume_callback = callback

    @classmethod
    def __report_data(cls, status: Optional[ScriptStatus] = None):
        if cls.__task_id == 0:
            return
        if status is None:
            status = cls.__run_status
        data = {
            "moveStatus": status.value,
            "taskId": cls.__task_id
        }
        if cls.script_name:
            if cls.__rpc_client is None:
                # todo V3独有？
                from ..lib.rpc.client import RpcClient
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
            # 任务失败或完成时清空任务和task_id
            if status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
                cls.__task = None
                cls.__task_id = 0

    @classmethod
    def report_info(cls, info: Union[dict, list]):
        with cls.__lock:
            if cls.__rpc_client is None:
                # todo V3独有？
                from ..lib.rpc.client import RpcClient
                cls.__rpc_client = RpcClient()
            cls.__rpc_client.set_info(json.dumps(info))


from abc import ABC, abstractmethod
class ModuleBase(ABC):
    def __init__(self):
        Module.set_suspend_callback(self.suspend)
        Module.set_resume_callback(self.resume)
        Module.set_cancel_callback(self.cancel)
        Module.set_safe_move_check_callback(self.__safe_move_check)
        Module.set_modbus_callback(self.__modbus)
        self.stop_flag = False
        self.event_safe_move_check = False
        self.event_modbus = False

    def __safe_move_check(self):
        self.event_safe_move_check = True

    def __modbus(self):
        self.event_modbus = True

    @abstractmethod
    def suspend(self):
        Module.set_status(ScriptStatus.SUSPENDED)

    @abstractmethod
    def resume(self):
        if Module.get_status() == ScriptStatus.SUSPENDED:
            Module.set_status(ScriptStatus.RUNNING)

    @abstractmethod
    def cancel(self):
        Module.stop_flag = True
        Module.set_status(ScriptStatus.FAILED)

    def safe_move_check(self):
        ...

    def modbus(self):
        ...

    def set_safe_move_status(self, status: SafeMoveStatus):
        Module.set_safe_move_check_status(status)
