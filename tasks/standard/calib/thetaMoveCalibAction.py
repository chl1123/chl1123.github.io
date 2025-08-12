# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("thetaMoveCalibAction")

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
        "value": 0.3,
        "tips": "速度",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.1
    },
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
    MoveWait = 0
    Rot1st4LeftArc = 1
    GoLeftArc = 2
    Rot2nd4GoForward = 3
    GoForward2Origin = 4
    Rot3rd4RightArc = 5
    GoRightArc = 6
    Rot4th4GoBackward = 7
    GoBackward2Origin = 8
    ActionEnd = 9

class CalibMove:
    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.Rot1st4LeftArc
        self.move_dist = 2.0
        self.speed_x = 0.3
        self.speed_w = math.pi/4

    def run(self):
        if self.init:
            Navigation.resetOdoMove()
            Module.set_status(ScriptStatus.RUNNING)
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Rot1st4LeftArc
            self.move_dist = Module.get_task_args("L", 2.0)
            self.speed_x = Module.get_task_args("V", 0.3)
            self.speed_w = Module.get_task_args("W", 45) * math.pi / 180
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.Rot1st4LeftArc:
            self.status = Navigation.runOdoMove({"move_angle": math.pi/2,  "speed_w":self.speed_w, "action_name":"Rot1st4LeftArc"})
        elif self.move_action == MoveAction.GoLeftArc:
            self.status = Navigation.runOdoMove({"rot_degree":180.0,
                                                                      "rot_radius":-0.5*self.move_dist,
                                                                      "rot_speed":self.speed_x,
                                                                      "action_name":"GoLeftArc"})
        elif self.move_action == MoveAction.Rot2nd4GoForward:
            self.status = Navigation.runOdoMove({"move_angle": math.pi/2,  "speed_w":-self.speed_w, "action_name":"Rot2nd4GoForward"})
        elif self.move_action == MoveAction.GoForward2Origin:
            self.status = Navigation.runOdoMove({"move_dist":self.move_dist, "speed_x":self.speed_x,  "action_name":"GoForward2Origin"})
        elif self.move_action == MoveAction.Rot3rd4RightArc:
            self.status = Navigation.runOdoMove({"move_angle": math.pi/2,  "speed_w":self.speed_w, "action_name":"Rot3rd4RightArc"})
        elif self.move_action == MoveAction.GoRightArc:
            self.status = Navigation.runOdoMove({"rot_degree":180.0,
                                                                      "rot_radius":0.5*self.move_dist,
                                                                      "rot_speed":self.speed_x,
                                                                      "action_name":"GoRightArc"})
        elif self.move_action == MoveAction.Rot4th4GoBackward:
            self.status = Navigation.runOdoMove({"move_angle": math.pi/2,  "speed_w":-self.speed_w, "action_name":"Rot4th4GoBackward"})
        elif self.move_action == MoveAction.GoBackward2Origin:
            self.status = Navigation.runOdoMove({"move_dist":self.move_dist, "speed_x":-self.speed_x,  "action_name":"GoForward2Origin"})

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
