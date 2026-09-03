import json
import math
import time
from typing import Optional

from syspy import Module, ScriptStatus, Navigation, Loc, Trace
from syspy.lib.action_task import ActionBase, ActionStatus


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
      "tips":"最大线速度",
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
      "tips":"最大角加速度",
      "type":"double",
      "unit": "rad/s^2"
    },
    "maxRotDec":{
      "value": 1,
      "tips":"最大角减速度",
      "type":"double",
      "unit": "rad/s^2"   
    },
    "holdDir":{
      "value": 999,
      "tips":"全向车平移时车身的固定角度",
      "type":"double",
      "unit": "°"        
    }
}
####END DEFAULT ARGS####
"""


class GoPath(ActionBase):
    def __init__(self, args: Optional[dict] = None):
        super().__init__("GoPath")
        self.goal = [0, 0, 0]
        self.init = False
        self.action_status = ActionStatus.INIT
        self.param = {}
        self.path_started = False
        self.args = args
        self.action_name = self.__class__.__name__
        self.start_time = time.time()
        self.action_state = {}
        Trace.log(f"go path init, args:{args}", name="fork.task")

    def run(self, ctx=None, args: Optional[dict] = None):
        self.action_status = ActionStatus.RUNNING
        if args is None:
            if isinstance(ctx, dict):
                args = ctx
            elif self.args is not None:
                args = self.args
            else:
                args = Module.getTaskArgs()
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
                if "holdDir" in args:
                    Navigation.setPathHoldDir(float(args["holdDir"]))
                elif "hold_dir" in args and args["hold_dir"] not in (None, False):
                    Navigation.setPathHoldDir(float(args["hold_dir"]))
                if "maxAcc" in args:
                    self.param["maxAcc"] = float(args["maxAcc"])
                if "maxDec" in args:
                    self.param["maxDec"] = float(args["maxDec"])
                if "maxRotAcc" in args:
                    self.param["maxRotAcc"] = float(args["maxRotAcc"])
                if "maxRotDec" in args:
                    self.param["maxRotDec"] = float(args["maxRotDec"])
                Trace.log(f"goal:{str(self.goal)}")
                if args["coordinate"] == "robot":
                    Navigation.setPathOnRobot([0, self.goal[0]], [0, self.goal[1]], self.goal[2])
                elif args["coordinate"] == "world":
                    x = Loc.getPose()["x"]
                    y = Loc.getPose()["y"]
                    Navigation.setPathOnWorld([x, self.goal[0]], [y, self.goal[1]], self.goal[2])
                else:
                    coordinate = args["coordinate"]
                    Navigation.setTaskError("WrongCoordinate",
                                            f"coordinate only support robot and world. Input is {coordinate}")
                    self.action_status = ActionStatus.FAILED
            else:
                Navigation.setTaskError("GoPathArgsWrong", f"args wrong: {json.dumps(args)}")
                self.action_status = ActionStatus.FAILED
            if self.action_status != ActionStatus.FAILED:
                Navigation.goPathParam(self.param)
                self.path_started = True

        if self.action_status != ActionStatus.FAILED:
            if Navigation.isPathReached():
                self.action_status = ActionStatus.FINISHED
            else:
                self.action_status = ActionStatus.RUNNING
        return self.action_status

    def reset(self):
        self.action_status = ActionStatus.RUNNING
        self.init = False
        self.param = {}
        self.path_started = False
        Navigation.resetPath()

    def cancel(self):
        Navigation.resetPath()
        self.path_started = False
        self.action_status = ActionStatus.FAILED

    def suspend(self):
        if self.action_status == ActionStatus.RUNNING:
            if self.path_started:
                Navigation.stopRobotNow()
            super().suspend()

    def resume(self):
        if self.action_status == ActionStatus.SUSPENDED:
            if self.path_started:
                Navigation.goPathParam(self.param)
            super().resume()

    def _trace_state(self) -> dict:
        return {
            "action_status": int(self.action_status),
            "goal": self.goal if isinstance(self.goal, list) else [],
        }

    def print_info(self):
        # 打印当前任务队列、当前任务、当前任务id、当前任务状态
        Trace.log(f"{Module.getTaskArgs()=}")
        Trace.log(f"{Module.getTaskId()=}")
        Trace.log(f"{Module.getStatus()=}")


def to_script_status(status):
    if status == ActionStatus.FINISHED:
        return ScriptStatus.FINISHED
    if status == ActionStatus.FAILED:
        return ScriptStatus.FAILED
    if status == ActionStatus.RUNNING:
        return ScriptStatus.RUNNING
    return ScriptStatus.NONE


def main():
    Module.init()
    go_path = GoPath()

    while True:
        # 脚本任务状态管理
        status = Module.getStatus()
        if status is ScriptStatus.RUNNING:
            status = go_path.run()
            Module.setStatus(to_script_status(status))
        elif status in (ScriptStatus.FAILED, ScriptStatus.FINISHED):
            Module.setStatus(ScriptStatus.NONE)
            return
        go_path.print_info()
        time.sleep(0.1)


if __name__ == '__main__':
    main()
