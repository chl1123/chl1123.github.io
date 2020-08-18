import json
import time
from rbk import MoveStatus, BasicModule

####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "tips": "FrontRollerLoad/FrontRollerUnLoad/BackRollerLoad/BackRollerUnLoad/FrontBackLoad/AllRollerLoad/AllRollerUnLoad",
        "type": "string"
    }
}
####END DEFAULT ARGS####

class Module(BasicModule):
    def __init__(self, r, args):
        super(Module, self).__init__()
        self.front_di1 = 5
        self.front_di2 = 4
        self.front_di3 = 3
        self.back_di1 = 8
        self.back_di2 = 7
        self.back_di3 = 6
        self.front_block_motor = "frontDOMotor"
        self.back_block_motor = "backDOMotor"
        self.mid_block_motor = "midDOMotor"
        self.front_roller = "frontMotor"
        self.back_roller = "backMotor"
        self.operation = ""
        self.load_vel = 1.0
        self.unload_vel = -1.0
        self.start_time = time.time()
        self.over_time = 120.0
        self.init = True

    def operationCheck(self, r, args):
        r.logInfo(str(args))
        self.status = MoveStatus.RUNNING
        if "operation" in args:
            self.operation = args["operation"]["value"]
        if self.operation is not "":
            r.logDebug(self.operation)
            if self.operation == "FrontRollerLoad":
                #1前滚筒进货
                r.setMotorSpeed(self.mid_block_motor, 1.0, -1)
                if not r.isMotorReached(self.mid_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError(53000, "mid block is not in the up cannot load")
                r.setMotorSpeed(self.front_block_motor, -1.0, -1)
                if not r.isMotorReached(self.front_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError(53000, "front block is not in the bottom cannot load")
            elif self.operation == "FrontRollerUnLoad":
                #2前滚筒卸货
                pass
            elif self.operation == "BackRollerLoad":
                #3后滚筒进货
                r.setMotorSpeed(self.mid_block_motor, 1.0, -1)
                if not r.isMotorReached(self.mid_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError(53000, "mid block is not in the up cannot load")
                r.setMotorSpeed(self.back_block_motor, -1.0, -1)
                if not r.isMotorReached(self.back_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError(53000, "front block is not in the bottom cannot load")
                pass
            elif self.operation == "BackRollerUnLoad":
                #4后滚筒卸货
                pass
            elif self.operation == "FrontBackLoad":
                #5前后滚筒分开进货
                r.setMotorSpeed(self.back_block_motor, -1.0, -1)
                if not r.isMotorReached(self.back_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError(53000, "back block is not in the up cannot load")
                r.setMotorSpeed(self.front_block_motor, -1.0, -1)
                if not r.isMotorReached(self.front_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError(53000, "front block is not in the bottom cannot load")
            elif self.operation == "FrontBackUnLoad":
                #6前后滚筒分开卸货
                pass
            elif self.operation == "AllRollerLoad":
                #7所有滚筒一起进货
                r.setMotorSpeed(self.back_block_motor, -1.0, -1)
                if not r.isMotorReached(self.back_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError(53000, "back block is not in the bottom cannot load")
                r.setMotorSpeed(self.front_block_motor, -1.0, -1)
                if not r.isMotorReached(self.front_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError(53000, "front block is not in the bottom cannot load")
            elif self.operation == "AllRollerUnLoad":
                #8所有滚筒一起卸货
                pass
            else:
                pass
        return self.status
                           
    def run(self, r,args):
        dt = time.time() - self.start_time
        if dt > self.over_time:
            self.status = MoveStatus.FAILED
            r.setError(53000, "Roller is over Time")
            return self.status.value
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.operationCheck(r, args)

        if self.status is MoveStatus.FAILED:
            return self.status.value

        if self.operation is not "":
            #计算速度
            r.logDebug(self.operation)
            if self.operation == "FrontRollerLoad":
                #1前滚筒进货
                self.status = self.SingleRollerLoad(r,self.front_di1, self.front_di2, self.front_di3, self.front_roller, self.front_block_motor)
            elif self.operation == "FrontRollerUnLoad":
                #2前滚筒卸货
                self.status = self.SingleRollerUnLoad(r,self.front_di1, self.front_di2, self.front_di3, self.front_roller, self.front_block_motor)
            elif self.operation == "BackRollerLoad":
                #3后滚筒进货
                self.status = self.SingleRollerLoad(r,self.back_di1, self.back_di2, self.back_di3, self.back_roller, self.back_block_motor)
            elif self.operation == "BackRollerUnLoad":
                #4后滚筒卸货
                self.status = self.SingleRollerUnLoad(r,self.back_di1, self.back_di2, self.back_di3, self.back_roller, self.back_block_motor)
            elif self.operation == "FrontBackLoad":
                #5前后滚筒分开进货
                r.setMotorSpeed(self.mid_block_motor, 1.0, -1)
                if not r.isMotorReached(self.mid_block_motor):
                    self.status = MoveStatus.RUNNING
                else:
                    status1 = self.SingleRollerLoad(r,self.front_di1, self.front_di2, self.front_di3, self.front_roller, self.front_block_motor)
                    status2 = self.SingleRollerLoad(r,self.back_di1, self.back_di2, self.back_di3, self.back_roller, self.back_block_motor)
                    if status1 == MoveStatus.FINISHED and status2 == MoveStatus.FINISHED:
                        self.status = MoveStatus.FINISHED
                    elif status1 == MoveStatus.FAILED or status2 == MoveStatus.FAILED:
                        self.status = MoveStatus.FAILED
                    else:
                        self.status = MoveStatus.RUNNING
            elif self.operation == "FrontBackUnLoad":
                #6前后滚筒分开卸货
                status1 = self.SingleRollerUnLoad(r,self.front_di1, self.front_di2, self.front_di3, self.front_roller, self.front_block_motor)
                status2 = self.SingleRollerUnLoad(r,self.back_di1, self.back_di2, self.back_di3, self.back_roller, self.back_block_motor)
                if status1 == MoveStatus.FINISHED and status2 == MoveStatus.FINISHED:
                    self.status = MoveStatus.FINISHED
                elif status1 == MoveStatus.FAILED or status2 == MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
                else:
                    self.status = MoveStatus.RUNNING
            elif self.operation == "AllRollerLoad":
                #7所有滚筒一起进货
                r.setMotorSpeed(self.mid_block_motor, -1.0, -1)
                if not r.isMotorReached(self.mid_block_motor):
                    self.status = MoveStatus.RUNNING
                else:
                    status1 = self.SingleRollerLoad(r,self.front_di1, self.front_di2, self.front_di3, self.front_roller, self.front_block_motor)
                    status2 = self.SingleRollerLoad(r,self.back_di1, self.back_di2, self.back_di3, self.back_roller, self.back_block_motor)
                    if status1 == MoveStatus.FINISHED and status2 == MoveStatus.FINISHED:
                        self.status = MoveStatus.FINISHED
                    elif status1 == MoveStatus.FAILED or status2 == MoveStatus.FAILED:
                        self.status = MoveStatus.FAILED
                    else:
                        self.status = MoveStatus.RUNNING
            elif self.operation == "AllRollerUnLoad":
                #8所有滚筒一起卸货
                status1 = self.SingleRollerUnLoad(r,self.front_di1, self.front_di2, self.front_di3, self.front_roller, self.front_block_motor)
                status2 = self.SingleRollerUnLoad(r,self.back_di1, self.back_di2, self.back_di3, self.back_roller, self.back_block_motor)
                if status1 == MoveStatus.FINISHED and status2 == MoveStatus.FINISHED:
                    self.status = MoveStatus.FINISHED
                elif status1 == MoveStatus.FAILED or status2 == MoveStatus.FAILED:
                    self.status = MoveStatus.FAILED
                else:
                    self.status = MoveStatus.RUNNING
            else:
                # 如果是不支持的operation则报错
                r.setError(53000, "Operation: " + self.operation + " doesn't support")
                self.status = MoveStatus.FAILED
            #发送速度
            if self.status is not MoveStatus.FAILED and self.status is not MoveStatus.FINISHED:
                if not r.publishSpeed():
                    self.status = MoveStatus.FAILED
        else:
            self.status = MoveStatus.FINISHED
        return self.status.value
    
    def SingleRollerLoad(self, r, di1, di2, di3, roller_motor, block_motor):
        #单个滚筒进货
        status = MoveStatus.RUNNING
        di = r.Di()
        di1_status = True
        di2_status = True
        di3_status = True
        for (ind,node) in enumerate(di['node']):
            if node['id'] == di1:
                di1_status = node['status']
            elif node['id'] == di2:
                di2_status = node['status']
            elif node['id'] == di3:
                di3_status = node['status']
        r.logInfo("di1: " + str(di1_status) + " di3: " + str(di3_status))
        if not di1_status and di3_status:
            r.setMotorSpeed(roller_motor, 0.0, -1)
            if self.isRollerMotorStopped(r, roller_motor):
                r.setMotorSpeed(block_motor, 1.0, -1)
                r.logInfo("motors Reached: " + str(r.isAllMotorsReached()) + " " + str(r.isMotorReached(block_motor)))
                if r.isMotorReached(block_motor):
                    status = MoveStatus.FINISHED
                else:
                    status = MoveStatus.RUNNING
            else:
                status = MoveStatus.RUNNING
        else:
            r.setMotorSpeed(roller_motor, self.load_vel, -1)
            status = MoveStatus.RUNNING
        return status

    def SingleRollerUnLoad(self, r, di1, di2, di3, roller_motor, block_motor):
        #单个滚筒卸货
        status = MoveStatus.RUNNING
        di = r.Di()
        r.setMotorSpeed(block_motor, -1.0, -1)
        if not r.isMotorReached(block_motor):
            self.status = MoveStatus.RUNNING
        else:
            di1_status = True
            di2_status = True
            di3_status = True
            for (ind,node) in enumerate(di['node']):
                if node['id'] == di1:
                    di1_status = node['status']
                elif node['id'] == di2:
                    di2_status = node['status']
                elif node['id'] == di3:
                    di3_status = node['status']
            if not di1_status and not di2_status and not di3_status:
                    status = MoveStatus.FINISHED
            else:
                r.setMotorSpeed(roller_motor, self.unload_vel, -1)
                status = MoveStatus.RUNNING
        return status
    
    def isRollerMotorStopped(self, r, motor_name):
        speed = r.navSpeed()
        for iterm in speed['motor_cmd']:
            r.logInfo(str(iterm['motor_name']) + " : " + str(iterm['value']) + " " + motor_name)
            if str(iterm['motor_name']) == motor_name:
                if abs(iterm['value']) < 0.0001:
                    return True
                else:
                    return False
        return False
