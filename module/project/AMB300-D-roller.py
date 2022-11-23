# -*- coding: utf-8 -*-
# @Date : 2022/11/7
# @Author : lin, zhong
# @File : roller.py
# @Version : 1.0
# @Project : 博众精工非标辊筒车
# @Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/1775/detail
# @Support :
# @Update :

import json
import time

from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
from robot import ModuleTool, MotorType, Motor, Robot

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "None",
        "default_value": ["load","unload","zero"],
        "tips": "操作",
        "type": "complex"
    },
    "goods_size": {
        "value": "None",
        "default_value": ["400", "600"],
        "tips": "货物规格",
        "type": "complex"
    },
    "side": {
        "value": "None",
        "default_value": ["left", "right"],
        "tips": "上下料方向",
        "type": "complex"
    },
    "liftHeight": {
        "value": 0,
        "tips": "中间机构升降高度",
        "type": "float",
        "unit": "mm"
    },
    "guideLength": {
        "value": 0,
        "tips": "导向机构运动距离",
        "type": "float",
        "unit": "mm"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.do1 = p.loadParam("belt_positive_rotation", type="int", default=25, comment="皮带正转指令")
        self.do2 = p.loadParam("belt_reverse_rotation", type="int", default=27, comment="皮带反转指令")

        self.goods_check_di1 = p.loadParam("goods_check_di1", type="int", default=23, comment="货物检查一号感应器")
        self.goods_check_di2 = p.loadParam("goods_check_di2", type="int", default=24, comment="货物检查二号感应器")
        self.goods_check_di3 = p.loadParam("goods_check_di3", type="int", default=25, comment="货物检查三号感应器")
        self.goods_check_di4 = p.loadParam("goods_check_di4", type="int", default=26, comment="货物检查四号感应器")

        self.left_bezel_rise_do = p.loadParam("left_bezel_rise_do", type="int", default=20, comment="左挡板上升DO")
        self.left_bezel_drop_do = p.loadParam("left_bezel_drop_do", type="int", default=21, comment="左挡板下降DO")
        self.left_bezel_rise_di = p.loadParam("left_bezel_rise_di", type="int", default=21, comment="左挡板上升到位DI")
        self.left_bezel_drop_di = p.loadParam("left_bezel_drop_di", type="int", default=22, comment="左挡板下降到位DI")

        self.right_bezel_rise_do = p.loadParam("right_bezel_rise_do", type="int", default=18, comment="右挡板上升DO")
        self.right_bezel_drop_do = p.loadParam("right_bezel_drop_do", type="int", default=19, comment="右挡板下降DO")
        self.right_bezel_rise_di = p.loadParam("right_bezel_rise_di", type="int", default=19, comment="右挡板上升到位DI")
        self.right_bezel_drop_di = p.loadParam("right_bezel_drop_di", type="int", default=20, comment="右挡板下降到位DI")

        self.lift_zero_di = p.loadParam("lift_zero_di", type="int", default=31, comment="升降机构零位")
        self.rotate_zero_di = p.loadParam("rotate_zero_di", type="int", default=32, comment="旋转机构零位")

        self.guide_motor_name = p.loadParam("guide", type="str", default="motor1", comment="导向机构")
        self.limit_up_di = p.loadParam("guide limit up", type="int", default=29, comment="导向机构上限位光电")
        self.limit_down_di = p.loadParam("guide limit down", type="int", default=30, comment="导向机构下限位光电")
        self.lift_motor_name = p.loadParam("lift_motor_name", type="str", default="motor1", comment="顶升机构")
        self.spin_motor_name = p.loadParam("spin", type="str", default="motor", comment="旋转电机")

        self.goods_size = None
        self.lift_height = None
        self.lift_motor = None
        self.guide_length = 0
        self.guide_motor = None
        self.sleep_time = 2
        self.spin_rad = 0
        self.spin_motor = None
        r.logInfo(f"__init__ args: {args}")
        self.tool = ModuleTool
        self.state = dict()
        self.status = MoveStatus.NONE
        self.init = True
        self.robot = Robot(r)
        self.opt_step = [False] * 9
        self.start_time = time.time()

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            args_error = False
            self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name, -1)
            self.guide_motor = Motor(r, MotorType.LINEAR_MOTOR, self.guide_motor_name, -1)
            self.spin_motor = Motor(r, MotorType.LINEAR_MOTOR, self.spin_motor_name, -1)
            self.goods_size = args["goods_size"]
            if "operation" not in args:
                r.setError("please choose operation mode!")
                args_error = True

            if "side" not in args:
                r.setError("please choose operation side!")
                args_error = True

            if "goods_size" not in args:
                r.setError("please choose goods side!")
                args_error = True
            if "liftHeight" in args:
                if args["liftHeight"] < 0:
                    self.lift_height = 0
                elif args["liftHeight"] > 100:
                    r.setError("lift height too high!")
                    args_error = True
                else:
                    self.lift_height = args["liftHeight"]
            else:
                self.lift_height = 0

            if "guideLength" in args:
                if args["guideLength"] < 0:
                    self.guide_length = 0
                elif args["guideLength"] > 100:
                    r.setError("guide height too high!")
                    args_error = True
                else:
                    self.guide_length = args["guideLength"]
            else:
                self.guide_length = 0

            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED

        if args["operation"] == "load" and args["side"] == "left":
            self.left_load(r)
        elif args["operation"] == "load" and args["side"] == "right":
            self.right_load(r)
        elif args["operation"] == "unload" and args["side"] == "left":
            self.left_unload(r)
        elif args["operation"] == "unload" and args["side"] == "right":
            self.right_unload(r)
        elif args["operation"] == "zero":
            self.zero(r)

        r.publishSpeed()

        self.state['status'] = self.status
        self.state['args'] = args
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        r.setNotice(f"step: {self.opt_step}")
        return self.status

    def left_load(self, r):
        if not self.opt_step[0]:  # 左挡板下降
            r.setDO(self.left_bezel_drop_do, True)  # 左挡板下降
            if self.tool.check_DI(r, self.left_bezel_drop_di):  # 检查左挡板下降到位情况
                r.setDO(self.left_bezel_drop_do, False)  # 关闭下降
                self.opt_step[0] = True

        if self.goods_size == "400":
            if self.opt_step[0] and not self.opt_step[1]:  # 辊筒运动左上料
                r.setDO(self.do1, True)  # 认为左上料是正向
                if self.tool.check_DI(r, self.goods_check_di4):  # 检查货物中间光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    self.opt_step[1] = True

            if self.opt_step[1] and not self.opt_step[2]:  # 还原挡板
                r.setDO(self.left_bezel_rise_do, True)
                if self.tool.check_DI(r, self.left_bezel_rise_di):
                    r.setDO(self.left_bezel_rise_do, False)
                    self.opt_step[2] = True
        else:
            if self.opt_step[0] and not self.opt_step[1]:  # 启动导向电机
                self.opt_step[1] = self.robot.stretch(self.guide_motor, self.guide_length)

            if self.opt_step[1] and not self.opt_step[2]:
                r.setDO(self.do1, True)  # 认为左上料是正向
                if self.tool.check_DI(r, self.goods_check_di4):  # 检查货物中间光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    self.opt_step[2] = True

            if self.opt_step[2] and not self.opt_step[3]:
                self.opt_step[3] = self.robot.lift(self.lift_motor, self.lift_height)

            if self.opt_step[3] and not self.opt_step[4]:
                self.opt_step[4] = self.robot.lift(self.spin_motor, 1.5708)

            if self.opt_step[4] and not self.opt_step[5]:
                self.opt_step[5] = self.robot.lift(self.lift_motor, 0)

            if self.opt_step[5] and not self.opt_step[6]:  # 关闭导向机构
                self.opt_step[6] = self.robot.stretch(self.guide_motor, 0)

            if self.opt_step[6] and not self.opt_step[7]:
                r.setDO(self.left_bezel_rise_do, True)
                if self.tool.check_DI(r, self.left_bezel_rise_di):
                    r.setDO(self.left_bezel_rise_do, False)
                    self.opt_step[7] = True

        if self.goods_size == "400" and self.opt_step[2]:
            self.status = MoveStatus.FINISHED
        elif self.goods_size == "600" and self.opt_step[7]:
            self.status = MoveStatus.FINISHED

        load_state = dict()
        load_state['opt_name'] = "left_load"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state
        r.logInfo(f"load: {load_state}")

    def right_load(self, r):
        if not self.opt_step[0]:  # 右挡板下降
            r.setDO(self.right_bezel_drop_do, True)  # 右挡板下降
            if self.tool.check_DI(r, self.right_bezel_drop_di):  # 检查右挡板下降到位情况
                r.setDO(self.right_bezel_drop_do, False)  # 关闭下降
                self.opt_step[0] = True

        if self.goods_size == "400":
            if self.opt_step[0] and not self.opt_step[1]:  # 辊筒运动右上料
                r.setDO(self.do1, True)  # 认为左上料是反向
                r.setDO(self.do2, True)  # 皮带反转
                if self.tool.check_DI(r, self.goods_check_di1):  # 检查货物中间光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    r.setDO(self.do2, False)
                    self.opt_step[1] = True

            if self.opt_step[1] and not self.opt_step[2]:  # 还原挡板
                r.setDO(self.right_bezel_rise_do, True)
                if self.tool.check_DI(r, self.right_bezel_rise_di):
                    r.setDO(self.right_bezel_rise_do, False)
                    self.opt_step[2] = True
        else:
            if self.opt_step[0] and not self.opt_step[1]:  # 启动导向电机
                self.opt_step[1] = self.robot.stretch(self.guide_motor, self.guide_length)

            if self.opt_step[1] and not self.opt_step[2]:
                r.setDO(self.do1, True)  # 认为右上料是反向
                r.setDO(self.do2, True)  # 皮带反转
                if self.tool.check_DI(r, self.goods_check_di1):  # 检查货物中间光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    r.setDO(self.do2, False)
                    self.opt_step[2] = True

            if self.opt_step[2] and not self.opt_step[3]:
                self.opt_step[3] = self.robot.lift(self.lift_motor, self.lift_height)  # 启动顶升机构

            if self.opt_step[3] and not self.opt_step[4]:
                self.opt_step[4] = self.robot.lift(self.spin_motor, 1.5708)  # 旋转90度

            if self.opt_step[4] and not self.opt_step[5]:
                self.opt_step[5] = self.robot.lift(self.lift_motor, 0)  # 顶升机构下降

            if self.opt_step[5] and not self.opt_step[6]:  # 关闭导向机构
                self.opt_step[6] = self.robot.stretch(self.guide_motor, 0)

            if self.opt_step[6] and not self.opt_step[7]:
                r.setDO(self.right_bezel_rise_do, True)
                if self.tool.check_DI(r, self.right_bezel_rise_di):
                    r.setDO(self.right_bezel_rise_do, False)
                    self.opt_step[7] = True

        if self.goods_size == "400" and self.opt_step[2]:
            self.status = MoveStatus.FINISHED
        elif self.goods_size == "600" and self.opt_step[7]:
            self.status = MoveStatus.FINISHED

        load_state = dict()
        load_state['opt_name'] = "right_load"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state
        r.logInfo(f"load: {load_state}")

    def left_unload(self, r):
        if not self.opt_step[0]:  # 左挡板下降
            r.setDO(self.left_bezel_drop_do, True)  # 左挡板下降
            if self.tool.check_DI(r, self.left_bezel_drop_di):  # 检查左挡板下降到位情况
                r.setDO(self.left_bezel_drop_do, False)  # 关闭下降
                self.opt_step[0] = True

        if self.goods_size == "400":
            if self.opt_step[0] and not self.opt_step[1]:  # 辊筒运动左下料
                r.setDO(self.do1, True)  # 认为左上料是正向
                r.setDO(self.do2, True)
                if not self.tool.check_DI(r, self.goods_check_di2) and \
                        not self.tool.check_DI(r, self.goods_check_di3) and \
                        not self.tool.check_DI(r, self.goods_check_di1) and \
                        not self.tool.check_DI(r, self.goods_check_di4):  # 检查货物光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    r.setDO(self.do2, False)
                    self.opt_step[1] = True

            if self.opt_step[1] and not self.opt_step[2]:
                time.sleep(self.sleep_time)
                self.opt_step[2] = True

            if self.opt_step[2] and not self.opt_step[3]:  # 还原挡板
                r.setDO(self.left_bezel_rise_do, True)
                if self.tool.check_DI(r, self.left_bezel_rise_di):
                    r.setDO(self.left_bezel_rise_do, False)
                    self.opt_step[3] = True
        else:
            if self.opt_step[0] and not self.opt_step[1]:  # 启动导向电机
                self.opt_step[1] = self.robot.stretch(self.guide_motor, self.guide_length)

            if self.opt_step[1] and not self.opt_step[2]:
                self.opt_step[2] = self.robot.lift(self.lift_motor, self.lift_height)  # 升起顶升机构

            if self.opt_step[2] and not self.opt_step[3]:
                self.opt_step[3] = self.robot.lift(self.spin_motor, 1.5708)  # 旋转90度

            if self.opt_step[3] and not self.opt_step[4]:
                self.opt_step[4] = self.robot.lift(self.lift_motor, 0)  # 下降顶升机构

            if self.opt_step[4] and not self.opt_step[5]:
                self.opt_step[5] = self.robot.stretch(self.guide_motor, 0)  # 关闭导向机构

            if self.opt_step[5] and not self.opt_step[6]:
                r.setDO(self.do1, True)  # 认为左下料是反向
                r.setDO(self.do2, True)
                if not self.tool.check_DI(r, self.goods_check_di2) and \
                        not self.tool.check_DI(r, self.goods_check_di3) and \
                        not self.tool.check_DI(r, self.goods_check_di1) and \
                        not self.tool.check_DI(r, self.goods_check_di4):  # 检查货物光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    r.setDO(self.do2, False)
                    self.opt_step[6] = True

            if self.opt_step[6] and not self.opt_step[7]:
                time.sleep(self.sleep_time)
                self.opt_step[7] = True

            if self.opt_step[7] and not self.opt_step[8]:  # 还原挡板
                r.setDO(self.left_bezel_rise_do, True)
                if self.tool.check_DI(r, self.left_bezel_rise_di):
                    r.setDO(self.left_bezel_rise_do, False)
                    self.opt_step[8] = True

        if self.goods_size == "400" and self.opt_step[3]:
            self.status = MoveStatus.FINISHED
        elif self.goods_size == "600" and self.opt_step[8]:
            self.status = MoveStatus.FINISHED

        load_state = dict()
        load_state['opt_name'] = "left_unload"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state
        r.logInfo(f"load: {load_state}")

    def right_unload(self, r):
        if not self.opt_step[0]:  # 左挡板下降
            r.setDO(self.right_bezel_drop_do, True)  # 左挡板下降
            if self.tool.check_DI(r, self.right_bezel_drop_di):  # 检查左挡板下降到位情况
                r.setDO(self.right_bezel_drop_do, False)  # 关闭下降
                self.opt_step[0] = True

        if self.goods_size == "400":
            if self.opt_step[0] and not self.opt_step[1]:  # 辊筒运动左下料
                r.setDO(self.do1, True)  # 认为左上料是正向
                if not self.tool.check_DI(r, self.goods_check_di2) and \
                        not self.tool.check_DI(r, self.goods_check_di3) and \
                        not self.tool.check_DI(r, self.goods_check_di1) and \
                        not self.tool.check_DI(r, self.goods_check_di4):  # 检查货物光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    self.opt_step[1] = True

            if self.opt_step[1] and not self.opt_step[2]:
                time.sleep(self.sleep_time)
                self.opt_step[2] = True

            if self.opt_step[2] and not self.opt_step[3]:  # 还原挡板
                r.setDO(self.right_bezel_rise_do, True)
                if self.tool.check_DI(r, self.right_bezel_rise_di):
                    r.setDO(self.right_bezel_rise_do, False)
                    self.opt_step[3] = True
        else:
            if self.opt_step[0] and not self.opt_step[1]:  # 启动导向电机
                self.opt_step[1] = self.robot.stretch(self.guide_motor, self.guide_length)

            if self.opt_step[1] and not self.opt_step[2]:
                self.opt_step[2] = self.robot.lift(self.lift_motor, self.lift_height)  # 升起顶升机构

            if self.opt_step[2] and not self.opt_step[3]:
                self.opt_step[3] = self.robot.lift(self.spin_motor, 1.5708)  # 旋转90度

            if self.opt_step[3] and not self.opt_step[4]:
                self.opt_step[4] = self.robot.lift(self.lift_motor, 0)  # 下降顶升机构

            if self.opt_step[4] and not self.opt_step[5]:
                self.opt_step[5] = self.robot.stretch(self.guide_motor, 0)  # 关闭导向机构

            if self.opt_step[5] and not self.opt_step[6]:
                r.setDO(self.do1, True)  # 认为左下料是反向
                if not self.tool.check_DI(r, self.goods_check_di2) and \
                        not self.tool.check_DI(r, self.goods_check_di3) and \
                        not self.tool.check_DI(r, self.goods_check_di1) and \
                        not self.tool.check_DI(r, self.goods_check_di4):  # 检查货物光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    self.opt_step[6] = True

            if self.opt_step[6] and not self.opt_step[7]:
                time.sleep(self.sleep_time)
                self.opt_step[7] = True

            if self.opt_step[7] and not self.opt_step[8]:  # 还原挡板
                r.setDO(self.right_bezel_rise_do, True)
                if self.tool.check_DI(r, self.right_bezel_rise_di):
                    r.setDO(self.right_bezel_rise_do, False)
                    self.opt_step[8] = True

        if self.goods_size == "400" and self.opt_step[3]:
            self.status = MoveStatus.FINISHED
        elif self.goods_size == "600" and self.opt_step[7]:
            self.status = MoveStatus.FINISHED

        load_state = dict()
        load_state['opt_name'] = "right_unload"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state
        r.logInfo(f"load: {load_state}")

    def suspend(self, r):
        r.setDO(self.do1, False)
        r.setInfo("agv suspend!!")
        self.status = MoveStatus.SUSPENDED

    def cancel(self, r):
        r.setDO(self.do1, False)
        r.setDO(self.do2, False)
        r.setInfo("navigation stop!!")
        self.status = MoveStatus.NONE

    def zero(self, r):
        r.setDO(self.do1, False)
        r.setDO(self.do2, False)
        if not self.opt_step[0]:
            r.setDO(self.right_bezel_rise_do, True)
            if self.tool.check_DI(r, self.right_bezel_rise_di):
                r.setDO(self.right_bezel_rise_do, False)
                self.opt_step[0] = True

        if self.opt_step[0] and not self.opt_step[1]:
            r.setDO(self.left_bezel_rise_do, True)
            if self.tool.check_DI(r, self.left_bezel_rise_di):
                r.setDO(self.left_bezel_rise_do, False)
                self.opt_step[1] = True

        if self.opt_step[1] and not self.opt_step[2]:
            self.robot.stretch(self.guide_motor, 10)
            if self.tool.check_DI(r, self.limit_down_di):
                r.resetMotor(self.guide_motor)
                self.opt_step[2] = True

        if self.opt_step[2] and not self.opt_step[3]:
            self.opt_step[3] = self.robot.lift(self.lift_motor, 10)

        if self.opt_step[3] and not self.opt_step[4]:
            if self.tool.check_DI(r, self.rotate_zero_di):
                self.opt_step[4] = True
            else:
                self.robot.lift(self.spin_motor, 3.14)
                if self.tool.check_DI(r, self.rotate_zero_di):
                    r.resetMotor(self.spin_motor)
                    self.opt_step[4] = True

        if self.opt_step[4] and not self.opt_step[5]:
            self.opt_step[5] = self.robot.lift(self.lift_motor, 0)

        if self.opt_step[5]:
            self.status = MoveStatus.FINISHED

        load_state = dict()
        load_state['opt_name'] = "zero"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state
        r.logInfo(f"load: {load_state}")
