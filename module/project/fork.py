# -*- coding: utf-8 -*-
# @Date: 2024/01/22
# @Author: zhong
# @Version: 1.0
# @Project:冠鸿-宇锋-仙工叉车
# @Coding:https://seer-group.coding.net/p/order_issue_pool/assignments/issues/5261/detail
# @Update: 控制下压装置和货叉

import json
import time
import sys
sys.path.append("../syspy")
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import ModuleTool, MotorType, Motor, Robot

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "reset",
        "default_value":["reset","lift","clamp", "preload", "goto_site"],
        "type": "complex"
    },
    "lift_height": {
        "value": 0.079,
        "tips": "举升高度值",
        "type": "float",
        "unit": "m"
    },
    "clamp_length": {
        "value": 0.079,
        "tips": "夹紧距离值",
        "type": "float",
        "unit": "m"
    },
    "site": {
        "value": "",
        "tips": "目标站点",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.timeout = p.loadParam("timeout", type="int", default=300, unit="s", comment="程序运行超时时间")
        self.lift_min_height = p.loadParam("lift_min_height", type="float", default=0.079, unit="m", comment="举升最小值")
        self.lift_max_height = p.loadParam("lift_max_height", type="float", default=1.70, unit="m", comment="举升最大值")
        self.load_safety_height = p.loadParam("load_safety_height", type="float", default=0.079, unit="m", comment="载货状态安全高度")
        self.clamp_min_height = p.loadParam("clamp_min_height", type="float", default=0.355, unit="m", comment="夹紧最小值")
        self.clamp_max_height = p.loadParam("clamp_max_height", type="float", default=1.355, unit="m", comment="夹紧最大值")
        self.up_limit_di = p.loadParam("up_limit_di", type="int", default=6, comment="货叉上限位DI")
        self.down_limit_di = p.loadParam("down_limit_di", type="int", default=-1, comment="下限位DI")
        self.clamp_reach_di1 = p.loadParam("clamp_reach_di1", type="int", default=20, comment="夹紧到位DI1")
        self.clamp_reach_di2 = p.loadParam("clamp_reach_di2", type="int", default=21, comment="夹紧到位DI2")
        self.clamp_reach_di3 = p.loadParam("clamp_reach_di3", type="int", default=22, comment="夹紧到位DI3")
        self.lift_motor_name = p.loadParam("lift_motor_name", type="str", default="JUSHENG", comment="举升电机名称")
        self.clamp_motor_name = p.loadParam("clamp_motor_name", type="str", default="JIAJIN", comment="夹紧电机名称")
        self.max_lift_speed = p.loadParam("max_lift_speed", type="float", default=0.08, comment="举升电机最大速度")
        self.max_clamp_speed = p.loadParam("max_clamp_speed", type="float", default=0.08, comment="夹紧电机最大速度")
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name, -1)
        self.clamp_motor = Motor(r, MotorType.LINEAR_MOTOR, self.clamp_motor_name, -1)
        self.init_lift_height = None
        self.init_clamp_height = None
        self.robot = Robot(r)
        self.task_lift_height = None
        self.task_clamp_length = None
        self.task_site = None
        self.task = args
        self.opt = None
        self.opt_length = 10
        self.opt_step = [False]*self.opt_length
        self.check_di = ModuleTool.check_DI
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            self.init_lift_height = ModuleTool.get_motor_pos(r, self.lift_motor_name)
            self.init_clamp_height = ModuleTool.get_motor_pos(r, self.clamp_motor_name)
            self.task_lift_height = args.get("lift_height", None)
            self.task_clamp_length = args.get("clamp_length", None)
            self.task_site = args.get("site", None)
            self.opt = args.get("operation", None)
        
        if self.opt == "reset":
            self.zero(r)
        elif self.opt == "lift":
            self.lift(r)
        elif self.opt == "clamp":
            self.clamp(r)
        elif self.opt == "preload":
            self.preload(r)

        # 超时判断
        if time.time() - self.start_time > self.timeout:
            r.setError(f"script running timeout")
            self.status = MoveStatus.FAILED

        # =====处理业务逻辑=====
        r.publishSpeed()  # 下发电机速度
        
        # =====数据上报及日志打印=====
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        self.report_info['motor_info'] = self.robot.state
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def cancel(self, r):
        # =====处理任务取消时的业务=====
        r.setNotice(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        r.setNotice(f"suspend task")
        self.status = MoveStatus.SUSPENDED
        
    def zero(self, r):
        self.task_clamp_length = self.clamp_max_height
        self.task_lift_height = self.lift_min_height
        if not self.opt_step[0]:
            self.opt_step[0] = self.clamp(r)
        elif self.opt_step[0] and not self.opt_step[1]:
            self.opt_step[1] = self.lift(r)
        if all(self.opt_step[:2]):
            self.status = MoveStatus.FINISHED
            return True
        return False
        
    def lift(self, r):
        if self.task_lift_height is None:
            r.setError(f"Missing lift_height parameters! {self.task}")
            self.status = MoveStatus.FAILED
            return False
        if self.task_lift_height <= self.lift_min_height:
            self.task_lift_height = self.lift_min_height
        if self.task_lift_height >= self.lift_max_height:
            self.task_lift_height = self.lift_max_height
            
        self.opt_step[0] = self.robot.run_motor(self.lift_motor, pos=self.task_lift_height, max_vel=self.max_lift_speed)
        if self.opt_step[0]:
            self.status = MoveStatus.FINISHED
            return True
        return False
        
    def clamp(self, r):
        if self.task_clamp_length is None:
            r.setError(f"Missing clamp_length parameters! {self.task}")
            self.status = MoveStatus.FAILED
            return False
        if self.task_clamp_length <= self.clamp_min_height:
            self.task_clamp_length = self.clamp_min_height
            self.opt_step[0] = not (self.check_di(r, self.clamp_reach_di1) or self.check_di(r, self.clamp_reach_di2)
                                    or self.check_di(r, self.clamp_reach_di3))
            self.opt_step[0] = self.opt_step[0] or self.robot.run_motor(self.clamp_motor, self.task_clamp_length,
                                                                        max_vel=self.max_clamp_speed)
            
        elif self.task_clamp_length >= self.clamp_max_height:
            self.task_clamp_length = self.clamp_max_height
            self.opt_step[0] = (self.check_di(r, self.clamp_reach_di1) and self.check_di(r, self.clamp_reach_di2)
                                and self.check_di(r, self.clamp_reach_di3))
            self.opt_step[0] = self.opt_step[0] and self.robot.run_motor(self.clamp_motor, self.task_clamp_length,
                                                                         max_vel=self.max_clamp_speed)
            
        else:
            self.opt_step[0] = self.robot.run_motor(self.clamp_motor, self.task_clamp_length,
                                                    max_vel=self.max_clamp_speed)
        
        if self.opt_step[0]:
            self.status = MoveStatus.FINISHED
            return True
        return False
    
    def preload(self, r):
        if not self.opt_step[0]:
            self.opt_step[0] = self.clamp(r)
        elif self.opt_step[0] and not self.opt_step[1]:
            self.opt_step[1] = self.lift(r)
        if all(self.opt_step[:2]):
            self.status = MoveStatus.FINISHED
            return True
        return False

    def goto_site(self, r):
        task = r.moveTask()
        r.addMoveTaskList(json.dumps(task))
        self.status = r.goMapPath(json.dumps(r.moveTask()))
        pass
    
    def load(self, r):
        pass
    
    def unload(self):
        pass


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
