# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("imuCanRotCalibAction")

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
        "value": 1.0,
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
    "W": {
        "value": 45,
        "tips": "Rotational angular velocity",
        "type": "double",
        "unit":"°/s",
        "maxValue":90,
        "minValue":10
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
    GoRotForWard = 2
    GoRotBackWard = 3
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
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.GoStraightForWard
            self.move_dist = Module.get_task_args("L", 2.0)
            self.speed_x = Module.get_task_args("V", 1.0)
            self.speed_w = Module.get_task_args("W", 45) * math.pi / 180
            self.goStraightCnt = Module.get_task_args("goStraightCnt",3)
            self.goRotCnt = Module.get_task_args("goRotCnt",2)
            self.curGoStraightCnt = 0
            self.curGoRotCnt = 0
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.GoStraightForWard:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":self.speed_x, "action_name":"GoStraight"})
        elif self.move_action == MoveAction.GoStraightBackWard:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":-self.speed_x, "action_name":"GoStraight"})
        elif self.move_action == MoveAction.GoRotForWard:
            self.status = Navigation.runOdoMove({"move_angle": 3 * math.pi,  "speed_w":self.speed_w, "action_name":"GoRot"})
        elif self.move_action == MoveAction.GoRotBackWard:
            self.status = Navigation.runOdoMove({"move_angle": 3 * math.pi,  "speed_w":-self.speed_w, "action_name":"GoRot"})
    
        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            if self.move_action == MoveAction.GoStraightBackWard and self.curGoStraightCnt < self.goStraightCnt - 1:
                self.curGoStraightCnt = self.curGoStraightCnt + 1
                self.move_action = MoveAction.GoStraightForWard
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING
            elif self.move_action == MoveAction.GoRotBackWard and self.curGoRotCnt < self.goRotCnt - 1:
                self.curGoRotCnt = self.curGoRotCnt + 1
                self.move_action = MoveAction.GoRotForWard
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
        info["speed_w"] = self.speed_w
        info["goStraightCnt"] = self.goStraightCnt
        info["goRotCnt"] = self.goRotCnt
        info["curGoStraightCnt"] = self.curGoStraightCnt
        info["curGoRotCnt"] = self.curGoRotCnt
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
        if calib_move.status == ScriptStatus.FAILED:
            Module.set_status(ScriptStatus.FAILED)
            return
        if calib_move.cancel:
            return

if __name__ == '__main__':
    main()