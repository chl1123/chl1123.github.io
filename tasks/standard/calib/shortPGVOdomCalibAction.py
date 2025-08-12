# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("shortPGVOdomCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "distanceBack": {
        "value": 0.2,
        "tips": "长度",
        "type": "double",
        "unit":"m",
        "maxValue":10.0,
        "minValue":0.01
    },
    "angleBack": {
        "value":30,
        "tips": "角度",
        "type": "double",
        "unit":"°",
        "maxValue":360.0,
        "minValue":1.0
    },
    "distanceForward": {
        "value": 0.3,
        "tips": "长度",
        "type": "double",
        "unit":"m",
        "maxValue":10.0,
        "minValue":0.01
    },
    "angleForward": {
        "value": 360,
        "tips": "角度",
        "type": "double",
        "unit":"°",
        "maxValue":3600.0,
        "minValue":1.0
    },
    "V": {
        "value": 0.02,
        "tips": "速度",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.01
    },
    "W": {
        "value": 30,
        "tips": "角速度",
        "type": "double",
        "unit":"°/s",
        "maxValue":360.0,
        "minValue":1.0
    }
}
####END DEFAULT ARGS####
"""

class MoveAction(IntEnum):
    InitcallGo2QRCenter = 0
    ShortBackward = 1
    Forward = 2
    Backward = 3
    callGo2QRCenter = 4
    ShortRotRightInPlace = 5
    ShortRotLeftInPlace = 6
    RotLeftInPlace = 7
    ActionEnd = 8

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.InitcallGo2QRCenter
        self.short_move_dist = 0.2
        self.short_rot_angle = math.pi/6
        self.move_dist = 0.3
        self.move_angle = 2 * math.pi
        self.speed_x = 0.02
        self.speed_w = math.pi/6

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Navigation.resetOdoMove()
            Module.set_status(ScriptStatus.RUNNING)
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.InitcallGo2QRCenter
            self.upside = Module.get_task_args("up_side", False)
            self.short_move_dist = Module.get_task_args("distanceBack", 0.2)
            self.short_rot_angle = Module.get_task_args("angleBack", 30.0)*math.pi/180
            self.move_dist = Module.get_task_args("distanceForward", 0.3)
            self.move_angle = Module.get_task_args("angleForward", 360)*math.pi/180
            self.speed_x = Module.get_task_args("V", 0.02)
            self.speed_w = Module.get_task_args("W", 30) * math.pi / 180
            Navigation.resetGoPGV()
            self.cancel = False

        # 实时运行 , "PGV_ReachAngle":0.5
        if self.move_action == MoveAction.InitcallGo2QRCenter:
            self.status = Navigation.goPGVRun({"use_down_pgv":not self.upside, "action_name":"callGo2QRCenter", "PGV_ReachDist":0.01})
        elif self.move_action == MoveAction.ShortBackward:
            self.status = Navigation.runOdoMove({"move_dist": self.short_move_dist,  "speed_x":-self.speed_x, "action_name":"short_move_dist"})
        elif self.move_action == MoveAction.Forward:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":self.speed_x, "action_name":"Forward"})
        elif self.move_action == MoveAction.Backward:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist - self.short_move_dist,  "speed_x":-self.speed_x, "action_name":"Backward"})
        elif self.move_action == MoveAction.callGo2QRCenter:
            self.status = Navigation.goPGVRun({"use_down_pgv":not self.upside, "action_name":"callGo2QRCenter", "PGV_ReachDist":0.01})
        elif self.move_action == MoveAction.ShortRotRightInPlace:
            self.status = Navigation.runOdoMove({"move_angle": self.short_rot_angle,  "speed_w":-self.speed_w, "action_name":"ShortRotRightInPlace"})
        elif self.move_action == MoveAction.ShortRotLeftInPlace:
            self.status = Navigation.runOdoMove({"move_angle": self.short_rot_angle,  "speed_w":self.speed_w, "action_name":"ShortRotLeftInPlace"})
        elif self.move_action == MoveAction.RotLeftInPlace:
            self.status = Navigation.runOdoMove({"move_angle": self.move_angle,  "speed_w":self.speed_w, "action_name":"RotLeftInPlace"})

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
            if self.move_action == MoveAction.callGo2QRCenter:
                Navigation.resetGoPGV()
                self.status = ScriptStatus.RUNNING
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING

        return self.status
    
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