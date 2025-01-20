import inspect
import os
import queue
import threading

from .lib.rpc_client import rpcClient
from .lib.rpc_sub import rpcSub

from .lib.abnormal import Abnormal
from .lib.trace import Trace
from .lib.can_frame import Can
from .lib.model import Model
from .lib.param import Param
from .lib.net_protocol import NetProtocol
from .lib.module import ScriptStatus

from .battery import Battery
from .bin import Bin
from .camera import Camera
from .charger import Charger
from .controller import Controller
from .dio import Di, Do
from .distance import Distance
from .laser import Laser
from .led import Led
from .loc import Loc
from .magnetic import Magnetic
from .map import Map
from .motor import Motor
from .move import Move
from .navigation import NavSpeed
from .odometer import Odometer
from .pgv import Pgv
from .rfid import RFID
from .sound import Sound

from .mf import MF

extracted_path = ""

__all__ = [
    'Abnormal',
    'Trace',
    'NetProtocol',
    'Can',
    'Model',
    'Param',
    'BasicModule',
    'ScriptStatus',

    'Battery',
    'Bin',
    'Camera',
    'Charger',
    'Controller',
    'Di',
    'Do',
    'Distance',
    'Laser',
    'Led',
    'Loc',
    'Magnetic',
    'Map',
    'Motor',
    'Move',
    'NavSpeed',
    'Odometer',
    'Pgv',
    'RFID',
    'Sound',

    'MF'
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

    print("extracted_path", extracted_path)
    if module_obj is not None:
        rpc_sub = rpcSub()
        rpc_sub.registerFunction(module_obj.update_cmd, "update_cmd", extracted_path)
        rpc_sub.registerFunction(module_obj.suspend, "suspend", extracted_path)
        rpc_sub.registerFunction(module_obj.resume, "resume", extracted_path)
        rpc_sub.registerFunction(module_obj.cancel, "cancel", extracted_path)
        rpc_sub.registerFunction(module_obj.reset, "reset", extracted_path)


class BasicModule:
    def __init__(self):
        self._lock = threading.Lock()
        self._run_status = None
        self._info = None
        self._task_id = None
        self.task_queue = queue.Queue()
        self.rpc_client = rpcClient()

    def __del__(self):
        self.rpc_client.close()

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
        elif self.status != ScriptStatus.RUNNING:
            self.status = ScriptStatus.NONE

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
        if extracted_path != "" and data != {}:
            self.rpc_client.report(extracted_path, data)

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
