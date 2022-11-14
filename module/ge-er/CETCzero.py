# ��������
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

"""
operation(动作)说明：
    
    "jack":表示顶升先动，顶升到指定高度，推送电机再动作到指定位置
    "push":表示推送电机先动作到指定位置，顶升电机再动到指定高度
    "module":取设备上的料篮，需要使用货叉头的光电，所以分开写

"""
"""
####BEGIN DEFAULT ARGS####
{
    "jackHeight": {
        "value": "",
        "default_value": "",
        "tips": "tips",
        "type": "double"
    },
    "pushPosition": {
        "value": "",
        "default_value": "",
        "tips": "tips",
        "type": "double"
    },
    "operation": {
        "value": "",
        "default_value": [
            "jack", "FindZero", "useDI"
        ],
        "tips": "tips",
        "type": "complex"
    }

}

####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.di1 = 0
        self.di2 = 2
        self.jackMotor = "jack"
        self.pushMotor = "push"
        self.operation = ""
        self.operation_list = ["jack", "FindZero", "useDI"]
        self.jack_height = ""
        self.push_position = ""
        self.task_list = []
        self.task_id = 0
        self.start_time = time.time()
        self.over_time = p.loadParam("over_time", type="float", default=120.0, maxValue=3600.0, minValue=0.0, unit="s",
                                     comment="time")
        self.init = True
        self.operation_status = MoveStatus.NONE
        self.state = dict()

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
            if "jackHeight" not in args or "pushPosition" not in args or "operation" not in args:
                r.setError("user args define error {}".format(
                    json.dumps(args)))
                self.status = MoveStatus.FAILED
            else:
                self.jack_height = args["jackHeight"]
                self.push_position = args["pushPosition"]
                self.operation = args["operation"]
        if self.status is MoveStatus.FAILED:
            return self.status

        if self.jack_height == "" or not self.is_number(self.jack_height):
            r.setError("please inside jackHeight!")
            self.status = MoveStatus.FAILED
        elif self.push_position == "" or not self.is_number(self.push_position):
            r.setError("please inside pushPosition!")
            self.status = MoveStatus.FAILED
        elif self.operation not in self.operation_list:
            r.setError("operation doesn't support!")
            self.status = MoveStatus.FAILED

        else:
            self.jack(r, self.jackMotor, self.jack_height,
                      self.pushMotor, self.push_position, self.operation, self.di1, self.di2)
        if self.status is not MoveStatus.FAILED:
            if not r.publishSpeed():
                self.status = MoveStatus.FAILED
        self.status = self.operation_status
        self.state["status"] = self.status
        self.state["args"] = args
        str_state = json.dumps(self.state)
        r.setInfo(str_state)
        r.logDebug(str_state)
        return self.status

    def runTakList(self, r):
        """����TaskList
        """
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

    def jack(self, r, jackMotor, jack_height, pushMotor, push_position, operation, di1, di2):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            # r.setError("jack_motor{}".format(self.jack_motor))
            self.task_list = [
                Motor(jackMotor, jack_height, pushMotor,
                      push_position, operation, di1, di2)
            ]
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
    def __init__(self, jackMotor, jack_height, pushMotor, push_position, operation, di1, di2):
        """
        LineMotorPosition
        Args:
            jackMotor (string): 顶升电机
            jack_height(String):指定顶升高度，注意发送的距离如果大于限位距离，会报错（最大1.1m)
            pushMotor(string):货叉电机
            push_position(string):指定伸出距离，0-0.35m
            operation(string):动作名称
        """
        self.status = MoveStatus.NONE
        self.jackMotor = jackMotor
        self.jackHeight = float(jack_height)
        self.pushMotor = pushMotor
        self.push_position = float(push_position)
        self.operation = operation
        self.di1 = di1
        self.di2 = di2
        self.reachDI = -1

    def reset(self, r: SimModule, roller):
        r.resetMotor(self.jackMotor)
        r.resetMotor(self.pushMotor)
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, roller):
        self.status = MoveStatus.RUNNING
        di = r.Di()
        di1_status = False
        di2_status = False
        for (ind, node) in enumerate(di['node']):
            if node['id'] == self.di1:
                di1_status = node['status']
            elif node['id'] == self.di2:
                di2_status = node['status']

        if self.operation == "jack":
            r.setMotorPosition(self.jackMotor, self.jackHeight, 0.05, -1)
            if r.isMotorPositionReached(self.jackMotor, self.jackHeight, -1):
                r.setMotorPosition(
                    self.pushMotor, self.push_position, 0.02, self.reachDI)
                if r.isMotorPositionReached(self.pushMotor, self.push_position, self.reachDI):
                    self.status = MoveStatus.FINISHED

        if self.operation == "FindZero":
            r.setMotorPosition(self.pushMotor, 0, 0.02, -1)
            if r.isMotorPositionReached(self.pushMotor, 0, -1):
                r.setMotorPosition(self.jackMotor, 0, 0.005, -1)
                if r.isMotorPositionReached(self.jackMotor, 0, -1):
                    self.status = MoveStatus.FINISHED

        if self.operation == "useDI":
            r.setMotorPosition(self.jackMotor, self.jackHeight, 0.005, -1)
            if r.isMotorPositionReached(self.jackMotor, self.jackHeight, -1):
                r.setMotorPosition(
                    self.pushMotor, self.push_position, 0.02, self.reachDI)
                if di2_status or r.isMotorPositionReached(self.pushMotor, self.push_position, self.reachDI):
                    r.setMotorSpeed(self.pushMotor, 0, self.reachDI)
                    r.publishSpeed()
                    if r.isMotorStop(self.pushMotor):
                        self.status = MoveStatus.FINISHED

        state = dict()
        state["operation"] = self.operation
        state["status"] = self.status

    # 判断一个字符串是否是一串数字

    def is_number(x):
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
