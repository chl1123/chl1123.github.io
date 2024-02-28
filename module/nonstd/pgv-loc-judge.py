# -*- coding: utf-8 -*-
# @Date: 2023/02/27
# @Author: zhong
# @Version: 1.0
# @Project: pgv 定位误差分析
# @Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/5540/detail
# @Update:

import json
import time
import math
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####

####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.diff_x = 0.1  # x偏差阈值
        self.diff_y = 0.1  # y偏差阈值
        self.diff_angle = 0.1  # 角度偏差阈值
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if time.time() - self.start_time > 3:
            self.status = MoveStatus.FINISHED

        # =====处理业务逻辑=====
        pgv_data = r.pgv().get("pgvs", [{}])[0]
        is_detected = pgv_data.get("is_DMT_detected", False)
        diff_x = pgv_data.get("tag_diff_x", 0.0)
        diff_y = pgv_data.get("tag_diff_y", 0.0)
        diff_angle = pgv_data.get("tag_diff_angle", 0.0)
        if is_detected:
            if abs(diff_x) > self.diff_x:
                r.setUserError(53901, f"前后偏差大于{diff_x}米")
            if abs(diff_y) > self.diff_y:
                r.setUserError(53902, f"左右偏差大于{diff_x}米")
            if abs(diff_angle) > self.diff_angle:
                r.setUserError(53903, f"角度偏差大于{round(diff_x*180/math.pi, 6)}度")
        else:
            r.setError(f"PGV data not captured")
        
        # =====数据上报及日志打印=====
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        self.report_info['pgv_data'] = pgv_data
        self.report_info['diff'] = {"diff_x": diff_x, "diff_y": diff_y, "diff_angle": diff_angle}

        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def cancel(self, r: SimModule):
        # =====处理任务取消时的业务=====
        r.setNotice(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        # =====处理任务暂停时的业务=====
        r.setNotice(f"suspend task")
        self.status = MoveStatus.SUSPENDED


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
