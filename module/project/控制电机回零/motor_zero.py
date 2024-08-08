import sys

sys.path.append("../syspy")
import json
from syspy.rbkSim import SimModule
from syspy.robot import Robot, ModuleTool, NetHandle, Motor, MotorType
from syspy.rbk import MoveStatus, BasicModule, ParamServer

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "zero_motor3",
        "default_value":["zero_motor3","zero_motor4","motor3","motor4"],
        "tips": "tips",
        "type": "complex"
    },
    "speed": {
        "value": -0.01,
        "tips": "标零速度",
        "type": "float",
        "unit": "m"
    },
    "stretch":{
        "value": 0.0,
        "tips": "伸出长度",
        "type": "float",
        "unit": "m"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.check_id = None
        self.init_motor4_pos = None
        self.init_motor3_pos = None
        p = ParamServer(__file__)
        self.status = MoveStatus.NONE
        self.max_motor3_name = p.loadParam("motor3", type="str", default="motor3", comment="motor3")
        self.max_motor4_name = p.loadParam("motor4", type="str", default="motor4", comment="motor4")

        self.motor3_zeroDI = p.loadParam("motor3_DI", type="int", default=2, comment="motor3零位DI")
        self.motor4_zeroDI = p.loadParam("motor4_DI", type="int", default=4, comment="motor4零位DI")

        self.max_motor3_len = p.loadParam("motor3_max_len", type="float", default=1.1, comment="motor3最大行程")
        self.max_motor4_len = p.loadParam("motor4_max_len", type="float", default=0.4, comment="motor4最大行程")
        self.min_motor3_len = p.loadParam("motor3_min_len", type="float", default=0., comment="motor3最小行程")
        self.min_motor4_len = p.loadParam("motor4_min_len", type="float", default=0., comment="motor4最小行程")
        self.motor3 = Motor(r, MotorType.LINEAR_MOTOR, self.max_motor3_name, -1)
        self.motor4 = Motor(r, MotorType.LINEAR_MOTOR, self.max_motor4_name, -1)
        self.init = True
        self.speed = None
        self.stretch_len = None
        self.robot = Robot(r)
        self.zero_state = False
        self.state = dict()
        self.m3_pos = 0.
        self.m4_pos = 0.
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            args_error = False
            if "operation" in args:  # 参数检查
                if "speed" in args:
                    self.speed = args["speed"]
                if "stretch" in args:
                    self.stretch_len = args["stretch"]
            else:
                args_error = True
            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED
        if args["operation"] == "zero_motor3":
            self.zero(r, "zero_motor3")
        elif args["operation"] == "zero_motor4":
            self.zero(r, "zero_motor4")
        elif args["operation"] == "motor3":
            self.stretch(r, "motor3")
        elif args["operation"] == "motor4":
            self.stretch(r, "motor4")
        else:
            r.setError(f"operation error: {args['operation']}")
            self.status = MoveStatus.FAILED
        self.state['status'] = self.status
        self.m3_pos = self.get_motor_pos(r, self.max_motor3_name)
        self.m4_pos = self.get_motor_pos(r, self.max_motor4_name)
        if self.m3_pos:
            if not self.min_motor3_len < self.m3_pos < self.max_motor3_len:
                r.stopMotor()
                self.status = MoveStatus.FAILED
                r.setError("motor3 out of len")
        if self.m4_pos:
            if not self.min_motor4_len < self.m4_pos < self.max_motor4_len:
                r.stopMotor()
                self.status = MoveStatus.FAILED
                r.setError("motor4 out of len")

        self.state['init_motor3_pos'] = self.get_motor_pos(r, self.max_motor3_name)
        self.state['init_motor4_pos'] = self.get_motor_pos(r, self.max_motor4_name)

        self.state['speed'] = self.speed
        self.state['di'] = self.motor3_zeroDI
        self.state['args'] = args
        self.state['c'] = r.getCount()
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        r.publishSpeed()
        return self.status

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

    def zero(self, r, param):
        if not self.zero_state:
            if param == "zero_motor3":
                self.check_id = self.motor3_zeroDI
                r.setMotorSpeed(self.max_motor3_name, self.speed, self.motor3_zeroDI)
                r.publishSpeed()
            if param == "zero_motor4":
                self.check_id = self.motor4_zeroDI
                r.setMotorSpeed(self.max_motor4_name, self.speed, self.motor4_zeroDI)
                r.publishSpeed()
        if self.check_di(r):
            self.zero_state = True
        if self.zero_state:
            self.status = MoveStatus.FINISHED
        zero_state = dict()
        zero_state['opt_name'] = "zero"
        zero_state['opt_status'] = self.status
        zero_state['zero_motor'] = param
        zero_state['check_id'] = self.check_id
        self.state['operation'] = zero_state

    def check_di(self, r: SimModule) -> bool:
        """
        货叉到位DI检测
        :param r:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node['id'] == self.check_id:
                if node['status']:
                    return True
        return False

    def stretch(self, r, param):
        if param == "motor3":
            if self.robot.stretch(self.motor3, self.stretch_len):
                self.status = MoveStatus.FINISHED
        if param == "motor4":
            if self.robot.stretch(self.motor4, self.stretch_len):
                self.status = MoveStatus.FINISHED
