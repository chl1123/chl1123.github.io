import abc
import json
import queue
import time
from typing import Union

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
from .recognize import Recognize
from .rfid import RFID
from .sound import Sound

# from typeguard import install_import_hook
# install_import_hook('syspy')

__all__ = [
    "Abnormal",
    "Trace",
    "NetProtocol",
    "Can",
    "Model",
    "Param",
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
    "Recognize",
    "Sound",
]  # 列出所有公共模块


def register(module_obj=None, script_name=""):
    if module_obj is not None:
        from .lib.rpc.server import RpcServer
        rpc_server = RpcServer(script_name)
        rpc_server.registerFunction(module_obj.update_cmd, "update_cmd")
        rpc_server.registerFunction(module_obj.suspend, "suspend")
        rpc_server.registerFunction(module_obj.resume, "resume")
        rpc_server.registerFunction(module_obj.cancel, "cancel")
        rpc_server.start()


# 获取脚本启动参数
def get_args():
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


class LoopModule(metaclass=abc.ABCMeta):
    def __init__(self, period=0.1):
        self.period = period

    @abc.abstractmethod
    def run(self):
        pass

    def main(self):
        while True:
            self.run()
            time.sleep(self.period)


class TaskModule:
    def __init__(self):
        from threading import Lock
        self._lock = Lock()
        self.__run_status = ScriptStatus.NONE
        self.__task_id = None
        self.__rpc_client = None
        self.__task_queue = queue.Queue()

        self.__current_task = None

        from inspect import getfile
        full_path = getfile(self.__class__)
        from .utils import SCRIPTS_DIR
        # 获取脚本相对路径
        self.script_name = full_path.split(SCRIPTS_DIR + "/")[-1]
        self.__is_init = False

        args = get_args()
        if args != {}:
            self.update_cmd(args)
            self.init_task_args()

    def __del__(self):
        if self.__rpc_client:
            self.__rpc_client.close()

    def update_cmd(self, args):
        self.__task_queue.put(args)

    def cancel(self):
        self.set_status(ScriptStatus.FINISHED)

    def suspend(self):
        if self.get_status() == ScriptStatus.RUNNING:
            self.set_status(ScriptStatus.SUSPENDED)

    def resume(self):
        if self.get_status() == ScriptStatus.SUSPENDED:
            self.set_status(ScriptStatus.RUNNING)

    def __report_data(self):
        if self.__task_id is None:
            return
        data = {
            "moveStatus": self.__run_status.value or ScriptStatus.NONE,
            "taskId": self.__task_id
        }
        if self.script_name:
            if self.__rpc_client is None:
                from .lib.rpc.client import RpcClient
                self.__rpc_client = RpcClient()
            self.__rpc_client.report(self.script_name, data)

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

    def report_info(self, info: Union[dict, list]):
        with self._lock:
            if self.__rpc_client is None:
                from .lib.rpc.client import RpcClient
                self.__rpc_client = RpcClient()
            self.__rpc_client.set_info(json.dumps(info))

    def init_task_args(self):
        try:
            self.__current_task = self.__task_queue.get(True, 5)  # 取出最先入队的任务
            self.__set_task_id(self.__current_task.get("taskId", None))
            self.set_status(ScriptStatus.RUNNING)
            return
        except queue.Empty:
            pass
        self.set_status(ScriptStatus.NONE)

    def run(self):
        self.set_status(ScriptStatus.RUNNING)

    def print_info(self):
        time.sleep(0.05)
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        print(f"{self.get_tasks_list()=}")
        print(f"{self.get_task_args()=}")
        print(f"{self.get_task_id()=}")
        print(f"{self.get_status()=}")

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
                return
            elif status is ScriptStatus.FINISHED:
                self.set_status(ScriptStatus.NONE)
                return
            if not self.__is_init:
                self.__is_init = True
                register(self, self.script_name)
            self.print_info()
