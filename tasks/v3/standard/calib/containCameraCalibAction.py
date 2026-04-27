# coding=utf-8
import math
from enum import  IntEnum
import json
import time
from syspy import Logger, ScriptStatus, Navigation, Module, Motor, Do
from standard.module.cartonTransferUnit import ContainerRobot

log = Logger("containCameraCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "tagDistance": {
        "value": 0.0925,
        "tips": "Distance between two tags",
        "type": "double",
        "unit":"m",
        "maxValue":1.0,
        "minValue":0.01
    },
    "tagSize": {
        "value": 0.0615,
        "tips": "Tag size",
        "type": "double",
        "unit":"m",
        "maxValue":1.0,
        "minValue":0.01
    },
    "angle": {
        "value": 50.0,
        "tips": "Angle the container will rotate",
        "type": "double",
        "unit":"deg",
        "maxValue":80.0,
        "minValue":10.0
    },
    "isContorller3000": {
        "value": false,
        "tips": "Whether is SRC3000 contorller?",
        "type": "bool",
        "unit": ""
    }
}
####END DEFAULT ARGS####
"""

class MoveAction(IntEnum):
    Start = 1
    Rotate = 2
    RevRotate = 3
    Reset = 4
    ActionEnd = 5

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.Start
        self.cur_angle = 0.0

    # def Rotate(self, pos):
    #     cur_pos = Motor.getMotorPos(self.motor_name)
    #     info = dict()
    #     info["cur_pos"] = cur_pos
    #     info["pos"] = pos
    #     info["name"] = self.motor_name
    #     log.info(json.dumps(info))
    #     if(abs(cur_pos - pos) < 0.001):
    #         return ScriptStatus.FINISHED
    #     else:
    #         return self.spk.rotate(pos)

    def run(self):
        # 初始化
        if self.init:
            Navigation.resetOdoMove()
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Start
            # self.spk = ContainerRobot()
            self.step_angle = 2.0
            self.cur_angle = self.step_angle
            self.angle = Module.getTaskArgs("angle", 50.0)
            self.motor_name = Module.getTaskArgs("name","Motor-003")
            self.isContorller3000 = Module.getTaskArgs("isContorller3000",False)
            self.cancel = False

        # 实时运行
        self.pos = Motor.getMotorPos(self.motor_name)
        if self.move_action == MoveAction.Start:
            self.cur_angle = 0.0
            if Motor.setMotorPosition(self.motor_name, self.cur_angle/180*math.pi, 10.0):
                if math.fabs(self.pos-self.cur_angle/180*math.pi) < 0.01:
                    self.status = ScriptStatus.FINISHED
                else:
                    self.status = ScriptStatus.RUNNING
            else:
                self.status = ScriptStatus.RUNNING
        elif self.move_action == MoveAction.Rotate:
            if Motor.setMotorPosition(self.motor_name, self.cur_angle/180*math.pi, 10.0):
                if math.fabs(self.pos-self.cur_angle/180*math.pi) < 0.01:
                    self.status = ScriptStatus.FINISHED
                else:
                    self.status = ScriptStatus.RUNNING
            else:
                self.status = ScriptStatus.RUNNING
        elif self.move_action == MoveAction.RevRotate:
            if Motor.setMotorPosition(self.motor_name, -self.cur_angle/180*math.pi, 10.0):
                if math.fabs(self.pos+self.cur_angle/180*math.pi) < 0.01:
                    self.status = ScriptStatus.FINISHED
                else:
                    self.status = ScriptStatus.RUNNING
            else:
                self.status = ScriptStatus.RUNNING
        elif self.move_action == MoveAction.Reset:
            self.cur_angle = 0.0
            if Motor.setMotorPosition(self.motor_name, self.cur_angle/180*math.pi, 10.0):
                if math.fabs(self.pos-self.cur_angle/180*math.pi) < 0.01:
                    self.status = ScriptStatus.FINISHED
                else:
                    self.status = ScriptStatus.RUNNING
            else:
                self.status = ScriptStatus.RUNNING

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            if self.move_action == MoveAction.Start or \
                self.move_action == MoveAction.Rotate or \
                self.move_action == MoveAction.RevRotate:
                if self.isContorller3000:
                    Do.setDo("DO-005", True)
                else:
                    Do.setDo("DO-004", True)
                record_status =  Navigation.calibRecord()
                if not record_status:
                    self.status = ScriptStatus.RUNNING
                    return ScriptStatus.RUNNING
                else:
                    if self.isContorller3000:
                        Do.setDo("DO-005", False)
                    else:
                        Do.setDo("DO-004", True)
                if self.move_action == MoveAction.Rotate or self.move_action == MoveAction.RevRotate:
                    if self.cur_angle < self.angle:
                        self.cur_angle = self.cur_angle + self.step_angle
                        self.status = ScriptStatus.RUNNING
                        return ScriptStatus.RUNNING
                    else:
                        self.cur_angle = self.step_angle
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                Motor.resetMotor(self.motor_name)
                self.status = ScriptStatus.RUNNING

        return self.status

    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["angle"] = self.angle
        info["cur_obj_angle"] = self.cur_angle
        info["cur_real_angle"] = self.pos*180/math.pi
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
        # time.sleep(0.1)
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
