# -*- coding: utf-8 -*-
# @Date : 2022/12/10
# @Author : zhong
# @File :ReBoTe-CDD14.py
# @Version : 1.0
# @Project : 黛丝自动化（厦门金鹭）
# @Coding : https://seer-group.coding.net/p/issue_pool/requirements/issues/3585/detail
# @Update :

import json
import time

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import Robot, ModuleTool, Motor, MotorType

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "zero",
        "default_value":["zero", "hook-lift", "hook-stretch", "fork-lift"],
        "tips": "操作选项",
        "type": "complex"        
    },
    "hook-lift-mode": {
        "value": 0.4,
        "default_value":["up", "down"],
        "tips": "挂钩上升或下降",
        "type": "complex"
    },
    "hook-stretch-mode": {
        "value": 0,
        "default_value":["out", "back"],
        "tips": "挂钩伸出或缩回",
        "type": "complex"
    },
    "forkHeight": {
        "value": 0,
        "tips": "叉臂抬升高度",
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
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s", comment=" 运行超时时间")
        self.fork_arm_motor_name = p.loadParam("fork_arm_motor_name", type="str", default="motor-name", comment="叉臂电机名称")
        self.hook_lift_motor_name = p.loadParam("hook_lift_motor_name", type="str", default="motor-name", comment="挂钩升降电机名称")
        self.hook_stretch_motor_name = p.loadParam("hook_stretch_motor_name", type="str", default="motor-name", comment="挂钩伸缩电机名称")
        self.hook_lift_up_di = p.loadParam("hook_lift_up_di", type="int", default=6, comment="挂钩上升到位检测DI")
        self.hook_lift_down_di = p.loadParam("hook_lift_down_di", type="int", default=2, comment="挂钩下降到位检测DI")
        self.hook_stretch_out_di = p.loadParam("hook_stretch_out_di", type="int", default=5, comment="挂钩伸出到位检测DI")
        self.hook_stretch_zero_di = p.loadParam("hook_stretch_zero_di", type="int", default=4, comment="挂钩缩回到位检测DI")
        self.fork_zero_height = p.loadParam("fork_zero_height", type="float", default=0.4, comment="叉臂零位高度")
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.opt = None
        self.fork_height = None
        self.hook_lift_mode = None
        self.hook_stretch_mode = None
        self.fork_motor = None
        self.hook_lift_motor = None
        self.hook_stretch_motor = None
        self.robot = Robot(r)
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            self.opt = args.get("operation", None)
            self.fork_height = args.get("forkHeight", 0.4)
            self.hook_lift_mode = args.get("hook-lift-mode", "")
            self.hook_stretch_mode = args.get("hook-stretch-mode", "")
            self.fork_motor = Motor(r, MotorType.LINEAR_MOTOR, self.fork_arm_motor_name, -1)
            self.hook_lift_motor = Motor(r, MotorType.ROLLER_MOTOR, self.hook_lift_motor_name, -1)
            self.hook_stretch_motor = Motor(r, MotorType.ROLLER_MOTOR, self.hook_stretch_motor_name, -1)

        # =====处理业务逻辑=====
        if time.time() - self.start_time > self.timeout:
            r.setError(f"running timeout!")
            self.status = MoveStatus.FAILED
        if self.opt == "zero":
            self.zero(r)
        elif self.opt == "load":
            self.load(r)
        elif self.opt == "unload":
            self.unload(r)
        elif self.opt == "hook-lift":
            if self.hook_lift(r, self.hook_lift_mode):
                self.status = MoveStatus.FINISHED

        elif self.opt == "hook-stretch":
            if self.hook_stretch(r, self.hook_stretch_mode):
                self.status = MoveStatus.FINISHED

        elif self.opt == "fork-lift":
            if self.fork_lift(r):
                self.status = MoveStatus.FINISHED

        # =====数据上报及日志打印=====
        r.publishSpeed()
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        self.report_info['robot_state'] = self.robot.state
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def cancel(self, r):
        # =====处理任务取消时的业务=====
        r.stopMotor()
        r.logInfo(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        pass
        r.logInfo(f"suspend task")
        self.status = MoveStatus.SUSPENDED

    def fork_lift(self, r):
        if self.fork_height < self.fork_zero_height:
            self.fork_height = self.fork_zero_height
            r.logInfo(f"bad fork_height args: {self.fork_height}")
        return self.robot.lift(self.fork_motor, self.fork_height)

    def hook_lift(self, r, mode):
        if mode == "up":
            self.robot.roller(self.hook_lift_motor, 0.14)
            if ModuleTool.check_DI(r, self.hook_lift_up_di):
                r.resetMotor(self.hook_lift_motor_name)
                return True
        elif mode == "down":
            self.robot.roller(self.hook_lift_motor, -0.14)
            if ModuleTool.check_DI(r, self.hook_lift_down_di):
                r.resetMotor(self.hook_lift_motor_name)
                return True
        else:
            r.setError(f"hook lift mode error: {mode}")
        return False

    def hook_stretch(self, r, mode):
        if mode == "out":
            self.robot.roller(self.hook_stretch_motor, 0.14)
            if ModuleTool.check_DI(r, self.hook_stretch_out_di):
                r.resetMotor(self.hook_stretch_motor_name)
                return True
        elif mode == "back":
            self.robot.roller(self.hook_stretch_motor, -0.14)
            if ModuleTool.check_DI(r, self.hook_stretch_zero_di):
                r.resetMotor(self.hook_stretch_motor_name)
                return True
        else:
            r.setError(f"hook stretch mode error: {mode}")
        return False

    def load(self, r):
        r.logInfo(f"load opt")
        self.status = MoveStatus.FINISHED
        pass

    def unload(self, r):
        r.logInfo(f"unload opt")
        self.status = MoveStatus.FINISHED
        pass

    def zero(self, r):
        self.fork_height = self.fork_zero_height
        return self.fork_lift(r) and self.hook_stretch(r, "back") and self.hook_lift(r, "down")


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
