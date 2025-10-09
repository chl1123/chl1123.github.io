import time
from typing import List

start_time = time.time()
from syspy import Trace, RobotParam, Module, ScriptStatus
from syspy.lib.module import ModuleBase

robot_param = {}
def _load_robot_params():
    global robot_param
    robot_param = {
        "moduleType": RobotParam.getDevice("Model-000", "moduleType")
    }
    Trace.log(f"moduleType: {robot_param['moduleType']}")

def _device_change_callback(device_change_set: List[str]):
    """设备参数变化回调"""
    for device in device_change_set:
        if device == "Model":
            _load_robot_params()

_load_robot_params()
RobotParam.setDeviceChangeCallBack(_device_change_callback)

class Jack(ModuleBase):
    def __init__(self):
        super().__init__()
        self.count = 0
        self.report_info = {}
        self.args = {}
        self.status = ScriptStatus.NONE

    def init_args(self, args):
        self.args = args
        if args:
            self.status = ScriptStatus.RUNNING

    def run(self):
        self.status = ScriptStatus.RUNNING
        self.count += 1
        self.report_info["args"] = self.args
        self.report_info["count"] = self.count
        self.report_info["run_time"] = round(time.time() - start_time, 2)

    def print_info(self):
        Trace.log(f"task_id={Module.get_task_id()}, status={Module.get_status()}, args={self.args}")
        Module.report_info(self.report_info)

    def suspend(self):
        self.status = ScriptStatus.SUSPENDED
        Trace.log("suspend")

    def resume(self):
        if Module.get_status() == ScriptStatus.SUSPENDED:
            self.status = ScriptStatus.RUNNING
        Trace.log("resume")

    def cancel(self):
        self.status = ScriptStatus.FAILED
        Trace.log("cancel")


def main():
    Module.init()
    j = Jack()
    while True:
        status = j.status
        Module.set_status(status)
        j.report_info["status"] = status
        j.print_info()
        if status == ScriptStatus.NONE:
            args = Module.get_task_args()
            j.init_args(args)
        elif status == ScriptStatus.RUNNING:
            j.run()
        elif status == ScriptStatus.SUSPENDED:
            j.suspend()
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            j.status = ScriptStatus.NONE

        current_module_type = robot_param.get("moduleType")
        print("module_type", current_module_type)

        time.sleep(0.1)

if __name__ == '__main__':
    main()