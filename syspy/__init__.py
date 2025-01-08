import inspect
import os

from .lib.rpc_client import rpcClient
from .lib.rpc_sub import rpcSub

from .lib.abnormal import Abnormal
from .lib.trace import Trace
from .lib.can_frame import Can
from .lib.model import Model
from .lib.param import Param
from .lib.net_protocol import NetProtocol
from .lib.module import BasicModule, ScriptStatus

from .battery import Battery
from .bin import Bin
from .camera import Camera
from .controller import Controller
from .dio import Di, Do
from .distance import Distance
from .laser import Laser
from .led import Led
from .loc import Loc
from .magnetic import Magnetic
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
    'Controller',
    'Di',
    'Do',
    'Distance',
    'Laser',
    'Led',
    'Loc',
    'Magnetic',
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
        rpc_sub.registerFunction(module_obj.reset, "reset", extracted_path)
        rpc_sub.registerFunction(module_obj.cancel, "cancel", extracted_path)


url = "http://127.0.0.1:21006/api/v1/ide/send_ide_report"
rpc_client = rpcClient()


class Report:
    def __init__(self):
        self.run_status = None
        self.info = None
        self.task_id = None

    def report_data(self):
        data = {
            "report": ""
        }
        if self.run_status is not None:
            data["moveStatus"] = self.run_status.value
        if self.info is not None:
            data["info"] = self.info
        if self.task_id is not None:
            data["taskId"] = self.task_id
        if extracted_path != "" and data != {}:
            rpc_client.report(extracted_path, data)

    def set_task_id(self, task_id):
        self.task_id = task_id
        self.report_data()

    def set_status(self, status: ScriptStatus):
        self.run_status = status
        self.report_data()

    def set_info(self, info):
        self.info = info
        self.report_data()


report = Report()
script_name = None
