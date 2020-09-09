import Hairou
import json
import time
from rbk import MoveStatus, BasicModule, normalize_theta
from rbkSim import SimModule
import math
####BEGIN DEFAULT ARGS####
{
    "lift": {
        "value": 0,
        "tips": "pos",
        "type": "double",
        "max_value":1850,
        "min_value":380,
        "unit": "mm"
    },
    "rotate": {
        "value": 0,
        "tips": "theta",
        "type": "double",
        "unit": "rad"
    },    
    "stretch": {
        "value": 0,
        "tips": "pos",
        "type": "double",
        "unit": "mm"
    }, 
    "finger": {
        "value": 0,
        "tips": "1: open, 0: close",
        "max_value":1,
        "min_value":0,
        "type": "double"
    }, 
    "vision_targetType": {
        "value": 0,
        "type": "double"
    },
    "vision_binType": {
        "value": 0,
        "type": "double"
    },
    "chassisLedFront": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "double"
    }, 
    "chassisLedBack": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "double"
    }, 
    "buzzer": {
        "value": 0,
        "tips": "0: off 1: fast_blink 2: slow_blink 3: hold",
        "type": "double"
    }, 
    "headLedRed": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "double"
    }, 
    "headLedYellow": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "double"
    }, 
    "headLedGreen": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "double"
    }, 
    "headLedFreq": {
        "value": 0,
        "tips": "0: off 1: fast_blink 2: slow_blink 3: hold",
        "type": "double"
    }
}
####END DEFAULT ARGS####

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.status = MoveStatus.RUNNING
        self.h = Hairou.Hairou("192.168.192.20",4172)
        self.lift_reach_dist = 0.5
        self.rotate_reach_angle = 0.01
        self.stretch_reach_dist = 0.5
        self.init = True
        self.task = dict()
        self.stretch_status = MoveStatus.FINISHED
        self.lift_status = MoveStatus.FINISHED
        self.rotate_status = MoveStatus.FINISHED
        self.finger_status = MoveStatus.FINISHED
        self.vision_status = MoveStatus.FINISHED
        self.indicator_status = MoveStatus.FINISHED
        if self.h.connect():
            self.h.initDevice()
    def run(self, r:SimModule,args):
        if self.init:
            self.init = False
            self.status = MoveStatus.RUNNING
            self.task = args
        if self.status is not MoveStatus.FINISHED:
            state = self.h.getReport()
            r.setInfo(json.dumps(state))
            if "lift" in self.task:
                self.lift(r,self.task["lift"])
            if "rotate" in self.task:
                self.rotate(r, self.task["rotate"])
            if "stretch" in self.task:
                self.stretch(r, self.task["stretch"])
            if "finger" in self.task:
                self.finger(r,self.task["finger"])
            if "vision_targetType" in self.task and "vision_binType" in self.task:
                self.vision(r, self.task["vision_targetType"], self.task["vision_binType"])

            chassisLedFront, chassisLedBack, buzzer, headLedYellow, headLedRed, headLedGreen, headLedFreq = None, None, None, None, None, None,None
            if "chassisLedFront" in self.task:
                chassisLedFront = self.task["chassisLedFront"]
            if "chassisLedBack" in self.task:
                chassisLedBack = self.task["chassisLedBack"]
            if "buzzer" in self.task:
                buzzer = self.task["buzzer"]
            if "headLedRed" in self.task:
                headLedRed = self.task["headLedRed"]
            if "headLedYellow" in self.task:
                headLedYellow = self.task["headLedYellow"]
            if "headLedGreen" in self.task:
                headLedGreen = self.task["headLedGreen"]
            if "headLedFreq" in self.task:
                headLedFreq = self.task["headLedFreq"]
            if chassisLedFront is not None\
                 or chassisLedBack is not None\
                     or buzzer is not None \
                         or headLedYellow is not None \
                             or headLedRed is not None \
                                 or headLedGreen is not None \
                                     or headLedFreq is not None:
                                     self.indicator(r, chassisLedFront, chassisLedBack, buzzer, headLedYellow, headLedRed, headLedGreen, headLedFreq)
            if self.lift_status == MoveStatus.FAILED or \
                self.rotate_status == MoveStatus.FAILED or \
                    self.stretch_status == MoveStatus.FAILED or \
                        self.finger_status == MoveStatus.FAILED or \
                            self.indicator_status == MoveStatus.FAILED or \
                                self.vision_status == MoveStatus.FAILED:
                                self.status = MoveStatus.FAILED
            elif self.lift_status == MoveStatus.FINISHED and \
                self.rotate_status == MoveStatus.FINISHED and \
                    self.stretch_status == MoveStatus.FINISHED and \
                        self.finger_status == MoveStatus.FINISHED and \
                            self.indicator_status == MoveStatus.FINISHED and \
                                self.vision_status == MoveStatus.FINISHED:
                                self.status = MoveStatus.RUNNING
            else:
                self.status = MoveStatus.RUNNING
        return self.status.value
    def lift(self, r, height):
        self.lift_status = MoveStatus.RUNNING
        state = self.h.getReport()
        if "lift" in state:
            device_state = state["lift"]
            if "position" in device_state:
                if abs(device_state["position"] - height) < self.lift_reach_dist:
                    self.lift_status = MoveStatus.FINISHED
                    return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    (flag, res) = self.h.liftReset()
                    res["flag"] = flag
                    r.setInfo(json.dumps(res))
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    (flag, res) = self.h.liftPos(height)
                    res["flag"] = flag
                    r.setInfo(json.dumps(res))
        return False
    def rotate(self, r, theta):
        self.rotate_status = MoveStatus.RUNNING
        state = self.h.getReport()
        if "rotate" in state:
            device_state = state["rotate"]
            if "position" in device_state:
                if abs(normalize_theta(device_state["position"] - theta)) < self.rotate_reach_angle:
                    self.rotate_status = MoveStatus.FINISHED
                    return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    (flag, res) = self.h.rotateReset()
                    res["flag"] = flag
                    r.setInfo(json.dumps(res))
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    (flag, res) = self.h.rotateAngle(theta)
                    res["flag"] = flag
                    r.setInfo(json.dumps(res))
        return False       
    def stretch(self, r, pos):
        self.stretch_status = MoveStatus.RUNNING
        state = self.h.getReport()
        if "stretch" in state:
            device_state = state["stretch"]
            if "position" in device_state:
                if abs(device_state["position"] - pos) < self.stretch_reach_dist:
                    self.stretch_status = MoveStatus.FINISHED
                    return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    (flag, res)= self.h.stretchReset()
                    res["flag"] = flag
                    r.setInfo(json.dumps(res))
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    (flag, res) = self.h.stretchPos(pos)
                    res["flag"] = flag
                    r.setInfo(json.dumps(res))
        return False    
    def finger(self, r, pos):
        self.finger_status = MoveStatus.RUNNING
        state = self.h.getReport()
        if "finger" in state:
            device_state = state["finger"]
            if "leftStatus" in device_state:
                if abs(device_state["leftStatus"] - pos) < 0.1 and abs(device_state["rightStatus"] - pos) < 0.1:
                    self.finger_status = MoveStatus.FINISHED
                    return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    self.h.fingerReset()
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    self.h.fingerPos(pos)
        return False            
    def vision(self, r, targetType, binType):
        self.vision_status = MoveStatus.RUNNING
        state = self.h.getReport()
        if "vision" in state:
            device_state = state["vision"]
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    self.h.visionReset()
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    flag, res = self.h.visionReq(targetType,binType)
                    if flag:
                        if "positionMatrix" in res:
                            self.vision_status = MoveStatus.FINISHED
                            print("positionMatrix", res["positionMatrix"])
                            return True
                        else:
                            print(res)
                    else:
                        r.logInfo("vision no response")
        return False       
    def indicator(self, r, chassisLedFront = None, chassisLedBack = None, buzzer = None, headLedRed = None, headLedYellow = None, headLedGreen = None, headLedFreq = None):
        (flag, res) = self.h.indicatorReq(chassisLedFront,chassisLedBack,buzzer,headLedRed,headLedYellow,headLedGreen,headLedFreq)
        if not flag:
            r.setInfo(json.dumps(res))
            self.indicator_status = MoveStatus.RUNNING
            return False
        else :
            self.indicator_status = MoveStatus.FINISHED
        return True            
    def cancel(self, r:SimModule):
        r.logInfo("script cancel")
        self.h.disconnect()
        self.status = MoveStatus.NONE

if __name__ == '__main__':
    import rbkSim
    r = rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["headLedFreq"] = dict()
    data["headLedFreq"]["value"] = "1"
    print(m.run(r, data))