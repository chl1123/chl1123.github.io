# -*- coding: utf-8 -*-
# @Date: 2023/02/13
# @Author: zhong
# @File: userDefinedAlarm.py
# @Version: 1.0
# @Project:支持用户输出自定义报警
# @Coding: https://seer-group.coding.net/p/order_issue_pool/requirements/issues/2259/detail
# @Update:

import json
import time

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "setError",
        "default_value":["setError","clearError", "setErrorList", "clearErrorList"],
        "type": "complex"        
    },
    "code":{
        "value": "301",
        "type": "string"
    },
    "content":{
        "value": "",
        "type": "string"        
    },
    "errCodeList":{
        "value": "",
        "type": "json"        
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",
                                   comment=" 运行超时时间")
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.opt = None
        self.err_code = ""
        self.err_content = ""
        self.err_code_list = []
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        """
        # with setError:
        {
            "errCodeList": [
                {"code": "301", "content": "error1"},
                {"code": "302", "content": "error2"}
            ]
        }

        # with clearError:
        {
            "errCodeList": ["301", "302", "303"]
        }
        """
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            self.opt = args.get("operation", None)
            self.err_code = args.get("code", "-1")
            self.err_content = args.get("content", "null")
            self.err_code_list = args.get("errCodeList", [])
            pass

        # 超时判断
        if time.time() - self.start_time > self.timeout:
            r.setError(f"script running timeout")

        # =====处理业务逻辑=====
        if self.opt == 'setError':
            if self.err_code in CodeMapping.CODEMAPPING:
                r.setUserError(int(CodeMapping.CODEMAPPING.get(self.err_code)), self.err_content or "null")
            else:
                r.setError(f"unsupported error code: {self.err_code}")
            pass
        elif self.opt == 'clearError':
            if self.err_code in CodeMapping.CODEMAPPING:
                r.clearError(int(CodeMapping.CODEMAPPING.get(self.err_code)))
            else:
                r.setError(f"unsupported error code: {self.err_code}")
            pass
        elif self.opt == 'setErrorList':
            for err in self.err_code_list:
                try:
                    r.setUserError(int(CodeMapping.CODEMAPPING.get(err.get("code"))), err.get("content"))
                except Exception as e:
                    r.setError(f"script args error! exception:{e}")
            pass
        elif self.opt == 'clearErrorList':
            for err in self.err_code_list:
                try:
                    r.clearError(int(CodeMapping.CODEMAPPING.get(err)))
                except Exception as e:
                    r.setError(f"script args error! exception:{e}")
            pass
        else:
            r.setError(f"script args error: {args}")
            self.status = MoveStatus.FAILED
        pass

        # =====数据上报及日志打印=====
        self.status = MoveStatus.FINISHED
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
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


class CodeMapping:
    """
    用户自定义报错码和 RBK 报错码映射表
    用户可自行扩展, 最多支持50个自定义报错
    RBK 报错码范围: 53950~53999
    """
    CODEMAPPING = {
        "301": "53950",
        "302": "53951",
        "303": "53952",
        "304": "53953",
        "305": "53954",
        "306": "53955",
        "307": "53956",
        "308": "53957",
        "309": "53958",
        "310": "53959",
        "311": "53960",
        "650": "53961",
        "651": "53962",
        "800": "53963",
        "801": "53964"
    }


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
