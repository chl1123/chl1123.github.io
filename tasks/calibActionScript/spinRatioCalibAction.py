# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("spinRatioCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "W": {
        "value": 45,
        "tips": "角速度",
        "type": "double",
        "unit":"°/s",
        "maxValue":90,
        "minValue":10
    }
}
####END DEFAULT ARGS####
"""

class MoveAction(IntEnum):
    ActionStart = 0
    ActionEnd = 1

class CalibMove:

    def __init__(self):

        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.ActionStart
        self.move_angle = math.pi * 2
        self.speed_w=math.pi / 4

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.ActionStart
            self.move_angle = math.pi * 2
            self.speed_w = Module.get_task_args("W", 30) * math.pi / 180

        # 实时运行
        if self.move_action == 0:
            self.status = Navigation.runOdoMove({"move_angle":self.move_angle,  "speed_w":self.speed_w, "action_name":"GoRotForward", "spin":True})
        
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
        info["move_angle"] = self.move_angle
        info["speed_w"] = self.speed_w
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