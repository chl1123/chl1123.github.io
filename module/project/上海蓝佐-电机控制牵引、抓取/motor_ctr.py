# -*- coding: utf-8 -*-
# @Request : 用于 测试 resetGoForkPath 和 goForkPath 接口
# @Version: 1.0
import json
import math
import sys
import time

sys.path.append("../syspy")
import syspy.goPath
from syspy import goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.robot import ModuleTool, Motor, MotorType, Robot, GoodsManger


"""

####BEGIN DEFAULT ARGS####
{
    "motor_name": {
        "value": "lift",
        "default_value": "LIFT",
        "tips": "tips",
        "type": "string"
    },
    "operation":{
        "value": "forward",
        "default_value":["forward","reversal","goPos"],
        "tips": "选择模式",
        "type": "complex"
    },
    "position":{
        "value": 0.0,
        "default_value":0.0,
        "tips": "位置",
        "type": "float"
    },
    "limit_di":{
        "value": 1,
        "default_value":1,
        "tips": "到位DI",
        "type": "int"
    },
    "motor_speed": {
        "value": 0.1,
        "default_value": 0.1,
        "tips": "速度",
        "type": "string"
    }
}

####END DEFAULT ARGS####
"""
class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super().__init__()
        self.position = 0
        p = ParamServer(__file__)
        self.motor_name = p.loadParam("motor_name", type="str", default="lift", comment="motor_name")
        self.limit_di = p.loadParam("limit_di", type="int", default=1, comment="limit_di")
        self.motor = Motor(r, MotorType.LINEAR_MOTOR, self.motor_name, -1)
        self.motor_speed = p.loadParam("motor_speed", type="float", default=0.1, comment="电机运转速度")
        self.operation = None
        self.init = True
        self.state = {}
        self.robot = Robot(r)
        self.ModuleTool = ModuleTool()
        self.init_time = time.time()
        self.height = 0
        r.logInfo(f"init args:{args}")

    def periodRun(self, r: SimModule):
        # self.state["task"] = r.moveTask()
        # # self.state["taskSTATUS"] = r.getCurrentTaskStatus()
        # # if ModuleTool.check_DI(r,2):
        # #     r.stopRobot(True)
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        return True

    def run(self, r: SimModule, args:dict):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            if args.get("operation",None):
                self.operation = args.get("operation",None)
            if args.get("motor_name",None):
                self.motor_name = args.get("motor_name",None)
            if args.get("motor_speed",None):
                self.motor_speed = args.get("motor_speed",None)
            if args.get("limit_di", None):
                self.limit_di = args.get("limit_di",None)
            if args.get("position", None):
                self.position = args["position"]
                if self.operation == "goPos" and self.position is None:
                    r.setError(f"请输入电机位置")
                    self.status = MoveStatus.FAILED
                    return
            self.motor = Motor(r, MotorType.LINEAR_MOTOR, self.motor_name, -1)
            self.robot = Robot(r)

        if self.status != MoveStatus.FAILED or self.status != MoveStatus.FINISHED and not self.init:
            if self.operation == "forward":
                r.setMotorSpeed(self.motor_name, float(self.motor_speed), self.limit_di)
                if r.isMotorReached(self.motor_name):
                    r.resetMotor(self.motor_name)
                    self.status = MoveStatus.FINISHED
            elif self.operation == "reversal":
                r.setMotorSpeed(self.motor_name, 0 - float(self.motor_speed), self.limit_di)
                if r.isMotorReached(self.motor_name) or self.ModuleTool.check_DI(r, self.limit_di):
                    r.resetMotor(self.motor_name)
                    self.status = MoveStatus.FINISHED
            elif self.operation == "goPos":
                r.setMotorPosition(self.motor_name, float(self.position), 1.0, -1)
                if r.isMotorReached(self.motor_name):
                    r.resetMotor(self.motor_name)
                    self.status = MoveStatus.FINISHED
            else:
                r.setError(f"operation error:{self.operation}")
                self.status = MoveStatus.FAILED
            r.publishSpeed()

        self.state["motor_name"] = self.motor_name
        self.state["operation"] = self.operation
        self.state['motor_pos'] = self.ModuleTool.get_motor_pos(r, self.motor_name)
        self.state['motor_speed'] = self.ModuleTool.get_motor_speed(r, self.motor_name)
        self.state['limit_di'] = self.ModuleTool.check_DI(r,self.limit_di)
        self.state['position'] = self.position
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        return self.status

    def cancel(self, r: SimModule):
        r.stopMotor()
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.logInfo("task suspend")
        r.stopMotor()
        self.status = MoveStatus.SUSPENDED

if __name__ == '__main__':
    pass