# -*- coding: utf-8 -*-
# @Date: 2023/03/02
# @Author: zhong
# @Version: 1.3
# @Project: 北京德利九州皮带控制脚本
# @Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/2188/detail
# @Update: 脚本检测DO状态并执行对应功能

import json
import time

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
from robot import ModuleTool, MotorType, Motor, Robot

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "load",
        "default_value":["load","unload","adjust", "do_func"],
        "tips": "机构动作选项",
        "type": "complex"        
    },
    "speed": {
        "value": 0.5,
        "tips": "皮带转速",
        "type": "double"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.timeout = 120
        self.adjust_vel = 0.3  # 货物调整位置时速度：m/s
        self.di_a1 = 6
        self.di_b1 = 2
        self.di_c = 5
        self.di_b2 = 8
        self.di_a2 = 7
        self.do_func_unload = 50  # 触发卸货任务的DO
        self.do_func_adjust = [51, 52]  # 触发行李调整的DO列表
        self.do_func_stop = 60  # 触发辊筒停止的DO
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.motor = Motor(r, MotorType.ROLLER_MOTOR, "motor3", -1)
        self.motor_init_pos = ModuleTool.get_motor_pos(r, "motor3")
        self.robot = Robot(r)
        self.opt = None
        self.motor_vel = 0
        self.check_di = ModuleTool.check_DI
        self.unload_flag = False
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            self.opt = args.get("operation", None)
            self.motor_vel = args.get("speed", 0)
            pass

        # 超时判断
        if time.time() - self.start_time > self.timeout:
            r.setError(f"script running timeout")
            self.status = MoveStatus.FAILED

        # =====处理业务逻辑=====
        if self.opt == "load":
            self.load(r)
        elif self.opt == "unload":
            self.unload(r)
        elif self.opt == "adjust":
            self.adjust(r)
        elif self.opt == "do_func":
            self.do_func(r)
        else:
            r.setError(f"script args error!")
            self.status = MoveStatus.FAILED
        pass
        r.publishSpeed()

        # =====数据上报及日志打印=====
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        self.report_info["agv"] = self.robot.state
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def cancel(self, r):
        # =====处理任务取消时的业务=====
        r.setNotice(f"cancel task")
        r.stopRobot(True)
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        r.setNotice(f"suspend task")
        self.robot.run_motor(self.motor, vel=0, reach_di=-1)
        r.resetMotor()
        self.status = MoveStatus.SUSPENDED

    def do_func(self, r):
        if ModuleTool.check_DO(r, self.do_func_unload):
            self.unload(r)
        elif ModuleTool.check_DO(r, self.do_func_stop):
            self.robot.run_motor(self.motor, vel=0, reach_di=-1)
            r.resetMotor()
            self.status = MoveStatus.FINISHED
        else:
            for di in self.do_func_adjust:
                if ModuleTool.check_DO(r, di):
                    self.adjust(r)

    def load(self, r):
        # 检测到任意光电，开始调整货物位置
        if (self.check_di(r, self.di_a1) or self.check_di(r, self.di_b1) or self.check_di(r, self.di_c) or
                self.check_di(r, self.di_a2) or self.check_di(r, self.di_b2)):
            if self.adjust(r):
                r.setGoodsShape(0., 0., 0.)
        else:
            self.robot.run_motor(self.motor, vel=self.motor_vel, reach_di=-1)

    def unload(self, r):
        # 确认货物触发过 a1 或 a2 光电
        if self.check_di(r, self.di_a1) or self.check_di(r, self.di_a2):
            self.unload_flag = True
        # 未检测到任何光电且货物触发过 a1 或 a2
        if not (self.check_di(r, self.di_a1) or self.check_di(r, self.di_b1) or self.check_di(r, self.di_c) or
                self.check_di(r, self.di_a2) or self.check_di(r, self.di_b2)) and self.unload_flag:
            # 超过2秒未检测到任何光电，辊筒停转，卸货完成
            if ModuleTool.delay(2):
                self.robot.run_motor(self.motor, vel=0, reach_di=-1)
                r.clearGoodsShape()
                self.status = MoveStatus.FINISHED
        else:
            self.robot.run_motor(self.motor, vel=self.motor_vel, reach_di=-1)

    def adjust(self, r):
        # =============== a1 - b1 - c - b2 - a2 ====================
        # 物料过大
        if self.check_di(r, self.di_a1) and self.check_di(r, self.di_a2):
            r.setError(f"Oversize goods")
            return False
        # 小料到位
        elif self.check_di(r, self.di_c) and not self.check_di(r, self.di_b1) and not self.check_di(r, self.di_b2):
            self.robot.run_motor(self.motor, vel=0, reach_di=-1)
            self.status = MoveStatus.FINISHED
            return True
        # 大料到位
        elif self.check_di(r, self.di_c) and self.check_di(r, self.di_b1) and self.check_di(r, self.di_b2) \
                and not self.check_di(r, self.di_a1) and not self.check_di(r, self.di_a2):
            self.robot.run_motor(self.motor, vel=0, reach_di=-1)
            self.status = MoveStatus.FINISHED
            return True
        # 物料偏左
        elif self.check_di(r, self.di_a1) and self.check_di(r, self.di_b2) and not self.check_di(r, self.di_a2):
            self.robot.run_motor(self.motor, vel=self.adjust_vel, reach_di=-1)
        elif self.check_di(r, self.di_a1) and self.check_di(r, self.di_c) and not self.check_di(r, self.di_b2):
            self.robot.run_motor(self.motor, vel=self.adjust_vel, reach_di=-1)
        elif self.check_di(r, self.di_a1) and self.check_di(r, self.di_b1) and not self.check_di(r, self.di_c):
            self.robot.run_motor(self.motor, vel=self.adjust_vel, reach_di=-1)
        elif self.check_di(r, self.di_a1) and not self.check_di(r, self.di_b1):
            self.robot.run_motor(self.motor, vel=self.adjust_vel, reach_di=-1)
        elif not self.check_di(r, self.di_a1) and self.check_di(r, self.di_b1) and not self.check_di(r, self.di_c):
            self.robot.run_motor(self.motor, vel=self.adjust_vel, reach_di=-1)
        elif not self.check_di(r, self.di_a1) and self.check_di(r, self.di_b1) \
                and self.check_di(r, self.di_c) and not self.check_di(r, self.di_b2):
            self.robot.run_motor(self.motor, vel=self.adjust_vel, reach_di=-1)
        # 物料偏右
        elif self.check_di(r, self.di_a2) and self.check_di(r, self.di_b1) and not self.check_di(r, self.di_a1):
            self.robot.run_motor(self.motor, vel=-self.adjust_vel, reach_di=-1)
        elif self.check_di(r, self.di_a2) and self.check_di(r, self.di_c) and not self.check_di(r, self.di_b1):
            self.robot.run_motor(self.motor, vel=-self.adjust_vel, reach_di=-1)
        elif self.check_di(r, self.di_a2) and self.check_di(r, self.di_b2) and not self.check_di(r, self.di_c):
            self.robot.run_motor(self.motor, vel=-self.adjust_vel, reach_di=-1)
        elif self.check_di(r, self.di_a2) and not self.check_di(r, self.di_b2):
            self.robot.run_motor(self.motor, vel=-self.adjust_vel, reach_di=-1)
        elif not self.check_di(r, self.di_a2) and self.check_di(r, self.di_b2) and not self.check_di(r, self.di_c):
            self.robot.run_motor(self.motor, vel=-self.adjust_vel, reach_di=-1)
        elif not self.check_di(r, self.di_a2) and self.check_di(r, self.di_b2) \
                and self.check_di(r, self.di_c) and not self.check_di(r, self.di_b1):
            self.robot.run_motor(self.motor, vel=-self.adjust_vel, reach_di=-1)
        else:
            r.setNotice(f"In the process of adjusting")
        return False


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
