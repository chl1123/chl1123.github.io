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
        self._run_status = None
        self._info = None
        self._task_id = None
        self._rpc_client = None
        self.task_queue = queue.Queue()

        self.current_task = None

    def __del__(self):
        if self._rpc_client:
            self._rpc_client.close()

    def update_cmd(self, args):
        self.task_queue.put(args)

    def cancel(self):
        self.status = ScriptStatus.NONE

    def suspend(self):
        if self.status == ScriptStatus.RUNNING:
            self.status = ScriptStatus.SUSPENDED

    def resume(self):
        if self.status == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING

    def _report_data(self):
        data = {
            "moveStatus": ScriptStatus.NONE,
            "info": "",
            "taskId": -1
        }
        if self._run_status is not None:
            data["moveStatus"] = self._run_status.value
        if self._info is not None:
            data["info"] = self._info
        if self._task_id is not None:
            data["taskId"] = self._task_id
        if extracted_path and data:
            if self._rpc_client is None:
                from .lib.rpc.client import RpcClient
                self._rpc_client = RpcClient()
            self._rpc_client.report(extracted_path, data)

    @property
    def task_id(self):
        with self._lock:
            return self._task_id

    @task_id.setter
    def task_id(self, task_id):
        with self._lock:
            self._task_id = task_id
            self._report_data()

    @property
    def status(self) -> ScriptStatus:
        with self._lock:
            return self._run_status

    @status.setter
    def status(self, status: ScriptStatus):
        with self._lock:
            self._run_status = status
            self._report_data()

    @property
    def info(self):
        with self._lock:
            return self._info

    @info.setter
    def info(self, info):
        with self._lock:
            self._info = info
            self._report_data()

    def init_task_args(self):
        try:
            self.current_task = self.task_queue.get(True, 5)  # 取出最先入队的任务
            log.debug(f"{self.current_task=}")
            self.task_id = self.current_task.get("taskId", None)
            self.status = ScriptStatus.RUNNING
        except queue.Empty:
            log.info("task_queue is empty")
            return

    def run(self):
        self.status = ScriptStatus.RUNNING

    def print_info(self):
        time.sleep(0.05)
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.debug("task queue: ", list(self.task_queue.queue))
        log.debug("current task: ", self.current_task)
        log.debug("current task id: ", self.task_id)
        log.debug("current task status: ", self.status)

    def main(self):
        while True:
            # 脚本任务状态管理
            if self.status is ScriptStatus.NONE:
                self.init_task_args()
            elif self.status is ScriptStatus.RUNNING:
                self.run()
            elif self.status is ScriptStatus.SUSPENDED:
                self.suspend()
            elif self.status is ScriptStatus.FAILED:
                self.cancel()
                self.current_task = None
                self.task_id = None
            elif self.status is ScriptStatus.FINISHED:
                self.status = ScriptStatus.NONE
                self.current_task = None
                self.task_id = None
            self.print_info()
