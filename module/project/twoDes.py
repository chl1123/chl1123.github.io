# 这个是给井智开发的前移货叉脚本
# 主要功能：控制前移货叉举升，迁移，车体后退，以及前移货叉的碰撞阻挡
# 使用前需要配置 货叉到位检测DI与货叉尖端检测。相应代码如下：
#        self.reach_num1 = 9  # 货叉到位检测DI1
#        self.reach_num2 = 1  # 货叉到位检测DI2
#        self.fork_tailDI1 = -1 # 货叉尖端检测DI1
#        self.fork_tailDI2 = -1 # 货叉尖端检测DI2
import json
import time
import math
import sys, os

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(path)
path = os.path.join(path, "syspy")
sys.path.append(path)
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer, CollisionType
import syspy.goPath as goPath

"""
####BEGIN DEFAULT ARGS####
{
    "liftDist": {
        "value": 0.,
        "tips": "lift hight",
        "type": "double",
        "unit": "m"
    },   
    "operation":{
        "value": "zero",
        "default_value":[
        "zero","liftAndStretch","stretchBackLift"
        ],
        "tips": "tips",
        "type": "complex"        
    },    
    "stretchDist": {
        "value": 0.,
        "tips": "stretch dis",
        "type": "double",
        "unit": "m"
    },
    "backDist": {
        "value": 0.,
        "tips": "back dis",
        "type": "double",
        "unit": "m"
    },
    "backSpeed": {
        "value": 0.2,
        "tips": "后退速度",
        "type": "double",
        "unit": "m/s"
    },
    "action":{
        "value": "Load",
        "default_value":[
        "Load","Unload"
        ],
        "tips":"所执行的动作",
        "type":"complex"
    } 
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.status = MoveStatus.RUNNING
        self.lift_motor = "motor2"  # 提升电机
        self.stretch_motor = "motor3"  # 前移电机
        self.operation = ""  # 定义操作
        self.lift_dist = None  # 提升距离设定
        self.stretch_dist = None  # 前移距离设定
        self.back_dist = None
        self.reach_num1 = 9  # 货叉到位检测DI1
        self.reach_num2 = 1  # 货叉到位检测DI2
        self.fork_tailDI1 = -1 # 货叉尖端检测DI1
        self.fork_tailDI2 = -1 # 货叉尖端检测DI2
        self.task_list = []
        self.task_id = 0
        self.init = True
        self.state = dict()
        self.lift_zero = 0.08  # 提升零位
        self.stretch_zero = 0.035  # 前移零位
        self.operation_status = MoveStatus.NONE
        self.back_speed = None
        self.action = None
        self.goPath = goPath.Module(r, args)

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            if "operation" not in args or "action" not in args:
                r.setError("user args error {}".format(json.dumps(args)))
                self.status = MoveStatus.FAILED
            else:
                self.operation = args["operation"]
                self.lift_dist = args.get("liftDist", None)
                self.stretch_dist = args.get("stretchDist", None)
                self.back_dist = args.get("backDist", None)
                self.back_speed = args.get("backSpeed", None)
                self.action = args.get("action", None)

        if self.status is MoveStatus.FAILED:
            return self.status
        if self.operation == "zero":
            # r.setError(args["operation"])
            self.zero(r)
        if self.operation == "liftAndStretch":
            self.liftAndStretch(r)
        elif self.operation == "stretchBackLift":
            self.stretchBackLift(r)
        if self.status is not MoveStatus.FAILED:
            if not r.publishSpeed():
                self.status = MoveStatus.FAILED
        if self.status is not MoveStatus.FAILED:
            self.status = self.operation_status
        self.state["status"] = self.status
        self.state["args"] = args
        str_state = json.dumps(self.state)
        r.setInfo(str_state)
        r.logDebug(str_state)
        return self.status

    def liftAndStretch(self, r):
        if (not self.is_number(self.lift_dist) or self.lift_dist < 0) or (
                not self.is_number(self.stretch_dist) or self.stretch_dist < 0):
            self.status = MoveStatus.FAILED  # 导航状态
            r.setError("lift or stretch 's Dist is zero or <0.0")
            return self.status
        elif self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                StretchMotor(self.stretch_motor, self.stretch_dist, self.reach_num1, self.reach_num2),
                LiftMotor(self.lift_motor, self.lift_dist),
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["lift"] = cur_state

    def stretchBackLift(self, r):
        if not self.is_number(self.lift_dist) or self.lift_dist < 0 \
                or not self.is_number(self.stretch_dist) or self.stretch_dist < 0 \
                or not self.is_number(self.back_dist) or self.back_dist < 0:
            self.status = MoveStatus.FAILED  # 导航状态
            r.setError("lift or stretch or back Dist is zero or <0.0")
            return self.status
        elif self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if self.action == "Load":
                self.task_list = [
                    StretchMotor(self.stretch_motor, self.stretch_dist, self.reach_num1, self.reach_num2, self.action),
                    GoBack(self.back_dist, self.reach_num1, self.reach_num2, self.goPath),
                    LiftMotor(self.lift_motor, self.lift_dist,self.reach_num1, self.reach_num2),
                ]
            if self.action == "Unload":
                self.task_list = [
                    StretchMotor(self.stretch_motor, self.stretch_dist, self.reach_num1, self.reach_num2, self.action),
                    LiftMotor(self.lift_motor, self.lift_dist,self.reach_num1, self.reach_num2),
                ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["state"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["stretchBackLift"] = cur_state

    def zero(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                StretchMotor(self.stretch_motor, self.stretch_zero, self.reach_num1,
                             self.reach_num2,self.action),
                LiftMotor(self.lift_motor, self.lift_zero, self.reach_num1, self.reach_num2),
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

    def is_number(self, s):
        if s is None:
            return False
        try:
            float(s)  # for int, long and float
        except ValueError:
            try:
                complex(s)  # for complex
            except ValueError:
                return False
        return True

    def cancel(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("script cancel")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("script suspended")
        self.status = MoveStatus.SUSPENDED
        self.start_connect_time = time.time()


class LiftMotor:
    """提升电机操作
    Args: status 状态；
          motor:电机名称；
          dist:电机行驶距离；
          init：是否是第一次初始化
    """

    def __init__(self, motor_name, dist, reach_num1, reach_num2):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
        self.init = True
        self.reach_num1 = reach_num1
        self.reach_num2 = reach_num2

    def run(self, r: SimModule, agv: Module):
        self.status = MoveStatus.RUNNING
        di = r.Di()
        reach_num1_status = False
        reach_num2_status = False
        for (ind, node) in enumerate(di['node']):
            if node['id'] == self.reach_num1:
                reach_num1_status = node['status']
            elif node['id'] == self.reach_num2:
                reach_num2_status = node['status']
        if self.init:
            self.init = False

        if reach_num1_status and reach_num2_status:
            r.setMotorPosition(self.motor, self.dist, 0.1, -1)
            if r.isMotorReached(self.motor):
                self.status = MoveStatus.FINISHED
        else:
            self.status = MoveStatus.FAILED
            r.setError("materials is not exist,so must to sure material existed or backDist latter")
        cur_state = dict()
        cur_state['lift_state'] = self.status
        cur_state['dist'] = self.dist
        agv.state['lift_org'] = cur_state

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING
        self.init = True


class StretchMotor:
    """前移电机操作
    Args: status 状态；
          motor:电机名称；
          dist:电机行驶距离；
          init：是否是第一次初始化
          reach_num1:货物到位检测传感器编号1
          reach_num2:货物到位检测传感器编号2
          action:取、放货操作
    """

    def __init__(self, motor_name, dist, reach_num1, reach_num2, action):
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.dist = dist
        self.init = True
        self.reach_num1 = reach_num1
        self.reach_num2 = reach_num2
        self.action = action

    def run(self, r: SimModule, agv: Module):
        di = r.Di()
        reach_num1_status = False
        reach_num2_status = False
        tailDI1_status = False
        tailDI1x = 0
        tailDI1y = 0
        tailDI2_status = False
        tailDI2x = 0
        tailDI2y = 0
        hasDI1 = False
        hasDI2 = False
        for (ind, node) in enumerate(di['node']):
            if node['id'] == self.reach_num1:
                reach_num1_status = node['status']
            elif node['id'] == self.reach_num2 :
                reach_num2_status = node['status']
            elif node['id'] == agv.fork_tailDI1:
                tailDI1_status = node['status']
                tailDI1x = node['x']
                tailDI1y = node['y']
                hasDI1 = True
            elif node['id'] == agv.fork_tailDI2:
                tailDI2_status = node['status']
                tailDI2x = node['x']
                tailDI2y = node['y']
                hasDI2 = True
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
        if tailDI1_status or tailDI2_status:
            r.setBlockError()
            if tailDI1_status:
                r.setBlockReason(CollisionType.Infrared, tailDI1x, tailDI1y, agv.fork_tailDI1)
                r.logDebug("[StopPoints|{}|{}|{}|{}|{}]".format(tailDI1x, tailDI1y,CollisionType.Infrared,agv.fork_tailDI1,0))
            elif tailDI2_status:
                r.setBlockReason(CollisionType.Infrared, tailDI2x, tailDI2y, agv.fork_tailDI2)
                r.logDebug("[StopPoints|{}|{}|{}|{}|{}]".format(tailDI2x, tailDI2y,CollisionType.Infrared,agv.fork_tailDI2,0))
            r.setMotorSpeed(self.motor, 0, -1)
        else:
            r.clearBlockError()
            if self.action == "Load":
                r.setMotorPosition(self.motor, self.dist, 0.1, -1)
                # r.setError("num1{} num2{}".format(reach_num1_status,reach_num2_status))
                if r.isMotorReached(self.motor) or reach_num1_status or reach_num2_status:
                    r.isMotorStop(self.motor)
                    r.resetMotor(self.motor)
                    self.status = MoveStatus.FINISHED
            if self.action == "Unload" or reach_num1_status or reach_num2_status:
                r.setMotorPosition(self.motor, self.dist, 0.1, -1)
                # r.setError("num1{} num2{}".format(reach_num1_status,reach_num2_status))
                if r.isMotorReached(self.motor):
                    r.isMotorStop(self.motor)
                    self.status = MoveStatus.FINISHED
        cur_state = dict()
        cur_state['lift_state'] = self.status
        cur_state['dist'] = self.dist
        agv.state['lift_org'] = cur_state
        r.logDebug("[twoDos|{}|{}|{}|{}|{}|{}]".format(agv.fork_tailDI1, agv.fork_tailDI2, tailDI1_status, tailDI2_status,
            hasDI1, hasDI2))

    def reset(self, r):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING
        self.init = True


class GoBack:
    """前移电机操作
    Args: status 状态；
          dist:倒车距离
          init：是否是第一次初始化
          reach_num1:货物到位检测传感器编号1
          reach_num2:货物到位检测传感器编号2
    """

    def __init__(self, dist, reach_num1, reach_num2, goPath):
        self.status = MoveStatus.NONE
        self.dist = dist
        self.init = True
        self.reach_num1 = reach_num1
        self.reach_num2 = reach_num2
        self.go_args = dict()
        self.goPath = goPath

    def run(self, r: SimModule, agv: Module):
        if self.init:
            self.go_args = dict()
            self.go_args["coordinate"] = "robot"
            self.go_args["x"] = -self.dist
            self.go_args["y"] = 0
            self.go_args["theta"] = 0
            self.go_args["reachAngle"] = math.pi
            self.go_args["reachDist"] = 0.002
            self.go_args["backMode"] = 1
            if agv.back_speed is not None:
                self.go_args["maxSpeed"] = agv.back_speed
            self.init = False
        di = r.Di()
        reach_num1_status = False
        reach_num2_status = False
        for (ind, node) in enumerate(di['node']):
            if node['id'] == self.reach_num1:
                reach_num1_status = node['status']
            elif node['id'] == self.reach_num2:
                reach_num2_status = node['status']
        self.status = MoveStatus.RUNNING
        if reach_num1_status or reach_num2_status:
            self.status = MoveStatus.FINISHED
            r.stopRobot(False)
        else:
            if self.goPath.status != MoveStatus.FINISHED and self.goPath.status != MoveStatus.FAILED:
                self.goPath.run(r, self.go_args)
            self.status = self.goPath.status
        cur_state = dict()
        cur_state['state'] = self.status
        cur_state['dist'] = self.dist
        cur_state['di1'] = reach_num1_status
        cur_state['di2'] = reach_num2_status
        agv.state['goBack'] = cur_state

    def reset(self, r):
        self.goPath.reset()
        self.status = MoveStatus.RUNNING
        self.init = True


if __name__ == '__main__':
    import syspy.rbkSim

    r = syspy.rbkSim.SimModule()
    m = Module(r, None)
    data = dict()
    data["operation"] = "stretchBackLift"
    data["liftDist"] = 0.3
    data["stretchDist"] = 0.4
    data["backDist"] = 0.3
    print(m.run(r, data))
    print(m.run(r, data))
