# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("clawMoveCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "L": {
        "value": 5.0,
        "tips": "Motion range length ",
        "type": "double",
        "unit":"m",
        "maxValue":10.0,
        "minValue":1.0
    },
    "V": {
        "value": 0.2,
        "tips": "Motion Speed",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.1
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

class MoveAction(IntEnum):
    MoveWait = 0
    Straight = 1
    Back = 2
    RightArcStraight = 3
    RightArcBack = 4
    LeftArcStraight = 5
    LeftArcBack = 6
    ActionEnd = 7

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.Straight
        self.move_dist = 5.0
        self.speed_x = 0.3

    def run(self):
        # 初始化
        if self.init:
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Straight
            self.move_dist = Module.get_task_args("L", 5.0)
            self.RotRadius = Module.get_task_args("RotRadius", 10.0)
            self.speed_x = Module.get_task_args("V", 0.5)
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.Straight:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":self.speed_x, "action_name":"GoStraightForward"})
        elif self.move_action == MoveAction.Back:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":-self.speed_x, "action_name":"GoStraightBackward"})
        elif self.move_action == MoveAction.RightArcStraight:
            self.status = Navigation.runOdoMove({"rot_degree":math.degrees(self.move_dist/self.RotRadius),
                                                                      "rot_radius":self.RotRadius,
                                                                      "rot_speed":self.speed_x/2,
                                                                      "maxAcc":0.05,
                                                                      "maxDec":0.05,
                                                                      "action_name":"GoLeftArcForward"})
        elif self.move_action == MoveAction.RightArcBack:
            self.status = Navigation.runOdoMove({"rot_degree":math.degrees(self.move_dist/self.RotRadius),
                                                                      "rot_radius":self.RotRadius,
                                                                      "rot_speed":-self.speed_x/2,
                                                                      "maxAcc":0.05,
                                                                      "maxDec":0.05,
                                                                      "action_name":"GoLeftArcBackward"})
        elif self.move_action == MoveAction.LeftArcStraight:
            self.status = Navigation.runOdoMove({"rot_degree":math.degrees(self.move_dist/self.RotRadius),
                                                                      "rot_radius":-self.RotRadius,
                                                                      "rot_speed":self.speed_x/2,
                                                                      "maxAcc":0.05,
                                                                      "maxDec":0.05,
                                                                      "action_name":"GoRightArcForward"})
        elif self.move_action == MoveAction.LeftArcBack:
            self.status = Navigation.runOdoMove({"rot_degree":math.degrees(self.move_dist/self.RotRadius),
                                                                      "rot_radius":-self.RotRadius,
                                                                      "rot_speed":-self.speed_x/2,
                                                                      "maxAcc":0.05,
                                                                      "maxDec":0.05,
                                                                      "action_name":"GoRightArcBackward"})

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING

        return self.status
    
    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["speed_x"] = self.speed_x
        info["RotRadius"] = self.RotRadius
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