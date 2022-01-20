# -*- coding: utf-8 -*-
# @Date : 2022/1/20 15:18
# @Author : zhong
# @File :post2SCADA.py
# @Version : 1.0
# @Project : issue_pool#2263 中电科项目，通过modbus TCP协议和客户SCADA进行产线交互
import json
import sys
import time

import requests
from requests import RequestException
from requests.exceptions import ConnectTimeout, HTTPError, ConnectionError
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule
sys.path.append("syspy")


"""
####BEGIN DEFAULT ARGS####
{
    "postURL":{
        "value":"http://192.168.8.222:8088/callTerminal",
        "type":"string"
    },
    "postData":{
        "value":{
            "id": "Terminal-01",
            "type": "write",
            "value": 666
        },
        "type":"json"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super().__init__()
        self.post_url = None
        self.post_data = None
        self.status = MoveStatus.NONE
        self.state = dict()
        self.init = True
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.post_url = args.get("postURL", None)
            self.post_data = args.get("postData", None)
        r.setNotice(f"post_url: {self.post_url}, post_data: {self.post_data}")
        if time.time() - self.start_time > 10:
            r.setError(f"time out: 10s")
            self.status = MoveStatus.FAILED
        if self.post_url and self.post_data:
            try:
                res = requests.post(url=self.post_url, json=self.post_data, timeout=3.0)
                res.encoding = 'utf-8'
                res_data = json.loads(res.text)   # 获取响应数据
                self.state["response"] = res_data
                if res_data.get("status", -1) == -1:
                    r.setError(f"Post Failed. Response: {res_data}")
                    self.status = MoveStatus.FAILED
                elif res.status_code == 200:
                    r.setNotice(f"Post Success")
                    self.status = MoveStatus.FINISHED
            except HTTPError:
                print(f"Invalid HTTP response")
            except ConnectTimeout:
                print('connect timeout')
            except ConnectionError:
                print('Connection refused')
            except Exception as e:
                print(f'unknown exception: {e}')
            else:
                pass
        else:
            r.setError(f"args error: {args}")
            self.status = MoveStatus.FAILED

        self.state["script args"] = args
        r.setInfo(json.dumps(self.state))
        return self.status


if __name__ == '__main__':
    r = SimModule()
    read_args = {
        "postURL": "http://192.168.8.222:8088/callTerminal",
        "postData": {
            "id": "Terminal-01",
            "type": "read"
        }
    }
    write_args = {
        "postURL": "http://192.168.8.222:8088/callTerminal",
        "postData": {
            "id": "Terminal-01",
            "type": "write",
            "value": 456
        }
    }
    m = Module(r, write_args)
    m.run(r, write_args)
