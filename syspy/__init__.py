import inspect
import os
import queue
import threading
import time

from loguru import logger as log

from .battery import Battery
from .bin import Bin
from .camera import Camera
from .charger import Charger
from .controller import Controller
from .dio import Di, Do
from .distance import Distance
from .laser import Laser
from .led import Led
from .lib.abnormal import Abnormal
from .lib.can_frame import Can
from .lib.model import Model
from .lib.module import ScriptStatus
from .lib.net_protocol import NetProtocol
from .lib.param import Param
from .lib.trace import Trace
from .loc import Loc
from .magnetic import Magnetic
from .map import Map
from .motor import Motor
from .navigation import Navigation, NavStatus, NavSpeed
from .odometer import Odometer
from .pgv import Pgv
from .rfid import RFID
from .sound import Sound

# from typeguard import install_import_hook
# install_import_hook('syspy')

extracted_path = ""

__all__ = [
    "Abnormal",
    "Trace",
    "NetProtocol",
    "Can",
    "Model",
    "Param",
    "BasicModule",
    "ScriptStatus",
    "Battery",
    "Bin",
    "Camera",
    "Charger",
    "Controller",
    "Di",
    "Do",
    "Distance",
    "Laser",
    "Led",
    "Loc",
    "Magnetic",
    "Map",
    "Motor",
    "Navigation",
    "NavStatus",
    "NavSpeed",
    "Odometer",
    "Pgv",
    "RFID",
    "Sound",
]  # 列出所有公共模块


def init(module_obj=None):
    global extracted_path
    caller_frame = inspect.stack()[1]
    dir_name = os.path.abspath(caller_frame.filename)
    # 从dir_name中第一个devices或者tasks到最后
    # 提取从第一个 'devices' 或 'tasks' 到最后的部分
    parts = dir_name.split(os.sep)
    start_index = next((i for i, part in enumerate(parts) if part in ['devices', 'tasks']), None)
    if start_index is not None:
        extracted_path = os.sep.join(parts[start_index:])
    else:
        extracted_path = dir_name  # 如果没有找到 'devices' 或 'tasks'，则保持原路径

    if module_obj is not None:
        from .lib.rpc.server import RpcServer
        rpc_server = RpcServer(extracted_path)
        rpc_server.registerFunction(module_obj.update_cmd, "update_cmd")
        rpc_server.registerFunction(module_obj.suspend, "suspend")
        rpc_server.registerFunction(module_obj.resume, "resume")
        rpc_server.registerFunction(module_obj.cancel, "cancel")
        rpc_server.start()


class BasicModule:

    def __init__(self):
        self._lock = threading.Lock()
        self.__run_status = ScriptStatus.NONE
        self.__info = None
        self.__task_id = None
        self.__rpc_client = None
        self.__task_queue = queue.Queue()

        self.__current_task = None

    def __del__(self):
        if self.__rpc_client:
            self.__rpc_client.close()

    def update_cmd(self, args):
        self.__task_queue.put(args)

    def cancel(self):
        self.set_status(ScriptStatus.NONE)

    def suspend(self):
        if self.get_status() == ScriptStatus.RUNNING:
            self.set_status(ScriptStatus.SUSPENDED)

    def resume(self):
        if self.get_status() == ScriptStatus.SUSPENDED:
            self.set_status(ScriptStatus.RUNNING)

    def __report_data(self):
        data = {
            "moveStatus": ScriptStatus.NONE,
            "info": "",
            "taskId": -1
        }
        if self.__run_status is not None:
            data["moveStatus"] = self.__run_status.value
        if self.__info is not None:
            data["info"] = self.__info
        if self.__task_id is not None:
            data["taskId"] = self.__task_id
        if extracted_path and data:
            if self.__rpc_client is None:
                from .lib.rpc.client import RpcClient
                self.__rpc_client = RpcClient()
            self.__rpc_client.report(extracted_path, data)

    def get_task_args(self, name: str = "", default=None):
        if name:
            if self.__current_task is not None:
                return self.__current_task.get(name, default)
        else:
            return self.__current_task

    def get_tasks_list(self):
        return list(self.__task_queue.queue)

    def __set_task_id(self, task_id):
        with self._lock:
            self.__task_id = task_id
            self.__report_data()

    def get_task_id(self):
        with self._lock:
            return self.__task_id

    def get_status(self) -> ScriptStatus:
        with self._lock:
            return self.__run_status

    def set_status(self, status: ScriptStatus):
        with self._lock:
            self.__run_status = status
            self.__report_data()

    def report_info(self, info):
        with self._lock:
            self.__info = info
            self.__report_data()

    def init_task_args(self):
        try:
            self.__current_task = self.__task_queue.get(True, 5)  # 取出最先入队的任务
            log.debug(f"{self.__current_task=}")
            self.__set_task_id(self.__current_task.get("taskId", None))
            self.set_status(ScriptStatus.RUNNING)
        except queue.Empty:
            log.info("tasks_list is empty")
            return

    def run(self):
        self.set_status(ScriptStatus.RUNNING)

    def print_info(self):
        time.sleep(0.05)
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.debug("task list: ", self.get_tasks_list())
        log.debug("current task args: ", self.get_task_args())
        log.debug("current task id: ", self.get_task_id())
        log.debug("current task status: ", self.get_status())

    def main(self):
        while True:
            # 脚本任务状态管理
            status = self.get_status()
            if status is ScriptStatus.NONE:
                self.init_task_args()
            elif status is ScriptStatus.RUNNING:
                self.run()
            elif status is ScriptStatus.SUSPENDED:
                self.suspend()
            elif status is ScriptStatus.FAILED:
                self.cancel()
                self.__current_task = None
                self.__set_task_id(None)
            elif status is ScriptStatus.FINISHED:
                self.set_status(ScriptStatus.NONE)
                self.__current_task = None
                self.__set_task_id(None)
            self.print_info()
