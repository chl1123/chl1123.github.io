import Hairou
import json
import time
from rbk import MoveStatus, BasicModule, normalize_theta
from rbkSim import SimModule
import math
import goPath
####BEGIN DEFAULT ARGS####
{
    "lift": {
        "value": 0,
        "tips": "pos",
        "type": "int",
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
        "type": "int",
        "unit": "mm"
    }, 
    "finger": {
        "value": 0,
        "tips": "1: open, 0: close",
        "max_value":1,
        "min_value":0,
        "type": "int"
    }, 
    "visionType": {
        "value": "shelf",
		"default_value":[
        "shelf","box"
        ],
        "tips": "tips",
        "type": "complex"
    },
    "chassisLedFront": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "int"
    }, 
    "chassisLedBack": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "int"
    }, 
    "buzzer": {
        "value": 0,
        "tips": "0: off 1: fast_blink 2: slow_blink 3: hold",
        "type": "int"
    }, 
    "headLedRed": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "int"
    }, 
    "headLedYellow": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "int"
    }, 
    "headLedGreen": {
        "value": 0,
        "tips": "1: open, 0: close",
        "type": "int"
    }, 
    "headLedFreq": {
        "value": 0,
        "tips": "0: off 1: fast_blink 2: slow_blink 3: hold",
        "type": "int"
    },
    "operation":{
        "value": "wait",
		"default_value":[
        "load","unload","change","zero","wait"
        ],
        "tips": "tips",
        "type": "complex"        
    },
    "selfPosition":{
        "value": 0,
        "tips": "pos",
        "type": "int",
        "max_value":3,
        "min_value":0       
    },
    "changePosition0":{
        "value": 0,
        "tips": "pos",
        "type": "int",
        "max_value":2,
        "min_value":0       
    },
    "changePosition1":{
        "value": 0,
        "tips": "pos",
        "type": "int",
        "max_value":2,
        "min_value":0       
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
        self.goodsPosFromId = dict({0:390, 1:840, 2:1290})
        self.stretch_status = MoveStatus.NONE
        self.lift_status = MoveStatus.NONE
        self.rotate_status = MoveStatus.NONE
        self.finger_status = MoveStatus.NONE
        self.vision_status = MoveStatus.NONE
        self.indicator_status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.preGoods_status = MoveStatus.NONE
        self.getGoods_status = MoveStatus.NONE
        self.getGoods_step1_status = MoveStatus.NONE
        self.getGoods_step2_status = MoveStatus.NONE
        self.prePutGoods_status = MoveStatus.NONE
        self.putGoods_status = MoveStatus.NONE
        self.putGoods_step1_status = MoveStatus.NONE
        self.putGoods_step2_status = MoveStatus.NONE
        self.rec_status = MoveStatus.NONE
        self.state = dict()
        self.goPath = goPath.Module(r, args)
        self.stretchDist = 740
        if self.h.connect():
            self.h.initDevice()
    def run(self, r:SimModule,args):
        if self.init:
            self.init = False
            self.status = MoveStatus.RUNNING
            self.task = args
        if self.status is not MoveStatus.FINISHED:
            self.state = self.h.getReport()
            self.state["task"] = self.task
            if "operation" in self.task and self.task["operation"] == "load":
                if "lift" in self.task and "rotate" in self.task and "stretch" in self.task and "selfPosition" in self.task:
                    if "rec" not in self.task:
                        self.rec_status = MoveStatus.FINISHED
                        self.vision_status = MoveStatus.FINISHED
                    self.load(r)
                else:
                    r.setError("task is wrong : {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED
            elif "operation" in self.task and self.task["operation"] == "unload":
                if "lift" in self.task and "rotate" in self.task and "stretch" in self.task and "selfPosition" in self.task:
                    if "rec" not in self.task:
                        self.rec_status = MoveStatus.FINISHED
                        self.vision_status = MoveStatus.FINISHED
                    self.unload(r)
                else:
                    r.setError("task is wrong : {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED
            elif "operation" in self.task and self.task["operation"] == "change":
                if "changePosition0" in self.task and "changePosition1" in self.task:
                    self.rec_status = MoveStatus.FINISHED
                    self.vision_status = MoveStatus.FINISHED
                    self.changePos(r)
                else:
                    r.setError("task is wrong : {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED  
            elif "operation" in self.task and self.task["operation"] == "zero":
                self.rec_status = MoveStatus.FINISHED
                self.vision_status = MoveStatus.FINISHED
                self.zero(r)
            else:
                self.operation_status = MoveStatus.FINISHED
                if "lift" in self.task:
                    self.lift(r,self.task["lift"])
                else:
                    self.lift_status = MoveStatus.FINISHED
                if "rotate" in self.task:
                    self.rotate(r, self.task["rotate"])
                else:
                    self.rotate_status = MoveStatus.FINISHED
                if "stretch" in self.task:
                    self.stretch(r, self.task["stretch"])
                else:
                    self.stretch_status = MoveStatus.FINISHED
                if "finger" in self.task:
                    self.finger(r,self.task["finger"])
                else:
                    self.finger_status = MoveStatus.FINISHED
                if "visionType" in self.task:
                    self.vision(r, self.task["visionType"])
                else:
                    self.vision_status = MoveStatus.FINISHED

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
            else:
                self.indicator_status = MoveStatus.FINISHED
            if self.lift_status == MoveStatus.FAILED or \
                self.rotate_status == MoveStatus.FAILED or \
                    self.stretch_status == MoveStatus.FAILED or \
                        self.finger_status == MoveStatus.FAILED or \
                            self.indicator_status == MoveStatus.FAILED or \
                                self.vision_status == MoveStatus.FAILED or \
                                    self.operation_status == MoveStatus.FAILED:
                                    self.status = MoveStatus.FAILED
            elif self.lift_status == MoveStatus.FINISHED and \
                self.rotate_status == MoveStatus.FINISHED and \
                    self.stretch_status == MoveStatus.FINISHED and \
                        self.finger_status == MoveStatus.FINISHED and \
                            self.indicator_status == MoveStatus.FINISHED and \
                                self.vision_status == MoveStatus.FINISHED and \
                                    self.operation_status == MoveStatus.FINISHED:
                                    self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING
        movestate = dict()
        movestate["lift"] = self.lift_status
        movestate["rotate"] = self.rotate_status
        movestate["stretch"] = self.stretch_status
        movestate["finger"] = self.finger_status
        movestate["indicator"] = self.indicator_status
        movestate["vision"] = self.vision_status
        movestate["operation"] = self.operation_status
        movestate["status"] = self.status
        self.state["MoveStatus"] = movestate
        r.setInfo(json.dumps(self.state))
        return self.status.value
    def lift(self, r, height):
        self.lift_status = MoveStatus.RUNNING
        if "lift" in self.state:
            device_state = self.state["lift"]
            if "position" in device_state and "state" in device_state:
                if abs(device_state["position"] - height) < self.lift_reach_dist  and device_state["state"] != Hairou.ModuleState.ERROR:
                    self.lift_status = MoveStatus.FINISHED
                    return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.liftReset()
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.liftPos(height)
                    self.state["res"] = res
        return False
    def rotate(self, r, theta):
        self.rotate_status = MoveStatus.RUNNING
        if "rotate" in self.state:
            device_state = self.state["rotate"]
            if "position" in device_state and "state" in device_state:
                if abs(normalize_theta(device_state["position"] - theta)) < self.rotate_reach_angle \
                    and device_state["state"] != Hairou.ModuleState.ERROR and device_state["state"] != Hairou.ModuleState.RESET:
                    self.rotate_status = MoveStatus.FINISHED
                    return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.rotateReset()
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.rotateAngle(theta)
                    self.state["res"] = res
        return False       
    def stretch(self, r, pos):
        self.stretch_status = MoveStatus.RUNNING
        if "stretch" in self.state:
            device_state = self.state["stretch"]
            if "position" in device_state and "state" in device_state:
                if abs(device_state["position"] - pos) < self.stretch_reach_dist and device_state["state"] != Hairou.ModuleState.ERROR:
                    self.stretch_status = MoveStatus.FINISHED
                    return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.stretchReset()
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.stretchPos(pos)
                    self.state["res"] = res
        return False    
    def finger(self, r, pos):
        self.finger_status = MoveStatus.RUNNING
        if "finger" in self.state:
            device_state = self.state["finger"]
            if "leftStatus" in device_state and "state" in device_state and device_state["state"] != Hairou.ModuleState.ERROR:
                if abs(pos - 1) < 0.1 and abs(device_state["leftStatus"] + 1) < 0.1 and abs(device_state["rightStatus"] + 1) < 0.1:
                    self.finger_status = MoveStatus.FINISHED
                    return True
                elif abs(pos) < 0.1 and abs(device_state["leftStatus"] - 1) < 0.1 and abs(device_state["rightStatus"] - 1) < 0.1:
                    self.finger_status = MoveStatus.FINISHED
                    return True                    
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.fingerReset()
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.fingerPos(pos)
                    self.state["res"] = res
        return False            
    def vision(self, r, vtype):
        if self.vision_status is not MoveStatus.FINISHED:
            self.vision_status = MoveStatus.RUNNING
            if "vision" in self.state:
                device_state = self.state["vision"]
                if "state" in device_state:
                    if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                        self.h.visionReset()
                    elif device_state["state"] == Hairou.ModuleState.IDLE:
                        res = dict()
                        if vtype == "shelf":
                            res = self.h.visionReq(Hairou.TargetType.SHELF.value,Hairou.BinType.DM_MARKED.value)
                        elif vtype == "box":
                            res = self.h.visionReq(Hairou.TargetType.BOX.value, Hairou.BinType.MARKERLESS.value)
                        else:
                            res["error"] = "wrong type {}".format(vtype)
                            res["flag"] = False
                        self.state["res"] = res
                        if res["flag"]:
                            if "positionMatrix" in res:
                                self.vision_status = MoveStatus.FINISHED
                                r.setNotice(json.dumps(res))
                                return res
        return dict()       
    def indicator(self, r, chassisLedFront = None, chassisLedBack = None, buzzer = None, headLedRed = None, headLedYellow = None, headLedGreen = None, headLedFreq = None):
        res = self.h.indicatorReq(chassisLedFront,chassisLedBack,buzzer,headLedRed,headLedYellow,headLedGreen,headLedFreq)
        self.state["res"] = res
        if not res["flag"]:
            self.indicator_status = MoveStatus.RUNNING
            return False
        else :
            self.indicator_status = MoveStatus.FINISHED
        return True

    def load(self,r):
        self.operation_status = MoveStatus.RUNNING
        if self.preGoods_status is MoveStatus.NONE:
            self.preGoodsReset()
        if self.preGoods_status is not MoveStatus.FINISHED:
            self.preGoods(r, self.task["lift"], self.task["rotate"])
        if self.preGoods_status is MoveStatus.FINISHED:
            if self.rec_status is MoveStatus.NONE:
                self.recAdjustReset()
            if self.rec_status is not MoveStatus.FINISHED:
                self.recAdjust(r)
            if self.rec_status is MoveStatus.FINISHED:
                if self.getGoods_status is MoveStatus.NONE:
                    self.getGoodsReset()
                if self.getGoods_status is not MoveStatus.FINISHED:
                    self.getGoods(r, self.task["stretch"])
                if self.getGoods_status is MoveStatus.FINISHED:
                    if self.prePutGoods_status is MoveStatus.NONE:            
                        self.prePutGoodsRest()
                    if self.prePutGoods_status is not MoveStatus.FINISHED:
                        liftPos = self.goodsPosFromId[int(self.task["selfPosition"])]
                        self.prePutGoods(r, liftPos, 0)
                    if self.prePutGoods_status is MoveStatus.FINISHED:
                        if self.putGoods_status is MoveStatus.NONE:
                            self.putGoodsReset()
                        if self.putGoods_status is not MoveStatus.FINISHED:
                            stretchDist = self.stretchDist
                            self.putGoods(r, stretchDist)
                        if self.putGoods_status is MoveStatus.FINISHED:
                            self.operation_status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state["preGoods"] = self.preGoods_status
        cur_state["rec_status"] = self.rec_status
        cur_state["getGoods_status"] = self.getGoods_status
        cur_state["prePutGoods_status"] = self.prePutGoods_status
        cur_state["putGoods_status"] = self.putGoods_status
        cur_state["operation_status"] = self.operation_status
        self.state["load"] = cur_state
    def unload(self,r):
        self.operation_status = MoveStatus.RUNNING
        if self.preGoods_status is MoveStatus.NONE:
            self.preGoodsReset()
        if self.preGoods_status is not MoveStatus.FINISHED:
            liftPos = self.goodsPosFromId[int(self.task["selfPosition"])]
            self.preGoods(r, liftPos, 0)
        if self.preGoods is MoveStatus.FINISHED:
            if self.getGoods_status is MoveStatus.NONE:
                self.getGoodsReset()
            if self.getGoods_status is not MoveStatus.FINISHED:
                stretchDist = self.stretchDist
                self.getGoods(r, stretchDist)
            if self.getGoods_status is MoveStatus.FINISHED:
                if self.prePutGoods_status is MoveStatus.NONE:            
                    self.prePutGoodsRest()
                if self.prePutGoods_status is not MoveStatus.FINISHED:
                    self.prePutGoods(r, self.task["lift"], self.task["rotate"])
                if self.prePutGoods_status is MoveStatus.FINISHED:
                    if self.rec_status is MoveStatus.NONE:
                        self.recAdjustReset()
                    if self.rec_status is not MoveStatus.FINISHED:
                        self.recAdjust(r)
                    if self.rec_status is MoveStatus.FINISHED:
                        if self.putGoods_status is MoveStatus.NONE:
                            self.putGoodsReset()
                        if self.putGoods_status is not MoveStatus.FINISHED:
                            self.putGoods(r, self.task["stretch"])
                        if self.putGoods_status is MoveStatus.FINISHED:
                            self.operation_status = MoveStatus.FINISHED 
        cur_state = dict()
        cur_state["preGoods"] = self.preGoods_status
        cur_state["rec_status"] = self.rec_status
        cur_state["getGoods_status"] = self.getGoods_status
        cur_state["prePutGoods_status"] = self.prePutGoods_status
        cur_state["putGoods_status"] = self.putGoods_status
        cur_state["operation_status"] = self.operation_status
        self.state["load"] = cur_state             
    def changePos(self,r):
        self.operation_status = MoveStatus.RUNNING
        if self.preGoods_status is MoveStatus.NONE:
            self.preGoodsReset()
        if self.preGoods_status is not MoveStatus.FINISHED:
            liftPos = self.goodsPosFromId[int(self.task["changePosition0"])]
            self.preGoods(r, liftPos, 0)
        if self.preGoods_status is MoveStatus.FINISHED:
            if self.getGoods_status is MoveStatus.NONE:
                self.getGoodsReset()
            if self.getGoods_status is not MoveStatus.FINISHED:
                stretchDist = self.stretchDist
                self.getGoods(r, stretchDist)
            if self.getGoods_status is MoveStatus.FINISHED:
                if self.prePutGoods_status is MoveStatus.NONE:            
                    self.prePutGoodsRest()
                if self.prePutGoods_status is not MoveStatus.FINISHED:
                    liftPos = self.goodsPosFromId[int(self.task["changePosition1"])]
                    self.prePutGoods(r, liftPos, 0)
                if self.prePutGoods_status is MoveStatus.FINISHED:
                    if self.putGoods_status is MoveStatus.NONE:
                        self.putGoodsReset()
                    if self.putGoods_status is not MoveStatus.FINISHED:
                        stretchDist = self.stretchDist
                        self.putGoods(r, stretchDist)
                    if self.putGoods_status is MoveStatus.FINISHED:
                        self.operation_status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state["preGoods"] = self.preGoods_status
        cur_state["getGoods"] = self.getGoods_status
        cur_state["prePut"] = self.prePutGoods_status
        cur_state["putGoods"] = self.putGoods_status
        self.state["changePos"] = cur_state
    def preGoodsReset(self):
        self.finger_status = MoveStatus.NONE
        self.rotate_status = MoveStatus.NONE
        self.lift_status = MoveStatus.NONE
        self.preGoods_status = MoveStatus.RUNNING          
    def preGoods(self, r, liftPos, rotAngle):
        self.preGoods_status = MoveStatus.RUNNING
        if self.finger_status is not MoveStatus.FINISHED:
            self.finger(r, 1)
        elif self.lift_status is not MoveStatus.FINISHED:
            self.lift(r, liftPos)
        elif self.rotate_status is not MoveStatus.FINISHED:
            self.rotate(r,rotAngle)
        else:
            self.preGoods_status = MoveStatus.FINISHED
    def getGoods(self, r, stretchDist):
        self.getGoods_status = MoveStatus.RUNNING
        if self.getGoods_step1_status is MoveStatus.NONE:
            self.getGoodsStep1Reset()
        if self.getGoods_step1_status is not MoveStatus.FINISHED:
            self.getGoodsStep1(r, stretchDist)
        if self.getGoods_step1_status is MoveStatus.FINISHED:
            if self.getGoods_step2_status is MoveStatus.NONE:
                self.getGoodsStep2Reset()
            if self.getGoods_step2_status is not MoveStatus.FINISHED:
                self.getGoodsStep2(r)
            if self.getGoods_step2_status is MoveStatus.FINISHED:
                self.getGoods_status = MoveStatus.FINISHED
    def getGoodsReset(self):
        self.getGoods_step1_status = MoveStatus.NONE
        self.getGoods_step2_status = MoveStatus.NONE
        self.getGoods_status = MoveStatus.RUNNING
    def getGoodsStep1(self, r, stretchDist):
        self.getGoods_step1_status = MoveStatus.RUNNING
        if self.stretch_status is not MoveStatus.FINISHED:
            self.stretch(r, self.stretchDist)
        elif self.finger_status is not MoveStatus.FINISHED:
            self.finger(r, 0)
        else:
            self.getGoods_step1_status = MoveStatus.FINISHED     
    def getGoodsStep1Reset(self):
        self.finger_status = MoveStatus.NONE
        self.stretch_status = MoveStatus.NONE
        self.getGoods_step1_status = MoveStatus.RUNNING     
    def getGoodsStep2(self, r):
        self.getGoods_step2_status = MoveStatus.RUNNING
        if self.stretch_status is not MoveStatus.FINISHED:
            self.stretch(r, 0)
        else:
            self.getGoods_step2_status = MoveStatus.FINISHED  
    def getGoodsStep2Reset(self):
        self.stretch_status = MoveStatus.NONE
        self.getGoods_step2_status = MoveStatus.RUNNING                          
    def prePutGoods(self, r, liftPos, rotAngle):
        self.prePutGoods_status = MoveStatus.RUNNING
        if self.lift_status is not MoveStatus.FINISHED:
            self.lift(r, liftPos)
        elif self.rotate_status is not MoveStatus.FINISHED:
            self.rotate(r,rotAngle)
        else:
            self.prePutGoods_status = MoveStatus.FINISHED
        cur_state = dict({"lift_state": self.lift_status, "rotate_state": self.rotate_status, "prePutState": self.prePutGoods_status})
        self.state["prePutGoods"] = cur_state
    def prePutGoodsRest(self):
        self.rotate_status = MoveStatus.NONE
        self.lift_status = MoveStatus.NONE
        self.prePutGoods_status = MoveStatus.RUNNING      
    def putGoods(self,r, stretchDist):
        self.putGoods_status = MoveStatus.RUNNING
        if self.putGoods_step1_status is MoveStatus.NONE:
            self.putGoodsStep1Reset()
        if self.putGoods_step1_status is not MoveStatus.FINISHED:
            self.putGoodsStep1(r, stretchDist)
        if self.putGoods_step1_status is MoveStatus.FINISHED:
            if self.putGoods_step2_status is MoveStatus.NONE:
                self.putGoodsStep2Reset()
            if self.putGoods_step2_status is not MoveStatus.FINISHED:
                self.putGoodsStep2(r)
            if self.putGoods_step2_status is MoveStatus.FINISHED:
                self.putGoods_status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state["putgoodsState"] = self.putGoods_status
        cur_state["putStep1"] = self.putGoods_step1_status
        cur_state["putStep2"] = self.putGoods_step2_status
        self.state["putGoods"] = cur_state
    def putGoodsReset(self):
        self.putGoods_status = MoveStatus.RUNNING
        self.putGoods_step1_status = MoveStatus.NONE
        self.putGoods_step2_status = MoveStatus.NONE
    def putGoodsStep1(self, r, stretchDist):
        self.putGoods_step1_status = MoveStatus.RUNNING
        if self.stretch_status is not MoveStatus.FINISHED:
            stretchDist = self.stretchDist
            self.stretch(r, stretchDist)
        elif self.finger_status is not MoveStatus.FINISHED:
            self.finger(r, 1)
        else:
            self.putGoods_step1_status = MoveStatus.FINISHED 
        cur_state = dict()
        cur_state["stretch"] = self.stretch_status
        cur_state["finger"] = self.finger_status
        cur_state["putStep1"] = self.putGoods_step1_status
        self.state["putStep1"] = cur_state          
    def putGoodsStep1Reset(self):
        self.finger_status = MoveStatus.NONE
        self.stretch_status = MoveStatus.NONE
        self.putGoods_step1_status = MoveStatus.RUNNING 
    def putGoodsStep2(self, r):
        self.putGoods_step2_status = MoveStatus.RUNNING
        if self.stretch_status is not MoveStatus.FINISHED:
            self.stretch(r, 0)
        elif self.finger_status is not MoveStatus.FINISHED:
            self.finger(r, 0)
        else:
            self.putGoods_step2_status = MoveStatus.FINISHED   
    def putGoodsStep2Reset(self):
        self.finger_status = MoveStatus.NONE
        self.stretch_status = MoveStatus.NONE
        self.putGoods_step2_status = MoveStatus.RUNNING   
    def recAdjustReset(self):
        self.rotate_status = MoveStatus.NONE
        self.goPath.reset()
        self.rec_status = MoveStatus.RUNNING
    def recAdjust(self, r):
        self.rec_status = MoveStatus.RUNNING
        if self.vision_status is not MoveStatus.FINISHED:
            if "visionType" in self.task and "rec" in self.task:
                if self.task["rec"] is True:
                    # TODO
                    self.vision(r, self.task["visionType"])
                else:
                    self.task["recAdjust"] = "rec is false!"
                    self.rec_status = MoveStatus.FINISHED
                    return
            else:
                self.task["recAdjust"] = "vision Type or rec is not in the arguments!"
                self.rec_status = MoveStatus.FINISHED
                return
        if self.vision_status is MoveStatus.FINISHED:
            # TODO
            pass
    def zero(self,r):
        self.operation_status = MoveStatus.RUNNING
        if self.finger_status is not MoveStatus.FINISHED:
            self.finger(r, 0)
        elif self.stretch_status is not MoveStatus.FINISHED:
            self.stretch(r,0)
        elif self.rotate_status is not MoveStatus.FINISHED:
            self.rotate(r, 0)
        elif self.lift_status is not MoveStatus.FINISHED:
            self.lift(r, 385)
        else:
            self.operation_status = MoveStatus.FINISHED
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