# -*- coding: utf-8 -*-
# @Time : 2022/11/22
# @Author : zhong
# @File : robot.py
# @Version : 1.6
"""
提供一些机构脚本常用的接口
"""
import enum
import json
import os
import logging
import time
import uuid
import requests
from logging.handlers import TimedRotatingFileHandler
from requests.exceptions import ReadTimeout, ConnectTimeout, ConnectionError
from concurrent.futures import ThreadPoolExecutor
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
        :return: 返回电机的当前位置，若电机不存在返回 -1
        """
        motors = r.odo().get("motor_info", [])
        motor_pos = -1
        for m in motors:
            if m['motor_name'] == motor_name:
                motor_pos = m.get('position', -1)
        return motor_pos

    @staticmethod
    def get_motor_speed(r: SimModule, motor_name: str):
        """
        获取指定电机的当前速度
        :param r:
        :param motor_name:
        :return: 返回电机的当前速度，若电机不存在返回 -1
        """
        motors = r.navSpeed().get("motor_cmd", [])
        motor_speed = -1
        for m in motors:
            if m['motor_name'] == motor_name:
                motor_speed = m.get('value', -1)
        return motor_speed

    @staticmethod
    def get_uuid():
        return uuid.uuid4().hex

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

    @staticmethod
    def script_running_counter(r: SimModule):
        return r.getCount()

    @staticmethod
    def get_now_date():
        return time.strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def clear_all_warnings(r: SimModule):
        """
        清除所有机构脚本相关的告警提示
        @param r:
        @return:
        """
        r.clearNotice(57019)
        r.clearNotice(57300)
        r.clearWarning(55300)
        r.clearError(53000)
        for code in range(53900, 54000):
            r.clearError(code)
        for code in range(55900, 56000):
            r.clearWarning(code)


def get_value_by_key(data: dict, key):
    """深度遍历解析字典数据，获取指定 key 对应的 value 值，如果 key 不存在，则返回 None
    :param data: 字典数据
    :param key: str
    :return:
    """
    for k in data.keys():
        # print("data:", data, "cur_key:", k)
        if k == key:
            return data[k]
        else:
            if isinstance(data[k], dict):
                result = get_value_by_key(data[k], key)
                if result is not None:
                    return result


class NetHandle:
    """提供HTTP协议的GET请求和POST请求接口 """

    def __init__(self):
        self.headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        self.status = MoveStatus.NONE

    def http_get(self, r: SimModule, url, params=None, data=None, timeout=(0.1, 0.3)):
        try:
            res = requests.get(url, headers=self.headers, params=params, data=data, timeout=timeout)
        except ConnectTimeout:
            r.logInfo(f'ConnectTimeout timeout, func: http_get: {url}')
        except ReadTimeout:
            r.logInfo(f'ReadTimeout, func: http_get: {url}')
        except ConnectionError as e:
            r.logInfo(f"ConnectionError {e}:{url}")
        except Exception as e:
            r.logInfo(f"Exception: {e}")
        else:
            r.logInfo(f"conn success: {url}, res code: {res.status_code}, res text: {res.text}")
            res.close()
            return res

    def http_post(self, r: SimModule, url, data=None, timeout=(0.1, 0.3)):
        """
        发送一次POST请求， 请求成功返回 response 的 json 数据
        :param r: SimModule
        :param url:
        :param data:
        :param timeout:
        :return: json
        """
        try:
            res = requests.post(url, json=data, headers=self.headers, timeout=timeout)
        except ConnectTimeout:
            r.logInfo(f"ConnectTimeout, func: http_post: {url}")
        except ReadTimeout:
            r.logInfo(f'ReadTimeout, func: http_post: {url}')
        except ConnectionError as e:
            r.logInfo(f"ConnectionError {e}:{url}")
        except Exception as e:
            r.logInfo(f"Exception: {e}")
        else:
            r.logInfo(f"conn success: {url}, res code: {res.status_code}, res text: {res.text}")
            res.close()
            return res

    @staticmethod
    def call_terminal(r: SimModule, url, data):
        """
        与终端设备交互, 使用 Core 的 callTerminal 接口
        :param r:
        :param url: "http:// Core IP:8088/callTerminal"
        :param data: json data
        :return: 成功则返回响应数据，失败返回 None
        """
        try:
            res = requests.post(url, json=data, timeout=(0.2, 0.5))
        except Exception as e:
            r.logInfo(f"post failed!!! url: {url}, data: {data}, error: {e}")
            return None
        else:
            if res.status_code == 200:
                return res.json()
            else:
                r.setWarning(f"res code: {res.status_code}, res: {res.text}")
                return None

    def ahttp_get(self, r):
        pass

    def ahttp_post(self, r):
        pass

    @staticmethod
    def post(seq, url, data=None, timeout=(0.1, 0.3)):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        re = NetHandle.requests.get(seq, None)
        if re is not None and re.get("status", "") == "success":
            result = dict()
            result["result"] = re.get('result')
            result["error"] = re.get("error")
            return result
        elif re is not None:
            return False
        else:
            dic = dict()
            dic['seq'] = seq
            dic['method'] = 'post'
            dic['url'] = url
            dic['json'] = data
            dic['timeout'] = timeout
            dic['status'] = 'request'
            dic['headers'] = headers
            NetHandle.requests[seq] = dic
            NetHandle.theard_pool.submit(NetHandle.request, dic)
            return False
        pass

    @staticmethod
    def get(seq, url, params=None, data=None, timeout=(0.1, 0.3)):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        re = NetHandle.requests.get(seq, None)
        if re is not None and re.get('status') == "success":
            result = dict()
            result["result"] = re.get('result')
            result["error"] = re.get("error")
            return result
        elif re is not None:
            return False
        else:
            dic = dict()
            dic['seq'] = seq
            dic['method'] = 'get'
            dic['url'] = url
            dic['params'] = params
            dic['data'] = data
            dic['timeout'] = timeout
            dic['status'] = 'request'
            dic['headers'] = headers
            NetHandle.requests[seq] = dic
            NetHandle.theard_pool.submit(NetHandle.request, dic)
            return False
        pass

    theard_pool = ThreadPoolExecutor(max_workers=2)
    requests = dict()

    @staticmethod
    def request(r: dict):
        if r.get('method') == 'get':
            try:
                res = requests.get(r.get('url'), headers=r.get("headers"), params=r.get("params", {}),
                                   data=r.get("data", {}), timeout=r.get("timeout"))
                try:
                    r['result'] = res.json()
                except:
                    # 处理返回值不是json的情况
                    r['result'] = res.text
                finally:
                    res.close()
            except Exception as e:
                r['error'] = e
                pass
            finally:
                # res.close()
                r['status'] = 'success'
                pass
            pass
        elif r.get('method') == 'post':
            try:
                res = requests.post(r.get('url'), json=r.get('json'), headers=r.get('headers'),
                                    timeout=r.get("timeout"))
                print(r)
                try:
                    r['result'] = res.json()
                except:
                    # 处理返回值不是json的情况
                    r['result'] = res.text
                finally:
                    res.close()
            except Exception as e:
                r['error'] = e
                pass
            finally:
                # res.close()
                r['status'] = 'success'
                pass
            pass
        pass


class MotorType(enum.IntEnum):
    LINEAR_MOTOR = 0
    ROLLER_MOTOR = 1


class Log:
    """兼容旧版本Log"""

    def __init__(self, filename, level=logging.INFO, when='H', interval=6, backupCount=30):
        log_dir = os.getcwd() + "/scripts-logs/"
        os.makedirs(log_dir, exist_ok=True)
        log_format = logging.Formatter('%(asctime)s - %(module)s - %(levelname)s: %(message)s')
        stream_handle = logging.StreamHandler()
        file_handle = TimedRotatingFileHandler(filename=log_dir + filename, when=when, interval=interval,
                                               backupCount=backupCount, encoding='utf-8')
        file_handle.setFormatter(log_format)
        if when == 'S':
            file_handle.suffix = "%Y-%m-%d_%H-%M-%S.log"
        elif when == 'M':
            file_handle.suffix = "%Y-%m-%d_%H-%M.log"
        elif when == 'H':
            file_handle.suffix = "%Y-%m-%d_%H.log"
        elif when == 'D' or when == 'MIDNIGHT':
            file_handle.suffix = "%Y-%m-%d.log"
        self.logger = logging.getLogger(filename)
        self.logger.setLevel(level)
        self.logger.addHandler(stream_handle)
        self.logger.addHandler(file_handle)


class ScriptLog:
    """输出脚本日志"""

    def __init__(self, filename, level=logging.INFO, when='H', interval=6, backupCount=30):
        log_dir = os.getcwd() + "/scripts-logs/"
        os.makedirs(log_dir, exist_ok=True)
        log_format = logging.Formatter('%(asctime)s - %(module)s - %(levelname)s: %(message)s')
        stream_handle = logging.StreamHandler()
        file_handle = TimedRotatingFileHandler(filename=log_dir + filename, when=when, interval=interval,
                                               backupCount=backupCount, encoding='utf-8')
        file_handle.setFormatter(log_format)
        if when == 'S':
            file_handle.suffix = "%Y-%m-%d_%H-%M-%S.log"
        elif when == 'M':
            file_handle.suffix = "%Y-%m-%d_%H-%M.log"
        elif when == 'H':
            file_handle.suffix = "%Y-%m-%d_%H.log"
        elif when == 'D' or when == 'MIDNIGHT':
            file_handle.suffix = "%Y-%m-%d.log"
        self.logger = logging.getLogger(filename)
        self.logger.setLevel(level)
        self.logger.addHandler(stream_handle)
        self.logger.addHandler(file_handle)


class Motor:
    def __init__(self, r, motor_type: MotorType, motor_name: str, stop_di: int = -1):
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
        self.r.publishSpeed()
        self.state['motor_name'] = self.motor_name
        self.state['motor_type'] = self.motor_type
        self.state['motor_pos'] = ModuleTool.get_motor_pos(self.r, self.motor_name)
        self.state['motor_speed'] = ModuleTool.get_motor_speed(self.r, self.motor_name)
        self.state['motor_status'] = self.status

    def reset(self):
        self.r.logInfo(f"motor reset: {self.motor_name}")
        self.r.resetMotor(self.motor_name)
        self.status = MoveStatus.RUNNING
        # self.state['motor_status'] = self.status

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
        self.reach_angle = 0.01  # 路径导航的到点角度精度
        self.reach_dist = 0.003  # 路径导航的到点精度
        self.state = dict()  # 记录机器人状态
        self.go_path = goPath.Module(r, dict())  # 控制AGV移动对象
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
            x_dist = self.r.loc().get('x', 0) - self.loc.get('x', 0)
            y_dist = self.r.loc().get('y', 0) - self.loc.get('y', 0)
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

    def lift_door(self, motor: Motor, height: float, max_vel=0.3) -> bool:
        """
        料箱车门架电机
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

    def rotate(self, motor: Motor, length: float, max_vel=0.3) -> bool:
        """
        控制旋转机构电机
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
        """
        控制顶升电机
        :param motor:
        :param height:
        :param max_vel:
        :return:
        """
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            # motor.reset()   # 适配多电机顶升同步顶升
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(pos=height, max_vel=max_vel)
        return False

    def run_motor(self, motor: Motor, pos=0, vel=0.3, max_vel=0.3, reach_di=-1):
        """
        @param motor: Motor类实例对象
        @param pos: 位置模式下电机运动的目标位置
        @param vel: 速度模式下电机运动的目标速度
        @param max_vel: 电机运动的最大速度
        @param reach_di: 到位 DI
        @return: 电机运行到位返回True, 否则返回False
        """
        motor.stop_di = reach_di
        self.state[f'{motor.motor_name}'] = motor.state
        if motor.status == MoveStatus.NONE:
            motor.reset()
        elif motor.status == MoveStatus.FINISHED:
            motor.reset()
            return True
        elif motor.status == MoveStatus.FAILED:
            return False
        else:
            motor.run(vel=vel, pos=pos, max_vel=max_vel)
        return False


class GoodsManger:
    """
    管理机器人自带的库位及货物数据
    """

    def __init__(self, r):
        self.container = list()
        self.move_task = r.moveTask()
        if "getContainers" in dir(SimModule):
            self.container = r.getContainers()
        else:
            r.setError(f"robot.GoodsManger: RBK version mismatch, please update RBK")

    def has_goods(self, pos: str = '0') -> bool:
        for c in self.container:
            if pos == c.get("container_name", None):
                return c.get("has_goods", False)
        return False

    def goods_id_exist(self, goods_id):
        for c in self.container:
            if goods_id == c['goods_id']:
                return True
        return False

    def get_task_goodsId(self):
        for p in self.move_task['params']:
            if p['key'] == 'goodsId':
                return p['string_value']
        return ""

    def get_goodsId_by_container(self, pos: str = '0'):
        for c in self.container:
            if pos == c.get("container_name", None):
                return c.get("goods_id", "")
        return ""

    def get_container_by_goodsId(self, goods_id):
        for c in self.container:
            if goods_id == c['goods_id'] and c['has_goods']:
                return c['container_name']
        return ""

    def get_json_containers(self) -> dict:
        containers = dict()
        for c in self.container:
            containers[c['container_name']] = c
        return containers


if __name__ == "__main__":

    """实例测试"""
    liner_motor = Motor(SimModule(), MotorType.LINEAR_MOTOR, "motor1", -1)
    roller_motor = Motor(SimModule(), MotorType.ROLLER_MOTOR, "motor2", -1)
    robot = Robot(SimModule())
    robot.move(1, 0)
    robot.lift(liner_motor, 1)
    robot.stretch(liner_motor, 1)
    robot.roller(roller_motor, 1)
    if ModuleTool.delay(1):
        if ModuleTool.delay(1):
            print("delay count:", ModuleTool.start_time)
    log = ScriptLog("robot-logs")
    log.logger.info(json.dumps(robot.state))
    log.logger.critical(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    log.logger.error(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    log.logger.warning(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    log.logger.info(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    log.logger.debug(f"{__file__} {time.strftime('%Y-%m-%d: %H')}")
    log.logger.info(f"uuid: {ModuleTool.get_uuid()}")
    log.logger.info(f"date time: {ModuleTool.get_now_date()}")
    log.logger.info(f"get motor_pos from state: {get_value_by_key(robot.state, 'motor_pos')}")


