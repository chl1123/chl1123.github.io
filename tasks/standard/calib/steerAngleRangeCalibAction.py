# -*- coding: utf-8 -*-
import math
import time
from enum import Enum, IntEnum
import json
from syspy import Navigation, Logger,Module,ScriptStatus,Motor

log = Logger("steerAngleRangeCalibAction")

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

class SteerDir(IntEnum):
    MoveWait = 0
    CounterClockWise = 1
    ClockWise = 2
    MoveCenter = 3

class CalibMove:

    def __init__(self):

        super().__init__()
        self.reset()

    def reset(self):
        self.init = True
        self.steer_name = ""
        self.steer_dir = SteerDir.MoveWait
        self.last_send_angle = 0
        self.send_angle = 0
        self.steer_start_time = 0
        self.status = ScriptStatus.RUNNING
        self.cur_angle = 0.0
        self.dt = 0.0
        self.d_steer = 0.0

    def reachLimit(self, dt = 3.0):
        if abs(self.last_send_angle - self.send_angle) < 0.001:
            if time.time() - self.steer_start_time > dt:
                return True
        else:
            self.steer_start_time = time.time()
        return False
    
    def run(self):
        if self.init:
            self.init = False
            Module.set_status(ScriptStatus.RUNNING)
            self.last_motor_angle = 0.0
            self.steer_name = Module.get_task_args("name","Motor-001")
            self.steer_max_angle = Module.get_task_args("max_angle",90.0)
            self.steer_min_angle = Module.get_task_args("min_angle",-90.0)
            self.steer_offset = Module.get_task_args("offset",0.0)
            self.chassis_mode = Module.get_task_args("chassis_mode","")
            self.cancel = False
            self.center_angle = self.steer_offset + 0.5*(self.steer_max_angle + self.steer_min_angle)

        if self.steer_name == "":
            log.info("steer name emtpy!")
            return ScriptStatus.FINISHED
        self.cur_angle = Motor.get_motor_pos(self.steer_name)

        if self.steer_dir == SteerDir.MoveWait:
            self.send_angle = self.center_angle*math.pi/180
            if self.reachLimit():
                self.steer_dir = SteerDir.CounterClockWise

        if self.steer_dir == SteerDir.CounterClockWise:
            self.send_angle = self.cur_angle + 0.1  
            # if self.chassis_mode == "dualDiff":
            self.send_angle = min(self.send_angle, (self.center_angle+150.0)*math.pi/180)
            if self.reachLimit():
                self.steer_dir = SteerDir.ClockWise

        if self.steer_dir == SteerDir.ClockWise:
            self.send_angle = self.cur_angle - 0.1  
            # if self.chassis_mode == "dualDiff":
            self.send_angle = max(self.send_angle, (self.center_angle-150.0)*math.pi/180)
            if self.reachLimit():
                self.steer_dir = SteerDir.MoveCenter

        if self.steer_dir == SteerDir.MoveCenter:
                self.send_angle = self.center_angle*math.pi/180
                if abs(self.last_motor_angle-self.cur_angle) < 0.001:
                    if self.reachLimit(3.0):
                        self.status = ScriptStatus.FINISHED
                else:
                    self.steer_start_time = time.time()

        if self.steer_dir == SteerDir.CounterClockWise:
            Navigation.setSteerAngle(self.steer_name, self.send_angle,"SteerLeft")
        elif self.steer_dir == SteerDir.ClockWise:
            Navigation.setSteerAngle(self.steer_name, self.send_angle,"SteerRight")
        else:
            Navigation.setSteerAngle(self.steer_name, self.send_angle,"")

        self.dt =  time.time() - self.steer_start_time
        self.d_steer = self.last_motor_angle-self.cur_angle
        self.last_send_angle = self.send_angle
        self.last_motor_angle = self.cur_angle
        return self.status

    def print(self):
        info = dict()
        info["steer_dir"] = self.steer_dir
        info["send_angle"] = self.send_angle
        info["last_send_angle"] = self.last_send_angle
        info["cur_angle"] = self.cur_angle
        info["da"] = abs(self.last_send_angle - self.send_angle)
        info["dt"] = self.dt
        info["reachLimit"] = self.reachLimit()
        info["steer_name"] = self.steer_name
        info["d_steer"] = self.d_steer
        info["center_angle"] = self.center_angle
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
