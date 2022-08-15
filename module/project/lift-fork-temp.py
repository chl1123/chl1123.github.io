# -*- coding: utf-8 -*-
# @Time : 2022/8/11
# @Author : qian, qiangsheng, zhong
# @File : lift-fork-temp.py
# @Project : 中电科8寸
# @Update：栈式存取，1号作为栈顶，只从1号工位取放货；增加库位 container 管理

import time
import json
import requests
import sys
sys.path.append("syspy")
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer, Pos2Base
from robot import ModuleTool


"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "zero",
        "default_value":["zero","load","unload","lift","stretch","shift"],
        "tips": "操作",
        "type": "complex"
    },
    "stretchLength": {
        "value": 0.5,
        "tips": "货叉伸出长度",
        "type": "float",
        "unit": "m"
    },
    "liftHeight": {
        "value": 0.5,
        "tips": "货叉升降高度",
        "type": "float",
        "unit": "m"
    },
    "shiftWidth": {
        "value": 0.5,
        "tips": "货叉平移距离",
        "type": "float",
        "unit": "m"
    },
    "forkLiftUp": {
        "value": 0.05,
        "tips": "货叉载物升降高度",
        "type": "float",
        "unit": "m"
    },
    "position": {
        "value": "P1",
        "default_value":["P1","P2"],
        "tips": "托盘存放位置",
        "type": "string"
    },
    "recFile": {
        "value": "",
        "tips": "识别文件",
        "type": "string"
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
        super().__init__()
        p = ParamServer(__file__)
        self.max_lift_height = p.loadParam("max_lift_height", type="float", default=0.7, comment="最大升降高度")
        self.max_stretch_length = p.loadParam("max_stretch_length", type="float", default=0.5, comment="最大伸出长度")
        self.max_shift_width = p.loadParam("max_shift_width", type="float", default=0.72, comment="最大平移宽度")
        self.lift_zero = p.loadParam("fork_lift_zero", type="float", default=0.000, comment="货叉升降零位")
        self.stretch_zero = p.loadParam("fork_stretch_zero", type="float", default=0.000, comment="货叉伸缩零位")
        self.shift_zero = p.loadParam("fork_shift_zero", type="float", default=0.000, comment="货叉平移零位")
        self.P1_shift_pos = p.loadParam("P1_shift_Pos", type="float", default=0.055, comment="P1工位叉取位")
        self.P2_shift_pos = p.loadParam("P2_shift_Pos", type="float", default=0.491, comment="P2工位叉取位")
        self.lift_up = p.loadParam("lift_up_Height", type="float", default=0.05, comment="货叉载物抬升高度")
        self.stretch_tray = p.loadParam("stretch_tray_position", type="float", default=0.03, comment="货叉伸缩放置托盘位置")
        self.stretch_tray1 = p.loadParam("stretch_tray1_position", type="float", default=0.025, comment="货叉unload伸缩放置托盘位置")
        self.DI1 = p.loadParam("DI_P1", type="int", default=17, comment="P1工位有货物")
        self.DI2 = p.loadParam("DI_P2", type="int", default=18, comment="P2工位有货物")
        self.DI3 = p.loadParam("DI_front_limit", type="int", default=4, comment="货叉前向限位开关")
        self.DI4 = p.loadParam("DI_rear_limit", type="int", default=2, comment="货叉后向限位开关")
        self.DI5 = p.loadParam("DI_left_limit", type="int", default=0, comment="货叉左向限位开关")
        self.DI6 = p.loadParam("DI_right_limit", type="int", default=1, comment="货叉右向限位开关")
        self.DI7 = p.loadParam("DI_bottom_limit", type="int", default=5, comment="货叉底部限位开关")
        self.DI8 = p.loadParam("DI_top_limit", type="int", default=7, comment="货叉顶部限位开关")
        self.reach_di = p.loadParam("fork_reached", type="int", default=22, comment="货叉到位DI信号通道")
        self.DO1 = p.loadParam("DI_top_limit", type="int", default=17, comment="扫码相机光源开关")
        self.lift_motor_name = p.loadParam("LiftMotorName", type="str", default="motor-z", comment="货叉升降电机名称")
        self.stretch_motor_name = p.loadParam("StretchMotorName", type="str", default="motor-y", comment="货叉伸缩电机名称")
        self.shift_motor_name = p.loadParam("ShiftMotorName", type="str", default="motor-x", comment="货叉平移电机名称")
        self.state = dict()
        self.status = MoveStatus.NONE
        self.operation_status = MoveStatus.NONE
        self.init = True
        self.robot = None
        self.lift_motor = None
        self.stretch_motor = None
        self.shift_motor = None
        self.opt_step = [False]*14
        self.rec_file = None
        self.rec = None
        self.rec_pos = 0
        self.lift_height = self.lift_zero
        self.stretch_length = self.stretch_zero
        self.shift_width = self.shift_zero
        self.terminal_url = None
        self.reach_data = None
        self.reach_flag = False
        self.action_data = None
        self.action_flag = False
        self.finish_data = None
        self.finish_flag = False
        self.reset_data = None
        self.reset_flag = False
        r.logInfo(f"__init__ args: {args}")
        self.p_offset = 0


    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        self.operation_status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.lift_motor = Motor(r, self.lift_motor_name, -1)
            self.stretch_motor = Motor(r, self.stretch_motor_name, -1)
            self.shift_motor = Motor(r, self.shift_motor_name, -1)
            self.robot = Robot(r)
            self.rec_file = args.get("recFile", None)
            # 获取与设备通信的参数
            self.terminal_url = args.get('postURL', False)
            self.reach_data = args.get('postData', dict()).get('reach', False)
            self.action_data = args.get('postData', dict()).get('action', False)
            self.finish_data = args.get('postData', dict()).get('finish', False)
            self.reset_data = args.get('postData', dict()).get('reset', False)
            if self.rec_file:
                self.rec = RecAdjust(r, self.rec_file)
            args_error = False
            if "operation" in args:
                code2pgv_x = 0
                code2pgv_y = 0
                pgv_datas = r.pgv()
                for p in pgv_datas["pgvs"]:
                    if "pgv_info" not in p:
                        continue
                    if p["pgv_info"]["is_upside"]:
                        continue
                    if not p["is_DMT_detected"]:
                        continue
                    code2pgv_x = p["tag_diff_x"]   # 平移方向
                    code2pgv_y = p["tag_diff_y"]   # 伸出方向
                r.logDebug("[pgv_tag_diff][{}|{}]".format(code2pgv_x, code2pgv_y))
                self.p_offset = code2pgv_y      # 获取伸缩方向增补距离
                if "liftHeight" in args:
                    self.lift_height = args["liftHeight"]
                    if args["liftHeight"] > self.max_lift_height:
                        r.setError(f"Out of max lift height {self.max_lift_height}")
                        args_error = True
                    elif args["liftHeight"] < self.lift_zero:
                        self.lift_height = self.lift_zero
                if "stretchLength" in args:
                    self.stretch_length = args["stretchLength"] - self.p_offset
                    if args["stretchLength"] > self.max_stretch_length:
                        r.setError(f"Out of max stretch length {self.max_stretch_length}")
                        args_error = True
                    elif args["stretchLength"] < self.stretch_zero:
                        self.stretch_length = self.stretch_zero
                if "shiftWidth" in args:    # 只在shift模式下使用
                    self.shift_width = args["shiftWidth"]
                    if args["shiftWidth"] > self.max_shift_width:
                        r.setError(f"Out of max shift width {self.max_shift_width}")
                        args_error = True
                    elif args["shiftWidth"] < self.shift_zero:
                        self.shift_width = self.shift_zero
                if "forkLiftUp" in args:
                    self.lift_up = args["forkLiftUp"]
                if args["operation"] == "zero":
                    if self.check_DI(r, self.DI1) or self.check_DI(r, self.DI2):
                        r.setError(f"AVG has goods, cannot zero")
                        args_error = True
                if args["operation"] == "load":
                    self.shift_width = self.P1_shift_pos
                    if "liftHeight" not in args:
                        r.setError(f"Pls input liftHeight")
                        args_error = True
                    if "stretchLength" not in args:
                        r.setError(f"Pls input stretchLength")
                        args_error = True
                if args["operation"] == "unload":
                    self.shift_width = self.P1_shift_pos
                    if "liftHeight" not in args:
                        r.setError(f"Pls input liftHeight")
                        args_error = True
                    if "stretchLength" not in args:
                        r.setError(f"Pls input stretchLength")
                        args_error = True
            else:
                r.setError(f"No operation in args, Pls choose operation")
                args_error = True
            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED

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

        if args["operation"] == "zero":
            self.zero(r)
        elif args["operation"] == "load":
            if self.rec is not None:
                if self.rec.status == MoveStatus.FINISHED:
                    r.setDO(r, self.DO1, False)
                    self.load(r)
                else:
                    r.setDO(r, self.DO1, True)
                    self.rec.read(r)
            else:
                self.load(r)
        elif args["operation"] == "unload":
            if self.rec is not None:
                if self.rec.status == MoveStatus.FINISHED:
                    self.unload(r)
                else:
                    self.rec.read(r)
            else:
                self.unload(r)
        elif args["operation"] == "lift":
            self.lift(r)
        elif args["operation"] == "stretch":
            self.stretch(r)
        elif args["operation"] == "shift":
            self.shift(r)
        else:
            r.setError(f"operation error: {args['operation']}")
            self.status = MoveStatus.FAILED
        if not r.publishSpeed():
            r.setError(f"Fail to publish speed")
            self.status = MoveStatus.FAILED

        # 给设备写完成信号
        if not self.finish_flag and self.operation_status == 3 and self.finish_data:
            finish_res = self.call_terminal(r, self.terminal_url, self.finish_data)
            if finish_res and finish_res.get('status', -1) == 1:
                self.finish_flag = True
        # 将到位信号与完成信号清零
        if self.finish_flag and not self.reset_flag and self.reset_data:
            if self.delay(5):
                reset_res0 = self.call_terminal(r, self.terminal_url, self.reset_data[0])
                reset_res1 = self.call_terminal(r, self.terminal_url, self.reset_data[1])
                if reset_res0 and reset_res1 and reset_res0.get('status', -1) == 1 and reset_res1.get('status', -1) == 1:
                    self.finish_flag = True
                    self.status = MoveStatus.FINISHED

        if self.terminal_url == "" or not bool(self.terminal_url):
            self.status = self.operation_status

        self.state['status'] = self.status
        self.state['args'] = args
        self.state['step'] = self.opt_step
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        r.setWarning(f"step: {self.opt_step}")
        return self.status

    def zero(self, r):
        """
        只有在agv没有货物的情况下才可以标零
        """
        if not self.opt_step[0]:
            self.opt_step[0] = self.robot.shift(self.shift_motor, self.P1_shift_pos)    # 先左右平移到P1缓存位位置
        if self.opt_step[0] and not self.opt_step[1]:
            if not self.check_DI(r, self.DI4):        # z轴限位开关
                self.opt_step[1] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
        if self.opt_step[1] and not self.opt_step[2]:
            if not self.check_DI(r, self.DI7):        # y轴限位开关
                self.opt_step[2] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[2] and not self.opt_step[3]:
            if not self.check_DI(r, self.DI6):        # x轴限位开关
                self.opt_step[3] = self.robot.shift(self.shift_motor, self.shift_zero)
        if self.opt_step[3]:
            self.operation_status = MoveStatus.FINISHED
        zero_state = dict()
        zero_state['opt_name'] = "zero"
        zero_state['opt_status'] = self.operation_status
        zero_state['actions'] = self.robot.state
        self.state['operation'] = zero_state
        r.logInfo(f"zero: {zero_state}")

    def stretch(self, r):
        if not self.opt_step[0]:
            if not self.check_DI(r, self.DI3) and not self.check_DI(r, self.DI4):
                self.opt_step[0] = self.robot.stretch(self.stretch_motor, self.stretch_length)
        else:
            self.operation_status = MoveStatus.FINISHED
        stretch_state = dict()
        stretch_state['opt_name'] = "stretch"
        stretch_state['opt_status'] = self.operation_status
        stretch_state['actions'] = self.robot.state
        self.state['operation'] = stretch_state
        r.logInfo(f"stretch: {stretch_state}")

    def lift(self, r):
        if not self.opt_step[0]:
            if not self.check_DI(r, self.DI7) and not self.check_DI(r, self.DI8):
                r.setNotice(f"step: {self.lift_height}")
                self.opt_step[0] = self.robot.lift(self.lift_motor, self.lift_height)
        else:
            self.operation_status = MoveStatus.FINISHED
        lift_state = dict()
        lift_state['opt_name'] = "lift"
        lift_state['opt_status'] = self.operation_status
        lift_state['actions'] = self.robot.state
        self.state['operation'] = lift_state
        r.logInfo(f"lift: {lift_state}")

    def shift(self, r):
        if not self.opt_step[0]:
            if not self.check_DI(r, self.DI5) and not self.check_DI(r, self.DI6):
                self.opt_step[0] = self.robot.shift(self.shift_motor, self.shift_width)
        else:
            self.operation_status = MoveStatus.FINISHED
        shift_state = dict()
        shift_state['opt_name'] = "shift"
        shift_state['opt_status'] = self.operation_status
        shift_state['actions'] = self.robot.state
        self.state['operation'] = shift_state
        r.logInfo(f"shift: {shift_state}")

    def load(self, r):
        if not self.opt_step[0]:
            self.opt_step[0] = self.robot.shift(self.shift_motor, self.P1_shift_pos)
        if self.opt_step[0] and not self.opt_step[1]:
            self.opt_step[1] = self.robot.lift(self.lift_motor, self.lift_height)
        if self.opt_step[1] and not self.opt_step[2]:
            if self.rec is None:
                self.opt_step[2] = True
            else:
                self.opt_step[2] = self.robot.shift(self.shift_motor, self.P1_shift_pos + self.rec.pos)
        if self.opt_step[2] and not self.opt_step[3]:
            self.opt_step[3] = self.robot.stretch(self.stretch_motor, self.stretch_length - self.p_offset - 0.03)
        if self.opt_step[3] and not self.opt_step[4]:
            self.opt_step[4] = self.robot.stretchlow(self.stretch_motor, self.stretch_length - self.p_offset)
            if self.fork_reached(r):
                self.stretch_motor.reset()
                self.opt_step[4] = True
        if self.opt_step[4] and not self.opt_step[5]:
            self.opt_step[5] = self.robot.liftlow(self.lift_motor, self.lift_height + self.lift_up)
        if self.opt_step[5] and not self.opt_step[6]:
            self.opt_step[6] = self.robot.stretch(self.stretch_motor, self.stretch_tray)
        if self.opt_step[6] and not self.opt_step[7]:
            self.opt_step[7] = self.robot.shift(self.shift_motor, self.shift_width)
        if self.opt_step[7] and not self.opt_step[8]:
            self.opt_step[8] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[8] and not self.opt_step[9]:
            self.opt_step[9] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
        if self.opt_step[9] and not self.opt_step[10]:
            self.opt_step[10] = self.robot.shift(self.shift_motor, self.shift_zero)
        if self.opt_step[10]:
            self.operation_status = MoveStatus.FINISHED
        load_state = dict()
        load_state['opt_name'] = "load"
        load_state['opt_status'] = self.operation_status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state
        r.logInfo(f"load: {load_state}")

    def unload(self, r):
        if not self.opt_step[0]:
            self.opt_step[0] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[0] and not self.opt_step[1]:
            self.opt_step[1] = self.robot.shift(self.shift_motor, self.shift_width)
        if self.opt_step[1] and not self.opt_step[2]:
            self.opt_step[2] = self.robot.stretch(self.stretch_motor, self.stretch_tray1)
        if self.opt_step[2] and not self.opt_step[3]:
            self.opt_step[3] = self.robot.lift(self.lift_motor, self.lift_height)
        if self.opt_step[3] and not self.opt_step[4]:
            self.opt_step[4] = self.robot.shift(self.shift_motor, self.P1_shift_pos)
        if self.opt_step[4] and not self.opt_step[5]:
            if self.rec is None:
                self.opt_step[5] = True
            else:
                self.opt_step[5] = self.robot.shift(self.shift_motor, self.P1_shift_pos + self.rec.pos)
        if self.opt_step[5] and not self.opt_step[6]:
            self.opt_step[6] = self.robot.stretch(self.stretch_motor, self.stretch_length - self.p_offset - 0.03)
        if self.opt_step[6] and not self.opt_step[7]:
            self.opt_step[7] = self.robot.stretchlow(self.stretch_motor, self.stretch_length - self.p_offset)
            if self.fork_reached(r):
                #self.position = self.get_motor_pos(r, self.stretch_motor_name)
                #r.resetMotor(self.stretch_motor_name)
                #r.setWarning(f"lift: {self.position}")
                self.stretch_motor.reset()
                self.opt_step[7] = True
                #self.position = self.get_motor_pos(r, self.stretch_motor_name)
                #self.opt_step[6] = self.robot.stretch(self.stretch_motor, self.position - 0.005)
        if self.opt_step[7] and not self.opt_step[8]:
            if self.fork_reached(r):
                #self.opt_step[7] = self.robot.stretch(self.stretch_motor, self.get_motor_pos(r, self.stretch_motor_name) - 0.25)
                #self.position = self.get_motor_pos(r, self.stretch_motor_name)
                #r.setError(f"stretch: {self.position}")
                #self.opt_step[8] = self.robot.stretchlow(self.stretch_motor, self.position - 0.01)
                self.opt_step[8] = True
            else:
                self.opt_step[8] = True
        if self.opt_step[8] and not self.opt_step[9]:
            self.opt_step[9] = self.robot.liftlow(self.lift_motor, self.lift_height - self.lift_up)
        if self.opt_step[9] and not self.opt_step[10]:
            self.opt_step[10] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
        if self.opt_step[10] and not self.opt_step[11]:
            self.opt_step[11] = self.robot.shift(self.shift_motor, self.P1_shift_pos)
        if self.opt_step[11] and not self.opt_step[12]:
            self.opt_step[12] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[12] and not self.opt_step[13]:
            self.opt_step[13] = self.robot.shift(self.shift_motor, self.shift_zero)
        if self.opt_step[13]:
            self.operation_status = MoveStatus.FINISHED
        unload_state = dict()
        unload_state['opt_name'] = "unload"
        unload_state['opt_status'] = self.operation_status
        unload_state['actions'] = self.robot.state
        self.state['operation'] = unload_state
        r.logInfo(f"unload: {unload_state}")

    # 与终端设备交互
    @staticmethod
    def call_terminal(r, url, data):
        try:
            res = requests.post(url, json=data, timeout=5.0)
        except Exception as e:
            r.logInfo(f"post failed!!! url: {url}, data: {data}, error: {e}")
            return False
        else:
            if res.status_code == 200:
                return json.loads(res.text)
            else:
                return False

    @staticmethod
    def get_motor_pos(r: SimModule, motor_name: str):
        """
        获取指定电机的当前位置
        :param r: SimModule类对象
        :param motor_name: 电机名称
        :return: 返回电机的当前位置，若电机不存在返回False
        """
        motors = r.odo().get("motor_info", [])
        motor_pos = False
        for m in motors:
            if m['motor_name'] == motor_name:
                motor_pos = m.get('position', False)
        return motor_pos

    @staticmethod
    def check_DI(r: SimModule, di: int):
        """
        检测单个DI是否被触发
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

    def fork_reached(self, r: SimModule) -> bool:
        """
        货叉到位DI检测
        :param r:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node['id'] == self.reach_di:
                if node['status']:
                    #r.setMotorSpeed(self.stretch_motor, 0)
                    #r.resetMotor(self.stretch_motor)
                    return True
        return False

    # 延时函数
    @staticmethod
    def delay(second):
        """
        延时 second 秒
       :param second:
        :return: 延时完成返回True
        """
        if ModuleTool.start_time is None:
            ModuleTool.start_time = time.time()
        if time.time() - ModuleTool.start_time > second:
            ModuleTool.start_time = None
            return True
        return False


class Motor:
    def __init__(self, r, motor_name: str, stop_di: int):
        self.motor_name = motor_name
        self.stop_di = stop_di
        self.r = r
        self.status = MoveStatus.NONE
        self.state = dict()

    def run(self, vel=0., pos=0., max_vel=0.):
        """
        控制电机运转，辊筒电机需传参 vel，线性电机需传参 pos 和 max_vel
        :param vel: 辊筒电机转速
        :param pos: 线性电机目标位置
        :param max_vel: 线性电机最大转速
        :return:
        """
        self.r.setMotorPosition(self.motor_name, pos, max_vel, self.stop_di)
        if self.r.isMotorReached(self.motor_name):
            self.r.resetMotor(self.motor_name)
            self.status = MoveStatus.FINISHED
        self.state['motor_name'] = self.motor_name
        self.state['motor_goal_pos'] = pos
        self.state['motor_pos'] = ModuleTool.get_motor_pos(self.r, self.motor_name)
        self.state['motor_speed'] = ModuleTool.get_motor_speed(self.r, self.motor_name)
        self.state['motor_status'] = self.status

    def reset(self):
        self.r.logInfo(f"motor reset: {self.motor_name}")
        self.r.resetMotor(self.motor_name)
        self.status = MoveStatus.RUNNING


class Robot:
    def __init__(self, r):
        self.r = r
        self.state = dict()

    def lift(self, motor: Motor, height: float, max_vel=0.05) -> bool:
        """
        控制升降电机
        :param motor:
        :param height:
        :param max_vel:
        :return:
        """
        self.state['lift'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=height, max_vel=max_vel)
        return False

    def liftlow(self, motor: Motor, height: float, max_vel=0.005) -> bool:
        """
        控制升降电机
        :param motor:
        :param height:
        :param max_vel:
        :return:
        """
        self.state['liftlow'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=height, max_vel=max_vel)
        return False

    def stretch(self, motor: Motor, length: float, max_vel=0.03) -> bool:
        """
        控制伸缩机构电机
        :param motor:
        :param length:
        :param max_vel:
        :return:
        """
        self.state['stretch'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=length, max_vel=max_vel)
        return False

    def stretchlow(self, motor: Motor, length: float, max_vel=0.005) -> bool:
        """
        控制伸缩机构电机
        :param motor:
        :param length:
        :param max_vel:
        :return:
        """
        self.state['stretchlow'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=length, max_vel=max_vel)
        return False

    def shift(self, motor: Motor, width: float, max_vel=0.05) -> bool:
        """
        控制伸缩机构电机
        :param motor:
        :param width:
        :param max_vel:
        :return:
        """
        self.state['shift'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=width, max_vel=max_vel)
        return False


class RecAdjust:
    def __init__(self, r, file):
        self.file = file
        self.status = MoveStatus.NONE
        self.rec_failed_time = 0
        self.max_rec_time = 5
        self.pos = 0
        self.state = dict()

    def read(self, r):
        self.status = MoveStatus.RUNNING
        rec_result = self.rec_file(r, self.file)
        if rec_result:
            pos2world = [rec_result['x'], rec_result['y'], rec_result['yaw']]
            robot2world = [r.loc()['x'], r.loc()['y'], r.loc()['angle']]
            pos2robot = Pos2Base(pos2world, robot2world)
            self.pos = pos2robot[0]
            self.status = MoveStatus.FINISHED
        else:
            self.rec_failed_time += 1
            if self.rec_failed_time > self.max_rec_time:
                r.setError(f"rec failed the max times, {rec_result}")
                self.status = MoveStatus.FAILED
        self.state['rec_result'] = rec_result
        self.state['rec_file'] = self.file
        self.state['rec_adjust'] = self.status

    @staticmethod
    def rec_file(r: SimModule, file):
        """
        识别文件, 识别成功返回识别数据，否则返回 False
        :param r:
        :param file:
        :return:
        """
        rec_status = r.getRecStatus()
        if rec_status == 2:
            return r.getRecResult()
        elif rec_status == 3:
            r.resetRec()
        else:
            r.doRec(file)
        return False


if __name__ == '__main__':
   pass
