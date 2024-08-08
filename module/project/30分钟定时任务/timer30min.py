# -*- coding: utf-8 -*-
# @Date: 2023/07/5
# @Author: CXN
# @File: comm.py
# @Version: 1.0
# @Project:
# @Coding:https://seer-group.coding.net/p/order_issue_pool/requirements/issues/3960/detail
# @Update: 30分钟的定时任务

import json
import sys
import time

sys.path.append("../syspy")
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.rbkSim import SimModule
from syspy.robot import ModuleTool


class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        self.init = True

        self.start_time = time.time()
        self.status = MoveStatus.NONE
        self.number= 0
        self.do = 3  # 需要在PP点打开的 DO
        self.dist = 0.1  # 判断是否在PP点的精度
        self.timer = 1  # 定时时间，单位是秒
        self.PP = "PP287"  # PP点位置
        self.percetage = 1  # 电池的阈值，范围 0 -1


    def periodRun(self, r: SimModule) -> bool:
        task_state = dict()
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        task_state["current_time"] = current_time
        task_state["elapsed_time"] = elapsed_time
        task_state["battery"] = r.battery()
        task_state["start_time"] = self.start_time
        battery = r.battery()
        percetage = battery.get("percetage",1)
        task_state["percetage"] = percetage
        l = r.loc()
        loc = (l.get("x", 0.), l.get("y", 0.), l.get("angle"))
        pp_l = r.getLM(self.PP,True)
        task_state["loc"] = loc
        task_state["pp_loc"] = pp_l

        # 每半小时输出信息
        if elapsed_time > self.timer:
            self.number += 1
            task_state["number"] = self.number
            if self.is_same_location(loc,pp_l) and self.percetage >= percetage:
                task_state["Do"] = r.Do()
                if r.Do().get("node", None):
                    r.setDO(self.do,True)
                    task_state["setDO"] = True

                    # 重新设置开始时间
                    self.start_time = time.time()
        else:
            task_state["setDO"] = False
        r.setInfo(json.dumps(task_state))
        r.logInfo(json.dumps(task_state))
        return True

    def is_same_location(self,coord1, coord2):
        # 检查三个维度之间的差距是否都在允许范围内
        x_diff = abs(coord1[0] - coord2[0])
        y_diff = abs(coord1[1] - coord2[1])
        z_diff = abs(coord1[2] - coord2[2])

        if x_diff <= self.dist and y_diff <= self.dist and z_diff <= self.dist:
            return True
        else:
            return False



    def run(self, r:SimModule,args:json):
        """主函数，每个运行周期都会执行run函数


        """
        self.status = MoveStatus.RUNNING
        if self.status == MoveStatus.FINISHED:
            return self.status.value
        self.periodRun(r)
        #self.status = MoveStatus.FINISHED
        return self.status