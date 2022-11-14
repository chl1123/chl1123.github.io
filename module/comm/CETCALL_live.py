# cetc
# -*- coding: utf-8 -*-
# @Time : 2022/3/28 PM 19:43
# @Author : Xingguang, zhong
# @Version : 1.2
# 在原脚本cetc.py 基础上增加通讯流程，以及任务完成后自动复位流程

import json
import time

import requests

from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

"""
operation(动作)说明: 
    "Jack":表示顶升先动，顶升到指定高度，推送电机再动作到指定位置
    "Home":设备回到初始位置
"""

""" 
####BEGIN DEFAULT ARGS####

{
    "operation": {
        "value": "",
        "default_value": ["Jack", "Home"],
        "type": "complex"
    },
    "jack_height1": {
        "value": "",
        "default_value": "",
        "type": "double"
    },
    "jack_height2": {
        "value": "",
        "default_value": "",
        "type": "double"
    },
    "postURL":{
        "value":"http://172.16.1.201:8088/callTerminal",
        "tips": "终端设备地址",
        "type":"string"
    },
    "postData":{
        "value":{
            "reach": {
                "address": 905,
                "functionCode": 6,
                "id": "TK02",
                "type": "writeAddr",
                "value": 1
            },
            "action":{
                "address": 803,
                "functionCode": 3,
                "id": "TK02",
                "type": "readAddr"
            },
            "finish":{
                "address": 906,
                "functionCode": 6,
                "id": "TK02",
                "type": "writeAddr",
                "value": 1
            },
            "reset":[
                {
                    "address": 905,
                    "functionCode": 6,
                    "id": "TK02",
                    "type": "writeAddr",
                    "value": 0
                },
                {
                    "address": 906,
                    "functionCode": 6,
                    "id": "TK02",
                    "type": "writeAddr",
                    "value": 0
                }
            ]
        },
        "tips": "与终端设备交互数据",
        "type":"json"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.jackMotor = p.loadParam(
            "jack_motor", type="str", default="jack", comment="motor name"
        )
        self.pushMotor = p.loadParam(
            "push_motor", type="str", default="push", comment="motor name"
        )
        self.operation = ""
        self.jack_height1 = ""
        self.jack_height2 = ""
        self.operation_list = ["Jack", "Home"]
        self.task_list = []
        self.task_id = 0
        self.start_time = time.time()
        self.over_time = p.loadParam(
            "over_time",
            type="float",
            default=240.0,
            maxValue=3600.0,
            minValue=0.0,
            unit="s",
            comment="time",
        )
        self.init = True
        self.operation_status = MoveStatus.NONE
        self.state = dict()

        self.terminal_url = None
        self.reach_data = None
        self.reach_flag = False
        self.action_data = None
        self.action_flag = False
        self.finish_data = None
        self.finish_flag = False
        self.reset_data = None
        self.reset_flag = False
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        dt = time.time() - self.start_time
        if dt > self.over_time:
            self.status = MoveStatus.FAILED
            r.setError("all operation is over Time")
            return self.status
        self.status = MoveStatus.RUNNING
        self.state = dict()
        if self.init:
            self.init = False
            if "jack_height1" not in args or "jack_height2" not in args or "operation" not in args or "postURL" not in args:
                r.setError("user args define error {}".format(json.dumps(args)))
                self.status = MoveStatus.FAILED
            else:
                self.jack_height1 = args["jack_height1"]
                self.jack_height2 = args["jack_height2"]
                self.operation = args["operation"]

            # 获取与设备通信的参数
            self.terminal_url = args.get('postURL', False)
            self.reach_data = args.get('postData', dict()).get('reach', False)
            self.action_data = args.get('postData', dict()).get('action', False)
            self.finish_data = args.get('postData', dict()).get('finish', False)
            self.reset_data = args.get('postData', dict()).get('reset', False)

        if self.status is MoveStatus.FAILED:
            return self.status

        # 给设备写到位信号
        if not self.reach_flag and self.reach_data:
            reach_res = self.call_terminal(r, self.terminal_url, self.reach_data)
            if reach_res and reach_res.get('status', -1) == 1:
                self.reach_flag = True
            else:
                return MoveStatus.RUNNING
        # 读设备允许动作信号
        if self.reach_flag and not self.action_flag and self.action_data:
            action_res = self.call_terminal(r, self.terminal_url, self.action_data)
            if action_res and action_res.get('status', -1) == 1:
                self.action_flag = True
            else:
                return MoveStatus.RUNNING

        if self.jack_height1 == "" or not self.is_number(self.jack_height1):
            r.setError("please enter the correct parameters!")
            self.status = MoveStatus.FAILED
        elif self.jack_height2 == "" or not self.is_number(self.jack_height2):
            r.setError("please enter the correct parameters!")
            self.status = MoveStatus.FAILED
        elif self.operation not in self.operation_list:
            r.setError("operation doesn't support!")
            self.status = MoveStatus.FAILED
        else:
            self.jack(r, self.jack_height1, self.jack_height2, self.operation)
        if self.status is not MoveStatus.FAILED:
            if not r.publishSpeed():
                self.status = MoveStatus.FAILED

        # 给设备写完成信号
        if not self.finish_flag and self.operation_status == 3 and self.finish_data:
            finish_res = self.call_terminal(r, self.terminal_url, self.finish_data)
            if finish_res and finish_res.get('status', -1) == 1:
                self.finish_flag = True

        # 将到位信号与完成信号清零
        if self.finish_flag and not self.reset_flag and self.reset_data:
            reset_res0 = self.call_terminal(r, self.terminal_url, self.reset_data[0])
            reset_res1 = self.call_terminal(r, self.terminal_url, self.reset_data[1])
            if reset_res0 and reset_res1 and reset_res0.get('status', -1) == 1 and reset_res1.get('status', -1) == 1:
                self.finish_flag = True
                self.status = MoveStatus.FINISHED

        if self.terminal_url == "" or not bool(self.terminal_url):
            self.status = self.operation_status

        call_flag = {"reach": self.reach_flag, "action": self.action_flag, "finish": self.finish_flag, "reset": self.reset_flag}
        self.state["operation_status"] = self.operation_status
        self.state["status"] = self.status
        self.state["args"] = args
        self.state["call_flag"] = call_flag
        str_state = json.dumps(self.state)
        r.setInfo(str_state)
        r.logDebug(str_state)
        return self.status

    # 与终端设备交互
    @staticmethod
    def call_terminal(r, url, data):
        try:
            res = requests.post(url, json=data, timeout=30)
        except Exception as e:
            r.logInfo(f"post failed!!! url: {url}, data: {data}, error: {e}")
            return False
        else:
            try:
                r.logInfo(f"url: {url}, status_code: {res.status_code}, resp: {res.text}")
            except Exception as e:
                r.logInfo(f"exception: {e}")
            if res.status_code == 200:
                return res.json()
            else:
                return False

    def runTakList(self, r):
        """����TaskList"""
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(r, self)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED
        self.state["task_id"] = self.task_id
        self.state["task_list_size"] = len(self.task_list)

    def jack(self, r, jack_height1, jack_height2, operation):
        self.operation = operation
        self.jack_height1 = jack_height1
        self.jack_height2 = jack_height2
        if self.operation == "Jack":
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [
                    Motor(jack_height1, "load1"),
                    Motor(jack_height1, "push1"),
                    Motor(jack_height2, "load2"),
                    Motor(0, 'Home')
                ]
                self.task_id = 0
            else:
                self.runTakList(r)
        elif self.operation == "Home":
            if self.operation_status == MoveStatus.NONE:
                self.operation_status = MoveStatus.RUNNING
                self.task_list = [Motor(0, operation)]
                self.task_id = 0
            else:
                self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id

    # 判断一个字符串是否是一串数字
    def is_number(self, x):
        try:
            float(x)
            return True
        except ValueError:
            pass
        try:
            import unicodedata

            unicodedata.numeric(x)
            return True
        except (TypeError, ValueError):
            pass
        return False


class Motor:
    def __init__(self, jack_height, action):
        """
        LineMotorPosition
        Args:
            jack_height(String):指定顶升高度，注意发送的距离如果大于限位距离，会报错（最大1.1m)
            pushMotor(string):货叉电机
            operation(string):动作名称
        """
        self.status = MoveStatus.NONE
        self.jackMotor = "jack"
        self.pushMotor = "push"
        self.jack_height = jack_height + 0
        self.action = action
        self.reachDI = 2
        self.push_motor_position = None
        self.trigger_flag = True

    def reset(self, r: SimModule, roller):
        r.resetMotor(self.jackMotor)
        r.resetMotor(self.pushMotor)
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, roller):
        self.status = MoveStatus.RUNNING

        if self.action == "load1":
            r.setMotorPosition(self.jackMotor, self.jack_height, 0.08, -1)
            if r.isMotorPositionReached(self.jackMotor, self.jack_height, -1):
                r.setMotorSpeed(self.pushMotor, 0.03, self.reachDI)
                if r.isMotorReached(self.pushMotor):
                    self.status = MoveStatus.FINISHED
        elif self.action == "push1":
            if self.trigger_flag:
                self.trigger_flag = False
                if self.get_motor_pos(r, self.pushMotor) is not False:
                    self.push_motor_position = self.get_motor_pos(r, self.pushMotor) - 0.008
            r.setMotorPosition(self.pushMotor, self.push_motor_position, 0.05, -1)
            if r.isMotorPositionReached(self.pushMotor, self.push_motor_position, -1):
                self.status = MoveStatus.FINISHED
        elif self.action == "load2":
            r.setMotorPosition(self.jackMotor, self.jack_height, 0.08, -1)
            if r.isMotorPositionReached(self.jackMotor, self.jack_height, -1):
                r.setMotorPosition(self.pushMotor, 0, 0.03, -1)
                if r.isMotorPositionReached(self.pushMotor, 0, -1):
                    self.status = MoveStatus.FINISHED
        elif self.action == "Home":
            r.setMotorPosition(self.pushMotor, 0, 0.05, -1)
            if r.isMotorPositionReached(self.pushMotor, 0, -1):
                r.setMotorPosition(self.jackMotor, 0, 0.05, -1)
                if r.isMotorPositionReached(self.jackMotor, 0, -1):
                    self.status = MoveStatus.FINISHED

        state = dict()
        state["action"] = self.action
        state["status"] = self.status

    # 判断一个字符串是否是一串数字
    @staticmethod
    def is_number(self, x):
        try:
            float(x)
            return True
        except ValueError:
            pass
        try:
            import unicodedata

            unicodedata.numeric(x)
            return True
        except (TypeError, ValueError):
            pass
        return False

    # 获取电机位置
    @staticmethod
    def get_motor_pos(r: SimModule, motor_name: str):
        motors = r.odo().get("motor_info", [])
        motor_pos = False
        for m in motors:
            if m['motor_name'] == motor_name:
                motor_pos = m.get('position', False)
        return motor_pos


if __name__ == '__main__':
    args = {}
    r = SimModule()
    m = Module(r, args)
