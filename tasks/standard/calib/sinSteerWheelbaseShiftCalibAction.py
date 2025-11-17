# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus,Motor

log = Logger("sinSteerWheelbaseShiftCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "rotCount": {
        "value": 3,
        "tips": "Number of in-place rotations",
        "type": "int",
        "unit":"count",
        "maxValue":10,
        "minValue":1
    },
    "W": {
        "value": 30,
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
    ForkUnload1 = 1
    Rot1st = 2
    ForkLoad = 3
    Rot2nd = 4
    ForkUnload2 = 5
    ActionEnd = 6

class CalibMove:

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = ScriptStatus.RUNNING
        self.move_action = MoveAction.ForkUnload1
        self.rotCount = 3
        self.speed_w = 45*math.pi/180

    def run(self):
        # 初始化
        if self.init:
            Navigation.resetOdoMove()
            Module.set_status(ScriptStatus.RUNNING)
            self.init = False
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.ForkUnload1
            self.rotCount = int(Module.get_task_args("rotCount",3))
            self.speed_w = Module.get_task_args("W", 30) * math.pi / 180
            self.wheelBaseMotorName = Module.get_task_args("wheelBaseMotorName", "Motor-002")
            self.wheelBaseMaxHeight = Module.get_task_args("wheelBaseMaxHeight", 0.205)
            self.wheelBaseMinHeight = Module.get_task_args("wheelBaseMinHeight", 0.085)
            self.pos = 0.0
            self.cancel = False

        self.pos = Motor.get_motor_pos(self.wheelBaseMotorName)
        # 实时运行
        if self.move_action == MoveAction.ForkUnload1:
            Motor.setMotorSpeed(self.wheelBaseMotorName, -0.02)
            if math.fabs(self.pos-self.wheelBaseMinHeight) < 0.01:
                self.status = ScriptStatus.FINISHED
            else:
                self.status = ScriptStatus.RUNNING
        elif self.move_action == MoveAction.Rot1st:
            self.status = Navigation.runOdoMove({"moveAngle": self.rotCount * 2 * math.pi,  "speedW":self.speed_w, "actionName":"Rot1st"})
        elif self.move_action == MoveAction.ForkLoad:
            Motor.setMotorSpeed(self.wheelBaseMotorName, 0.02)
            if math.fabs(self.pos-self.wheelBaseMaxHeight) < 0.01:
                self.status = ScriptStatus.FINISHED
            else:
                self.status = ScriptStatus.RUNNING
        elif self.move_action == MoveAction.Rot2nd:
            self.status = Navigation.runOdoMove({"moveAngle": self.rotCount * 2 * math.pi,  "speedW":self.speed_w, "actionName":"Rot2nd"})
        elif self.move_action == MoveAction.ForkUnload2:
            Motor.setMotorSpeed(self.wheelBaseMotorName, -0.02)
            if math.fabs(self.pos-self.wheelBaseMinHeight) < 0.01:
                self.status = ScriptStatus.FINISHED
            else:
                self.status = ScriptStatus.RUNNING

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            if self.move_action == MoveAction.ForkUnload1 or self.move_action == MoveAction.ForkUnload2:
                Navigation.wheelBaseShift(False)
            if self.move_action == MoveAction.ForkLoad:
                Navigation.wheelBaseShift(True)
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                Motor.resetMotor(self.wheelBaseMotorName)
                self.status = ScriptStatus.RUNNING
        return self.status
    
    def print(self):
        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["rotCount"] = self.rotCount
        info["move_action"] = self.move_action
        info["speed_w"] = self.speed_w
        info["wheelBaseMotorName"] = self.wheelBaseMotorName
        info["wheelBaseMaxHeight"] = self.wheelBaseMaxHeight
        info["wheelBaseMinHeight"] = self.wheelBaseMinHeight
        info["pos"] = self.pos
        log.info(json.dumps(info))

    def Cancel(self):
        print("cancel!!!")
        self.cancel = True

def main():
    calib_move = CalibMove()
    Module.init()
    Module.set_cancel_callback(calib_move.Cancel)
    while True:
        calib_move.run()
        calib_move.print()
        time.sleep(0.1)
        if calib_move.status == ScriptStatus.FINISHED:
            Module.set_status(ScriptStatus.FINISHED)
            return
        if calib_move.status == ScriptStatus.FAILED:
            Module.set_status(ScriptStatus.FAILED)
            return
        if calib_move.cancel:
            return

if __name__ == '__main__':
    main()