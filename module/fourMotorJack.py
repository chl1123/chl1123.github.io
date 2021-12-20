# -*- coding: utf-8 -*-
# @Date : 2021/12/20 13:24
# @Author : zhong
# @File :fourMotorJack.py.py
# @Version : 1.0
# @Project : 大族 4电机顶升
import json

from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
from robot import Motor, MotorType, Robot, check_DI


""" 
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value": [
            "JackLoad", "JackUnload"
        ],
        "type": "complex"
    },
    "loadHeight": {
        "value": 0.0,
        "tips": "指定上升高度，可选参数",
        "type": "float",
        "unit": "m"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.shelf_file = p.loadParam("ShelfFile", type="str", default="", comment="货物模型文件，默认为空")
        self.motor_name1 = p.loadParam("MotorName1", type="str", default="motor1", comment="电机名称1")
        self.motor_name2 = p.loadParam("MotorName2", type="str", default="motor2", comment="电机名称2")
        self.motor_name3 = p.loadParam("MotorName3", type="str", default="motor3", comment="电机名称3")
        self.motor_name4 = p.loadParam("MotorName4", type="str", default="motor4", comment="电机名称4")
        self.zero_height = p.loadParam("ZeroHeight", type="float", default=0.001, comment="顶升零位高度")
        self.default_height = p.loadParam("DefaultHeight", type="float", default=0.05, comment="顶升默认上升高度")
        self.up_limit_di = p.loadParam("UpLimitDi", type="int", default=-1, comment="上限位DI")
        self.init = True
        self.status = MoveStatus.NONE
        self.height = None
        self.state = dict()
        self.robot = Robot(r)
        self.opt_status = [False]*4
        self.jack_motors = list()
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        if self.init:
            self.init = False
            if "loadHeight" in args:
                self.height = args["loadHeight"]
                if args["loadHeight"] < self.zero_height:
                    self.height = self.zero_height
            else:
                self.height = self.default_height
            if "operation" not in args:
                r.setError(f"args error: {args}")
                return MoveStatus.FAILED
            self.jack_motors.append(Motor(r, MotorType.LINEAR_MOTOR, self.motor_name1, -1))
            self.jack_motors.append(Motor(r, MotorType.LINEAR_MOTOR, self.motor_name2, -1))
            self.jack_motors.append(Motor(r, MotorType.LINEAR_MOTOR, self.motor_name3, -1))
            self.jack_motors.append(Motor(r, MotorType.LINEAR_MOTOR, self.motor_name4, -1))

        self.status = MoveStatus.RUNNING
        if check_DI(r, self.up_limit_di):
            r.setError(f"触发上限位DI")
            self.status = MoveStatus.FAILED
        if args["operation"] == "JackLoad":
            self.jack_load(r)
        elif args["operation"] == "JackUnload":
            self.jack_unload(r)
        else:
            r.setError(f"operation args error: {args}")
            self.status = MoveStatus.FAILED

        r.publishSpeed()
        self.state["status"] = self.status
        self.state["args"] = args
        self.state["has_goods"] = r.hasGoods()
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        return self.status

    def jack_load(self, r):
        for i in range(4):
            self.opt_status[i] = self.robot.jack(self.jack_motors[i], self.height)
        if all(self.opt_status):
            r.setGoodsShape(0, 0, 0)
            if self.shelf_file != "":
                r.setLocalShelfArea(self.shelf_file)
            self.status = MoveStatus.FINISHED
        load_state = dict()
        load_state['otp_name'] = "JackLoad"
        load_state['status'] = self.opt_status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state

    def jack_unload(self, r):
        for i in range(4):
            self.opt_status[i] = self.robot.jack(self.jack_motors[i], self.zero_height)
        if all(self.opt_status):
            r.clearGoodsShape()
            r.resetLocalShelfArea()
            self.status = MoveStatus.FINISHED
        load_state = dict()
        load_state['otp_name'] = "JackUnload"
        load_state['status'] = self.opt_status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state

    def cancel(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("task cancel")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.stopRobot(False)
        r.logInfo("task suspend")
        self.status = MoveStatus.SUSPENDED


if __name__ == '__main__':
    print(Module.__dict__)
