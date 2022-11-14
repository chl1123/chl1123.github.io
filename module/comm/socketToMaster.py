# -*- coding: utf-8 -*-
# @Author : yifu
import json
from rbkSim import SimModule
from rbk import MoveStatus, BasicModule
import sys
sys.path.append("../../modbus_tk")
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp

"""
####BEGIN DEFAULT ARGS####
{
    "address": {
        "value":"",
        "tips": "modbus可读写地址位",
        "unit": "",
        "type": "int"
    },
    "shouldValue":{
        "value":"",
        "tips": "可读写地址位的值",
        "unit": "",
        "type": "int"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.init = True
        self.status = MoveStatus.NONE
        self.address = 0
        self.have_send = False
        self.ip = "192.168.1.102"
        self.port = 502
        self.modbus_connection = None
        r.setInfo(json.dumps(args))
        self.read_success_value = None
        self.write_success_value = 0
        self.result = None

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            if "address" in args and "shouldValue" in args:
                self.address = args.get("address", None)
                self.read_success_value = args.get("shouldValue", None)
            else:
                r.setError(
                    "user args error:req msg{},res msg{}".format(args.get("address", None),
                                                                 args.get("shouldValue", None)))
                self.status = MoveStatus.FAILED
            try:
                self.modbus_connection = modbus_tcp.TcpMaster(host=self.ip, port=self.port, timeout_in_sec=5)
            except Exception as e:
                r.setError("client modbus connect error: {}".format(e))
                self.status = MoveStatus.FAILED
        if self.status == MoveStatus.FAILED:
            return self.status
        self.result = self.modbus_connection.execute(1, cst.READ_HOLDING_REGISTERS, self.address, 1)
        #r.setError("result{},success_value{}".format(self.result[0],self.read_success_value))
        if self.result[0] != self.read_success_value:
            self.status = MoveStatus.RUNNING
        if self.result[0] == self.read_success_value:
            self.have_send = True
        if self.have_send:
            #r.setError("write{}".format(self.modbus_connection.execute(1, cst.WRITE_SINGLE_REGISTER, 0, 1, self.write_success_value)[1]))
            if self.modbus_connection.execute(1, cst.WRITE_SINGLE_REGISTER, 0, 1, self.write_success_value)[1] == 0:
                self.status = MoveStatus.FINISHED
            else:
                self.status = MoveStatus.RUNNING

            self.modbus_connection.close()
        info = dict()
        info['modbus_address'] = str(self.address)
        info['modbus_read_value'] = str(self.read_success_value)
        info['status'] = self.status
        r.setInfo(json.dumps(info))
        r.setNotice(f"{info}")
        return self.status
