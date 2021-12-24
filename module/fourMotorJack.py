# -*- coding: utf-8 -*-
# @Date : 2021/12/23 15:24
# @Author : zhong
# @File :fourMotorJack.py.py
# @Version : 1.1
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
        "value": 0.01,
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
        self.motor_name1 = p.loadParam("MotorName1", type="str", default="motor2", comment="电机1名称")
        self.motor_name2 = p.loadParam("MotorName2", type="str", default="motor3", comment="电机2名称")
        self.motor_name3 = p.loadParam("MotorName3", type="str", default="motor4", comment="电机3名称")
        self.motor_name4 = p.loadParam("MotorName4", type="str", default="motor5", comment="电机4名称")
        self.up_limit_di1 = p.loadParam("UpLimitDi1", type="int", default=1, comment="电机1上限位DI")
        self.up_limit_di2 = p.loadParam("UpLimitDi2", type="int", default=4, comment="电机2上限位DI")
        self.up_limit_di3 = p.loadParam("UpLimitDi3", type="int", default=6, comment="电机3上限位DI")
        self.up_limit_di4 = p.loadParam("UpLimitDi4", type="int", default=8, comment="电机4上限位DI")
        self.zero_di1 = p.loadParam("ZeroDi1", type="int", default=0, comment="电机1零位DI")
        self.zero_di2 = p.loadParam("ZeroDi2", type="int", default=2, comment="电机2零位DI")
        self.zero_di3 = p.loadParam("ZeroDi3", type="int", default=5, comment="电机3零位DI")
        self.zero_di4 = p.loadParam("ZeroDi4", type="int", default=7, comment="电机4零位DI")
        self.shelf_file = p.loadParam("ShelfFile", type="str", default="", comment="货物模型文件，默认为空")
        self.default_height = p.loadParam("DefaultHeight", type="float", default=0.01, comment="顶升默认上升高度")

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
                if args["loadHeight"] <= 0:
                    self.height = 0.00001
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
        if check_DI(r, self.up_limit_di1) or check_DI(r, self.up_limit_di2) or check_DI(r, self.up_limit_di3) or check_DI(r, self.up_limit_di4):
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
        # self.state["motors"] = {
        #     self.motor_name1: {"upLimitDi": self.up_limit_di1, "zeroDi": self.zero_di1, "reach": r.isMotorReached(self.motor_name1), "stop": r.isMotorStop(self.motor_name1)},
        #     self.motor_name2: {"upLimitDi": self.up_limit_di2, "zeroDi": self.zero_di2, "reach": r.isMotorReached(self.motor_name2), "stop": r.isMotorStop(self.motor_name2)},
        #     self.motor_name3: {"upLimitDi": self.up_limit_di3, "zeroDi": self.zero_di3, "reach": r.isMotorReached(self.motor_name3), "stop": r.isMotorStop(self.motor_name3)},
        #     self.motor_name4: {"upLimitDi": self.up_limit_di4, "zeroDi": self.zero_di4, "reach": r.isMotorReached(self.motor_name4), "stop": r.isMotorStop(self.motor_name4)},
        # }
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
            self.opt_status[i] = self.robot.jack(self.jack_motors[i], 0.00001)
        if all(self.opt_status):
            r.clearGoodsShape()
            r.resetLocalShelfArea()
            self.status = MoveStatus.FINISHED
        unload_state = dict()
        unload_state['otp_name'] = "JackUnload"
        unload_state['status'] = self.opt_status
        unload_state['actions'] = self.robot.state
        self.state['operation'] = unload_state

    def cancel(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("task cancel")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.stopRobot(False)
        r.logInfo("task suspend")
        self.status = MoveStatus.SUSPENDED


if __name__ == '__main__':
    r = SimModule()
    m = Module(r, {})
    print(m.__dict__)
