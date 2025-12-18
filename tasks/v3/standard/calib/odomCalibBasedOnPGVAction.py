# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus,CodeScanner

log = Logger("odomCalibBasedOnPGVAction")

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
        "tips": "Clockwise rotation angle",
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
    CalibShortBackward = 0
    CalibShortForward = 1
    InitcallGo2QRCenter = 2
    ShortBackward = 3
    Forward = 4
    Backward = 5
    RotLeftInPlace = 6
    ActionEnd = 7

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.CalibShortBackward
        self.short_move_dist = 0.2
        self.move_dist = 1.0
        self.move_angle = 2 * math.pi
        self.speed_x = 0.1
        self.speed_w = math.pi/6

    def run(self):
        # 初始化
        if self.init:
            self.init = False
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.CalibShortBackward
            self.up_side = Module.getTaskArgs("up_side", False)
            self.short_move_dist = Module.getTaskArgs("distanceBack", 0.2)
            self.move_dist = Module.getTaskArgs("distanceForward", 1.0)
            self.move_angle = Module.getTaskArgs("angleForward", 360)*math.pi/180
            self.speed_x = Module.getTaskArgs("V", 0.1)
            self.speed_w = Module.getTaskArgs("W", 30) * math.pi / 180
            Navigation.resetGoPGV()
            self.cancel = False
            self.pgv_datas = [] # 保存PGV数据用于标定
            self.has_cp_yaw = False
            self.cp_yaw = 0.0

        # 实时运行
        if self.move_action == MoveAction.CalibShortBackward:
            self.status = Navigation.runOdoMove({"moveDist": 0.05,  "speedX":-self.speed_x, "actionName":"short_move_dist"})
        elif self.move_action == MoveAction.CalibShortForward:
            self.status = Navigation.runOdoMove({"moveDist": 0.05,  "speedX":self.speed_x, "actionName":"short_move_dist"})
            pgv_data = CodeScanner.getCodeScanners()
            for pgv in pgv_data:
                if pgv.isDMTDetected and pgv.codeScannerInfo.isUpside == False:
                    self.pgv_datas.append(pgv)
        elif self.move_action == MoveAction.InitcallGo2QRCenter:
            if not self.has_cp_yaw:
                self.has_cp_yaw = True
                self.calCpYaw()
            self.status = Navigation.goPGVRun({"R2ADP":True, "actionName":"callGo2QRCenter", "pgvReachDist":0.01, "pgvCpYaw":self.cp_yaw})
        elif self.move_action == MoveAction.ShortBackward:
            self.status = Navigation.runOdoMove({"moveDist": self.short_move_dist,  "speedX":-self.speed_x, "actionName":"short_move_dist"})
        elif self.move_action == MoveAction.Forward:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist,  "speedX":self.speed_x, "actionName":"Forward"})
        elif self.move_action == MoveAction.Backward:
            self.status = Navigation.runOdoMove({"moveDist": self.move_dist - self.short_move_dist,  "speedX":-self.speed_x, "actionName":"Backward"})
        elif self.move_action == MoveAction.RotLeftInPlace:
            self.status = Navigation.runOdoMove({"moveAngle": self.move_angle,  "speedW":self.speed_w, "actionName":"RotLeftInPlace"})
        
        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
            if self.move_action == MoveAction.InitcallGo2QRCenter:
                Navigation.resetGoPGV()
                self.status = ScriptStatus.RUNNING
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING

        return self.status
    
    def calCpYaw(self): # yaw = -atan2(y1 - y2, x1 - x2);
        if len(self.pgv_datas) < 5:
            log.info("pgv data loss")
        else:
            y1 = self.pgv_datas[0].tagDiffY
            y2 = self.pgv_datas[-1].tagDiffY
            x1 = self.pgv_datas[0].tagDiffX
            x2 = self.pgv_datas[-1].tagDiffX
            self.cp_yaw = -math.atan2(y1-y2, x1-x2)

    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["move_dist"] = self.move_dist
        info["speed_x"] = self.speed_x
        info["speed_w"] = self.speed_w
        info["cp_yaw"] = self.cp_yaw
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
