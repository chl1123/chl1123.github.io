# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("canRotCalibAction")


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
    "W": {
        "value": 45,
        "tips": "Rotational angular velocity",
        "type": "double",
        "unit":"°/s",
        "maxValue":90,
        "minValue":10
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
        self.move_dist = 2.0
        self.speed_x = 0.5
        self.speed_w = 30 * math.pi / 180

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.GoStraightForWard
            self.move_dist = Module.get_task_args("L", 2.0)
            self.speed_x = Module.get_task_args("V", 0.5)
            self.speed_w = Module.get_task_args("W", 30 * math.pi / 180)
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.GoStraightForWard:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":self.speed_x, "action_name":"GoStraightForWard"})
        elif self.move_action == MoveAction.GoStraightBackWard:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":-self.speed_x, "action_name":"GoStraightBackWard"})
        elif self.move_action == MoveAction.GoRotForWard:
            self.status = Navigation.runOdoMove({"move_angle":  math.pi,  "speed_w":self.speed_w, "action_name":"GoRotForWard"})
        elif self.move_action == MoveAction.GoRotBackWard:
            self.status = Navigation.runOdoMove({"move_angle":  math.pi,  "speed_w":-self.speed_w, "action_name":"GoRotBackWard"})
    
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
        info["status"] = self.status
        info["move_dist"] = self.move_dist
        info["move_action"] = self.move_action
        info["speed_x"] = self.speed_x
        info["speed_w"] = self.speed_w
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