# -*- coding: utf-8 -*-
import serial
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule, ParamServer
import time
import modbus_tk
from modbus_tk import modbus_rtu
import modbus_tk.defines as cst
import fcntl
import json

"""
####BEGIN DEFAULT ARGS####
{
    "operation":{
        "value": 1,
        "default_value":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
        "tips": "动作方式",
        "type": "complex"
    },
    "direction":{
        "value": 0,
        "default_value":[0,1,3],
        "tips": "运动方向",
        "type": "complex"
    },
    "start_codeH":{
        "value": 0,
        "tips": "起点条码H",
        "type": "int"
    },
    "start_codeL":{
        "value": 0,
        "tips": "起点条码L",
        "type": "int"
    },
    "end_codeH":{
        "value": 0,
        "tips": "终点条码H",
        "type": "int"
    },
    "end_codeL":{
        "value": 0,
        "tips": "终点条码L",
        "type": "int"
    },
    "node_num":{
        "value": 0,
        "tips": "节点个数",
        "type": "int"
    },
    "life":{
        "value": 0,
        "tips": "时序号",
        "type": "int"
    },
    "interval_dist":{
        "value": [1, 2, 4, 7],
        "tips": "间隔距离列表",
        "type": "json"
    },
    "accelerate_speed":{
        "value": 676,
        "tips": "运动加速度",
        "type": "int"
    },
    "decelerate_speed":{
        "value": 676,
        "tips": "运动减速度",
        "type": "int"
    },
    "speed":{
        "value": 2700,
        "tips": "运动速度",
        "type": "int"
    },
    "accelerate_lift":{
        "value": 3000,
        "tips": "升降加速度",
        "type": "int"
    },
    "decelerate_lift":{
        "value": 3000,
        "tips": "升降减速度",
        "type": "int"
    },
    "speed_lift":{
        "value": 2700,
        "tips": "升降速度",
        "type": "int"
    },
    "task_num":{
        "value": 0,
        "tips": "任务号",
        "type": "int"
    },
    "action_confirm":{
        "value": 1,
        "tips": "动作确认",
        "type": "int"
    },
    "fault_confirm":{
        "value": 1,
        "tips": "故障确认",
        "type": "int"
    },
    "start":{
        "value": 1,
        "tips": "启动",
        "type": "int"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        self.info0 = None
        self.info1 = None
        self.info2 = p.loadParam("direction", type="int", default=0, comment="运动方向")
        self.info3 = p.loadParam("start_codeH", type="int", default=0, comment="起点条码H")
        self.info4 = p.loadParam("start_codeL", type="int", default=0, comment="起点条码L")
        self.info5 = p.loadParam("node_num", type="int", default=0, comment="节点个数")
        self.info6 = None
        self.info7 = p.loadParam("accelerate_speed", type="int", default=676, comment="运动加速度")
        self.info8 = p.loadParam("decelerate_speed", type="int", default=676, comment="运动减速度")
        self.info9 = p.loadParam("speed", type="int", default=2700, comment="运动速度")
        self.info10 = p.loadParam("accelerate_lift", type="int", default=3000, comment="升降加速度")
        self.info11 = p.loadParam("decelerate_lift", type="int", default=3000, comment="升降减速度")
        self.info12 = p.loadParam("speed_lift", type="int", default=2700, comment="升降速度")
        self.info13 = p.loadParam("task_num", type="int", default=0, comment="任务号")
        self.info14 = p.loadParam("start", type="int", default=1, comment="启动")
        self.info15 = p.loadParam("end_codeH", type="int", default=0, comment="终点条码H")
        self.info16 = p.loadParam("end_codeL", type="int", default=0, comment="终点条码L")
        self.info17 = None
        self.info18 = p.loadParam("fault_confirm", type="int", default=1, comment="故障清除")
        self.address = p.loadParam("address", type="int", default=3, comment="起始地址")
        self.slave = p.loadParam("Slave_station", type="int", default=1, comment="从站号")
        self.status = MoveStatus.NONE
        self.init = True
        #self.state = dict()

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.init = False
            args_error = False
            self.args_Flag = False
            if "operation" not in args:
                r.setError(f"Pls select operation mode")
                args_error = True
            if "node_num" in args and "interval_dist" in args:
                if args["node_num"] != len(args["interval_dist"]):
                    r.setError(f"node_num don't coincide with interval_dist")
                    args_error = True
            if "interval_dist" not in args:
                self.args_Flag = True
            if args_error:
                if not r.errorExits(53000):
                    r.setError(f"args error: {args}")
                return MoveStatus.FAILED
            if "action_confirm" in args:
                self.info0 = int(args["action_confirm"])
            if "operation" in args:
                self.info1 = int(args["operation"])
            if "direction" in args:
                self.info2 = int(args["direction"])
            if "start_codeH" in args:
                self.info3 = int(args["start_codeH"])
            if "start_codeL" in args:
                self.info4 = int(args["start_codeL"])
            if "node_num" in args:
                self.info5 = int(args["node_num"])
            if "interval_dist" in args:
                self.info6 = list(map(int, args["interval_dist"]))
            if "accelerate_speed" in args:
                self.info7 = int(args["accelerate_speed"])
            if "decelerate_speed" in args:
                self.info8 = int(args["decelerate_speed"])
            if "speed" in args:
                self.info9 = int(args["speed"])
            if "accelerate_lift" in args:
                self.info10 = int(args["accelerate_lift"])
            if "decelerate_lift" in args:
                self.info11 = int(args["decelerate_lift"])
            if "speed_lift" in args:
                self.info12 = int(args["speed_lift"])
            if "task_num" in args:
                self.info13 = int(args["task_num"])
            if "start" in args:
                self.info14 = int(args["start"])
            if "end_codeH" in args:
                self.info15 = int(args["end_codeH"])
            if "end_codeL" in args:
                self.info16 = int(args["end_codeL"])
            if "life" in args:
                self.info17 = int(args["life"])
            if "fault_confirm" in args:
                self.info18 = int(args["fault_confirm"])
        if args["operation"] == "14":
            self.check(r)
        elif args["operation"] == "15":
            self.confirm(r)
        elif args["operation"] == "16":
            self.reset(r)
        else:
            self.operation(r)
        #self.state['status'] = self.status
        #self.state['args'] = args
        #r.setInfo(json.dumps(self.state))
        #r.logInfo(json.dumps(self.state))
        return self.status

    def operation(self, r):
        if self.args_Flag:
            #r.setWarning(f"here1")
            fd = serial.Serial(port="/dev/ttyUart1", baudrate=19200, bytesize=8, parity='N', stopbits=1)
            fcntl.ioctl(fd, 0)
            master = modbus_rtu.RtuMaster(fd)
            master.set_timeout(2)

            #data1 = master.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, self.address, output_value=[self.info13, self.info14, self.info7, self.info8, self.info9, self.info10, self.info11, self.info12, self.info1, self.info2, self.info3, self.info4, self.info15, self.info16, self.info5])

           #### 哥伦布测试  start
            data = list()  # 要发送的测试数据
            for i in range(36):# 36个寄存器+modbus相关的字节，一共是81个字节，大于64
                data.append(i)
            data1 = master.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, self.address, output_value=data)
            #### 哥伦布测试  end

            if data1:
                self.status = MoveStatus.FINISHED
            else:
                r.setError(f"fail to sent erase command")
                self.status = MoveStatus.FAILED
        else:
            #r.setWarning(f"here2")
            fd = serial.Serial(port="/dev/ttyUart1", baudrate=19200, bytesize=8, parity='N', stopbits=1)
            fcntl.ioctl(fd, 0)
            master = modbus_rtu.RtuMaster(fd)
            master.set_timeout(20)
            data1 = [self.info13, self.info14, self.info7, self.info8, self.info9, self.info10, self.info11, self.info12, self.info1, self.info2, self.info3, self.info4, self.info15, self.info16, self.info5]
            for i in self.info6:
                data1.append(i)
            data2 = master.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, self.address, output_value=data1)
            #master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, self.address + 16 + i, output_value=1)
            #r.setError(f"{data2}")
            if data2:
                self.status = MoveStatus.FINISHED
            else:
                r.setError(f"fail to sent erase command")
                self.status = MoveStatus.FAILED

    def check(self, r):
        try:
            fd = serial.Serial(port="/dev/ttyUart1", baudrate=19200, bytesize=8, parity='N', stopbits=1)
            fcntl.ioctl(fd, 0)
            master = modbus_rtu.RtuMaster(fd)
            master.set_timeout(20)        
            data1 = master.execute(self.slave, cst.READ_INPUT_REGISTERS, 1, 13)
            if data1:
                report_info = dict()
                report_info["CurrentState"] = data1[0]
                report_info["TaskNum"] = data1[1]
                report_info["ActionResult"] = data1[2]
                report_info["MoveSpeed"] = data1[3]
                report_info["CodeH"] = data1[4]
                report_info["CodeL"] = data1[5]
                report_info["MoveDistanceH"] = data1[6]
                report_info["MoveDistanceL"] = data1[7]
                report_info["MotorencoderH"] = data1[8]
                report_info["MotorencoderL"] = data1[9]
                report_info["AlarmInfo"] = data1[10]
                report_info["ErrorInfo"] = data1[11]
                report_info["BatteryPower"] = data1[12]
                report_info["life"] = self.info17
                r.setInfo(json.dumps(report_info))
                self.status = MoveStatus.FINISHED
            else:
                report_info = dict()
                report_info["CurrentState"] = 10
                report_info["TaskNum"] = 0
                report_info["ActionResult"] = 0
                report_info["MoveSpeed"] = 0
                report_info["CodeH"] = 0
                report_info["CodeL"] = 0
                report_info["MoveDistanceH"] = 0
                report_info["MoveDistanceL"] = 0
                report_info["MotorencoderH"] = 0
                report_info["MotorencoderL"] = 0
                report_info["AlarmInfo"] = 0
                report_info["ErrorInfo"] = 0
                report_info["BatteryPower"] = 0
                report_info["life"] = self.info17
                r.setInfo(json.dumps(report_info))
                self.status = MoveStatus.FAILED
        except Exception as exc:
            r.setWarning(f"fail to read slave avg current state")
            report_info = dict()
            report_info["CurrentState"] = 10
            report_info["TaskNum"] = 0
            report_info["ActionResult"] = 0
            report_info["MoveSpeed"] = 0
            report_info["CodeH"] = 0
            report_info["CodeL"] = 0
            report_info["MoveDistanceH"] = 0
            report_info["MoveDistanceL"] = 0
            report_info["MotorencoderH"] = 0
            report_info["MotorencoderL"] = 0
            report_info["AlarmInfo"] = 0
            report_info["ErrorInfo"] = 0
            report_info["BatteryPower"] = 0
            report_info["life"] = self.info17
            r.setInfo(json.dumps(report_info))
            #self.status = MoveStatus.FAILED

    def confirm(self, r):
        fd = serial.Serial(port="/dev/ttyUart1", baudrate=19200, bytesize=8, parity='N', stopbits=1)
        fcntl.ioctl(fd, 0)
        master = modbus_rtu.RtuMaster(fd)
        master.set_timeout(20)
        data1 = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=1)
        if data1:
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"fail to sent erase command")
            self.status = MoveStatus.FAILED

    def reset(self, r):
        fd = serial.Serial(port="/dev/ttyUart1", baudrate=19200, bytesize=8, parity='N', stopbits=1)
        fcntl.ioctl(fd, 0)
        master = modbus_rtu.RtuMaster(fd)
        master.set_timeout(20)
        data1 = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 2, output_value=self.info18)
        if data1:
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"fail to sent erase command")
            self.status = MoveStatus.FAILED

    def do_connect(self):
        try:
            fd = serial.Serial(port="/dev/ttyUart1", baudrate=19200, bytesize=8, parity='N', stopbits=1)
            fcntl.ioctl(fd, 0)
            master = modbus_rtu.RtuMaster(fd)
            master.set_timeout(20)
            return True
        except Exception as exc:
            return False


if __name__ == '__main__':
    pass
