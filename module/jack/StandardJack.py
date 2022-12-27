# -*- coding: utf-8 -*-
# @Date: 2022/11/21
# @Author: zhong
# @File:StandardJack.py
# @Version: 1.0
# @Project: 标准顶升车脚本, 同时支持 DoMotor 和 LinearMotor 类型顶升车
# @Description: 通过 DO 控制时只能上升固定高度，通过线性电机控制时可以选择指定顶升高度
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
            "JackLoadByDo", "JackUnloadByDo", "JackLoadByMotor", "JackUnloadByMotor"
        ],
        "type": "complex"
    },
    "loadHeight": {
        "value": 0.05,
        "tips": "指定上升高度，电机控制时可选",
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
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                                   comment=" 运行超时时间")
        self.up_do = p.loadParam("up_do", type="int", default=-1, comment="DoMotor顶升上升DO")
        self.down_do = p.loadParam("down_do", type="int", default=-1, comment="DoMotor顶升下降DO")
        self.up_di = p.loadParam("up_di", type="int", default=-1, comment="DoMotor上升到位DI")
        self.down_di = p.loadParam("down_di", type="int", default=-1, comment="DoMotor下降到位DI")
        self.jack_motor_name = p.loadParam("jack_motor_name", type="str", default="jack", comment="LinearMotor顶升电机名称")
        self.default_height = p.loadParam("default_height", type="float", default=0.05, comment="默认顶升高度")
        self.opt = None
        self.jack_height = None
        self.jack_motor = Motor(r, MotorType.LINEAR_MOTOR, self.jack_motor_name)  # 定义顶升电机对象
        self.jack_robot = Robot(r)   # 定义顶升车对象

        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.opt = args.get("operation", None)
            self.jack_height = args.get("loadHeight", None)
            pass

        # =====处理业务逻辑=====
        if self.opt == "JackLoadByDo":
            self.load_by_do(r)
        elif self.opt == "JackUnloadByDo":
            self.unload_by_do(r)
        elif self.opt == "JackLoadByMotor":
            self.load_by_motor(r)
        elif self.opt == "JackUnloadByMotor":
            self.unload_by_motor(r)
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED
        # =====数据上报及日志打印=====
        di_do_info = {
            "up_do": ModuleTool.check_DI(r, self.up_do),
            "up_di": ModuleTool.check_DI(r, self.up_di),
            "down_do": ModuleTool.check_DI(r, self.down_do),
            "down_di": ModuleTool.check_DI(r, self.down_di)
        }
        self.report_info['args'] = args
        self.report_info['DI&DO'] = di_do_info
        self.report_info['jack_height'] = ModuleTool.get_motor_pos(r, self.jack_motor_name)
        self.report_info['task_status'] = self.status
        self.report_info['jack_robot'] = self.jack_robot.state
        r.setInfo(json.dumps(self.report_info))
        return self.status

    def load_by_do(self, r):
        r.setDO(self.up_do, True)
        r.setDO(self.down_do, False)
        if ModuleTool.check_DI(r, self.up_di):
            self.status = MoveStatus.FINISHED

    def unload_by_do(self, r):
        r.setDO(self.up_do, False)
        r.setDO(self.down_do, True)
        if ModuleTool.check_DI(r, self.down_di):
            self.status = MoveStatus.FINISHED

    def load_by_motor(self, r):
        if self.jack_height is None:
            self.jack_height = self.default_height
        if self.jack_robot.run_motor(self.jack_motor, pos=self.jack_height):
            self.status = MoveStatus.FINISHED

    def unload_by_motor(self, r):
        if self.jack_height is None:
            self.jack_height = 0.0
        if self.jack_robot.run_motor(self.jack_motor, pos=self.jack_height):
            self.status = MoveStatus.FINISHED

    def cancel(self, r):
        # =====处理任务取消时的业务=====
        r.logInfo(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        r.logInfo(f"suspend task")
        self.status = MoveStatus.SUSPENDED


if __name__ == '__main__':  # 本地运行测试
    r1 = SimModule()
    args1 = {}
    m = Module(r1, args1)
    run_counter = 0
    r1.setMotorPosition("", 5.0, 0.3, -1)
    while m.status is not MoveStatus.FAILED and m.status is not MoveStatus.FINISHED:
        m.run(r1, args1)
        if run_counter > 10:
            break
        else:
            run_counter += 1
