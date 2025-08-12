# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("steerOffsetRotCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "W": {
        "value": 25,
        "tips": "长度",
        "type": "double",
        "unit":"°/s",
        "maxValue":90,
        "minValue":10
    }
}
####END DEFAULT ARGS####
"""

class ActionType(Enum):
    NoAction = "NoAction"
    GoStraightForward = "GoStraightForward"
    GoStraightBackward = "GoStraightBackward"
    GoRotForward = "GoRotForward"
    GoRotBackward = "GoRotBackward"
    GoLeftArcForward = "GoLeftArcForward"
    GoLeftArcBackward = "GoLeftArcBackward"
    GoRightArcForward = "GoRightArcForward"
    GoRightArcBackward = "GoRightArcBackward"
    Capture = "Capture"
    SteerLeft = "SteerLeft"
    SteerRight = "SteerRight"

# 为方便分离模态，每次运动的角速度方向要相异
class MoveAction(IntEnum):
    SteerPSpeedPSteer = 0
    SteerPSpeedP = 1
    SteerPSpeedNSteer = 2
    SteerPSpeedN = 3
    SteerNSpeedNSteer = 4
    SteerNSpeedN = 5
    SteerNSpeedPSteer = 6
    SteerNSpeedP = 7
    ActionEnd = 8

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.SteerPSpeedPSteer
        self.steer_name = ""

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.SteerPSpeedPSteer
            self.steer_name = Module.get_task_args("name","")
            self.speed_w = Module.get_task_args("W", 45) * math.pi / 180
            self.cancel = False

        # 实时运行
        if self.move_action == 0:
            self.status = Navigation.setSteerAngle(self.steer_name, math.pi/2,"NoAction")
            if self.status:
                self.status = ScriptStatus.FINISHED
        elif self.move_action == 1:
            self.status = Navigation.runOdoMove({"move_angle": math.pi,  "speed_w":self.speed_w, "action_name":"GoRotForward1"})
        elif self.move_action == 2:
            self.status = Navigation.setSteerAngle(self.steer_name,math.pi/2,"NoAction")
            if self.status:
                self.status = ScriptStatus.FINISHED
        elif self.move_action == 3:
            self.status = Navigation.runOdoMove({"move_angle": math.pi,  "speed_w":-self.speed_w, "action_name":"GoRotBackward1"})
        elif self.move_action == 4:
            self.status = Navigation.setSteerAngle(self.steer_name, -math.pi/2,"NoAction")
            if self.status:
                self.status = ScriptStatus.FINISHED
        elif self.move_action == 5:
            self.status = Navigation.runOdoMove({"move_angle": math.pi,  "speed_w":self.speed_w, "action_name":"GoRotForward2"})
        elif self.move_action == 6:
            self.status = Navigation.setSteerAngle(self.steer_name, -math.pi/2,"NoAction")
            if self.status:
                self.status = ScriptStatus.FINISHED
        elif self.move_action == 7:
            self.status = Navigation.runOdoMove({"move_angle": math.pi,  "speed_w":-self.speed_w, "action_name":"GoRotBackward2"})
        
        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
            if self.move_action !=  MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING
        
    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["steer_name"] = self.steer_name
        info["speed_w"] = self.speed_w
        info["status"] = self.status
        info["goal status"] = ScriptStatus.FINISHED
        log.info(json.dumps(info))

    def Cancel(self):
        print("cancel!!!")
        self.cancel = True

def main():
    calib_move = CalibMove()
    Module.init()
    Module.set_cancel_callback(calib_move.Cancel)
    while True:
        calib_move.run()
        calib_move.print()
        time.sleep(0.1)
        if calib_move.status == ScriptStatus.FINISHED:
            Module.set_status(ScriptStatus.FINISHED)
            return
        if calib_move.cancel:
            return

if __name__ == '__main__':
    main()