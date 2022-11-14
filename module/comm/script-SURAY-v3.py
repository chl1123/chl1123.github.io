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
V3.14
Qbj 2022/9/19
将WCS下达的json报文转换为modbus报文后发给子车
将子车返回的modbus报文转换为json报文传给WCS
r.setInfo是发信息给WCS的函数
r.setError是向 XXX 报错
r.setWarning是向WCS报警
master.execute 是把JSON转换为modbus

#                从站号          写多个寄存器                 起始地址           内容
master.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, self.address, output_value=data1)

#                从站号         写单个寄存器                  起始地址           内容
master.execute(self.slave, cst.WRITE_SINGLE_REGISTER,        2,        output_value=self.info18)

#               从站号          读输入寄存器                  起始地址     要读取的长度
master.execute(self.slave, cst.READ_INPUT_REGISTERS,         1,         13    )

"""

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

# regmap
ACCELERATE_SPEED_ADDR = 0X0005
DECELERATE_SPEED = 0X0006
SPEED = 0X0007
ACCELERATE_LIFT = 0X0008
DECELERATE_LIFT = 0X0009
SPEED_LIFT = 0X000A

TASKDIRECTION = 0X4000
NODENUM = 0X4001
ORIGINALCODEH = 0X4002
ORIGINALCODEL = 0X4003

ComPort = "/dev/ttyUart1"
ComBaudRate = 115200
ModbusTimeOut = 2

class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        p = ParamServer(__file__)
        # 未被初始化时的默认参数  Qbj 2022/9/19
        self.info0 = None  # 保持寄存器（W/R）0x0001
        self.info1 = 0  # 保持寄存器（W/R）0x000b
        self.info2 = p.loadParam("direction", type="int", default=0, comment="运动方向")  # 保持寄存器（W/R）0x000c   >本体车写运动信息（动作信息）写保持寄存器：0x000a 0x000b 0x000c~最后
        self.info3 = p.loadParam("start_codeH", type="int", default=0, comment="起点条码H") # 保持寄存器（W/R）0x000d
        self.info4 = p.loadParam("start_codeL", type="int", default=0, comment="起点条码L") # 保持寄存器（W/R）0x000e
        self.info5 = p.loadParam("node_num", type="int", default=0, comment="节点个数") # 保持寄存器（W/R）0x0011
        self.info6 = None # 保持寄存器（W/R）0x0012 ~ 0x0011+N
        self.info7 = p.loadParam("accelerate_speed", type="int", default=676, comment="运动加速度")  # 保持寄存器（W/R）0x0005  >本体车写预设信息（速度信息相关）写保持寄存器：x0005~0x000a
        self.info8 = p.loadParam("decelerate_speed", type="int", default=676, comment="运动减速度")  # 保持寄存器（W/R）0x0006
        self.info9 = p.loadParam("speed", type="int", default=2700, comment="运动速度")              # 保持寄存器（W/R）0x0007
        self.info10 = p.loadParam("accelerate_lift", type="int", default=3000, comment="升降加速度") # 保持寄存器（W/R）0x0008
        self.info11 = p.loadParam("decelerate_lift", type="int", default=3000, comment="升降减速度") # 保持寄存器（W/R）0x0009
        self.info12 = p.loadParam("speed_lift", type="int", default=2700, comment="升降速度")        # 保持寄存器（W/R）0x000a
        self.info13 = p.loadParam("task_num", type="int", default=0, comment="任务号") # 保持寄存器（W/R）0x0003  >本体车写触发信号（动作开始运行）写保持寄存器：0x0003~0x0004
        self.info14 = p.loadParam("start", type="int", default=1, comment="启动") # 保持寄存器（W/R）0x0004
        self.info15 = p.loadParam("end_codeH", type="int", default=0, comment="终点条码H") # 保持寄存器（W/R）0x000f
        self.info16 = p.loadParam("end_codeL", type="int", default=0, comment="终点条码L") # 保持寄存器（W/R）0x0010
        self.info17 = None
        self.info18 = p.loadParam("fault_confirm", type="int", default=1, comment="故障清除") # 保持寄存器（W/R）0x0002
        self.address = p.loadParam("address", type="int", default=3, comment="起始地址")
        self.slave = p.loadParam("Slave_station", type="int", default=1, comment="从站号")
        self.status = MoveStatus.NONE
       # self.Life = 1
        self.init = True
        #self.state = dict()

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            # 初始化参数  Qbj 2022/9/19
            self.init = False
            args_error = False
            self.args_Flag = False
            if "mode" not in args:
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
            if "mode" not in args:
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

            # if args["operation"] == "setPara":
            #     self.setpara(r)

            # if args["operation"] == "quickMove":
            #     r.setError(f"Pls set para first")
        if "mode" in args:
            if args["mode"] == "quickMove":
                self.operationNew(r, args)

            elif args["mode"] == "setPara":
                self.setpara(r)
            else:
                r.setError(f"Pls set mode")

        else:
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
 
    def operationNew(self,r,args):

        adder_list = list()
        buff_send = list()

        if "taskDirection" in args:
            datalist = list()
            datalist.append(args["taskDirection"])
            datalist.append(args["nodeNum"])
            datalist.append(args["originalCodeH"])
            datalist.append(args["originalCodeL"])
            for node_id in args["nodeInfo"]:
                datalist.append(node_id["distance"])
                datalist.append(node_id["codeH"])
                datalist.append(node_id["codeL"])

            for i in range(30-len(args["nodeInfo"])): # 填充0
                datalist.append(0)
                datalist.append(0)
                datalist.append(0)

            datalist.append(args["taskId"])
            datalist.append(args["startTask"])
            datalist.append(args["segment"])
            datalist.append(0)
            datalist.append(0)
            datalist.append(0)
            datalist.append(args["taskNodeNum"])

            for task_id in args["taskInfo"]:
                datalist.append(task_id["location"] << 8 | task_id["action"])

            adder_list.append(0x4000)
            buff_send.append(datalist)

        elif "taskId" in args and "startTask" in args and "segment" in args:
            datalist2 = list()
            datalist2.append(args["taskId"])
            datalist2.append(args["startTask"])
            datalist2.append(args["segment"])

            adder_list.append(0x405e)
            buff_send.append(datalist2)

        fd = serial.Serial(port=ComPort, baudrate=ComBaudRate, bytesize=8, parity='N', stopbits=1)
        master = modbus_rtu.RtuMaster(fd)
        master.set_timeout(ModbusTimeOut)

        for i in range(len(buff_send)):
            data1 = master.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, adder_list[i], output_value=buff_send[i])

        if data1:
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"fail to sent erase command")
            self.status = MoveStatus.FAILED

    def setpara(self, r):
        # 设定子车预设信息（速度信息相关）
        fd = serial.Serial(port=ComPort, baudrate=ComBaudRate, bytesize=8, parity='N', stopbits=1)
        fcntl.ioctl(fd, 0)
        master = modbus_rtu.RtuMaster(fd)
        master.set_timeout(ModbusTimeOut)
        datalist = [self.info7, self.info8, self.info9, self.info10, self.info11, self.info12]
        data1 = master.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, ACCELERATE_SPEED_ADDR, output_value=datalist)
        if data1:
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"fail to sent erase command")
            self.status = MoveStatus.FAILED

    def operation(self, r):
        if self.args_Flag:
            #r.setWarning(f"here1")
            fd = serial.Serial(port=ComPort, baudrate=ComBaudRate, bytesize=8, parity='N', stopbits=1)
            fcntl.ioctl(fd, 0)
            master = modbus_rtu.RtuMaster(fd)
            master.set_timeout(ModbusTimeOut)
            data1 = master.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, self.address, output_value=[self.info13, self.info14, self.info7, self.info8, self.info9, self.info10, self.info11, self.info12, self.info1, self.info2, self.info3, self.info4, self.info15, self.info16, self.info5])
            if data1:
                self.status = MoveStatus.FINISHED
            else:
                r.setError(f"fail to sent erase command")
                self.status = MoveStatus.FAILED
        else:
            #r.setWarning(f"here2")
            fd = serial.Serial(port=ComPort, baudrate=ComBaudRate, bytesize=8, parity='N', stopbits=1)
            fcntl.ioctl(fd, 0)
            master = modbus_rtu.RtuMaster(fd)
            master.set_timeout(ModbusTimeOut)
            data1 = [self.info13, self.info14, self.info7, self.info8, self.info9, self.info10, self.info11, self.info12, self.info1, self.info2, self.info3, self.info4, self.info15, self.info16, self.info5]
            for i in self.info6:
                data1.append(i)
            data2 = master.execute(self.slave, cst.WRITE_MULTIPLE_REGISTERS, self.address, output_value=data1)
            #master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, self.address + 16 + i, output_value=1)
            #r.setError(f"{data2}")
            if data2:
                self.status = MoveStatus.FINISHED   # 操作成功，状态置为操作结束
            else:
                r.setError(f"fail to sent erase command")
                self.status = MoveStatus.FAILED    # 操作失败，状态置为失败

    def check(self, r):
        try:
            fd = serial.Serial(port=ComPort, baudrate=ComBaudRate, bytesize=8, parity='N', stopbits=1)
            fcntl.ioctl(fd, 0)
            master = modbus_rtu.RtuMaster(fd)
            master.set_timeout(ModbusTimeOut)
            '''
            读输入寄存器  0x0001 - 0x0024  # Qbj 2022/9/19
            #data1 = master.execute(self.slave, cst.READ_INPUT_REGISTERS, 1, 13)
            '''
            data1 = master.execute(self.slave, cst.READ_INPUT_REGISTERS, 1, 36) # Qbj 2022/9/19
            if data1:
                report_info = dict()
                report_info["CurrentState"] = data1[0x0001 - 1]  # 输入寄存器0x0001
                report_info["TaskNum"] = data1[0x0002 - 1]  # 输入寄存器0x0002
                report_info["ActionResult"] = data1[0x0003 - 1]  # 输入寄存器0x0003
                report_info["MoveSpeed"] = data1[0x0004 - 1]  # 输入寄存器0x0004
                report_info["CodeH"] = data1[0x0005 - 1]  # ...
                report_info["CodeL"] = data1[0x0006 - 1]
                report_info["MoveDistanceH"] = data1[0x0007 - 1]
                report_info["MoveDistanceL"] = data1[0x0008 - 1]
                report_info["MotorencoderH"] = data1[0x0009 - 1]
                report_info["MotorencoderL"] = data1[0x000a - 1]
                report_info["AlarmInfo"] = data1[0x000b - 1]
                report_info["ErrorInfo"] = data1[0x000c - 1]
                report_info["BatteryPower"] = data1[0x000d - 1]  # 输入寄存器0x000d
                #  新增开始 Qbj 2022/9/19
                report_info["taskStatus"] = data1[0x0020 - 1]  # 0x0020
                report_info["execTaskId"] = data1[0x0021 - 1]  # 0x0021
                report_info["finishSegment"] = data1[0x0022 - 1]  # 0x0022
                report_info["taskResult"] = data1[0x0023 - 1]  # 0x0023
                report_info["errorCode"] = data1[0x0024 - 1]  # 0x0024
                #  新增结束 Qbj 2022/9/19
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
                #  新增开始 Qbj 2022/9/19
                report_info["taskStatus"] = 0
                report_info["execTaskId"] = 0
                report_info["finishSegment"] = 0
                report_info["taskResult"] = 0
                report_info["errorCode"] = 0
                #  新增结束 Qbj 2022/9/19
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
            #  新增开始 Qbj 2022/9/19
            report_info["taskStatus"] = 0
            report_info["execTaskId"] = 0
            report_info["finishSegment"] = 0
            report_info["taskResult"] = 0
            report_info["errorCode"] = 0
            #  新增结束 Qbj 2022/9/19
            report_info["life"] = self.info17
            r.setInfo(json.dumps(report_info))
            # self.status = MoveStatus.FAILED

    def confirm(self, r):
        fd = serial.Serial(port=ComPort, baudrate=ComBaudRate, bytesize=8, parity='N', stopbits=1)
        fcntl.ioctl(fd, 0)
        master = modbus_rtu.RtuMaster(fd)
        master.set_timeout(ModbusTimeOut)
        data1 = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 1, output_value=1)
        if data1:
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"fail to sent erase command")
            self.status = MoveStatus.FAILED


    # 故障清除
    def reset(self, r):
        fd = serial.Serial(port=ComPort, baudrate=ComBaudRate, bytesize=8, parity='N', stopbits=1)
        fcntl.ioctl(fd, 0)
        master = modbus_rtu.RtuMaster(fd)
        master.set_timeout(ModbusTimeOut)
        data1 = master.execute(self.slave, cst.WRITE_SINGLE_REGISTER, 2, output_value=self.info18)  # 故障清除
        if data1:
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"fail to sent erase command")
            self.status = MoveStatus.FAILED

    # 判断是否连接成功
    def do_connect(self):
        try:
            fd = serial.Serial(port=ComPort, baudrate=ComBaudRate, bytesize=8, parity='N', stopbits=1)
            fcntl.ioctl(fd, 0)
            master = modbus_rtu.RtuMaster(fd)
            master.set_timeout(ModbusTimeOut)
            return True
        except Exception as exc:
            return False


if __name__ == '__main__':
    pass
