# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("akmanClawMoveCalibAction")

"""
####BEGIN DEFAULT ARGS####
{    
    "L": {
        "value": 3.0,
        "tips": "Motion range length",
        "type": "double",
        "unit":"m",
        "maxValue":10.0,
        "minValue":0.01
    },
    "V": {
        "value": 0.5,
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
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Straight
            self.move_dist = Module.getTaskArgs("L", 5.0)
            self.RotRadius = Module.getTaskArgs("RotRadius", 10.0)
            self.speed_x = Module.getTaskArgs("V", 0.5)
            self.cancel = False
            # 定位策略切换
            self.locType = Module.getTaskArgs("locType", "")
            self.locName = Module.getTaskArgs("locName", "")
            if self.locType != "" and self.locName != "":
                policy = dict()
                if self.locType == "Laser":
                    policy = {"localization.localizationType": "2D",
                              "localization.localizationType.2D.localizationLaser": self.locName}
                elif self.locType == "Camera":
                    policy = {"localization.localizationType": "3D",
                              "localization.localizationType.3D.localizationLaser": self.locName}
                elif self.locType == "CodeScanner":
                    policy = {"localization.localizationType": "codeScanner",
                              "localization.localizationType.codeScanner.localizationCodeScanner": self.locName}
                Navigation.appendCustomPolicy("policy", policy)

        # 实时运行
        if self.move_action == MoveAction.Straight:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed_x, "actionName":"GoStraightForward"})
        elif self.move_action == MoveAction.Back:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":-self.speed_x, "actionName":"GoStraightBackward"})
        elif self.move_action == MoveAction.RightArcStraight:
            self.status = Navigation.runOdoMove({"rotDegree":math.degrees(self.move_dist/self.RotRadius),
                                                                      "rotRadius":self.RotRadius,
                                                                      "rotSpeed":self.speed_x,
                                                                      "actionName":"GoLeftArcForward"})
        elif self.move_action == MoveAction.RightArcBack:
            self.status = Navigation.runOdoMove({"rotDegree":math.degrees(self.move_dist/self.RotRadius),
                                                                      "rotRadius":self.RotRadius,
                                                                      "rotSpeed":-self.speed_x,
                                                                      "actionName":"GoLeftArcBackward"})
        elif self.move_action == MoveAction.LeftArcStraight:
            self.status = Navigation.runOdoMove({"rotDegree":math.degrees(self.move_dist/self.RotRadius),
                                                                      "rotRadius":-self.RotRadius,
                                                                      "rotSpeed":self.speed_x,
                                                                      "actionName":"GoRightArcForward"})
        elif self.move_action == MoveAction.LeftArcBack:
            self.status = Navigation.runOdoMove({"rotDegree":math.degrees(self.move_dist/self.RotRadius),
                                                                      "rotRadius":-self.RotRadius,
                                                                      "rotSpeed":-self.speed_x,
                                                                      "actionName":"GoRightArcBackward"})

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING

    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["speed_x"] = self.speed_x
        info["RotRadius"] = self.RotRadius
        info["locType"] = self.locType
        info["locName"] = self.locName
        log.info(json.dumps(info))

    def Cancel(self):
        print("cancel!!!")
        self.cancel = True

def main():
    calib_move = CalibMove()
    Module.init()
    Module.setCancelCallback(calib_move.Cancel)
    while True:
        calib_move.run()
        calib_move.print()
        time.sleep(0.1)
        if calib_move.status == ScriptStatus.FINISHED:
            Module.setStatus(ScriptStatus.FINISHED)
            return
        if calib_move.status == ScriptStatus.FAILED:
            Module.setStatus(ScriptStatus.FAILED)
            return
        if calib_move.cancel:
            return

if __name__ == '__main__':
    main()