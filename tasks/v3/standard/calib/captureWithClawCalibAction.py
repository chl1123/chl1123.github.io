# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("captureWithClawCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "L": {
        "value": 1.5,
        "tips": "Motion range length",
        "type": "double",
        "unit":"m",
        "maxValue":5.0,
        "minValue":1.0
    },
    "angle": {
        "value": 30,
        "tips": "Rotational angular",
        "type": "double",
        "unit":"°",
        "maxValue":90,
        "minValue":10
    },
    "num": {
        "value": 8,
        "tips": "Image capture count",
        "type": "int",
        "unit":"count",
        "maxValue":30,
        "minValue":1
    } ,
    "factor": {
        "value": 0.75,
        "tips": "Coefficient",
        "type": "double",
        "unit":"",
        "maxValue":1.0,
        "minValue":0.0
    },
    "time": {
        "value": 1,
        "tips": "Repeat run count",
        "type": "int",
        "unit":"count",
        "maxValue":10,
        "minValue":1
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
    MoveWait = 0
    Straight = 1
    Back = 2
    TrunRight = 3
    RightArcStraight = 4
    RightArcBack = 5
    TrunLeft = 6
    LeftArcStraight = 7
    LeftArcBack = 8
    TurnToOrigin = 9
    ActionEnd = 10

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.Straight
        self.MoveMaxDist = 1.5
        self.MoveMaxAngle = 30 * math.pi/180
        self.MoveSpeed = 0.3
        self.MoveAngleSpeed = math.pi / 6
        self.CapturePhotoNum = 8

    def run(self):
        # 初始化
        if self.init:
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Straight
            self.cur_num = 0
            self.cur_time = 1
            self.MoveMaxDist = Module.getTaskArgs("L", 1.5)
            self.MoveMaxAngle = float(Module.getTaskArgs("angle",30))* math.pi/180
            self.CapturePhotoNum = int(Module.getTaskArgs("num",8))
            self.time = Module.getTaskArgs("time",1)
            self.MoveSpeed = Module.getTaskArgs("MoveSpeed",0.3)
            self.MoveAngleSpeed = Module.getTaskArgs("MoveAngleSpeed",math.pi / 6)
            self.fileName = Module.getTaskArgs("fileName","")
            self.filePath = Module.getTaskArgs("filePath","")
            self.camName = Module.getTaskArgs("deviceName","Camera-000")
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.Straight:
            self.status = Navigation.runOdoMove({"moveDist": self.MoveMaxDist / self.CapturePhotoNum,  "speedX":self.MoveSpeed, "actionName":"GoStraightForward"})
        elif self.move_action == MoveAction.Back:
            self.status = Navigation.runOdoMove({"moveDist": self.MoveMaxDist,  "speedX":-self.MoveSpeed, "actionName":"GoStraightBackward"})
        elif self.move_action == MoveAction.TrunRight:
            self.status = Navigation.runOdoMove({"moveAngle": self.MoveMaxAngle,  "speedW":-self.MoveAngleSpeed, "actionName":"GoRotBackward"})
        elif self.move_action == MoveAction.RightArcStraight:
            self.status = Navigation.runOdoMove({"rotDegree":2 * math.degrees(self.MoveMaxAngle) / self.CapturePhotoNum ,
                                                                      "rotRadius":(self.MoveMaxDist/2)/math.sin(self.MoveMaxAngle),
                                                                      "rotSpeed":self.MoveSpeed/2,
                                                                      "maxAcc":0.05,
                                                                      "maxDec":0.05,
                                                                      "actionName":"GoLeftArcForward"})
        elif self.move_action == MoveAction.RightArcBack:
            self.status = Navigation.runOdoMove({"rotDegree":2 * math.degrees(self.MoveMaxAngle)  ,
                                                            "rotRadius":(self.MoveMaxDist/2)/math.sin(self.MoveMaxAngle),
                                                            "rotSpeed":-self.MoveSpeed/2,
                                                            "maxAcc":0.05,
                                                            "maxDec":0.05,
                                                            "actionName":"GoLeftArcBackward"})
        elif self.move_action == MoveAction.TrunLeft:
            self.status = Navigation.runOdoMove({"moveAngle": 2 * self.MoveMaxAngle,  "speedW":self.MoveAngleSpeed, "actionName":"GoRotForward"})
        elif self.move_action == MoveAction.LeftArcStraight:
            self.status = Navigation.runOdoMove({"rotDegree":2 * math.degrees(self.MoveMaxAngle) / self.CapturePhotoNum ,
                                                            "rotRadius":-(self.MoveMaxDist/2)/math.sin(self.MoveMaxAngle),
                                                            "rotSpeed":self.MoveSpeed/2,
                                                            "maxAcc":0.05,
                                                            "maxDec":0.05,
                                                            "actionName":"GoRightArcForward"})
        elif self.move_action == MoveAction.LeftArcBack:
            self.status = Navigation.runOdoMove({"rotDegree":2 * math.degrees(self.MoveMaxAngle),
                                                            "rotRadius":-(self.MoveMaxDist/2)/math.sin(self.MoveMaxAngle),
                                                            "rotSpeed":-self.MoveSpeed/2,
                                                            "maxAcc":0.05,
                                                            "maxDec":0.05,
                                                            "actionName":"GoRightArcBackward"})
        elif self.move_action == MoveAction.TurnToOrigin:
            self.status = Navigation.runOdoMove({"moveAngle": self.MoveMaxAngle,  "speedW":-self.MoveAngleSpeed, "actionName":"NoAction"})

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            if (self.move_action == MoveAction.Straight  or self.move_action == MoveAction.RightArcStraight or
                 self.move_action == MoveAction.LeftArcStraight ):

                captrue_status =  Navigation.recordCapture(self.fileName,self.filePath,self.camName)
                #captrue_status = True
                if not captrue_status:
                    self.status = ScriptStatus.RUNNING
                    return ScriptStatus.RUNNING
                
                self.cur_num = self.cur_num + 1
                
                if self.cur_num == self.CapturePhotoNum:
                    self.move_action = self.move_action + 1
                    self.cur_num = 0
            else:
                self.move_action = self.move_action + 1
                self.cur_num = 0
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING

        if self.move_action == MoveAction.ActionEnd and self.cur_time < self.time:
            Navigation.resetOdoMove()
            self.cur_time = self.cur_time + 1
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Straight

        return self.status
    
    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["MoveMaxDist"] = self.MoveMaxDist
        info["MoveMaxAngle"] = self.MoveMaxAngle
        info["MoveSpeed"] = self.MoveSpeed
        info["MoveAngleSpeed"] = self.MoveAngleSpeed
        info["CapturePhotoNum"] = self.CapturePhotoNum
        info["cur_num"] = self.cur_num
        info["fileName"] = self.fileName
        info["filePath"] = self.filePath
        info["camName"] = self.camName
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
