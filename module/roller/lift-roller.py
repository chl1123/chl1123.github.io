# -*- coding: utf-8 -*-
# @Time : 2022/6/30 - 2022/8/3
# @Author : qian, zhong
# @project : Y20220513 SMT上下料可升降辊筒装运专车-SSR-S50S1-DSV1
# @File : lift-roller.py
# @Version: 1.7
# @Update :  https://seer-group.coding.net/p/issue_pool/assignments/issues/3367/detail

import json

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer


"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "None",
        "default_value":["load","unload","lift","zero"],
        "tips": "操作",
        "type": "complex"
    },
    "side":{
        "value": "",
        "default_value":["right","left"],
        "tips": "上下料",
        "type": "complex"
    },
    "liftHeight": {
        "value": 0,
        "tips": "货叉升降高度",
        "type": "float",
        "unit": "mm"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super().__init__()
        p = ParamServer(__file__)
        self.max_lift_height = p.loadParam("max_lift_height", type="float", default=0.3, comment="最大升降高度")
        self.lift_zero = p.loadParam("lift_zero", type="float", default=0.000, comment="货叉升降零位")
        self.di1 = p.loadParam("belt_detect_front", type="int", default=21, comment="皮带左侧检测光电")
        self.di2 = p.loadParam("belt_detect_middle", type="int", default=22, comment="皮带中部检测光电")
        self.di3 = p.loadParam("belt_detect_rear", type="int", default=23, comment="皮带右侧检测光电")
        self.di4 = p.loadParam("left_damper_bottom", type="int", default=17, comment="左挡板低位信号")
        self.di5 = p.loadParam("left_damper_top", type="int", default=18, comment="左挡板高位信号")
        self.di6 = p.loadParam("right_damper_bottom", type="int", default=19, comment="右挡板低位信号")
        self.di7 = p.loadParam("right_damper_top", type="int", default=20, comment="右挡板高位信号")
        self.do1 = p.loadParam("belt_positive_rotation", type="int", default=12, comment="皮带正转指令")
        self.do2 = p.loadParam("left_damper_up", type="int", default=13, comment="左挡板上升")
        self.do3 = p.loadParam("left_damper_down", type="int", default=14, comment="左挡板下降")
        self.do4 = p.loadParam("right_damper_up", type="int", default=15, comment="右挡板上升")
        self.do5 = p.loadParam("right_damper_down", type="int", default=16, comment="右挡板下降")
        self.do6 = p.loadParam("belt_reverse_rotation", type="int", default=12, comment="皮带反转指令")
        self.lift_motor_name = p.loadParam("LiftMotorName", type="str", default="motor1", comment="货叉升降电机名称")
        r.logInfo(f"__init__ args: {args}")
        self.state = dict()
        self.status = MoveStatus.NONE
        self.init = True
        self.robot = Robot(r)
        self.lift_motor = None
        self.opt_step = [False]*5
        self.lift_height = self.lift_zero

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.lift_motor = Motor(r, self.lift_motor_name, -1)
            args_error = False
            if "operation" in args:
                if "liftHeight" in args:
                    self.lift_height = args["liftHeight"]
                    if args["liftHeight"] > self.max_lift_height:
                        r.setError(f"Out of max lift height {self.max_lift_height}")
                        args_error = True
                    elif args["liftHeight"] < self.lift_zero:
                        self.lift_height = self.lift_zero
                if args["operation"] == "load":
                    if "liftHeight" not in args:
                        r.setError(f"Pls input lift height...")
                        args_error = True
                    if "side" not in args:
                        r.setError(f"Pls select load side...")
                        args_error = True
                if args["operation"] == "unload":
                    if "liftHeight" not in args:
                        r.setError(f"Pls input lift height...")
                        args_error = True
                    if "side" not in args:
                        r.setError(f"Pls select unload side...")
                        args_error = True
                if args["operation"] == "lift":
                    if "liftHeight" not in args:
                        r.setError(f"Pls input lift height...")
                        args_error = True
            else:
                r.setError(f"Pls choose operation mode")
                args_error = True
            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED
        if args["operation"] == "lift":
            self.lift(r)
        elif args["operation"] == "load" and args["side"] == "left":
            self.left_load(r)
        elif args["operation"] == "load" and args["side"] == "right":
            self.right_load(r)
        elif args["operation"] == "unload" and args["side"] == "left":
            self.left_unload(r)
        elif args["operation"] == "unload" and args["side"] == "right":
            self.right_unload(r)
        else:
            r.setError(f"operation error: {args['operation']}")
            self.status = MoveStatus.FAILED
        if not r.publishSpeed():
            r.setError(f"Failed to publish the current motor control scheme ")
            self.status = MoveStatus.FAILED
        self.state['status'] = self.status
        self.state['args'] = args
        self.state['has_goods'] = r.hasGoods()
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        r.setNotice(f"step: {self.opt_step}")
        return self.status

    def lift(self, r):
        if not self.opt_step[0]:
            self.opt_step[0] = self.robot.lift(self.lift_motor, self.lift_height)
        else:
            self.status = MoveStatus.FINISHED
        lift_state = dict()
        lift_state['opt_name'] = "lift"
        lift_state['opt_status'] = self.status
        lift_state['actions'] = self.robot.state
        self.state['operation'] = lift_state
        r.logInfo(f"lift: {lift_state}")

    def left_load(self, r):
        if not self.opt_step[0]:    # 提升升降机
            self.opt_step[0] = self.robot.lift(self.lift_motor, self.lift_height)
        if self.opt_step[0] and not self.opt_step[1]:   # 左挡板下降
            r.setDO(self.do3, True)
            if self.check_DI(r, self.di4):
                r.setDO(self.do3, False)
                self.opt_step[1] = True
        if self.opt_step[1] and not self.opt_step[2]:   # 皮带机运行
            r.setDO(self.do1, True)
            if self.check_DI(r, self.di3):             # 检测右侧光电触发
                r.setDO(self.do1, False)
                self.opt_step[2] = True
        if self.opt_step[2] and not self.opt_step[3]:   # 左挡板上升
            r.setDO(self.do2, True)
            if self.check_DI(r, self.di5):
                r.setDO(self.do2, False)
                self.opt_step[3] = True
        if self.opt_step[3]:
            self.status = MoveStatus.FINISHED
        load_state = dict()
        load_state['opt_name'] = "load"
        load_state['opt_side'] = "left"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state
        r.logInfo(f"load: {load_state}")

    def right_load(self, r):
        if not self.opt_step[0]:    # 提升升降机
            self.opt_step[0] = self.robot.lift(self.lift_motor, self.lift_height)
        if self.opt_step[0] and not self.opt_step[1]:   # 右挡板下降
            r.setDO(self.do5, True)
            if self.check_DI(r, self.di6):
                r.setDO(self.do5, False)
                self.opt_step[1] = True
        if self.opt_step[1] and not self.opt_step[2]:   # 皮带机运行
            r.setDO(self.do1, True)
            r.setDO(self.do6, True)
            if self.check_DI(r, self.di1):              # 检测左侧光电触发
                r.setDO(self.do1, False)
                r.setDO(self.do6, False)
                self.opt_step[2] = True
        if self.opt_step[2] and not self.opt_step[3]:   # 右挡板上升
            r.setDO(self.do4, True)
            if self.check_DI(r, self.di7):
                r.setDO(self.do4, False)
                self.opt_step[3] = True
        if self.opt_step[3]:
            self.status = MoveStatus.FINISHED
        load_state = dict()
        load_state['opt_name'] = "load"
        load_state['opt_side'] = "left"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state
        r.logInfo(f"load: {load_state}")

    def left_unload(self, r):
        if not self.opt_step[0]:    # 提升升降机
            self.opt_step[0] = self.robot.lift(self.lift_motor, self.lift_height)
        if self.opt_step[0] and not self.opt_step[1]:   # 左挡板下降
            r.setDO(self.do3, True)
            if self.check_DI(r, self.di4):
                r.setDO(self.do3, False)
                self.opt_step[1] = True
        if self.opt_step[1] and not self.opt_step[2]:   # 皮带机反转运行
            r.setDO(self.do1, True)
            r.setDO(self.do6, True)
            if not self.check_DI(r, self.di3) and not self.check_DI(r, self.di2) and not self.check_DI(r, self.di1):             # 检测光电
                r.setDO(self.do1, False)
                r.setDO(self.do6, False)
                self.opt_step[2] = True
        if self.opt_step[2] and not self.opt_step[3]:   # 左挡板上升
            r.setDO(self.do2, True)
            if self.check_DI(r, self.di5):
                r.setDO(self.do2, False)
                self.opt_step[3] = True
        if self.opt_step[3] and not self.opt_step[4]:
            self.opt_step[4] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[4]:
            self.status = MoveStatus.FINISHED
        unload_state = dict()
        unload_state['opt_name'] = "unload"
        unload_state['opt_side'] = "left"
        unload_state['opt_status'] = self.status
        unload_state['actions'] = self.robot.state
        self.state['operation'] = unload_state
        r.logInfo(f"unload: {unload_state}")

    def right_unload(self, r):
        if not self.opt_step[0]:    # 提升升降机
            self.opt_step[0] = self.robot.lift(self.lift_motor, self.lift_height)
        if self.opt_step[0] and not self.opt_step[1]:   # 右挡板下降
            r.setDO(self.do5, True)
            if self.check_DI(r, self.di6):
                r.setDO(self.do5, False)
                self.opt_step[1] = True
        if self.opt_step[1] and not self.opt_step[2]:   # 皮带机运行
            r.setDO(self.do1, True)
            if not self.check_DI(r, self.di3) and not self.check_DI(r, self.di2) and not self.check_DI(r, self.di1):             # 检测光电
                r.setDO(self.do1, False)
                self.opt_step[2] = True
        if self.opt_step[2] and not self.opt_step[3]:   # 右挡板上升
            r.setDO(self.do4, True)
            if self.check_DI(r, self.di7):
                r.setDO(self.do4, False)
                self.opt_step[3] = True
        if self.opt_step[3] and not self.opt_step[4]:
            self.opt_step[4] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[4]:
            self.status = MoveStatus.FINISHED

    def reset(self, r):
        if not self.opt_step[0]:    # 左右挡板上升
            r.setDO(self.do3, False)
            r.setDO(self.do5, False)
            r.setDO(self.do2, True)
            r.setDO(self.do4, True)
            if self.check_DI(r, self.di7) and self.check_DI(r, self.di5):
                r.setDO(self.do2, False)
                r.setDO(self.do4, False)
                self.opt_step[0] = True
        if self.opt_step[0] and not self.opt_step[1]:   # 辊筒复位
            r.setDO(self.do1, False)
            r.setDO(self.do6, False)
            self.opt_step[1] = True
        if self.opt_step[1] and not self.opt_step[2]:   # 升降机复位
            self.opt_step[2] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[2]:
            self.status = MoveStatus.FINISHED

    @staticmethod
    def check_DI(r: SimModule, di: int):
        """
        检测单个DI是否被触发
        :param r: SimModule类对象
        :param di: 需要检测的DI
        :return: 返回指定DI的状态，若DI不存在返回False
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node['id'] == di:
                return node['status']
        return False


class Motor:
    def __init__(self, r, motor_name: str, stop_di: int):
        self.motor_name = motor_name
        self.stop_di = stop_di
        self.r = r
        self.status = MoveStatus.NONE
        self.state = dict()

    def run(self, vel=0., pos=0., max_vel=0.):
        """
        控制电机运转，辊筒电机需传参 vel，线性电机需传参 pos 和 max_vel
        :param vel: 辊筒电机转速
        :param pos: 线性电机目标位置
        :param max_vel: 线性电机最大转速
        :return:
        """
        self.r.setMotorPosition(self.motor_name, pos, max_vel, self.stop_di)
        if self.r.isMotorReached(self.motor_name):
            self.r.resetMotor(self.motor_name)
            self.status = MoveStatus.FINISHED
        self.state['motor_name'] = self.motor_name
        self.state['motor_status'] = self.status

    def reset(self):
        self.r.logInfo(f"motor reset: {self.motor_name}")
        self.r.resetMotor(self.motor_name)
        self.status = MoveStatus.RUNNING


class Robot:
    def __init__(self, r):
        self.r = r
        self.state = dict()

    def lift(self, motor: Motor, height: float, max_vel=0.3) -> bool:
        """
        控制升降电机
        :param motor:
        :param height:
        :param max_vel:
        :return:
        """
        self.state['lift'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=height, max_vel=max_vel)
        return False


if __name__ == '__main__':
    r = SimModule()
    robot = Robot(r)
    lift_motor = Motor(r, "motor1", -1)
    robot.lift(lift_motor, 2)
    module = Module(r, {})
