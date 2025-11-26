# coding=utf-8
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("auxSensorCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "L": {
        "value": 0.2,
        "tips": "Motion range length",
        "type": "double",
        "unit":"m",
        "maxValue":10.0,
        "minValue":0.01
    },
    "V": {
        "value": 0.1,
        "tips": "Motion Speed",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.01
    }
}
####END DEFAULT ARGS####
"""

class MoveAction(IntEnum):
    Back1 = 1
    Back2 = 2
    Straight = 3
    NullAction = 4
    ActionEnd = 5

class CalibMove:
    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.Back1
        self.move_dist = 0.2
        self.speed_x = 0.1

    def run(self):
        # 初始化
        if self.init:
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Back1
            self.move_dist = Module.getTaskArgs("L", 0.2)
            self.speed_x = Module.getTaskArgs("V", 0.1)
            self.cancel = False
            self.calibType = Module.getTaskArgs("calibType", "")
            # self.deviceName = Module.getTaskArgs("deviceNameList", "")
            # if self.deviceName != "":
            #     if self.calibType == "CameraMid360RPZExtrinsicCalib" or self.calibType == "CameraLocMid360RPZExtrinsicCalib":
            #         Camera.addDisableDepthStrName(self.deviceName)

        # 实时运行
        if self.move_action == MoveAction.Back1:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist*0.5,  "speedX":-self.speed_x, "actionName":""})
        elif self.move_action == MoveAction.Back2:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist*0.5,  "speedX":-self.speed_x, "actionName":""})
        elif self.move_action == MoveAction.Straight:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed_x, "actionName":""})
        elif self.move_action == MoveAction.NullAction:
            self.status = ScriptStatus.FINISHED

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            record_status =  Navigation.calibRecord()
            if not record_status:
                self.status = ScriptStatus.RUNNING
                return self.status
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING
            # if self.status == ScriptStatus.FINISHED and self.deviceName != "":
            #     Camera.clearDisableDepthStrName()

        return self.status

    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["move_dist"] = self.move_dist
        info["speed_x"] = self.speed_x
        info["calibType"] = self.calibType
        # info["deviceName"] = self.deviceName
        log.info(json.dumps(info))

    def Cancel(self):
        print("cancel!!!")
        self.cancel = True
        # if self.deviceName != "":
        #     Camera.clearDisableDepthStrName()

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