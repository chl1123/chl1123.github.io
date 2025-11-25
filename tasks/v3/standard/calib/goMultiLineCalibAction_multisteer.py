# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("goMultiLineCalibAction_multisteer")

"""
####BEGIN DEFAULT ARGS####
{
    "V": {
        "value": 0.5,
        "tips": "Motion Speed",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.1
    },
    "L": {
        "value": 2.0,
        "tips": "Motion range length",
        "type": "double",
        "unit":"m",
        "maxValue":5.0,
        "minValue":1.0
    }
}
####END DEFAULT ARGS####
"""

class ActionType(Enum):
    NoAction = "NoAction"
    GoForward = "GoForward"
    GoBack = "GoBack"
    GoLeft = "GoLeft"
    BackLeft = "BackLeft"
    GoRight = "GoRight"
    BackRight = "BackRight"

class MoveAction(IntEnum):
    GoForward = 0
    GoBack = 1
    GoLeft = 2
    BackLeft = 3
    GoForward2 = 4
    GoRight = 5
    BackRight = 6
    BackForward2 = 7
    ActionEnd = 8

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.GoForward

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.GoForward
            self.move_dist = Module.getTaskArgs("L", 2.0)
            self.speed = Module.getTaskArgs("V", 0.5)
            self.cancel = False

        # 实时运行
        if self.move_action == 0:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed, "speedY":0.0, "actionName":"GoForward"})
        elif self.move_action == 1:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":-self.speed, "speedY":0.0, "actionName":"GoBack"})
        elif self.move_action == 2:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":0.0, "speedY":self.speed, "actionName":"GoLeft"})
        elif self.move_action == 3:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":0.0, "speedY":-self.speed, "actionName":"BackLeft"})
        elif self.move_action == 4:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist*0.1,  "speedX":self.speed, "speedY":0.0, "actionName":"GoForward2"})
        elif self.move_action == 5:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":0.0, "speedY":-self.speed, "actionName":"GoRight"})
        elif self.move_action == 6:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":0.0, "speedY":self.speed, "actionName":"BackRight"})
        elif self.move_action == 7:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist*0.1,  "speedX":-self.speed, "speedY":0.0, "actionName":"BackForward2"})

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
        info["move_dist"] = self.move_dist
        info["speed"] = self.speed
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