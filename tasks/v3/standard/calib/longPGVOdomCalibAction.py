# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("longPGVOdomCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "distanceBack": {
        "value": 0.1,
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
        "value": 1,
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
        "value": 0.1,
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
    InitcallGo2QRCenter = 0
    ShortBackward = 1
    Forward = 2
    Backward = 3
    callGo2QRCenter = 4
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
        self.move_action = MoveAction.InitcallGo2QRCenter
        self.short_move_dist = 0.1
        self.short_rot_angle = math.pi/6
        self.move_dist = 1.0
        self.move_angle = 2 * math.pi
        self.speed_x = 0.1
        self.speed_w = math.pi/6

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Navigation.resetOdoMove()
            Module.setStatus(ScriptStatus.RUNNING)
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.InitcallGo2QRCenter
            self.upside = Module.getTaskArgs("up_side", False)
            self.short_move_dist = Module.getTaskArgs("distanceBack", 0.1)
            self.short_rot_angle = Module.getTaskArgs("angleBack", 30.0)*math.pi/180
            self.move_dist = Module.getTaskArgs("distanceForward", 1.0)
            self.move_angle = Module.getTaskArgs("angleForward", 360)*math.pi/180
            self.speed_x = Module.getTaskArgs("V", 0.1)
            self.speed_w = Module.getTaskArgs("W", 30) * math.pi / 180
            Navigation.resetGoPGV()
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.InitcallGo2QRCenter:
            self.status = Navigation.goPGVRun({"useDownPgv":not self.upside, "actionName":"callGo2QRCenter"})
        elif self.move_action == MoveAction.ShortBackward:
            self.status = Navigation.runOdoMove({"moveDist": self.short_move_dist,  "speedX":-self.speed_x, "actionName":"short_move_dist"})
        elif self.move_action == MoveAction.Forward:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed_x, "actionName":"Forward"})
        elif self.move_action == MoveAction.Backward:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist - self.short_move_dist,  "speedX":-self.speed_x, "actionName":"Backward"})
        elif self.move_action == MoveAction.callGo2QRCenter:
            self.status = Navigation.goPGVRun({"useDownPgv":not self.upside, "actionName":"callGo2QRCenter"})
        elif self.move_action == MoveAction.ShortRotLeftInPlace:
            self.status = Navigation.runOdoMove({"moveAngle": self.short_rot_angle,  "speedW":-self.speed_w, "actionName":"ShortRotLeftInPlace"})
        elif self.move_action == MoveAction.RotLeftInPlace:
            self.status = Navigation.runOdoMove({"moveAngle": self.move_angle+self.short_rot_angle,  "speedW":self.speed_w, "actionName":"RotLeftInPlace"})

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
            if self.move_action == MoveAction.callGo2QRCenter:
                Navigation.resetGoPGV()
                self.status = ScriptStatus.RUNNING
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
        Navigation.resetGoPGV()

    def Suspend(self):
        Module.setStatus(ScriptStatus.SUSPENDED)
        print("suspend!!!")

    def Resume(self):
        Module.setStatus(ScriptStatus.RUNNING)
        Navigation.resetGoPGV()
        Navigation.resetOdoMove()
        print("resume!!!")
        
def main():
    calib_move = CalibMove()
    Module.init()
    Module.setCancelCallback(calib_move.Cancel)
    Module.setSuspendCallback(calib_move.Suspend)
    Module.setResumeCallback(calib_move.Resume)
    while True:
        calib_move.run()
        calib_move.print()
        time.sleep(0.1)
        if calib_move.status == ScriptStatus.FINISHED:
            Module.setStatus(ScriptStatus.FINISHED)
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