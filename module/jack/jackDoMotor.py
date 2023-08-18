# -*- coding: utf-8 -*-
# @Date : 2022/11/22
# @Author : zhong
# @File :jackDoMotor.py
# @Version : 1.0
# @Project : 改编J系列顶升标准脚本，电机到位条件变更为DI触发

import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

""" 
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value": [
            "JackLoadAndSetShelf", "JackUnLoadAndResetShelf", "JackLoad"
        ],
        "tips": "tips",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""

class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.shelf = "shelf/s0002.shelf"
        self.jack_motor = "lift"
        self.jack_up_di = 6
        self.jack_down_di = 3
        self.operation = ""
        self.task_list = []
        self.task_id = 0
        self.start_time = time.time()
        self.over_time = p.loadParam("over_time", type="float", default=120.0, maxValue=3600.0, minValue=0.0, unit="s",
                                     comment="time")
        self.precision = p.loadParam("precision", type="float", default=0.005, unit="m", comment="顶升到位精度")
        self.jack_height = p.loadParam("jackHeight", type="float", default=0.06, unit="m", comment="顶升高度")
        self.init = True
        self.operation_status = MoveStatus.NONE
        self.state = dict()

    def run(self, r: SimModule, args):
        dt = time.time() - self.start_time
        if dt > self.over_time:
            self.status = MoveStatus.FAILED  # 导航状态
            r.setError("jack operation is over Time")
            return self.status
        self.status = MoveStatus.RUNNING
        self.state = dict()
        if self.init:
            self.init = False
            if "operation" not in args:
                r.setError("user args error {}".format(json.dumps(args)))
                self.status = MoveStatus.FAILED
            else:
                self.operation = args["operation"]
        if self.status is MoveStatus.FAILED:
            return self.status

        if self.operation == "JackLoadAndSetShelf":
            self.jackload(r, self.jack_motor, "JackLoadAndSetShelf",
                          self.shelf, self.jack_up_di, self.jack_down_di)
        elif self.operation == "JackUnLoadAndResetShelf":
            self.jackunload(r, self.jack_motor, "JackUnLoadAndResetShelf",
                            self.shelf, self.jack_up_di, self.jack_down_di)
        elif self.operation == "JackLoad":
            self.jackload(r, self.jack_motor, "JackLoad",
                               self.shelf, self.jack_up_di, self.jack_down_di)
        else:
            # 如果是不支持的operation则报错
            r.setError("operation: {}doesn't support!".format(self.operation))
            self.status = MoveStatus.FAILED
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

    def jackload(self, r, motor_name, operation, shelf, jack_up_di, jack_down_di):
        self.operation = operation
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            # r.setError("jack_motor{}".format(self.jack_motor))
            self.task_list = [
                DoJackMotor(motor_name, self.operation,
                            shelf, jack_up_di, jack_down_di)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state

    def jackunload(self, r, motor_name, operation, shelf, jack_up_di, jack_down_di):
        self.operation = operation
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            #r.setError("rollerLoad can be runing but block_motor position is error motor:{} 's inverse motor".format(block_motor))
            self.task_list = [
                DoJackMotor(motor_name, self.operation,
                            shelf, jack_up_di, jack_down_di)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["unload"] = cur_state


class DoJackMotor:
    def __init__(self, motor_name, operation, shelf, jack_up_di, jack_down_di):
        """dojack电机的arg声明
        Args:
            motor_name (string): 电机名称
            operation (string):JackLoadAndSetShelf/JackUnLoadAndResetShelf
            jack_up_di(int):上到位di编号
            jack_down_di(int):下到位di编号
        """
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.operation = operation
        self.shelf = shelf
        self.jack_up_di = jack_up_di
        self.jack_down_di = jack_down_di

    def reset(self, r: SimModule, roller):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, roller):
        self.status = MoveStatus.RUNNING
        di = r.Di()
        odo = r.odo()
        jack_pos = 0
        try:
            motors = odo['motor_info']
            for motor in motors:
                if motor['motor_name'] == self.motor:
                    jack_pos = motor['position']
        except KeyError:
            r.setError(f"such key not found")
            pass
        except Exception as e:
            r.setError(f"get motor_info error---{e}")
        jack_up_di_status = False
        jack_down_di_status = False
        for (ind, node) in enumerate(di['node']):
            if node['id'] == self.jack_up_di:
                jack_up_di_status = node['status']
            elif node['id'] == self.jack_down_di:
                jack_down_di_status = node['status']
        if self.operation == "JackLoadAndSetShelf":
            # r.setMotorSpeed(self.motor, roller.block_vel, -1)
            # r.setError("jack_motor{}".format(self.motor))
            r.setMotorPosition(self.motor, roller.jack_height, 0.015, -1)
            # if r.isMotorReached(self.motor):
            # if abs(jack_pos - roller.jack_height) < roller.precision:                               # 通过编码器判断顶升是否到位
            if jack_up_di_status:
                r.setLocalShelfArea(self.shelf)
                self.status = MoveStatus.FINISHED
            # else:
            #     r.setNotice(f"jack is running---{jack_pos}")
        elif self.operation == "JackLoad":
            r.setMotorPosition(self.motor, roller.jack_height, 0.015, -1)
            # if r.isMotorReached(self.motor):
            # if abs(jack_pos - roller.jack_height) < roller.precision:
            if jack_up_di_status:
                # r.setLocalShelfArea()
                self.status = MoveStatus.FINISHED
            # else:
            #     r.setNotice(f"jack is running---{jack_pos}")
        elif self.operation == "JackUnLoadAndResetShelf":
            r.setMotorPosition(self.motor, -0.01, 0.015, -1)
            # if r.isMotorReached(self.motor):
            # if abs(jack_pos - 0) < roller.precision:
            if jack_down_di_status:
                r.resetLocalShelfArea()
                self.status = MoveStatus.FINISHED
            # else:
            #     r.setNotice(f"jack is running---{jack_pos}")
        r.publishSpeed()
        state = dict()
        state["operation"] = self.operation
        state["status"] = self.status
        roller.state["BlockMotor"] = state


class ServoJackMotor:
    def __int__(self, operation, speed_control, jack_up_di, jack_down_di, jack_zero_di):
        """主参数声明
            Args:
                operation(String):顶升电机的操作jackLoad/jackUnload
                speed_control(float):顶升电机的speed数值（限于顶升SRC控制方案）
                jack_up_di(int):顶升电机的上到位
                jack_down_di(int):顶升电机下到位
                jack_zero_di（int）:顶升电机零位

        """
        self.status = MoveStatus.NONE
        self.operation = operation
        self.speedControl = speed_control
        self.jackUpDI = jack_up_di
        self.jackDownDI = jack_down_di

    def reset(self, r: SimModule, jack_motor_name):
        r.resetMotor(jack_motor_name)
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, jack_motor):
        self.status = MoveStatus.RUNNING
        di = r.Di()
        jack_up_di_status = False
        jack_down_di_status = False
        jack_zero_di_status = False


if __name__ == '__main__':
    import rbkSim

    r = rbkSim.SimModule()
    m = Module(r, None)
    data = dict()
    data["operation"] = "RollerLoad"
    data["direction"] = "Right"
    print(m.run(r, data))
