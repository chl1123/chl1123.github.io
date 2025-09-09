import time
import json
import math
from syspy import Navigation, Logger,Module,ScriptStatus,Motor

log = Logger("linearMotorZeroCalibAction")

"""
####BEGIN DEFAULT ARGS####
{
    "sendHeight": {
        "value": 1.0,
        "tips": "Linear motor actuation height",
        "type": "double",
        "unit":"m/s",
        "maxValue":2.0,
        "minValue":0.0
    }
}
####END DEFAULT ARGS####
"""

class CalibMove:
    def __init__(self):
        self.init = True

    def run(self):
        if self.init:
            self.init = False
            self.cancel = False
            self.status = ScriptStatus.RUNNING
            self.motor_name = Module.get_task_args("name","Motor-005")
            self.height = Module.get_task_args("sendHeight",1.0)
            self.pos = 1.0

        self.pos = Motor.get_motor_pos(self.motor_name)
        Motor.resetMotor(self.motor_name)
        if Motor.setMotorPosition(self.motor_name, self.height, 1.0):
            if math.fabs(self.pos-self.height) < 0.01:
                self.status = ScriptStatus.FINISHED 
            else:
                self.status = ScriptStatus.RUNNING
        else:
            self.status = ScriptStatus.RUNNING

    def print(self):
        # 实时打印
        info = dict()
        info["motor_name"] = self.motor_name
        info["status"] = self.status
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
