import json
import math
import time
from enum import IntEnum
from threading import Lock
from typing import Union, Optional, Callable, Tuple
from syspy.utils import ScriptType
from ..core.rbk_rpc import Service
from ..utils import SCRIPTS_DIR
from syspy import RBK_VERSION, RobotParam, Container, Abnormal, ScriptParam
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


def normalizeTheta(theta):
    if theta >= -math.pi and theta < math.pi:
        return theta
    multiplier = math.floor(theta / (2 * math.pi))
    theta = theta - multiplier * 2 * math.pi
    if theta >= math.pi:
        theta = theta - 2 * math.pi
    if theta < -math.pi:
        theta = theta + 2 * math.pi
    return theta


def pos2World(pos2base, base2world) -> list:
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
    pos2world[2] = normalizeTheta(pos2base[2] + base2world[2])
    return pos2world


def pos2Base(pos2world, base2world):
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
    pos2base[2] = normalizeTheta(pos2world[2] - base2world[2])
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
        args = cls.__getArgs()
        if args != {}:
            cls.__task = args
            if cls.script_name.startswith("tasks/"):
                cls.__initTaskArgs()
        if cls.script_name.startswith("tasks/"):
            cls.__register()
        if RBK_VERSION == 3:
            Service.server().start()

    # 获取脚本启动参数
    @classmethod
    def __getArgs(cls):
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
    def __initTaskArgs(cls):
        if cls.__task is not None:
            cls.__setTaskId(cls.__task.get("taskId", None))
            cls.__task_args = cls.__task.copy()
            cls.__task_args.pop("taskId", None)
            with cls.__lock:
                cls.__run_status = ScriptStatus.RUNNING
            # 任务中有配置参数则合并
            if "configs" in cls.__task_args:
                ScriptParam.getInstance().setTaskConfig(cls.__task_args["configs"])

    @classmethod
    def __register(cls):
        # 如果是料箱车，初始化container
        container_num = RobotParam.getDevice("Model-000", "moduleType.cartonTransferUnit.id")
        is_container = isinstance(container_num, int) and container_num > 0

        Service.server().register_function(cls.__updateCmd, "update_cmd")
        Service.server().register_function(cls.__suspend, "suspend")
        Service.server().register_function(cls.__resume, "resume")
        Service.server().register_function(cls.__cancel, "cancel")
        Service.server().register_function(cls.__getTask, "get_task")
        Service.server().register_function(cls.safeMoveCheck, "safe_move_check")
        Service.server().register_function(cls.getSafeMoveCheck, "get_safe_move_check")
        Service.server().register_function(cls.modbus, "modbus")
        if is_container:
            Service.server().register_function(cls.setContainer, "setContainer")
            Service.server().register_function(cls.clearContainerByGoods, "clearContainerByGoods")
            Service.server().register_function(cls.clearContainer, "clearContainer")

    def __del__(self):
        if self.__rpc_client:
            self.__rpc_client.close()

    @classmethod
    def __updateCmd(cls, args, script_mode="instead"):
        start_time = time.time()
        # 脚本任务状态为初始态或终态时，执行新任务
        while cls.getStatus() not in [ScriptStatus.NONE, ScriptStatus.FINISHED, ScriptStatus.FAILED]:
            wait_time = time.time() - start_time
            if wait_time > NEW_TASK_TIMEOUT:
                Abnormal.client().call_service("Abnormal", "setTaskAbnormal", 53221,
                                               f"Script '{cls.script_name}' task timeout",
                                               f"Previous task timeout {NEW_TASK_TIMEOUT} second not set to NONE, FINISHED or FAILED status",
                                               "Check whether the script calls Module.setStatus() to set the status of NONE, FINISHED or FAILED after responding to the cancel() method",
                                               str(args), "", "", "", "", "", "")
                return
            time.sleep(0.05)
        cls.__task = args
        cls.__initTaskArgs()
        cls.setStatus(ScriptStatus.RUNNING)

    @classmethod
    def __cancel(cls):
        if cls.getStatus() in [ScriptStatus.RUNNING, ScriptStatus.NEARTOGOAL, ScriptStatus.SUSPENDED]:
            cls.stop_flag = True
            if cls.__cancel_callback is not None:
                cls.__cancel_callback()
            else:
                cls.setStatus(ScriptStatus.FAILED)

    @classmethod
    def __getTask(cls):
        """获取脚本任务"""
        return {
            "scriptName": cls.script_name,
            "scriptStatus": cls.__run_status.value,
            "scriptTask": cls.__task_args,
            "taskId": cls.__task_id
        }

    @classmethod
    def __suspend(cls):
        if cls.getStatus() == ScriptStatus.RUNNING:
            if cls.__suspend_callback is not None:
                cls.__suspend_callback()
            else:
                cls.setStatus(ScriptStatus.SUSPENDED)

    @classmethod
    def __resume(cls):
        if cls.getStatus() == ScriptStatus.SUSPENDED:
            if cls.__resume_callback is not None:
                cls.__resume_callback()
            else:
                cls.setStatus(ScriptStatus.RUNNING)

    @classmethod
    def safeMoveCheck(cls, task_id: int):
        """移动安全检查

        Args:
            task_id (int): 检查ID
        """
        if task_id != cls.__safe_move_check_id:
            cls.__safe_move_check_id = task_id
            cls.__safe_move_check_callback()

    @classmethod
    def getSafeMoveCheck(cls) -> Tuple[int, int]:
        """获取移动安全检查状态

        Returns:
            (int): 移动安全检查状态。
            (int): 当前检查id（通过safe_move_check入参获取）
        """
        return cls.__safe_move_check_status.value, cls.__safe_move_check_id

    @classmethod
    def setSafeMoveCheckStatus(cls, status: SafeMoveStatus):
        cls.__safe_move_check_status = status

    @classmethod
    def modbus(cls, task_id):
        cls.__setTaskId(task_id)
        cls.setStatus(ScriptStatus.RUNNING)
        cls.__modbus_callback()

    @classmethod
    def setContainer(cls, container_id: str, goods_name: str, desc: str) -> bool:
        return cls.__set_container_callback(container_id, goods_name, desc)

    @classmethod
    def clearContainerByGoods(cls, goods_name: str) -> bool:
        return cls.__clear_container_by_goods_callback(goods_name)

    @classmethod
    def clearContainer(cls, container_id: str) -> bool:
        return cls.__clear_container_callback(container_id)

    @classmethod
    def setSafeMoveCheckCallback(cls, callback: Callable[[], None]):
        cls.__safe_move_check_callback = callback

    @classmethod
    def setModbusCallback(cls, callback: Callable[[], None]):
        cls.__modbus_callback = callback

    @classmethod
    def setSetContainerCallback(cls, callback: Callable[[str, str, str], bool]):
        cls.__set_container_callback = callback

    @classmethod
    def setClearContainerByGoodsCallback(cls, callback: Callable[[str], bool]):
        cls.__clear_container_by_goods_callback = callback

    @classmethod
    def setClearContainerCallback(cls, callback: Callable[[str], bool]):
        cls.__clear_container_callback = callback

    @classmethod
    def setCancelCallback(cls, callback: Callable[[], None]):
        cls.__cancel_callback = callback

    @classmethod
    def setSuspendCallback(cls, callback: Callable[[], None]):
        cls.__suspend_callback = callback

    @classmethod
    def setResumeCallback(cls, callback: Callable[[], None]):
        cls.__resume_callback = callback

    @classmethod
    def __reportData(cls, status: Optional[ScriptStatus] = None):
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
    def __setTaskId(cls, task_id):
        with cls.__lock:
            cls.__task_id = task_id

    @classmethod
    def getTaskArgs(cls, name: str = "", default=None):
        if name:
            if cls.__task is not None:
                return cls.__task.get(name, default)
        else:
            return cls.__task

    @classmethod
    def getTaskId(cls):
        with cls.__lock:
            return cls.__task_id

    @classmethod
    def getStatus(cls) -> ScriptStatus:
        with cls.__lock:
            return cls.__run_status

    @classmethod
    def setStatus(cls, status: ScriptStatus):
        with cls.__lock:
            cls.__run_status = status
            cls.__reportData()
            # 任务状态为终态时清空任务、task_id、任务中的配置参数
            if status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
                cls.__task = None
                cls.__task_id = 0
                ScriptParam.getInstance().clearTaskConfig()

    @classmethod
    def reportInfo(cls, info: Union[dict, list]):
        with cls.__lock:
            if cls.__rpc_client is None:
                # todo V3独有？
                from ..v3.lib.rpc.client import RpcClient
                cls.__rpc_client = RpcClient()
            cls.__rpc_client.set_info(json.dumps(info))


