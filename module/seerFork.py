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
    "operation":{
        "value": "zero",
        "default_value":[
        "zero","unload","load","lift","finger","stretch","rec","recAdjust"
        ],
        "tips": "tips",
        "type": "complex"        
    },
    "lift": {
        "value": 0.,
        "tips": "lift hight",
        "type": "double",
        "unit": "m"
    },    
    "stretch": {
        "value": 0.,
        "tips": "stretch length",
        "type": "double",
        "unit": "m"
    },  
    "finger": {
        "value": 0.,
        "tips": "finger gap",
        "type": "double",
        "unit": "m"
    },
    "recfile": {
        "value": "tag/t0001.tag",
        "tips": "识别文件",
        "unit": "",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""
def Pos2Base(pos2world, base2world):
    """将基于世界坐标系的两个位姿，转换为基于base的位姿

    Args:
        pos2world ([3]): 被转换的位姿，基于世界坐标系,0:x, 1:y, 2: theta
        base2world ([3]): 基准，基于世界坐标系,0:x, 1:y, 2: theta
    Returns:
        [3]: pos2base
    """
    pos2base = [0.,0.,0.]
    x = pos2world[0] - base2world[0]
    y = pos2world[1] - base2world[1]
    pos2base[0] = x * math.cos(base2world[2]) + y * math.sin(base2world[2])
    pos2base[1] = -x * math.sin(base2world[2]) + y * math.cos(base2world[2])
    pos2base[2] = normalize_theta(pos2world[2] - base2world[2])
    return pos2base
class lift:
    def __init__(self, motor_name, dist):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
    def run(self, r:SimModule, agv):
        self.status = MoveStatus.RUNNING
        r.setMotorPosition(self.motor, self.dist, 0.025, -1)
        if r.isMotorReached(self.motor):
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['lift_state'] = self.status
        cur_state['dist'] = self.dist
        agv.state['lift_org'] = cur_state

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

class stretch:
    def __init__(self, motor_name, dist):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
    def run(self, r:SimModule, agv):
        self.status = MoveStatus.RUNNING
        r.setMotorPosition(self.motor, self.dist, 0.1, -1)
        if r.isMotorReached(self.motor):
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['stretch_state'] = self.status
        cur_state['dist'] = self.dist
        agv.state['stretch_org'] = cur_state

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

class finger:
    def __init__(self, motor_name, dist):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
    def run(self, r:SimModule, agv):
        self.status = MoveStatus.RUNNING
        r.setMotorPosition(self.motor, self.dist, 0.1, -1)
        if r.isMotorReached(self.motor):
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['finger_state'] = self.status
        cur_state['dist'] = self.dist
        agv.state['finger_org'] = cur_state

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

class rec:
    def __init__(self, filename):
        self.status = MoveStatus.NONE
        self.filename = filename
        self.rec_times = 0
        self.max_rec_times = 10
        self.result = dict()
    def run(self, r:SimModule,agv):
        self.status = MoveStatus.RUNNING
        rec_status = r.getRecStatus()
        r.logDebug("rec_status: {}".format(rec_status))
        if rec_status == 3:
            self.rec_times = self.rec_times + 1
            if self.rec_times > self.max_rec_times:
                r.setError("rec fail. reach max times {}".format(self.max_rec_times))
                self.status = MoveStatus.FAILED
            else:
                r.doRec(self.filename)
        elif rec_status == 0 or rec_status == 1:
            r.doRec(self.filename)
        elif rec_status == 2:
            self.result = r.getRecResult()
            r.logDebug("rec_result:{}".format(self.result))
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['rec_result'] = self.result
        cur_state['rec_state'] = self.status
        cur_state['rec_status'] = rec_status
        cur_state['file'] = self.filename
        agv.state['rec_org'] = cur_state
        r.logDebug(json.dumps(agv.state))

    def reset(self, r):
        r.resetRec()
        self.status = MoveStatus.RUNNING

class recAdjust:
    def __init__(self, r, filename):
        self.status = MoveStatus.NONE
        self.rec = rec(filename)
        self.result = []
        self.max_rec_fail_times = 10
        self.max_adjust_time = 10
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.go_args = dict()
        self.ok = False
        self.plan_status = MoveStatus.NONE
        self.goPath = goPath.Module(r, dict())
    def run(self, r:SimModule, agv):
        self.status = MoveStatus.RUNNING
        if self.plan_status is not MoveStatus.FINISHED:
            self.plan_status = MoveStatus.RUNNING
            if self.rec.status is MoveStatus.RUNNING or self.rec.status is MoveStatus.NONE:
                self.rec.run(r,agv)
            elif self.rec.status is MoveStatus.FAILED:
                self.rec_fail_time = self.rec_fail_time + 1
                if self.rec_fail_time < self.max_rec_fail_times:
                    self.rec.reset(r)
                    self.rec.run(r,agv)
                else:
                    self.status = MoveStatus.FAILED
                    r.setError("rec fails!!! reach max times. {}".format(self.max_rec_fail_times))
                r.setNotice("rec fail!!! {}".format(self.rec_fail_time))
            elif self.rec.status is MoveStatus.FINISHED:
                self.rec_fail_time = 0
                code2world = [self.rec.result['x'], self.rec.result['y'], self.rec.result['yaw']]  # 目标点在世界坐标系的位置
                loc = r.loc()
                robot2world = [loc['x'], loc['y'], loc['angle']]  # 小车在世界坐标系的位置
                code2robot = Pos2Base(code2world, robot2world)   # 目标点相对小车的位置
                self.go_args["coordinate"] = "robot"
                self.go_args["x"] = code2robot[0]
                self.go_args["y"] = 0
                self.go_args["theta"] = 0
                self.go_args["reachAngle"] = math.pi
                self.go_args["useOdo"] = 1
                self.go_args["reachDist"] = 0.002
                if self.go_args["x"] < 0:
                    self.go_args["backMode"] = 1
                ok_x = 0.005
                if abs(self.go_args['x']) < ok_x:
                    self.status = MoveStatus.FINISHED
                else:
                    if self.adjust_count >= self.max_adjust_time:
                        self.status = MoveStatus.FAILED
                        r.setError("recAdjust fails!!! reach max times.")
                self.plan_status = MoveStatus.FINISHED
                self.rec.reset(r)
        elif self.status is not MoveStatus.FINISHED and self.status is not MoveStatus.FAILED:
            if self.goPath.status != MoveStatus.FINISHED and self.goPath.status != MoveStatus.FAILED:
                if abs(self.go_args["x"]) < 0.003:
                    self.goPath.status = MoveStatus.FINISHED
                else:
                    self.goPath.run(r,self.go_args)
            elif self.goPath.status == MoveStatus.FAILED:
                self.status = MoveStatus.FAILED
            elif self.goPath.status == MoveStatus.FINISHED:
                self.adjust_count = self.adjust_count + 1
                self.rec_count = 0
                self.goPath.reset()
                self.status = MoveStatus.RUNNING
                self.go_args = dict()
                self.plan_status = MoveStatus.NONE
        cur_state = dict()
        cur_state["goaPathStatus"] = self.goPath.status
        cur_state["planStatus"] = self.plan_status
        cur_state["go_args"] = self.go_args
        cur_state["rec_fail_time"] = self.rec_fail_time
        cur_state["ajdust_time"] = self.adjust_count
        cur_state["status"] = self.status
        agv.state["recAdjust_org"] = cur_state

    def reset(self, r):
        self.rec.reset(r)
        self.status = MoveStatus.RUNNING
        self.rec_fail_time = 0
        self.adjust_count = 0
        self.goPath.reset()

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.finger_open = -0.04
        self.finger_close = 0.0
        self.lift_down = 0
        self.lift_up = 0.05
        self.stretch_out = 0.5
        self.stretch_in = 0.0
        self.status = MoveStatus.RUNNING
        self.lift_motor = "shengjiang"
        self.stretch_motor = "shengsuo"
        self.finger_motor = "baojia"
        self.rec_file = ""
        self.init = True
        self.task = dict()
        self.state = dict()
        self.operation_status = MoveStatus.NONE
    def run(self, r:SimModule,args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.task = args
            self.rec_file = args.get("recfile","")
            self.operation_status = MoveStatus.NONE
            if "operation" not in self.task:
                r.setError("operation is empty!!!")
                self.status = MoveStatus.FAILED
                return self.status
        operation = self.task.get("operation","")
        if operation == "":
            self.status = MoveStatus.FINISHED
        elif operation == "load":
            self.load(r)
        elif operation == "unload":
            self.unload(r)
        elif operation == "zero":
            self.zero(r)
        elif operation == "recAdjust":
            self.recAdjust(r)
        elif operation == "lift":
            self.lift(r)
        elif operation == "stretch":
            self.stretch(r)
        elif operation == "finger":
            self.finger(r)
        elif operation == "rec":
            self.rec(r)
        else:
            r.setError("operation is wrong {}".format(str(operation)))
            self.status = MoveStatus.FAILED
        if self.operation_status == MoveStatus.FINISHED:
            self.status = MoveStatus.FINISHED
        self.state["MoveStatus"] = self.status
        self.state["task"] = self.task
        str_state = json.dumps(self.state)
        r.setInfo(str_state)
        r.logDebug(str_state)
        if self.status is MoveStatus.FAILED:
            r.stopRobot(True)
        r.publishSpeed()
        return self.status
    def lift(self, r):
        if "lift" not in self.task:
            r.setError("lift height is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [lift(self.lift_motor, self.task["lift"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["lift"] = cur_state          
    def stretch(self, r):
        if "stretch" not in self.task:
            r.setError("stretch length is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED    
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [stretch(self.stretch_motor, self.task["stretch"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["stretch"] = cur_state   
    def finger(self, r):
        if "finger" not in self.task:
            r.setError("finger length is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED  
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [finger(self.finger_motor, self.task["finger"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["finger"] = cur_state     
    def rec(self,r):
        if "recfile" not in self.task:
            r.setError("recfile is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED 
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [rec(self.task["recfile"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["rec"] = cur_state
    def recAdjust(self,r):
        if "recfile" not in self.task:
            r.setError("recfile is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED 
        else:        
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [recAdjust(r, self.task["recfile"])]
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
            if "recfile" in self.task:
                self.task_list = [
                    recAdjust(r, self.task["recfile"]),
                    finger(self.finger_motor, self.finger_open),
                    lift(self.lift_motor, self.lift_down),
                    stretch(self.stretch_motor, self.stretch_out),
                    lift(self.lift_motor, self.lift_up),
                    stretch(self.stretch_motor, self.stretch_in),
                    finger(self.finger_motor, self.finger_close),
                ]
            else:
                self.task_list = [
                    finger(self.finger_motor, self.finger_open),
                    lift(self.lift_motor, self.lift_down),
                    stretch(self.stretch_motor, self.stretch_out),
                    lift(self.lift_motor, self.lift_up),
                    stretch(self.stretch_motor, self.stretch_in),
                    finger(self.finger_motor, self.finger_close)
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
            if "recfile" in self.task:
                self.task_list = [
                    recAdjust(r, self.rec_file),
                    finger(self.finger_motor, self.finger_open),
                    lift(self.lift_motor, self.lift_up),
                    stretch(self.stretch_motor, self.stretch_out),
                    lift(self.lift_motor, self.lift_down),
                    stretch(self.stretch_motor, self.stretch_in),
                    finger(self.finger_motor, self.finger_close)      
                ]
            else:
                self.vision_status = MoveStatus.FINISHED
                self.task_list = [
                    finger(self.finger_motor, self.finger_open),
                    lift(self.lift_motor, self.lift_up),
                    stretch(self.stretch_motor, self.stretch_out),
                    lift(self.lift_motor, self.lift_down),
                    stretch(self.stretch_motor, self.stretch_in),
                    finger(self.finger_motor, self.finger_close) 
                ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["unload"] = cur_state             

    def zero(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                finger(self.finger_motor, self.finger_open),
                stretch(self.stretch_motor, self.stretch_in),
                lift(self.lift_motor, self.lift_down)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["zero"] = cur_state

    def runTakList(self, r):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(r)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED

    def cancel(self, r:SimModule):
        r.stopRobot(True)
        r.logInfo("script cancel")
        self.status = MoveStatus.NONE
    def suspend(self, r:SimModule):
        r.stopRobot(True)
        r.logInfo("script suspended")
        self.status = MoveStatus.SUSPENDED
        self.start_connect_time = time.time()

if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["operation"] = "rec"
    data["recfile"] = "s001.shelf"
    data["lift"] = 1.0
    data["stretch"] = 1.0
    data["finger"]  = 1.0
    print(m.run(r, data))
    print(m.run(r, data))
    print(m.run(r, data))
    pos2world = [2,2,math.pi/2]
    base2world = [1,1,math.pi/2]
    print(Pos2Base(pos2world,base2world))