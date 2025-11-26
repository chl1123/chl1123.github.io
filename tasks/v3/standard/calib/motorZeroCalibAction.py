import time
import json
import math
from syspy import Navigation, Logger,Module,ScriptStatus,Motor

log = Logger("motorZeroCalibAction")

class CalibMove:
    def __init__(self):
        self.init = True

    def run(self):
        if self.init:
            self.init = False
            self.cancel = False
            self.status = ScriptStatus.RUNNING
            self.motor_name = Module.getTaskArgs("name","Motor-005")
            self.pos = 1.0
            Motor.resetMotor(self.motor_name)

        self.pos = Motor.getMotorPos(self.motor_name)
        if Motor.setMotorPosition(self.motor_name, 0.0, 10.0):
            if math.fabs(self.pos) < 0.01:
                self.status = ScriptStatus.FINISHED 
            else:
                self.status = ScriptStatus.RUNNING
        else:
            self.status = ScriptStatus.RUNNING
        Motor.resetMotor(self.motor_name)

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
