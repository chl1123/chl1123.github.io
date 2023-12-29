# -*- coding: utf-8 -*-
# @Date : 2023/07/10
# @Author : CXN
# @File :singleAxle_ZL.py
# @Version : 1.0
# @Project : 中丽制机SRC项目: 非标卷绕机落筒车。
# @coding:https://seer-group.coding.net/p/order_issue_pool/requirements/issues/3204/detail
# @Update :

import sys

sys.path.append("../../syspy")
import json
from syspy.rbkSim import SimModule
from syspy.robot import Robot, ModuleTool, NetHandle, Motor, MotorType
from syspy.rbk import MoveStatus, BasicModule, ParamServer

####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "push",
        "default_value": ["load", "unload", "zero","push", "stretch"],
        "tips": "tips",
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


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.status = MoveStatus.NONE
        self.stretch_motor_name = p.loadParam("stretch_motor", type="str", default="shensuo", comment="伸缩电机")
        self.push_barrel_name = p.loadParam("push_barrel", type="str", default="tuitong", comment="推筒电机")

        self.collision_DI = p.loadParam("collision_DI", type="int", default=1, comment="碰撞检测DI")

        self.goods_di = p.loadParam("goods_di", type="int", default=3, comment="货物到位检测DI")

        self.stretch_DI = p.loadParam("stretch_DI", type="int", default=6, comment="伸缩零位DI")

        self.push_DI = p.loadParam("push_DI", type="int", default=4, comment="推筒零位DI")

        self.max_stretch_length = p.loadParam("max_stretch_length", type="float", default=0.35, comment="伸缩最大长度")
        self.max_push_length = p.loadParam("max_push_length", type="float", default=1.8, comment="推筒最大长度")
        self.stretch_length = None
        self.push_length = None
        self.start_time = None
        self.robot = Robot(r)
        self.stretch_motor = None
        self.push_barrel = None
        self.stretch_ok = False
        self.push_ok = False
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
            self.stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, self.stretch_motor_name, self.stretch_DI)

            self.push_barrel = Motor(r, MotorType.LINEAR_MOTOR, self.push_barrel_name, self.push_DI)
            if "operation" in args:
                self.stretch_length = args.get("stretchLength", 0)
                self.push_length = args.get("pushLength", 0)

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

            else:
                args_error = True

            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED

        self.collision_check(r)

        if args["operation"] == "load":
            self.load(r)
        elif args["operation"] == "unload":
            self.unload(r)
        elif args["operation"] == "zero":
            self.zero(r)
        elif args["operation"] == "stretch":
            if self.stretch(r, self.stretch_length):
                self.status = MoveStatus.FINISHED
        elif args["operation"] == "push":
            if self.push(r, self.push_length):
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

    def load(self, r):
        # 启动伸缩电机
        if not self.opt[0]:
            self.opt[0] = self.stretch(r, self.stretch_length)

        # 检测货物是否到位
        if self.opt[0] and not self.opt[1]:
            self.opt[1] = ModuleTool.check_DI(r, self.goods_di)

        # 伸缩电机回零
        if self.opt[1] and not self.opt[2]:
            self.opt[2] = self.stretch(r, 0)

            # 伸缩电机回零启动6秒后，升降电机启动
            if ModuleTool.delay(6.0):
                self.opt[3] = True

        if self.opt[0] and self.opt[1] and self.opt[2] and self.opt[3] and self.opt[4]:
            self.status = MoveStatus.FINISHED

    def unload(self, r, ):
        # 启动伸缩电机
        if not self.opt[0]:
            self.opt[0] = self.stretch(r, self.stretch_length)

        # 启动推筒
        if self.opt[0] and not self.opt[1]:
            self.opt[1] = self.push(r, self.push_length)
            if ModuleTool.delay(6.0):
                self.opt[2] = True

        # 推筒回零
        if self.opt[2] and not self.opt[3]:
            self.opt[3] = self.push(r, 0)

        # 伸缩回零
        if self.opt[3] and not self.opt[4]:
            self.opt[4] = self.stretch(r, 0)

        if self.opt[0] and self.opt[1] and self.opt[2] and self.opt[3] and self.opt[4]:
            self.status = MoveStatus.FINISHED

    def zero(self, r):
        self.status = MoveStatus.RUNNING
        if ModuleTool.check_DI(r, self.goods_di):
            r.setError("has goods in robot, can not zero")
            self.status = MoveStatus.FAILED
        else:
            if self.opt[0]:
                self.opt[1] = self.stretch(r, 0)
            if self.opt[0] and not self.opt[1]:
                self.opt[2] = self.push(r, 0)
            if self.opt[0] and not self.opt[2]:
                self.status = MoveStatus.FINISHED

    def stretch(self, r, length):
        if length != 0:
            self.stretch_ok = self.robot.stretch(self.stretch_motor, length)
            r.setUserWarning(55900, f"stretch: {length}, {self.stretch_ok}, {r.getCount()}")

        else:
            self.robot.stretch(self.stretch_motor, length)
            r.setUserWarning(55903, f"stretch zero: {length}, {self.stretch_ok}, {r.getCount()}")

            if ModuleTool.check_DI(r, self.stretch_DI):
                r.resetMotor(self.stretch_motor_name)
                self.stretch_ok = True
        return self.stretch_ok

    def push(self, r, length):
        if length != 0:
            self.push_ok = self.robot.stretch(self.push_barrel, length)
            r.setUserWarning(55910, f"push: {length}, {self.push_ok}, {r.getCount()}")

        else:
            self.robot.stretch(self.push_barrel, length)
            r.setUserWarning(55913, f"push zero: {length}, {self.push_ok}, {r.getCount()}")
            if ModuleTool.check_DI(r, self.push_DI):
                r.resetMotor(self.push_barrel_name)
                self.push_ok = True

        return self.push_ok

    def collision_check(self, r):
        if ModuleTool.check_DI(r, self.collision_DI):
            r.setError(f"stretch collision occurred")
            self.status = MoveStatus.FAILED


if __name__ == '__main__':
    r1 = SimModule()
    args1 = {
        "operation": "load",
        "stretchLength": 0.,
        "liftHeight": 0.,

    }
    m = Module(r1, args1)
    m.run(r1, args1)
