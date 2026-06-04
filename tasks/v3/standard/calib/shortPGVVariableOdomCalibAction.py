# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus,CodeScanner

log = Logger("shortPGVOdomCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "distanceBack": {
        "value": 0.2,
        "tips": "Backward movement distance",
        "type": "double",
        "unit":"m",
        "maxValue":10.0,
        "minValue":0.01
    },
    "angleBack": {
        "value":30,
        "tips": "Clockwise rotation angle",
        "type": "double",
        "unit":"°",
        "maxValue":360.0,
        "minValue":1.0
    },
    "distanceForward": {
        "value": 0.3,
        "tips": "Forward movement distance",
        "type": "double",
        "unit":"m",
        "maxValue":10.0,
        "minValue":0.01
    },
    "angleForward": {
        "value": 360,
        "tips": "Counterclockwise rotation angle",
        "type": "double",
        "unit":"°",
        "maxValue":3600.0,
        "minValue":1.0
    },
    "V": {
        "value": 0.02,
        "tips": "Motion Speed",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.01
    },
    "W": {
        "value": 30,
        "tips": "Rotational angular velocity",
        "type": "double",
        "unit":"°/s",
        "maxValue":360.0,
        "minValue":1.0
    }
}
####END DEFAULT ARGS####
"""

class MoveAction(IntEnum):
    ShortBackward = 1
    Forward = 2
    Backward = 3
    ShortRotRightInPlace = 4
    ShortRotLeftInPlace = 5
    RotLeftInPlace = 6
    ActionEnd = 7

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.ShortBackward
        self.short_move_dist = 0.2
        self.short_rot_angle = math.pi/6
        self.move_dist = 0.3
        self.move_angle = 2 * math.pi
        self.speed_x = 0.02
        self.speed_w = math.pi/6
        self.move_center_x = 0.0
        self.move_center_y = 0.0
        self.move_center_theta = 0.0

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Navigation.resetOdoMove()
            Module.setStatus(ScriptStatus.RUNNING)
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.ShortBackward 
            self.upside = Module.getTaskArgs("up_side", False)
            self.short_move_dist = Module.getTaskArgs("distanceBack", 0.2)
            self.short_rot_angle = Module.getTaskArgs("angleBack", 30.0)*math.pi/180
            self.move_dist = Module.getTaskArgs("distanceForward", 0.3)
            self.move_angle = Module.getTaskArgs("angleForward", 360)*math.pi/180
            self.speed_x = Module.getTaskArgs("V", 0.02)
            self.speed_w = Module.getTaskArgs("W", 30) * math.pi / 180
            self.move_center_x = Module.getTaskArgs("move_center_x", 0.0)
            self.move_center_y = Module.getTaskArgs("move_center_y", 0.0)
            self.move_center_theta = Module.getTaskArgs("move_center_theta", 0.0)
            self.cancel = False

        # 实时运行 , "PGV_ReachAngle":0.5
        if self.move_action == MoveAction.ShortBackward:
            self.status = Navigation.runOdoMove({"moveDist": self.short_move_dist,  "speedX":-self.speed_x, "actionName":"short_move_dist"})
        elif self.move_action == MoveAction.Forward:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed_x, "actionName":"Forward"})
        elif self.move_action == MoveAction.Backward:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist - self.short_move_dist,  "speedX":-self.speed_x, "actionName":"Backward"})
        elif self.move_action == MoveAction.ShortRotRightInPlace:
            self.status = Navigation.runOdoMove({"moveAngle": self.short_rot_angle,  "speedW":-self.speed_w, "actionName":"ShortRotRightInPlace", 
                                                 "move_center_x":self.move_center_x, "move_center_y":self.move_center_y, "move_center_theta":self.move_center_theta})
        elif self.move_action == MoveAction.ShortRotLeftInPlace:
            self.status = Navigation.runOdoMove({"moveAngle": self.short_rot_angle,  "speedW":self.speed_w, "actionName":"ShortRotLeftInPlace", 
                                                  "move_center_x":self.move_center_x, "move_center_y":self.move_center_y, "move_center_theta":self.move_center_theta})
        elif self.move_action == MoveAction.RotLeftInPlace:
            self.status = Navigation.runOdoMove({"moveAngle": self.move_angle,  "speedW":self.speed_w, "actionName":"RotLeftInPlace", 
                                                 "move_center_x":self.move_center_x, "move_center_y":self.move_center_y, "move_center_theta":self.move_center_theta})

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
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
        info["speed_x"] = self.speed_x
        info["speed_w"] = self.speed_w
        log.info(json.dumps(info))

    def Cancel(self):
        print("cancel!!!")
        self.cancel = True
        Navigation.resetOdoMove()
        
def main():
    calib_move = CalibMove()
    Module.init()
    Module.setCancelCallback(calib_move.Cancel)
    Module.setSuspendCallback(calib_move.Cancel)
    Module.setResumeCallback(calib_move.Cancel)
    while True:
        calib_move.run()
        calib_move.print()
        time.sleep(0.1)
        if calib_move.status == ScriptStatus.FINISHED:
            Module.setStatus(ScriptStatus.FINISHED)
            Navigation.resetOdoMove()
            return
        if calib_move.status == ScriptStatus.FAILED:
            Module.setStatus(ScriptStatus.FAILED)
            calib_move.Cancel()
            return
        if calib_move.cancel:
            Module.setStatus(ScriptStatus.FAILED)
            return

if __name__ == '__main__':
    main()