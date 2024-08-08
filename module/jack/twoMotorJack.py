# -*- coding: utf-8 -*-
# @Date : 2022/5/25 15:25
# @Author : zhong
# @File :twoMotorJack.py.py
# @Version : 1.0
# @Project : 双电机顶升
import json

from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
from robot import Motor, MotorType, Robot, ModuleTool


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
        "value": 0.05,
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
        self.up_limit_di1 = p.loadParam("UpLimitDi1", type="int", default=1, comment="电机1上限位DI")
        self.up_limit_di2 = p.loadParam("UpLimitDi2", type="int", default=4, comment="电机2上限位DI")
        self.zero_di1 = p.loadParam("ZeroDi1", type="int", default=0, comment="电机1零位DI")
        self.zero_di2 = p.loadParam("ZeroDi2", type="int", default=2, comment="电机2零位DI")
        self.shelf_file = p.loadParam("ShelfFile", type="str", default="", comment="货物模型文件，默认为空")
        self.default_height = p.loadParam("DefaultHeight", type="float", default=0.05, comment="顶升默认上升高度")
        self.extremum_diff = p.loadParam("ExtremumDiff", type="float", default=0.001, comment="多电机同步时编码器极值差阈值")
        self.variance = p.loadParam("Variance", type="float", default=1.0, comment="多电机同步时编码器方差阈值")

        self.init = True
        self.status = MoveStatus.NONE
        self.height = None
        self.state = dict()
        self.robot = Robot(r)
        self.opt_status = [False]*2
        self.jack_motors = list()
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        if self.init:
            self.init = False
            if "loadHeight" in args:
                self.height = args["loadHeight"]
                if args["loadHeight"] <= 0:
                    self.height = 0.000001
            else:
                self.height = self.default_height
            if "operation" not in args:
                r.setError(f"args error: {args}")
                return MoveStatus.FAILED
            self.jack_motors.append(Motor(r, MotorType.LINEAR_MOTOR, self.motor_name1, -1))
            self.jack_motors.append(Motor(r, MotorType.LINEAR_MOTOR, self.motor_name2, -1))

        self.status = MoveStatus.RUNNING
        if ModuleTool.check_DI(r, self.up_limit_di1) or ModuleTool.check_DI(r, self.up_limit_di2):
            r.setError(f"触发上限位DI")
            self.status = MoveStatus.FAILED
        if args["operation"] == "JackLoad":
            self.jack_load(r)
        elif args["operation"] == "JackUnload":
            self.jack_unload(r)
        else:
            r.setError(f"operation args error: {args}")
            self.status = MoveStatus.FAILED
        # 电机控制方案速度规划和下发
        r.publishSpeed()
        # 多电机同步机制安全检查
        motor_pos = []
        for motor_name in [self.motor_name1, self.motor_name2]:
            motor_pos.append(ModuleTool.get_motor_pos(r, motor_name))
        self.motor_safe_check(r, motor_pos)
        # ############## 数据上报 ##############
        self.state["status"] = self.status
        self.state["args"] = args
        self.state["has_goods"] = r.hasGoods()
        self.state["motor_pos_extremum_diff"] = self.get_extremum_diff(*motor_pos)
        self.state["motor_pos_variance"] = self.get_variance(*motor_pos)
        self.state["motors"] = {
            self.motor_name1: {"upLimitDi": self.up_limit_di1, "zeroDi": self.zero_di1, "reach": r.isMotorReached(self.motor_name1), "stop": r.isMotorStop(self.motor_name1)},
            self.motor_name2: {"upLimitDi": self.up_limit_di2, "zeroDi": self.zero_di2, "reach": r.isMotorReached(self.motor_name2), "stop": r.isMotorStop(self.motor_name2)}
        }
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        return self.status

    def jack_load(self, r: SimModule):
        for i in range(2):
            if not self.opt_status[i]:
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

    def jack_unload(self, r: SimModule):
        for i in range(2):
            if not self.opt_status[i]:
                self.opt_status[i] = self.robot.jack(self.jack_motors[i], 0.000001)
        if all(self.opt_status):
            r.clearGoodsShape()
            r.resetLocalShelfArea()
            self.status = MoveStatus.FINISHED
        unload_state = dict()
        unload_state['otp_name'] = "JackUnload"
        unload_state['status'] = self.opt_status
        unload_state['actions'] = self.robot.state
        self.state['operation'] = unload_state

    def motor_safe_check(self, r, motor_data):
        """多电机同步安全检查，通过极值差值和方差判断"""
        if self.get_extremum_diff(*motor_data) > self.extremum_diff or self.get_variance(*motor_data) > self.variance:
            r.setError(f"Motor running out of sync! Motor pos:{motor_data}")
            self.status = MoveStatus.FAILED

    def cancel(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("task cancel")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.stopRobot(False)
        r.logInfo("task suspend")
        self.status = MoveStatus.SUSPENDED

    @staticmethod
    def get_variance(*data):
        """
        获取一组数据的方差
        :param data: 一组数据
        :return: 方差
        """
        average = sum(data)/len(data)
        return sum([(x - average) ** 2 for x in data]) / len(data)

    @staticmethod
    def get_extremum_diff(*data):
        """
        获取一组数据的极值差值
        :param data: 一组数据
        :return: 极值差
        """
        return max(data) - min(data)


if __name__ == '__main__':
    r1 = SimModule()
    m = Module(r1, {})
    print(m.__dict__)
