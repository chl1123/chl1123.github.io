# ��������
import json
import time
from rbk import MoveStatus, BasicModule, ParamServer
from rbkSim import SimModule

"""
operation(动作)说明：
    
    "roller_low_load":下层辊筒上料
    "roller_low_unload":下层辊筒下料
    "roller_high_load":上层辊筒上料
    "roller_high_unload":上层辊筒下料
    "jack":顶升至指定高度
    "RollerStop":机构停止动作

"""

####BEGIN DEFAULT ARGS####
{
    "operation": {
        "value": "",
        "default_value": [
            "roller_low_load", "roller_low_unload", "roller_high_load", "roller_high_unload", "jack", "RollerStop", "pre_roller_low", "pre_roller_high"
        ],
        "tips": "tips",
        "type": "complex"
    },
    "direction": {
        "value": "",
        "default_value": [
            "left", "right"
        ],
        "tips": "tips",
        "type": "complex"
    },
    "jackHeight": {
        "value": "",
        "default_value": "",
        "tips": "tips",
        "type": "double"
    }

}

####END DEFAULT ARGS####


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        """
           roller_low : 下层辊筒
           roller_high : 上层辊筒
           block1 : 下层辊筒左挡板
           block2 : 下层辊筒右挡板
           block3 : 上层辊筒左挡板
           block4 : 上层辊筒右挡板
        """
        super(Module, self).__init__()
        p = ParamServer(__file__)
        # 下层辊筒对射光电
        self.roller_low_1 = p.loadParam("di19", type="int", default=19,
                                        maxValue=100, minValue=0, comment="roller low di1")
        self.roller_low_2 = p.loadParam("di20", type="int", default=20,
                                        maxValue=100, minValue=0, comment="roller low di2")
        self.roller_low_3 = p.loadParam("di21", type="int", default=21,
                                        maxValue=100, minValue=0, comment="roller low di3")
        self.roller_low_4 = p.loadParam("di22", type="int", default=22,
                                        maxValue=100, minValue=0, comment="roller low di4")
        # 上层辊筒对射光电
        self.roller_high_1 = p.loadParam("di23", type="int", default=23,
                                         maxValue=100, minValue=0, comment="roller high di1")
        self.roller_high_2 = p.loadParam("di24", type="int", default=24,
                                         maxValue=100, minValue=0, comment="roller high di2")
        self.roller_high_3 = p.loadParam("di25", type="int", default=25,
                                         maxValue=100, minValue=0, comment="roller high di3")
        self.roller_high_4 = p.loadParam("di26", type="int", default=26,
                                         maxValue=100, minValue=0, comment="roller high di4")
        # 下层辊筒挡板

        self.block1_up = p.loadParam("di35", type="int", default=35,
                                     maxValue=100, minValue=0, comment="block1 up di")
        self.block1_down = p.loadParam("di36", type="int", default=36,
                                       maxValue=100, minValue=0, comment="block1 down di")
        self.block2_up = p.loadParam("di37", type="int", default=37,
                                     maxValue=100, minValue=0, comment="block2 up di")
        self.block2_down = p.loadParam("di38", type="int", default=38,
                                       maxValue=100, minValue=0, comment="block2 down di")
        self.block1_motor = p.loadParam(
            "block1_motor", type="str", default="block1_motor", comment="motor name")
        self.block2_motor = p.loadParam(
            "block2_motor", type="str", default="block2_motor", comment="motor name")

        # 上层辊筒挡板

        self.block3_up = p.loadParam("di39", type="int", default=39,
                                     maxValue=100, minValue=0, comment="block3 up di")
        self.block3_down = p.loadParam("di40", type="int", default=40,
                                       maxValue=100, minValue=0, comment="block3 down di")
        self.block4_up = p.loadParam("di41", type="int", default=41,
                                     maxValue=100, minValue=0, comment="block4 up di")
        self.block4_down = p.loadParam("di42", type="int", default=42,
                                       maxValue=100, minValue=0, comment="block4 down di")
        self.block3_motor = p.loadParam(
            "block3_motor", type="str", default="block3_motor", comment="motor name")
        self.block4_motor = p.loadParam(
            "block4_motor", type="str", default="block4_motor", comment="motor name")
        # 到位光电
        self.check_di = p.loadParam("di0", type="int", default=0,
             maxValue=100, minValue=0, comment="check_di")
        self.check_do = p.loadParam(
            "check_do", type="int", default="1", comment="do id")
        #
        # 下层辊筒
        self.roller_low_left_do = p.loadParam(
            "roller_low_left_do", type="int", default="18", comment="do id")
        self.roller_low_right_do = p.loadParam(
            "roller_low_right_do", type="int", default="19", comment="do id")
        # 上层辊筒
        self.roller_high_left_do = p.loadParam(
            "roller_high_left_do", type="int", default="20", comment="do id")
        self.roller_high_right_do = p.loadParam(
            "roller_high_right_do", type="int", default="21", comment="do id")
        # 升降电机
        self.jack_motor = p.loadParam(
            "jack_motor", type="str", default="jack_motor", comment="motor name")

        self.operation = ""
        self.direction = ""
        self.jack_height = ""
        self.operation_list = ["roller_low_load", "roller_low_unload",
                               "roller_high_load", "roller_high_unload", "jack", "Rollerstop", "pre_roller_low", "pre_roller_high"]
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
            if "jackHeight" not in args and "operation" not in args:
                r.setError("user args define error {}".format(
                    json.dumps(args)))
                self.status = MoveStatus.FAILED
            else:
                self.jack_height = args["jackHeight"]
                self.operation = args["operation"]
                self.direction = args["direction"]
        if self.status is MoveStatus.FAILED:
            return self.status

        if self.operation == "RollerStop":
            # 滚筒停止
            self.operation_status = self.RollerStop(r)
        elif self.operation == "roller_low_unload" and self.direction == "left":
            self.roller(r, self.roller_low_right_do, "unload", self.direction, self.block1_motor,
                        self.block1_up, self.block1_down, self.roller_low_1, self.roller_low_2, self.roller_low_4, self.roller_low_3)
        elif self.operation == "roller_low_load" and self.direction == "right":
            self.roller(r, self.roller_low_left_do, "load", self.direction, self.block2_motor,
                        self.block2_up, self.block2_down, self.roller_low_4, self.roller_low_3, self.roller_low_1, self.roller_low_2)
        elif self.operation == "roller_low_load" and self.direction == "left":
            self.roller(r, self.roller_low_left_do, "load", self.direction, self.block1_motor,
                        self.block1_up, self.block1_down, self.roller_low_4, self.roller_low_3, self.roller_low_1,self.roller_low_2)
        elif self.operation == "roller_low_unload" and self.direction == "right":
            self.roller(r, self.roller_low_right_do, "unload", self.direction, self.block2_motor,
                        self.block2_up, self.block2_down, self.roller_low_1, self.roller_low_2, self.roller_low_4, self.roller_low_3)
        elif self.operation == "roller_high_unload" and self.direction == "left":
            self.roller(r, self.roller_high_right_do, "unload", self.direction, self.block3_motor,
                        self.block3_up, self.block3_down, self.roller_high_1, self.roller_high_2, self.roller_high_4, self.roller_high_3)
        elif self.operation == "roller_high_load" and self.direction == "right":
            self.roller(r, self.roller_high_left_do, "load", self.direction, self.block4_motor,
                        self.block4_up, self.block4_down, self.roller_high_4, self.roller_high_3, self.roller_high_1,self.roller_high_2)
        elif self.operation == "roller_high_load" and self.direction == "left":
            self.roller(r, self.roller_high_left_do, "load", self.direction, self.block3_motor,
                        self.block3_up, self.block3_down, self.roller_high_4, self.roller_high_3, self.roller_high_1, self.roller_high_2)
        elif self.operation == "roller_high_unload" and self.direction == "right":
            self.roller(r, self.roller_high_right_do, "unload", self.direction, self.block4_motor,
                        self.block4_up, self.block4_down, self.roller_high_1, self.roller_high_2, self.roller_high_4, self.roller_high_3)
        elif self.operation == "pre_roller_low" and self.direction == "left":
            self.roller(r, self.roller_low_left_do, "pre_low_load", self.direction, self.block1_motor,
                        self.block1_up, self.block1_down, self.roller_low_4, self.roller_low_3, self.roller_low_1, self.roller_low_2)
        elif self.operation == "pre_roller_high" and self.direction == "left":
            self.roller(r, self.roller_high_left_do, "pre_high_load", self.direction, self.block3_motor,
                        self.block3_up, self.block3_down, self.roller_low_1, self.roller_low_2, self.roller_low_4, self.roller_low_3)

        elif self.operation == "jack":
            self.jack(r, self.jack_motor,
                      self.operation, self.jack_height, self.check_di, self.check_do)
        else:
            # 如果是不支持的operation则报错
            r.setError("operation: {}, direction: {} doesn't support!".format(
                self.operation, self.direction))
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

    def RollerStop(self, r):
        r.setDO(self.roller_low_left_do, False)
        r.setDO(self.roller_low_right_do, False)
        r.setDO(self.roller_high_left_do, False)
        r.setDO(self.roller_high_right_do, False)
        r.setMotorSpeed(self.block1_motor, 0, -1)
        r.setMotorSpeed(self.block2_motor, 0, -1)
        r.setMotorSpeed(self.block3_motor, 0, -1)
        r.setMotorSpeed(self.block4_motor, 0, -1)
        r.setMotorSpeed(self.jack_motor, 0, -1)
        r.publishSpeed()
        return MoveStatus.FINISHED

    def roller(self, r, roller_do, action, direction, block_motor, block_up_di, block_down_di, di1, di2, di3, di4):
        self.direction = direction
        self.roller_do = roller_do
        self.action = action
        self.block_motor = block_motor
        self.block_up_di = block_up_di
        self.block_down_di = block_down_di

        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                BlockMotor(r, self.block_motor, "down",
                           self.block_up_di, self.block_down_di),
                RollerMotor(r, self.action, roller_do,
                            self.direction, di1, di2, di3, di4),
                BlockMotor(r, self.block_motor, "up",
                           self.block_up_di, self.block_down_di)
            ]
            self.task_id = 0
        else:
            self.runTakList(r)
        cur_state = dict()
        cur_state["operation_status"] = self.operation_status
        cur_state["task_id"] = self.task_id
        self.state["load"] = cur_state

    def jack(self, r, jack_Motor, action, jack_height, check_di, check_do):
        self.jack_motor = jack_Motor
        self.action = action
        self.jack_height = jack_height
        self.check_di = check_di
        self.check_do = check_do

        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            if self.jack_height == "" or not self.is_number(self.jack_height):
                r.setError("please inside correct jackHeight!")
                self.status = MoveStatus.FAILED
            else:
                self.task_list = [
                    JackMotor(r, self.jack_motor,
                              self.action, self.jack_height, self.check_di, self.check_do)
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


class JackMotor:
    def __init__(self, r: SimModule, jack_Motor, action, jack_height, check_di, check_do):
        """挡板电机初始化

        Args:
            jackMotor(string): 顶升电机
            operation (string): 执行方式"jack"
            jack_height(float): 顶升高度

        """
        self.status = MoveStatus.NONE
        self.jack_motor = jack_Motor
        self.action = action
        self.jack_height = jack_height
        self.check_di = check_di
        self.check_do = check_do


    def reset(self, r: SimModule, jack):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, jack):
        self.status = MoveStatus.RUNNING
        di = r.Di()
        check_di_status = True

        for (ind, node) in enumerate(di['node']):
            if node['id'] == self.check_di:
                check_di_status = node['status']
        if self.action == "jack":
            r.setMotorPosition(self.jack_motor, self.jack_height, 0.01, -1)
            r.setDO(self.check_do, True)
            r.publishSpeed()
            if r.isMotorPositionReached(self.jack_motor, self.jack_height, -1) and check_di_status:
                self.status = MoveStatus.FINISHED
        r.publishSpeed()
        state = dict()
        state["action"] = self.action
        state["status"] = self.status
        jack.state["JackMotor"] = state


