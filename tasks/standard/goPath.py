import json
import logging
import math
import time
from typing import Optional

from syspy import Module, ScriptStatus, Abnormal, Navigation, Loc

log = logging.getLogger("rbk.script")

"""
####BEGIN DEFAULT ARGS####
{
    "x": {
      "value": 1,
      "tips":"x 必填",
      "type":"double",
      "unit": "m"
      },
    "y": {
      "value": 1,
      "tips":"y 必填",
      "type":"double",
      "unit": "m"
    },
    "theta": {
      "value": 1,
      "tips":"机器人朝向",
      "type":"double",
      "unit": "rad"
    },
    "reachAngle": {
      "value": 3.14,
      "tips":"到点角度精度",
      "type":"double",
      "unit": "rad"
    },
    "reachDist": {
      "value": 0.005,
      "tips":"到点距离精度",
      "type":"double",
      "unit": "m"
    },
    "useOdo": {
      "value": 1,
      "tips":"是否使用里程定位，默认为否",
      "type":"int"
    },
    "backMode":{
      "value": 1,
      "tips":"是否倒走",
      "type":"int"
    },
    "coordinate":{
      "value": "robot",
      "default_value":[
      "robot","world"
      ],
      "tips": "目标点的坐标系，必填",
      "type": "complex"  
    },
    "maxSpeed":{
      "value": 1,
      "tips":"最大速度必填",
      "type":"double",
      "unit": "m/s"        
    },
    "maxRot":{
      "value": 1,
      "tips":"最大角速度",
      "type":"double",
      "unit": "rad"        
    },
    "maxAcc":{
      "value": 1,
      "tips":"最大加速度",
      "type":"double",
      "unit": "m/s^2"   
    },
    "maxDec":{
      "value": 1,
      "tips":"最大减速度",
      "type":"double",
      "unit": "m/s^2"   
    },
    "maxRotAcc":{
      "value": 1,
      "tips":"最大角速度",
      "type":"double",
      "unit": "rad/s^2"
    },
    "maxRotDec":{
      "value": 1,
      "tips":"最大角减速度",
      "type":"double",
      "unit": "rad/s^2"   
    },
    "hold_dir":{
      "value": 999,
      "tips":"全向车平移时车身的固定角度",
      "type":"double",
      "unit": "°"        
    }
}
####END DEFAULT ARGS####
"""


class GoPath:
    def __init__(self):
        self.goal = [0, 0, 0]
        self.init = False
        self.status = ScriptStatus.NONE
        self.param = {}

    def run(self, args: Optional[dict] = None):
        self.status = ScriptStatus.RUNNING
        if args is None:
            args = Module.get_task_args()
        if Abnormal.exists(52111):
            self.status = ScriptStatus.FAILED
            return self.status
        if not self.init:
            self.init = True
            Navigation.resetPath()
            if "x" in args and "y" in args and "coordinate" in args:
                if "x" in args:
                    self.goal[0] = float(args["x"])
                if "y" in args:
                    self.goal[1] = float(args["y"])
                if "theta" in args:
                    self.goal[2] = float(args["theta"])
                    if "reachAngle" in args:
                        Navigation.setPathReachAngle(float(args["reachAngle"]))
                else:
                    Navigation.setPathReachAngle(math.pi)
                if "reachAngle" in args:
                    Navigation.setPathReachAngle(float(args["reachAngle"]))
                if "reachDist" in args:
                    Navigation.setPathReachDist(float(args["reachDist"]))
                if "useOdo" in args:
                    Navigation.setPathUseOdo(bool(int(args["useOdo"])))
                if "backMode" in args:
                    Navigation.setPathBackMode(bool(int(args["backMode"])))
                if "maxSpeed" in args:
                    Navigation.setPathMaxSpeed(float(args["maxSpeed"]))
                if "maxRot" in args:
                    Navigation.setPathMaxRot(float(args["maxRot"]))
                if "hold_dir" in args:
                    Navigation.setPathHoldDir(float(args["hold_dir"]))
                if "maxAcc" in args:
                    self.param["maxAcc"] = float(args["maxAcc"])
                if "maxDec" in args:
                    self.param["maxDec"] = float(args["maxDec"])
                if "maxRotAcc" in args:
                    self.param["maxRotAcc"] = float(args["maxRotAcc"])
                if "maxRotDec" in args:
                    self.param["maxRotDec"] = float(args["maxRotDec"])
                log.info("goal: %s", str(self.goal))
                if args["coordinate"] == "robot":
                    Navigation.setPathOnRobot([0, self.goal[0]], [0, self.goal[1]], self.goal[2])
                elif args["coordinate"] == "world":
                    x = Loc.get_pose()["x"]
                    y = Loc.get_pose()["y"]
                    Navigation.setPathOnWorld([x, self.goal[0]], [y, self.goal[1]], self.goal[2])
                else:
                    log.error("coordinate only support robot and world. Input is %s", args["coordinate"])
                    self.status = ScriptStatus.FAILED
            else:
                log.error("args error: %s", json.dumps(args))
                self.status = ScriptStatus.FAILED
            Navigation.goPathParam(self.param)

        if self.status != ScriptStatus.FAILED:
            if Navigation.isPathReached():
                self.status = ScriptStatus.FINISHED
            else:
                self.status = ScriptStatus.RUNNING
        return self.status

    def reset(self):
        self.status = ScriptStatus.NONE
        self.init = False
        self.param = {}
        Navigation.resetPath()

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        log.info(f"{Module.get_task_args()=}")
        log.info(f"{Module.get_task_id()=}")
        log.info(f"{Module.get_status()=}")


def main():
    Module.init()
    go_path = GoPath()

    while True:
        # 脚本任务状态管理
        status = Module.get_status()
        if status is ScriptStatus.RUNNING:
            status = go_path.run()
            Module.set_status(status)
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            Module.set_status(ScriptStatus.NONE)
            return
        go_path.print_info()
        time.sleep(0.1)


if __name__ == '__main__':
    from syspy import Logger

    log = Logger("jack_example")
    main()
