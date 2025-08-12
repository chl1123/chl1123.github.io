# -*- coding: utf-8 -*-
import math
from enum import Enum, IntEnum
import json
import time
from syspy import Navigation, Logger,Module,ScriptStatus

log = Logger("hybridOmniThetaCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "L": {
        "value": 2.0,
        "tips": "长度",
        "type": "double",
        "unit":"m",
        "maxValue":5.0,
        "minValue":1.0
    },
    "V": {
        "value": 0.3,
        "tips": "速度",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.1
    },
    "W": {
        "value": 45,
        "tips": "角速度",
        "type": "double",
        "unit":"°/s",
        "maxValue":90,
        "minValue":10
    }
}
####END DEFAULT ARGS####
"""

class MoveAction(IntEnum):
    Forward = 0
    Backward = 1
    GoLeftArc = 2
    Rot2nd4GoForward = 3
    GoForward2Origin = 4
    Rot3rd4RightArc = 5
    GoRightArc = 6
    Rot4th4GoBackward = 7
    GoBackward2Origin = 8
    GoRot2Origin = 9
    ActionEnd = 10

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
            Module.set_status(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.status = ScriptStatus.RUNNING
            self.move_action = MoveAction.Forward
            self.move_dist = Module.get_task_args("L", 2.0)
            self.speed = Module.get_task_args("V", 0.3)
            self.speed_w = Module.get_task_args("W", 45)*math.pi/180
            self.move_num = Module.get_task_args("move_num", 1)
            self.move_n = 0
            self.move_dir = self.move_n * math.pi / self.move_num
            self.speed_x = self.speed * math.cos(self.move_dir)
            self.speed_y = self.speed * math.sin(self.move_dir)
            self.cancel = False

        # 实时运行
        if self.move_action == MoveAction.Forward:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":self.speed_x, "speed_y":self.speed_y, "action_name":"OmniMove"})
        elif self.move_action == MoveAction.Backward:
            self.status = Navigation.runOdoMove({"move_dist": self.move_dist,  "speed_x":-self.speed_x, "speed_y":-self.speed_y, "action_name":"OmniMove"})
        elif self.move_action == MoveAction.GoLeftArc:
            self.status = Navigation.runOdoMove({"rot_degree":180.0,
                                                                      "rot_radius":0.5*self.move_dist,
                                                                      "rot_speed":self.speed,
                                                                      "action_name":"ThetaMove"})
        elif self.move_action == MoveAction.Rot2nd4GoForward:
            self.status = Navigation.runOdoMove({"move_angle": math.pi/2,  "speed_w":self.speed_w, "action_name":"ThetaMove"})
        elif self.move_action == MoveAction.GoForward2Origin:
            self.status = Navigation.runOdoMove({"move_dist":self.move_dist, "speed_x":self.speed,  "action_name":"ThetaMove"})
        elif self.move_action == MoveAction.Rot3rd4RightArc:
            self.status = Navigation.runOdoMove({"move_angle": math.pi/2,  "speed_w":-self.speed_w, "action_name":"ThetaMove"})
        elif self.move_action == MoveAction.GoRightArc:
            self.status = Navigation.runOdoMove({"rot_degree":180.0,
                                                                      "rot_radius":-0.5*self.move_dist,
                                                                      "rot_speed":self.speed,
                                                                      "action_name":"ThetaMove"})
        elif self.move_action == MoveAction.Rot4th4GoBackward:
            self.status = Navigation.runOdoMove({"move_angle": math.pi/2,  "speed_w":self.speed_w, "action_name":"ThetaMove"})
        elif self.move_action == MoveAction.GoBackward2Origin:
            self.status = Navigation.runOdoMove({"move_dist":self.move_dist, "speed_x":-self.speed,  "action_name":"ThetaMove"})
        elif self.move_action == MoveAction.GoRot2Origin:
            self.status = Navigation.runOdoMove({"move_angle": math.pi/2,  "speed_w":-self.speed_w, "action_name":"ThetaMove"})

        # 当前任务完成时改变状态
        if self.status == ScriptStatus.FINISHED:
            self.move_action = self.move_action + 1
            if self.move_action != MoveAction.ActionEnd:
                Navigation.resetOdoMove()
                self.status = ScriptStatus.RUNNING
            if self.move_action ==  MoveAction.GoLeftArc and self.move_n + 1 < self.move_num:
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
        if calib_move.cancel:
            return

if __name__ == '__main__':
    main()