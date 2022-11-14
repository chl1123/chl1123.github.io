# 艾崇
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

""" 线性电机辊筒车 """
""" 
####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value": [
            "RollerLoad", "RollerUnLoad", "RollerStop"
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
        self.di1 = 7  # 进口处物料检测传感器
        self.di2 = 8  # 挡板处物料检测传感器
        self.roller_motor = "roller"  # 线性滚筒电机名称
        self.operation = ""
        self.task_list = []
        self.task_id = 0
        self.start_time = time.time()
        self.over_time = 120.0
        self.init = True
        self.operation_status = MoveStatus.NONE
        self.state = dict()
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        t = time.time() - self.start_time
        if t > self.over_time:
            self.status = MoveStatus.FAILED
            r.setError("Roller is over Time")
            return self.status
        self.status = MoveStatus.RUNNING
        self.state = dict()
        if self.init:
            self.init = False
            if "operation" not in args:
                r.setError("user args error {}".format(json.dumps(args)))
                self.status = MoveStatus.FAILED
            else:
                self.operation = args["operation"]
        if self.status is MoveStatus.FAILED:
            return self.status
        if self.operation == "RollerStop":
            self.RollerStop(r, self.roller_motor, self.di1, self.di2)
        elif self.operation == "RollerLoad":
            self.load(r, self.roller_motor, self.di1, self.di2)
        elif self.operation == "RollerUnLoad":
            self.unload(r, self.roller_motor, self.di1, self.di2)
        else:
            # 如果是不支持的operation则报错
            r.setError("operation: {} doesn't support!".format(self.operation))
            self.status = MoveStatus.FAILED
        # 发送速度
        if self.status is not MoveStatus.FAILED:
            if not r.publishSpeed():
                self.status = MoveStatus.FAILED
        self.status = self.operation_status
        self.state["status"] = self.status
        self.state["args"] = args
        str_state = json.dumps(self.state)
        r.setInfo(str_state)
        r.logInfo(str_state)
        return self.status

    def RollerStop(self, r, roller_motor, di1, di2):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                RollerMotor("Stop", roller_motor, di1, di2)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state

    def runTakList(self, r):
        """运行TaskList
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

    def load(self, r, roller_motor, di1, di2):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                RollerMotor("Load", roller_motor, di1, di2)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state

    def unload(self, r, roller_motor, di1, di2):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                RollerMotor("UnLoad", roller_motor, di1, di2)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["unload"] = cur_state


class SensorCheck:
    def __abs__(self, r: SimModule, sensor_id: int, check_time: float, check_value: bool):
        """传感器防止抖动
           Arg:
              sensor_id(int):防抖检测的DI
              check_time(float):防抖检测时间
              check_value(bool):防抖检测值
        """
        self.sensor_id = sensor_id
        self.check_time = check_time
        self.check_value = check_value
        self.start_time = time.time()

    def removeShake(self, result: bool):
        """
          消除传感器抖动
        """
        ti = time.time() - self.start_time
        dis = r.Di()
        for (ind, node) in enumerate(dis['node']):
            if node['id'] == self.sensor_id and ti <= self.check_time:
                if node['status'] == self.check_value:
                    result = True
                else:
                    result = False
                    r.setError("sensor di{} check shake is error,please check SRC or call SEER", self.sensor_id)
            else:
                r.setError("di{} number is not exist or checkOverTime", self.sensor_id)


class RollerMotor:
    """控制roller电机
    """

    def __init__(self, operation, roller_motor, di1, di2):
        """初始化

        Args:
            operation (string): 电机执行的方式 Load或者Unload
            roller_motor(string):滚筒电机名称
            di1 (int): # 物料检测传感器
            di2 (int):  # 物料检测传感器
            flag(bool):物料触发过di1&di2 or di3&di4
        """
        self.status = MoveStatus.NONE
        self.operation = operation
        self.roller_motor = roller_motor
        self.di1 = di1
        self.di2 = di2
        self.flag = False

    def reset(self, r, roller):
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
        # 执行上料操作
        if self.operation == "Load":
            # 检测光电都没有触发时执行滚筒转动 ,203速度
            if not di1_status and not di2_status:
                r.setMotorSpeed(self.roller_motor, 1, -1)
            if di1_status:
                self.flag = True
            if di2_status and self.flag:
                r.setMotorSpeed(self.roller_motor, 0, -1)
                self.status = MoveStatus.FINISHED
                r.publishSpeed()
        # 执行下料操作
        if self.operation == "UnLoad":
            # 检测光电都触发时执行滚筒转动,214速度
            if di1_status and di2_status:
                r.setMotorSpeed(self.roller_motor, -1, -1)
            if not di2_status and not di1_status:
                r.setMotorSpeed(self.roller_motor, 0, -1)
                self.status = MoveStatus.FINISHED
                r.publishSpeed()

        if self.operation == "Stop":
            r.setMotorSpeed(self.roller_motor, 0, -1)
            self.status = MoveStatus.FINISHED
            r.publishSpeed()
        state = dict()
        state["operation"] = self.operation
        state["status"] = self.status
        state["DI"] = {"di1": di1_status, "di2": di2_status}
        roller.state["RollerMotor"] = state


if __name__ == '__main__':
    import rbkSim

    r = rbkSim.SimModule()
    m = Module(r, None)
    data = dict()
    data["operation"] = "RollerLoad"
    print(m.run(r, data))
