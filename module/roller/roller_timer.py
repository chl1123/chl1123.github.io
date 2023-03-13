# -*- coding: utf-8 -*-
# @Date : 2023/03/13
# @Author : zhong
# @File :roller_timer.py
# @Version : 1.0
# @Project : 脚本控制辊筒运转固定时间

import json
import time
from rbk import MoveStatus, BasicModule
from rbkSim import SimModule

"""
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value": [
            "RollerRunning", "RollerStop"
        ],
        "tips": "辊筒操作选项",
        "type": "complex"
    },
    "side":{
        "value": "",
        "default_value":["left","right"],
        "tips": "辊筒运转方向",
        "type": "complex"
    },
    "time":{
        "value": 5,
        "tips": "辊筒运转时长/秒",
        "type": "double"
    },
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.over_time = 60  # 脚本运行超时时间
        self.start_time = time.time()  # 记录脚本开始运行的时间
        self.report_info = dict()   # 脚本上报数据
        self.init = True   # 标识符
        self.status = MoveStatus.NONE  # 脚本运行状态
        self.roller_speed = 0.3   # 辊筒运转的速度, 正负决定辊筒运转方向, 大小决定辊筒运转快慢
        self.motor_name = "roller"
        self.opt = None
        self.side = None
        self.time = None
        r.logInfo(f"init args: {args}")  # 初始化日志打印，便于日志分析时查询该字段

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # 获取脚本输入参数
            self.opt = args.get("operation", None)
            self.side = args.get("side", None)
            self.time = args.get("time", None)

        # time.time() 获取系统当前时间
        if time.time() - self.start_time > self.over_time:
            r.setError(f"脚本运行超时！")

        if self.opt and self.side and self.time:  # 确认输入的三个参数值都存在
            if self.opt == "RollerRunning":
                self.roller_running(r)
            elif self.opt == "RollerStop":
                self.roller_stop(r)
            else:
                r.setError(f"args input error: {args}")
                self.status = MoveStatus.FAILED
        else:
            r.setError(f"args lost: {args}")
            self.status = MoveStatus.FAILED

        # 下发电机控制速度
        r.publishSpeed()

        # 数据上报，日志打印
        self.report_info["status"] = self.status
        self.report_info["args"] = args
        r.setInfo(json.dumps(self.report_info))
        r.logDebug(json.dumps(self.report_info))
        return self.status

    def roller_running(self, r: SimModule):
        if self.side == "left":
            r.setMotorSpeed(self.motor_name, self.roller_speed, -1)
        elif self.side == "right":
            # 速度值正负不一样
            r.setMotorSpeed(self.motor_name, -self.roller_speed, -1)
        else:
            r.setError(f"side input error: {self.side}")

        # 计算辊筒运转时间
        if time.time() - self.start_time > self.time:
            r.setMotorSpeed(self.motor_name, 0, -1)  # 速度值给0
            r.resetMotor(self.motor_name)  # 将电机复位
            self.status = MoveStatus.FINISHED  # 任务完成

    def roller_stop(self, r):
        r.setMotorSpeed(self.motor_name, 0, -1)  # 速度值给0
        r.resetMotor(self.motor_name)
        self.status = MoveStatus.FINISHED

    # 取消任务时触发
    def cancel(self, r: SimModule):
        self.roller_stop(r)
        self.status = MoveStatus.NONE

    # 暂停任务时触发
    def suspend(self, r: SimModule):
        r.setMotorSpeed(self.motor_name, 0, -1)
        self.status = MoveStatus.SUSPENDED


if __name__ == '__main__':
    pass
