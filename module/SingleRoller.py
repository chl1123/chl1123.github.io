#广州望月
import json
import time
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.rbkSim import SimModule
"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value":[
        "RollerLoad","RollerUnLoad","RollerStop"
        ],
        "tips": "tips",
        "type": "complex"
    },
    "direction": {
        "value": "",
        "default_value":[
        "Left","Right"
        ],
        "tips": "tips",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""
class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.di1 = p.loadParam("di1", type="int", default = 23, maxValue = 100, minValue = 0, comment = "right di") #right
        self.di2 = p.loadParam("di2", type="int", default = 24, maxValue = 100, minValue = 0, comment = "mid di") #mid
        self.di3 = p.loadParam("di3", type="int", default = 25, maxValue = 100, minValue = 0, comment = "left di") #left
        self.left_block_motor = p.loadParam("left_block_motor", type="str", default = "motor3", comment = "motor_name")
        self.right_block_motor = p.loadParam("right_block_motor", type="str", default = "motor2", comment = "motor_name")
        self.block_vel = p.loadParam("block_vel", type="float", default = 1.0, maxValue = 2.0, minValue = 0.01, unit = "m/s", comment = "speed")
        self.left_roller_load_do = p.loadParam("left_roller_load_do", type="int", default = 24, maxValue = 100, minValue = 0, comment = "do id")
        self.left_roller_unload_do = p.loadParam("left_roller_unload_do", type="int", default = 23, maxValue = 100, minValue = 0, comment = "do id")
        self.left_roller_slow_do = p.loadParam("left_roller_slow_do", type="int", default = 25, maxValue = 100, minValue = 0, comment = "do id")
        self.right_roller_load_do = p.loadParam("right_roller_load_do", type="int", default = 23, maxValue = 100, minValue = 0, comment = "do id")
        self.right_roller_unload_do = p.loadParam("right_roller_unload_do", type="int", default = 24, maxValue = 100, minValue = 0, comment = "do id")
        self.right_roller_slow_do = p.loadParam("right_roller_slow_do", type="int", default = 25, maxValue = 100, minValue = 0, comment = "do id")
        self.operation = ""
        self.direction = ""
        self.task_list = []
        self.task_id = 0
        self.start_time = time.time()
        self.over_time = p.loadParam("over_time", type="float", default = 120.0, maxValue = 3600.0, minValue = 0.0, unit = "s", comment = "time")
        self.init = True
        self.operation_status = MoveStatus.NONE
        self.state = dict()
                           
    def run(self, r:SimModule,args):
        dt = time.time() - self.start_time
        if dt > self.over_time:
            self.status = MoveStatus.FAILED
            r.setError("Roller is over Time")
            return self.status
        self.status = MoveStatus.RUNNING
        self.state = dict()
        if self.init:
            self.init = False
            if "operation" not in args or "direction" not in args:
                r.setError("args error {}".format(json.dumps(args)))
                self.status = MoveStatus.FAILED
            else:
                self.operation = args["operation"]
                self.direction = args["direction"]
        if self.status is MoveStatus.FAILED:
            return self.status

        if self.operation == "RollerStop":
            #滚筒停止
            self.status = self.RollerStop(r)
        elif self.operation == "RollerLoad" and self.direction == "Right":
            self.load(r, self.right_block_motor, self.right_roller_load_do, self.right_roller_slow_do, self.right_roller_unload_do, self.di1, self.di2)
        elif self.operation == "RollerLoad" and self.direction == "Left":
            self.load(r, self.left_block_motor, self.left_roller_load_do, self.left_roller_slow_do, self.left_roller_unload_do, self.di3, self.di2)
        elif self.operation == "RollerUnLoad" and self.direction == "Right":
            self.unload(r, self.right_block_motor, self.right_roller_load_do, self.right_roller_slow_do, self.right_roller_unload_do, self.di1, self.di2)
        elif self.operation == "RollerUnLoad" and self.direction == "Left":
            self.unload(r, self.left_block_motor, self.left_roller_load_do, self.left_roller_slow_do, self.left_roller_unload_do, self.di3, self.di2)
        else:
            # 如果是不支持的operation则报错
            r.setError("operation: {}, direction: {} doesn't support!".format(self.operation, self.direction))
            self.status = MoveStatus.FAILED
        #发送速度
        if self.status is not MoveStatus.FAILED:
            if not r.publishSpeed():
                self.status = MoveStatus.FAILED
        self.status = self.operation_status
        self.state["status"] = self.status
        self.state["args"] = args
        str_state = json.dumps(self.state)
        r.setInfo(str_state)
        r.logDebug(str_state)
        return self.status
    
    def RollerStop(self, r):
        r.setDO(self.right_roller_load_do, False)
        r.setDO(self.right_roller_slow_do, False)
        r.setDO(self.right_roller_unload_do, False)
        r.setDO(self.left_roller_load_do, False)
        r.setDO(self.left_roller_slow_do, False)
        r.setDO(self.left_roller_unload_do, False)
        r.setMotorSpeed(self.left_block_motor, 0, -1)
        r.setMotorSpeed(self.right_block_motor, 0, -1)
        return MoveStatus.FINISHED

    def runTakList(self, r):
        """运行TaskList
        """
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(r, self)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED
        self.state["task_id"] = self.task_id
        self.state["task_list_size"] = len(self.task_list)

    def load(self,r, block_motor, load_do, load_slow_do, unload_do, di1, di2):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                BlockMotor(block_motor, "Down"),
                RollerMotor("Load", load_do, load_slow_do, unload_do, di1, di2),
                BlockMotor(block_motor, "Up")
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state 

    def unload(self,r, block_motor, load_do, load_slow_do, unload_do, di1, di2):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                BlockMotor(block_motor, "Down"),
                RollerMotor("Unload", load_do, load_slow_do, unload_do, di1, di2),
                BlockMotor(block_motor, "Up")
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["unload"] = cur_state  

class BlockMotor:
    def __init__(self, motor_name, operation):
        """挡板电机初始化

        Args:
            motor_name (string): 电机名称
            operation (string): 执行方式"Up"或者"Down"
        """
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.operation = operation
    def reset(self, r:SimModule, roller):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING
    def run(self, r:SimModule, roller):
        self.status = MoveStatus.RUNNING
        if self.operation == "Up":
            # r.setMotorSpeed(self.motor, roller.block_vel, -1)
            r.setMotorPosition(self.motor,0.0, 1.0, -1)
            if r.isMotorReached(self.motor):
                self.status = MoveStatus.FINISHED
        elif self.operation == "Down":
            r.setMotorPosition(self.motor, -0.8, 1.0, -1)
            # r.setMotorSpeed(self.motor, -roller.block_vel, -1)
            if r.isMotorReached(self.motor):
                self.status = MoveStatus.FINISHED
        state = dict()
        state["operation"] = self.operation
        state["status"] = self.status
        roller.state["BlockMotor"] = state
        

class RollerMotor:
    """控制roller电机
    """
    def __init__(self, operation, load_do, load_slow_do, unload_do, di1, di2):
        """初始化

        Args:
            operation (string): 电机执行的方式 Load或者Unload
            load_do (int): 电机Load
            load_slow_do (int): 电机Load Slow
            unload_do (int): 电机unLoad
            di1 (int): 外侧di序号
            di2 (int): 中间di序号
        """
        self.status = MoveStatus.NONE
        self.operation = operation
        self.load_do = load_do
        self.load_slow_do = load_slow_do
        self.unload_do = unload_do
        self.di1 = di1
        self.di2 = di2
    def reset(self, r, roller):
        self.status = MoveStatus.RUNNING
    def run(self, r:SimModule, roller):
        self.status = MoveStatus.RUNNING
        di = r.Di()
        di1_status = True
        di2_status = True
        for (ind,node) in enumerate(di['node']):
            if node['id'] == self.di1:
                di1_status = node['status']
            elif node['id'] == self.di2:
                di2_status = node['status']
        if self.operation == "Load":
            if not di2_status:
                r.setDO(self.load_do, True)
            if di2_status and di1_status:
                r.setDO(self.load_do, True)
                r.setDO(self.load_slow_do, True)
            if di2_status and not di1_status:
                r.setDO(self.load_slow_do, False)
                r.setDO(self.load_do, False)
                r.setDO(self.unload_do, False)
                self.status = MoveStatus.FINISHED
        elif self.operation == "Unload":
            if not di1_status and not di2_status:
                r.setDO(self.load_slow_do, False)
                r.setDO(self.load_do, False)
                r.setDO(self.unload_do, False)
                self.status = MoveStatus.FINISHED
            else:
                r.setDO(self.unload_do, True)
        state = dict()
        state["operation"] = self.operation
        state["status"] = self.status
        roller.state["RollerMotor"] = state

if __name__ == '__main__':
    import syspy.rbkSim
    r = syspy.rbkSim.SimModule()
    m = Module(r,None)
    data = dict()
    data["operation"] = "RollerLoad"
    data["direction"] = "Right"
    print(m.run(r, data))