# -*- coding: utf-8 -*-
import math

import goPath
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer, Pos2Base
import time
import modbus_tk.modbus
from modbus_tk import modbus_tcp
import modbus_tk.defines as cst
import modbus_tk.utils
"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": "load",
        "default_value":["load","unload"],
        "tips": "operation mode",
        "type": "complex"
    },
    "material":{
        "value": "CELL",
        "default_value":["CELL","BMU","C-tray","B-tray"],
        "tips": "material type",
        "type": "complex"
    },
    "height":{
        "value": "0",
        "default_value":[950,550],
        "tips": "drilling crew height",
        "type": "complex"
    },
    "side":{
        "value": "None",
        "default_value":["Left","Right","Left+Right"],
        "tips": "AGV position",
        "type": "complex"
    },
    "recFile": {
        "value": "",
        "tips": "识别文件",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r:SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        # 以下DO、DI参数按项目实际情况进行修改，脚本生成的json配置文件也需要同步修改
        self.DO1 = p.loadParam("task_confirm", type="int", default=11, comment="任务发布指令")
        self.DO2 = p.loadParam("Emergency_stop", type="int", default=12, comment="紧急停止指令")
        self.DO3 = p.loadParam("task_cancel", type="int", default=13, comment="任务取消指令")
        self.DI1 = p.loadParam("task_running", type="int", default=18, comment="任务运行信号")
        self.DI2 = p.loadParam("task_completed", type="int", default=19, comment="任务完成信号")
        self.DI3 = p.loadParam("task_fault", type="int", default=20, comment="任务故障信号")
        self.DI4 = p.loadParam("DMS_check", type="int", default=21, comment="DMS检测信号1")
        self.DI5 = p.loadParam("DMS_check", type="int", default=22, comment="DMS检测信号2")
        self.url = p.loadParam("URL", type="str", default="192.168.192.66", comment="slave IP")
        self.address = p.loadParam("address", type="int", default=1, comment="primary address")
        self.slave = p.loadParam("Slave_station", type="int", default=1, comment="slave Station")
        self.status = MoveStatus.NONE
        self.init = True
        self.rec_file = None
        self.rec = None
        self.reach_flag = False
        self.start_time = None

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            '''
            self.rec_file = args.get("recFile", None)
            if self.rec_file:
                self.rec = RecAdjust(r, self.rec_file)
            '''
            self.rec = RecDMS()
            args_error = False
            if "operation" in args:
                if args["side"] != "Left+Right" and "material" not in args:
                    r.setError(f"Pls select material type")
                    args_error = True
            elif "side" not in args:
                r.setError(f"Pls select side")
                args_error = True
            else:
                r.setError(f"Pls select operation mode")
                args_error = True
            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED

        if self.rec:
            if self.rec.status == MoveStatus.FINISHED:
                self.reach_flag = True
            elif self.rec.status == MoveStatus.FAILED:
                self.reach_flag = False
                self.status = MoveStatus.FAILED
            else:
                self.rec.run(r, self)
        else:
            self.reach_flag = True

        if self.reach_flag and args["operation"] == "load" and args["side"] == "Left+Right":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=1)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        # r.setSound("navigation", True)
                        # self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "unload" and args["side"] == "Left+Right":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=2)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "load" and args["side"] == "Left" and args["material"] == "CELL":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=3)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "load" and args["side"] == "Right" and args["material"] == "CELL":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=4)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "load" and args["side"] == "Left" and args["material"] == "C-tray":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=5)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "load" and args["side"] == "Right" and args["material"] == "C-tray":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=6)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "load" and args["side"] == "Left" and args["material"] == "BMU":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=7)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "load" and args["side"] == "Right" and args["material"] == "BMU":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=8)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "load" and args["side"] == "Left" and args["material"] == "M-tray":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=9)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED

        elif self.reach_flag and args["operation"] == "load" and args["side"] == "Right" and args["material"] == "M-tray":
            try:
                master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                master.set_timeout(5)
                data = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=10)
                if data:
                    # master = modbus_tcp.TcpMaster(host="192.168.192.66", port=502)
                    # master.set_timeout(5)
                    data1 = master.execute(self.slave, cst.READ_HOLDING_REGISTERS, 6, 1)
                    # r.setNotice(f"here5")
                    # r.logInfo(f"post failed!!! url: {data1} abc: {data1[0]}")
                    if int(data1[0]) == 100:
                        # r.clearError(f"task finished, reset alarm")
                        master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 6, output_value=0)
                        self.status = MoveStatus.FINISHED
                    elif self.delay(18):
                        r.setError(f"alarm, task exceeding the max time")
                        #self.status = MoveStatus.RUNNING
            except Exception as e:
                r.logInfo(f"post failed!!! url: {self.url}, error: {e}")
                self.status = MoveStatus.FAILED
        return self.status

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

    @staticmethod
    def check_DO(r: SimModule, do: int):
        """
        检测单个DO是否被触发
        :param r: SimModule类对象
        :param do: 需要检测的DO
        :return: 返回指定DO的状态，若DO不存在返回False
        """
        DO = r.Do()
        nodes = DO.get('node', list())
        for node in nodes:
            if node['id'] == do:
                return node['status']
        return False

    def do_connect(self, url, slave, address, timeout=5.0):
        try:
            master = modbus_tcp.TcpMaster(url)  # 填写server的IP地址，作地址查询用
            master.set_timeout(5)
            master.execute(slave, cst.READ_HOLDING_REGISTERS, address, 1)
            return True
        except Exception as exc:
            return False

    # 延时函数
    def delay(self, second):
        """
        延时 second 秒
       :param second:
        :return: 延时完成返回True
        """
        if self.start_time is None:
            self.start_time = time.time()
        if time.time() - self.start_time > second:
            self.start_time = None
            return True
        return False


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
        if rec_result:              # 成功获取识别结果
            # r.resetRec()           # 重置识别模块
            if self.go_path.status == MoveStatus.NONE:
                self.go_path.status = MoveStatus.RUNNING
                pos2world = [rec_result['x'], rec_result['y'], rec_result['yaw']]    # 目标点在世界坐标系的位置
                robot2world = [r.loc()['x'], r.loc()['y'], r.loc()['angle']]    # 小车在世界坐标系的位置
                pos2robot = Pos2Base(pos2world, robot2world)    # 目标点相对小车的位置
                if abs(pos2robot[0]) < 0.005:      # 目标点相对小车的位置小于阈值时，识别调整完成
                    self.status = MoveStatus.FINISHED
                    #return True
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
        else:    # 识别失败
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

class RecDMS:
    def __init__(self):
        self.status = MoveStatus.NONE
        self.max_rec_time = 20
        self.current_time = 0
        self.init_times = 0
        self.state = dict()
        self.init = True

    def run(self, r, agv):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.init_times = time.time()
        rec_result = agv.check_DI(r, agv.DI4) or agv.check_DI(r, agv.DI5)
        if rec_result:              # 成功获取识别结果
            self.status = MoveStatus.FINISHED
        else:
            self.current_time = time.time() - self.init_time
            if self.current_time > self.max_rec_time:
                r.setError(f"rec time exceeding the max time")
                self.status = MoveStatus.FAILED
        self.state['rec_result'] = rec_result
        self.state['rec_adjust'] = self.status


if __name__ == '__main__':
    pass