from abc import ABC, abstractmethod


class ModuleBase(ABC):
    def __init__(self):
        Module.setSuspendCallback(self.suspend)
        Module.setResumeCallback(self.resume)
        Module.setCancelCallback(self.cancel)
        Module.setSafeMoveCheckCallback(self.__safeMoveCheck)
        Module.setModbusCallback(self.__modbus)
        Module.setSetContainerCallback(self.setContainer)
        Module.setClearContainerCallback(self.clearContainer)
        Module.setClearContainerByGoodsCallback(self.clearContainerByGoods)
        self.stop_flag = False
        self.event_safe_move_check = False
        self.event_modbus = False

    def __safeMoveCheck(self):
        self.event_safe_move_check = True

    def __modbus(self):
        self.event_modbus = True

    @abstractmethod
    def suspend(self):
        Module.setStatus(ScriptStatus.SUSPENDED)

    @abstractmethod
    def resume(self):
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            Module.setStatus(ScriptStatus.RUNNING)

    @abstractmethod
    def cancel(self):
        Module.stop_flag = True
        Module.setStatus(ScriptStatus.FAILED)

    def safeMoveCheck(self):
        ...

    def modbus(self):
        ...

    def setSafeMoveStatus(self, status: SafeMoveStatus):
        Module.setSafeMoveCheckStatus(status)

    def setContainer(self, container_id: str, goods_name: str, desc: str) -> bool:
        """设置车子上库位或者背篓货物

        Args:
            container_id (str): 库位或者背篓id
            goods_name (str): 货物名
            desc (str): 描述

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        return Container.setContainer(container_id, goods_name, desc)

    def clearContainerByGoods(self, goods_name: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            goods_name (str): 货物名称，货物名称如果为All则全部清除
        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        return Container.clearContainerByGoods(goods_name)

    def clearContainer(self, container_id: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            container_id (str): 库位或者背篓id，container_id如果为"All"则全部清除

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        return Container.clearContainer(container_id)