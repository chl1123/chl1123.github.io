# -*- coding: utf-8 -*-
# @Request :
# @Version: 1.0
# @project:【现场】【成都先进功率】现场需要调用脚本反馈上位机任务状态
# @coding:https://seer-group.coding.net/p/order_issue_pool/requirements/issues/4819/detail
import json

import requests

from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer, Pos2Base
from syspy.robot import ModuleTool
"""
####BEGIN DEFAULT ARGS####
{
    "id": {
        "value": "",
        "default_value": "123",
        "tips": "tips",
        "type": "string"
    }
}

####END DEFAULT ARGS####
"""
class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super().__init__()
        self.task_id = ""
        self.init = True
        self.state = {}
        self.url = f'http://10.10.10.200:8080/Car/NavigateIsOk?taskid='

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))

        # 发送POST请求
        self.task_id = args.get("id")  # 获取动态参数 taskid
        response = requests.post(self.url+self.task_id)

        if response.status_code == 200:
            # 请求成功，返回完成状态
            self.status = MoveStatus.FINISHED
            self.state = {
                "reason":response.reason,
                "status":self.status,
                "status_code":response.status_code
            }
        r.setInfo(json.dumps(self.state))
    def cancel(self, r: SimModule):
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.logInfo("task suspend")
        self.status = MoveStatus.SUSPENDED




if __name__ == '__main__':
    r = SimModule()
    m = Module(r,{})
    m.run(r,{"id":"123"})