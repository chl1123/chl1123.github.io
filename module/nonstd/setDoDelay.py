# -*- coding: utf-8 -*-
# @Date: 2023/02/27
# @Author: zhong
# @Version: 1.0
# @Project: 延时设置DO状态
# @Coding:
# @Update:

import json
import time
import math
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
from robot import ModuleTool

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "DO":{
        "value": [
            {"id": 1, "status": false},
            {"id": 2, "status": true}
        ],
        "type": "json"
    },
    "delay":{
        "value": 2.0,
        "type": "float"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.delay_time = 0
        self.do_list = []
        r.logInfo(f"init args: {args}")
    
    def run(self, r: SimModule, args):
        if self.init:
            self.init = False
            self.delay_time = args.get("delay", 0)
            self.do_list = args.get("DO", [])
        self.status = MoveStatus.RUNNING
        if time.time() - self.start_time > self.delay_time:
            for item in self.do_list:
                try:
                    r.setDO(item["id"], item["status"])
                except Exception as e:
                    r.setError(f"Err: {e}, args: {args}")
                    
            self.status = MoveStatus.FINISHED
        # =====数据上报及日志打印=====
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
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
