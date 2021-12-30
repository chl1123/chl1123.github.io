# -*- coding: utf-8 -*-
# @Date : 2021/12/28 11:01
# @Author : zhong
# @File :lishengDoubleRoller.py
# @Version : 1.1
# @Project : 河南力生  线性电机双辊筒

import json
import time

from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
from robot import Motor, MotorType, check_DI, Robot


""" 
####BEGIN DEFAULT ARGS####
{
    "HeadRoller": {
        "value": "",
        "default_value": [
            "LeftLoad", "LeftUnload", "RightLoad", "RightUnload"
        ],
        "tips": "车头辊筒操作",
        "type": "complex"
    },
    "TailRoller": {
        "value": "",
        "default_value": [
            "LeftLoad", "LeftUnload", "RightLoad", "RightUnload"
        ],
        "tips": "车尾辊筒操作",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.DI_Head_L = p.loadParam("DI_Head_L", type="int", default=4, comment="车头辊筒左光电DI")
        self.DI_Head_M = p.loadParam("DI_Head_M", type="int", default=5, comment="车头辊筒中间光电DI")
        self.DI_Head_R = p.loadParam("DI_Head_R", type="int", default=6, comment="车头辊筒右光电DI")
        self.DI_Tail_L = p.loadParam("DI_Tail_L", type="int", default=0, comment="车尾辊筒左光电DI")
        self.DI_Tail_M = p.loadParam("DI_Tail_M", type="int", default=1, comment="车尾辊筒中间光电DI")
        self.DI_Tail_R = p.loadParam("DI_Tail_R", type="int", default=2, comment="车尾辊筒右光电DI")
        self.head_motor_name = p.loadParam("HeadMotorName", type="str", default="motor4", comment="车头辊筒电机名称")
        self.tail_motor_name = p.loadParam("TailMotorName", type="str", default="motor3", comment="车尾辊筒电机名称")
        self.time_out = p.loadParam("TimeOut", type="int", default=30, comment="超时时间: 秒")
        self.high_speed = p.loadParam("HighSpeed", type="float", default=-0.01, comment="辊筒高速运转时速度")
        self.low_speed = p.loadParam("LowSpeed", type="float", default=-0.005, comment="辊筒低速运转时速度")
        r.logInfo(f"init args: {args}")
        self.robot = Robot(r)
        self.head_motor = None
        self.tail_motor = None
        self.init = True
        self.state = dict()
        self.status = MoveStatus.NONE
        self.start_time = time.time()
        self.load_goods = False
        self.unload_goods = False
        self.delay_time = None
        self.head_status = True
        self.tail_status = True


    def run(self, r: SimModule, args):
        if self.init:
            self.init = False
            self.head_motor = Motor(r, MotorType.ROLLER_MOTOR, self.head_motor_name, -1)
            self.tail_motor = Motor(r, MotorType.ROLLER_MOTOR, self.tail_motor_name, -1)
        self.status = MoveStatus.RUNNING
        if 'HeadRoller' in args:
            if args.get('HeadRoller', False) == 'LeftLoad':
                self.head_status = self.load(r, self.head_motor, self.low_speed, self.high_speed, self.DI_Head_M, self.DI_Head_R)
            elif args.get('HeadRoller', False) == 'RightLoad':
                self.head_status = self.load(r, self.head_motor, -self.low_speed, -self.high_speed, self.DI_Head_M, self.DI_Head_L)
            elif args.get('HeadRoller', False) == 'LeftUnload':
                self.head_status = self.unload(r, self.head_motor, self.high_speed)
            elif args.get('HeadRoller', False) == 'RightUnload':
                self.head_status = self.unload(r, self.head_motor, -self.high_speed)
            else:
                r.setError(f"args error: {args}")
                self.status = MoveStatus.FAILED
        if 'TailRoller' in args:
            if args.get('TailRoller', False) == 'LeftLoad':
                self.tail_status = self.load(r, self.tail_motor, self.low_speed, self.high_speed, self.DI_Tail_M, self.DI_Tail_R)
            elif args.get('TailRoller', False) == 'RightLoad':
                self.tail_status = self.load(r, self.tail_motor, -self.low_speed, -self.high_speed, self.DI_Tail_M, self.DI_Tail_L)
            elif args.get('TailRoller', False) == 'LeftUnload':
                self.tail_status = self.unload(r, self.tail_motor, self.high_speed)
            elif args.get('TailRoller', False) == 'RightUnload':
                self.tail_status = self.unload(r, self.tail_motor, -self.high_speed)
            else:
                r.setError(f"args error: {args}")
                self.status = MoveStatus.FAILED
        if not r.publishSpeed():
            self.status = MoveStatus.FAILED
        self.state["status"] = self.status
        self.state["args"] = args
        self.state["has_goods"] = r.hasGoods()
        # self.state["motor_state"] = {
        #     self.head_motor_name: {
        #         "speed": get_motor_speed(r, self.head_motor_name),
        #         "reach": r.isMotorReached(self.head_motor_name),
        #         "stop": r.isMotorStop(self.head_motor_name)
        #     },
        #     self.tail_motor_name: {
        #         "speed": get_motor_speed(r, self.tail_motor_name),
        #         "reach": r.isMotorReached(self.tail_motor_name),
        #         "stop": r.isMotorStop(self.tail_motor_name)
        #     }
        # }
        r.logInfo(f"DoubleRollers: {self.state}")
        r.setInfo(json.dumps(self.state))
        if self.head_status and self.tail_status:
            self.status = MoveStatus.FINISHED
        return self.status

    def load(self, r, motor: Motor, low_speed, high_speed, slow_di, finish_di):
        run_time = time.time() - self.start_time
        if run_time > self.time_out and not check_DI(r, finish_di):   # 上料超时
            r.setError(f"Roller {motor.motor_name} load time out")
            self.status = MoveStatus.FAILED
        if not self.load_goods and check_DI(r, finish_di):   # 上料方向反了
            r.setError(f"{motor.motor_name} load direction error !")
            return False
        if self.prep_load(r, motor):    # 无光电触发，辊筒高速运转，预上料
            self.load_goods = True
            self.robot.roller(motor, high_speed)
        else:
            if not self.load_goods:
                r.setError(f"Goods already exists, {motor.motor_name} cannot load")
        if check_DI(r, slow_di):     # 中间光电触发，减速
            self.robot.roller(motor, low_speed)
        if self.load_goods and check_DI(r, finish_di):   # 上料完成
            self.robot.roller(motor, 0)
            r.setGoodsShape(0, 0, 0)
            return True
        load_state = dict()
        load_state[f"{motor.motor_name}"] = motor.motor_name
        load_state['actions'] = self.robot.state
        load_state["status"] = motor.status
        return False


    def unload(self, r, motor: Motor, high_speed):
        run_time = time.time() - self.start_time
        if self.prep_load(r, motor):  # 无光电触发
            if self.unload_goods:  # 辊筒已运转
                if self.delay(3):
                    self.robot.roller(motor, 0)
                    r.clearGoodsShape()
                    return True
            else:   # 辊筒未运转
                r.setError(f"No goods, cannot unload")
        else:  # 有光电触发
            if run_time > self.time_out:  # 运行超时
                r.setError(f"Roller {motor.motor_name} unload time out")
            self.robot.roller(motor, high_speed)
            self.unload_goods = True
        unload_state = dict()
        unload_state[f"{motor.motor_name}"] = motor.motor_name
        unload_state["status"] = motor.status
        unload_state['actions'] = self.robot.state
        self.state['unload'] = unload_state
        return False

    def prep_load(self, r, motor: Motor) -> bool:
        """
        左中右三个光电都未触发，则辊筒处于预上料状态
        :param r: 
        :param motor: 
        :return: 
        """
        if motor == self.head_motor:
            return not (check_DI(r, self.DI_Head_R) or check_DI(r, self.DI_Head_L) or check_DI(r, self.DI_Head_M))
        if motor == self.tail_motor:
            return not (check_DI(r, self.DI_Tail_R) or check_DI(r, self.DI_Tail_L) or check_DI(r, self.DI_Tail_M))
        r.setError(f"motor not exists: {motor.motor_name}")
        return False

    def delay(self, second):   # 延时
        if self.delay_time is None:
            self.delay_time = time.time()
        t = time.time()
        if t - self.delay_time > second:
            return True
        return False


if __name__ == '__main__':
    r = SimModule()
    m = Module(r, {})
    m.run(r, {})
    print(MotorType(1) == MotorType.ROLLER_MOTOR)
