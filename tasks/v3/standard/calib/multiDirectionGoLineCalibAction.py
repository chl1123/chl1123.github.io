# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus,RobotParam

log = Logger("multiDirectionGoLineCalibAction")

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
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Forward
            self.move_dist = Module.getTaskArgs("L", 2.0)
            self.speed = Module.getTaskArgs("V", 0.5)
            self.move_num = Module.getTaskArgs("move_num", 4)
            self.move_n = 0
            self.move_dir = self.move_n * math.pi / self.move_num
            self.speed_x = self.speed * math.cos(self.move_dir)
            self.speed_y = self.speed * math.sin(self.move_dir)
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
        if self.move_action == 0:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed_x, "speedY":self.speed_y, "actionName":"GoStraightForward"+str(self.move_n)})
        elif self.move_action == 1:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":-self.speed_x, "speedY":-self.speed_y, "actionName":"GoStraightBackward"+str(self.move_n)})
        
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