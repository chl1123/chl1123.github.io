# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("goMultiLineCalibAction_multisteer")

"""
####BEGIN DEFAULT ARGS####
{
    "V": {
        "value": 0.5,
        "tips": "速度",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.1
    },
    "L": {
        "value": 2.0,
        "tips": "长度",
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
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.GoForward
            self.move_dist = Module.get_task_args("L", 2.0)
            self.speed = Module.get_task_args("V", 0.5)

        # 实时运行
        if self.move_action == 0:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":self.speed, "speed_y":0.0, "action_name":"GoForward"})
        elif self.move_action == 1:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":-self.speed, "speed_y":0.0, "action_name":"GoBack"})
        elif self.move_action == 2:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":0.0, "speed_y":self.speed, "action_name":"GoLeft"})
        elif self.move_action == 3:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":0.0, "speed_y":-self.speed, "action_name":"BackLeft"})
        elif self.move_action == 4:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist*0.1,  "speed_x":self.speed, "speed_y":0.0, "action_name":"GoForward2"})
        elif self.move_action == 5:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":0.0, "speed_y":-self.speed, "action_name":"GoRight"})
        elif self.move_action == 6:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":0.0, "speed_y":self.speed, "action_name":"BackRight"})
        elif self.move_action == 7:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist*0.1,  "speed_x":-self.speed, "speed_y":0.0, "action_name":"BackForward2"})

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

def main():
    calib_move = CalibMove()
    Module.init()
    while True:
        calib_move.run()
        calib_move.print()
        if calib_move.status == ScriptStatus.FINISHED:
            Module.set_status(ScriptStatus.FINISHED)
            return

if __name__ == '__main__':
    main()