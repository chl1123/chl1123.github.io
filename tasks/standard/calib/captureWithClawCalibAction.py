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
        "tips": "长度",
        "type": "double",
        "unit":"m",
        "maxValue":5.0,
        "minValue":1.0
    },
    "angle": {
        "value": 30,
        "tips": "角度",
        "type": "double",
        "unit":"°",
        "maxValue":90,
        "minValue":10
    },
    "num": {
        "value": 8,
        "tips": "个数",
        "type": "int",
        "unit":"count",
        "maxValue":30,
        "minValue":1
    } ,
    "factor": {
        "value": 0.75,
        "tips": "系数",
        "type": "double",
        "unit":"",
        "maxValue":1.0,
        "minValue":0.0
    },
    "time": {
        "value": 1,
        "tips": "次数",
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
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Straight
            self.cur_num = 0
            self.cur_time = 1
            self.MoveMaxDist = Module.get_task_args("L", 1.5)
            self.MoveMaxAngle = float(Module.get_task_args("angle",30))* math.pi/180
            self.CapturePhotoNum = int(Module.get_task_args("num",8))
            self.time = Module.get_task_args("time",1)
            self.MoveSpeed = Module.get_task_args("MoveSpeed",0.3)
            self.MoveAngleSpeed = Module.get_task_args("MoveAngleSpeed",math.pi / 6)
            self.fileName = Module.get_task_args("fileName","")
            self.filePath = Module.get_task_args("filePath","")
            self.camName = Module.get_task_args("deviceName","Camera-000")
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.Straight:
            self.status = Navigation.runOdoMove({"move_dist": self.MoveMaxDist / self.CapturePhotoNum,  "speed_x":self.MoveSpeed, "action_name":"GoStraightForward"})
        elif self.move_action == MoveAction.Back:
            self.status = Navigation.runOdoMove({"move_dist": self.MoveMaxDist,  "speed_x":-self.MoveSpeed, "action_name":"GoStraightBackward"})
        elif self.move_action == MoveAction.TrunRight:
            self.status = Navigation.runOdoMove({"move_angle": self.MoveMaxAngle,  "speed_w":-self.MoveAngleSpeed, "action_name":"GoRotBackward"})
        elif self.move_action == MoveAction.RightArcStraight:
            self.status = Navigation.runOdoMove({"rot_degree":2 * math.degrees(self.MoveMaxAngle) / self.CapturePhotoNum ,
                                                                      "rot_radius":(self.MoveMaxDist/2)/math.sin(self.MoveMaxAngle),
                                                                      "rot_speed":self.MoveSpeed/2,
                                                                      "maxAcc":0.05,
                                                                      "maxDec":0.05,
                                                                      "action_name":"GoLeftArcForward"})
        elif self.move_action == MoveAction.RightArcBack:
            self.status = Navigation.runOdoMove({"rot_degree":2 * math.degrees(self.MoveMaxAngle)  ,
                                                            "rot_radius":(self.MoveMaxDist/2)/math.sin(self.MoveMaxAngle),
                                                            "rot_speed":-self.MoveSpeed/2,
                                                            "maxAcc":0.05,
                                                            "maxDec":0.05,
                                                            "action_name":"GoLeftArcBackward"})
        elif self.move_action == MoveAction.TrunLeft:
            self.status = Navigation.runOdoMove({"move_angle": 2 * self.MoveMaxAngle,  "speed_w":self.MoveAngleSpeed, "action_name":"GoRotForward"})
        elif self.move_action == MoveAction.LeftArcStraight:
            self.status = Navigation.runOdoMove({"rot_degree":2 * math.degrees(self.MoveMaxAngle) / self.CapturePhotoNum ,
                                                            "rot_radius":-(self.MoveMaxDist/2)/math.sin(self.MoveMaxAngle),
                                                            "rot_speed":self.MoveSpeed/2,
                                                            "maxAcc":0.05,
                                                            "maxDec":0.05,
                                                            "action_name":"GoRightArcForward"})
        elif self.move_action == MoveAction.LeftArcBack:
            self.status = Navigation.runOdoMove({"rot_degree":2 * math.degrees(self.MoveMaxAngle),
                                                            "rot_radius":-(self.MoveMaxDist/2)/math.sin(self.MoveMaxAngle),
                                                            "rot_speed":-self.MoveSpeed/2,
                                                            "maxAcc":0.05,
                                                            "maxDec":0.05,
                                                            "action_name":"GoRightArcBackward"})
        elif self.move_action == MoveAction.TurnToOrigin:
            self.status = Navigation.runOdoMove({"move_angle": self.MoveMaxAngle,  "speed_w":-self.MoveAngleSpeed, "action_name":"NoAction"})

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

    def cancel(self):
        print("cancel!!!")
        self.cancel = True

def main():
    calib_move = CalibMove()
    Module.init()
    Module.set_cancel_callback(calib_move.cancel)
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
