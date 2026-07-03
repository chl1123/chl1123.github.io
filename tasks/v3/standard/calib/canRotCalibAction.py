# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus,RobotParam

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
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.GoStraightForWard
            self.move_dist = Module.getTaskArgs("L", 2.0)
            self.speed_x = Module.getTaskArgs("V", 0.5)
            self.speed_w = Module.getTaskArgs("W", 30) * math.pi / 180
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
        if self.move_action == MoveAction.GoStraightForWard:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed_x, "actionName":"GoStraightForWard"})
        elif self.move_action == MoveAction.GoStraightBackWard:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":-self.speed_x, "actionName":"GoStraightBackWard"})
        elif self.move_action == MoveAction.GoRotForWard:
            self.status = Navigation.runOdoMove({"moveAngle":  math.pi,  "speedW":self.speed_w, "actionName":"GoRotForWard"})
        elif self.move_action == MoveAction.GoRotBackWard:
            self.status = Navigation.runOdoMove({"moveAngle":  math.pi,  "speedW":-self.speed_w, "actionName":"GoRotBackWard"})
    
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
        info["locType"] = self.locType
        info["locName"] = self.locName
        log.info(json.dumps(info))
        
    def Cancel(self):
        print("cancel!!!")
        self.cancel = True

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
            return
        if calib_move.status == ScriptStatus.FAILED:
            Module.setStatus(ScriptStatus.FAILED)
            return
        if calib_move.cancel:
            return

if __name__ == '__main__':
    main()