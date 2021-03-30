import HairouNoBlock as Hairou
import json
import time
import sys
sys.path.append("syspy")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, normalize_theta, ParamServer
import math
import syspy.goPath as goPath
"""
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
        "shelf","box", "reset"
        ],
        "tips": "tips",
        "type": "complex"
    },
    "visionBinType":{
        "value": "code",
        "default_value":[
            "code","markerless", "barcode"
        ],
        "tips":"货物识别类型",
        "type": "complex"
    },
    "binModel":{
        "value":"plasticbox",
        "default_value":[
            "carton","plasticbox"
        ],
        "tips":"料箱种类，当visionBinType为markerless时需要填写这项",
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
"""

def matrixDot(a,b, m, l, n):
    """ c = a * b

    Args:
        a ([type]): 2d matrix m * l
        b ([type]): 2d matrix l * n
        m ([type]): row
        l ([type]): col
        n ([type]): row

    Returns:
        [type]: 2d matrix
    """
    out = [[0] * n for i in range(m)]
    for i in range(m):
        for j in range(n):
            v = 0
            for k in range(l):
                v = v + a[i][k] * b[k][j]
            out[i][j] = v
    return out

def matrixReshape(a, m, n):
    """[summary]

    Args:
        a ([type]): input matrix
        m ([type]): row num
        n ([type]): col num

    Returns:
        [type]: 2d matrix
    """
    out = [[0]*n for i in range(m)]
    mid = []
    for i in range(len(a)):
        for j in range(len(a[i])):
            mid.append(a[i][j])
    for i in range(m):
        for j in range(n):
            out[i][j] = mid [i*n + j]
    return out

def TMatrixReverse(a):
    """transition matrix reverse

    Args:
        a ([type]): 2d 4 * 4 transition matrix

    Returns:
        [type]: 2d  4 * 4 transitionmatrix
    """
    rMatrix = [[0]*3 for i in range(3)]
    for i in range(3):
        for j in range(3):
            rMatrix[i][j] = a[j][i]
    org_t = [[a[i][3]] for i in range(3)]
    tMatrix = [[0]for i in range(3)]
    tMatrix = matrixDot(rMatrix, org_t, 3, 3, 1)
    for i in range(3):
        tMatrix[i][0] = -tMatrix[i][0]
    out = [[0]*4 for i in range(4)]
    for i in range(3):
        for j in range(3):
            out[i][j] = rMatrix[i][j]
    for i in range(3):
        out[i][3] = tMatrix[i][0]
    out[3][3] = 1
    return out

def getYPRZYX(p):
    yaw = math.atan2(p[4],p[0])
    pitch = math.atan2(-p[8],math.sqrt(p[9]*p[9] + p[10]*p[10]))
    roll = math.atan2(p[9],p[10])
    dx = p[3]
    dy = p[7]
    dz = p [11]
    return yaw, pitch, roll, dz, dy, dx

def getYPRZYX_code(p, theta):
    Tagv2f = [[math.cos(theta), -math.sin(theta), 0., 0.],
              [math.sin(theta), math.cos(theta), 0., 0.],
              [0.,0.,1.,0.],
              [0.,0.,0.,1.]]
    Tf2c = [[0.,0.,1.,0.262],
            [0.,-1.,0.,0.],
            [1.,0.,0.,-0.029],
            [0.,0.,0.,1.]]
    Tc2m_now = matrixReshape(p, 4, 4)
    Tf2m_now = matrixDot(Tf2c,Tc2m_now, 4, 4, 4)
    newp = matrixReshape(Tf2m_now, 1, 16)[0]
    yaw, pitch, roll, dz, dy, dx = getYPRZYX(newp)
    Tagv2m_now = matrixDot(Tagv2f,Tf2m_now, 4, 4, 4)
    #pf2m 二维码在货叉坐标系中的位置
    pf2m = [[dx],[0],[dz],[1]]
    pagv2m = matrixDot(Tagv2f, pf2m, 4 ,4 ,1)
    dist = Tagv2m_now[0][3] - pagv2m[0][0]
    return  yaw, pitch, roll, dz, dy, dx, dist

