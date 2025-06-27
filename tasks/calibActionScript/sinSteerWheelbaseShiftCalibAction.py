# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("sinSteerWheelbaseShiftCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "rotCount": {
        "value": 3,
        "tips": "圈数",
        "type": "int",
        "unit":"圈",
        "maxValue":10,
        "minValue":1
    },
    "W": {
        "value": 30,
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
    ForkUnload1 = 1
    Rot1st = 2
    ForkLoad = 3
    Rot2nd = 4
    ForkUnload2 = 5
    ActionEnd = 6

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.ForkUnload1
        self.rotCount = 3
        self.speed_w = 45*math.pi/180

    def run(self):
        # 初始化
        if self.init:
            Navigation.resetOdoMove()
            Navigation.resetForkHeight()
            Module.set_status(ScriptStatus.RUNNING)
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.ForkUnload1
            self.rotCount = int(Module.get_task_args("rotCount",3))
            self.speed_w = Module.get_task_args("W", 30) * math.pi / 180
            Navigation.resetGoPGV()
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.ForkUnload1:
            self.status = Navigation.runForkHeight({"id":"SELF_POSITION",  "operation":"ForkUnload", "end_height":0.0})
        elif self.move_action == MoveAction.Rot1st:
            self.status = Navigation.runOdoMove({"move_angle": self.rotCount * 2 * math.pi,  "speed_w":self.speed_w, "action_name":"Rot1st"})
        elif self.move_action == MoveAction.ForkLoad:
            self.status = Navigation.runForkHeight({"id":"SELF_POSITION",  "operation":"ForkLoad", "end_height":1.0})
        elif self.move_action == MoveAction.Rot2nd:
            self.status = Navigation.runOdoMove({"move_angle": self.rotCount * 2 * math.pi,  "speed_w":self.speed_w, "action_name":"Rot2nd"})
        elif self.move_action == MoveAction.ForkUnload2:
            self.status = Navigation.runForkHeight({"id":"SELF_POSITION",  "operation":"ForkUnload", "end_height":0.0})

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            if self.move_action == MoveAction.ForkUnload1 or self.move_action == MoveAction.ForkUnload2:
                Navigation.wheelBaseShift(False)
            if self.move_action == MoveAction.ForkLoad:
                Navigation.wheelBaseShift(True)
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                Navigation.resetForkHeight()
                self.status = ScriptStatus.RUNNING
        return self.status
    
    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["rotCount"] = self.rotCount
        info["move_action"] = self.move_action
        info["speed_w"] = self.speed_w
        log.info(json.dumps(info))

    def cancel(self):
        print("cancel!!!")
        self.cancel = True

def main():
    calib_move = CalibMove()
    Module.init()
    Module.set_cancel_callback(calib_move.cancel)
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