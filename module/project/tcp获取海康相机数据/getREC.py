# -*- coding: utf-8 -*-
# @Request : 获取tcp服务端数据
# @Version: 1.0
import json
import socket
import time

import syspy.goPath as goPath
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer, Pos2Base
from syspy.robot import ModuleTool
"""
####BEGIN DEFAULT ARGS####

####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super().__init__()
        self.timeout = 60
        self.read_times = 0 # 当前读的数据次数
        self.max_read_times = 10 # 当前读的数据 的 最大次数
        self.client_socket_read = None
        self.client_socket_send = None
        self.init = True
        self.state = {}
        self.init_time = time.time()
        self.ip = "192.168.8.81"
        self.port_send = 2001
        self.port_read = 2002
        self.opt = [False] * 3
        self.start_content = "start"
        self.read_data = "NoRead"
        self.NoRead = "NoRead"

    def periodRun(self, r: SimModule):
        self.state["task"] = r.moveTask()
        # self.state["taskSTATUS"] = r.getCurrentTaskStatus()
        # if ModuleTool.check_DI(r,2):
        #     r.stopRobot(True)
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        return True

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            self.client_socket_send = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket_read = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket_send.connect((self.ip, self.port_send))
            self.client_socket_read.connect((self.ip, self.port_read))
        if not self.client_socket_read or not self.client_socket_send:
            return self.status
        if time.time()-self.init_time > self.timeout:
            self.status = MoveStatus.FAILED
            r.setError(f"任务超时 {self.timeout}s")
        if self.read_times >= self.max_read_times:
            # r.setError(f"发送 start {self.max_read_times}次，还有收到正确的数据")
            self.status = MoveStatus.FINISHED
        if not self.init and self.status != MoveStatus.FINISHED:
            if not self.opt[0]:
                # 发送数据
                self.client_socket_send.sendall(self.start_content.encode())
                self.opt[0] = True
            if not self.opt[1] and self.opt[0]:
                # 接受数据
                read_data = self.client_socket_read.recv(1024)
                if not read_data:
                    pass
                else:
                    self.read_data = read_data.decode()
                    self.read_times += 1
                    self.opt[1] = True
            if not self.opt[2] and self.opt[1]:
                if self.read_data != self.NoRead:
                    self.opt[2] = True
            if all(self.opt):
                self.status = MoveStatus.FINISHED
        if self.status == MoveStatus.FINISHED or self.status == MoveStatus.FAILED:
            if self.client_socket_read:
                self.client_socket_read.close()
            if self.client_socket_send:
                self.client_socket_send.close()
        self.state["opt"] = self.opt
        self.state["READ_data"] = self.read_data
        self.state["max_read_times"] = self.max_read_times
        self.state["read_times_current"] = self.read_times
        r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        return self.status

    def cancel(self, r: SimModule):
        if self.client_socket_read:
            self.client_socket_read.close()
        if self.client_socket_send:
            self.client_socket_send.close()
        self.status = MoveStatus.NONE

    def suspend(self, r: SimModule):
        r.logInfo("task suspend")
        self.status = MoveStatus.SUSPENDED



if __name__ == '__main__':
    pass