import json
import math
import time
from enum import IntEnum
from threading import Lock
from typing import Union, Optional, Callable, Tuple
from syspy.utils import ScriptType
from ..core.rbk_rpc import Service
from ..utils import SCRIPTS_DIR
from syspy import RBK_VERSION, RobotParam, Container, Abnormal
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
        (list): 世界坐标系
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

NEW_TASK_TIMEOUT = 1

class Module:
    stop_flag = False
    script_name = None
    script_type = ScriptType.GENERAL
    __lock = Lock()
    __run_status = ScriptStatus.NONE
    __rpc_client = None
    __task = None
    __task_id = 0
    __task_args = {}
    __cancel_callback = None
    __suspend_callback = None
    __resume_callback = None

    __safe_move_check_callback = None
    __safe_move_check_id = 0
    __safe_move_check_status = SafeMoveStatus.NONE
    __modbus_callback = None
    __set_container_callback = None
    __clear_container_by_goods_callback = None
    __clear_container_callback = None
    __service = None
    script_id = ""

    @classmethod
    def init(cls, name: str = ""):
        cls.script_id = name
        caller_frame = stack()[1]
        caller_file = caller_frame.filename
        # 获取脚本相对路径
        cls.script_name = caller_file.split(SCRIPTS_DIR + "/")[-1]
        if cls.script_name.startswith("tasks/"):
            cls.script_type = ScriptType.TASK
        if name == "":
            cls.script_id = cls.script_name

        Service.init(cls.script_id, cls.script_type)

        print("script_name: ", cls.script_name)
        print("script_id", cls.script_id)
        args = cls.__get_args()
        if args != {}:
            cls.__task = args
            if cls.script_name.startswith("tasks/"):
                cls.__init_task_args()
        if cls.script_name.startswith("tasks/"):
            cls.__register()
        if RBK_VERSION == 3:
            Service.server().start()

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
            cls.__task_args = cls.__task.copy()
            cls.__task_args.pop("taskId", None)
            with cls.__lock:
                cls.__run_status = ScriptStatus.RUNNING

    @classmethod
    def __register(cls):
        # 如果是料箱车，初始化container
        container_num = RobotParam.getDevice("Model-000", "moduleType.cartonTransferUnit.id")
        is_container = isinstance(container_num, int) and container_num > 0

        Service.server().register_function(cls.__update_cmd, "update_cmd")
        Service.server().register_function(cls.__suspend, "suspend")
        Service.server().register_function(cls.__resume, "resume")
        Service.server().register_function(cls.__cancel, "cancel")
        Service.server().register_function(cls.__get_task, "get_task")
        Service.server().register_function(cls.safe_move_check, "safe_move_check")
        Service.server().register_function(cls.get_safe_move_check, "get_safe_move_check")
        Service.server().register_function(cls.modbus, "modbus")
        if is_container:
            Service.server().register_function(cls.set_container, "setContainer")
            Service.server().register_function(cls.clear_container_by_goods, "clearContainerByGoods")
            Service.server().register_function(cls.clear_container, "clearContainer")

    def __del__(self):
        if self.__rpc_client:
            self.__rpc_client.close()

    @classmethod
    def __update_cmd(cls, args, script_mode="instead"):
        start_time = time.time()
        # 脚本任务状态为初始态或终态时，执行新任务
        while cls.get_status() not in [ScriptStatus.NONE, ScriptStatus.FINISHED, ScriptStatus.FAILED]:
            wait_time = time.time() - start_time
            if wait_time > NEW_TASK_TIMEOUT:
                Abnormal.client().call_service("Abnormal", "setTaskAbnormal", 53221,
                                               f"Script '{cls.script_name}' task timeout",
                                               f"Previous task timeout {NEW_TASK_TIMEOUT} second not set to NONE, FINISHED or FAILED status",
                                               "Check whether the script calls Module.set_status() to set the status of NONE, FINISHED or FAILED after responding to the cancel() method",
                                               str(args), "", "", "", "", "", "")
                return
            time.sleep(0.05)
        cls.__task = args
        cls.__init_task_args()
        cls.set_status(ScriptStatus.RUNNING)

    @classmethod
    def __cancel(cls):
        if cls.get_status() in [ScriptStatus.RUNNING, ScriptStatus.NEARTOGOAL, ScriptStatus.SUSPENDED]:
            cls.stop_flag = True
            if cls.__cancel_callback is not None:
                cls.__cancel_callback()
            else:
                cls.set_status(ScriptStatus.FAILED)

    @classmethod
    def __get_task(cls):
        """获取脚本任务"""
        return {
            "scriptName": cls.script_name,
            "scriptStatus": cls.__run_status.value,
            "scriptTask": cls.__task_args,
            "taskId": cls.__task_id
        }

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
            (int): 移动安全检查状态。
            (int): 当前检查id（通过safe_move_check入参获取）
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
    def set_container(cls, container_id: str, goods_name: str, desc: str) -> bool:
        return cls.__set_container_callback(container_id, goods_name, desc)

    @classmethod
    def clear_container_by_goods(cls, goods_name: str) -> bool:
        return cls.__clear_container_by_goods_callback(goods_name)

    @classmethod
    def clear_container(cls, container_id: str) -> bool:
        return cls.__clear_container_callback(container_id)

    @classmethod
    def set_safe_move_check_callback(cls, callback: Callable[[], None]):
        cls.__safe_move_check_callback = callback

    @classmethod
    def set_modbus_callback(cls, callback: Callable[[], None]):
        cls.__modbus_callback = callback

    @classmethod
    def set_set_container_callback(cls, callback: Callable[[str, str, str], bool]):
        cls.__set_container_callback = callback

    @classmethod
    def set_clear_container_by_goods_callback(cls, callback: Callable[[str], bool]):
        cls.__clear_container_by_goods_callback = callback

    @classmethod
    def set_clear_container_callback(cls, callback: Callable[[str], bool]):
        cls.__clear_container_callback = callback

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
        if cls.__task_id == 0 or cls.__task_id is None:
            return
        if status is None:
            status = cls.__run_status
        data = {
            "moveStatus": status.value,
            "taskId": cls.__task_id
        }
        print("report data:", data)
        if cls.script_name:
            if cls.__rpc_client is None:
                # todo V3独有？
                from ..v3.lib.rpc.client import RpcClient
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
            # 任务状态为终态时清空任务和task_id
            if status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
                cls.__task = None
                cls.__task_id = 0

    @classmethod
    def report_info(cls, info: Union[dict, list]):
        with cls.__lock:
            if cls.__rpc_client is None:
                # todo V3独有？
                from ..v3.lib.rpc.client import RpcClient
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
        Module.set_set_container_callback(self.set_container)
        Module.set_clear_container_callback(self.clear_container)
        Module.set_clear_container_by_goods_callback(self.clear_container_by_goods)
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

    def set_container(self, container_id: str, goods_name: str, desc: str) -> bool:
        """设置车子上库位或者背篓货物

        Args:
            container_id (str): 库位或者背篓id
            goods_name (str): 货物名
            desc (str): 描述

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        return Container.setContainer(container_id, goods_name, desc)

    def clear_container_by_goods(self, goods_name: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            goods_name (str): 货物名称，货物名称如果为All则全部清除
        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        return Container.clearContainerByGoods(goods_name)

    def clear_container(self, container_id: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            container_id (str): 库位或者背篓id，container_id如果为"All"则全部清除

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        return Container.clearContainer(container_id)