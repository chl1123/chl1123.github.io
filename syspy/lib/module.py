import json
import math
import time
from copy import deepcopy
from enum import IntEnum
from threading import Lock
from typing import Union, Optional, Callable, Tuple, Any
from syspy.utils import ScriptType
from ..core.rbk_rpc import Service
from ..utils import SCRIPTS_DIR
from syspy import RBK_VERSION, Container, ScriptParam, Navigation
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
    script_name = None
    script_type = ScriptType.GENERAL
    script_id = ""
    __lock = Lock()
    __run_status = ScriptStatus.NONE
    __rpc_client = None
    __task_id: str = ""
    __task_params = {}
    __cancel_callback = None
    __suspend_callback = None
    __resume_callback = None

    __safe_move_check_callback = None
    __safe_move_check_id = 0
    __safe_move_check_status = SafeMoveStatus.NONE
    __modbus_callback = None
    __bind_container_callback = None
    __unbind_container_callback = None
    __service = None

    @classmethod
    def init(
            cls,
            name: str = "",
            *,
            script_type: Optional[ScriptType] = None,
            script_file: Optional[str] = None,
    ):
        """脚本初始化

        Args:
            name (str): 脚本标识。缺省为脚本名。
            script_type (Optional[ScriptType]): 脚本类型。任务脚本或通用脚本。缺省为通用脚本。

        Examples:
        ```python
        from syspy import Module
        from syspy.utils import ScriptType
        # 指定类型为任务脚本
        Module.init(script_type=ScriptType.TASK)
        ```
        """
        if script_file:
            caller_file = script_file
        else:
            caller_frame = stack()[1]
            caller_file = caller_frame.filename
        cls.script_file = caller_file
        # 获取脚本相对路径
        cls.script_name = caller_file.split(SCRIPTS_DIR)[-1]

        cls.script_id = name or cls.script_name

        if script_type:
            cls.script_type = script_type
        elif cls.script_name.startswith("tasks/"):
            cls.script_type = ScriptType.TASK

        Service.init(cls.script_id, cls.script_type)

        print("script_name=", cls.script_name)
        print("script_id=", cls.script_id)
        args = cls.__getArgs()
        print("args=", args)
        if cls.script_type == ScriptType.TASK:
            cls.__initTaskArgs(args)
            cls.__register()
        else:
            cls.__task_params = args
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
    def __initTaskArgs(cls, args: dict):
        if args:
            cls.__setTaskId(args.get("taskId", None))
            cls.__task_params = args
            with cls.__lock:
                cls.__run_status = ScriptStatus.RUNNING
            # 任务中有配置参数则合并
            if "config" in cls.__task_params:
                instance=ScriptParam.getInstance(cls.script_file)
                if instance:
                    instance.setTaskConfig(cls.__task_params["config"])
                else:
                    print(f"ScriptParam.getInstance({cls.script_file}) is None")
                    return
    @classmethod
    def __register(cls):
        Service.server().register_function(cls.__updateCmd, "update_cmd")
        Service.server().register_function(cls.__suspend, "suspend")
        Service.server().register_function(cls.__resume, "resume")
        Service.server().register_function(cls.__cancel, "cancel")
        Service.server().register_function(cls.__getTask, "get_task")
        Service.server().register_function(cls.__safeMoveCheck, "safe_move_check")
        Service.server().register_function(cls.getSafeMoveCheck, "get_safe_move_check")
        Service.server().register_function(cls.__modbus, "modbus")
        Service.server().register_function(cls.__bindContainer, "bindContainer")
        Service.server().register_function(cls.__unbindContainer, "unbindContainer")

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
                Navigation.setTaskError("TaskTimeout", f"Script task timeout. Previous task timeout {NEW_TASK_TIMEOUT} second not set to NONE, FINISHED or FAILED status."
                                                       f"Check whether the script calls Module.setStatus() to set the status of NONE, FINISHED or FAILED after responding to the cancel() method")
                return
            time.sleep(0.05)
        cls.__initTaskArgs(args)
        cls.setStatus(ScriptStatus.RUNNING)

    @classmethod
    def __cancel(cls):
        if cls.getStatus() in [ScriptStatus.RUNNING, ScriptStatus.NEARTOGOAL, ScriptStatus.SUSPENDED]:
            if cls.__cancel_callback is not None:
                cls.__cancel_callback()
            else:
                cls.setStatus(ScriptStatus.FAILED)

    @classmethod
    def __getTask(cls):
        """获取脚本任务"""
        task_params = cls.__task_params.copy()
        task_params.pop("taskId", None)

        return {
            "scriptName": cls.script_name,
            "scriptStatus": cls.__run_status.value,
            "taskParams": task_params,  # 移除taskId后的参数字典
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
    def __safeMoveCheck(cls, task_id: str):
        """移动安全检查（MF调用）

        Args:
            task_id (str): 检查ID
        """
        if task_id != cls.__safe_move_check_id:
            cls.__safe_move_check_id = task_id
            cls.__safe_move_check_callback()

    @classmethod
    def __modbus(cls, task_id: str):
        """modbus 任务回调（NP -> MF调用）

        Args:
            task_id (str): 任务ID
        """
        cls.__setTaskId(task_id)
        cls.setStatus(ScriptStatus.RUNNING)
        cls.__modbus_callback()

    @classmethod
    def __bindContainer(cls, container_id: str, goods_name: str, desc: str) -> bool:
        return cls.__bind_container_callback(container_id, goods_name, desc)

    @classmethod
    def __unbindContainer(cls, container_id: str = "", goods_name: str = "") -> bool:
        return cls.__unbind_container_callback(container_id, goods_name)

    @classmethod
    def setSafeMoveCheckCallback(cls, callback: Callable[[], None]):
        cls.__safe_move_check_callback = callback

    @classmethod
    def setModbusCallback(cls, callback: Callable[[], None]):
        cls.__modbus_callback = callback

    @classmethod
    def bindContainerCallback(cls, callback: Callable[[str, str, str], bool]):
        cls.__bind_container_callback = callback

    @classmethod
    def unbindContainerCallback(cls, callback: Callable[[str, str], bool]):
        cls.__unbind_container_callback = callback

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
        if not cls.__task_id:
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
                from ..v3.lib.rpc.client import RpcClient
                cls.__rpc_client = RpcClient()
            cls.__rpc_client.report(cls.script_name, data)

    @classmethod
    def __setTaskId(cls, task_id: Optional[Union[str, int]]):
        with cls.__lock:
            cls.__task_id = "" if task_id is None else str(task_id)

    @classmethod
    def getTaskArgs(cls, name: str = "", default: Any = None) -> Any:
        """获取任务参数

        Args:
            name (str): 参数名。缺省返回所有任务参数
            default (Any): 如果参数不存在，返回默认值

        Returns:
            (Any): 参数值
        """
        task_args = cls.__task_params.get("args", {})
        if name:
            if task_args:
                return task_args.get(name, default)
            else:
                return default
        else:
            return task_args

    @classmethod
    def getTaskConfig(cls, name: str = "", default: Any = None) -> Any:
        """获取任务配置

        Args:
            name (str): 配置参数名。缺省返回所有任务配置
            default (Any): 如果配置不存在，返回默认值

        Returns:
            (Any): 配置值
        """
        task_config = cls.__task_params.get("config", {})
        if name:
            if task_config:
                return task_config.get(name, default)
            else:
                return default
        else:
            return task_config

    @classmethod
    def getTaskParams(cls, name: str = "", default: Any = None) -> Any:
        """获取当前 TASK 的只读参数快照。

        Args:
            name (str): 顶层参数名。缺省返回完整 TASK 参数。
            default (Any): 参数不存在时的缺省值。

        Returns:
            (Any): 参数值或完整参数的深拷贝。
        """
        with cls.__lock:
            if name:
                return deepcopy(cls.__task_params.get(name, default))
            return deepcopy(cls.__task_params)

    @classmethod
    def getAutoPre(cls) -> bool:
        """返回当前 TASK 是否启用 AutoPre。"""
        return bool(cls.getTaskParams("autoPre", False))

    @classmethod
    def getTaskId(cls) -> str: 
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
                cls.__task_params = {}
                cls.__task_id = ""
                instance=ScriptParam.getInstance(cls.script_file)
                if instance:
                    instance.clearTaskConfig()
                    
    @classmethod
    def reportInfo(cls, info: Union[dict, list]):
        with cls.__lock:
            if cls.__rpc_client is None:
                # todo V3独有？
                from ..v3.lib.rpc.client import RpcClient
                cls.__rpc_client = RpcClient()
            cls.__rpc_client.set_info(json.dumps(info))

    @classmethod
    def setSafeMoveCheckStatus(cls, status: SafeMoveStatus):
        """设置移动安全检查状态

        Args:
            status (SafeMoveStatus): 状态。上报 SafeMoveStatus.FINISHED 时底盘才能移动。
        """
        cls.__safe_move_check_status = status

    @classmethod
    def getSafeMoveCheck(cls) -> Tuple[int, int]:
        """获取移动安全检查状态（MF调用）

        Returns:
            (int): 移动安全检查状态。
            (int): 当前检查id（通过safe_move_check入参获取）
        """
        return cls.__safe_move_check_status.value, cls.__safe_move_check_id


from abc import ABC, abstractmethod


class ModuleBase(ABC):
    """任务脚本基类

    Attributes:
        event_safe_move_check (bool): 移动安全检查事件标志。
            开启移动安全检查时底盘移动前 event_safe_move_check 会变为 True;
            脚本执行安全检查、调用 Module.setSafeMoveStatus 上报状态;
            完成安全检查后脚本设置 event_safe_move_check 为 False。
        event_modbus (bool): Modbus TCP 指令标志。
            机器人Modbus可写寄存器00200位被写入1时，event_modbus 会变为 True;
            脚本调用 NetProtocol.getModbusData 读取可写寄存器00201-00230位脚本参数、执行对应任务、调用Module.setStatus上报状态;
            完成任务后脚本设置 event_modbus 为 False。
    """
    def __init__(self):
        Module.setSuspendCallback(self.suspend)
        Module.setResumeCallback(self.resume)
        Module.setCancelCallback(self.cancel)
        Module.setSafeMoveCheckCallback(self.__safeMoveCheck)
        Module.setModbusCallback(self.__modbus)
        Module.bindContainerCallback(self.bindContainer)
        Module.unbindContainerCallback(self.unbindContainer)
        self.event_safe_move_check = False
        self.event_modbus = False

    def __safeMoveCheck(self):
        self.event_safe_move_check = True

    def __modbus(self):
        self.event_modbus = True

    @abstractmethod
    def suspend(self):
        """暂停任务方法（必须重写）：导航暂停时如果脚本任务状态为RUNNING会调用该方法"""
        Module.setStatus(ScriptStatus.SUSPENDED)

    @abstractmethod
    def resume(self):
        """恢复任务方法（必须）：导航恢复时如果脚本任务状态为SUSPENDED会调用该方法"""
        if Module.getStatus() == ScriptStatus.SUSPENDED:
            Module.setStatus(ScriptStatus.RUNNING)

    @abstractmethod
    def cancel(self):
        """取消任务方法（必须）：导航取消时如果脚本任务状态为RUNNING或SUSPENDED会调用该方法"""
        Module.setStatus(ScriptStatus.FAILED)

    def setSafeMoveStatus(self, status: SafeMoveStatus):
        """设置移动安全检查状态

        Args:
            status (SafeMoveStatus): 状态。上报 SafeMoveStatus.FINISHED 时底盘才能移动。
        """
        Module.setSafeMoveCheckStatus(status)

    def bindContainer(self, container_id: str, goods_name: str, desc: str) -> bool:
        """绑定货物到容器

        Args:
            container_id (str): 库位或者容器id
            goods_name (str): 货物名
            desc (str): 货物描述

        Returns:
            (bool): 如果没有库位或者容器，则返回false
        """
        return Container.bindContainer(container_id, goods_name, desc)

    def unbindContainer(self, container_id: str = "", goods_name: str = "") -> bool:
        """解绑容器和货物（通过容器ID或货物名解绑），所有容器都没有货物时清除货物形状

        Args:
            container_id (str): 库位或者容器名称
            goods_name (str): 货物名称

        Returns:
            (bool): 如果没有库位或者容器，则返回false
        """
        return Container.unbindContainer(container_id, goods_name)
