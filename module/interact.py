# -*- coding: utf-8 -*-
# @Date : 2022/8/5
# @Author : zhong
# @File :interact.py
# @Version : 1.3
# @Project : https://seer-group.coding.net/p/issue_pool/requirements/issues/3427/detail
# @Protocol: [RDSCore与终端交互] https://seer-group.yuque.com/pf4yvd/lg4q1h/wbno17
import json
import time
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import NetHandle

SCRIPT_VERSION = "V1.1-20220805"

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
        p = ParamServer(__file__)
        self.get_path = p.loadParam("get_path", type="str", default="/api/get path", comment="HTTP-GET-API 路径")
        self.post_path = p.loadParam("post_path", type="str", default="/api/post path", comment="HTTP-POST-API 路径")
        self.read_value = p.loadParam("read_value", type="int", default=-1, comment="读取寄存器指定的值，为 -1 时该参数不生效")
        self.http_get_key = p.loadParam("http_get_key", type="str", default="code", comment="HTTP-GET 请求成功判断字段，不启用时设为空")
        self.http_get_value = p.loadParam("http_get_value", type="int", default=0, comment="HTTP-GET 请求成功判断字段值")
        self.wait_time = p.loadParam("timeout", type="int", default=60, comment="通信等待最长时间(秒)")
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

        if time.time() - self.start_time > self.wait_time:
            r.setError(f"script running time out")
            self.status = MoveStatus.FAILED

        if self.addr and self.data and self.protocol:
            self.reach_data = self.data.get("reach", None)
            self.action_data = self.data.get("action", None)
            self.finish_data = self.data.get("finish", None)
            if self.reach_data is None:
                self.flag[0] = True
            if self.action_data is None:
                self.flag[1] = True
            if self.finish_data is None:
                self.flag[2] = True
            r.logInfo(f"reach_data: {self.reach_data}, action_data: {self.action_data}, finish_data: {self.finish_data}")

            if self.protocol == "HTTP":
                get_addr = str(self.addr) + self.get_path
                post_addr = str(self.addr) + self.post_path
                if not self.flag[0]:
                    reach_res = self.net_handle.http_post(r, post_addr, data=self.reach_data)
                    r.logInfo(f"reach_res: {reach_res}")
                    if reach_res and reach_res.status_code == 200:
                        self.flag[0] = True

                if self.flag[0] and not self.flag[1]:
                    action_res = self.net_handle.http_get(r, get_addr, params=self.action_data)
                    r.logInfo(f"action_res: {action_res}")
                    if action_res and action_res.status_code == 200:
                        if bool(self.http_get_key):
                            if action_res.json().get("code",  None) == self.http_get_value:
                                self.flag[1] = True
                        else:
                            self.flag[1] = True

                if self.flag[1] and not self.flag[2]:
                    finish_res = self.net_handle.http_post(r, post_addr, data=self.finish_data)
                    r.logInfo(f"finish_res: {finish_res}")
                    if finish_res and finish_res.status_code == 200:
                        self.flag[2] = True

                if all(self.flag):
                    self.status = MoveStatus.FINISHED

            elif self.protocol == "ModbusTCP":
                if not self.flag[0]:
                    reach_res = self.net_handle.call_terminal(r, self.addr, self.reach_data)
                    r.logInfo(f"reach_res: {reach_res}")
                    if reach_res and reach_res.get("status", -1) != -1:
                        self.flag[0] = True

                if self.flag[0] and not self.flag[1]:
                    action_res = self.net_handle.call_terminal(r, self.addr, self.action_data)
                    r.logInfo(f"action_res: {action_res}")
                    if action_res and action_res.get("status", -1) != -1:
                        if self.read_value != -1:
                            if action_res.get("status", -1) == self.read_value:
                                self.flag[1] = True
                        else:
                            self.flag[1] = True

                if self.flag[1] and not self.flag[2]:
                    finish_res = self.net_handle.call_terminal(r, self.addr, self.finish_data)
                    r.logInfo(f"finish_res: {finish_res}")
                    if finish_res and finish_res.get("status", -1) != -1:
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
        r.logInfo(json.dumps(self.report_info))
        r.setInfo(json.dumps(self.report_info))
        return self.status


if __name__ == '__main__':
    r = SimModule()
    args = {
        'addr': 'http://192.168.8.36:8885',
        'data': {
            'action': {'id': 'terminal-MA1181-C02-02'},
            'reach': {'id': 'terminal-MA1181-C02-02', 'status': '1'},
            'finish': {'id': 'terminal-MA1181-C02-02', 'status': '0'}
        },
        'protocol': 'HTTP'
    }
    m = Module(r, args)
    m.run(r, args)
