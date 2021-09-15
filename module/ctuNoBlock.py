import pickingRobot as Hairou
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
    "recBoxLift":{
        "value": 0,
        "tips": "卸货时，识别料箱时，货叉的高度",
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
        "load","unload","change","zero","wait","getMarkerPos","put"
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
    "putPosition":{
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
    },
    "unloadHeight":{
        "value": 0,
        "tips": "rec_offz_shelf",
        "type": "double",
        "unit": "mm"
    },
    "loadHeight":{
        "value": 0,
        "tips": "rec_offz_box",
        "type": "double",
        "unit": "mm"
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
    Tm2box = [[0.,-1.,0.,0.],
              [0.,0.,1.,0.],
              [-1.,0.,0.,0.],
              [0.,0.,0.,1.]]
    Tc2m_now = matrixReshape(p, 4, 4)
    Tf2m_now = matrixDot(Tf2c,Tc2m_now, 4, 4, 4)
    # newp = matrixReshape(Tf2m_now, 1, 16)[0]
    # yaw, pitch, roll, dz, dy, dx = getYPRZYX(newp)
    Tagv2m_now = matrixDot(Tagv2f,Tf2m_now, 4, 4, 4)
    Tagv2box = matrixDot(Tagv2m_now, Tm2box,4, 4, 4)
    Tf2box = matrixDot(Tf2m_now, Tm2box, 4,4,4)
    boxX = [[1.],[0.],[0.],[1.]]
    boxX2agv = matrixDot(Tagv2box, boxX,4,4,1)
    angle_agv = math.atan2(boxX2agv[1][0] - Tagv2box[1][3], boxX2agv[0][0] - Tagv2box[0][3])
    dx = Tagv2box[0][3]
    dy = Tagv2box[1][3]
    dz = Tagv2box[2][3]
    #pf2box， box在理想货叉坐标系中的位置
    pf2box_ideal = [[Tf2box[0][3]],[0],[Tf2box[2][3]],[1]]
    print(pf2box_ideal)
    Tagv2f_ideal = [[math.cos(angle_agv), -math.sin(angle_agv), 0., 0.],
                    [math.sin(angle_agv), math.cos(angle_agv), 0., 0.],
                    [0.,0.,1.,0.],
                    [0.,0.,0.,1.]] 
    pagv2box_ideal = matrixDot(Tagv2f_ideal, pf2box_ideal, 4 ,4 ,1)
    dist = Tagv2box[0][3] - pagv2box_ideal[0][0] 
    return  angle_agv, dx, dy, dz, dist, Tagv2box

def getMarkerInWorld(loc, Tagv2m):
    Tw2agv = [[math.cos(loc[2]), -math.sin(loc[2]), 0., loc[0]],
              [math.sin(loc[2]), math.cos(loc[2]), 0., loc[1]],
              [0.,0.,1.,0.],
              [0.,0.,0.,1.]]
    Tw2m = matrixDot(Tw2agv, Tagv2m, 4, 4, 4)
    return Tw2m

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
    # newp = matrixReshape(Tf2box, 1,16)[0]
    # yaw, pitch, roll, dz, dy, dx = getYPRZYX(newp)
    Tagv2box = matrixDot(Tagv2f,Tf2box, 4, 4, 4)
    boxX = [[1.],[0.],[0.],[1.]]
    boxX2agv = matrixDot(Tagv2box, boxX,4,4,1)
    angle_agv = math.atan2(boxX2agv[1][0] - Tagv2box[1][3], boxX2agv[0][0] - Tagv2box[0][3])
    dx = Tagv2box[0][3]
    dy = Tagv2box[1][3]
    dz = Tagv2box[2][3]
    #pf2box， box在理想货叉坐标系中的位置
    pf2box_ideal = [[Tf2box[0][3]],[0],[Tf2box[2][3]],[1]]
    Tagv2f_ideal = [[math.cos(angle_agv), -math.sin(angle_agv), 0., 0.],
                    [math.sin(angle_agv), math.cos(angle_agv), 0., 0.],
                    [0.,0.,1.,0.],
                    [0.,0.,0.,1.]] 
    pagv2box_ideal = matrixDot(Tagv2f_ideal, pf2box_ideal, 4 ,4 ,1)
    dist = Tagv2box[0][3] - pagv2box_ideal[0][0] 
    return angle_agv, dx, dy, dz, dist, Tagv2box

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
        self.maxStretchDist = p.loadParam("max_stretch_dist", type="float", default=920.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "stretch_max_dist")
        self.init = True
        self.task = dict()
        self.low = dict({0:740, 1:1130, 2:1520, 3:1910, 4:2300}) #mm
        #此处在背篓取货时需要略低于背篓的高度，此处所更改的数值为默认值，需要在"ctuNoBlock.json"文件里修改才是最终执行的高度
        self.low[0] = p.loadParam("low0", type="float", default = 397.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第0层高度")
        self.low[1] = p.loadParam("low1", type="float", default = 907.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第1层高度")
        self.low[2] = p.loadParam("low2", type="float", default = 1417.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第2层高度")
        self.low[3] = p.loadParam("low3", type="float", default = 1927.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第3层高度")
        self.low[4] = p.loadParam("low4", type="float", default = 2437.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第4层高度")
        self.low[5] = p.loadParam("low5", type="float", default = 2947.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "取货时，第5层高度")
        self.high = dict({0:407, 1:917, 2:1427, 3:1937, 4:2447, 5:2957}) #mm
        #此处在背篓放货时需要略高于背娄的高度，此处所更改的数值为默认值，需要在"ctuNoBlock.json"文件里修改才是最终执行的高度
        self.high[0] = p.loadParam("high0", type="float", default = 407.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第0层高度")
        self.high[1] = p.loadParam("high1", type="float", default = 917.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第1层高度")
        self.high[2] = p.loadParam("high2", type="float", default = 1427.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第2层高度")
        self.high[3] = p.loadParam("high3", type="float", default = 1937.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第3层高度")
        self.high[4] = p.loadParam("high4", type="float", default = 2447.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第4层高度")
        self.high[5] = p.loadParam("high5", type="float", default = 2957.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放货时，第5层高度")
        #此处修改的是默认值，最终执行请在“ctuNoBlock.json"里进行更改
        self.stretchDist = p.loadParam("stretchDist", type="float", default = 716, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "放在自己货架上，抽屉伸出长度")
        #此处修改的是默认值，最终执行请在“ctuNoBlock.json"里进行更改
        self.rec_offz_box = p.loadParam("rec_offz_box", type="float", default = -80.0, maxValue = 1000.0, minValue = -1000.0, unit = "mm", comment = "识别货物后，抓货物时高度的调整距离")
         #此处修改的是默认值，最终执行请在“ctuNoBlock.json"里进行更改
        self.rec_offz_shelf = p.loadParam("rec_offz_shelf", type="float", default = 50.0, maxValue = 1000.0, minValue = -1000.0, unit = "mm", comment = "识别货架后，放货物时高度的调整距离")
        self.fork_up_limit = p.loadParam("fokr_up_limit", type="int", default = 4, maxValue = 100, minValue = -1, unit = "", comment = "货叉上限位DI")
        self.fork_down_limit = p.loadParam("fork_down_limit", type="int", default = 2, maxValue = 100, minValue = -1, unit = "", comment = "货叉下限位DI")
        self.minLiftHeight = p.loadParam("min_fork_height", type="float", default=400.0, maxValue = 10000.0, minValue = 0.0, unit = "mm", comment = "货叉最低高度")
        self.fork_limit = p.loadParam("fork_limit", type="int", default = 1, maxValue = 100, minValue = -1, unit = "", comment = "货叉机械限位限位DI")
        self.loadOffset = p.loadParam("loadOffset", type="float", default=0.0, maxValue = 500.0, minValue = -500.0, unit = "mm", comment = "load货物时，货叉额外伸出的距离")
        
        self.stretch_status = MoveStatus.NONE
        self.lift_status = MoveStatus.NONE
        self.rotate_status = MoveStatus.NONE
        self.finger_status = MoveStatus.NONE
        self.vision_status = MoveStatus.NONE
        self.indicator_status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.getMarkerPos_status = 0 # 0识别获得了位姿， 1获得id, 2保持结果TotTime
        self.getMarkerPos_data = dict()
        self.getMarkerPosTotTime = 5.0
        self.getMarkerStartTime = time.time()
        self.task_list = []
        self.task_id = 0
        self.state = dict()
        self.goPath = goPath.Module(r, args)
        self.waitVision = waitVision()
        self.waitVision.status = MoveStatus.NONE
        self.unloadHeight = self.rec_offz_shelf
        self.loadHeight = self.rec_offz_box
        self.h.connect()
    def run(self, r:SimModule,args):
        if r.errorExits(52111):
            self.status = MoveStatus.FAILED
            return self.status.value
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.task = args
            if "unloadHeight" in self.task:
                self.unloadHeight = self.task["unloadHeight"]
            if "loadHeight" in self.task:
                self.loadHeight = self.task["loadHeight"]
        if not self.h.isconnect:
            self.state["init"] = self.h.initDevice(r)
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
            self.state['pickingRobotInfo'] = self.h.report
            r.setInfo(json.dumps(self.state))

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
            r.logDebug("first in script {}".format(self.task.get("_script_first_run_", False)))
            if self.task.get("_script_first_run_", False) is True:
                self.vision_status = MoveStatus.FINISHED
                self.zero(r)
            elif "operation" in self.task and self.task["operation"] == "load":
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
            elif "operation" in self.task and self.task["operation"] == "put":
                if "putPosition" in self.task:
                    self.vision_status = MoveStatus.FINISHED
                    self.putPos(r)
                else:
                    r.setError("task is wrong : {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED                
            elif "operation" in self.task and self.task["operation"] == "zero":
                self.vision_status = MoveStatus.FINISHED
                self.zero(r)
            elif "operation" in self.task and self.task["operation"] == "getMarkerPos":
                self.stretch_status = MoveStatus.FINISHED
                self.lift_status = MoveStatus.FINISHED
                self.rotate_status = MoveStatus.FINISHED
                self.finger_status = MoveStatus.FINISHED
                self.indicator_status = MoveStatus.FINISHED
                self.getMarkerPos(r)
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
                                    self.stop(r)
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
        if "_script_first_run_" in self.task \
            and self.task["_script_first_run_"] == True\
            and self.status is MoveStatus.FINISHED:
            self.task["_script_first_run_"] = False
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
        try:
            r.logDebug("[HaiRou][{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}]".format(
            self.state["lift"]["position"],self.state["lift"]["state"], self.state["lift"]["speed"],
            self.state["rotate"]["position"],self.state["rotate"]["state"], self.state["rotate"]["speed"],
            self.state["stretch"]["position"],self.state["stretch"]["state"], self.state["stretch"]["speed"],
            self.state["finger"]["leftStatus"],self.state["finger"]["rightStatus"], self.state["finger"]["state"],
            self.state["vision"]["state"]))
        except KeyError as e:
            r.logDebug("KeyError: "+str(e))
        except Exception as e:
            r.logDebug("Other error in print hairou state")
    
        try:
            if "forkDetect" in self.state :
                log_key = "HaiRou_forkDetect"
                log_str = ""
                for fork in self.state["forkDetect"]:
                    tmp_str = "{}|{}|{}|".format(fork["id"],fork["state"],fork["state"])
                    log_str = log_str+tmp_str
                r.logDebug("[{}][{}]".format(log_key, log_str))
        except KeyError as e:
            r.logDebug("KeyError: "+str(e))
        except Exception as e:
            r.logDebug("Other error in print hairou forkDetect state")
    
        try:
            if "trays" in self.state:
                log_key = "HaiRou_trays"
                log_str = ""
                for trays in self.state["trays"]:
                    tmp_str = "{}|{}|{}|".format(trays["id"],trays["state"],trays["state"])
                    log_str = log_str+tmp_str
                r.logDebug("[{}][{}]".format(log_key, log_str))
        except KeyError as e:
            r.logDebug("KeyError: "+str(e))
        except Exception as e:
            r.logDebug("Other error in print hairou trays state")

        return self.status.value
    def lift(self, r, height, clear_error = False):
        self.lift_status = MoveStatus.RUNNING
        if height < self.minLiftHeight:
            r.logDebug("lift {} is set to {}".format(height, self.minLiftHeight))
            height = self.minLiftHeight
        if "lift" in self.state:
            dis = r.Di()
            upLimit = False
            downLimit = False
            forkLimit = False
            for node in dis['node']:
                if node['id'] == self.fork_up_limit:
                    status = node.get('status',False)
                    if status:
                        upLimit = True
                elif node['id'] == self.fork_down_limit:
                    status = node.get('status',False)
                    if status:
                        downLimit = True
                elif node['id'] == self.fork_limit:
                    status = node.get('status',False)
                    if status:
                        forkLimit = True
            device_state = self.state["lift"]
            if upLimit and device_state["position"] < height:
                r.setError("fork upLimit DI is True. Cannot up!")
                self.lift_status = MoveStatus.FAILED
                self.status = MoveStatus.FAILED
            elif downLimit and device_state["position"] > height:
                r.setError("fork downLimit DI is True. Cannot down!")
                self.lift_status = MoveStatus.FAILED
                self.status = MoveStatus.FAILED
            elif forkLimit:
                r.setError("fork limitDi is True.Cannot Move!")
                self.stop(r)
                self.lift_status = MoveStatus.FAILED
                self.status = MoveStatus.FAILED
            elif "stretch" in self.state and self.state["stretch"]["position"] < 10:
                if "position" in device_state and "state" in device_state:
                    if abs(device_state["position"] - height) < self.lift_reach_dist  \
                        and device_state["state"] == Hairou.ModuleState.IDLE:
                            self.lift_status = MoveStatus.FINISHED
                            self.h.reset_liftPos()
                            return True
                if "state" in device_state:
                    if device_state["state"] == Hairou.ModuleState.INIT:
                        res = self.h.liftReset(r)
                        self.h.reset_liftPos()
                        self.state["res"] = res
                    elif device_state["state"] == Hairou.ModuleState.IDLE:
                        res = self.h.liftPos(height,r)
                        self.state["res"] = res
                    elif device_state["state"] == Hairou.ModuleState.ERROR:
                        if clear_error:
                            res = self.h.liftReset(r)
                            self.h.reset_liftPos()
                            self.state["res"] = res
                        else:
                            r.setError("Lift has error. Please zero the machine!")
                            self.stretch_status = MoveStatus.FAILED                          
            else:
                r.setError("stretch pos is not zero cannot lift.!!! {}".format(self.state["stretch"]["position"]))
                self.lift_status = MoveStatus.FAILED
                self.status = MoveStatus.FAILED
        return False
    def rotate(self, r, theta, clear_error = False):
        self.rotate_status = MoveStatus.RUNNING
        theta = normalize_theta(theta)
        if theta < -3.0:
            theta = 2 *math.pi + theta
        if "rotate" in self.state:
            if "stretch" in self.state and self.state["stretch"]["position"] < 10:
                device_state = self.state["rotate"]
                if "position" in device_state and "state" in device_state:
                    if abs(normalize_theta(device_state["position"] - theta)) < self.rotate_reach_angle \
                        and device_state["state"] == Hairou.ModuleState.IDLE:
                            self.rotate_status = MoveStatus.FINISHED
                            self.h.reset_rotateAngle()
                            return True
                if "state" in device_state:
                    if device_state["state"] == Hairou.ModuleState.INIT:
                        res = self.h.rotateReset(r)
                        self.h.reset_rotateAngle()
                        self.state["res"] = res
                    elif device_state["state"] == Hairou.ModuleState.IDLE:
                        res = self.h.rotateAngle(theta,r)
                        self.state["res"] = res
                    elif device_state["state"] == Hairou.ModuleState.ERROR:
                        if clear_error:
                            res = self.h.rotateReset(r)
                            self.h.reset_rotateAngle()
                            self.state["res"] = res
                        else:
                            r.setError("Rotate has error. Please zero the machine!")
                            self.stretch_status = MoveStatus.FAILED                           
            else:
                self.rotate_status = MoveStatus.FAILED
                self.status = MoveStatus.FAILED
                r.setError("stretch pos is not zero cannot rotate.!!! {}".format(self.state["stretch"]["position"]))
        return False       
    def stretch(self, r, pos, clear_error = False):
        if pos > self.maxStretchDist:
            r.setError("reach max stretch dist!")
            self.stretch_status = MoveStatus.FAILED
            return False
        self.stretch_status = MoveStatus.RUNNING
        if "stretch" in self.state:
            device_state = self.state["stretch"]
            if "position" in device_state and "state" in device_state:
                if abs(device_state["position"] - pos) < self.stretch_reach_dist \
                    and device_state["state"] == Hairou.ModuleState.IDLE:
                        self.stretch_status = MoveStatus.FINISHED
                        self.h.reset_stretchPos()
                        return True
            if "state" in device_state:
                if device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.stretchReset(r)
                    self.h.reset_stretchPos()
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.stretchPos(pos,r)
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.ERROR:
                    if clear_error:
                        res = self.h.stretchReset(r)
                        self.h.reset_stretchPos()
                        self.state["res"] = res
                    else:
                        r.setError("Stretch has error. Please zero the machine!")
                        self.stretch_status = MoveStatus.FAILED      
        return False 
    def checkFingerStatus(self,r, state):
        if "finger" in self.state:
            device_state = self.state["finger"]
            if device_state.get("state",-1) != Hairou.ModuleState.IDLE:
                r.setError("Finger status is not idle. Ctu cannot lift or rotate or stretch!")
                self.finger_status = MoveStatus.FAILED
                return False
            # if device_state.get("leftStatus",-1) != device_state.get("rightStatus",-1):
            #     r.setError("Finger left and right status is not same. Ctu cannot  lift or rotate or stretch! {}, {}".format(
            #         device_state.get("leftStatus",-1), device_state.get("rightStatus",-1)
            #     ))
            #     self.finger_status = MoveStatus.FAILED
            #     return False
            # if abs(device_state.get("leftStatus",-1)- state) > 0.1 \
            # or abs(device_state.get("rightStatus",-1) - state) > 0.1:
            #     r.setError(f"Finger left and right status is not right! Ctu cannot lift or rotate or stretch! {state}")
            #     self.finger_status = MoveStatus.FAILED
            #     return False
        else:
            r.setError(f"No finger in message! Ctu cannot lift or rotate or stretch!")
            self.finger_status = MoveStatus.FAILED
            return False            
    def finger(self, r, pos, clear_error = False):
        self.finger_status = MoveStatus.RUNNING
        if "finger" in self.state:
            device_state = self.state["finger"]
            if "leftStatus" in device_state and "state" in device_state \
                    and device_state["state"] != Hairou.ModuleState.ERROR \
                        and device_state["state"] != Hairou.ModuleState.INIT \
                            and device_state["state"] != Hairou.ModuleState.RESET:
                            if abs(pos - 1) < 0.1 \
                            and abs(device_state["leftStatus"] - 1) < 0.1 \
                            and abs(device_state["rightStatus"] - 1) < 0.1 \
                            and device_state["state"] == Hairou.ModuleState.IDLE:
                                self.finger_status = MoveStatus.FINISHED
                                self.h.reset_fingerPos()
                                return True
                            elif abs(pos) < 0.1 \
                            and abs(device_state["leftStatus"]) < 0.1 \
                            and abs(device_state["rightStatus"]) < 0.1 \
                            and device_state["state"] == Hairou.ModuleState.IDLE:
                                self.finger_status = MoveStatus.FINISHED
                                self.h.reset_fingerPos()
                                return True                    
            if "state" in device_state:
                if  device_state["state"] == Hairou.ModuleState.INIT:
                    res = self.h.fingerReset(r)
                    self.h.reset_fingerPos()
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.IDLE:
                    res = self.h.fingerPos(pos,r)
                    self.state["res"] = res
                elif device_state["state"] == Hairou.ModuleState.ERROR:
                    if clear_error:
                        res = self.h.fingerReset(r)
                        self.h.reset_fingerPos()   
                        self.state["res"] = res  
                    else:
                        r.setError("Finger has error. Please zero the machine!")
                        self.finger_status = MoveStatus.FAILED
        return False
    def record_vision(self, r):
        res = self.h.visionRecord(r)
        self.state["record_vision_res"] = res    
        self.h.reset_visionRecord()        
    def vision(self, r, vtype, binType, binModel, recgo = False):
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
                        if device_state["state"] == Hairou.ModuleState.INIT:
                            self.h.visionReset(r)
                            self.h.reset_visionReq()
                            self.waitVision.reset()
                        elif device_state["state"] == Hairou.ModuleState.ERROR:
                            self.h.visionReset(r)
                            self.h.reset_visionReq()
                            self.waitVision.reset()
                            self.vision_status = MoveStatus.FAILED
                            if not recgo:
                                r.setError("rec no results.")
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
                                        r.setNotice(json.dumps(res))
                                        return res
                                    elif "positionMatrix" in res['res']:
                                        res = res['res']
                                        self.vision_status = MoveStatus.FINISHED
                                        self.waitVision.status = MoveStatus.NONE
                                        yaw, pitch, roll, dx , dy, dz, dist = 0, 0, 0, 0, 0, 0, 0
                                        positionMatrix = [res["positionMatrix"]]
                                        Tagv2box = [] 
                                        if vtype == "shelf" or (vtype == "box" and binType == "code"):
                                            pass
                                            yaw, dx , dy, dz,dist, Tagv2box = getYPRZYX_code(positionMatrix, self.state["rotate"]["position"])
                                            # yaw = yaw + math.pi/2.0
                                            # roll = roll - math.pi/2.0
                                        elif vtype == "box" and binType == "markerless":
                                            yaw, dx , dy, dz, dist, Tagv2box = getYPRZYX_markerless(positionMatrix, self.state["rotate"]["position"])
                                        else:
                                            r.setError("visionBinType Type is wrong: {}".format(binType))
                                            self.vision_status = MoveStatus.FAILED
                                        out1 = dict()
                                        out1["yaw"] = yaw * 180.0/math.pi
                                        out1["dx"] = dx
                                        out1["dy"] = dy
                                        out1["dz"] = dz
                                        out1["dist"] = dist
                                        out1["Ta2b"] = Tagv2box
                                        res["vout"] = out1
                                        res["targetType"] = vtype
                                        res["binType"] = binType    
                                        res["binId"] = "" 
                                        if "operation" in self.task and self.task["operation"] == "getMarkerPos":  
                                            loc_org = r.loc()
                                            loc = [loc_org["x"],loc_org["y"],loc_org["angle"]]
                                            Tw2box = getMarkerInWorld(loc, Tagv2box)
                                            boxX = [[1],[0],[0],[1]]
                                            boxX2w = matrixDot(Tw2box, boxX, 4, 4,1)
                                            angle_world = math.atan2(boxX2w[1][0] -Tw2box[1][3], boxX2w[0][0]-Tw2box[0][3])
                                            res["x"] = Tw2box[0][3]
                                            res["y"] = Tw2box[1][3]
                                            res["theta"] = angle_world       
                                        r.setNotice(json.dumps(res))
                                        self.state["res"] = res
                                        return res
                                    else:
                                        self.vision_status = MoveStatus.FAILED
                                        if not recgo:
                                            r.setError("rec no results. {}".format(json.dumps(res)))
        return dict()
    def getMarkerPos(self, r):
        self.operation_status = MoveStatus.RUNNING
        if self.vision_status is not MoveStatus.FINISHED \
            or self.vision_status is not MoveStatus.FAILED:
            if self.getMarkerPos_status is 0:
                res = self.vision(r, "shelf", "code", "plasticbox")
                if self.vision_status is MoveStatus.FINISHED:
                    self.getMarkerPos_data["x"] = res["x"]
                    self.getMarkerPos_data["y"] = res["y"]
                    self.getMarkerPos_data["theta"] = res["theta"]
                    self.getMarkerPos_data["id"] = ""
                    self.getMarkerPos_status = 1
                    self.getMarkerStartTime = time.time()
            elif self.getMarkerPos_status is 1:
                dt = time.time() - self.getMarkerStartTime
                if dt > self.getMarkerPosTotTime:
                    self.getMarkerPos_status =2
                    self.operation_status = MoveStatus.FINISHED
        self.state["MarkerPos"] = self.getMarkerPos_data 


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
                          self.task.get("binModel", "plasticbox"), self.loadHeight, self.unloadHeight)
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
                                  self.task.get("binModel", "plasticbox"), self.loadHeight, self.unloadHeight),
                        getGoods(self.task["stretch"] + self.loadOffset),
                        prePutGoods(self.high[int(self.task["selfPosition"])],0,"load"),
                        putGoods(self.stretchDist)
                    ]
                else:
                    r.setError("task is wrong in load with recAdjust: {}".format(json.dumps(self.task)))
                    self.operation_status = MoveStatus.FAILED
            else:
                self.vision_status = MoveStatus.FINISHED
                self.task_list = [
                    preGoods(self.task["lift"], self.task["rotate"]),
                    getGoods(self.task["stretch"] + self.loadOffset),
                    prePutGoods(self.high[int(self.task["selfPosition"])],0,"load"),
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
                    if "recBoxLift" in self.task:
                        self.task_list = [
                            preGoods(self.low[int(self.task["selfPosition"])], 0),
                            getGoods(self.stretchDist),
                            preRecBox(self.task["recBoxLift"], self.task["rotate"]),
                            recBox(),
                            prePutGoods(self.task["lift"], self.task["rotate"],"unload"),
                            recAdjust(self.task["visionType"], self.task["visionBinType"], 
                                    self.task.get("binModel", "plasticbox"), self.loadHeight, self.unloadHeight),
                            putGoods(self.task["stretch"])
                        ]
                    else:
                        self.task_list = [
                            preGoods(self.low[int(self.task["selfPosition"])], 0),
                            getGoods(self.stretchDist),
                            prePutGoods(self.task["lift"], self.task["rotate"],"unload"),
                            recBox(),
                            recAdjust(self.task["visionType"], self.task["visionBinType"], 
                                    self.task.get("binModel", "plasticbox"), self.loadHeight, self.unloadHeight),
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
                    prePutGoods(self.task["lift"], self.task["rotate"],"unload"),
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
                prePutGoods(self.high[int(self.task["changePosition1"])], 0,"changePos"),
                putGoods(self.stretchDist)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["change"] = cur_state  

    def putPos(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                putGoodsS2(),
                prePutGoods(self.high[int(self.task["putPosition"])], 0, "putPos"),
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
            self.finger(r, 0, True)
        elif self.stretch_status is not MoveStatus.FINISHED:
            self.h.stretchReset(r)
            self.stretch(r,0, True)
        elif self.lift_status is not MoveStatus.FINISHED:
            self.h.liftReset(r)
            self.lift(r, 385, True)
        elif self.rotate_status is not MoveStatus.FINISHED:
            self.h.rotateReset(r)
            self.rotate(r, 0, True)
        else:
            self.operation_status = MoveStatus.FINISHED
        rotate_state = -1
        lift_state = -1
        stretch_state = -1
        finger_state = -1
        if "rotate" in self.state and "state" in self.state["rotate"]:
            rotate_state = self.state["rotate"]["state"]
        if "lift" in self.state and "state" in self.state["lift"]:
            lift_state = self.state["lift"]["state"]
        if "stretch" in self.state and "state" in self.state["stretch"]:
            stretch_state = self.state["stretch"]["state"]
        if "finger" in self.state and "state" in self.state["finger"]:
            finger_state = self.state["finger"]["state"]
        if rotate_state == Hairou.ModuleState.ERROR \
            or lift_state == Hairou.ModuleState.ERROR \
                or stretch_state == Hairou.ModuleState.ERROR \
                    or finger_state == Hairou.ModuleState.ERROR:
                    if not r.errorExits(53000):
                        r.setError("Picking robot has error in zero operation")
        else:
            if r.errorExits(53000):
                r.clearError(53000)
        r.logDebug("53000 error : {}".format(r.errorExits(53000)))
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


class recBox:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.visionType = "box"
        self.visionBinType = "code"
        self.binModel = "plasticbox"
    def reset(self, ctu):
        ctu.vision_status = MoveStatus.NONE
        self.status = MoveStatus.RUNNING   
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.vision_status is not MoveStatus.FINISHED:
            res = ctu.vision(r, self.visionType, self.visionBinType, self.binModel, True)
            if ctu.vision_status == MoveStatus.FAILED:
                self.status = MoveStatus.FINISHED
                ctu.vision_status = MoveStatus.FINISHED
            elif ctu.vision_status == MoveStatus.FINISHED:
                method = "vout"
                dz = res[method]["dz"]
                dx = res[method]["dx"]
                dy = res[method]["dy"]
                dist = res[method]["dist"]
                dtheta = res[method]["yaw"] * math.pi /180.0
                dist_stretch = abs(dx * math.cos(dtheta) + dy * math.sin(dtheta))
                if dz < -0.2 or dist_stretch > 1.0:
                    self.status = MoveStatus.FINISHED
                    r.logDebug(f"Has shelf but not in here. dz {dz} dist {dist_stretch}")
                else:
                    self.status = MoveStatus.FAILED
                    r.setError("The shelf has box. Cannot unload!!")
        cur_state = dict()
        cur_state["status"] = self.status
        ctu.state["recBox"] = cur_state
        
class recAdjust:
    def __init__(self, visionType, visionBinType, binModel, loadHeight, unloadHeight):
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
        self.offz_box = loadHeight
        self.offz_shelf = unloadHeight
        self.lift_pos = 0
        self.rot_theta = 0
        self.go_args = dict()
        self.adjust_count = 0
        self.ok = False
        self.first_adj = True
        self.last_ddtheta = 100
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
        self.ok_x = 0.012
        self.ok_theta = 0.013
        self.first_adj = True
        self.last_ddtheta = 100
    def run(self, r, ctu):
        self.status = MoveStatus.RUNNING
        if ctu.vision_status is not MoveStatus.FINISHED:
            if self.rec_count < self.max_rec_times:
                res = ctu.vision(r, self.visionType, self.visionBinType, self.binModel)
                if ctu.vision_status == MoveStatus.FAILED:
                    self.rec_count = self.rec_count + 1
                    ctu.vision_status = MoveStatus.RUNNING
                method = "vout"
                if ctu.vision_status == MoveStatus.FINISHED:
                    dist, dz, dtheta = 0, 0, 0
                    if self.visionBinType == "code":
                        dz = res[method]["dz"]
                        dist = res[method]["dist"]
                        dtheta = res[method]["yaw"] * math.pi /180.0
                    elif self.visionBinType == "markerless":
                        dz = 0
                        dist = res[method]["dist"]
                        dtheta = res[method]["yaw"] * math.pi /180.0
                    else:
                        r.setError(" binType error: {}".format(self.visionBinType))
                        ctu.vision_status = MoveStatus.FAILED
                        self.status = MoveStatus.FAILED
                    ddtheta = normalize_theta(dtheta - ctu.state["rotate"]["position"])
                    if abs(ddtheta) < 0.14:
                        self.dtheta = dtheta
                        self.dz = dz
                        self.dist = dist
                        if self.adjust_count >= self.max_adjust_time:
                            self.status = MoveStatus.FAILED
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
                            self.rot_theta = self.dtheta
                            self.ok_x = 0.012
                            self.ok_theta = 0.013
                            if self.visionBinType == "markerless":
                                self.ok_x = 0.02
                                self.ok_theta = 0.035
                            elif self.visionType == "shelf" and self.adjust_count + 3 > self.max_adjust_time:
                                self.ok_x = 0.02
                                self.ok_theta = 0.035
                            elif self.adjust_count + 3 > self.max_adjust_time:
                                self.ok_x = 0.012
                                self.ok_theta = 0.02
                            r.logDebug("[recAdjust][{}|{}|{}|{}|{}|{}]".format(
                                self.go_args["x"],self.ok_x,ddtheta,self.ok_theta,self.last_ddtheta, self.first_adj))
                            if (abs(ddtheta) < self.ok_theta or abs(ddtheta) > abs(self.last_ddtheta)) \
                                and abs(self.go_args["x"]) < self.ok_x and not self.first_adj:
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
                            self.last_ddtheta = ddtheta                           
                    else:
                        ctu.record_vision(r)
                        r.setNotice(" yaw is too large: {}".format(res[method]["yaw"]))
                        self.rec_count = self.rec_count + 1
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
        cur_state["ok"] = self.ok
        cur_state["ok_x"] = self.ok_x
        cur_state["ok_theta"] = self.ok_theta
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
            ctu.checkFingerStatus(r,1)
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
            ctu.checkFingerStatus(r,0)
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

class preRecBox:
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

class prePutGoods:
    def __init__(self, liftPos, rotAngle, operation):
        self.status = MoveStatus.NONE
        self.liftPos = liftPos
        self.rotAngle = rotAngle
        self.seperate_height = 2000
        self.operation = operation
    def reset(self, ctu):
        ctu.rotate_status = MoveStatus.NONE
        ctu.lift_status = MoveStatus.NONE
        self.status = MoveStatus.RUNNING
    def run(self, r, ctu:Module):
        device_state = ctu.state["lift"]
        self.status = MoveStatus.RUNNING 
        r.logDebug("prePutGoods, {}, {}, {}".format(self.seperate_height, self.operation, device_state["position"]))
        if self.seperate_height >= 0 and self.operation == "load" and device_state["position"] >= self.seperate_height:
            self.status = MoveStatus.RUNNING
            if ctu.lift_status is not MoveStatus.FINISHED:
                ctu.lift(r, self.liftPos)
            if ctu.lift_status is MoveStatus.FINISHED and ctu.rotate_status is not MoveStatus.FINISHED:
                ctu.rotate(r,self.rotAngle)
            if ctu.lift_status is MoveStatus.FINISHED and ctu.rotate_status is MoveStatus.FINISHED:
                self.status = MoveStatus.FINISHED   
        elif self.seperate_height >= 0 and self.operation == "unload" and self.liftPos >= self.seperate_height:
            if ctu.rotate_status is not MoveStatus.FINISHED:
                ctu.rotate(r,self.rotAngle)
            if ctu.rotate_status is MoveStatus.FINISHED and ctu.lift_status is not MoveStatus.FINISHED:
                ctu.lift(r, self.liftPos)
            if ctu.lift_status is MoveStatus.FINISHED and ctu.rotate_status is MoveStatus.FINISHED:
                self.status = MoveStatus.FINISHED  
        else:
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
            ctu.checkFingerStatus(r,0)
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
    # res = {"errorState": [], "finger": {"leftStatus": 1, "rightStatus": 1, "state": 2}, "lastUpdate": 1616926318459, "lift": {"position": 485.754, "speed": 0.548552, "state": 2}, "msgType": 10, "rotate": {"position": -1.56325, "speed": 0.0, "state": 2}, "seqNum": 406, "stretch": {"position": -0.0, "speed": -1.01203, "state": 2}, "vision": {"state": 2}, "task": {"lift": 400, "operation": "load", "recAdjust": 1, "rotate": -1.57, "selfPosition": 3, "stretch": 860, "visionType": "box", "visionBinType": "code"}, "res": {"status": 0, "seqNum": 22, "res": {"executionResult": 0, "msgType": 255, "positionMatrix": [-0.005162753438078038, 0.9998964839473677, 0.013430091832507686, 0.02913439950958338, 0.9995693010948689, 0.004772144649372367, 0.02895581019694668, -0.010669121054354028, 0.02888872246489524, 0.013573799215306236, -0.9994904670326821, 0.34266477417180574, 0.0, 0.0, 0.0, 1.0], "seqNum": 22, "vout": {"yaw": 1.6554542548874005, "pitch": 0.2958052967453177, "roll": -0.7695209701947723, "dx": 0.6046647741718058, "dy": 0.010669121054354028, "dz": 0.0001343995095833793, "dist": 0.010668817268320767}, "targetType": "box", "binType": "code", "binId": ""}}, "recAdjStatus": {"dz": 0.0001343995095833793, "dist": 0.010668817268320767, "dtheta": 0.028893127363934568, "goaPathStatus": 0, "lift_pos": 485.8883995095834, "go_args": {"coordinate": "robot", "x": 0.010668817268320767, "y": 0, "theta": 0, "reachAngle": 3.141592653589793, "useOdo": 1, "reachDist": 0.002}, "rot_theta": -1.5343568726360655, "adj_count": 8, "visionType": "box", "binType": "code", "status": 1}, "load": {"state": 1, "task_id": 1}, "MoveStatus": {"lift": 0, "rotate": 0, "stretch": 0, "finger": 3, "indicator": 3, "vision": 3, "operation": 1, "status": 1}}
    # res = {"errorState": [], "finger": {"leftStatus": 1, "rightStatus": 1, "state": 2}, "lastUpdate": 1616926319885, "lift": {"position": 485.755, "speed": -0.0, "state": 2}, "msgType": 10, "rotate": {"position": -1.53436, "speed": -0.0167552, "state": 2}, "seqNum": 434, "stretch": {"position": -0.0, "speed": 0.337344, "state": 2}, "vision": {"state": 2}, "task": {"lift": 400, "operation": "load", "recAdjust": 1, "rotate": -1.57, "selfPosition": 3, "stretch": 860, "visionType": "box", "visionBinType": "code"}, "res": {"status": 0, "seqNum": 24, "res": {"executionResult": 0, "msgType": 255, "positionMatrix": [-0.007429246509390142, 0.999766852892183, 0.020274273214173785, 0.029153939962044777, 0.9997064956292621, 0.007893279536360431, -0.022904557075420436, 0.015400308396874191, -0.02305924745005849, 0.02009815902567019, -0.9995320580705833, 0.3421031880788719, 0.0, 0.0, 0.0, 1.0], "seqNum": 24, "vout": {"yaw": -1.3213511442478674, "pitch": 0.4256683857140494, "roll": -1.1617419484584592, "dx": 0.6041031880788719, "dy": -0.015400308396874191, "dz": 0.00015393996204477595, "dist": -0.015390086757584222}, "targetType": "box", "binType": "code", "binId": ""}}, "recAdjStatus": {"dz": 0.00015393996204477595, "dist": -0.015390086757584222, "dtheta": -0.023061928042119817, "goaPathStatus": 0, "lift_pos": 485.90893996204477, "go_args": {"coordinate": "robot", "x": -0.015390086757584222, "y": 0, "theta": 0, "reachAngle": 3.141592653589793, "useOdo": 1, "reachDist": 0.002, "backMode": 1}, "rot_theta": -1.5574219280421198, "adj_count": 9, "visionType": "box", "binType": "code", "status": 1}, "load": {"state": 1, "task_id": 1}, "MoveStatus": {"lift": 0, "rotate": 0, "stretch": 0, "finger": 3, "indicator": 3, "vision": 3, "operation": 1, "status": 1}}
    # res = {"errorState": [], "finger": {"leftStatus": 1, "rightStatus": 1, "state": 2}, "lastUpdate": 1616926321457, "lift": {"position": 485.753, "speed": 0.274276, "state": 2}, "msgType": 10, "rotate": {"position": -1.55743, "speed": 0.00167552, "state": 2}, "seqNum": 465, "stretch": {"position": -0.0, "speed": -0.0, "state": 2}, "vision": {"state": 2}, "task": {"lift": 400, "operation": "load", "recAdjust": 1, "rotate": -1.57, "selfPosition": 3, "stretch": 860, "visionType": "box", "visionBinType": "code"}, "res": {"status": 0, "seqNum": 26, "res": {"executionResult": 0, "msgType": 255, "positionMatrix": [-0.007004054562370299, 0.9999739902400965, -0.0017210644922518769, 0.02916108667094663, 0.9999590953971117, 0.007013779326262126, 0.005710904670219258, -0.01148737215256884, 0.005722827297514875, -0.0016809946048815666, -0.999982211594217, 0.342662612258709, 0.0, 0.0, 0.0, 1.0], "seqNum": 26, "vout": {"yaw": 0.3279036839872235, "pitch": 0.4013060470792056, "roll": 0.09861219918784905, "dx": 0.604662612258709, "dy": 0.01148737215256884, "dz": 0.00016108667094662937, "dist": 0.011486346008404863}, "targetType": "box", "binType": "code", "binId": ""}}, "recAdjStatus": {"dz": 0.00016108667094662937, "dist": 0.011486346008404863, "dtheta": 0.005722998914996058, "goaPathStatus": 0, "lift_pos": 0, "go_args": {}, "rot_theta": 0, "adj_count": 10, "visionType": "box", "binType": "code", "status": 1}, "load": {"state": 1, "task_id": 1}, "MoveStatus": {"lift": 0, "rotate": 0, "stretch": 0, "finger": 3, "indicator": 3, "vision": 3, "operation": 1, "status": 1}}
    # res = {"errorState": [], "finger": {"leftStatus": 1, "rightStatus": 1, "state": 2}, "lastUpdate": 1617774196313, "lift": {"position": 1150.08, "speed": -0.0, "state": 2}, "msgType": 10, "rotate": {"position": 3.13999, "speed": 0.00753982, "state": 2}, "seqNum": 97, "stretch": {"position": 0.00202406, "speed": 0.337344, "state": 2}, "vision": {"state": 2}, "task": {"lift": 1080, "operation": "load", "recAdjust": 1, "rotate": 3.14, "selfPosition": 0, "stretch": 920, "visionType": "box", "visionBinType": "code"}, "res": {"status": 0, "seqNum": 6, "res": {"executionResult": 0, "msgType": 255, "positionMatrix": [-0.009344127654362655, 0.9982044929080618, 0.05916483428979484, 0.02896389952587754, 0.9998971162527275, 0.009971164304003799, -0.010311779279186539, -0.008335600717951527, -0.010883206690082945, 0.059062392608007996, -0.9981949657214058, 0.39888548170899063, 0.0, 0.0, 0.0, 1.0], "seqNum": 6, "vout": {"yaw": -0.6236013469464964, "pitch": 0.5353868690333142, "roll": -3.3920243909026055, "dx": 0.6608854817089906, "dy": 0.008335600717951527, "dz": -3.610047412246076e-05, "dist": -1.3359074694907491e-05}, "targetType": "box", "binType": "code", "binId": ""}}, "recAdjStatus": {"dz": -3.610047412246076e-05, "dist": -1.3359074694907491e-05, "dtheta": -0.01088389672408785, "goaPathStatus": 0, "lift_pos": 1070.0438995258776, "go_args": {"coordinate": "robot", "x": -1.3359074694907491e-05, "y": 0, "theta": 0, "reachAngle": 3.141592653589793, "useOdo": 1, "reachDist": 0.002, "backMode": 1}, "rot_theta": 3.1291061032759124, "adj_count": 1, "visionType": "box", "binType": "code", "status": 1}, "load": {"state": 1, "task_id": 1}, "MoveStatus": {"lift": 0, "rotate": 0, "stretch": 0, "finger": 3, "indicator": 3, "vision": 3, "operation": 1, "status": 1}}
    res = {"errorState": [], "finger": {"leftStatus": 1, "rightStatus": 1, "state": 2}, "lastUpdate": 1617774196313, "lift": {"position": 1150.08, "speed": -0.0, "state": 2}, "msgType": 10, "rotate": {"position": 3.13999, "speed": 0.00753982, "state": 2}, "seqNum": 97, "stretch": {"position": 0.00202406, "speed": 0.337344, "state": 2}, "vision": {"state": 2}, "task": {"lift": 1080, "operation": "load", "recAdjust": 1, "rotate": 3.14, "selfPosition": 0, "stretch": 920, "visionType": "box", "visionBinType": "code"}, "res": {"status": 0, "seqNum": 6, "res": {"executionResult": 0, "msgType": 255, "positionMatrix": [-0.009344127654362655, 0.9982044929080618, 0.05916483428979484, 0.02896389952587754, 0.9998971162527275, 0.009971164304003799, -0.010311779279186539, -0.008335600717951527, -0.010883206690082945, 0.059062392608007996, -0.9981949657214058, 0.39888548170899063, 0.0, 0.0, 0.0, 1.0], "seqNum": 6, "vout": {"yaw": -0.6236013469464964, "pitch": 0.5353868690333142, "roll": -3.3920243909026055, "dx": 0.6608854817089906, "dy": 0.008335600717951527, "dz": -3.610047412246076e-05, "dist": -1.3359074694907491e-05}, "targetType": "box", "binType": "code", "binId": ""}}, "recAdjStatus": {"dz": -3.610047412246076e-05, "dist": -1.3359074694907491e-05, "dtheta": -0.01088389672408785, "goaPathStatus": 0, "lift_pos": 1070.0438995258776, "go_args": {"coordinate": "robot", "x": -1.3359074694907491e-05, "y": 0, "theta": 0, "reachAngle": 3.141592653589793, "useOdo": 1, "reachDist": 0.002, "backMode": 1}, "rot_theta": 3.1291061032759124, "adj_count": 1, "visionType": "box", "binType": "code", "status": 1}, "load": {"state": 1, "task_id": 1}, "MoveStatus": {"lift": 0, "rotate": 0, "stretch": 0, "finger": 3, "indicator": 3, "vision": 3, "operation": 1, "status": 1}}
    print(f"rotate: {res['rotate']['position']+res['recAdjStatus']['dtheta']}, dist: {res['recAdjStatus']['dist']}")
    yaw, dx , dy, dz, dist, Tagv2box = getYPRZYX_code([res["res"]["res"]["positionMatrix"]], res["rotate"]["position"])
    print(f"yaw: {yaw}, dx: {dx}, dy: {dy}, dz: {dz}, dist: {dist}")
    loc_org = {"x":-26.89989,"y":-1.768388,"angle":-0.228760}
    loc = [loc_org["x"],loc_org["y"],loc_org["angle"]]
    Tw2box = getMarkerInWorld(loc, Tagv2box)

    print("Tw2box: ", Tw2box)
    print("yaw", yaw)
    boxX = [[1],[0],[0],[1]]
    boxX2agv = matrixDot(Tagv2box, boxX,4,4,1)
    boxX2w = matrixDot(Tw2box, boxX, 4, 4,1)
    angle_agv = math.atan2(boxX2agv[1][0] - Tagv2box[1][3], boxX2agv[0][0] - Tagv2box[0][3])
    angle_world = math.atan2(boxX2w[1][0] -Tw2box[1][3], boxX2w[0][0]-Tw2box[0][3])
    out = dict()
    out["x"] = Tw2box[0][3]
    out["y"] = Tw2box[1][3]
    out["theta"] = angle_world
    print("box in world: ", out)      
    print("box in agv: ", Tagv2box[0][3],Tagv2box[1][3],angle_agv)

    res = {"errorState": [], "finger": {"leftStatus": 0, "rightStatus": 0, "state": 2}, "forkDetect": [{"binId": "", "id": 1, "state": 1, "type": 1}, {"binId": "", "id": 0, "state": 1, "type": 0}], "lastUpdate": 1624259373931, "lift": {"position": 1080.0, "speed": 0.548552, "state": 2}, "msgType": 10, "rotate": {"position": 3.14, "speed": 0.00167552, "state": 2}, "seqNum": 0, "stretch": {"position": -0.0, "speed": -0.0, "state": 2}, "trays": [{"binId": "", "id": 1, "state": 1, "type": 0}], "vision": {"state": 2}, "task": {"lift": 1080, "operation": "unload", "recAdjust": 1, "rotate": 3.14, "selfPosition": 1, "stretch": 920, "visionType": "shelf", "visionBinType": "code"}, "unload": {"state": 1, "task_id": 0}, "MoveStatus": {"lift": 0, "rotate": 0, "stretch": 0, "finger": 0, "indicator": 3, "vision": 0, "operation": 1, "status": 1}, "connect_error": "ctu recv error!!!"}
    dz = 0
    dist_stretch = 0
    r.logDebug(f"Has shelf but not in here. dz {dz} dist {dist_stretch}")
    try:
        r.logDebug("[HaiRou][{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}]".format(
        res["lift"]["position"],res["lift"]["state"], res["lift"]["speed"],
        res["rotate"]["position"],res["rotate"]["state"], res["rotate"]["speed"],
        res["stretch"]["position"],res["stretch"]["state"], res["stretch"]["speed"],
        res["finger"]["leftStatus"],res["finger"]["rightStatus"], res["finger"]["state"],
        res["vision"]["state"]))
    except KeyError as e:
        r.logDebug("KeyError: "+str(e))
    except Exception as e:
        r.logDebug("Other error in print hairou state")

    try:
        if "forkDetect" in res :
            log_key = "HaiRou_forkDetect"
            log_str = ""
            for fork in res["forkDetect"]:
                tmp_str = "{}|{}|{}|".format(fork["id"],fork["state"],fork["state"])
                log_str = log_str+tmp_str
            r.logDebug("[{}][{}]".format(log_key, log_str))
    except KeyError as e:
        r.logDebug("KeyError: "+str(e))
    except Exception as e:
        r.logDebug("Other error in print hairou forkDetect state")

    try:
        if "trays" in res:
            log_key = "HaiRou_trays"
            log_str = ""
            for trays in res["trays"]:
                tmp_str = "{}|{}|{}|".format(trays["id"],trays["state"],trays["state"])
                log_str = log_str+tmp_str
            if log_str != "":
                r.logDebug("[{}][{}]".format(log_key, log_str))
    except KeyError as e:
        r.logDebug("KeyError: "+str(e))
    except Exception as e:
        r.logDebug("Other error in print hairou trays state")

    print(m.checkFingerStatus(r,1))
    print("DONE")

    # yaw = (yaw+math.pi/2)/math.pi*180.0
    # pitch = pitch/math.pi*180
    # roll = roll/math.pi *180
    # print(dx, dy, dz, dist, yaw, pitch ,roll)







    # yaw, p, r, z, y, x = getYPRZYX(one)
    # print(yaw/math.pi*180,p/math.pi*180,r/math.pi*180,z,y,x)

    
