# -*- coding: utf-8 -*-
import time
from syspy import Logger,Module,ScriptStatus

log = Logger("noAction")

class CalibMove:
    def __init__(self):
        self.cancel = False

    def cancel(self):
        print("cancel!!!")
        self.cancel = True
    

def main():
    calib_move = CalibMove()
    Module.init()
    Module.set_cancel_callback(calib_move.cancel)
    while True:
        time.sleep(0.1)
        print("run noAction.py")
        if calib_move.cancel:
            return

if __name__ == '__main__':
    main()