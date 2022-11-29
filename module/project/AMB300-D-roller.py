# -*- coding: utf-8 -*-
# @Date : 2022/11/27
# @Author : lin, zhong
# @File : AMB300-D-roller.py
# @Version : 1.1
# @Project : 博众精工非标辊筒车
# @Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/1775/detail
# @Support :
# @Update : 增加夹爪指定长度加紧

import json
import time

from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule
from robot import ModuleTool

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "zero",
        "default_value": ["load","unload","zero", "lift", "spin", "clamp"],
        "tips": "操作类型",
        "type": "complex"
    },
    "goods_size": {
        "value": "",
        "default_value": ["400", "600"],
        "tips": "货物规格",
        "type": "complex"
    },
    "side": {
        "value": "",
        "default_value": ["left", "right"],
        "tips": "上下料方向",
        "type": "complex"
    },
    "lift": {
        "value": "",
        "default_value": ["up", "down"],
        "tips": "升降机构",
        "type": "complex"
    },
    "clamp": {
        "value": "",
        "default_value": ["zero", "clamp", "clamp-length"],
        "tips": "夹爪",
        "type": "complex"
    },
    "spin_rad": {
        "value": 0.0,
        "tips": "旋转角度",
        "type": "float"
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

        self.left_block_up_do = p.loadParam("left_block_up_do", type="int", default=20, comment="左挡板上升DO")
        self.left_block_down_do = p.loadParam("left_block_down_do", type="int", default=21, comment="左挡板下降DO")
        self.left_block_up_di = p.loadParam("left_block_up_di", type="int", default=21, comment="左挡板上升到位DI")
        self.left_block_down_di = p.loadParam("left_block_down_di", type="int", default=22, comment="左挡板下降到位DI")

        self.right_block_up_do = p.loadParam("right_block_up_do", type="int", default=18, comment="右挡板上升DO")
        self.right_block_down_do = p.loadParam("right_block_down_do", type="int", default=19, comment="右挡板下降DO")
        self.right_block_up_di = p.loadParam("right_block_up_di", type="int", default=19, comment="右挡板上升到位DI")
        self.right_block_down_di = p.loadParam("right_block_down_di", type="int", default=20,
                                               comment="右挡板下降到位DI")

        self.lift_down_di = p.loadParam("lift_down_di", type="int", default=4, comment="升降机构下到位DI")
        self.lift_up_di = p.loadParam("lift_up_di", type="int", default=6, comment="升降机构上到位DI")
        self.rotate_zero_di = p.loadParam("rotate_zero_di", type="int", default=5, comment="旋转机构零位DI")
        self.clamp_up_di = p.loadParam("clamp_up_di", type="int", default=1, comment="夹爪上到位光电")
        self.clamp_down_di = p.loadParam("clamp_down_di", type="int", default=2, comment="夹爪零位光电")

        self.clamp_motor_name = p.loadParam("clamp_motor_name", type="str", default="clamp", comment="夹爪电机")
        self.lift_motor_name = p.loadParam("lift_motor_name", type="str", default="lift", comment="顶升机构")
        self.spin_motor_name = p.loadParam("spin_motor_name", type="str", default="spin", comment="旋转电机")

        self.motor_speed = p.loadParam("motor_speed", type="float", default=0.03, comment="电机运转速度")
        self.clamp_length = p.loadParam("clamp_length", type="float", default=0.0427, comment="夹爪加紧时的位置")

        self.goods_size = None
        self.lift_opt = None
        self.lift_motor = None
        self.clamp_opt = None
        self.clamp_motor = None
        self.spin_rad = 0
        self.spin_motor = None
        self.operation = None
        self.side = None
        self.sleep_time = 2
        self.tool = ModuleTool
        self.state = dict()
        self.status = MoveStatus.NONE
        self.init = True
        # self.robot = Robot(r)
        self.opt_step = [False] * 10
        self.start_time = time.time()
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args: dict):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name, -1)
            # self.clamp_motor = Motor(r, MotorType.LINEAR_MOTOR, self.clamp_motor_name, -1)
            # self.spin_motor = Motor(r, MotorType.LINEAR_MOTOR, self.spin_motor_name, -1)
            self.goods_size = args.get('goods_size', None)
            self.clamp_opt = args.get('clamp', None)
            self.lift_opt = args.get('lift', None)
            self.spin_rad = args.get('spin_rad', 0.0)
            self.operation = args.get('operation', None)
            self.side = args.get("side", None)

        if self.operation == "load" and self.side == "left":
            self.left_load(r)
        elif self.operation == "load" and self.side == "right":
            self.right_load(r)
        elif self.operation == "unload" and self.side == "left":
            self.left_unload(r)
        elif self.operation == "unload" and self.side == "right":
            self.right_unload(r)
        elif self.operation == "zero":
            self.zero(r)
        elif self.operation == "lift":
            if self.lift(r, self.lift_opt):
                self.status = MoveStatus.FINISHED
        elif self.operation == "clamp":
            if self.clamp(r, self.clamp_opt):
                self.status = MoveStatus.FINISHED
        elif self.operation == "spin":
            if self.spin(r, self.spin_rad):
                self.status = MoveStatus.FINISHED
        else:
            r.setError(f"args error: {args}")

        r.publishSpeed()

        self.state['status'] = self.status
        self.state['args'] = args
        self.state['run_time'] = time.time() - self.start_time
        self.state['spin_motor_pos'] = ModuleTool.get_motor_pos(r, self.spin_motor_name)
        self.state['lift_motor_pos'] = ModuleTool.get_motor_pos(r, self.lift_motor_name)
        self.state['clamp_motor_pos'] = ModuleTool.get_motor_pos(r, self.clamp_motor_name)
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        return self.status

    def left_load(self, r):
        if not self.opt_step[0]:  # 左挡板下降
            r.setDO(self.left_block_down_do, True)  # 左挡板下降
            if self.tool.check_DI(r, self.left_block_down_di):  # 检查左挡板下降到位情况
                r.setDO(self.left_block_down_do, False)  # 关闭下降
                self.opt_step[0] = True

        if self.goods_size == "400":
            if self.opt_step[0] and not self.opt_step[1]:  # 辊筒运动左上料
                r.setDO(self.do1, True)  # 认为左上料是正向
                if self.tool.check_DI(r, self.goods_check_di3):  # 检查货物中间光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    self.opt_step[1] = True

            if self.opt_step[1] and not self.opt_step[2]:  # 还原挡板
                r.setDO(self.left_block_up_do, True)
                if self.tool.check_DI(r, self.left_block_up_di):
                    r.setDO(self.left_block_up_do, False)
                    self.opt_step[2] = True
        else:
            if self.opt_step[0] and not self.opt_step[1]:  # 启动导向电机
                # self.opt_step[1] = self.robot.stretch(self.clamp_motor, self.clamp_length)
                self.opt_step[1] = self.clamp(r, "zero")

            if self.opt_step[1] and not self.opt_step[2]:
                r.setDO(self.do1, True)  # 认为左上料是正向
                if self.tool.check_DI(r, self.goods_check_di4):  # 检查货物中间光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    self.opt_step[2] = True

            if self.opt_step[2] and not self.opt_step[3]:
                # self.opt_step[3] = self.robot.lift(self.lift_motor, self.lift_height)
                self.opt_step[3] = self.lift(r, "up")

            if self.opt_step[3] and not self.opt_step[4]:
                # self.opt_step[4] = self.robot.lift(self.spin_motor, 1.5708)
                self.opt_step[4] = self.spin(r, 1.5708)

            if self.opt_step[4] and not self.opt_step[5]:
                # self.opt_step[5] = self.robot.lift(self.lift_motor, 0)
                self.opt_step[5] = self.lift(r, "down")

            if self.opt_step[5] and not self.opt_step[6]:  # 关闭夹爪
                # self.opt_step[6] = self.robot.stretch(self.clamp_motor, 0)
                self.opt_step[6] = self.clamp(r, "clamp-length")

            if self.opt_step[6] and not self.opt_step[7]:
                r.setDO(self.left_block_up_do, True)
                if self.tool.check_DI(r, self.left_block_up_di):
                    r.setDO(self.left_block_up_do, False)
                    self.opt_step[7] = True

        if self.goods_size == "400" and self.opt_step[2]:
            self.status = MoveStatus.FINISHED
        elif self.goods_size == "600" and self.opt_step[7]:
            self.status = MoveStatus.FINISHED

        load_state = dict()
        load_state['opt_name'] = "left_load"
        load_state['opt_status'] = self.status
        load_state['load_opt'] = self.opt_step[0:8]
        self.state['left_load'] = load_state
        r.logInfo(f"left_load: {load_state}")

    def right_load(self, r):
        if not self.opt_step[0]:  # 右挡板下降
            r.setDO(self.right_block_down_do, True)  # 右挡板下降
            if self.tool.check_DI(r, self.right_block_down_di):  # 检查右挡板下降到位情况
                r.setDO(self.right_block_down_do, False)  # 关闭下降
                self.opt_step[0] = True

        if self.goods_size == "400":
            if self.opt_step[0] and not self.opt_step[1]:  # 辊筒运动右上料
                r.setDO(self.do1, True)  # 认为左上料是反向
                r.setDO(self.do2, True)  # 皮带反转
                if self.tool.check_DI(r, self.goods_check_di2):  # 检查货物中间光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    r.setDO(self.do2, False)
                    self.opt_step[1] = True

            if self.opt_step[1] and not self.opt_step[2]:  # 还原挡板
                r.setDO(self.right_block_up_do, True)
                if self.tool.check_DI(r, self.right_block_up_di):
                    r.setDO(self.right_block_up_do, False)
                    self.opt_step[2] = True
        else:
            if self.opt_step[0] and not self.opt_step[1]:  # 启动导向电机
                # self.opt_step[1] = self.robot.stretch(self.clamp_motor, self.clamp_length)
                self.opt_step[1] = self.clamp(r, "zero")

            if self.opt_step[1] and not self.opt_step[2]:
                r.setDO(self.do1, True)  # 认为右上料是反向
                r.setDO(self.do2, True)  # 皮带反转
                if self.tool.check_DI(r, self.goods_check_di1):  # 检查货物中间光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    r.setDO(self.do2, False)
                    self.opt_step[2] = True

            if self.opt_step[2] and not self.opt_step[3]:
                # self.opt_step[3] = self.robot.lift(self.lift_motor, self.lift_height)  # 启动顶升机构
                self.opt_step[3] = self.lift(r, "up")

            if self.opt_step[3] and not self.opt_step[4]:
                # self.opt_step[4] = self.robot.lift(self.spin_motor, 1.5708)  # 旋转90度
                self.opt_step[4] = self.spin(r, 1.5708)

            if self.opt_step[4] and not self.opt_step[5]:
                # self.opt_step[5] = self.robot.lift(self.lift_motor, 0)  # 顶升机构下降
                self.opt_step[5] = self.lift(r, "down")

            if self.opt_step[5] and not self.opt_step[6]:  # 关闭夹爪
                # self.opt_step[6] = self.robot.stretch(self.clamp_motor, 0)
                self.opt_step[6] = self.clamp(r, "clamp-length")

            if self.opt_step[6] and not self.opt_step[7]:
                r.setDO(self.right_block_up_do, True)
                if self.tool.check_DI(r, self.right_block_up_di):
                    r.setDO(self.right_block_up_do, False)
                    self.opt_step[7] = True

        if self.goods_size == "400" and self.opt_step[2]:
            self.status = MoveStatus.FINISHED
        elif self.goods_size == "600" and self.opt_step[7]:
            self.status = MoveStatus.FINISHED

        load_state = dict()
        load_state['opt_name'] = "right_load"
        load_state['opt_status'] = self.status
        load_state['load_opt'] = self.opt_step[0:8]
        self.state['right_load'] = load_state
        r.logInfo(f"right_load: {load_state}")

    def left_unload(self, r):
        if not self.opt_step[0]:  # 左挡板下降
            r.setDO(self.left_block_down_do, True)  # 左挡板下降
            if self.tool.check_DI(r, self.left_block_down_di):  # 检查左挡板下降到位情况
                r.setDO(self.left_block_down_do, False)  # 关闭下降
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
                if self.tool.delay(self.sleep_time):
                    self.opt_step[2] = True

            if self.opt_step[2] and not self.opt_step[3]:  # 还原挡板
                r.setDO(self.left_block_up_do, True)
                if self.tool.check_DI(r, self.left_block_up_di):
                    r.setDO(self.left_block_up_do, False)
                    self.opt_step[3] = True
        else:
            if self.opt_step[0] and not self.opt_step[1]:  # 启动导向电机
                # self.opt_step[1] = self.robot.stretch(self.clamp_motor, self.clamp_length)
                self.opt_step[1] = self.clamp(r, "zero")

            if self.opt_step[1] and not self.opt_step[2]:
                # self.opt_step[2] = self.robot.lift(self.lift_motor, self.lift_height)  # 升起顶升机构
                self.opt_step[2] = self.lift(r, "up")

            if self.opt_step[2] and not self.opt_step[3]:
                # self.opt_step[3] = self.robot.lift(self.spin_motor, 1.5708)  # 反旋转90度
                self.opt_step[3] = self.spin(r, 0.00001)

            if self.opt_step[3] and not self.opt_step[4]:
                # self.opt_step[4] = self.robot.lift(self.lift_motor, 0)  # 下降顶升机构
                self.opt_step[4] = self.lift(r, "down")

            if self.opt_step[4] and not self.opt_step[5]:
                # self.opt_step[5] = self.robot.stretch(self.clamp_motor, 0)  # 关闭夹爪
                self.opt_step[5] = self.clamp(r, "clamp-length")

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
                if self.tool.delay(self.sleep_time):
                    self.opt_step[7] = True

            if self.opt_step[7] and not self.opt_step[8]:  # 还原挡板
                r.setDO(self.left_block_up_do, True)
                if self.tool.check_DI(r, self.left_block_up_di):
                    r.setDO(self.left_block_up_do, False)
                    self.opt_step[8] = True

        if self.goods_size == "400" and self.opt_step[3]:
            self.status = MoveStatus.FINISHED
        elif self.goods_size == "600" and self.opt_step[8]:
            self.status = MoveStatus.FINISHED

        unload_state = dict()
        unload_state['opt_name'] = "left_unload"
        unload_state['opt_status'] = self.status
        unload_state['unload_opt'] = self.opt_step[0:9]
        self.state['left_unload'] = unload_state
        r.logInfo(f"left_unload: {unload_state}")

    def right_unload(self, r):
        if not self.opt_step[0]:  # 左挡板下降
            r.setDO(self.right_block_down_do, True)  # 左挡板下降
            if self.tool.check_DI(r, self.right_block_down_di):  # 检查左挡板下降到位情况
                r.setDO(self.right_block_down_do, False)  # 关闭下降
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
                if self.tool.delay(self.sleep_time):
                    self.opt_step[2] = True

            if self.opt_step[2] and not self.opt_step[3]:  # 还原挡板
                r.setDO(self.right_block_up_do, True)
                if self.tool.check_DI(r, self.right_block_up_di):
                    r.setDO(self.right_block_up_do, False)
                    self.opt_step[3] = True
        else:
            if self.opt_step[0] and not self.opt_step[1]:  # 启动导向电机
                # self.opt_step[1] = self.robot.stretch(self.clamp_motor, self.clamp_length)
                self.opt_step[1] = self.clamp(r, "zero")

            if self.opt_step[1] and not self.opt_step[2]:
                # self.opt_step[2] = self.robot.lift(self.lift_motor, self.lift_height)  # 升起顶升机构
                self.opt_step[2] = self.lift(r, "up")

            if self.opt_step[2] and not self.opt_step[3]:
                # self.opt_step[3] = self.robot.lift(self.spin_motor, 1.5708)  # 反旋转90度
                self.opt_step[3] = self.spin(r, 0.00001)

            if self.opt_step[3] and not self.opt_step[4]:
                # self.opt_step[4] = self.robot.lift(self.lift_motor, 0)  # 下降顶升机构
                self.opt_step[4] = self.lift(r, "down")

            if self.opt_step[4] and not self.opt_step[5]:
                # self.opt_step[5] = self.robot.stretch(self.clamp_motor, 0)  # 关闭夹爪
                self.opt_step[5] = self.clamp(r, "clamp-length")

            if self.opt_step[5] and not self.opt_step[6]:
                r.setDO(self.do1, True)  # 认为左下料是反向
                if not self.tool.check_DI(r, self.goods_check_di2) and \
                        not self.tool.check_DI(r, self.goods_check_di3) and \
                        not self.tool.check_DI(r, self.goods_check_di1) and \
                        not self.tool.check_DI(r, self.goods_check_di4):  # 检查货物光电
                    r.setDO(self.do1, False)  # 关闭辊筒
                    self.opt_step[6] = True

            if self.opt_step[6] and not self.opt_step[7]:
                if self.tool.delay(self.sleep_time):
                    self.opt_step[7] = True

            if self.opt_step[7] and not self.opt_step[8]:  # 还原挡板
                r.setDO(self.right_block_up_do, True)
                if self.tool.check_DI(r, self.right_block_up_di):
                    r.setDO(self.right_block_up_do, False)
                    self.opt_step[8] = True

        if self.goods_size == "400" and self.opt_step[3]:
            self.status = MoveStatus.FINISHED
        elif self.goods_size == "600" and self.opt_step[8]:
            self.status = MoveStatus.FINISHED

        unload_state = dict()
        unload_state['opt_name'] = "right_unload"
        unload_state['opt_status'] = self.status
        unload_state['unload_opt'] = self.opt_step[:9]
        self.state['right_unload'] = unload_state
        r.logInfo(f"right_unload: {unload_state}")

    def lift(self, r, opt):
        r.setNotice(f"lift opt: {opt}")
        if opt == "up":
            r.setMotorSpeed(self.lift_motor_name, -self.motor_speed, self.lift_up_di)
            if self.tool.check_DI(r, self.lift_up_di):
                r.resetMotor(self.lift_motor_name)
                return True
        elif opt == "down":
            r.setMotorSpeed(self.lift_motor_name, self.motor_speed, self.lift_down_di)
            if self.tool.check_DI(r, self.lift_down_di):
                r.resetMotor(self.lift_motor_name)
                return True
        else:
            r.setError(f"lift opt error: {opt}")
        return False

    def spin(self, r, rad):
        if rad == 0:
            r.setMotorSpeed(self.spin_motor_name, 0.2, self.rotate_zero_di)
            if r.isMotorReached(self.spin_motor_name):
                r.resetMotor(self.spin_motor_name)
                return True
        else:
            r.setMotorPosition(self.spin_motor_name, rad, 0.2, -1)
            if r.isMotorReached(self.spin_motor_name):
                r.resetMotor(self.spin_motor_name)
                return True
        return False

    def clamp(self, r, opt):
        if opt == "zero":
            r.setMotorSpeed(self.clamp_motor_name, -self.motor_speed, self.clamp_down_di)
            if self.tool.check_DI(r, self.clamp_down_di):
                r.resetMotor(self.clamp_motor_name)
                return True
        elif opt == "clamp":
            r.setMotorSpeed(self.clamp_motor_name, self.motor_speed, self.clamp_up_di)
            if self.tool.check_DI(r, self.clamp_up_di):
                r.resetMotor(self.clamp_motor_name)
                return True
        elif opt == "clamp-length":
            r.setMotorPosition(self.clamp_motor_name, self.clamp_length, self.motor_speed, -1)
            if r.isMotorReached(self.clamp_motor_name):
                r.resetMotor(self.clamp_motor_name)
                return True
        else:
            r.setError(f"clamp opt error: {opt}")
        return False

    def suspend(self, r):
        r.setDO(self.do1, False)
        r.setDO(self.do2, False)
        r.setInfo("task suspend!")
        self.status = MoveStatus.SUSPENDED

    def cancel(self, r):
        r.setDO(self.do1, False)
        r.setDO(self.do2, False)
        r.setInfo("task stop!")
        self.status = MoveStatus.NONE

    def zero(self, r):
        r.setDO(self.do1, False)
        r.setDO(self.do2, False)
        if not self.opt_step[0]:
            r.setDO(self.right_block_up_do, True)
            if self.tool.check_DI(r, self.right_block_up_di):
                r.setDO(self.right_block_up_do, False)
                self.opt_step[0] = True

        if self.opt_step[0] and not self.opt_step[1]:
            r.setDO(self.left_block_up_do, True)
            if self.tool.check_DI(r, self.left_block_up_di):
                r.setDO(self.left_block_up_do, False)
                self.opt_step[1] = True

        if self.opt_step[1] and not self.opt_step[2]:
            self.opt_step[2] = self.clamp(r, "zero")

        if self.opt_step[2] and not self.opt_step[3]:
            self.opt_step[3] = self.lift(r, "up")

        if self.opt_step[3] and not self.opt_step[4]:
            self.opt_step[4] = self.spin(r, 0.0)

        if self.opt_step[4] and not self.opt_step[5]:
            self.opt_step[5] = self.lift(r, "down")

        if self.opt_step[5]:
            self.status = MoveStatus.FINISHED

        zero_state = dict()
        zero_state['zero_opt'] = self.opt_step[:6]
        self.state['zero'] = zero_state
        r.logInfo(f"zero: {zero_state}")
