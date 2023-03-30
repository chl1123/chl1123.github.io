# -*- coding: utf-8 -*-
# @Date: 2023/03/30
# @Author: zhong
# @File: clearWarnings.py
# @Version: 1.0
# @Project: 用于清除过期的告警提示信息
# @Coding: https://seer-group.coding.net/p/robokit/requirements/issues/1760/detail
# @Update:

"""
脚本提供一键清除功能，包含以下：
一键清除所有 notice，warning，error 提示信息
清除指定 code 的 warning
清除指定 code 的 error
备注： 1 提到的所有notice， warning 和 error，仅包括机构脚本上报的告警提示，其他服务的告警信息可以通过指定报错码清除
"""

import json
import time

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
from robot import ModuleTool

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "clearAllWarning",
        "default_value":["clearAll", "clearError", "clearWarning"],
        "type": "complex"        
    },
    "code":{
        "value": 55300,
        "tips": "指定要清除的报错码",
        "type": "int"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.timeout = 60
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.opt = args.get("operation", None)
        self.code = args.get("code", None)
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if time.time() - self.start_time > self.timeout:
            r.setError(f"script running timeout")

        if self.opt == 'clearWarning' and self.code:
            r.clearWarning(self.code)

        elif self.opt == 'clearError' and self.code:
            r.clearError(self.code)

        elif self.opt == 'clearAll':
            """
            清除所有机构脚本相关的告警
            """
            r.clearNotice(57019)
            r.clearNotice(57300)
            r.clearWarning(55300)
            r.clearError(53000)
            for code in range(53900, 54000):
                r.clearError(code)
            for code in range(55900, 56000):
                r.clearWarning(code)
        else:
            r.setError(f"script args error: {args}")
            self.status = MoveStatus.FAILED

        if ModuleTool.delay(0.3):
            self.status = MoveStatus.FINISHED

        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def cancel(self, r):
        r.setNotice(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r):
        r.setNotice(f"suspend task")
        self.status = MoveStatus.SUSPENDED
