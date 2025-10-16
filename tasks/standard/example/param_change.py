import time
from typing import List, Dict, Any

start_time = time.time()
from syspy import Trace, RobotParam, Module, ScriptStatus
from syspy.lib.module import ModuleBase

robot_param = {}
def load_robot_device_params():
    """加载机器人设备参数"""
    global robot_param
    robot_param.update(
        {
            "moduleType": RobotParam.getDevice("Model-000", "moduleType")
        }
    )

def load_robot_config_params():
    """加载机器人配置参数"""
    global robot_param
    robot_param.update(
        {
            "manualSlowDownDist": RobotParam.getConfig("control", "manualControl.manualBlock.on.manualSlowDownDist"),
            "manualStopAngle": RobotParam.getConfig("control", "manualControl.manualBlock.on.manualStopAngle"),
            "localizationLaser": RobotParam.getConfig("localization", "localizationType.2D.localizationLaser"),
            "unloadMaxSpeed": RobotParam.getConfig("navigation", "basic.unload.maxSpeed"),
            "carrierHeight": RobotParam.getConfig("recognition", "recognitionObject.pallet.carrierParameter.carrierHeight"),
        }
    )

def _robot_device_change_callback(device_change_set: List[str]):
    """机器人设备参数改变回调"""
    global robot_param
    """设备参数变化回调"""
    for device in device_change_set:
        if device == "Model":
            load_robot_device_params()

def _robot_config_change_callback(diff_map: Dict[str, Any]):
    """机器人配置参数变化回调"""
    global robot_param
    for key, value in diff_map.items():
        if key == "manualControl.manualBlock.on.manualSlowDownDist":
            robot_param["manualSlowDownDist"] = value
        elif key == "manualControl.manualBlock.on.manualStopAngle":
            robot_param["manualStopAngle"] = value
        elif key == "localizationType.2D.localizationLaser":
            robot_param["localizationLaser"] = value
        elif key == "basic.unload.maxSpeed":
            robot_param["unloadMaxSpeed"] = value
        elif key == "recognitionObject.pallet.carrierParameter.carrierHeight":
            robot_param["carrierHeight"] = value

load_robot_device_params()
load_robot_config_params()


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
    RobotParam.setConfigChangeCallBack(_robot_config_change_callback)
    RobotParam.setDeviceChangeCallBack(_robot_device_change_callback)

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

        print("robot_param", robot_param)

        time.sleep(0.1)

if __name__ == '__main__':
    main()