class BlockMotor:
    def __init__(self, r, motor_name, action, block_up_di, block_down_di):
        """挡板电机初始化

        Args:
            motor_name (string): 电机名称
            operation (string): 执行方式"Up"或者"Down"
        """
        self.status = MoveStatus.NONE
        self.motor = motor_name
        self.action = action
        self.block_up_di = block_up_di
        self.block_down_di = block_down_di

    def reset(self, r: SimModule, roller):
        r.resetMotor(self.motor)
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, roller):
        self.status = MoveStatus.RUNNING
        
        if self.action == "up":
            r.setMotorSpeed(self.motor, 1.0, -1)
            r.publishSpeed()
            if r.isMotorReached(self.motor):
                self.status = MoveStatus.FINISHED
        elif self.action == "down":
            r.setMotorSpeed(self.motor, -1, -1)
            r.publishSpeed()
            if r.isMotorReached(self.motor):
                self.status = MoveStatus.FINISHED
        state = dict()
        state["action"] = self.action
        state["status"] = self.status
        roller.state["BlockMotor"] = state


class RollerMotor:
    """控制roller电机
    """

    def __init__(self, r: SimModule, action, roller_do, direction, di1, di2, di3, di4):
        """初始化

        Args:
            operation (string): 电机执行的方式 Load或者Unload
            roller_left_do (int): 辊筒左转do
            roller_right_do (int): 辊筒右转do
            direction(string):辊筒转动方向
            di1 (int): 外侧di序号
            di2 (int): 中间di序号
            di3 (int): 内侧di序号
        """
        self.status = MoveStatus.NONE
        self.action = action
        self.roller_do = roller_do
        self.direction = direction
        self.di1 = di1
        self.di2 = di2
        self.di3 = di3
        self.di4 = di4

        self.unloadDI_flag = False
        self.run_time = time.time()
        self.start_time_flag = True

    def reset(self, r: SimModule, roller):
        self.status = MoveStatus.RUNNING
        self.unloadDI_flag = False

    def run(self, r: SimModule, roller):
        self.status = MoveStatus.RUNNING
        di = r.Di()
        di1_status = True
        di2_status = True
        di3_status = True
        di4_status = True

        for (ind, node) in enumerate(di['node']):
            if node['id'] == self.di1:
                di1_status = node['status']
            elif node['id'] == self.di2:
                di2_status = node['status']
            elif node['id'] == self.di3:
                di3_status = node['status']
            elif node['id'] == self.di4:
                di4_status = node['status']

        if self.action == "load":
            r.setDO(self.roller_do, True)
            if di1_status and di2_status and di3_status:
                #r.setDO(self.roller_do, False)
                #self.status = MoveStatus.FINISHED
                if self.start_time_flag:
                    self.start_time_flag = False
                    self.run_time = time.time()
                sleep_time = time.time() - self.run_time
                if sleep_time > 2:
                    r.setDO(self.roller_do, False)
                    self.status = MoveStatus.FINISHED
            elif di1_status and di2_status and di4_status:
                #r.setDO(self.roller_do, False)
                #self.status = MoveStatus.FINISHED
                if self.start_time_flag:
                    self.start_time_flag = False
                    self.run_time = time.time()
                sleep_time = time.time() - self.run_time
                if sleep_time > 2:
                    r.setDO(self.roller_do, False)
                    self.status = MoveStatus.FINISHED
        elif self.action == "unload":
            r.setDO(self.roller_do, True)
            if di3_status:
                self.unloadDI_flag = True
            if not di3_status and self.unloadDI_flag and not di1_status and not di2_status:
                if self.start_time_flag:
                    self.start_time_flag = False
                    self.run_time = time.time()
                sleep_time = time.time() - self.run_time
                if sleep_time > 3:
                    r.setDO(self.roller_do, False)
                    self.status = MoveStatus.FINISHED
        elif self.action == "pre_low_load":
            r.setDO(self.roller_do, True)
            self.status = MoveStatus.FINISHED
        elif self.action == "pre_high_load":
            r.setDO(self.roller_do, True)
            self.status = MoveStatus.FINISHED

        state = dict()
        state["action"] = self.action
        state["status"] = self.status
        roller.state["RollerMotor"] = state
