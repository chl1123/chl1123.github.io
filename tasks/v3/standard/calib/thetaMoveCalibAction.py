# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus,RobotParam

log = Logger("thetaMoveCalibAction")

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
        "value": 0.2,
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
            Module.setStatus(ScriptStatus.RUNNING)
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Rot1st4LeftArc
            self.move_dist = Module.getTaskArgs("L", 2.0)
            self.speed_x = Module.getTaskArgs("V", 0.3)
            self.speed_w = Module.getTaskArgs("W", 45) * math.pi / 180
            self.cancel = False
            # 定位策略切换
            self.locType = Module.getTaskArgs("locType", "")
            self.locName = Module.getTaskArgs("locName", "")
            if self.locType != "" and self.locName != "":
                policy = dict()
                if self.locType == "Laser":
                    localization_type = RobotParam.getConfig("localization", "localizationType")
                    if localization_type == "reflector":
                        policy = {"localization.localizationType": "reflector",
                                "localization.localizationType.reflector.localizationLaser": self.locName}
                    else:
                        policy = {"localization.localizationType": "laser2d",
                                "localization.localizationType.laser2d.localizationLaser": self.locName}
                elif self.locType == "Camera":
                    policy = {"localization.localizationType": "laser3d",
                              "localization.localizationType.laser3d.localizationLaser": self.locName}
                elif self.locType == "CodeScanner":
                    policy = {"localization.localizationType": "codeScanner",
                              "localization.localizationType.codeScanner.localizationCodeScanner": self.locName}
                Navigation.appendCustomPolicy("policy", policy)

        # 实时运行
        if self.move_action == MoveAction.Rot1st4LeftArc:
            self.status = Navigation.runOdoMove({"moveAngle": math.pi/2,  "speedW":self.speed_w, "actionName":"Rot1st4LeftArc"})
        elif self.move_action == MoveAction.GoLeftArc:
            self.status = Navigation.runOdoMove({"rotDegree":180.0,
                                                                      "rotRadius":-0.5*self.move_dist,
                                                                      "rotSpeed":self.speed_x,
                                                                      "actionName":"GoLeftArc"})
        elif self.move_action == MoveAction.Rot2nd4GoForward:
            self.status = Navigation.runOdoMove({"moveAngle": math.pi/2,  "speedW":-self.speed_w, "actionName":"Rot2nd4GoForward"})
        elif self.move_action == MoveAction.GoForward2Origin:
            self.status = Navigation.runOdoMove({"moveDist":self.move_dist, "speedX":self.speed_x,  "actionName":"GoForward2Origin"})
        elif self.move_action == MoveAction.Rot3rd4RightArc:
            self.status = Navigation.runOdoMove({"moveAngle": math.pi/2,  "speedW":self.speed_w, "actionName":"Rot3rd4RightArc"})
        elif self.move_action == MoveAction.GoRightArc:
            self.status = Navigation.runOdoMove({"rotDegree":180.0,
                                                                      "rotRadius":0.5*self.move_dist,
                                                                      "rotSpeed":self.speed_x,
                                                                      "actionName":"GoRightArc"})
        elif self.move_action == MoveAction.Rot4th4GoBackward:
            self.status = Navigation.runOdoMove({"moveAngle": math.pi/2,  "speedW":-self.speed_w, "actionName":"Rot4th4GoBackward"})
        elif self.move_action == MoveAction.GoBackward2Origin:
            self.status = Navigation.runOdoMove({"moveDist":self.move_dist, "speedX":-self.speed_x,  "actionName":"GoForward2Origin"})

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
        info["locType"] = self.locType
        info["locName"] = self.locName
        log.info(json.dumps(info))

    def Cancel(self):
        print("cancel!!!")
        self.cancel = True

    def Suspend(self):
        Module.setStatus(ScriptStatus.SUSPENDED)
        print("suspend!!!") 

    def Resume(self):
        Module.setStatus(ScriptStatus.RUNNING)
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
            return
        if calib_move.cancel:
            return

if __name__ == '__main__':
    main()
