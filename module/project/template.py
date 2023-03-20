# -*- coding: utf-8 -*-
# @Date: 2023/01/01
# @Author: zhong
# @File: template.py
# @Version: 1.0
# @Project: 机构脚本模板示例
# @Coding:
# @Update:

import json
import time

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import ModuleTool, MotorType, Motor, Robot

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "opt1",
        "default_value":["opt1", "opt2", "opt3", "clear", "show"],
        "type": "complex"   
    },
    "param1":{
        "value": 0,
        "type": "int"
    }, 
    "param2": {
        "value": 0.0,
        "type": "float"
    },
    "param3":{
        "value": "",
        "tips": "json格式参数",
        "type": "json"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                                   comment=" 运行超时时间")
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.motor1 = Motor(r, MotorType.LINEAR_MOTOR, "lift", -1)
        self.robot = Robot(r)
        self.opt = args.get("operation", None)
        self.param1 = args.get("param1", None)
        self.param2 = args.get("param2", None)
        self.param3 = args.get("param3", None)
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            pass
        # 超时判断
        if time.time() - self.start_time > self.timeout:
            r.setError(f"script running timeout")

        # =====处理业务逻辑=====
        r.setNotice(f"param2: {self.param2}")
        if self.param2 is not None:
            ret = self.robot.lift(self.motor1, self.param2)
            if ret:
                self.status = MoveStatus.FINISHED

        # 下发电机速度
        r.publishSpeed()
        # 打印电机运行数据
        self.report_info['motor_info'] = self.robot.state

        # =====报错及清除示例=====
        if args.get("operation", None) == "clear":
            self.clear(r)
        if args.get("operation", None) == "show":
            self.show(r)

        # =====数据上报及日志打印=====
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status

        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def cancel(self, r: SimModule):
        # =====处理任务取消时的业务=====
        r.setNotice(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        # =====处理任务暂停时的业务=====
        r.setNotice(f"suspend task")
        self.status = MoveStatus.SUSPENDED

    def clear(self, r: SimModule):
        """
        # 清除不同等级报错, 接口参数为具体报错码
        @param r:
        @return:
        """
        r.clearNotice(57300)
        r.clearWarning(55300)
        r.clearError(53000)
        # 延时处理
        if ModuleTool.delay(0.5):
            self.status = MoveStatus.FINISHED

    def show(self, r: SimModule):
        """
        不同等级报错
        @param r:
        @return:
        """
        r.setError("show error")
        r.setWarning("show warning")
        r.setNotice("show notice")
        self.status = MoveStatus.FINISHED


if __name__ == '__main__':  # 本地运行测试
    r1 = SimModule()
    args1 = {}
    m = Module(r1, args1)
    run_counter = 0
    while m.status is not MoveStatus.FAILED and m.status is not MoveStatus.FINISHED:
        m.run(r1, args1)
        if run_counter > 10:
            break
        else:
            run_counter += 1
