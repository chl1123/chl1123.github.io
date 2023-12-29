# -*- coding: utf-8 -*-
# @Time : 2022/4/5
# @Author : CXN
# @project ：
# @object ：
# @coding ：
# @File :模板.py
# @Version: 1.0
import json
import math
import struct
import sys
import time
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/genetic/syspy/battery/')

sys.path.append("../syspy")
from syspy import goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
from syspy.robot import ModuleTool, Motor, MotorType, Robot, GoodsManger

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "zero",
        "default_value":["load","unload"],
        "tips": "机构动作选项",
        "type": "complex"        
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.delay_time = 0.0
        self.task_list = []
        self.task_id = 0
        self.operation_status = MoveStatus.NONE
        p = ParamServer(__file__)
        self.timeout = p.loadParam("timeout", type="int", default=120, maxValue=300, minValue=0, unit="s",comment=" 运行超时时间")
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()
        self.start_time = time.time()
        self.goods_id = ""
        self.operation = None
        self.operations= self.init_operations()
        self.handle = None
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            """==== 输入参数初始化函数 ==== """
            self.init_args(r,args)
            if not self.handle:
                """==== 初始化操作，确定任务内容 ==== """
                self.handle = self.get_handle(r, args)
                if not self.handle:
                    r.setError(f"找不到输入的操作:{self.operation}，检检查脚本输入参数。")
                    self.status = MoveStatus.FAILED
                    return self.status
            self.init = False
        if not self.init and self.status != MoveStatus.FINISHED:
            """==== 初始化完成，开始运行任务 ==== """
            self.handle_robot(r)
        self.status = self.operation_status
        """==== 循环结束，上报数据（打印） ==== """
        self.report_data(r)
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def init_args(self,r:SimModule,args:dict):
        """==== 初始化操作，处理脚本的输入参数 按需取用 ==== """
        self.operation = args.get("operation", None)
        self.delay_time = args.get("delay", None)
        self.report_info["args"] = args
        """==== 初始化操作，获取导航任务参数，按需取用 ==== """
        self.get_move_task_params(r)  # 获取任务的货物 goodsId

    def handle_robot(self, r: SimModule):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
        else:
            self.run_tak_list(r)

    def run_tak_list(self, r):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(r,self)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED

    def get_handle(self, r: SimModule, args: dict):
        # 这里的意思是，获取操作的内容，如果 脚本的输入参数有 operation，则 operation 优先，
        """
        "finger": {
            "value": 0,
            "tips": "1: open, 0: close",
            "type": "int"
        },
        "operation": {
            "value": "zero",
            "default_value": ["load", "unload", "change", "zero", "take", "put"],
            "tips": "机构动作选项",
            "type": "complex"
        }
        """
        # 比如，输入 operation ，不输入 finger，则 operation生效
        # 比如，输入 operation ，输入 finger，则 operation生效
        # 比如，不输入 operation ，输入 finger，则 finger 生效
        handler = self.operations.get(self.operation or next((op for op in args if op in self.operations), None))
        if handler:
            handler(r)
        return handler

    def check_timeout(self,r:SimModule):
        if time.time() - self.start_time > self.timeout:
            r.setError(f"running time out")
            self.status = MoveStatus.FAILED

    def init_operations(self):
        return {
            "load": self.load,  # 取货
            "unload": self.unload,  # 放货
            "motorPos": self.motorPos,
            "delay": self.delay,  # 延时
        }

    def motorPos(self,r:SimModule):
        self.task_list = [MotorPos("lift",0.1)]

    def delay(self,r:SimModule):
        self.task_list = [DelayTime(self.delay_time)]

    def load(self,r:SimModule):
        pass

    def unload(self,r):
        pass

    def cancel(self, r: SimModule):
        r.resetRec()
        self.status = MoveStatus.NONE

    def get_move_task_params(self, r):
        """
        获取moveTask参数 goods_id
        """
        move_task = r.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsId':
                self.goods_id = p['string_value']


    def report_data(self, r):
        self.report_info['getCount'] = r.getCount()
        self.report_info['task_len'] = len(self.task_list)
        self.report_info['task_id'] = self.task_id



