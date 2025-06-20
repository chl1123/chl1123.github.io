# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("multiDirectionGoLineCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "L": {
        "value": 2.0,
        "tips": "长度",
        "type": "double",
        "unit":"m",
        "maxValue":5.0,
        "minValue":1.0
    },
    "V": {
        "value": 0.5,
        "tips": "速度",
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
    Forward = 0
    Backward = 1
    ActionEnd = 2

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.Forward

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Forward
            self.move_dist = Module.get_task_args("L", 2.0)
            self.speed = Module.get_task_args("V", 0.5)
            self.move_num = Module.get_task_args("move_num", 4)
            self.move_n = 0
            self.move_dir = self.move_n * math.pi / self.move_num
            self.speed_x = self.speed * math.cos(self.move_dir)
            self.speed_y = self.speed * math.sin(self.move_dir)

        # 实时运行
        if self.move_action == 0:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":self.speed_x, "speed_y":self.speed_y, "action_name":"GoStraightForward"+str(self.move_n)})
        elif self.move_action == 1:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":-self.speed_x, "speed_y":-self.speed_y, "action_name":"GoStraightBackward"+str(self.move_n)})
        
        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING
            if self.move_action == MoveAction.ActionEnd and self.move_n + 1 < self.move_num:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING
                self.move_n = self.move_n + 1
                self.move_dir = self.move_n * math.pi / self.move_num
                self.speed_x = self.speed * math.cos(self.move_dir)
                self.speed_y = self.speed * math.sin(self.move_dir)
                self.move_action = MoveAction.Forward
        
    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["move_dist"] = self.move_dist
        info["speed_x"] = self.speed_x
        info["speed_y"] = self.speed_y
        info["move_n"] = self.move_n
        info["move_num"] = self.move_num
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
