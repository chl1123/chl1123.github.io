# -*- coding: utf-8 -*-
# @Time : 2021/11/29 13:42
# @Author : zhong
# @File : robot.py
# @Version : 1.0
"""
提供一些机构脚本常用的接口
"""
import enum
import os
import logging
import time
import goPath
from rbk import MoveStatus
from rbkSim import SimModule


class ModuleTool:
    """
    机构脚本工具接口类
    """
    start_time = None

    @staticmethod
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

    @staticmethod
    def check_DO(r: SimModule, do: int):
        """
        检测单个DO状态信息
        :param r: SimModule类对象
        :param do: 需要检测的 DO
        :return: 返回指定DO的状态，若DO不存在返回False
        """
        DO = r.Do()
        nodes = DO.get('node', list())
        for node in nodes:
            if node['id'] == do:
                return node['status']
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
    def get_motor_speed(r: SimModule, motor_name: str):
        """
        获取指定电机的当前速度
        :param r:
        :param motor_name:
        :return: 返回电机的当前速度，若电机不存在返回False
        """
        motors = r.navSpeed().get("motor_cmd", [])
        motor_speed = False
        for m in motors:
            if m['motor_name'] == motor_name:
                motor_speed = m.get('value', False)
        return motor_speed

    @staticmethod
    def delay(second):       # 延时 second 秒
        if ModuleTool.start_time is None:
            ModuleTool.start_time = time.time()
        if time.time() - ModuleTool.start_time > second:
            ModuleTool.start_time = None
            return True
        return False


class MotorType(enum.IntEnum):
    LINEAR_MOTOR = 0
    ROLLER_MOTOR = 1


class Log:
    """
    输出脚本日志
    """
    logger = logging.getLogger('script')

    @staticmethod
    def config_log(filepath: str):
        log_dir = os.path.dirname(filepath) + '/scripts-logs'
        # log_dir = "/usr/local/etc/.SeerRobotics/rbk/diagnosis/log/scripts-logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, mode=0o777)
        log_time = time.strftime("%Y-%m-%d")
        log_fmt = "%(name)s - %(asctime)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            filename=f"{log_dir}/scripts_log_{log_time}.log",
            format=log_fmt,
            level=logging.DEBUG
        )

    @staticmethod
    def new_dir(filepath: str, dirname: str):
        """
        在当前文件目录下生成指定文件夹
        :param dirname:
        :param filepath:
        :return:
        """
        new_dir = os.path.dirname(filepath) + '/' + dirname
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)


class Motor:
    def __init__(self, r, motor_type: MotorType, motor_name: str, stop_di: int):
        self.r = r
        self.motor_type = motor_type
        self.motor_name = motor_name
        self.stop_di = stop_di
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
        self.status = MoveStatus.RUNNING
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
        self.state['motor_pos'] = ModuleTool.get_motor_pos(self.r, self.motor_name)
        self.state['motor_speed'] = ModuleTool.get_motor_speed(self.r, self.motor_name)
        self.state['motor_status'] = self.status
        return self.status

    def reset(self):
        self.r.logInfo(f"motor reset: {self.motor_name}")
        self.r.resetMotor(self.motor_name)
        self.status = MoveStatus.RUNNING
        self.state['motor_status'] = self.status

    def stop(self):
        self.r.isMotorStop(self.motor_name)
        self.status = MoveStatus.NONE
        self.state['motor_status'] = self.status


class Robot:
    """
    实例化一个 AGV 对象，控制 AGV 移动和操作上层机构
    """
    def __init__(self, r):
        self.r = r
        self.reach_angle = 0.01           # 路径导航的到点角度精度
        self.reach_dist = 0.003            # 路径导航的到点精度
        self.state = dict()                       # 记录状态
        self.go_path = goPath.Module(r, dict())    # 控制AGV移动对象
        self.init = True
        self.loc = None

    def move(self, x: float, y: float, theta=0., coordinate='robot', back_mode=False, max_speed=0.3) -> bool:
        """
        控制机器人移动
        :param x: 坐标x值
        :param y:坐标y值
        :param theta: 世界坐标系下agv朝向，与x轴夹角弧度值
        :param coordinate: 坐标系
        :param back_mode: 是否倒走
        :param max_speed: 最大移动速度
        :return: bool 是否完成导航过程
        """
        if self.init:
            self.init = False
            self.loc = self.r.loc()
        try:
            x_dist = self.r.loc().get('x') - self.loc.get('x')
            y_dist = self.r.loc().get('y') - self.loc.get('y')
        except Exception as e:
            x_dist, y_dist = 0, 0
            self.r.logInfo(f"robot move error: {e}")
        move_args = dict()
        move_args['x'] = x
        move_args['y'] = y
        move_args['theta'] = theta
        move_args['useOdo'] = 1
        move_args['coordinate'] = coordinate
        move_args['backMode'] = back_mode
        move_args['maxSpeed'] = max_speed
        move_args['actualMoveDist'] = {
            'x': x_dist,
            'y': y_dist
        }
        self.state['move'] = move_args
        if self.go_path.status != MoveStatus.FAILED or self.go_path.status != MoveStatus.FINISHED:
            self.go_path.run(self.r, move_args)
        if self.go_path.status == MoveStatus.FINISHED:
            self.go_path.reset()
            return True
        return False

    def lift(self, motor: Motor, height: float, max_vel=0.3) -> bool:
        """
        控制升降电机
        :param motor:
        :param height:
        :param max_vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=float(height), max_vel=float(max_vel))
        return False


    def stretch(self, motor: Motor, length: float, max_vel=0.3) -> bool:
        """
        控制伸缩机构电机
        :param motor:
        :param length:
        :param max_vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=float(length), max_vel=float(max_vel))
        return False

    def roller(self, motor: Motor, vel) -> bool:
        """
        控制辊筒电机
        :param motor:
        :param vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
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

    def jack(self, motor: Motor, height: float, max_vel=0.3):
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            # motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=height, max_vel=max_vel)
        return False



if __name__ == "__main__":
    log_dir = os.getcwd() + "/scripts-logs"
    print("log_dir: ", log_dir)
    liner_motor = Motor(SimModule(), MotorType.LINEAR_MOTOR, "motor1", -1)
    roller_motor = Motor(SimModule(), MotorType.ROLLER_MOTOR, "motor2", -1)
    robot = Robot(SimModule())
    robot.move(1, 0)
    robot.lift(liner_motor, 1)
    robot.stretch(liner_motor, 1)
    robot.roller(roller_motor, 1)
    Log.config_log(log_dir)
    Log.logger.info(robot.state)
    Log.logger.critical(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    Log.logger.error(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    Log.logger.warning(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    Log.logger.info(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    Log.logger.debug(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
