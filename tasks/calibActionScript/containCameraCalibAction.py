# coding=utf-8
import sys
import math
from enum import  IntEnum
import json
from containerRobot import Module as ContainerRobotModule
sys.path.append("syspy")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule
from syspy.robot import ModuleTool

"""
####BEGIN DEFAULT ARGS####
{
    "tagDistance": {
        "value": 0.05,
        "tips": "The distance between the centers of two tag",
        "type": "double",
        "unit": "m"
    },
    "tagSize": {
        "value": 0.1,
        "tips": "Tag size",
        "type": "double",
        "unit": "m"
    },
    "angle": {
        "value": 50.0,
        "tips": "Container will rotate this angle",
        "type": "double",
        "unit": "deg"
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

class Module(BasicModule):

    def __init__(self, r: SimModule, args):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.status = MoveStatus.RUNNING
        self.move_action = MoveAction.Start
        self.cur_angle = 0.0
        
    def Rotate(self, r, pos):
        cur_pos = ModuleTool.get_motor_pos(r, "rotate")
        info = dict()
        info["cur_pos"] = cur_pos
        info["pos"] = pos
        r.setInfo(json.dumps(info))
        r.logDebug("Rotate][{}|{}".format(cur_pos,pos))
        if(abs(cur_pos - pos) < 0.001):
            return MoveStatus.FINISHED
        else:
            return self.spk.rotate(r, pos)

    def run(self, r: SimModule, args):
        # 初始化
        if self.init:
            r.resetOdoMove()
            self.init = False
            self.status = MoveStatus.RUNNING
            self.move_action = MoveAction.Start
            self.spk = ContainerRobotModule(r, args)
            self.step_angle = 2.0
            self.cur_angle = self.step_angle
            if type(args) is dict and "angle" in args:
                self.angle = float(args["angle"])
            else:
                self.angle = 50.0

        # 实时运行
        if self.move_action == MoveAction.Start:
            if self.Rotate(r, pos=0.0):
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING
        elif self.move_action == MoveAction.Rotate:
            if self.Rotate(r, pos=self.cur_angle/180*math.pi):
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING
        elif self.move_action == MoveAction.RevRotate:
            if self.Rotate(r, pos=-self.cur_angle/180*math.pi):
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING
        elif self.move_action == MoveAction.Reset:
            if self.Rotate(r, pos=0.0):
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING

        # 实时打印
        info = dict()
        info["move_action"] = self.move_action
        info["status"] = self.status
        info["angle"] = self.angle
        info["cur_angle"] = self.cur_angle

        r.setInfo(json.dumps(info))
        r.logDebug("containCameraCalibAction][{}|{}|{}|{}".format(
                    self.move_action,
                    self.status,
                    self.angle,
                    self.cur_angle))

        # 当前任务完成时改变状态
        if self.status == MoveStatus.FINISHED:
            if self.move_action == MoveAction.Start or \
                self.move_action == MoveAction.Rotate or \
                self.move_action == MoveAction.RevRotate:
                r.setDO(4, True)
                record_status =  r.calibRecordService()
                if not record_status:
                    return MoveStatus.RUNNING
                else:
                    r.setDO(4, False)
                if self.move_action == MoveAction.Rotate or self.move_action == MoveAction.RevRotate:
                    if self.cur_angle < self.angle:
                        self.cur_angle = self.cur_angle + self.step_angle
                        return MoveStatus.RUNNING
                    else:
                        self.cur_angle = self.step_angle
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                r.resetOdoMove()
                self.status = MoveStatus.RUNNING

        return self.status

if __name__ == '__main__':
    r = SimModule()
    m = Module(r, None)
    args = dict()
    print(m.run(r, args))