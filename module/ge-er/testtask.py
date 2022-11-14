# -*- coding: utf-8 -*-
import json
import random
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
import socket
from rbkEnum import RbkNetProtocol

"""
####BEGIN DEFAULT ARGS####
{
    "tasklist": {
        "value": {"name":"task_DB01RF"},
        "tips": "执行预存任务链",
        "unit": "",
        "type": "json"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.init = True
        self.status = MoveStatus.NONE
        self.req_msg = ''
        self.res_msg = ''
        self.have_send = False
        self.ip = "127.0.0.1"
        self.port = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        r.setInfo(json.dumps(args))
        self.success_str = '"ret_code":0'

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            if "tasklist" in args:
                #req_num = random.randint(1, 100)
                req_msg = args.get("tasklist", None)
                req_msg['name'] = int(req_msg['name'])
                #r.setInfo("random num is {}".format(req_num))
                self.req_msg = RbkNetProtocol.pack_byte_array(req_msg, RbkNetProtocol.robot_config_di,r)
            else:
                r.setError("user args error:{}".format(json.dumps(args["tasklist"])))
                self.status = MoveStatus.FAILED
            try:
                self.port = RbkNetProtocol.port_task.value
                self.sock.connect((self.ip, self.port))
            except Exception as e:
                r.setError("client socket connect error: {}".format(e))
                self.status = MoveStatus.FAILED
            else:
                self.sock.setblocking(False)
                r.setNotice("client socket connect success")

        if self.status == MoveStatus.FAILED:
            return self.status
        if not self.have_send:
            self.sock.send(bytearray(self.req_msg, "ascii"))
            self.have_send = True
        try:
            self.res_msg = self.sock.recv(1024)
        except BlockingIOError:
            pass
        except Exception as e:
            r.setError(str(e))
        else:
            if RbkNetProtocol.unpack_byte_array(self.res_msg, self.success_str, r) != -1:
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.FAILED
                r.setError("recv error")
            self.sock.close()
        info = dict()
        info['req_msg'] = str(self.req_msg)
        info['res_msg'] = str(self.res_msg)
        info['status'] = self.status
        r.setInfo(json.dumps(info))
        r.setNotice(f"{info}")
        return self.status
