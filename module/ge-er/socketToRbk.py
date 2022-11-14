# -*- coding: utf-8 -*-
import json
import random
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
import socket

"""
####BEGIN DEFAULT ARGS####
{
    "Req": {
        "value":" ",
        "default_value": [
            "PauseScript,;","ContinueScript,;","StartScript,;","StopScript,;","SwitchScript,DBL_43OK.json;","SwitchScript,DBR_42OK.json;""SwitchScript,WBL_35OK.json;""SwitchScript,WBR_36OK0125.json;""SwitchScript,MSL_28OK.json;""SwitchScript,MSR_31OK.json;"
        ],
        "tips": "发送给大族的信息",
        "unit": "",
        "type": "complex"
    },
    "shouldRes":{
        "value":" ",
        "default_value": [
           "PauseScript,OK,;","ContinueScript,OK,;","StartScript,OK,;","StopScript,OK,;","SwitchScript,OK,;"
        ],
        "tips": "发送至大族成功响应的信息",
        "unit": "",
        "type": "complex"
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
        self.ip = "192.168.192.10"
        self.port = 10003
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        r.setInfo(json.dumps(args))
        self.success_str = None

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            if "Req" not in args or "shouldReq" not in args:
                req_msg = args.get("Req", None)
                self.success_str = args.get("shouldRes", None)
                self.req_msg = req_msg
            else:
                r.setError(
                    "user args error:req msg{},res msg{}".format(args.get("Req", None), args.get("shouldRes", None)))
                self.status = MoveStatus.FAILED
            try:
                self.sock.connect((self.ip, self.port))
            except Exception as e:
                r.setError("client socket connect error: {}".format(e))
                self.status = MoveStatus.FAILED
            else:
                self.sock.setblocking(True)
                r.setNotice("client socket connect success")

        if self.status == MoveStatus.FAILED:
            return self.status
        if not self.have_send:
            self.sock.send(bytearray(self.req_msg, "ascii"))
            self.have_send = True
        try:
            self.res_msg = self.sock.recv(1024)
            # r.setError("res_msg{}".format(self.res_msg))
        except BlockingIOError:
            pass
        except Exception as e:
            r.setError(str(e))
        else:
            #r.setError("res_msg{}".format(str(self.res_msg).find(self.success_str)))
            # if str(self.res_msg).find(self.success_str) != -1:
            #     self.status = MoveStatus.FINISHED
            # else:
            self.status = MoveStatus.FINISHED
            # self.init = True
            # self.have_send = False
            #r.setError("recv error")
            self.sock.close()
        info = dict()
        info['req_msg'] = str(self.req_msg)
        info['res_msg'] = str(self.res_msg)
        info['status'] = self.status
        r.setInfo(json.dumps(info))
        r.setNotice(f"{info}")
        return self.status
