import HairouNoBlock as Hairou
import json
import time
from syspy.rbk import MoveStatus, BasicModule, normalize_theta, ParamServer
from syspy.rbkSim import SimModule
import math
import syspy.goPath
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
        "shelf","box","reset"
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
    },
    "recAdjust":{
        "value":1,
        "tips":"",
        "type":"int",
        "max_value":1,
        "min_value":1
    },
    "useLoc":{
        "value":1,
        "tips":"",
        "type":"int",
        "max_value":1,
        "min_value":1
    }
}
####END DEFAULT ARGS####
def getYPRZYX(p):
    yaw = math.atan2(p[4],p[0])
    pitch = math.atan2(-p[8],math.sqrt(p[9]*p[9] + p[10]*p[10]))
    roll = math.atan2(p[9],p[10])
    dx = p[3]
    dy = p[7]
    dz = p [11]
    return yaw, pitch, roll, dz, dy, dx

def getYPRZYXV2(p):
    sy = math.sqrt(p[0] * p[0] + p[4] * p[4])
    if sy >= 1e-6:
        yaw = math.atan2(p[4], p[0])
        c = math.cos(yaw)
        s = math.sin(yaw)
        pitch = math.atan2(-p[8], c * p[0] + s * p[4])
        roll = math.atan2(p[2] * s - p[6] * c, - p[1] * s + p[5] *c)
        dx = p[3]
        dy = p[7]
        dz = p [11]
        return yaw, pitch, roll, dz, dy, dx 
    else:
        yaw = 0
        pitch = math.atan2(-p[8], sy)
        roll = math.atan2(-p[6],p[5])
        dx = p[3]
        dy = p[7]
        dz = p [11]
        return yaw, pitch, roll, dz, dy, dx 

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.status = MoveStatus.RUNNING
        p = ParamServer(__file__)
        ip = p.loadParam("ip", type="str", default = "192.168.192.20", comment = "ip addr")
        port = p.loadParam("port", type="int", default = 4172, maxValue = 999999, minValue = 0, comment = "port")
        self.h = Hairou.Hairou(ip,port)
        self.lift_reach_dist = p.loadParam("lift_reach_dist", type="float", default = 0.5, maxValue = 10.0, minValue = 0.0, unit = "mm", comment = "lift_reach_dist")
        self.rotate_reach_angle = p.loadParam("rotate_reach_angle", type="float", default = 0.01, maxValue = 10.0, minValue = 0.0, unit = "rad", comment = "rotate_reach_angle")
        self.stretch_reach_dist = p.loadParam("stretch_reach_dist", type="float", default = 0.5, maxValue = 10.0, minValue = 0.0, unit = "mm", comment = "stretch_reach_dist")
        self.init = True
        self.task = dict()
        self.low = dict({0:390, 1:840, 2:1285}) #mm
        self.low[0] = p.loadParam("low0", type="float", default = 390.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "下降时，第0层高度")
        self.low[1] = p.loadParam("low1", type="float", default = 840.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "下降时，第1层高度")
        self.low[2] = p.loadParam("low2", type="float", default = 1285.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "下降时，第2层高度")
        self.high = dict({0:420, 1:870, 2:1320}) #mm
        self.high[0] = p.loadParam("high0", type="float", default = 420.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "上升时，第0层高度")
        self.high[1] = p.loadParam("high1", type="float", default = 870.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "上升时，第1层高度")
        self.high[2] = p.loadParam("high2", type="float", default = 1320.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "上升时，第2层高度")
        self.stretchDist = p.loadParam("stretchDist", type="float", default = 740.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放在自己货架上，抽屉伸出长度")
        self.rec_offz_box = p.loadParam("rec_offz_box", type="float", default = -120.0, maxValue = 1000.0, minValue = -1000.0, unit = "mm", comment = "识别货物后，抓货物时高度的调整距离")
        self.rec_offz_shelf = p.loadParam("rec_offz_shelf", type="float", default = 10.0, maxValue = 1000.0, minValue = -1000.0, unit = "mm", comment = "识别货架后，放货物时高度的调整距离")
        self.stretch_status = MoveStatus.NONE
        self.lift_status = MoveStatus.NONE
        self.rotate_status = MoveStatus.NONE
        self.finger_status = MoveStatus.NONE
        self.vision_status = MoveStatus.NONE
        self.indicator_status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.task_list = []
        self.task_id = 0
        self.state = dict()
        self.goPath = goPath.Module(r, args)
        self.waitVision = waitVision()
        self.waitVision.status = MoveStatus.NONE
        self.h.connect()
    def run(self, r:SimModule,args):
        if r.errorExits(52111):
            self.status = MoveStatus.FAILED
            return self.status.value
        if self.init:
            self.init = False
            self.status = MoveStatus.RUNNING
            self.task = args
        if not self.h.isconnect:
            self.h.initDevice(r)
            return self.status
        if self.status is not MoveStatus.FINISHED:
            self.state = self.h.getReport(r)
            self.state["task"] = self.task
            if "operation" in self.task and self.task["operation"] == "load":
                if "lift" in self.task and "rotate" in self.task and "stretch" in self.task and "selfPosition" in self.task:
                    self.load(r)
                else:
                    r.setError("task is wrong : {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED
            elif "operation" in self.task and self.task["operation"] == "unload":
                if "lift" in self.task and "rotate" in self.task and "stretch" in self.task and "selfPosition" in self.task:
                    self.unload(r)
                else:
                    r.setError("task is wrong : {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED
            elif "operation" in self.task and self.task["operation"] == "change":
                if "changePosition0" in self.task and "changePosition1" in self.task:
                    self.vision_status = MoveStatus.FINISHED
                    self.changePos(r)
                else:
                    r.setError("task is wrong : {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED  
            elif "operation" in self.task and self.task["operation"] == "zero":
                self.vision_status = MoveStatus.FINISHED
                self.zero(r)
            elif "recAdjust" in self.task:
                self.stretch_status = MoveStatus.FINISHED
                self.finger_status = MoveStatus.FINISHED
                self.indicator_status = MoveStatus.FINISHED
                if "visionType" in self.task:
                    self.rec(r)
                else:
                    r.setError("rec task is wrong : {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED                     
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
        str_state = json.dumps(self.state)
        r.setInfo(str_state)
        r.logDebug(str_state)
        return self.status.value
    def lift(self, r, height):
        self.lift_status = MoveStatus.RUNNING
        if "lift" in self.state:
            if "stretch" in self.state and self.state["stretch"]["position"] < 10:
                device_state = self.state["lift"]
                if "position" in device_state and "state" in device_state:
                    if abs(device_state["position"] - height) < self.lift_reach_dist  \
                        and device_state["state"] != Hairou.ModuleState.ERROR \
                            and device_state["state"] != Hairou.ModuleState.INIT \
                                and device_state["state"] != Hairou.ModuleState.RESET:
                                self.lift_status = MoveStatus.FINISHED
                                return True
                if "state" in device_state:
                    if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                        res = self.h.liftReset(r)
                        self.state["res"] = res
                    elif device_state["state"] == Hairou.ModuleState.IDLE:
                        res = self.h.liftPos(height,r)
                        self.state["res"] = res
            else:
                r.setError("stretch pos is not zero cannot lift.!!! {}".format(self.state["stretch"]["position"]))
        return False
    def rotate(self, r, theta):
        self.rotate_status = MoveStatus.RUNNING
        if "rotate" in self.state:
            if "stretch" in self.state and self.state["stretch"]["position"] < 10:
                device_state = self.state["rotate"]
                if "position" in device_state and "state" in device_state:
                    if abs(normalize_theta(device_state["position"] - theta)) < self.rotate_reach_angle \
                        and device_state["state"] != Hairou.ModuleState.ERROR \
                            and device_state["state"] != Hairou.ModuleState.INIT \
                                and device_state["state"] != Hairou.ModuleState.RESET:
                                self.rotate_status = MoveStatus.FINISHED
                                return True
                if "state" in device_state:
                    if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                        res = self.h.rotateReset(r)
                        self.state["res"] = res
                    elif device_state["state"] == Hairou.ModuleState.IDLE:
                        res = self.h.rotateAngle(theta,r)
                        self.state["res"] = res
            else:
                r.setError("stretch pos is not zero cannot rotate.!!! {}".format(self.state["stretch"]["position"]))
        return False       
    def stretch(self, r, pos):
        self.stretch_status = MoveStatus.RUNNING
        if "stretch" in self.state:
            device_state = self.state["stretch"]
            if "position" in device_state and "state" in device_state:
                if abs(device_state["position"] - pos) < self.stretch_reach_dist \
                    and device_state["state"] != Hairou.ModuleState.ERROR \
                        and device_state["state"] != Hairou.ModuleState.INIT \
                            and device_state["state"] != Hairou.ModuleState.RESET:
                            self.stretch_status = MoveStatus.FINISHED
                            return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.stretchReset(r)
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.stretchPos(pos,r)
                    self.state["res"] = res
        return False    
    def finger(self, r, pos):
        self.finger_status = MoveStatus.RUNNING
        if "finger" in self.state:
            device_state = self.state["finger"]
            if "leftStatus" in device_state and "state" in device_state \
                    and device_state["state"] != Hairou.ModuleState.ERROR \
                        and device_state["state"] != Hairou.ModuleState.INIT \
                            and device_state["state"] != Hairou.ModuleState.RESET:
                            if abs(pos - 1) < 0.1 and abs(device_state["leftStatus"] + 1) < 0.1 and abs(device_state["rightStatus"] + 1) < 0.1:
                                self.finger_status = MoveStatus.FINISHED
                                return True
                            elif abs(pos) < 0.1 and abs(device_state["leftStatus"] - 1) < 0.1 and abs(device_state["rightStatus"] - 1) < 0.1:
                                self.finger_status = MoveStatus.FINISHED
                                return True                    
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.fingerReset(r)
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.fingerPos(pos,r)
                    self.state["res"] = res
        return False
    def record_vision(self, r):
        res = self.h.visionRecord(r)
        self.state["record_vision_res"] = res            
    def vision(self, r, vtype):
        if self.vision_status is not MoveStatus.FINISHED:
            self.vision_status = MoveStatus.RUNNING
            if "vision" in self.state:
                device_state = self.state["vision"]
                if vtype == "reset":
                    res = self.h.visionReset(r)
                    self.state["res"] = res
                    self.vision_status = MoveStatus.FINISHED
                else :
                    if "state" in device_state:
                        if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                            self.h.visionReset(r)
                        elif device_state["state"] == Hairou.ModuleState.IDLE:
                            if self.waitVision.status == MoveStatus.NONE:
                                self.waitVision.reset()
                            self.waitVision.run(r,self)
                            if self.waitVision.status == MoveStatus.FINISHED:
                                res = dict()
                                if vtype == "shelf":
                                    res = self.h.visionReq(Hairou.TargetType.SHELF.value,Hairou.BinType.DM_MARKED.value,r)
                                elif vtype == "box":
                                    res = self.h.visionReq(Hairou.TargetType.BOX.value, Hairou.BinType.DM_MARKED.value,r)
                                else:
                                    res["error"] = "wrong type {}".format(vtype)
                                    res["flag"] = False
                                    self.vision_status = MoveStatus.FAILED
                                self.state["res"] = res
                                if res["flag"]:
                                    if "positionMatrix" in res:
                                        self.vision_status = MoveStatus.FINISHED
                                        self.waitVision.status = MoveStatus.NONE
                                        yaw, pitch, roll, dx , dy, dz = getYPRZYX(res["positionMatrix"])
                                        out1 = dict()
                                        out1["yaw"] = yaw * 180.0/math.pi
                                        out1["pitch"] = pitch * 180.0/math.pi
                                        out1["roll"] = roll * 180.0/math.pi
                                        out1["dx"] = dx
                                        out1["dy"] = dy
                                        out1["dz"] = dz
                                        self.state["vout1"] = out1
                                        yaw2, pitch2, roll2, dx2, dy2, dz2 = getYPRZYXV2(res["positionMatrix"])
                                        out2 = dict()
                                        out2["yaw"] = yaw2 * 180.0/math.pi
                                        out2["pitch"] = pitch2 * 180.0/math.pi
                                        out2["roll"] = roll2 * 180.0/math.pi
                                        out2["dx"] = dx2
                                        out2["dy"] = dy2
                                        out2["dz"] = dz2
                                        self.state["vout2"] = out2   
                                        res["vout1"] = out1
                                        res["vout2"] = out2                           
                                        r.setNotice(json.dumps(res))
                                        return res
                                else:
                                    self.vision_status = MoveStatus.FAILED
                                    r.setNotice("no results. {}".format(json.dumps(res)))
        return dict()       
    def indicator(self, r, chassisLedFront = None, chassisLedBack = None, buzzer = None, headLedRed = None, headLedYellow = None, headLedGreen = None, headLedFreq = None):
        res = self.h.indicatorReq(chassisLedFront,chassisLedBack,buzzer,headLedRed,headLedYellow,headLedGreen,headLedFreq,r)
        self.state["res"] = res
        if not res["flag"]:
            self.indicator_status = MoveStatus.RUNNING
            return False
        else :
            self.indicator_status = MoveStatus.FINISHED
        return True
    def runTakList(self, r):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(self)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED
    def rec(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                recAdjust(self.task["visionType"], self.rec_offz_box, self.rec_offz_shelf)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["rec"] = cur_state
    def load(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if "recAdjust" in self.task:
                if "visionType" in self.task and self.task["visionType"] == "box":
                    self.task_list = [
                        preGoods(self.task["lift"], self.task["rotate"]),
                        recAdjust(self.task["visionType"], self.rec_offz_box, self.rec_offz_shelf),
                        getGoods(self.task["stretch"]),
                        prePutGoods(self.high[int(self.task["selfPosition"])],0),
                        putGoods(self.stretchDist)
                    ]
                else:
                    r.setError("task is wrong in unload with recAdjust: {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED
            else:
                self.vision_status = MoveStatus.FINISHED
                self.task_list = [
                    preGoods(self.task["lift"], self.task["rotate"]),
                    getGoods(self.task["stretch"]),
                    prePutGoods(self.high[int(self.task["selfPosition"])],0),
                    putGoods(self.stretchDist)
                ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state
    def unload(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if "recAdjust" in self.task:
                if "visionType" in self.task and self.task["visionType"] == "shelf":
                    self.task_list = [
                        preGoods(self.low[int(self.task["selfPosition"])], 0),
                        getGoods(self.stretchDist),
                        prePutGoods(self.task["lift"], self.task["rotate"]),
                        recAdjust(self.task["visionType"], self.rec_offz_box, self.rec_offz_shelf),
                        putGoods(self.task["stretch"])
                    ]
                else:
                    r.setError("task is wrong in unload with recAdjust: {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED
            else:
                self.vision_status = MoveStatus.FINISHED
                self.task_list = [
                    preGoods(self.low[int(self.task["selfPosition"])], 0),
                    getGoods(self.stretchDist),
                    prePutGoods(self.task["lift"], self.task["rotate"]),
                    putGoods(self.task["stretch"])
                ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["unload"] = cur_state             
    def changePos(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                preGoods(self.low[int(self.task["changePosition0"])], 0),
                getGoods(self.stretchDist),
                prePutGoods(self.high[int(self.task["changePosition1"])], 0),
                putGoods(self.stretchDist)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["change"] = cur_state  

    def zero(self,r):
        self.operation_status = MoveStatus.RUNNING
        if self.finger_status is not MoveStatus.FINISHED:
            self.h.visionReset(r)
            self.h.fingerReset(r)
            self.finger(r, 0)
        elif self.stretch_status is not MoveStatus.FINISHED:
            self.h.stretchReset(r)
            self.stretch(r,0)
        elif self.rotate_status is not MoveStatus.FINISHED:
            self.h.rotateReset(r)
            self.rotate(r, 0)
        elif self.lift_status is not MoveStatus.FINISHED:
            self.h.liftReset(r)
            self.lift(r, 385)
        else:
            self.operation_status = MoveStatus.FINISHED
    def cancel(self, r:SimModule):
        r.logInfo("script cancel")
        self.h.disconnect()
        self.status = MoveStatus.NONE


class recAdjust:
    def __init__(self, visionType, rec_offz_box, rec_offz_shelf):
        self.status = MoveStatus.NONE
        self.visionType = visionType
        self.dtheta = 0 #角度方向
        self.dy = 0 #侧向
        self.dz = 0 #垂直方向
        p = ParamServer(__file__)
        self.max_rec_times = p.loadParam("max_rec_times", type="int", default = 10, maxValue = 999999, minValue = 0, comment = "最多识别次数")
        self.max_adjust_time = p.loadParam("max_adjust_time", type="int", default = 10, maxValue = 999999, minValue = 0, comment = "最多调整次数")
        self.rec_count = 0
        self.offz_box = rec_offz_box
        self.offz_shelf = rec_offz_shelf
        self.lift_pos = 0
        self.rot_theta = 0
        self.go_args = dict()
        self.adjust_count = 0
        self.ok = False
    def reset(self, ctu):
        ctu.vision_status = MoveStatus.NONE
        ctu.rotate_status = MoveStatus.NONE
        ctu.lift_status = MoveStatus.NONE
        self.dtheta = 0
        self.dy = 0
        self.dz = 0
        self.rec_count = 0
        ctu.goPath.reset()
        self.status = MoveStatus.RUNNING
        self.lift_pos = 0
        self.rot_theta = 0
        self.go_args = dict()
        self.adjust_count = 0
        self.ok = False
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.vision_status is not MoveStatus.FINISHED:
            if self.rec_count < self.max_rec_times:
                if ctu.vision_status == MoveStatus.FAILED:
                    self.rec_count = self.rec_count + 1
                res = ctu.vision(r, self.visionType)
                if "vout1" in res and "vout2" in res:
                    method = "vout2"
                    if abs(res[method]["pitch"] < 8) :
                        self.dtheta = -res[method]["pitch"] * math.pi /180.0
                        self.dz = res[method]["dz"]
                        self.dy = res[method]["dy"]
                        if self.adjust_count >= self.max_adjust_time:
                            self.operation_status = MoveStatus.FAILED
                            r.setError("recAdjust fails!!! reach max times.")
                        else:
                            self.go_args["x"] = self.dy * math.sin(ctu.state["rotate"]["position"])
                            self.go_args["y"] = 0
                            self.go_args["theta"] = 0
                            self.go_args["reachAngle"] = math.pi
                            if "useLoc" not in ctu.task:
                                self.go_args["useOdo"] = 1
                            self.go_args["reachDist"] = 0.002
                            if self.go_args["x"] < 0:
                                self.go_args["backMode"] = 1
                            self.rot_theta = ctu.state["rotate"]["position"] + self.dtheta
                            if abs(self.go_args["x"]) < 0.006 and abs(self.dtheta) < 0.03:
                                self.ok = True 
                                self.lift_pos = ctu.state["lift"]["position"]
                                if self.visionType == "shelf":
                                    self.lift_pos = self.lift_pos + self.dz * 1000 + self.offz_shelf
                                elif self.visionType == "box":
                                    self.lift_pos = self.lift_pos + self.dz * 1000 + self.offz_box
                            else:
                                self.lift_pos = ctu.state["lift"]["position"]
                                if self.visionType == "shelf":
                                    self.lift_pos = self.lift_pos + self.dz * 1000
                                elif self.visionType == "box":
                                    self.lift_pos = self.lift_pos + self.dz * 1000                           
                    else:
                        ctu.record_vision(r)
                        r.setNotice(" pitch is too large: {}".format(res[method]["pitch"]))
                        ctu.vision_status = MoveStatus.FAILED
                        self.status = MoveStatus.FAILED
                else:
                    ctu.vision_status = MoveStatus.NONE
            else:
                r.setError("rec fails!!! reach max times.")
                self.status = MoveStatus.FAILED
        else:
            if self.ok:
                if ctu.lift_status is not MoveStatus.FINISHED:
                    ctu.lift(r,self.lift_pos)
                if ctu.lift_status is MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
                elif ctu.lift_status is MoveStatus.FINISHED:
                    ctu.rotate_status = MoveStatus.FINISHED
                    ctu.goPath.status = MoveStatus.FINISHED
                    self.status = MoveStatus.FINISHED
            else:
                if ctu.lift_status is not MoveStatus.FINISHED:
                    ctu.lift(r,self.lift_pos)
                if ctu.goPath.status is not MoveStatus.FINISHED:
                    if abs(self.go_args["x"]) < 0.003:
                        ctu.goPath.status = MoveStatus.FINISHED
                    else:
                        ctu.goPath.run(r,self.go_args)
                if ctu.rotate_status is not MoveStatus.FINISHED:
                    ctu.rotate(r,self.rot_theta)
                if ctu.lift_status is MoveStatus.FAILED or ctu.goPath.status is MoveStatus.FAILED or ctu.rotate_status is MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
                elif ctu.lift_status is MoveStatus.FINISHED and ctu.goPath.status is MoveStatus.FINISHED and ctu.rotate_status is MoveStatus.FINISHED:
                    self.adjust_count = self.adjust_count + 1
                    ctu.vision_status = MoveStatus.NONE
                    ctu.rotate_status = MoveStatus.NONE
                    ctu.lift_status = MoveStatus.NONE
                    self.dtheta = 0
                    self.dy = 0
                    self.dz = 0
                    self.rec_count = 0
                    ctu.goPath.reset()
                    self.status = MoveStatus.RUNNING
                    self.lift_pos = 0
                    self.rot_theta = 0
                    self.go_args = dict()
        cur_state = dict()
        cur_state["dz"] = self.dz
        cur_state["dy"] = self.dy
        cur_state["dtheta"] = self.dtheta
        cur_state["goaPathStatus"] = ctu.goPath.status
        cur_state["lift_pos"] = self.lift_pos
        cur_state["go_args"] = self.go_args
        cur_state["rot_theta"] = self.rot_theta
        cur_state["adj_count"] = self.adjust_count
        cur_state["visionType"] = self.visionType
        cur_state["status"] = self.status
        ctu.state["recAdjStatus"] = cur_state

class preGoods:
    def __init__(self, liftPos, rotAngle):
        self.status = MoveStatus.NONE
        self.liftPos = liftPos
        self.rotAngle = rotAngle
    def reset(self, ctu):
        ctu.finger_status = MoveStatus.NONE
        ctu.rotate_status = MoveStatus.NONE
        ctu.lift_status = MoveStatus.NONE
        self.status = MoveStatus.RUNNING
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.finger_status is not MoveStatus.FINISHED:
            ctu.finger(r, 1)
        if ctu.lift_status is not MoveStatus.FINISHED:
            ctu.lift(r, self.liftPos)
        if ctu.rotate_status is not MoveStatus.FINISHED:
            ctu.rotate(r,self.rotAngle)
        if ctu.finger_status is MoveStatus.FINISHED and ctu.lift_status is MoveStatus.FINISHED and ctu.rotate_status is MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED

class getGoodsS1:
    def __init__(self, stretchDist):
        self.status = MoveStatus.NONE
        self.stretchDist = stretchDist
    def reset(self, ctu):
        ctu.finger_status = MoveStatus.NONE
        ctu.stretch_status = MoveStatus.NONE
        self.status = MoveStatus.RUNNING    
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.stretch_status is not MoveStatus.FINISHED:
            ctu.stretch(r, self.stretchDist)
        elif ctu.finger_status is not MoveStatus.FINISHED:
            ctu.finger(r, 0)
        else:
            self.status = MoveStatus.FINISHED

class getGoodsS2:
    def __init__(self):
        self.status = MoveStatus.NONE
    def reset(self, ctu):
        ctu.stretch_status = MoveStatus.NONE
        self.status = MoveStatus.RUNNING
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.stretch_status is not MoveStatus.FINISHED:
            ctu.stretch(r, 0)
        else:
            self.status = MoveStatus.FINISHED  

class getGoods:
    def __init__(self, stretchDist):
        self.status = MoveStatus.NONE
        self.task_list = [getGoodsS1(stretchDist), getGoodsS2()]
        self.task_id = 0
    def reset(self, ctu):
        for task in self.task_list:
            task.status = MoveStatus.NONE
        self.task_id = 0
        self.status = MoveStatus.RUNNING
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(ctu)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            else:
                self.task_list[self.task_id].run(r, ctu)
        else:
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state["task_id"] = self.task_id
        cur_state["status"] = self.status
        ctu.state["getGoods"] = cur_state

class prePutGoods:
    def __init__(self, liftPos, rotAngle):
        self.status = MoveStatus.NONE
        self.liftPos = liftPos
        self.rotAngle = rotAngle
    def reset(self, ctu):
        ctu.rotate_status = MoveStatus.NONE
        ctu.lift_status = MoveStatus.NONE
        self.status = MoveStatus.RUNNING
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.lift_status is not MoveStatus.FINISHED:
            ctu.lift(r, self.liftPos)
        if ctu.rotate_status is not MoveStatus.FINISHED:
            ctu.rotate(r,self.rotAngle)
        if ctu.lift_status is MoveStatus.FINISHED and ctu.rotate_status is MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED      

class putGoodsS1:
    def __init__(self,stretchDist):
        self.status = MoveStatus.NONE
        self.stretchDist = stretchDist
    def reset(self, ctu):
        ctu.finger_status = MoveStatus.NONE
        ctu.stretch_status = MoveStatus.NONE
        self.status = MoveStatus.RUNNING     
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.stretch_status is not MoveStatus.FINISHED:
            ctu.stretch(r, self.stretchDist)
        elif ctu.finger_status is not MoveStatus.FINISHED:
            ctu.finger(r, 1)
        else:
            self.status = MoveStatus.FINISHED 

class putGoodsS2:
    def __init__(self):
        self.status = MoveStatus.NONE
    def reset(self, ctu):
        ctu.finger_status = MoveStatus.NONE
        ctu.stretch_status = MoveStatus.NONE
        self.status = MoveStatus.RUNNING    
    def run(self, r ,ctu):
        self.status = MoveStatus.RUNNING
        if ctu.stretch_status is not MoveStatus.FINISHED:
            ctu.stretch(r, 0)
        elif ctu.finger_status is not MoveStatus.FINISHED:
            ctu.finger(r, 0)
        else:
            self.status = MoveStatus.FINISHED  

class putGoods:
    def __init__(self, stretchDist):
        self.status = MoveStatus.NONE
        self.task_list = [putGoodsS1(stretchDist), putGoodsS2()]
        self.task_id = 0
    def reset(self, ctu):
        for task in self.task_list:
            task.status = MoveStatus.NONE
        self.task_id = 0
        self.status = MoveStatus.RUNNING
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(ctu)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            else:
                self.task_list[self.task_id].run(r, ctu)
        else:
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state["task_id"] = self.task_id
        cur_state["status"] = self.status
        ctu.state["putGoods"] = cur_state
class waitVision:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.wtime = 0.5
        self.start_time = time.time()
    def reset(self):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()
    def run(self, r, ctu):
        if self.status is not MoveStatus.FINISHED:
            t = time.time()
            dt = t - self.start_time
            if dt > self.wtime:
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING
if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["headLedFreq"] = dict()
    data["headLedFreq"]["value"] = "1"
    print(m.run(r, data))