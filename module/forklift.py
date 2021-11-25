# -*- coding: utf-8 -*-
# @Time : 2021/11/24 19:20
# @Author : zhong
# @File :forklift.py 前移叉车脚本
# @Version: 1.3
import enum
import json
import math
import syspy.goPath as goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer

"""
####BEGIN DEFAULT ARGS####
{
   "operation":{
        "value": "zero",
        "default_value":["zero","load","unload", "lift", "stretch"],
        "tips": "operation options",
        "type": "complex"        
    },    
    "stretchLength": {
        "value": 0.,
        "tips": "货叉伸出长度",
        "type": "float",
        "unit": "m"
    },
    "liftHeight": {
        "value": 0.,
        "tips": "货叉升降高度",
        "type": "float",
        "unit": "m"
    },
    "reachHeight": {
        "value": 0.,
        "tips": "取放货后货叉到位高度",
        "type": "float",
        "unit": "m"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super().__init__()
        p = ParamServer(__file__)
        self.move_dist = p.loadParam("MoveDist", type="float", default=0.6, comment="叉车移动的固定距离, 叉车尖端到支撑腿最前端的距离, 单位：米")
        self.max_move_speed = p.loadParam("MaxMoveSpeed", type="float", default=0.2, comment="叉车移动固定距离时的最大速度，单位：米/秒")
        self.safe_lift_height = p.loadParam("SafeLiftHeight", type="float", default=0.4, comment="载货时货叉安全高度")
        self.reach_di1 = p.loadParam("ReachDI1", type="int", default=1, comment="货叉到位检测DI1")
        self.reach_di2 = p.loadParam("ReachDI2", type="int", default=9, comment="货叉到位检测DI2")
        self.fork_peak_di1 = p.loadParam("ForkPeakDI1", type="int", default=2, comment="货叉尖端检测DI1")
        self.fork_peak_di2 = p.loadParam("ForkPeakDI2", type="int", default=4, comment="货叉尖端检测DI2")
        self.lift_zero = p.loadParam("LiftZero", type="float", default=0.079, comment="货叉升降零位")
        self.stretch_zero = p.loadParam("StretchZero", type="float", default=0.035, comment="货叉伸缩零位")
        self.lift_motor_name = p.loadParam("LiftMotorName", type="str", default="motor2", comment="货叉升降电机名称")
        self.stretch_motor_name = p.loadParam("StretchMotorName", type="str", default="motor3", comment="货叉伸缩电机名称")
        r.logInfo(f"__init__ args: {args}")
        self.state = dict()
        self.status = MoveStatus.NONE
        self.init = True
        self.go_path = goPath.Module(r, args)
        self.robot = Robot(r)
        self.lift_motor = None
        self.stretch_motor = None
        self.opt_step = [False]*6

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name, -1)
            self.stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, self.stretch_motor_name, -1)
            args_error = False
            # 获取升降电机数据
            lift_motor_pos = None
            try:
                motor_info = r.odo()['motor_info']
                for motor in motor_info:
                    if motor['motor_name'] == self.lift_motor_name:
                        lift_motor_pos = motor['position']
            except Exception as e:
                r.setError(f"Get motor info failed: {e}")
            if "operation" in args:     # 参数检查
                if args["operation"] == "zero":
                    pass
                elif args["operation"] == "lift" and "liftHeight" in args:
                    pass
                elif args["operation"] == "stretch" and "stretchLength" in args:
                    pass
                elif (args["operation"] == "load" or args["operation"] == "unload") and \
                        ("stretchLength" in args and "liftHeight" in args and "reachHeight" in args):
                    # 检查升降高度参数合理性
                    if args["operation"] == "load":
                        if args["liftHeight"] < lift_motor_pos:
                            r.setWarning(f"load liftHeight lower than current lift height {lift_motor_pos}")
                            args_error = True
                    elif args["operation"] == "unload":
                        if args["liftHeight"] > lift_motor_pos:
                            r.setWarning(f"unload liftHeight higher than current lift height {lift_motor_pos}")
                            args_error = True
                else:
                    args_error = True
            else:
                args_error = True
            if args_error:
                r.setError(f"args error: {args}")
                return MoveStatus.FAILED
        # 货叉碰撞检测
        if self.fork_collision(r):
            r.setError(f"fork has collided!")
            self.suspend(r)
        # else:
        #     r.clearError(53000)  # 自动清除错误

        if args["operation"] == "zero":
            self.zero(r)
        elif args["operation"] == "lift":
            self.lift(r, args["liftHeight"])
        elif args["operation"] == "stretch":
            self.stretch(r, args["stretchLength"])
        elif args["operation"] == "load":
            self.load(r, args["liftHeight"], args["stretchLength"], args["reachHeight"])
        elif args["operation"] == "unload":
            self.unload(r, args["liftHeight"], args["stretchLength"], args["reachHeight"])
        else:
            r.setError(f"operation error: {args['operation']}")
            return MoveStatus.FAILED
        if not r.publishSpeed():
            r.setError(f"Failed to publish the current motor control scheme ")
            self.status = MoveStatus.FAILED
        self.state['status'] = self.status
        self.state['args'] = args
        self.state['has_goods'] = r.hasGoods()
        r.setInfo(json.dumps(self.state))
        r.clearWarning(57300)
        r.setNotice(f"{args['operation']} opt_step: {self.opt_step}")
        return self.status

    def zero(self, r):
        """
        叉车标零
        :param r:
        :return: MoveStatus
        """
        if r.hasGoods():
            r.setError(f"Forklift has goods, cannot zero")
            return MoveStatus.FAILED
        if not self.opt_step[0]:
            # 货叉收回
            self.opt_step[0] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
        if self.opt_step[0] and not self.opt_step[1]:
            # 升降归零
            self.opt_step[1] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[0] and self.opt_step[1]:
            self.status = MoveStatus.FINISHED
        zero_state = dict()
        zero_state['opt_name'] = "zero"
        zero_state['opt_status'] = self.status
        zero_state['actions'] = self.robot.state
        self.state['operation'] = zero_state

    def lift(self, r, lift_height):
        if r.hasGoods() and lift_height < self.safe_lift_height:
            r.setError(f"Fork has goods, cannot lift down lower than {self.safe_lift_height}")
            return MoveStatus.FAILED
        if not self.opt_step[0]:
            self.opt_step[0] = self.robot.lift(self.lift_motor, lift_height)
        else:
            self.status = MoveStatus.FINISHED
        lift_state = dict()
        lift_state['opt_name'] = "lift"
        lift_state['opt_status'] = self.status
        lift_state['actions'] = self.robot.state
        self.state['operation'] = lift_state
        r.logInfo(f"lift: {lift_state}")

    def stretch(self, r, stretch_length):
        if not self.opt_step[0]:
            self.opt_step[0] = self.robot.stretch(self.stretch_motor, stretch_length)
        else:
            self.status = MoveStatus.FINISHED
        stretch_state = dict()
        stretch_state['opt_name'] = "stretch"
        stretch_state['opt_status'] = self.status
        stretch_state['actions'] = self.robot.state
        self.state['operation'] = stretch_state
        r.logInfo(f"stretch: {stretch_state}")

    def load(self, r, lift_height, stretch_length, reach_height):
        if r.hasGoods():
            r.setError(f"Fork has goods, cannot load")
            return MoveStatus.FAILED
        if lift_height < self.safe_lift_height:
            lift_height = self.safe_lift_height
        if reach_height < self.safe_lift_height:
            reach_height = self.safe_lift_height
        if not self.opt_step[0]:
            # 叉车后移固定距离
            self.opt_step[0] = self.move(r, {'x': -self.move_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 1})
        if self.opt_step[0] and not self.opt_step[1]:
            # 货叉伸出, 货叉到位DI检测
            self.opt_step[1] = self.fork_reached(r) or self.robot.stretch(self.stretch_motor, stretch_length)
        if self.opt_step[1] and not self.opt_step[2]:
            # 货叉到位DI未触发
            if not self.fork_reached(r):
                r.setError(f"Fork reach DI not triggered, check please!")
            else:
                self.stretch_motor.reset()
            # 货叉上升
            self.opt_step[2] = self.robot.lift(self.lift_motor, lift_height)
        if self.opt_step[2] and not self.opt_step[3]:
            # 货叉收回
            self.opt_step[3] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
        if self.opt_step[3] and not self.opt_step[4]:
            # 叉车前移固定距离
            self.opt_step[4] = self.move(r, {'x': self.move_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 0})
        if self.opt_step[4] and not self.opt_step[5]:
            # 货叉升降到指定高度
            self.opt_step[5] = self.robot.lift(self.lift_motor, reach_height)
        if all(self.opt_step):
            r.setGoodsShape(0, 0, 0)
            self.status = MoveStatus.FINISHED
        load_state = dict()
        load_state['opt_name'] = "load"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        self.state['operation'] = load_state

    def unload(self, r, lift_height, stretch_length, reach_height):
        if lift_height < self.lift_zero:
            lift_height = self.lift_zero
        if reach_height < self.lift_zero:
            reach_height = self.lift_zero
        if not self.opt_step[0]:
            # 叉车后移固定距离
            self.opt_step[0] = self.move(r, {'x': -self.move_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 1})
        if self.opt_step[0] and not self.opt_step[1]:
            # 货叉伸出
            self.opt_step[1] = self.robot.stretch(self.stretch_motor, stretch_length)
        if self.opt_step[1] and not self.opt_step[2]:
            # 货叉下降到目标位置
            self.opt_step[2] = self.robot.lift(self.lift_motor, lift_height)
        if self.opt_step[2] and not self.opt_step[3]:
            # 货叉收回
            self.opt_step[3] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
        if self.opt_step[3] and not self.opt_step[4]:
            # 叉车前移固定距离
            self.opt_step[4] = self.move(r, {'x': self.move_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 0})
        if self.opt_step[4] and not self.opt_step[5]:
            # 货叉升降到指定高度
            self.opt_step[5] = self.robot.lift(self.lift_motor, reach_height)
        if all(self.opt_step):
            r.clearGoodsShape()
            self.status = MoveStatus.FINISHED
        unload_state = dict()
        unload_state['opt_name'] = "unload"
        unload_state['opt_status'] = self.status
        unload_state['actions'] = self.robot.state
        self.state['operation'] = unload_state

    def move(self, r, move_args) -> bool:
        if self.go_path.status != 3 or self.go_path.status != 4:
            self.go_path.run(r, move_args)
        if self.go_path.status == MoveStatus.FINISHED:
            self.go_path = goPath.Module(r, dict())
            return True
        return False

    def fork_collision(self, r: SimModule) -> bool:
        """
        货叉尖端DI碰撞检测
        :param r:
        :return: bool
        """
        DI = r.Di()
        nodes = DI.get('node', list())
        for node in nodes:
            if node['id'] == self.fork_peak_di1 or node['id'] == self.fork_peak_di2:
                if node['status']:
                    return True
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
            if node['id'] == self.reach_di1 or node['id'] == self.reach_di2:
                if node['status']:
                    return True
        return False

    def cancel(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("task cancel")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("task suspend")
        self.status = MoveStatus.SUSPENDED


class MotorType(enum.IntEnum):
    LINEAR_MOTOR = 0
    ROLLER_MOTOR = 1


class Motor:
    def __init__(self, r, motor_type: MotorType, motor_name: str, stop_di: int):
        self.motor_type = motor_type
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
        if self.motor_type == MotorType.LINEAR_MOTOR:
            self.r.setMotorPosition(self.motor_name, pos, max_vel, self.stop_di)
        elif self.motor_type == MotorType.ROLLER_MOTOR:
            self.r.setMotorSpeed(self.motor_name, vel, self.stop_di)
        else:
            self.r.setError(f"motor type error {self.motor_type}")
            self.status = MoveStatus.FAILED
        if self.r.isMotorReached(self.motor_name):
            self.status = MoveStatus.FINISHED
        self.state['motor_name'] = self.motor_name
        self.state['motor_type'] = self.motor_type
        self.state['motor_status'] = self.status

    def reset(self):
        self.r.logInfo(f"motor reset: {self.motor_name}")
        self.r.resetMotor(self.motor_name)
        self.status = MoveStatus.RUNNING

    def stop(self):
        self.r.isMotorStop(self.motor_name)
        self.status = MoveStatus.NONE


class Robot:
    def __init__(self, r):
        self.r = r
        self.reach_angle = 0.01           # 路径导航的到点角度精度
        self.reach_dist = 0.003            # 路径导航的到点精度
        self.state = dict()                       # 记录状态

    def move(self, x: float, y: float, theta=None, coordinate='robot', back_mode=False, max_speed=None) -> bool:
        """
        控制机器人移动
        :param x:
        :param y:
        :param theta:
        :param coordinate:
        :param back_mode:
        :param max_speed:
        :return: MoveStatus
        """
        move_state = dict()
        move_state['x'] = x
        move_state['y'] = y
        move_state['theta'] = theta
        move_state['coordinate'] = coordinate
        move_state['back_mode'] = back_mode
        move_state['max_speed'] = max_speed
        self.state['move'] = move_state
        self.r.resetPath()   # 让agv沿着规划的线路行驶
        self.r.setPathBackMode(back_mode)    # 设置是否倒走
        self.r.setPathReachDist(self.reach_dist)
        if theta is not None:
            self.r.setPathReachAngle(self.reach_angle)
        else:
            theta = 0
            self.r.setPathReachAngle(math.pi)
        if max_speed is not None:
            self.r.setPathMaxSpeed(float(max_speed))
        if coordinate == 'robot':
            self.r.setPathOnRobot([0, x], [0, y], float(theta))
        elif coordinate == 'world':
            loc = self.r.loc()
            self.r.setPathOnWorld([loc['x'], x], [loc['y'], y], float(theta))
        else:
            self.r.setError(f"coordinate param error!")
            return False
        if self.r.isPathReached():
            self.r.logInfo("move finish")
            self.r.stopRobot(False)
            return True
        self.r.goPath()
        return False

    def lift(self, motor: Motor, height: float, max_vel=0.2) -> bool:
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


    def stretch(self, motor: Motor, length: float, max_vel=0.2) -> bool:
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


if __name__ == '__main__':
    r = SimModule()
    robot = Robot(r)
    lift_motor = Motor(r, MotorType.LINEAR_MOTOR, "motor1", -1)
    robot.move(3, 0)
    robot.lift(lift_motor, 2)
    module = Module(r, {})
