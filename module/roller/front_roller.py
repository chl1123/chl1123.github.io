# -*- coding: utf-8 -*-
# @Time : 2022/5/30  17:00
# @Author : qian, zhong
# @Version : V1.1-20220530
# @Project SaiMo_roller
import json
import time
import requests
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

""" 
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "RollerPreLoad",
        "default_value": ["RollerLoad", "RollerUnload", "RollerStop", "RollerPreLoad", "SafeMoveCheck", "BlockUp", "BlockDown"],
        "tips": "辊筒操作选项: 上货、卸货、停转、预转、安全检查",
        "type": "complex"
    },
    "direction": {
        "value": "Right",
        "default_value": ["Left", "Right"],
        "tips": "辊筒运转方向",
        "type": "complex"
    },
    "postURL":{
        "value":"http://192.168.125.201:8088/callTerminal",
        "tips": "终端设备地址",
        "type":"string"
    },
    "postData":{
        "value":{
            "reach": {
                "address": 34,
                "functionCode": 6,
                "id": "Upper_Computer",
                "type": "writeAddr",
                "value": 1
            },
            "action":{
                "address": 35,
                "functionCode": 3,
                "id": "Upper_Computer",
                "type": "readAddr"
            },
            "finish":{
                "address": 36,
                "functionCode": 6,
                "id": "Upper_Computer",
                "type": "writeAddr",
                "value": 1
            },
            "reset":[
                {
                    "address": 34,
                    "functionCode": 6,
                    "id": "Upper_Computer",
                    "type": "writeAddr",
                    "value": 0
                },
                {
                    "address": 36,
                    "functionCode": 6,
                    "id": "Upper_Computer",
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
        self.right_reach_di = p.loadParam("di1", type="int", default=6, maxValue=100, minValue=0,
                                          comment="Right di")  # inside  # 右物料到位检测
        self.mid_reach_di = p.loadParam("di2", type="int", default=2, maxValue=100, minValue=0,
                                        comment="mid di")  # inside  # 中间物料到位检测
        self.left_reach_di = p.loadParam("di3", type="int", default=5, maxValue=100, minValue=0,
                                         comment="Left di")  # inside  # 左物料到位检测
        self.left_block_up_di = p.loadParam("di4", type="int", default=7, maxValue=100, minValue=0,
                                            comment="Left block up di")  # inside  # 挡板左上
        self.left_block_down_di = p.loadParam("di5", type="int", default=0, maxValue=100, minValue=0,
                                              comment="Left block down di")  # inside  # 挡板左下
        self.right_block_up_di = p.loadParam("di6", type="int", default=4, maxValue=100, minValue=0,
                                             comment="Right block up di")  # inside  # 挡板右上
        self.right_block_down_di = p.loadParam("di7", type="int", default=8, maxValue=100, minValue=0,
                                               comment="Right block down di")  # inside  # 挡板右下

        self.left_block_motor = p.loadParam("left_block_motor", type="str", default="left_block_motor",
                                            comment="左侧挡板电机")
        self.right_block_motor = p.loadParam("right_block_motor", type="str", default="right_block_motor",
                                             comment="右侧挡板电机")
        self.direction_do = p.loadParam("direction_do", type="int", default=23, maxValue=100, minValue=0,
                                        comment="滚筒换向DO")
        self.roller_do = p.loadParam("roller_do", type="int", default=22, maxValue=100, minValue=0, comment="滚筒使能DO")
        self.right_block_up_do = p.loadParam("right_block_up_do", type="int", default=18, maxValue=100, minValue=0,
                                             comment="右侧挡板Up-DO")
        self.right_block_down_do = p.loadParam("right_block_down_do", type="int", default=19, maxValue=100, minValue=0,
                                               comment="右侧挡板down-DO")
        self.left_block_up_do = p.loadParam("left_block_up_do", type="int", default=20, maxValue=100, minValue=0,
                                            comment="左侧挡板Up-DO")
        self.left_block_down_do = p.loadParam("left_block_down_do", type="int", default=21, maxValue=100, minValue=0,
                                              comment="左侧挡板down-DO")
        self.over_time = p.loadParam("over_time", type="float", default=120.0, maxValue=3600.0, minValue=0.0, unit="s",
                                     comment="超时时间")
        self.init = True
        self.start_time = time.time()
        self.operation_status = MoveStatus.NONE
        self.status = MoveStatus.NONE
        self.operation = ""
        self.operation_list = ["RollerLoad", "RollerUnload", "RollerStop", "RollerPreLoad", "SafeMoveCheck"]
        self.direction_list = ["left", "right"]
        self.direction = ""
        self.speed = ""
        self.task_list = []
        self.task_id = 0
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
        self.wait_time = None
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        self.operation_status = MoveStatus.RUNNING
        dt = time.time() - self.start_time
        if dt > self.over_time:
            self.roller_stop(r)
            self.status = MoveStatus.FAILED
            r.setError("Roller running is over time!")
            return self.status

        if self.init:
            self.init = False
            # 获取辊筒操作参数
            self.operation = args.get("operation", None)
            self.direction = args.get("direction", None)
            # 获取与设备通信的参数
            self.terminal_url = args.get('postURL', None)
            self.reach_data = args.get('postData', dict()).get('reach', None)
            self.action_data = args.get('postData', dict()).get('action', None)
            self.finish_data = args.get('postData', dict()).get('finish', None)
            self.reset_data = args.get('postData', dict()).get('reset', None)

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

        # 辊筒运转
        if self.operation == "SafeMoveCheck":
            self.safe_move_check(r)
        elif self.operation == "BlockUp":
            self.left_block_up(r)
            self.right_block_up(r)
            if check_DI(r, self.left_block_up_di) and check_DI(r, self.right_block_up_di):
                self.operation_status = MoveStatus.FINISHED
        elif self.operation == "BlockDown":
            self.left_block_down(r)
            self.right_block_down(r)
            if check_DI(r, self.left_block_down_di) and check_DI(r, self.right_block_down_di):
                self.operation_status = MoveStatus.FINISHED
        elif self.operation == "RollerStop":
            self.roller_stop(r)
            self.operation_status = MoveStatus.FINISHED
        else:
            self.roller_run(r, self.operation, self.direction)
        if self.status is not MoveStatus.FAILED:
            r.publishSpeed()

        # 给设备写完成信号
        if not self.finish_flag and self.operation_status == MoveStatus.FINISHED and self.finish_data:
            finish_res = self.call_terminal(r, self.terminal_url, self.finish_data)
            if finish_res and finish_res.get('status', -1) == 1:
                self.finish_flag = True

        # 将到位信号与完成信号清零
        if self.finish_flag and not self.reset_flag:  # and self.reset_data:
            # reset_res0 = self.call_terminal(r, self.terminal_url, self.reset_data[0])
            # reset_res1 = self.call_terminal(r, self.terminal_url, self.reset_data[1])
            # if reset_res0 and reset_res1 and reset_res0.get('status', -1) == 1 and reset_res1.get('status', -1) == 1:
            # self.finish_flag = True
            self.status = MoveStatus.FINISHED

        # 不需要交互
        if not bool(self.terminal_url):
            self.status = self.operation_status

        flags = {"reach": self.reach_flag, "action": self.action_flag, "finish": self.finish_flag,
                 "reset": self.reset_flag}
        di_status = {"di0": check_DI(r, 0), "di7": check_DI(r, 7), "di4": check_DI(r, 4), "di8": check_DI(r, 8)}
        self.state["operation_status"] = self.operation_status
        self.state["status"] = self.status
        self.state["args"] = args
        self.state["script version"] = "V1.1 - 20220530"
        self.state["DI"] = di_status
        self.state["flags"] = flags
        self.state["running count"] = r.getCount()
        r.setInfo(json.dumps(self.state))
        r.logDebug(json.dumps(self.state))
        return self.status

    def suspend(self, r: SimModule):
        """导航任务暂停"""
        self.start_time = time.time()
        r.logInfo("script suspend")
        self.roller_stop(r)
        self.status = MoveStatus.SUSPENDED

    def cancel(self, r: SimModule):
        """导航任务取消"""
        self.roller_stop(r)      # 停止辊筒运转
        if self.terminal_url and self.reset_data:     # 复位设备信号
            self.call_terminal(r, self.terminal_url, self.reset_data[0])
            self.call_terminal(r, self.terminal_url, self.reset_data[1])
        r.logInfo(f"terminal url:{self.terminal_url}, reset data: {self.reset_data}")
        self.status = MoveStatus.NONE

    # 与终端设备交互
    def call_terminal(self, r, url, data):
        try:
            res = requests.post(url, json=data, timeout=5.0)
        except Exception as e:
            r.logInfo(f"post failed!!! url: {url}, data: {data}, error: {e}")
            return False
        else:
            self.state["response"] = res.text
            if res.status_code == 200:
                return json.loads(res.text)
            else:
                return False

    def left_block_up(self, r):
        r.setMotorSpeed(self.left_block_motor, 1, self.left_block_up_di)
        r.setWarning(f"left_block_up: {r.getCount()}")

    def left_block_down(self, r):
        r.setMotorSpeed(self.left_block_motor, -1, self.left_block_down_di)
        r.setWarning(f"left_block_down: {r.getCount()}")

    def right_block_up(self, r):
        r.setMotorSpeed(self.right_block_motor, 1, self.right_block_up_di)
        r.setWarning(f"right_block_up: {r.getCount()}")

    def right_block_down(self, r):
        r.setMotorSpeed(self.right_block_motor, -1, self.right_block_down_di)
        r.setWarning(f"right_block_down: {r.getCount()}")

    def roller_run(self, r, opt, direction):
        if opt == "RollerPreLoad" and direction == "Right":  # 右上料+ # 辊筒预转
            if self.has_goods(r):  # 辊筒上有物料
                r.setError(f"there are already materials on the roller!")
                self.operation_status = MoveStatus.FAILED
            else:
                self.right_block_down(r)
                self.left_block_up(r)
                r.setDO(self.roller_do, True)
                r.setDO(self.direction_do, False)
                if check_DI(r, self.right_block_down_di) and check_DI(r, self.left_block_up_di):
                    self.operation_status = MoveStatus.FINISHED

        elif opt == "RollerPreLoad" and direction == "Left":  # 左上料+ # 辊筒预转
            if self.has_goods(r):  # 辊筒上有物料
                r.setError(f"there are already materials on the roller!")
                self.operation_status = MoveStatus.FAILED
            else:
                self.left_block_down(r)
                self.right_block_up(r)
                r.setDO(self.roller_do, False)
                r.setDO(self.direction_do, True)
                if check_DI(r, self.left_block_down_di) and check_DI(r, self.right_block_up_di):
                    self.operation_status = MoveStatus.FINISHED

        elif opt == "RollerLoad" and direction == "Left":  # 左上料
            if not check_DI(r, self.left_reach_di) and not check_DI(r, self.left_block_down_di):
                self.left_block_down(r)
            if check_DI(r, self.left_block_down_di):  # and not check_DI(r, self.left_reach_di) :
                r.setDO(self.roller_do, False)
                r.setDO(self.direction_do, True)
            if check_DI(r, self.mid_reach_di) and (
                    not check_DI(r, self.left_reach_di) or check_DI(r, self.right_reach_di)):
                self.roller_stop(r)
                self.left_block_up(r)
                if check_DI(r, self.left_block_up_di) and check_DI(r, self.mid_reach_di):
                    self.operation_status = MoveStatus.FINISHED

        elif opt == "RollerLoad" and direction == "Right":  # 右上料
            if not check_DI(r, self.right_block_down_di) and not check_DI(r, self.right_reach_di):
                self.right_block_down(r)
            if check_DI(r, self.right_block_down_di):  # and not check_DI(r, self.right_reach_di):
                r.setDO(self.roller_do, True)
                r.setDO(self.direction_do, False)
            if check_DI(r, self.mid_reach_di) and (
                    not check_DI(r, self.right_reach_di) or check_DI(r, self.left_reach_di)):
                self.roller_stop(r)
                self.right_block_up(r)
                if check_DI(r, self.right_block_up_di) and check_DI(r, self.mid_reach_di):
                    self.operation_status = MoveStatus.FINISHED

        elif opt == "RollerUnload" and direction == "Left":  # 左下料
            if not check_DI(r, self.left_block_down_di) and self.has_goods(r):
                self.left_block_down(r)
                r.setNotice(f"left down")
            elif check_DI(r, self.left_block_down_di) and self.has_goods(r):
                r.setDO(self.roller_do, True)
                r.setDO(self.direction_do, False)
            elif not self.has_goods(r):
                self.roller_stop(r)
                self.safe_move_check(r)
                self.operation_status = MoveStatus.FINISHED
            else:
                r.setError(f"DI status error, please check")

        elif opt == "RollerUnload" and direction == "Right":  # 右下料
            self.operation_status = MoveStatus.RUNNING
            if not check_DI(r, self.right_block_down_di) and self.has_goods(r):
                self.right_block_down(r)
            elif check_DI(r, self.right_block_down_di) and self.has_goods(r):
                r.setDO(self.roller_do, False)
                r.setDO(self.direction_do, True)
            elif not self.has_goods(r):
                self.roller_stop(r)
                self.safe_move_check(r)
                self.operation_status = MoveStatus.FINISHED
            else:
                r.setError(f"DI status error, please check")

    def roller_stop(self, r):
        r.setNotice("roller stop!")
        r.setDO(self.roller_do, False)
        r.setDO(self.direction_do, False)

    def has_goods(self, r):
        """检查辊筒上是否有物料"""
        if check_DI(r, self.right_reach_di) or check_DI(r, self.mid_reach_di) or check_DI(r, self.left_reach_di):
            return True
        else:
            return False

    def safe_move_check(self, r):
        """机器行走前安全检查"""
        self.operation_status = MoveStatus.RUNNING
        self.left_block_up(r)
        self.right_block_up(r)
        self.roller_stop(r)
        if check_DI(r, self.left_block_up_di) and check_DI(r, self.right_block_up_di):
            self.operation_status = MoveStatus.FINISHED


def check_DI(r: SimModule, di: int):
    """
    检测单个DI状态信息
    :param r: SimModule类对象
    :param di: 需要检测的DI
    :return: 返回指定DI的状态，若DI不存在返回False
    """
    DI = r.Di()
    nodes = DI.get('node', list())
    for node in nodes:
        if node['id'] == di:
            return node['status']
    return False


def check_DO(r: SimModule, do: int):
    """
    检测单个DO状态信息
    :param r: SimModule类对象
    :param do: 需要检测的DO
    :return: 返回指定DO的状态，若DO不存在返回False
    """
    DO = r.Do()
    nodes = DO.get('node', list())
    for node in nodes:
        if node['id'] == do:
            return node['status']
    return False
