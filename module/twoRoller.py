import json
import time
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.rbkSim import SimModule

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
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.front_di1 = p.loadParam("front_di1", type="int", default = 5, maxValue = 100, minValue = 0, comment = "di id")
        self.front_di2 = p.loadParam("front_di2", type="int", default = 4, maxValue = 100, minValue = 0, comment = "di id")
        self.front_di3 = p.loadParam("front_di3", type="int", default = 3, maxValue = 100, minValue = 0, comment = "di id")
        self.back_di1 = p.loadParam("back_di1", type="int", default = 8, maxValue = 100, minValue = 0, comment = "di id")
        self.back_di2 = p.loadParam("back_di2", type="int", default = 7, maxValue = 100, minValue = 0, comment = "di id")
        self.back_di3 = p.loadParam("back_di3", type="int", default = 6, maxValue = 100, minValue = 0, comment = "di id")
        self.front_block_motor = p.loadParam("front_block_motor", type="str", default = "frontDOMotor", comment = "motor name")
        self.back_block_motor = p.loadParam("back_block_motor", type="str", default = "backDOMotor", comment = "motor name")
        self.mid_block_motor = p.loadParam("mid_block_motor", type="str", default = "midDOMotor", comment = "motor name")
        self.front_roller = p.loadParam("front_roller", type="str", default = "frontMotor", comment = "motor name")
        self.back_roller = p.loadParam("back_roller", type="str", default = "backMotor", comment = "motor name")
        self.operation = ""
        self.load_vel = p.loadParam("load_vel", type="float", default = 1.0, maxValue = 2.0, minValue = -2.0, unit = "m/s", comment = "speed")
        self.unload_vel = p.loadParam("unload_vel", type="float", default = -1.0, maxValue = 2.0, minValue = -2.0, unit = "m/s", comment = "speed")
        self.start_time = time.time()
        self.over_time = p.loadParam("over_time", type="float", default = 120.0, maxValue = 36000.0, minValue = 1.0, unit = "s", comment = "time")
        self.init = True

    def operationCheck(self, r:SimModule, args):
        r.logInfo(str(args))
        self.status = MoveStatus.RUNNING
        if "operation" in args:
            self.operation = args["operation"]
        if self.operation is not "":
            r.logDebug(self.operation)
            if self.operation == "FrontRollerLoad":
                #1前滚筒进货
                r.setMotorSpeed(self.mid_block_motor, 1.0, -1)
                if not r.isMotorReached(self.mid_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError("mid block is not in the up cannot load")
                r.setMotorSpeed(self.front_block_motor, -1.0, -1)
                if not r.isMotorReached(self.front_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError("front block is not in the bottom cannot load")
            elif self.operation == "FrontRollerUnLoad":
                #2前滚筒卸货
                pass
            elif self.operation == "BackRollerLoad":
                #3后滚筒进货
                r.setMotorSpeed(self.mid_block_motor, 1.0, -1)
                if not r.isMotorReached(self.mid_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError("mid block is not in the up cannot load")
                r.setMotorSpeed(self.back_block_motor, -1.0, -1)
                if not r.isMotorReached(self.back_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError("front block is not in the bottom cannot load")
                pass
            elif self.operation == "BackRollerUnLoad":
                #4后滚筒卸货
                pass
            elif self.operation == "FrontBackLoad":
                #5前后滚筒分开进货
                r.setMotorSpeed(self.back_block_motor, -1.0, -1)
                if not r.isMotorReached(self.back_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError( "back block is not in the up cannot load")
                r.setMotorSpeed(self.front_block_motor, -1.0, -1)
                if not r.isMotorReached(self.front_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError("front block is not in the bottom cannot load")
            elif self.operation == "FrontBackUnLoad":
                #6前后滚筒分开卸货
                pass
            elif self.operation == "AllRollerLoad":
                #7所有滚筒一起进货
                r.setMotorSpeed(self.back_block_motor, -1.0, -1)
                if not r.isMotorReached(self.back_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError("back block is not in the bottom cannot load")
                r.setMotorSpeed(self.front_block_motor, -1.0, -1)
                if not r.isMotorReached(self.front_block_motor):
                    self.status = MoveStatus.FAILED
                    r.setError("front block is not in the bottom cannot load")
            elif self.operation == "AllRollerUnLoad":
                #8所有滚筒一起卸货
                pass
            else:
                pass
        return self.status
                           
    def run(self, r:SimModule,args):
        dt = time.time() - self.start_time
        if dt > self.over_time:
            self.status = MoveStatus.FAILED
            r.setError("Roller is over Time")
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
                r.setError("Operation: " + self.operation + " doesn't support")
                self.status = MoveStatus.FAILED
            #发送速度
            if self.status is not MoveStatus.FAILED and self.status is not MoveStatus.FINISHED:
                if not r.publishSpeed():
                    self.status = MoveStatus.FAILED
        else:
            self.status = MoveStatus.FINISHED
        return self.status.value
    
    def SingleRollerLoad(self, r:SimModule, di1, di2, di3, roller_motor, block_motor):
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

    def SingleRollerUnLoad(self, r:SimModule, di1, di2, di3, roller_motor, block_motor):
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
    
    def isRollerMotorStopped(self, r:SimModule, motor_name):
        speed = r.navSpeed()
        for iterm in speed['motor_cmd']:
            r.logInfo(str(iterm['motor_name']) + " : " + str(iterm['value']) + " " + motor_name)
            if str(iterm['motor_name']) == motor_name:
                if abs(iterm['value']) < 0.0001:
                    return True
                else:
                    return False
        return False

if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["operation"] = "RollerLoad"
    data["direction"] = "Right"
    print(m.run(r, data))