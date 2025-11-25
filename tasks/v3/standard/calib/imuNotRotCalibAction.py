# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("imuNotRotCalibAction")


"""
####BEGIN DEFAULT ARGS####
{
    "L": {
        "value": 2.0,
        "tips": "Motion range length",
        "type": "double",
        "unit":"m",
        "maxValue":5.0,
        "minValue":1.0
    },
    "V": {
        "value": 0.5,
        "tips": "Motion Speed",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.1
    },
    "goStraightCnt": {
        "value": 3,
        "tips": "Number of forward/backward straight movements",
        "type": "int",
        "unit":"count",
        "maxValue":10,
        "minValue":1
    },
    "goRotCnt": {
        "value": 2,
        "tips": "Number of in-place rotations",
        "type": "int",
        "unit":"count",
        "maxValue":10,
        "minValue":1
    }
}
####END DEFAULT ARGS####
"""

class MoveAction(IntEnum):
    GoStraightForWard = 0
    GoStraightBackWard = 1
    GoArcForWard = 2
    GoArcBackWard = 3
    ActionEnd = 4

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.GoStraightForWard

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.GoStraightForWard
            self.move_dist = Module.getTaskArgs("L", 2.0)
            self.speed_x = Module.getTaskArgs("V", 0.5)
            self.goStraightCnt = Module.getTaskArgs("goStraightCnt",3)
            self.goRotCnt = Module.getTaskArgs("goRotCnt",2)
            self.goCircleRadius = Module.getTaskArgs("goCircleRadius",3.0)
            self.curGoStraightCnt = 0
            self.curGoRotCnt = 0
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.GoStraightForWard:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed_x, "actionName":"GoStraight"})
        elif self.move_action == MoveAction.GoStraightBackWard:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":-self.speed_x, "actionName":"GoStraight"})
        elif self.move_action == MoveAction.GoArcForWard:
            self.status = Navigation.runOdoMove({"rotDegree":math.degrees(2*math.pi),
                                                                      "rotRadius":self.goCircleRadius,
                                                                      "rotSpeed":self.speed_x,
                                                                      "actionName":"GoRot"})
        elif self.move_action == MoveAction.GoArcBackWard:
            self.status = Navigation.runOdoMove({"rotDegree":math.degrees(2*math.pi),
                                                                      "rotRadius":self.goCircleRadius,
                                                                      "rotSpeed":-self.speed_x,
                                                                      "actionName":"GoRot"})
    
        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            if self.move_action == MoveAction.GoStraightBackWard and self.curGoStraightCnt < self.goStraightCnt - 1:
                self.curGoStraightCnt = self.curGoStraightCnt + 1
                self.move_action = MoveAction.GoStraightForWard
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING
            elif self.move_action == MoveAction.GoArcBackWard and self.curGoRotCnt < self.goRotCnt - 1:
                self.curGoRotCnt = self.curGoRotCnt + 1
                self.move_action = MoveAction.GoArcForWard
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING
            else:
                self.move_action = self.move_action + 1
                if self.move_action !=  MoveAction.ActionEnd:
                    Navigation.resetOdoMove()
                    self.status = ScriptStatus.RUNNING

    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["speed_x"] = self.speed_x
        info["goStraightCnt"] = self.goStraightCnt
        info["goRotCnt"] = self.goRotCnt
        info["curGoStraightCnt"] = self.curGoStraightCnt
        info["curGoRotCnt"] = self.curGoRotCnt
        info["goCircleRadius"] = self.goCircleRadius
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