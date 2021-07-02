import json
import time
import math
import sys
sys.path.append("syspy")
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "zero",
        "default_value":[
        "zero","unload","load","lift","rotate","stretch"
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
        "tips": ">0 : out, <0 in",
        "type": "int",
        "unit": ""
    },  
    "rotate": {
        "value": 0.,
        "tips": "rotate angle",
        "type": "double",
        "unit": "rad"
    },
    "lift_up": {
        "value": 0.,
        "tips": "lift up height in unload",
        "type": "double",
        "unit": "m"
    },
    "lift_mid": {
        "value": 0.,
        "tips": "lift mid height in unload",
        "type": "double",
        "unit": "m"
    }
}
####END DEFAULT ARGS####
"""
class DIFilter:
    def __init__(self,id, size, status) -> None:
        self.di_status = [status for i in range(size)]
        self.id = id
    def updateStatus(self,status):
        tmp_status = []
        for i in range(len(self.di_status)-1):
            tmp_status.append(self.di_status[i+1])
        self.di_status = tmp_status
        self.di_status.append(status)
    def reset(self, status):
        self.di_status = [status for i in range(len(self.di_status))]
    def status(self):
        false_size = 0
        true_size = 0
        for d in self.di_status:
            if d == False:
                false_size = false_size + 1
            else:
                true_size = true_size + 1
        if true_size > false_size:
            return True
        else:
            return False

class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.status = MoveStatus.RUNNING
        self.lift_motor = "shengjiang"
        self.stretch_motor = "shengsuo"
        self.rotate_motor = "rotate"
        self.stretch_out_DI = DIFilter(id = -1, size = 5, status = False)
        self.stretch_in_DI = DIFilter(id = -1, size = 5, status = False)
        self.reachDI = DIFilter(id = -1, size = 5, status = False)
        self.lift_warn_height = 0.2
        self.lift_msg = 0
        self.rotate_msg = 0
        self.stretch_zero = 0
        self.lift_zero = 0
        self.rotate_zero = 0

        self.init = True
        self.task = dict()
        self.state = dict()
        self.task_list = []
        self.task_id = 0
        self.operation_status = MoveStatus.NONE
        
    def reset(self, r:SimModule):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()
        self.init = True
        self.task = dict()
        self.state = dict()
        self.task_list = []
        self.task_id = 0
        self.operation_status = MoveStatus.NONE

    def getMessage(self, r:SimModule):
        odo = r.odo()
        r.logDebug(str(odo))
        for motor_info in odo.get('motor_info',[]):
            if self.lift_motor == motor_info.get('motor_name'):
                self.lift_msg = motor_info.get('position', 0)
            elif self.stretch_motor == motor_info.get('motor_name'):
                self.stretch_msg = motor_info.get('position', 0)
        dis = r.Di()
        r.logDebug(str(dis))
        for d in dis.get('node',[]):
            if self.stretch_in_DI.id == d.get('id', -1):
                self.stretch_in_DI.updateStatus(bool(d.get('status', False)))
            elif self.stretch_out_DI.id == d.get('id', -1):
                self.stretch_out_DI.updateStatus(bool(d.get('status', False)))
            elif self.reachDI.id == d.get('id', -1):
                self.reachDI.updateStatus(bool(d.get('status', False)))

    def run(self, r:SimModule,args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.task = args
            self.operation_status = MoveStatus.NONE
            if "operation" not in self.task:
                r.setError("operation is empty!!!")
                self.status = MoveStatus.FAILED
                return self.status
            dis = r.Di()
            for d in dis.get('node',[]):
                if self.stretch_in_DI.id == d.get('id', -1):
                    self.stretch_in_DI.reset(bool(d.get('status', False)))
                elif self.stretch_out_DI.id == d.get('id', -1):
                    self.stretch_out_DI.reset(bool(d.get('status', False)))
                elif self.reachDI.id == d.get('id', -1):
                    self.reachDI.reset(bool(d.get('status', False)))
        self.getMessage(r)
        operation = self.task.get("operation","")
        if operation == "":
            self.status = MoveStatus.FINISHED
        elif operation == "load":
            self.load(r)
        elif operation == "unload":
            self.unload(r)
        elif operation == "zero":
            self.zero(r)
        elif operation == "lift":
            self.lift(r)
        elif operation == "stretch":
            self.stretch(r)
        elif operation == "rotate":
            self.rotate(r)
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
        r.logDebug("[TianTian][{}|{}|{}|{}|{}|{}|{}|{}|{}]".format(
        self.lift_msg, self.rotate_msg, 
        self.stretch_in_DI.status(), self.stretch_out_DI.status(), 
        self.reachDI.status(), self.status, 
        self.task_id, len(self.task_list), self.operation_status))
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
                self.task_list = [stretch(self.stretch_motor, self.task["stretch"], self.stretch_in_DI.id, self.stretch_out_DI.id)]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["stretch"] = cur_state   

    def rotate(self, r):
        if "rotate" not in self.task:
            r.setError("rotate angle is empty {}".format(json.dumps(self.task)))
            self.status = MoveStatus.FAILED  
        else:
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [rotate(self.rotate_motor, self.task["rotate"])]
                self.task_id = 0
            else:
                self.runTakList(r)
            cur_state = dict()
            cur_state["state"] = self.operation_status
            cur_state["task_id"] = self.task_id
            self.state["rotate"] = cur_state     

    def load(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                stretch(self.stretch_motor, 1.0, self.stretch_in_DI.id, self.stretch_out_DI.id),
                lift(self.lift_motor, self.task["lift"]),
                rotate(self.rotate_motor, self.task["rotate"]),
                stretch(self.stretch_motor, -1.0, self.stretch_in_DI.id, self.stretch_out_DI.id)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        if self.operation_status == MoveStatus.FINISHED:
            r.setGoodsShape(0,0,0)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state

    def unload(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                lift(self.lift_motor, self.task["lift_up"]),
                stretch(self.stretch_motor, 1.0, self.stretch_in_DI.id, self.stretch_out_DI.id),
                lift(self.lift_motor, self.task["lift_mid"]),
                rotate(self.rotate_motor, self.task["rotate"]),
                lift(self.lift_motor, self.lift_zero),
                stretch(self.stretch_motor, -1.0, self.stretch_in_DI.id, self.stretch_out_DI.id),
            ]
        else:
            self.runTakList(r)
        if self.operation_status == MoveStatus.FINISHED:
            r.clearGoodsShape(0,0,0)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["unload"] = cur_state             

    def zero(self,r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                rotate(self.rotate_motor, self.rotate_zero),
                stretch(self.stretch_motor, -1., self.stretch_in_DI.id, self.stretch_out_DI.id),
                lift(self.lift_motor, self.lift_zero)
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

class lift:
    def __init__(self, motor_name, dist):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
        self.init = True
    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            hasGoods = r.hasGoods()
            if hasGoods and self.dist < agv.lift_warn_height and agv.stretch_in_DI.status():
                self.dist = agv.lift_warn_height
                r.setWarning("Cannot lift to {} in load mode with stretch dist {}.".format(self.dist, agv.stretch_in_DI.status()))
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
        self.init = True

class stretch:
    def __init__(self, motor_name, dist, stretch_in_DI, stretch_out_DI):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
        self.inDI = stretch_in_DI
        self.outDI = stretch_out_DI
        self.init = True
    def run(self, r:SimModule, agv:Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            hasGoods = r.hasGoods()
            if hasGoods and agv.lift_msg < agv.lift_warn_height and self.dist < 0:
                r.setError("Cannot stretch to {} in load mode with lift height {}.".format(self.dist, agv.lift_msg))
                self.status = MoveStatus.FAILED
                cur_state = dict()
                cur_state['stretch_state'] = self.status
                cur_state['dist'] = self.dist
                agv.state['stretch_org'] = cur_state
                return
        if self.dist > 0:
            if agv.task.get("operation","") == "load"  and agv.reachDI.status():
                r.setMotorSpeed(self.motor, 0)
            else:
                r.setMotorSpeed(self.motor, 0.05, self.outDI)
        else:
            r.setMotorSpeed(self.motor, 0.05, self.inDI)
        if r.isMotorReached(self.motor):
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['stretch_state'] = self.status
        cur_state['dist'] = self.dist
        agv.state['stretch_org'] = cur_state
    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING
        self.init = True

class rotate:
    def __init__(self, motor_name, angle):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.angle = angle
    def run(self, r:SimModule, agv):
        self.status = MoveStatus.RUNNING
        r.setMotorPosition(self.motor, self.angle, 0.1, -1)
        if r.isMotorReached(self.motor):
            self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['rotate_state'] = self.status
        cur_state['angle'] = self.angle
        agv.state['rotate_org'] = cur_state
    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING


if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)

    print(1)
    data = dict()
    data["operation"] = "zero"
    print(m.run(r, data))

    print(2)
    m.reset(r)
    data = dict()
    data["operation"] = "lift"
    data["lift"] = 1.0
    print(m.run(r, data))

    print(3)
    m.reset(r)
    data = dict()
    data["operation"] = "stretch"
    data["stretch"] = 1.0
    print(m.run(r, data))
    print(m.run(r, data))
    print(m.run(r, data))

    print(4)
    m.reset(r)
    data = dict()
    data["operation"] = "rotate"
    data["rotate"] = 1.0
    print(m.run(r, data))
    print(m.run(r, data))
    print(m.run(r, data))

    print(5)
    m.reset(r)
    data = dict()
    data["operation"] = "load"
    data["lift"] = 1.0
    data["rotate"] = 0.017
    print(m.run(r, data))

    print(6)
    m.reset(r)
    data = dict()
    data["operation"] = "unload"
    data["lift_up"] = 1.0
    data["lift_mid"] = 1.0
    data["rotate"] = 0.017
    print(m.run(r, data))