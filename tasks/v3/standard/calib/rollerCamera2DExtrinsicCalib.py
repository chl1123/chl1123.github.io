# coding=utf-8
import math
from enum import  IntEnum
import json
import time
from syspy import Logger, ScriptStatus, Navigation, Module

log = Logger("RollerCamera2DExtrinsicCalib")

"""
####BEGIN DEFAULT ARGS####
{
    "x": {
        "value": -1.0,
        "tips": "X",
        "type": "double",
        "unit":"m",
        "maxValue":3.0,
        "minValue":-3.0
    },
    "y": {
        "value": 0.0,
        "tips": "Y",
        "type": "double",
        "unit":"m",
        "maxValue":3.0,
        "minValue":-3.0
    },
    "z": {
        "value": 0.3,
        "tips": "Z",
        "type": "double",
        "unit":"m",
        "maxValue":3.0,
        "minValue":-3.0
    },
    "roll": {
        "value": 0.0,
        "tips": "Roll",
        "type": "double",
        "unit":"deg",
        "maxValue":180.0,
        "minValue":-180.0
    },
    "pitch": {
        "value": 0.0,
        "tips": "Pitch",
        "type": "double",
        "unit":"deg",
        "maxValue":180.0,
        "minValue":-180.0
    },
    "yaw": {
        "value": -90.0,
        "tips": "Yaw",
        "type": "double",
        "unit":"deg",
        "maxValue":180.0,
        "minValue":-180.0
    },
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
    }
}
####END DEFAULT ARGS####
"""

class CalibMove:
    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        self.init = True

    def run(self):
        # 初始化
        if self.init:
            Module.setStatus(ScriptStatus.RUNNING)
            Navigation.resetOdoMove()
            self.init = False
            self.cancel = False
            self.status = ScriptStatus.RUNNING

        record_status =  Navigation.calibRecord()
        if not record_status:
            self.status  = ScriptStatus.RUNNING
        else:
            self.status = ScriptStatus.FINISHED
        return self.status
    
    def print(self):
        # 实时打印
        info = dict()
        info["info"] = "RollerCamera2DExtrinsicCalib is running..."
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