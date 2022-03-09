# -*- coding: utf-8 -*-
# @Time : 2022/3/1 21:10
# @Author : zhong
# @File :SFL-R16S.py
# @Request : test_center#964 SFL-R16S叉车脚本
# @Version: 1.2
import enum
import json
import math
import sys
import time

sys.path.append("syspy")
import syspy.goPath as goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer

"""
####BEGIN DEFAULT ARGS####
{
   "operation":{
        "value": "zero",
        "default_value":["zero","load","unload", "lift", "stretch"],
        "tips": "操作",
        "type": "complex"        
    },    
    "stretchLength": {
        "value": 0.528,
        "tips": "货叉伸出长度",
        "type": "float",
        "unit": "m"
    },
    "liftHeight": {
        "value": 0.8,
        "tips": "货叉升降高度",
        "type": "float",
        "unit": "m"
    },
    "reachHeight": {
        "value": 0.4,
        "tips": "取放货后货叉到位高度",
        "type": "float",
        "unit": "m"
    },
    "recFile": {
        "value": "p0001.pallet",
        "tips": "识别文件, 带识别加此参数",
        "type": "string"
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
        self.max_stretch_length = p.loadParam("MaxStretchLength", type="float", default=0.79, comment="最大伸出长度")
        self.max_lift_height = p.loadParam("MaxLiftHeight", type="float", default=1.6, comment="最大升降高度")
        self.reach_di = p.loadParam("ReachDI", type="int", default=1, comment="货叉到位检测DI")
        self.fork_peak_di1 = p.loadParam("ForkPeakDI1", type="int", default=2, comment="货叉尖端检测DI1")
        self.fork_peak_di2 = p.loadParam("ForkPeakDI2", type="int", default=4, comment="货叉尖端检测DI2")
        self.lift_zero = p.loadParam("LiftZero", type="float", default=0.079, comment="货叉升降零位")
        self.stretch_zero = p.loadParam("StretchZero", type="float", default=0.035, comment="货叉伸缩零位")
        # 定义四个电机的名称
        self.lift_motor_name = p.loadParam("LiftMotorName", type="str", default="motor2", comment="货叉升降电机名称")
        self.stretch_motor_name = p.loadParam("StretchMotorName", type="str", default="qianhouyi", comment="货叉伸缩电机名称")
        self.tilt_motor_name = p.loadParam("TiltMotorName", type="str", default="qianhouqing", comment="货叉倾斜电机名称")
        self.leftRight_motor_name = p.loadParam("LiftRightMotor", type="str", default="zuoyouyi", comment="货叉左右移动电机名称")
        
        self.fork_di_dist = p.loadParam("ForkDiDist", type="float", default=0.1, comment="货叉到位DI补足距离")
        self.laser_valid_height = p.loadParam("EnableHeight", type="float", default=0.25, comment="后视激光有效高度")
        self.tilt_time = p.loadParam("TiltTime", type="float", default=3, comment="控制倾斜电机运转的时间，单位：秒")
        self.fork_center_pos = p.loadParam("ForkCenterPos", type="float", default=3, comment="货叉模型质点相对齿尖的位置，单位：米")
        r.logInfo(f"__init__ args: {args}")

        self.state = dict()
        self.status = MoveStatus.NONE

        self.init = True
        
        self.go_path = goPath.Module(r, dict())
        
        self.robot = Robot(r)

        self.lift_motor = None
        self.stretch_motor = None

        self.opt_step = [False] * 6
        self.agv_loc_x = None
        self.actual_move_dist = 0
        self.actual_stretch_length = 0
        self.twice_move = False
        self.lift_height = self.lift_zero
        self.reach_height = self.lift_zero
        self.stretch_length = self.stretch_zero
        self.init_lift_motor_pos = None #升降电机的初始位置
        self.init_stretch_motor_pos = None #伸缩电机的初始位置
        self.tilt_motor = None
        self.tilt_start = None
        self.tilt_finish = False
        self.rec_file = None
        self.rec = None

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.agv_loc_x = r.loc().get('x')
            self.lift_motor = Motor(r, MotorType.LINEAR_MOTOR, self.lift_motor_name, -1)
            self.stretch_motor = Motor(r, MotorType.LINEAR_MOTOR, self.stretch_motor_name, -1)
            self.tilt_motor = Motor(r, MotorType.ROLLER_MOTOR, self.tilt_motor_name, -1)
            # r.initForkCollisionCheck()   # 初始化后视激光检测
            args_error = False
            # 获取升降电机和伸缩电机的初始位置
            if self.get_motor_pos(r, self.lift_motor_name) is not False:
                self.init_lift_motor_pos = self.get_motor_pos(r, self.lift_motor_name)
            if self.get_motor_pos(r, self.stretch_motor_name) is not False:
                self.init_stretch_motor_pos = self.get_motor_pos(r, self.stretch_motor_name)
            self.rec_file = args.get("recFile", None)  # 识别文件
            if self.rec_file is not None:
                self.rec = RecAdjust(r, self.rec_file)

            if "operation" in args:  # 参数检查
                if "stretchLength" in args:
                    self.stretch_length = args["stretchLength"]
                    if args["stretchLength"] > self.max_stretch_length:
                        r.setError(f"Out of max stretch length {self.max_stretch_length}")
                        args_error = True
                    elif args["stretchLength"] < self.stretch_zero:
                        self.stretch_length = self.stretch_zero
                if "liftHeight" in args:
                    self.lift_height = args["liftHeight"]
                    if args["liftHeight"] > self.max_lift_height:
                        r.setError(f"Out of max lift height {self.max_lift_height}")
                        args_error = True
                    elif args["liftHeight"] < self.lift_zero:
                        self.lift_height = self.lift_zero
                if "reachHeight" in args:
                    self.reach_height = args["reachHeight"]
                    if args["reachHeight"] > self.max_lift_height:
                        r.setError(f"Out of max lift height {self.max_lift_height}")
                        args_error = True
                    elif args["reachHeight"] < self.lift_zero:
                        self.reach_height = self.lift_zero
                if args["operation"] == "zero":
                    if r.hasGoods():
                        r.setError(f"Forklift has goods, cannot zero")
                        args_error = True
                elif args["operation"] == "lift" and "liftHeight" in args:
                    if r.hasGoods() and args["liftHeight"] < self.safe_lift_height:
                        r.setError(f"Fork has goods, cannot lift down lower than safe height, {args}")
                        args_error = True
                elif args["operation"] == "stretch" and "stretchLength" in args:
                    pass
                elif args["operation"] == "load" and "stretchLength" in args and "liftHeight" in args and "reachHeight" in args:
                    # load时检查升降高度参数合理性
                    if args["liftHeight"] < self.init_lift_motor_pos:
                        r.setError(f"load liftHeight lower than current lift height {self.init_lift_motor_pos}")
                        args_error = True
                    if r.hasGoods():
                        r.setError(f"Fork has goods, cannot load")
                        args_error = True
                elif args["operation"] == "unload" and "stretchLength" in args and "liftHeight" in args and "reachHeight" in args:
                    # unload时检查升降高度参数合理性
                    if args["liftHeight"] > self.init_lift_motor_pos:
                        r.setError(f"unload liftHeight higher than current lift height {self.init_lift_motor_pos}")
                        args_error = True
                    if args["stretchLength"] < self.max_stretch_length and args["liftHeight"] < self.safe_lift_height:
                        r.setError(f"Not stretch to the max length,  cannot lift lower than the safe lift height.")
                        args_error = True
                else:
                    args_error = True
            else:
                args_error = True
            if args_error:
                if not r.errorExits(53000):
                    if len(args.keys()) < 1:
                        r.setError(f"args is empty!")
                    else:
                        r.setError(f"args error: {args}")
                return MoveStatus.FAILED

        if args["operation"] == "zero":
            self.zero(r)
        elif args["operation"] == "lift":
            self.lift(r)
        elif args["operation"] == "stretch":
            self.stretch(r)
        elif args["operation"] == "load":
            if self.rec is not None:  # 识别栈板，调整位置
                if self.rec.status == MoveStatus.FINISHED:
                    self.load(r)
                else:
                    self.rec.run(r)
            else:
                self.load(r)
        elif args["operation"] == "unload":
            self.unload(r)
        else:
            r.setError(f"operation error: {args['operation']}")
            self.status = MoveStatus.FAILED
        if not r.publishSpeed():
            r.setError(f"Failed to publish the current motor control scheme ")
            self.status = MoveStatus.FAILED
        self.state['status'] = self.status
        self.state['args'] = args
        if self.rec is not None:
            self.state['rec'] = self.rec.state
        self.state['has_goods'] = r.hasGoods()
        r.setInfo(json.dumps(self.state))
        r.logInfo("SFLState][{}".format(json.dumps(self.state)))
        r.setNotice(f"step: {self.opt_step}")
        return self.status

    def zero(self, r):
        """
        叉车标零
        :param r:
        :return: MoveStatus
        """
        if not self.opt_step[0]:
            self.opt_step[0] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
        if self.opt_step[0] and not self.opt_step[1]:
            # 检查后视激光
            if not self.back_laser_check(r):
                self.opt_step[1] = self.robot.lift(self.lift_motor, self.lift_zero)
        if self.opt_step[0] and self.opt_step[1]:
            self.status = MoveStatus.FINISHED
        zero_state = dict()
        zero_state['opt_name'] = "zero"
        zero_state['opt_status'] = self.status
        zero_state['actions'] = self.robot.state
        self.state['operation'] = zero_state

    def lift(self, r):
        is_finished = False
        if self.lift_height < self.init_lift_motor_pos:  # 货叉下降
            if not self.back_laser_check(r):  # 检查后视激光
                is_finished = self.robot.lift(self.lift_motor, self.lift_height)
            else:
                # TODO 报错
                pass
        else:  # 货叉上升
            is_finished = self.robot.lift(self.lift_motor, self.lift_height)
        if is_finished:
            self.status = MoveStatus.FINISHED
        lift_state = dict()
        lift_state['opt_name'] = "lift"
        lift_state['is_finished'] = is_finished
        lift_state['actions'] = self.robot.state
        self.state['operation'] = lift_state

    def stretch(self, r):
        if not self.opt_step[0]:
            if self.stretch_length > self.stretch_zero:  # 货叉伸出
                if not self.fork_collision(r) and not self.back_laser_check(r):
                    self.opt_step[0] = self.robot.stretch(self.stretch_motor, self.stretch_length)
            else:  # 货叉收回
                self.opt_step[0] = self.robot.stretch(self.stretch_motor, self.stretch_length)
        else:
            self.status = MoveStatus.FINISHED
        stretch_state = dict()
        stretch_state['opt_name'] = "stretch"
        stretch_state['opt_status'] = self.status
        stretch_state['actions'] = self.robot.state
        self.state['operation'] = stretch_state
        r.logInfo(f"stretch: {stretch_state}")

    def load(self, r):
        if self.lift_height < self.safe_lift_height:
            self.lift_height = self.safe_lift_height
        if self.reach_height < self.safe_lift_height:
            self.reach_height = self.safe_lift_height
        # Step0 货叉伸出, 检测到位DI
        if not self.opt_step[0]:
            if not self.fork_collision(r) and not self.back_laser_check(r):
                self.opt_step[0] = self.fork_reached(r) or self.robot.stretch(self.stretch_motor, self.stretch_length)
                self.actual_stretch_length = self.get_motor_pos(r, self.stretch_motor_name)  # 计算货叉实际伸出长度
            if self.opt_step[0]:
                self.stretch_motor.reset()

        # Step1 叉车后移固定距离
        if self.opt_step[0] and not self.opt_step[1]:
            if not self.fork_collision(r) and not self.back_laser_check(r):
                self.opt_step[1] = self.fork_reached(r) and self.move(r, {'x': -self.move_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 1})
                self.actual_move_dist = abs(r.loc().get("x") - self.agv_loc_x)  # 计算实际移动距离
            if self.opt_step[1]:
                self.go_path.reset()
                if self.fork_di_dist > 0 and self.actual_move_dist < (self.move_dist - self.fork_di_dist):
                    r.setError(f"Error! Fork reach DI has been wrong triggered ")
                    self.status = MoveStatus.FAILED

        # Step2 货叉上升
        if self.opt_step[1] and not self.opt_step[2]:
            if self.twice_move and not self.fork_reached(r):
                r.setError(f"Fork reach DI not triggered, check please!")
                self.status = MoveStatus.FAILED
            if not self.fork_reached(r) and self.reach_di != -1:  # 货叉到位DI 已配置且未触发
                if self.fork_di_dist > 0 and not self.twice_move:
                    self.twice_move = self.fork_reached(r) or self.move(r, {'x': -self.fork_di_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 1})  # 二次后移
                    self.actual_move_dist = abs(r.loc().get("x") - self.agv_loc_x)
                else:
                    r.setError(f"Fork reach DI not triggered, check please!")
                    self.status = MoveStatus.FAILED
            else:  # 到位 DI 已触发
                self.go_path.reset()
                self.opt_step[2] = self.robot.lift(self.lift_motor, self.lift_height)

        # Step3 货叉收回
        if self.opt_step[2] and not self.opt_step[3]:
            if not self.tilt_finish:  # 货叉倾斜动作未完成
                if self.tilt_start is None:
                    self.tilt_start = time.time()
                else:
                    self.robot.tilt(self.tilt_motor, -0.3)
                    if time.time() - self.tilt_start > self.tilt_time:
                        self.tilt_finish = True
            else:
                self.opt_step[3] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
            self.lost_goods_check(r)  # 掉货检测

        # Step4 叉车前移固定距离
        if self.opt_step[3] and not self.opt_step[4]:
            self.opt_step[4] = self.move(r, {'x': self.actual_move_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 0})
            self.lost_goods_check(r)  # 掉货检测

        # Step5 货叉升降到指定的安全高度
        if self.opt_step[4] and not self.opt_step[5]:
            if self.reach_height < self.get_motor_pos(r, self.lift_motor_name):
                self.back_laser_check(r)
            self.opt_step[5] = self.robot.lift(self.lift_motor, self.reach_height)
            self.lost_goods_check(r)  # 掉货检测

        if all(self.opt_step):
            r.setGoodsShape(0, 0, 0)
            self.status = MoveStatus.FINISHED
        load_state = dict()
        load_state['opt_name'] = "load"
        load_state['opt_status'] = self.status
        load_state['actions'] = self.robot.state
        load_state['reach_di'] = self.fork_reached(r)
        load_state['actual_move_dist'] = self.actual_move_dist
        load_state['actual_stretch_length'] = self.actual_stretch_length
        self.state['operation'] = load_state

    def unload(self, r):
        # Step0 叉车后移固定距离
        if not self.opt_step[0]:
            if not self.fork_collision(r) and not self.back_laser_check(r):
                self.opt_step[0] = self.move(r, {'x': -self.move_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 1})
                self.actual_move_dist = abs(r.loc().get("x") - self.agv_loc_x)
        # Step1 货叉伸出
        if self.opt_step[0] and not self.opt_step[1]:
            if not self.fork_collision(r) and not self.back_laser_check(r):
                self.opt_step[1] = self.robot.stretch(self.stretch_motor, self.stretch_length)
                self.actual_stretch_length = self.get_motor_pos(r, self.stretch_motor_name)
        # Step2 货叉下降到目标位置
        if self.opt_step[1] and not self.opt_step[2]:
            if not self.tilt_finish:  # 货叉倾斜动作未完成
                if self.tilt_start is None:
                    self.tilt_start = time.time()
                else:
                    self.robot.tilt(self.tilt_motor, 0.3)
                    if time.time() - self.tilt_start > self.tilt_time:
                        self.tilt_finish = True
            else:
                self.opt_step[2] = self.robot.lift(self.lift_motor, self.lift_height)
        # Step3 货叉收回
        if self.opt_step[2] and not self.opt_step[3]:
            self.opt_step[3] = self.robot.stretch(self.stretch_motor, self.stretch_zero)
        # Step4 叉车前移固定距离
        if self.opt_step[3] and not self.opt_step[4]:
            self.opt_step[4] = self.move(r, {'x': self.move_dist, 'y': 0, 'coordinate': 'robot', 'backMode': 0})
        # Step5 货叉升降到指定高度
        if self.opt_step[4] and not self.opt_step[5]:
            if self.reach_height < self.get_motor_pos(r, self.lift_motor_name):
                self.back_laser_check(r)
            self.opt_step[5] = self.robot.lift(self.lift_motor, self.reach_height)
        if all(self.opt_step):
            r.clearGoodsShape()
            self.status = MoveStatus.FINISHED
        unload_state = dict()
        unload_state['opt_name'] = "unload"
        unload_state['opt_status'] = self.status
        unload_state['actions'] = self.robot.state
        unload_state['actual_move_dist'] = self.actual_move_dist
        unload_state['actual_stretch_length'] = self.actual_stretch_length
        self.state['operation'] = unload_state

    def move(self, r, move_args) -> bool:
        r.logDebug(f"move args: {move_args}")
        if self.go_path.status != 3 or self.go_path.status != 4:
            self.go_path.run(r, move_args)
        if self.go_path.status == MoveStatus.FINISHED:
            self.go_path.reset()
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
                    r.setError(f"fork has collided!")
                    self.suspend(r)
                    return True
        return False

    def back_laser_check(self, r: SimModule) -> bool:
        """
        后视激光检测, 有阻挡会自动报错52200，需先调用一次initForkCollisionCheck
        :param r:
        :return:
        """
        # if self.get_motor_pos(r, self.lift_motor_name) > self.laser_valid_height:
        #     if r.forkCollisionCheck():
        #         r.setError(f"back laser block!")
        #         self.suspend(r)
        #         return True
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
                    return True
        return False

    def lost_goods_check(self, r):
        """
        掉货检测
        :param r:
        :return:
        """
        if not self.fork_reached(r) and self.reach_di != -1:
            r.setError(f"Goods maybe lost, check please!")
            self.status = MoveStatus.FAILED

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

    def cancel(self, r: SimModule):
        r.stopRobot(True)
        r.logInfo("task cancel")
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.stopRobot(True)
        self.lift_motor.stop()
        self.stretch_motor.stop()
        self.lift_motor.reset()
        self.stretch_motor.reset()
        r.logInfo("task suspend")
        self.status = MoveStatus.SUSPENDED


class RecAdjust:
    def __init__(self, r, file):
        self.file = file
        self.status = MoveStatus.NONE
        self.rec_failed_time = 0
        self.max_rec_time = 20
        self.adjust_count = 0
        self.max_adjust_times = 10
        self.go_path = goPath.Module(r, dict())
        self.move_args = dict()
        self.state = dict()

    def run(self, r):
        self.status = MoveStatus.RUNNING
        rec_result = self.rec_file(r, self.file)
        if rec_result:  # 成功获取识别结果
            # r.resetRec()           # 重置识别模块
            if self.go_path.status == MoveStatus.NONE:
                self.go_path.status = MoveStatus.RUNNING
                pos2world = [rec_result['x'], rec_result['y'], rec_result['yaw']]  # 目标点在世界坐标系的位置
                robot2world = [r.loc()['x'], r.loc()['y'], r.loc()['angle']]  # 小车在世界坐标系的位置
                pos2robot = Pos2Base(pos2world, robot2world)  # 目标点相对小车的位置
                if abs(pos2robot[0]) < 0.005:  # 目标点相对小车的位置小于阈值时，识别调整完成
                    self.status = MoveStatus.FINISHED
                    return True
                self.move_args['coordinate'] = 'robot'
                self.move_args['x'] = pos2robot[0]
                self.move_args['y'] = 0
                self.move_args['theta'] = 0
                self.move_args['reachAngle'] = math.pi
                self.move_args['useOdo'] = 1
                self.move_args['reachDist'] = 0.003
                if self.move_args["x"] < 0:
                    self.move_args["backMode"] = 1
            elif self.go_path.status == MoveStatus.RUNNING:
                self.go_path.run(r, self.move_args)
            elif self.go_path.status == MoveStatus.FINISHED:
                self.adjust_count = self.adjust_count + 1
                self.go_path.reset()
                r.resetRec()
                self.rec_failed_time = 0
                if self.adjust_count > self.max_adjust_times:
                    r.setError(f"rec adjust failed the max times")
                    self.status = MoveStatus.FAILED
            elif self.go_path.status == MoveStatus.FAILED:
                r.setWarning(f"adjust failed, {self.move_args}")
                self.status = MoveStatus.FAILED
        else:  # 识别失败
            self.rec_failed_time += 1
            if self.rec_failed_time > self.max_rec_time:
                r.setError(f"rec failed the max times, {rec_result}")
                self.status = MoveStatus.FAILED
        self.state['rec_result'] = rec_result
        self.state['rec_file'] = self.file
        self.state['rec_adjust'] = self.status

    def reset(self, r):
        self.status = MoveStatus.RUNNING
        self.rec_failed_time = 0
        self.adjust_count = 0
        self.go_path.reset()

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


def normalize_theta(theta):
    if -math.pi <= theta < math.pi:
        return theta
    multiplier = math.floor(theta / (2 * math.pi))
    theta = theta - multiplier * 2 * math.pi
    if theta >= math.pi:
        theta = theta - 2 * math.pi
    if theta < -math.pi:
        theta = theta + 2 * math.pi
    return theta


def Pos2Base(pos2world, base2world):
    """将基于世界坐标系的两个位姿，转换为基于base的位姿
            Args:
                pos2world ([3]): 被转换的位姿，基于世界坐标系,0:x, 1:y, 2: theta
                base2world ([3]): 基准，基于世界坐标系,0:x, 1:y, 2: theta
            Returns:
                [3]: pos2base
            """
    pos2base = [0., 0., 0.]
    x = pos2world[0] - base2world[0]
    y = pos2world[1] - base2world[1]
    pos2base[0] = x * math.cos(base2world[2]) + y * math.sin(base2world[2])
    pos2base[1] = -x * math.sin(base2world[2]) + y * math.cos(base2world[2])
    pos2base[2] = normalize_theta(pos2world[2] - base2world[2])
    return pos2base


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
            self.r.resetMotor(self.motor_name)
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
        self.reach_angle = 0.01  # 路径导航的到点角度精度
        self.reach_dist = 0.003  # 路径导航的到点精度
        self.state = dict()  # 记录状态
        self.go_path = goPath.Module(r, dict())  # 控制AGV移动对象

    def move(self, x: float, y: float, theta=0., coordinate='robot', back_mode=False, max_speed=0.3) -> bool:
        """
        控制机器人移动
        :param x:
        :param y:
        :param theta:
        :param coordinate:
        :param back_mode:
        :param max_speed:
        :return: bool
        """
        move_args = dict()
        move_args['x'] = x
        move_args['y'] = y
        move_args['theta'] = theta
        move_args['coordinate'] = coordinate
        move_args['backMode'] = back_mode
        move_args['maxSpeed'] = max_speed
        self.state['move'] = move_args
        if self.go_path.status != MoveStatus.FAILED or self.go_path.status != MoveStatus.FINISHED:
            self.go_path.run(self.r, move_args)
        if self.go_path.status == MoveStatus.FINISHED:
            self.go_path.reset()
            return True
        return False

    def lift(self, motor: Motor, height: float, max_vel=0.5) -> bool:
        """
        控制升降电机
        :param motor:
        :param height:
        :param max_vel:
        :return: true 任务完成， false 任务没有完成
        """
        self.state[motor.motor_name] = motor.state
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

    def stretch(self, motor: Motor, length: float, max_vel=0.5) -> bool:
        """
        控制伸缩机构电机
        :param motor:
        :param length:
        :param max_vel:
        :return:
        """
        self.state[motor.motor_name] = motor.state
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

    def tilt(self, motor: Motor, vel=0.3):
        """
        控制倾斜机构电机
        :param motor:
        :param vel:
        :return:
        """
        self.state[motor.motor_name] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(vel=vel)
        return False


if __name__ == '__main__':
    r = SimModule()
    robot = Robot(r)
    lift_motor = Motor(r, MotorType.LINEAR_MOTOR, "motor1", -1)
    robot.move(3, 0)
    robot.lift(lift_motor, 2)
    module = Module(r, {})
    module.run(r,{})
