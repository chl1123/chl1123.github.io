# -*- coding: utf-8 -*-
# @Date: 2023-03-03
# @Author: zhong
# @File: rfid_read.py
# @Version: 2023-03-03
# @Project:
# @Coding: https://seer-group.coding.net/p/product-requirements/requirements/issues/95/detail
# @Update: 可改变要读取的块数量，结果去除首位标识符

import json
import time
import socket

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer
from robot import ModuleTool, MotorType, Motor, Robot

# =======脚本输入参数=======
"""
####BEGIN DEFAULT ARGS####
{
    "seq": {
        "value": "123456",
        "tips": "读码指令序列号",
        "type": "string"
    }
}
####END DEFAULT ARGS####
"""


class Message:
    block_num = 25  # 要读取的块数量
    READ_ALL = f"sMN CSRdMltBlck 0 0 0 0 0 0 0 0 +0 {block_num}"
    READ_ALL_STR = f"sMN RdMltBlckStr 0 0 0 0 0 0 0 0 +0 {block_num}"


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.timeout = 30
        self.init = True
        self.status = MoveStatus.NONE
        self.report_info = dict()

        self.seq = None
        self.ip = "192.168.192.16"
        self.port = 2112
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = None
        self.has_send = False
        self.recv_msg = ''
        r.logInfo(f"init args: {args}")

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            # =====参数初始化和参数检查=====
            self.seq = args.get('seq', '001')
            try:
                self.conn = socket.create_connection((self.ip, self.port))
            except Exception as e:
                r.setError(f'conn error: {e}')
                self.status = MoveStatus.FAILED
            else:
                self.conn.setblocking(False)

        # 超时判断
        if time.time() - self.start_time > self.timeout:
            r.setError(f"script running timeout")
            self.status = MoveStatus.FAILED

        # =====处理业务逻辑=====
        send_msg = b'\x02' + Message.READ_ALL.encode() + b'\x03'
        try:
            if not self.has_send:
                count = self.conn.send(send_msg)
                self.report_info['send_counter'] = count
        except Exception as e:
            r.logInfo(f"send msg error: {e}")
        else:
            self.has_send = True

        try:
            recv_msg = self.conn.recv(1024)
        except BlockingIOError as e:
            r.setNotice(f"BlockingIOError: {e}")
        except Exception as e:
            r.logInfo(f"recv data error: {e}")
        else:
            self.report_info[f'seq'] = self.seq
            self.recv_msg = recv_msg[1:-1].decode()
            r.setNotice(f"recv: {recv_msg or 'None'}")
            self.report_info[f'result'] = self.recv_msg
            if recv_msg:
                self.status = MoveStatus.FINISHED

                # =====数据上报及日志打印=====
        if self.status == MoveStatus.FAILED:
            self.report_info[f'result'] = "read failed"

        self.report_info['script_args'] = args
        self.report_info['task_status'] = self.status
        self.report_info[f'send_msg'] = send_msg
        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def cancel(self, r):
        # =====处理任务取消时的业务=====
        r.setNotice(f"cancel task")
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        r.setNotice(f"suspend task")
        self.status = MoveStatus.SUSPENDED


if __name__ == '__main__':  # 本地运行测试
    r1 = SimModule()
    args1 = {}
    m = Module(r1, args1)
    run_counter = 0
    while True:
        m.run(r1, args1)
        if m.status == MoveStatus.FINISHED or m.status == MoveStatus.FAILED:
            break
        if run_counter > 10:
            break
        else:
            run_counter += 1
