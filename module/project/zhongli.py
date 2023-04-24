# -*- coding: utf-8 -*-
# @Date : 2023/04/06
# @Author : zhong
# @File :zhongli.py
# @Version : 1.1
# @Project : 中丽制机SRC项目: 非标卷绕机落筒车。
# @coding:https://seer-group.coding.net/p/order_issue_pool/requirements/issues/1433/detail
# @Update :

import sys

sys.path.append("../syspy")
import json
from rbkSim import SimModule
from robot import Robot, ModuleTool, NetHandle, Motor, MotorType
from rbk import MoveStatus, BasicModule, ParamServer

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "push",
        "default_value":["load","unload","zero", "push", "stretch"],
        "tips": "tips",
        "type": "complex"        
    },
    "side":{
        "value":"right",
        "default_value":["right", "left", "double"],
        "tips": "左右伸缩和推筒",
        "type": "complex"   
    },
    "stretchLength": {
        "value": 0.35,
        "tips": "伸缩长度",
        "type": "float",
        "unit": "m"
    },
    "pushLength": {
        "value": 0.5,
        "tips": "推筒推出距离",
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
        self.status = MoveStatus.NONE
        self.left_stretch_motor_name = p.loadParam("left_stretch_motor", type="str", default="zuoshensuo",
                                                   comment="左伸缩电机")
        self.right_stretch_motor_name = p.loadParam("right_stretch_motor", type="str", default="youshensuo",
                                                    comment="右伸缩电机")
        self.left_push_barrel_name = p.loadParam("left_push_barrel", type="str", default="zuotuitong",
                                                 comment="左推筒电机")
        self.right_push_barrel_name = p.loadParam("right_push_barrel", type="str", default="youtuitong",
                                                  comment="右推筒电机")
        self.lift_motor_name = p.loadParam("lift_motor", type="str", default="lift", comment="顶升电机")

        self.left_collision_DI = p.loadParam("left_collision_DI", type="int", default=1, comment="左碰撞检测DI")
        self.right_collision_DI = p.loadParam("right_collision_DI", type="int", default=0, comment="右碰撞检测DI")

        self.left_goods_di = p.loadParam("left_goods_di", type="int", default=3, comment="左货物到位检测DI")
        self.right_goods_di = p.loadParam("right_goods_di", type="int", default=7, comment="右货物到位检测DI")

        self.left_stretch_DI = p.loadParam("left_stretch_DI", type="int", default=6, comment="左伸缩零位DI")
        self.right_stretch_DI = p.loadParam("right_stretch_DI", type="int", default=5, comment="右伸缩零位DI")

        self.left_push_DI = p.loadParam("left_push_DI", type="int", default=4, comment="左推筒零位DI")
        self.right_push_DI = p.loadParam("right_push_DI", type="int", default=2, comment="右推筒零位DI")

        self.max_lift_height = p.loadParam("max_lift_height", type="float", default=0.1, comment="顶升的最大高度")
        self.max_stretch_length = p.loadParam("max_stretch_length", type="float", default=0.35, comment="伸缩最大长度")
        self.max_push_length = p.loadParam("max_push_length", type="float", default=1.8, comment="推筒最大长度")
        self.lift_height = None
        self.stretch_length = None
        self.push_length = None
        self.start_time = None
        self.robot = Robot(r)
        self.side = None
        self.lift_motor = None
        self.left_stretch_motor = None
        self.right_stretch_motor = None
        self.left_push_barrel = None
        self.right_push_barrel = None
        self.left_stretch_ok, self.right_stretch_ok = False, False
        self.left_push_ok, self.right_push_ok = False, False
        self.info = dict()
        self.opt = [False] * 10
        self.net = NetHandle()
        self.data = None
        self.init = True
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            args_error = False
            self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name, -1)
            self.left_stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, self.left_stretch_motor_name, -1)
            self.right_stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, self.right_stretch_motor_name, -1)
            self.left_push_barrel = Motor(r, MotorType.LINEAR_MOTOR, self.left_push_barrel_name, -1)
            self.right_push_barrel = Motor(r, MotorType.LINEAR_MOTOR, self.right_push_barrel_name, -1)
            if "operation" in args:
                self.side = args.get("side", "None")
                self.stretch_length = args.get("stretchLength", 0)
                self.push_length = args.get("pushLength", 0)
                self.lift_height = args.get("liftHeight", 0)

                if self.stretch_length > self.max_stretch_length:
                    r.setError(f"over max stretch length: {self.max_stretch_length}")
                    args_error = True
                elif self.stretch_length < 0:
                    self.stretch_length = 0

                if self.push_length > self.max_push_length:
                    r.setError(f"over max push length: {self.max_push_length}")
                    args_error = True
                elif self.push_length < 0:
                    self.push_length = 0

                if self.lift_height > self.max_lift_height:
                    r.setError(f"over max lift height: {self.max_lift_height}")
                    args_error = True
                elif self.lift_height < 0:
                    self.lift_height = 0
            else:
                args_error = True

            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED

        self.collision_check(r)

        if args["operation"] == "load":
            self.load(r, self.side)
        elif args["operation"] == "unload":
            self.unload(r, self.side)
        elif args["operation"] == "zero":
            self.zero(r)
        elif args["operation"] == "lift":
            if self.lift(r, self.lift_height):
                self.status = MoveStatus.FINISHED
        elif args["operation"] == "stretch":
            if self.stretch(r, self.side, self.stretch_length):
                self.status = MoveStatus.FINISHED
        elif args["operation"] == "push":
            if self.push(r, self.side, self.push_length):
                self.status = MoveStatus.FINISHED
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED

        r.publishSpeed()
        self.info['args'] = args
        self.info['status'] = self.status
        self.info['motorInfo'] = self.robot.state

        r.setInfo(json.dumps(self.info))
        r.logInfo(json.dumps(self.info))
        return self.status

    def cancel(self, r: SimModule):
        r.stopMotor()
        return MoveStatus.NONE

    def suspend(self, r: SimModule):
        return MoveStatus.SUSPENDED

    def load(self, r, side):
        # 启动伸缩电机
        if not self.opt[0]:
            self.opt[0] = self.stretch(r, side, self.stretch_length)

        # 检测货物是否到位
        if self.opt[0] and not self.opt[1]:
            if side == "left":
                self.opt[1] = ModuleTool.check_DI(r, self.left_goods_di)
            elif side == "right":
                self.opt[1] = ModuleTool.check_DI(r, self.right_goods_di)
            elif side == "double":
                self.opt[1] = ModuleTool.check_DI(r, self.left_goods_di) and ModuleTool.check_DI(r, self.right_goods_di)
            else:
                r.setError(f"side error: {side}")

        # 伸缩电机回零
        if self.opt[1] and not self.opt[2]:
            self.opt[2] = self.stretch(r, side, 0)

            # 伸缩电机回零启动6秒后，升降电机启动
            if ModuleTool.delay(6.0):
                self.opt[3] = True

        if self.opt[3] and not self.opt[4]:
            # 升降电机启动
            self.opt[4] = self.lift(r, self.lift_height)

        if all(self.opt[:5]):
            self.status = MoveStatus.FINISHED

        self.info['step'] = self.opt[:5]

    def unload(self, r, side):
        # 启动伸缩电机
        if not self.opt[0]:
            self.opt[0] = self.stretch(r, side, self.stretch_length)

        # 启动推筒
        if self.opt[0] and not self.opt[1]:
            self.opt[1] = self.push(r, side, self.push_length)

        if self.opt[1] and not self.opt[2]:
            if ModuleTool.delay(6.0):
                self.opt[2] = True

        # 启动顶升电机
        if self.opt[2] and not self.opt[3]:
            self.opt[3] = self.lift(r, self.lift_height)
            self.opt[3] = self.opt[3] and ModuleTool.delay(3.0)

        # 推筒回零
        if self.opt[3] and not self.opt[4]:
            self.opt[4] = self.push(r, side, 0)

        # 伸缩回零
        if self.opt[4] and not self.opt[5]:
            self.opt[5] = self.stretch(r, side, 0)

        if all(self.opt[:6]):
            self.status = MoveStatus.FINISHED

        self.info['step'] = self.opt[0:6]

    def zero(self, r):
        self.status = MoveStatus.RUNNING
        if ModuleTool.check_DI(r, self.left_goods_di) or ModuleTool.check_DI(r, self.right_goods_di):
            r.setError("has goods in robot, can not zero")
            self.status = MoveStatus.FAILED
        else:
            if not self.opt[0]:
                self.opt[0] = self.lift(r, 0)
            if self.opt[0] and not self.opt[1]:
                self.opt[1] = self.stretch(r, "double", 0)
            if self.opt[1] and not self.opt[2]:
                self.opt[2] = self.push(r, "double", 0)
            if self.opt[2]:
                self.status = MoveStatus.FINISHED

        self.info['step'] = self.opt[:3]

    def stretch(self, r, side, length):
        if length != 0:
            if side == "left":
                self.left_stretch_ok = self.robot.stretch(self.left_stretch_motor, length)
                self.right_stretch_ok = True
                # r.setUserWarning(55900, f"left stretch: {length}, {self.left_stretch_ok}, {self.right_stretch_ok}, {r.getCount()}")

            elif side == "right":
                self.right_stretch_ok = self.robot.stretch(self.right_stretch_motor, length)
                self.left_stretch_ok = True
                # r.setUserWarning(55901, f"right stretch: {length}, {self.left_stretch_ok}, {self.right_stretch_ok}, {r.getCount()}v")

            elif side == "double":
                self.left_stretch_ok = self.left_stretch_ok or self.robot.stretch(self.left_stretch_motor, length)
                self.right_stretch_ok = self.right_stretch_ok or self.robot.stretch(self.right_stretch_motor, length)
                # r.setUserWarning(55902, f"double stretch: {length}, {self.left_stretch_ok}, {self.right_stretch_ok}, {r.getCount()}")

            else:
                r.setError(f"side error: {side}")
        else:
            self.robot.stretch(self.left_stretch_motor, length)
            self.robot.stretch(self.right_stretch_motor, length)
            # r.setUserWarning(55903, f"stretch zero: {length}, {self.left_stretch_ok}, {self.right_stretch_ok}, {r.getCount()}")
            if ModuleTool.check_DI(r, self.left_stretch_DI):
                r.resetMotor(self.left_stretch_motor_name)
                self.left_stretch_ok = True
            if ModuleTool.check_DI(r, self.right_stretch_DI):
                r.resetMotor(self.right_stretch_motor_name)
                self.right_stretch_ok = True
        return self.left_stretch_ok and self.right_stretch_ok

    def push(self, r, side, length):
        if length != 0:
            if side == "left":
                self.left_push_ok = self.robot.stretch(self.left_push_barrel, length)
                self.right_push_ok = True
                # r.setUserWarning(55910, f"left push: {length}, {self.left_push_ok}, {self.right_push_ok}, {r.getCount()}")

            elif side == "right":
                self.right_push_ok = self.robot.stretch(self.right_push_barrel, length)
                self.left_push_ok = True
                # r.setUserWarning(55911, f"right push: {length}, {self.left_push_ok}, {self.right_push_ok}, {r.getCount()}")

            elif side == "double":
                self.left_push_ok = self.left_push_ok or self.robot.stretch(self.left_push_barrel, length)
                self.right_push_ok = self.right_push_ok or self.robot.stretch(self.right_push_barrel, length)
                # r.setUserWarning(55912, f"double push: {length}, {self.left_push_ok}, {self.right_push_ok}, {r.getCount()}")

            else:
                r.setError(f"side error: {side}")
        else:
            self.robot.stretch(self.left_push_barrel, length)
            self.robot.stretch(self.right_push_barrel, length)
            # r.setUserWarning(55913, f"push zero: {length}, {self.left_push_ok}, {self.right_push_ok}, {r.getCount()}")

            if ModuleTool.check_DI(r, self.left_push_DI):
                r.resetMotor(self.left_push_barrel_name)
                self.left_push_ok = True
            if ModuleTool.check_DI(r, self.right_push_DI):
                r.resetMotor(self.right_push_barrel_name)
                self.right_push_ok = True

        return self.left_push_ok and self.right_push_ok

    def lift(self, r, height):
        # return self.robot.lift(self.lift_motor, height)
        # 取消升降功能
        self.lift_height = 0
        return True

    def collision_check(self, r):
        if ModuleTool.check_DI(r, self.left_collision_DI) or ModuleTool.check_DI(r, self.right_collision_DI):
            r.setError(f"stretch collision occurred")
            self.status = MoveStatus.FAILED


if __name__ == '__main__':
    r1 = SimModule()
    args1 = {
        "operation": "load",
        "side": "left",
        "stretchLength": 0.5,
        "liftHeight": 0.5,
        "data": {
            "reach": {'id': 'terminal-MA1181-C02-02', 'status': '3'}
        }
    }
    m = Module(r1, args1)
    m.run(r1, args1)
