# -*- coding: utf-8 -*-
# @Request :
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
        "default_value":["release","capture","clamp_open","clamp_close","stretch_out","stretch_back","forward","reversal","goPos"],
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
        self.left_clamp_motor_name = p.loadParam("left_clamp_motor_name", type="str", default="linearleft", comment="左夹爪电机名称")
        self.right_clamp_motor_name = p.loadParam("right_clamp_motor_name", type="str", default="linearright", comment="右夹爪电机名称")
        self.right_clamp_limit_di_open = p.loadParam("right_clamp_limit_di_open", type="int", default=4, comment="右夹爪开到位")
        self.right_clamp_limit_di_close = p.loadParam("right_clamp_limit_di_close", type="int", default=5, comment="右夹爪关到位")
        self.left_clamp_limit_di_open = p.loadParam("left_clamp_limit_di_open", type="int", default=0, comment="左夹爪开到位")
        self.stretch_limit_di_out = p.loadParam("stretch_limit_di_out", type="int", default=6, comment="伸缩到位DI")
        self.stretch_limit_di_back = p.loadParam("stretch_limit_di_back", type="int", default=7, comment="缩回到位DI")
        self.left_clamp_limit_di_close = p.loadParam("left_clamp_limit_di_close", type="int", default=1, comment="左夹爪关到位")
        self.stretch_out_DO = p.loadParam("stretch_out_DO", type="int", default=2, comment="伸缩机构伸出DO")
        self.stretch_DO = p.loadParam("stretch_DO", type="int", default=3, comment="伸缩机构激活DO、回原点DO")
        self.electromagnet_DO = p.loadParam("electromagnet_DO", type="int", default=5, comment="电磁铁DO")
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
        self.c_opt = [False]*6
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
            r.setDO(self.stretch_DO, False)
            r.setDO(self.stretch_out_DO, False)

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
            elif self.operation == "capture":
                if not self.c_opt[0]:
                    if not self.ModuleTool.check_DO(r,self.stretch_out_DO):
                        r.setDO(self.stretch_out_DO,False)
                        r.setDO(self.stretch_DO,False)
                        self.c_opt[0] = True
                if not self.c_opt[1] and self.c_opt[0]:
                    r.setDO(self.stretch_out_DO,True)
                    self.c_opt[1] = True
                if not self.c_opt[2] and self.c_opt[1]:
                    r.setDO(self.stretch_DO,True)
                    r.setDO(self.electromagnet_DO, True)
                    self.c_opt[2] = True
                if not self.c_opt[3] and self.c_opt[2]:
                    if self.ModuleTool.check_DI(r,self.stretch_limit_di_out):
                        r.setDO(self.stretch_DO, False)
                        r.setDO(self.stretch_out_DO, False)
                        self.c_opt[3] = True
                if not self.c_opt[4] and self.c_opt[3]:
                   if self.ModuleTool.delay(2):
                       r.setDO(self.stretch_DO, True)
                       self.c_opt[4] = True
                if not self.c_opt[5] and self.c_opt[4]:
                   if self.ModuleTool.check_DI(r,self.stretch_limit_di_back):
                       r.setDO(self.stretch_DO, False)
                       self.c_opt[5] = True
                if all(self.c_opt):
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
            elif self.operation == "clamp_open":
                r.setMotorSpeed(self.right_clamp_motor_name, float(self.motor_speed), self.right_clamp_limit_di_open)
                r.setMotorSpeed(self.left_clamp_motor_name, float(self.motor_speed), self.left_clamp_limit_di_open)
                self.state[f"{self.right_clamp_motor_name}"] = self.ModuleTool.get_motor_pos(r,self.right_clamp_motor_name)
                self.state[f"{self.left_clamp_motor_name}"] = self.ModuleTool.get_motor_pos(r,self.left_clamp_motor_name)
                if r.isMotorReached(self.right_clamp_motor_name) and r.isMotorReached(self.left_clamp_motor_name):
                    r.resetMotor(self.right_clamp_motor_name)
                    r.resetMotor(self.left_clamp_motor_name)
                    self.status = MoveStatus.FINISHED
            elif self.operation == "clamp_close":
                r.setMotorSpeed(self.right_clamp_motor_name, 0-float(self.motor_speed), self.right_clamp_limit_di_close)
                r.setMotorSpeed(self.left_clamp_motor_name, 0-float(self.motor_speed), self.left_clamp_limit_di_close)
                self.state[f"{self.right_clamp_motor_name}"] = self.ModuleTool.get_motor_pos(r,self.right_clamp_motor_name)
                self.state[f"{self.left_clamp_motor_name}"] = self.ModuleTool.get_motor_pos(r,self.left_clamp_motor_name)
                if r.isMotorReached(self.right_clamp_motor_name) and r.isMotorReached(self.left_clamp_motor_name):
                    r.resetMotor(self.right_clamp_motor_name)
                    r.resetMotor(self.left_clamp_motor_name)
                    self.status = MoveStatus.FINISHED
            elif self.operation == "stretch_out":
                if not self.ModuleTool.check_DO(r,self.stretch_out_DO):
                    r.setDO(self.stretch_out_DO,True)
                if not self.ModuleTool.check_DO(r,self.stretch_DO) and self.ModuleTool.check_DO(r,self.stretch_out_DO):
                    r.setDO(self.stretch_DO,True)
                    if self.ModuleTool.check_DO(r, self.stretch_DO):
                        r.setDO(self.stretch_DO, False)
                if not self.ModuleTool.check_DO(r,self.electromagnet_DO):
                    r.setDO(self.electromagnet_DO,True)
                if self.ModuleTool.check_DI(r,self.stretch_limit_di_out):
                    self.status = MoveStatus.FINISHED
            elif self.operation == "stretch_back":
                if self.ModuleTool.check_DI(r,self.stretch_limit_di_back):
                    self.status = MoveStatus.FINISHED
                else:
                    r.setDO(self.stretch_DO, False)
                    if self.ModuleTool.delay(1):
                        r.setDO(self.stretch_DO,True)
            elif self.operation == "release":
                if self.ModuleTool.check_DO(r,self.electromagnet_DO):
                    r.setDO(self.stretch_DO,False)
                if not self.ModuleTool.check_DO(r,self.electromagnet_DO):
                    self.status = MoveStatus.FINISHED
            else:
                r.setError(f"operation error:{self.operation}")
                self.status = MoveStatus.FAILED
            r.publishSpeed()

        if self.status == MoveStatus.FAILED or self.status == MoveStatus.FINISHED:
            r.setDO(self.stretch_DO, False)
            r.setDO(self.stretch_out_DO, False)
        self.state["DI"] = r.Di()
        self.state["DO"] = r.Do()
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