class TpModule:
    """所有新增类需要继承的类"""
    def __init__(self):
        self.status = MoveStatus.NONE
        self.start_time = time.time()

    def reset(self, r: SimModule,m:Module):
        self.status = MoveStatus.RUNNING
        self.start_time = time.time()


class MotorCalib(TpModule):
    """驱动器标零"""
    def __init__(self,motor_name):
        super().__init__()
        self.motor_name = motor_name
        self.is_calib = None
        self.is_stop = []
        self.is_setMotorCalib = False
        self.state = {}

    def run(self, r: SimModule,m:Module):
        odo_data = r.odo()
        if odo_data.get("motor_info", None):
            motor_info = odo_data["motor_info"]
            self.is_stop = []
            for m_f in motor_info:
                if m_f.get("motor_name", None):
                    if m_f["motor_name"] == self.motor_name:
                        self.is_calib = m_f.get("calib", None)
                self.is_stop.append(m_f.get("stop", None))
        if self.is_calib:
            self.status = MoveStatus.FINISHED
        else:
            if all(self.is_stop):
                r.setMotorCalib(self.motor_name)
                self.is_setMotorCalib = True
        if self.is_setMotorCalib and all(self.is_stop):
            self.status = MoveStatus.FINISHED
        self.state["is_calib"] = self.is_calib
        self.state["is_stop"] = self.is_stop
        self.state["is_setMotorCalib"] = self.is_setMotorCalib
        self.state["status"] = self.status
        self.state["taskid"] = m.task_id

        m.report_info[f"MotorCalib_{self.motor_name}"] = self.state

class OpenDO(TpModule):
    """打开DO"""
    def __init__(self, task: list):
        super().__init__()
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            for i, t in enumerate(self.task):
                r.setDO(t, True)
                self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        m.report_info["OpenDO"] = task_state


class CloseDO(TpModule):
    """关闭DO"""
    def __init__(self, task: list):
        super().__init__()
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            for i, t in enumerate(self.task):
                r.setDO(t, False)
                self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        m.report_info["CloseDO"] = task_state


class WaitDI(TpModule):
    """等待DI，输入是【1,2】，False或者 True"""
    def __init__(self, task: list, mode: bool):
        super().__init__()
        self.status = MoveStatus.NONE
        self.task = task
        self.opt = [False] * len(self.task)
        self.mode = mode

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        task_state = dict()
        if self.status != MoveStatus.FINISHED:
            if self.mode:
                for i, t in enumerate(self.task):
                    if ModuleTool.check_DI(r, t):
                        self.opt[i] = True
            else:
                for i, t in enumerate(self.task):
                    if not ModuleTool.check_DI(r, t):
                        self.opt[i] = True
        if all(self.opt):
            self.status = MoveStatus.FINISHED
        task_state["task"] = self.task
        task_state["status"] = self.status
        m.report_info["WaitDI"] = task_state


class DelayTime(TpModule):
    """延时指定时间"""
    def __init__(self, time_delay):
        super().__init__()
        self.status = MoveStatus.NONE
        self.time_delay = time_delay
        self.start = time.time()
        self.init = True

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.start = time.time()
            self.init = False
        task_state = dict()
        if not self.init and time.time() - self.start > self.time_delay:
            self.status = MoveStatus.FINISHED
        task_state["time"] = self.time_delay
        task_state["start"] = self.start
        task_state["status"] = self.status
        task_state["time"] = time.time()
        m.report_info["DelayTime"] = task_state


class MotorPos(TpModule):
    """
    控制电机到达某个位置
    """
    def __init__(self, r,name,position = None,speed= 1.0):
        super().__init__()
        self.name = name
        self.position = position
        self.speed = speed
        self.init = True
        self.robot = Robot(r)
        self.motor = Motor(r, MotorType.LINEAR_MOTOR, name, -1)

    def run(self, r: SimModule, m: Module):
        task_state = dict()
        if self.init:
            self.init = False
        if not self.init and self.status != MoveStatus.FINISHED:
            if self.robot.stretch(self.motor, self.position, self.speed):
                self.status = MoveStatus.FINISHED
        r.publishSpeed()
        task_state["status"] = self.status
        task_state["position"] = self.position
        task_state["taskid"] = m.task_id
        m.report_info[f"MotorPos_{self.position}"] = task_state

if __name__ == '__main__':
    pass
