# -*- coding: utf-8 -*-
# @Date : 2022/7/18
# @Author : zhong
# @File :interact.py
# @Version : 1.0
# @Project : https://seer-group.coding.net/p/issue_pool/requirements/issues/3427/detail
# @Protocol: 海柔库卡项目接口文档V1.4;  [RDSCore与终端交互] https://seer-group.yuque.com/pf4yvd/lg4q1h/wbno17
import json
import time
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
from robot import NetHandle

SCRIPT_VERSION = "V1.0-20220718"

"""
####BEGIN DEFAULT ARGS####
{
    "addr":{
        "value":"http://127.0.0.1:8088",
        "tips": "通信地址",
        "type":"string"
    },
    "data":{
        "value":{
            "id": "Terminal-01",
            "type": "write",
            "value": 666
        },
        "tips": "通信数据",
        "type":"json"
    },
    "protocol": {
        "value": "HTTP",
        "default_value":["HTTP","ModbusTCP"],
        "tips": "通信协议",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super().__init__()
        self.addr = None
        self.data = None
        self.protocol = None
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.init = True
        self.net_handle = NetHandle()
        self.flag = [False]*3
        self.start_time = time.time()
        self.reach_data = None
        self.action_data = None
        self.finish_data = None
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.addr = args.get("addr", None)
            self.data = args.get("data", None)
            self.protocol = args.get("protocol", None)
            r.logDebug(f"addr: {self.addr}, data: {self.data}, protocol: {self.protocol}")

        if time.time() - self.start_time > 60:
            r.setError(f"script running time out")
            self.status = MoveStatus.FAILED

        if self.addr and self.data and self.protocol:
            self.reach_data = self.data.get("reach", None)
            self.action_data = self.data.get("action", None)
            self.finish_data = self.data.get("finish", None)
            r.logInfo(f"reach_data: {self.reach_data}, action_data: {self.action_data}, finish_data: {self.finish_data}")
            if self.protocol == "HTTP":
                get_addr = f"{str(self.addr)}/getTerminalStatus"
                post_addr = f"{str(self.addr)}/setRobotStatus"
                if not self.flag[0] and not self.reach_data:
                    reach_res = self.net_handle.http_post(r, post_addr, data=self.reach_data)
                    r.logInfo(f"reach_res: {reach_res.text}")
                    if reach_res and reach_res.status_code == 200:
                        self.flag[0] = True
                else:
                    self.flag[0] = True

                if not self.flag[1] and not self.action_data:
                    action_res = self.net_handle.http_get(r, get_addr)
                    r.logInfo(f"action_res: {action_res.text}")
                    if action_res and action_res.status_code == 200:
                        self.flag[1] = True
                else:
                    self.flag[1] = True

                if not self.flag[2] and not self.finish_data:
                    finish_res = self.net_handle.http_post(r, post_addr, data=self.finish_data)
                    r.logInfo(f"finish_res: {finish_res}")
                    if finish_res and finish_res.status_code == 200:
                        self.flag[2] = True
                else:
                    self.flag[2] = True
                if all(self.flag):
                    self.status = MoveStatus.FINISHED

            elif self.protocol == "ModbusTCP":
                if not self.flag[0] and not self.reach_data:
                    reach_res = self.net_handle.call_terminal(r, self.addr, self.reach_data)
                    r.logInfo(f"reach_res: {reach_res.text}")
                    if reach_res and reach_res.status_code == 200:
                        self.flag[0] = True
                else:
                    self.flag[0] = True
                if not self.flag[1] and not self.action_data:
                    action_res = self.net_handle.call_terminal(r, self.addr, self.action_data)
                    r.logInfo(f"action_res: {action_res.text}")
                    if action_res and action_res.status_code == 200:
                        self.flag[1] = True
                else:
                    self.flag[1] = True

                if not self.flag[2] and not self.finish_data:
                    finish_res = self.net_handle.call_terminal(r, self.addr, self.finish_data)
                    r.logInfo(f"finish_res: {finish_res.text}")
                    if finish_res and finish_res.status_code == 200:
                        self.flag[2] = True
                else:
                    self.flag[2] = True
                if all(self.flag):
                    self.status = MoveStatus.FINISHED
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED

        self.report_info["script args"] = args
        self.report_info["status"] = self.status
        self.report_info["flag"] = self.flag
        self.report_info["script-version"] = SCRIPT_VERSION
        r.setInfo(json.dumps(self.report_info))
        return self.status


if __name__ == '__main__':
    r = SimModule()
    args = dict()
    m = Module(r, args)
    m.run(r, args)