def getYPRZYX_markerless(p, theta): 
    Tagv2f = [[math.cos(theta), -math.sin(theta), 0., 0.],
              [math.sin(theta), math.cos(theta), 0., 0.],
              [0.,0.,1.,0.],
              [0.,0.,0.,1.]]    
    Tf2ifm = [[1.,0.,0.,-0.281],
              [0.,1.,0.,0.],
              [0.,0.,1.,0.218],
              [0.,0.,0.,1.]]
    Tifm2box = matrixReshape(p, 4,4)
    Tf2box = matrixDot(Tf2ifm,Tifm2box, 4, 4, 4)
    newp = matrixReshape(Tf2box, 1,16)[0]
    yaw, pitch, roll, dz, dy, dx = getYPRZYX(newp)
    Tagv2box = matrixDot(Tagv2f,Tf2box, 4, 4, 4)
    #pf2box， box在货叉坐标系中的位置
    pf2box = [[dx],[0],[dz],[1]]
    pagv2m = matrixDot(Tagv2f, pf2box, 4 ,4 ,1)
    dist = Tagv2box[0][3] - pagv2m[0][0] 
    return yaw, pitch, roll, dz, dy, dx, dist

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.status = MoveStatus.RUNNING
        p = ParamServer(__file__)
        ip = p.loadParam("ip", type="str", default = "192.168.192.20", comment = "ip addr")
        port = p.loadParam("port", type="int", default = 4172, maxValue = 999999, minValue = 0, comment = "port")
        self.start_connect_time = time.time()
        self.max_connect_time = p.loadParam("max_connect_time", type="int", default = 10, maxValue = 999999, minValue = 0, comment = "链接等待最长时间s")
        self.h = Hairou.Hairou(ip,port)
        self.lift_reach_dist = p.loadParam("lift_reach_dist", type="float", default = 0.5, maxValue = 10.0, minValue = 0.0, unit = "mm", comment = "lift_reach_dist")
        self.rotate_reach_angle = p.loadParam("rotate_reach_angle", type="float", default = 0.01, maxValue = 10.0, minValue = 0.0, unit = "rad", comment = "rotate_reach_angle")
        self.stretch_reach_dist = p.loadParam("stretch_reach_dist", type="float", default = 0.5, maxValue = 10.0, minValue = 0.0, unit = "mm", comment = "stretch_reach_dist")
        self.init = True
        self.task = dict()
        self.low = dict({0:740, 1:1130, 2:1520, 3:1910, 4:2300}) #mm
        #此处在背篓取货时需要略低于背篓的高度，此处所更改的数值为默认值，需要在"ctu.json"文件里修改才是最终执行的高度
        self.low[0] = p.loadParam("low0", type="float", default = 740.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第0层高度")
        self.low[1] = p.loadParam("low1", type="float", default = 1130.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第1层高度")
        self.low[2] = p.loadParam("low2", type="float", default = 1520.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第2层高度")
        self.low[3] = p.loadParam("low3", type="float", default = 1910.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第3层高度")
        self.low[4] = p.loadParam("low4", type="float", default = 2300.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第4层高度")
        self.high = dict({0:760, 1:1150, 2:1550, 3:1940, 4:2330}) #mm
        #此处在背篓放货时需要略高于背娄的高度，此处所更改的数值为默认值，需要在"ctu.json"文件里修改才是最终执行的高度
        self.high[0] = p.loadParam("high0", type="float", default = 760.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第0层高度")
        self.high[1] = p.loadParam("high1", type="float", default = 1150.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第1层高度")
        self.high[2] = p.loadParam("high2", type="float", default = 1550.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第2层高度")
        self.high[3] = p.loadParam("high3", type="float", default = 1940.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第3层高度")
        self.high[4] = p.loadParam("high4", type="float", default = 2320.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第4层高度")
        #此处修改的是默认值，最终执行请在“ctu.json"里进行更改
        self.stretchDist = p.loadParam("stretchDist", type="float", default = 750.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放在自己货架上，抽屉伸出长度")
         #此处修改的是默认值，最终执行请在“ctu.json"里进行更改
        self.rec_offz_box = p.loadParam("rec_offz_box", type="float", default = -80.0, maxValue = 1000.0, minValue = -1000.0, unit = "mm", comment = "识别货物后，抓货物时高度的调整距离")
         #此处修改的是默认值，最终执行请在“ctu.json"里进行更改
        self.rec_offz_shelf = p.loadParam("rec_offz_shelf", type="float", default = 40.0, maxValue = 1000.0, minValue = -1000.0, unit = "mm", comment = "识别货架后，放货物时高度的调整距离")        
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
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.task = args
        if not self.h.isconnect:
            self.h.initDevice(r)
            self.state["warning"] = "ctu is connecting!!!!"
            str_state = json.dumps(self.state)
            r.setInfo(str_state)
            r.logDebug(str_state)
            dtime = time.time() - self.start_connect_time
            if dtime > self.max_connect_time:
                r.setError("ctu connect is overtime: {}".format(self.max_connect_time))
                self.status = MoveStatus.FAILED
            return self.status
        if self.status is not MoveStatus.FINISHED:
            self.state = self.h.getReport(r)
            if "connect_error" in self.state:
                dtime = time.time() - self.start_connect_time
                if dtime > self.max_connect_time:
                    r.setError("ctu connect is overtime: {}".format(self.max_connect_time))
                    self.status = MoveStatus.FAILED
                    str_state = json.dumps(self.state)
                    r.setInfo(str_state)
                    r.logDebug(str_state)
                    return self.status    
            else:
                self.start_connect_time = time.time()
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
                    if "visionBinType" not in self.task:
                        self.task["visionBinType"] = "code"
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
                    if "visionBinType" not in self.task:
                        self.task["visionBinType"] = "code"
                    self.vision(r, self.task["visionType"], self.task["visionBinType"], 
                                self.task.get("binModel", "plasticbox"))
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
                                self.h.reset_liftPos()
                                return True
                if "state" in device_state:
                    if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                        res = self.h.liftReset(r)
                        self.h.reset_liftPos()
                        self.state["res"] = res
                    elif device_state["state"] == Hairou.ModuleState.IDLE:
                        res = self.h.liftPos(height,r)
                        self.state["res"] = res
            else:
                r.setError("stretch pos is not zero cannot lift.!!! {}".format(self.state["stretch"]["position"]))
                self.lift_status = MoveStatus.FAILED
                self.status = MoveStatus.FAILED
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
                                self.h.reset_rotateAngle()
                                return True
                if "state" in device_state:
                    if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                        res = self.h.rotateReset(r)
                        self.h.reset_rotateAngle()
                        self.state["res"] = res
                    elif device_state["state"] == Hairou.ModuleState.IDLE:
                        res = self.h.rotateAngle(theta,r)
                        self.state["res"] = res
            else:
                self.rotate_status = MoveStatus.FAILED
                self.status = MoveStatus.FAILED
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
                            self.h.reset_stretchPos()
                            return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.stretchReset(r)
                    self.h.reset_stretchPos()
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
                            if abs(pos - 1) < 0.1 and abs(device_state["leftStatus"] - 1) < 0.1 and abs(device_state["rightStatus"] - 1) < 0.1:
                                self.finger_status = MoveStatus.FINISHED
                                self.h.reset_fingerPos()
                                return True
                            elif abs(pos) < 0.1 and abs(device_state["leftStatus"]) < 0.1 and abs(device_state["rightStatus"]) < 0.1:
                                self.finger_status = MoveStatus.FINISHED
                                self.h.reset_fingerPos()
                                return True                    
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.ERROR or device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.fingerReset(r)
                    self.h.reset_fingerPos()
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.fingerPos(pos,r)
                    self.state["res"] = res
        return False
    def record_vision(self, r):
        res = self.h.visionRecord(r)
        self.state["record_vision_res"] = res    
        self.h.reset_visionRecord()        
    def vision(self, r, vtype, binType, binModel):
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
                            self.h.reset_visionReq()
                        elif device_state["state"] == Hairou.ModuleState.IDLE:
                            if self.waitVision.status == MoveStatus.NONE:
                                self.waitVision.reset()
                            self.waitVision.run(r,self)
                            if self.waitVision.status == MoveStatus.FINISHED:
                                res = dict()
                                if vtype == "shelf":
                                    binType = "code"
                                    res = self.h.visionReq(Hairou.TargetType.SHELF.value,
                                                           Hairou.BinType.DM_MARKED.value, Hairou.BinModel.PLASTICBOX,r)
                                elif vtype == "box":
                                    if binType == "code":
                                        res = self.h.visionReq(Hairou.TargetType.BOX.value, 
                                                               Hairou.BinType.DM_MARKED.value,Hairou.BinModel.PLASTICBOX, r)
                                    elif binType == "markerless":
                                        if binModel == "carton":
                                            res = self.h.visionReq(Hairou.TargetType.BOX.value, 
                                                                   Hairou.BinType.MARKERLESS.value,Hairou.BinModel.CARTON,r) 
                                        else:
                                            res = self.h.visionReq(Hairou.TargetType.BOX.value, 
                                                                   Hairou.BinType.MARKERLESS.value,Hairou.BinModel.PLASTICBOX,r)
                                    elif binType == "barcode":
                                        res = self.h.visionReq(Hairou.TargetType.BOX.value, Hairou.BinType.BARCODE.value,
                                                               Hairou.BinModel.PLASTICBOX,r)
                                    else:
                                        r.setError("visionBinType Type is wrong: {}".format(binType))
                                        self.vision_status = MoveStatus.FAILED
                                else:
                                    res["error"] = "wrong type {}".format(vtype)
                                    res["flag"] = False
                                    self.vision_status = MoveStatus.FAILED
                                self.state["res"] = res
                                if res.get("status", Hairou.Action.INIT) is Hairou.Action.FINISHED:
                                    self.h.reset_visionReq()
                                    if binType == "barcode" and "binId" in res['res']:
                                        res = res['res']
                                        self.vision_status = MoveStatus.FINISHED
                                        self.waitVision.status = MoveStatus.NONE
                                        out1 = dict()
                                        yaw, pitch, roll, dx , dy, dz, dist = 0, 0, 0, 0, 0, 0, 0
                                        out1["yaw"] = yaw * 180.0/math.pi
                                        out1["pitch"] = pitch * 180.0/math.pi
                                        out1["roll"] = roll * 180.0/math.pi
                                        out1["dx"] = dx
                                        out1["dy"] = dy
                                        out1["dz"] = dz
                                        out1["dist"] = dist
                                        res["vout"] = out1
                                        res["targetType"] = vtype
                                        res["binType"] = binType   
                                        res["binId"] = res['binId']
                                        r.setNotice(json.dumps(res))
                                        return res
                                    elif "positionMatrix" in res['res']:
                                        res = res['res']
                                        self.vision_status = MoveStatus.FINISHED
                                        self.waitVision.status = MoveStatus.NONE
                                        yaw, pitch, roll, dx , dy, dz, dist = 0, 0, 0, 0, 0, 0, 0
                                        positionMatrix = [res["positionMatrix"]] 
                                        if vtype == "shelf" or (vtype == "box" and binType == "code"):
                                            yaw, pitch, roll, dz , dy, dx, dist = getYPRZYX_code(positionMatrix, self.state["rotate"]["position"])
                                            yaw = yaw + math.pi/2.0
                                            roll = roll - math.pi/2.0
                                        elif vtype == "box" and binType == "markerless":
                                            yaw, pitch, roll, dz , dy, dx, dist = getYPRZYX_markerless(positionMatrix, self.state["rotate"]["position"])
                                        else:
                                            r.setError("visionBinType Type is wrong: {}".format(binType))
                                            self.vision_status = MoveStatus.FAILED
                                        out1 = dict()
                                        out1["yaw"] = yaw * 180.0/math.pi
                                        out1["pitch"] = pitch * 180.0/math.pi
                                        out1["roll"] = roll * 180.0/math.pi
                                        out1["dx"] = dx
                                        out1["dy"] = dy
                                        out1["dz"] = dz
                                        out1["dist"] = dist
                                        res["vout"] = out1
                                        res["targetType"] = vtype
                                        res["binType"] = binType    
                                        res["binId"] = "" 
                                        res["dist"] = dist                     
                                        r.setNotice(json.dumps(res))
                                        self.state["vision"] = res
                                        return res
                                    else:
                                        self.vision_status = MoveStatus.FAILED
                                        r.setError("rec no results. {}".format(json.dumps(res)))
        return dict()       
    def indicator(self, r, chassisLedFront = None, chassisLedBack = None, buzzer = None, headLedRed = None, headLedYellow = None, headLedGreen = None, headLedFreq = None):
        res = self.h.indicatorReq(chassisLedFront,chassisLedBack,buzzer,headLedRed,headLedYellow,headLedGreen,headLedFreq,r)
        self.state["res"] = res
        if res['status'] is not Hairou.Action.FINISHED:
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
                recAdjust(self.task["visionType"], self.task["visionBinType"], 
                          self.task.get("binModel", "plasticbox"), self.rec_offz_box, self.rec_offz_shelf)
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
                    if "visionBinType" not in self.task:
                        self.task["visionBinType"] = "code"
                    self.task_list = [
                        preGoods(self.task["lift"], self.task["rotate"]),
                        recAdjust(self.task["visionType"], self.task["visionBinType"], 
                                  self.task.get("binModel", "plasticbox"), self.rec_offz_box, self.rec_offz_shelf),
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
                    if "visionBinType" not in self.task:
                        self.task["visionBinType"] = "code"
                    self.task_list = [
                        preGoods(self.low[int(self.task["selfPosition"])], 0),
                        getGoods(self.stretchDist),
                        prePutGoods(self.task["lift"], self.task["rotate"]),
                        recAdjust(self.task["visionType"], self.task["visionBinType"], 
                                  self.task.get("binModel", "plasticbox"), self.rec_offz_box, self.rec_offz_shelf),
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
        elif self.lift_status is not MoveStatus.FINISHED:
            self.h.liftReset(r)
            self.lift(r, 385)
        elif self.rotate_status is not MoveStatus.FINISHED:
            self.h.rotateReset(r)
            self.rotate(r, 0)
        else:
            self.operation_status = MoveStatus.FINISHED
    def stop(self,r):
        if self.lift_status is MoveStatus.RUNNING:
            self.h.liftStop(r)
        if self.stretch_status is MoveStatus.RUNNING:
            self.h.stretchStop(r)
        if self.rotate_status is MoveStatus.RUNNING:
            self.h.rotateStop(r)
        if self.finger_status is MoveStatus.RUNNING:
            self.h.fingerStop(r)
        if self.vision_status is MoveStatus.RUNNING:
            self.h.visionStop(r)
    def cancel(self, r:SimModule):
        r.logInfo("script cancel")
        self.stop(r)
        self.h.disconnect()
        self.status = MoveStatus.NONE
    def suspend(self, r:SimModule):
        self.stop(r)
        if self.stretch_status is not MoveStatus.FINISHED \
        and self.stretch_status is not MoveStatus.NONE:
            self.stretch_status = MoveStatus.RUNNING
        if self.lift_status is not MoveStatus.FINISHED \
        and self.lift_status is not MoveStatus.NONE:
            self.lift_status = MoveStatus.RUNNING
        if self.rotate_status is not MoveStatus.FINISHED \
        and self.rotate_status is not MoveStatus.NONE:
            self.rotate_status = MoveStatus.RUNNING
        if self.finger_status is not MoveStatus.FINISHED \
        and self.finger_status is not MoveStatus.NONE:
            self.finger_status = MoveStatus.RUNNING
        if self.vision_status is not MoveStatus.FINISHED \
        and self.vision_status is not MoveStatus.NONE:
            self.vision_status = MoveStatus.RUNNING
        if self.operation_status is not MoveStatus.FINISHED \
        and self.operation_status is not MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
        self.h.resetAll()
        r.logInfo("script suspended")
        self.status = MoveStatus.SUSPENDED
        self.start_connect_time = time.time()
        self.state = self.h.getReport(r)
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


class recAdjust:
    def __init__(self, visionType, visionBinType, binModel, rec_offz_box, rec_offz_shelf):
        self.status = MoveStatus.NONE
        self.visionType = visionType
        self.visionBinType = visionBinType
        self.binModel = binModel
        self.dtheta = 0 #角度方向
        self.dist = 0 #侧向
        self.dz = 0 #垂直方向
        p = ParamServer(__file__)
        self.max_rec_times = p.loadParam("max_rec_times", type="int", default = 10, maxValue = 999999, minValue = 0, comment = "最多识别次数")
        self.max_adjust_time = p.loadParam("max_adjust_time", type="int", default = 10, maxValue = 999999, minValue = 0, comment = "最多调整次数")
        self.rec_shelf_shift = p.loadParam("rec_shelf_shift", type="float", default = 10.0, maxValue = 1000.0, minValue = -1000.0, unit = "mm", comment = "识别货架时相机距离二维码的z方向偏差")
        self.rec_count = 0
        self.offz_box = rec_offz_box
        self.offz_shelf = rec_offz_shelf
        self.lift_pos = 0
        self.rot_theta = 0
        self.go_args = dict()
        self.adjust_count = 0
        self.ok = False
        self.first_adj = True
    def reset(self, ctu):
        ctu.vision_status = MoveStatus.NONE
        ctu.rotate_status = MoveStatus.NONE
        ctu.lift_status = MoveStatus.NONE
        self.dtheta = 0
        self.dist = 0
        self.dz = 0
        self.rec_count = 0
        ctu.goPath.reset()
        self.status = MoveStatus.RUNNING
        self.lift_pos = 0
        self.rot_theta = 0
        self.go_args = dict()
        self.adjust_count = 0
        self.ok = False
        self.first_adj = True
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.vision_status is not MoveStatus.FINISHED:
            if self.rec_count < self.max_rec_times:
                if ctu.vision_status == MoveStatus.FAILED:
                    self.rec_count = self.rec_count + 1
                res = ctu.vision(r, self.visionType, self.visionBinType, self.binModel)
                method = "vout"
                if ctu.vision_status == MoveStatus.FINISHED:
                    dist, dz, dtheta = 0, 0, 0
                    if self.visionBinType == "code":
                        dz = res[method]["dz"]
                        dist = res[method]["dist"]
                        dtheta = res[method]["yaw"]
                    elif self.visionBinType == "markerless":
                        dz = 0
                        dist = res[method]["dist"]
                        dtheta = res[method]["yaw"]
                    else:
                        r.setError(" binType error: {}".format(self.visionBinType))
                        ctu.vision_status = MoveStatus.FAILED
                        self.status = MoveStatus.FAILED
                    if abs(dtheta) < 8:
                        self.dtheta = dtheta * math.pi /180.0
                        self.dz = dz
                        self.dist = dist
                        if self.adjust_count >= self.max_adjust_time:
                            self.operation_status = MoveStatus.FAILED
                            r.setError("recAdjust fails!!! reach max times.")
                        else:
                            self.go_args["coordinate"] = "robot"
                            self.go_args["x"] = self.dist
                            self.go_args["y"] = 0
                            self.go_args["theta"] = 0
                            self.go_args["reachAngle"] = math.pi
                            if "useLoc" not in ctu.task:
                                self.go_args["useOdo"] = 1
                            self.go_args["reachDist"] = 0.002
                            if self.go_args["x"] < 0:
                                self.go_args["backMode"] = 1
                            self.rot_theta = ctu.state["rotate"]["position"] + self.dtheta
                            ok_x = 0.012
                            ok_theta = 0.02
                            if self.visionBinType == "markerless" or self.visionType == "shelf":
                                ok_x = 0.02
                                ok_theta = 0.035
                            if abs(self.go_args["x"]) < ok_x and abs(self.dtheta) < ok_theta and not self.first_adj:
                                self.ok = True 
                                self.lift_pos = ctu.state["lift"]["position"]
                                if self.visionType == "shelf":
                                    self.lift_pos = self.lift_pos + self.dz * 1000 + self.offz_shelf
                                elif self.visionType == "box" and self.visionBinType == "code":
                                    self.lift_pos = self.lift_pos + self.dz * 1000 + self.offz_box
                                elif self.visionType == "box" and self.visionBinType == "markerless":
                                    ctu.lift_status = MoveStatus.FINISHED
                            else:
                                self.first_adj = False
                                self.lift_pos = ctu.state["lift"]["position"]
                                if self.visionType == "shelf":
                                    self.lift_pos = self.lift_pos + self.dz * 1000 + self.rec_shelf_shift
                                elif self.visionType == "box" and self.visionBinType == "code":
                                    self.lift_pos = self.lift_pos + self.dz * 1000
                                elif self.visionType == "box" and self.visionBinType == "markerless":
                                    ctu.lift_status = MoveStatus.FINISHED                           
                    else:
                        ctu.record_vision(r)
                        r.setNotice(" yaw is too large: {}".format(res[method]["yaw"]))
                        ctu.vision_status = MoveStatus.NONE
                        self.status = MoveStatus.RUNNING
            else:
                r.setError("rec fails!!! reach max times.")
                self.status = MoveStatus.FAILED
        else:
            if self.ok:
                if ctu.lift_status != MoveStatus.FINISHED:
                    ctu.lift(r,self.lift_pos)
                if ctu.lift_status == MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
                elif ctu.lift_status == MoveStatus.FINISHED:
                    ctu.rotate_status = MoveStatus.FINISHED
                    ctu.goPath.status = MoveStatus.FINISHED
                    self.status = MoveStatus.FINISHED
            else:
                if ctu.lift_status is not MoveStatus.FINISHED:
                    ctu.lift(r,self.lift_pos)
                if ctu.goPath.status != MoveStatus.FINISHED and ctu.goPath.status != MoveStatus.FAILED:
                        if abs(self.go_args["x"]) < 0.003:
                            ctu.goPath.status = MoveStatus.FINISHED
                        else:
                            ctu.goPath.run(r,self.go_args)
                if ctu.rotate_status != MoveStatus.FINISHED:
                    ctu.rotate(r,self.rot_theta)
                if ctu.lift_status == MoveStatus.FAILED \
                    or ctu.goPath.status == MoveStatus.FAILED \
                        or ctu.rotate_status == MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
                elif ctu.lift_status == MoveStatus.FINISHED \
                    and ctu.goPath.status == MoveStatus.FINISHED \
                        and ctu.rotate_status == MoveStatus.FINISHED:
                    self.adjust_count = self.adjust_count + 1
                    ctu.vision_status = MoveStatus.NONE
                    ctu.rotate_status = MoveStatus.NONE
                    ctu.lift_status = MoveStatus.NONE
                    self.dtheta = 0
                    self.dist = 0
                    self.dz = 0
                    self.rec_count = 0
                    ctu.goPath.reset()
                    self.status = MoveStatus.RUNNING
                    self.lift_pos = 0
                    self.rot_theta = 0
                    self.go_args = dict()
        cur_state = dict()
        cur_state["dz"] = self.dz
        cur_state["dist"] = self.dist
        cur_state["dtheta"] = self.dtheta
        cur_state["goaPathStatus"] = ctu.goPath.status
        cur_state["lift_pos"] = self.lift_pos
        cur_state["go_args"] = self.go_args
        cur_state["rot_theta"] = self.rot_theta
        cur_state["adj_count"] = self.adjust_count
        cur_state["visionType"] = self.visionType
        cur_state["binType"] = self.visionBinType
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
    m.suspend(r)
    data = dict()
    data["headLedFreq"] = dict()
    data["headLedFreq"]["value"] = "1"
    print(m.run(r, data))