# @File :clean_robot.py
# @Version : 2.0
# @Project : 霞智清洁机器人项目,霞智自研XZ-MC700驱动器用于控制：
# 两个刷盘电机、喷水泵电机、刷盘升降电机、水扒升降电机、喷水电磁阀、排水球阀；
# 同时收清水液位计、污水液位计信号
# @coding: https://seer-group.coding.net/p/robokit/requirements/issues/1822/detail
# @Update : 20230906
import sys
import base64
import time
import socket

sys.path.append("../syspy")
import json
from syspy.rbkSim import SimModule
from syspy.rbk import MoveStatus, BasicModule
from syspy.robot import ModuleTool
import can_commad as cmd

"""
####BEGIN DEFAULT ARGS####
{
    "addingWater":{
        "value": "",
        "default_value":["true","false"],
        "tips": "tips",
        "type": "complex"
    },
    "operation":{
        "value": "",
        "default_value":["WashStart","WashEnd","DustStart", "DustEnd","check_level"],
        "tips": "tips",
        "type": "complex"
    },
    "shift":{
        "value": "",
        "default_value":["lowGear","MediumGear","highGear","light","normal","heavy"],
        "tips": "档位",
        "type": "complex"
    },
    "brush_plate":{
        "value": 0,
        "default_value":0,
        "tips": "刷盘电机",
        "type": "int",
        "max_value":100,
        "min_value":0
    },
    "brush_plate_lift":{
        "value": "up",
        "default_value":["up","down"],
        "tips": "刷盘上升或者下降",
        "type": "complex"
    },
    "suction_wing":{
        "value": 0,
        "default_value":0,
        "tips": "吸风电机",
        "type": "int",
        "max_value":100,
        "min_value":0
    },
    "water_pa":{
        "value": "up",
        "default_value":["up","down"],
        "tips": "水扒上升或者下降",
        "type": "complex"
    },
    "jet_water_valve":{
        "value": "open",
        "default_value":["open","close"],
        "tips": "喷水阀打开或关闭",
        "type": "complex"
    },
    "jet_water":{
        "value": 0,
        "default_value":0,
        "tips": "喷水电机",
        "type": "int",
        "max_value":100,
        "min_value":0
    },
    "brain_ball_valve":{
        "value": "open",
        "default_value":["open","close"],
        "tips": "排水球阀打开或关闭",
        "type": "complex"
    }
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()
        self.clean_water_level_add = 0
        self.block_start_time = time.time()
        self.stop_number = 0
        self.periodRun_start_time = time.time()
        self.check_level_start_time = time.time()
        self.stop_ok = None
        self.is_init_block = None
        self.block_init = None
        self.block_first = None
        self.is_block = None
        self.clean_water_alarm = 5  # 清水液位低于此值，任务便不执行
        self.waste_water_alarm = 90  # 污水液位高于此值，任务便不执行
        self.wash_start_time = 1  # wash start 的时间控制
        self.wash_end_time = 15  # wash start 的时间控制,暂未生效
        self.ip = "127.0.0.1"  # 机器人上报数据 ip
        self.port = 502
        self.report_addr_1 = 110  # 机器人上报数据地址
        self.report_addr_2 = 111  # 机器人上报数据地址
        self.addingWater_do = 4  # 机器人 addingWater_do
        self.addingWater_limit_level = 99  # 机器人 addingWater limit level
        self.can_frame = None
        self.state = dict()
        self.operation_status = MoveStatus.NONE
        self.task_list = []
        self.task_id = 0
        self.task = None
        self.status = MoveStatus.NONE
        self.operation = None
        self.init = True
        self.chanel = 2
        self.can_id = 0x605
        self.clean_water_level = 0
        self.waste_water_level = 0
        self.dlc = 8  # 发送报文的数据长度，一般为8
        self.extend = False  # 报文是否为扩展型，一般为false
        self.shift = "light"
        self.check_level_opt = [False] * 4
        self.block_stop_opt = [False] * 8
        self.block_re_start_opt = [False] * 8

        self.is_device_run = False

        # 液位滤波
        self.clean_filter = MeanValue(500)
        self.waste_filter = MeanValue(500)

        r.logInfo(str(args))

    def get_clean_filter(self, v):
        self.clean_filter.setValue(v)
        return self.clean_filter.getMeanValue()

    def get_waste_filter(self, v):
        self.waste_filter.setValue(v)
        return self.waste_filter.getMeanValue()

    def device_status(self, r):
        fj_s = False
        fj = self.get_proxy_info(r, cmd.SUCTION_WING_GET)
        if not fj[8:10] == "00":
            fj_s = True
        if fj_s:
            self.is_device_run = True

    def periodRun(self, r: SimModule) -> bool:
        task_status = r.getCurrentTaskStatus()
        self.state["task_status"] = task_status
        """任务异常，需要停止工作,需要停止刷盘旋转、吸水电机、喷水电机，每个设备下发两次停止信号，共下发8次"""
        if task_status in [3, 5, 6]:
            if not self.stop_ok:
                self.stopV1(r)
                if self.stop_number >= 8:
                    self.stop_ok = True
                    self.stop_number = 0
                else:
                    self.stop_number += 1  # 下发停止信号计数
        else:
            self.stop_ok = False
            self.stop_number = 0
        try:
            """"上报设备状态,清洁车驱动器新增看门狗，只要在 1 秒 内没有can通信，则会停止风机以及喷水"""
            """"WashStart 时的安全逻辑"""

            if self.operation == "WashStart":
                if time.time() - self.periodRun_start_time >= 0.2:
                    self.safe_ctr(r)
                    if self.status == MoveStatus.FAILED:
                        self.stop(r)
                    self.periodRun_start_time = time.time()
            self.check_level(r)
            """"上报液位.每1s上报一次"""
            if time.time() - self.check_level_start_time >= 1:
                self.state["operation"] = self.operation
                self.state["task_status"] = task_status
                self.state["time"] = time.strftime('%Y-%m-%d %H:%M:%S')
                r.setInfo(json.dumps(self.state))
                r.logInfo(json.dumps(self.state))
                self.check_level_start_time = time.time()
            return True
        except Exception as e:
            r.setWarning(f"periodRun error:{e}")
            self.periodRun_start_time = time.time()
            return False

    # def suspend(self, r: SimModule):
    #     self.start_time = time.time()
    #     # r.logInfo("script suspend")
    #     self.status = MoveStatus.SUSPENDED
    #
    # def cancel(self, r: SimModule):
    #     # r.logInfo("script cancel")
    #     self.status = MoveStatus.NONE

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING
        if self.init:
            if len(args) == 0:
                r.setError("pls input params can be running")
                self.status = MoveStatus.FAILED
                return self.status
            self.init = False
            self.task = args
            self.operation = self.task.get("operation", None)
            self.shift = self.task.get("shift", "MediumGear")
        # 扫地、推尘
        if self.operation:
            if self.task["operation"] == "WashStart":
                self.wash_start(r)
            elif self.task["operation"] == "WashEnd":
                self.wash_end(r)
            elif self.task["operation"] == "DustStart":
                self.dust_start(r)
            elif self.task["operation"] == "DustEnd":
                self.dust_end(r)
            elif self.task["operation"] == "check_level":
                self.check_level(r)
            else:
                r.setError("operation is wrong : {}".format(self.operation))
                self.status = MoveStatus.FAILED
                return self.status
        # 单个设备控制 addingWater
        if "addingWater" in self.task:
            if "true" in self.task["addingWater"] or "True" in self.task["addingWater"]:
                # r.setDO(self.addingWater_do, True)
                self.add_water(r)
            if "false" in self.task["addingWater"] or "False" in self.task["addingWater"]:
                r.setDO(self.addingWater_do, False)
                self.operation_status = MoveStatus.FINISHED
        if "suction_wing" in self.task:
            self.send_msg(r, "2B 80 30 01 " + '{:02x}'.format(self.task["suction_wing"]) + " 00 00 00")
            self.operation_status = MoveStatus.FINISHED
        if "jet_water" in self.task:
            self.send_msg(r, "2B 80 30 03 " + '{:02x}'.format(self.task["jet_water"]) + " 00 00 00")
            self.operation_status = MoveStatus.FINISHED
        if "water_pa" in self.task:
            self.water_pa(r, self.task["water_pa"])
        if "jet_water_valve" in self.task:
            self.jet_water_valve(r, self.task["jet_water_valve"])
        if "brain_ball_valve" in self.task:
            self.brain_ball_valve(r, self.task["brain_ball_valve"])

        if "brush_plate" in self.task:
            self.send_msg(r, "2B 80 30 02 " + '{:02x}'.format(self.task["brush_plate"]) + " 00 00 00")
            # self.send_msg(r, "2B 80 30 02 00 00 00 00")
            self.operation_status = MoveStatus.FINISHED
        if "brush_plate_lift" in self.task:
            self.brush_plate_lift(r, self.task["brush_plate_lift"])
        self.state['args'] = args
        self.state['status'] = self.status
        # r.setInfo(json.dumps(self.state))
        r.logInfo(json.dumps(self.state))
        self.status = self.operation_status
        return self.status

    def client(self, ip, port, addr, value, r):
        # 创建一个 TCP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 定义 Modbus TCP server 的 IP 和端口号
        server_ip = ip
        server_port = port
        # 连接到 Modbus TCP server
        client_socket.connect((server_ip, server_port))
        # 发送 Modbus TCP 的 ADU 到 Modbus TCP server
        client_socket.sendall(self.pack(addr, value))
        # 接收 Modbus TCP server 的返回数据
        response_adu = client_socket.recv(1024)

        unit_id = response_adu[0]  # Unit id，此处应该与写入操作中的一致
        func_code = response_adu[1]  # 功能码，此处应该与写入操作中的一致
        register_value = int.from_bytes(response_adu[-2:], byteorder='big')  # 获取写入的值
        # 接收 Modbus TCP server 的返回数据
        # 解析 Modbus TCP server 返回的 ADU
        # 检查是否写入成功
        if register_value == value:
            r.logInfo(f"Value written successfully!:{value}")
        else:
            r.logInfo(f"Value write failed!:{value}")
        # 关闭 socket 连接
        client_socket.close()

    def check_level(self, r):
        # 查詢液位-清水
        if not self.check_level_opt[0]:
            clean_gauge = self.get_proxy_info(r, cmd.CLEAN_WATER_LEVEL_GAUGE)
            self.clean_water_level = self.get_clean_filter(
                (int(clean_gauge[10:12] + clean_gauge[8:10], 16) / 4095 * 1000) / 950 * 100)
            self.state["clean_water_level"] = (int(clean_gauge[10:12] + clean_gauge[8:10],
                                                   16) / 4095 * 1000) / 950 * 100
            if self.clean_water_level > 99.9:
                self.clean_water_level = 100.
            if self.clean_water_level < 0.:
                self.clean_water_level = 0.
            if self.clean_water_level <= self.clean_water_alarm:
                r.setError(f"clean_water_level:{self.clean_water_level}")
                self.stopV1(r)
            else:
                if r.errorExits(53000):
                    r.clearError(53000)
                self.check_level_opt[0] = True
        # 查詢液位-污水
        elif self.check_level_opt[0] and not self.check_level_opt[1]:
            waste_gauge = self.get_proxy_info(r, cmd.WASTE_WATER_LEVEL_GAUGE)
            self.waste_water_level = self.get_waste_filter(
                (int(waste_gauge[10:12] + waste_gauge[8:10], 16) / 4095 * 1000) / 950 * 100)
            self.state["waste_water_level"] = (int(waste_gauge[10:12] + waste_gauge[8:10],
                                                   16) / 4095 * 1000) / 950 * 100
            if self.waste_water_level > 99.9:
                self.waste_water_level = 100.
            if self.waste_water_level < 0.:
                self.waste_water_level = 0.
            if self.waste_water_level >= self.waste_water_alarm:
                r.setError(f"waste_water_alarm:{self.waste_water_level}")
                self.stopV1(r)
            else:
                if r.errorExits(53000):
                    r.clearError(53000)
                self.check_level_opt[1] = True
        elif self.check_level_opt[1] and not self.check_level_opt[2]:
            # 上报液位
            self.client(self.ip, self.port, self.report_addr_1, int(self.clean_water_level), r)
            self.check_level_opt[2] = True
            # 上报液位
        elif self.check_level_opt[2] and not self.check_level_opt[3]:
            self.client(self.ip, self.port, self.report_addr_2, int(self.waste_water_level), r)
            self.check_level_opt[3] = True
        if all(self.check_level_opt):
            self.check_level_opt = [False] * 4
        self.state["cleanRobot"] = {
            "cleanWaterLevel": int(self.clean_water_level),
            "wasteWaterLevel": int(self.waste_water_level)
        }

    def block_wash_end(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                JetWater("close"),
                BrushPlate("close"),
                SuctionWing("close")
            ]
        else:
            self.run_tak_list(r)

    def re_wash_startV1(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                SuctionWing("open", self.shift),
                JetWater("open", self.shift),
                BrushPlate("open", self.shift, wash_time=self.wash_start_time)
            ]
        else:
            self.run_tak_list(r)

    def re_wash_start(self, r):
        r.logDebug("---------------re_wash_start-------------------")
        # 吸风电机
        if not self.block_re_start_opt[0]:
            self.send_msg(r, "2B 80 30 01 " + shift(self.shift, "FJ") + " 00 00 00")
            self.block_re_start_opt[0] = True
        elif not self.block_re_start_opt[1] and self.block_re_start_opt[0]:
            self.send_msg(r, "2B 80 30 01 " + shift(self.shift, "FJ") + " 00 00 00")
            self.block_re_start_opt[1] = True

        elif not self.block_re_start_opt[2] and self.block_re_start_opt[1]:
            self.send_msg(r, "2B 80 30 03 " + shift(self.shift, "SB") + " 00 00 00")
            self.block_re_start_opt[2] = True
        elif not self.block_re_start_opt[3] and self.block_re_start_opt[2]:
            self.send_msg(r, "2B 80 30 03 " + shift(self.shift, "SB") + " 00 00 00")
            self.block_re_start_opt[3] = True

        elif not self.block_re_start_opt[4] and self.block_re_start_opt[3]:
            self.send_msg(r, "2B 80 30 02 " + shift(self.shift, "SP") + " 00 00 00")
            self.block_re_start_opt[4] = True
        elif not self.block_re_start_opt[5] and self.block_re_start_opt[4]:
            self.send_msg(r, "2B 80 30 02 " + shift(self.shift, "SP") + " 00 00 00")
            self.block_re_start_opt[5] = True

        elif not self.block_re_start_opt[6] and self.block_re_start_opt[3]:
            self.send_msg(r, "2B 80 30 06 64 00 00 00")
            self.block_re_start_opt[6] = True
        elif not self.block_re_start_opt[7] and self.block_re_start_opt[4]:
            self.send_msg(r, "2B 80 30 06 64 00 00 00")
            self.block_re_start_opt[7] = True
            self.block_first = False

    def stop(self, r: SimModule, tpy=False):
        r.logDebug("--------------------stop----------------------")
        # 停止吸风电机
        if not self.block_stop_opt[0]:
            self.send_msg(r, "2B 80 30 01 00 00 00 00")
            self.block_stop_opt[0] = True
        elif not self.block_stop_opt[1] and self.block_stop_opt[0]:
            self.send_msg(r, "2B 80 30 01 00 00 00 00")
            self.block_stop_opt[1] = True
            # 停止喷水电机
        elif not self.block_stop_opt[2] and self.block_stop_opt[1]:
            self.send_msg(r, "2B 80 30 03 00 00 00 00")
            self.block_stop_opt[2] = True
        elif not self.block_stop_opt[3] and self.block_stop_opt[2]:
            self.send_msg(r, "2B 80 30 03 00 00 00 00")
            self.block_stop_opt[3] = True
            # 停止刷盘
        elif not self.block_stop_opt[4] and self.block_stop_opt[3]:
            self.send_msg(r, "2B 80 30 02 00 00 00 00")
            self.block_stop_opt[4] = True
        elif not self.block_stop_opt[5] and self.block_stop_opt[4]:
            self.send_msg(r, "2B 80 30 02 00 00 00 00")
            self.block_stop_opt[5] = True
        # 关闭水阀
        elif not self.block_stop_opt[6] and self.block_stop_opt[5]:
            self.send_msg(r, "2B 80 30 06 00 00 00 00")
            self.block_stop_opt[6] = True
        elif not self.block_stop_opt[7] and self.block_stop_opt[6]:
            self.send_msg(r, "2B 80 30 06 00 00 00 00")
            self.block_stop_opt[7] = True

    def stopV1(self, r: SimModule, tpy=False):
        r.logDebug("--------------------stop----------------------")
        # 停止吸风电机
        if not self.block_stop_opt[0]:
            self.send_msg(r, "2B 80 30 01 00 00 00 00")
            self.block_stop_opt[0] = True
        elif not self.block_stop_opt[1] and self.block_stop_opt[0]:
            self.send_msg(r, "2B 80 30 01 00 00 00 00")
            self.block_stop_opt[1] = True
            # 停止喷水电机
        elif not self.block_stop_opt[2] and self.block_stop_opt[1]:
            self.send_msg(r, "2B 80 30 03 00 00 00 00")
            self.block_stop_opt[2] = True
        elif not self.block_stop_opt[3] and self.block_stop_opt[2]:
            self.send_msg(r, "2B 80 30 03 00 00 00 00")
            self.block_stop_opt[3] = True
            # 停止刷盘
        elif not self.block_stop_opt[4] and self.block_stop_opt[3]:
            self.send_msg(r, "2B 80 30 02 00 00 00 00")
            self.block_stop_opt[4] = True
        elif not self.block_stop_opt[5] and self.block_stop_opt[4]:
            self.send_msg(r, "2B 80 30 02 00 00 00 00")
            self.block_stop_opt[5] = True
        # 关闭水阀
        elif not self.block_stop_opt[6] and self.block_stop_opt[5]:
            self.send_msg(r, "2B 80 30 06 00 00 00 00")
            self.block_stop_opt[6] = True
        elif not self.block_stop_opt[7] and self.block_stop_opt[6]:
            self.send_msg(r, "2B 80 30 06 00 00 00 00")
            self.block_stop_opt[7] = True
        if all(self.block_stop_opt):
            return True

    def safe_ctr(self, r: SimModule):
        safe_state = dict()
        block = r.isAnyErrorExists()  # 任务错误
        error_52316 = r.errorExits(52316)  # 下发速度超时
        warning_54231 = r.warningExits(54231)  # 调度报阻挡
        if (not error_52316) and (
                block or warning_54231) and not self.block_first and self.status == MoveStatus.FINISHED:
            self.block_first = True
            self.block_start_time = time.time()
            self.block_stop_opt = [False] * 8
            self.block_re_start_opt = [False] * 8
        if self.block_first:
            if time.time() - self.block_start_time > 1 and not all(self.block_stop_opt):
                self.stop(r)
        if not block and self.block_first and all(self.block_stop_opt) and r.getCurrentTaskStatus() == 2 and not all(
                self.block_re_start_opt):
            self.re_start(r)

        safe_state["block"] = block
        safe_state["block_start_time"] = self.block_start_time
        safe_state["all(self.block_stop_opt)"] = all(self.block_stop_opt)
        safe_state["all(self.block_re_start_opt)"] = all(self.block_re_start_opt)
        safe_state["block_first"] = self.block_first
        self.state["safe_ctr"] = safe_state

    def re_start(self, r: SimModule):
        if not int(self.clean_water_level) < self.clean_water_alarm and not int(
                self.waste_water_level) > self.waste_water_alarm:
            self.re_wash_start(r)
        else:
            r.setError(
                f"clean_water_level :{int(self.clean_water_level)} ,waste_water_level:{int(self.waste_water_level)}")
            self.status = MoveStatus.FAILED

    def pack(self, addr, v):
        def crc16(data):
            """
            计算 Modbus CRC16 校验码
            """
            crc = 0xFFFF
            for b in data:
                crc ^= b
                for _ in range(8):
                    if crc & 0x0001:
                        crc >>= 1
                        crc ^= 0xA001
                    else:
                        crc >>= 1
            return crc

        # 构造 Modbus TCP 协议中的 PDU
        unit_id = 1  # Modbus device 的 unit id
        func_code = 6  # 写单个寄存器的功能码
        register_addr = addr  # 寄存器地址，假设为 4x0001
        register_value1 = v  # 待写入的值，假设为 0xFFFF

        pdu = bytearray()
        pdu += unit_id.to_bytes(1, byteorder='big')
        pdu += func_code.to_bytes(1, byteorder='big')
        pdu += register_addr.to_bytes(2, byteorder='big')
        pdu += register_value1.to_bytes(2, byteorder='big')

        # 构造 Modbus TCP 的 ADU
        transaction_id = 1  # Modbus' transaction id，此处设为 1
        protocol_id = 0  # Modbus protocol id，此处设为 0
        length = len(pdu) + 1  # ADU 长度为 PDU 长度加 1（unit id 的长度）
        adu = bytearray()
        adu += transaction_id.to_bytes(2, byteorder='big')
        adu += protocol_id.to_bytes(2, byteorder='big')
        adu += length.to_bytes(2, byteorder='big')
        adu += pdu
        # 计算 CRC-16 校验码
        crc16 = crc16(pdu)
        adu += crc16.to_bytes(2, byteorder='big')
        return adu

    def wash_start(self, r):
        if int(self.clean_water_level) < self.clean_water_alarm and int(
                self.waste_water_level) > self.waste_water_alarm:
            r.setError(
                f"clean_water_level :{int(self.clean_water_level)} ,waste_water_level:{int(self.waste_water_level)}")
            self.status = MoveStatus.FAILED
            return
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                BrushPlateLift("down"),
                WaterPaLift("down"),
                SuctionWing("open", self.shift),
                JetWaterValve("open"),
                JetWater("open", self.shift),
                BrushPlate("open", self.shift, wash_time=self.wash_start_time)
            ]
        else:
            self.run_tak_list(r)

    def wash_end(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                JetWater("close"),
                JetWaterValve("close"),
                BrushPlate("close"),
                BrushPlateLift("up"),
                WaterPaLift("up"),
                SuctionWing("close")
            ]
        else:
            self.run_tak_list(r)

    def dust_start(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                WaterPaLift("down")
            ]
        else:
            self.run_tak_list(r)

    def dust_end(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                WaterPaLift("up")
            ]
        else:
            self.run_tak_list(r)

    def get_proxy_info(self, r: SimModule, msg):
        for i in range(10):
            flag = False
            data = dict()
            if not flag:
                time.sleep(0.01)
                flag = True
                data = self._send_get(r, msg)
                can_frame_id_res = data["ID"]
                if can_frame_id_res + 128 != self.can_id:
                    flag = False
                d_data = data["Data"]
                dict_obj = msg[3:5] + msg[6:8] + msg[9:11]
                dict_obj_res = d_data[2:8]
                if dict_obj != dict_obj_res:
                    flag = False
            if flag:
                return data["Data"]
            if i == 9:
                return "0000000000000000"
        return "0000000000000000"

    def get_info(self, r: SimModule):
        device = {
            "suction_wing":1,
            "brush_plate":1,
            "jet_water":1,
            "braun_ball_valve":1,
            "brush_plate_lift":1,
            "jet_water_valve":1,
            "water_pa":1,
        }
        get_can_frame = dict()
        get_can_frame["suction_wing"] = self.get_proxy_info(r, cmd.SUCTION_WING_GET)
        get_can_frame["brush_plate"] = self.get_proxy_info(r, cmd.BRUSH_PLATE_GET)
        get_can_frame["jet_water"] = self.get_proxy_info(r, cmd.WATER_JET_MOTOR_GET)
        get_can_frame["braun_ball_valve"] = self.get_proxy_info(r, cmd.BRAIN_BALL_VALVE_GET)
        get_can_frame["brush_plate_lift"] = self.get_proxy_info(r, cmd.BRUSH_PLATE_LIFT_GET)
        get_can_frame["jet_water_valve"] = self.get_proxy_info(r, cmd.JET_WATER_VALVE__GET)
        get_can_frame["water_pa"] = self.get_proxy_info(r, cmd.WATER_PA_LIFT_GET)
        clean_gauge = self.get_proxy_info(r, cmd.CLEAN_WATER_LEVEL_GAUGE)
        self.clean_water_level_add = (int(clean_gauge[10:12] + clean_gauge[8:10], 16) / 4095 * 1000) / 950 * 100
        waste_gauge = self.get_proxy_info(r, cmd.WASTE_WATER_LEVEL_GAUGE)
        self.waste_water_level = (int(waste_gauge[10:12] + waste_gauge[8:10], 16) / 4095 * 1000) / 950 * 100
        self.state["getCanFrame_all"] = get_can_frame
        return

    # 用于单个设备控制
    def send_msg(self, r: SimModule, msg):
        can_frame = dict()
        data = self.get_proxy_info(r, msg)
        can_frame["sendCanFrame"] = f'{self.chanel} {self.can_id} {self.dlc} {self.extend} {msg}'
        can_frame["getCanFrame"] = data
        self.state["CanFrame"] = can_frame

    def _send_get(self, r: SimModule, msg):
        r.sendCanFrame(self.chanel, self.can_id, self.dlc, self.extend, msg)
        data = r.getCanFrame()
        b64_str = data["Data"]
        # print(b64_str, type(b64_str))
        byte_str = base64.b64decode(b64_str)
        hex_str = byte_str.hex().upper()
        # print(hex_str[0], hex_str[1], hex_str[2], hex_str[3], hex_str[6], hex_str[7])
        data["Data"] = hex_str
        return data

    def run_tak_list(self, r):
        if self.task_id < len(self.task_list):
            if self.task_list[self.task_id].status == MoveStatus.NONE:
                self.task_list[self.task_id].reset(self)
            elif self.task_list[self.task_id].status == MoveStatus.FINISHED:
                self.task_id = self.task_id + 1
            elif self.task_list[self.task_id].status == MoveStatus.FAILED:
                self.operation_status = MoveStatus.FAILED
            else:
                self.task_list[self.task_id].run(r, self)
        else:
            self.operation_status = MoveStatus.FINISHED

    def brush_plate_lift(self, r: SimModule, opt):
        if opt == "up":
            self.send_msg(r, "2B 80 30 04 64 00 00 00")
        elif opt == "down":
            self.send_msg(r, "2B 80 30 04 FF 9C 00 00")
        else:
            r.setError(f"pls input up or down")
            self.operation_status = MoveStatus.FAILED
        if ModuleTool.delay(10):
            self.send_msg(r, "2B 80 30 04 00 00 00 00")
            self.operation_status = MoveStatus.FINISHED

    def brain_ball_valve(self, r, opt):
        if opt == "open":
            self.send_msg(r, "2B 80 30 07 64 00 00 00")
            self.operation_status = MoveStatus.FINISHED
        elif opt == "close":
            self.send_msg(r, "2B 80 30 07 00 00 00 00")
            self.operation_status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input open or close")
            self.operation_status = MoveStatus.FAILED

    def jet_water_valve(self, r, opt):
        if opt == "open":
            self.send_msg(r, "2B 80 30 06 64 00 00 00")
            self.operation_status = MoveStatus.FINISHED
        elif opt == "close":
            self.send_msg(r, "2B 80 30 06 00 00 00 00")
            self.operation_status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input open or close")
            self.operation_status = MoveStatus.FAILED

    def water_pa(self, r, opt):
        self.send_msg(r, "2B 80 30 05 00 00 00 00")
        if opt == "up":
            self.send_msg(r, "2B 80 30 05 FF 9C 00 00")
            time.sleep(0.1)
            self.send_msg(r, "2B 80 30 05 FF 9C 00 00")
        elif opt == "down":
            self.send_msg(r, "2B 80 30 05 64 00 00 00")
            time.sleep(0.1)
            self.send_msg(r, "2B 80 30 05 64 00 00 00")
        else:
            r.setError(f"pls input up or down")
            self.operation_status = MoveStatus.FAILED
        if ModuleTool.delay(1):
            self.operation_status = MoveStatus.FINISHED

    def add_water(self, r):
        if self.operation_status == MoveStatus.NONE:
            self.operation_status = MoveStatus.RUNNING
            self.task_list = [
                AddWater(),
                DelayTime(8)  # 延时5s
            ]
        else:
            self.run_tak_list(r)


class BrushPlateLift:
    """
        刷盘升降电机
    """

    def __init__(self, opt: str):
        self.status = MoveStatus.NONE
        self.opt = opt

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m_state = dict()
        if self.opt == "up":
            m.send_msg(r, "2B 80 30 04 64 00 00 00")
            self.status = MoveStatus.FINISHED
        elif self.opt == "down":
            m.send_msg(r, "2B 80 30 04 FF 9C 00 00")
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input up or down")
            self.status = MoveStatus.FAILED
        m_state["status"] = self.status
        m.state["BrushPlateLift"] = m_state


class BrushPlate:
    """
        刷盘电机
    """

    def __init__(self, opt: str, s: str = "lowGear", wash_time=10):
        self.status = MoveStatus.NONE
        self.opt = opt
        self.shift = s
        self.wash_time = wash_time

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m_state = dict()
        gear = shift(self.shift, "SP")
        if self.opt == "open":
            m.send_msg(r, "2B 80 30 02 " + gear + " 00 00 00")
            if ModuleTool.delay(self.wash_time):
                m.send_msg(r, "2B 80 30 02 " + gear + " 00 00 00")
                self.status = MoveStatus.FINISHED
        elif self.opt == "close":
            m.send_msg(r, "2B 80 30 02 00 00 00 00")
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input open or close")
            self.status = MoveStatus.FAILED

        m_state["status"] = self.status
        m.state["BrushPlate"] = m_state


class WaterPaLift:
    """
        水扒升降电机
    """

    def __init__(self, opt: str):
        self.status = MoveStatus.NONE
        self.opt = opt

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m_state = dict()
        if self.opt == "up":
            m.send_msg(r, "2B 80 30 05 FF 9C 00 00")
            self.status = MoveStatus.FINISHED
        elif self.opt == "down":
            m.send_msg(r, "2B 80 30 05 64 00 00 00")
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input up or down")
            self.status = MoveStatus.FAILED
        m_state["status"] = self.status
        m.state["WaterPush"] = m_state


class SuctionWing:
    """
        吸风电机
    """

    def __init__(self, opt: str, s: str = "lowGear"):
        self.status = MoveStatus.NONE
        self.opt = opt
        self.shift = s

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m_state = dict()
        gear = shift(self.shift, "FJ")
        if self.opt == "open":
            m.send_msg(r, "2B 80 30 01 " + gear + " 00 00 00")
            self.status = MoveStatus.FINISHED
        elif self.opt == "close":
            m.send_msg(r, "2B 80 30 01 00 00 00 00")
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input up or down")
            self.status = MoveStatus.FAILED
        m_state["status"] = self.status
        m.state["SuctionWing"] = m_state


def shift(sh: str, d: str = "") -> str:
    s = "08"
    if sh == "lowGear":
        s = "08"
    if sh == "light":
        s = "0"
    if sh == "highGear":
        s = "58"
        # 轻度：风机40% 水泵15% 刷盘50%
        # 标准：风机50%水泵 30% 刷盘67%
        # 重度：风机70% 水泵50% 刷盘67%
    if sh == "MediumGear":
        if d == "FJ":
            s = "60"
        if d == "SB":
            s = "10"
        if d == "SP":
            s = "32"
    if sh == "normal":
        if d == "FJ":
            s = "32"
        if d == "SB":
            s = "1E"
        if d == "SP":
            s = "43"
    if sh == "heavy":
        if d == "FJ":
            s = "46"
        if d == "SB":
            s = "32"
        if d == "SP":
            s = "43"
    return s


class JetWaterValve:
    """
        喷水泵电磁阀
    """

    def __init__(self, opt: str):
        self.status = MoveStatus.NONE
        self.opt = opt

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m_state = dict()
        if self.opt == "open":
            m.send_msg(r, "2B 80 30 06 64 00 00 00")
            self.status = MoveStatus.FINISHED
        elif self.opt == "close":
            m.send_msg(r, "2B 80 30 06 00 00 00 00")
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input open or close")
            self.status = MoveStatus.FAILED
        m_state["status"] = self.status
        m.state["JetWaterValve"] = m_state


class JetWater:
    """
        喷水泵电机
    """

    def __init__(self, opt: str, s: str = "lowGear"):
        self.shift = s
        self.status = MoveStatus.NONE
        self.opt = opt

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m_state = dict()
        gear = shift(self.shift, "SB")
        if self.opt == "open":
            m.send_msg(r, "2B 80 30 03 " + gear + " 00 00 00")
            self.status = MoveStatus.FINISHED
        elif self.opt == "close":
            m.send_msg(r, "2B 80 30 03 00 00 00 00")
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input open or close")
            self.status = MoveStatus.FAILED
        m_state["status"] = self.status
        m.state["JetWater"] = m_state


class DrainBallValve:
    """
        排水球阀
    """

    def __init__(self, opt: str):
        self.status = MoveStatus.NONE
        self.opt = opt

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        m_state = dict()
        if self.opt == "open":
            m.send_msg(r, "2B 80 30 07 64 00 00 00")
            self.status = MoveStatus.FINISHED
        elif self.opt == "close":
            m.send_msg(r, "2B 80 30 07 00 00 00 00")
            self.status = MoveStatus.FINISHED
        else:
            r.setError(f"pls input open or close")
            self.status = MoveStatus.FAILED
        m_state["status"] = self.status
        m.state["DrainBallValve"] = m_state


class AddWater:
    """
        自动加水
    """

    def __init__(self):
        self.status = MoveStatus.NONE
        self.is_open = False
        self.is_waste = False

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        m_state = dict()
        clean_gauge = m.get_proxy_info(r, cmd.CLEAN_WATER_LEVEL_GAUGE)
        clean_water_level_add = (int(clean_gauge[10:12] + clean_gauge[8:10], 16) / 4095 * 1000) / 950 * 100
        if clean_water_level_add >= m.addingWater_limit_level:
            if ModuleTool.check_DO(r, m.addingWater_do):
                r.setDO(m.addingWater_do, False)
        else:
            if not ModuleTool.check_DO(r, m.addingWater_do):
                r.setDO(m.addingWater_do, True)
        if m.waste_water_level > 0:
            if not self.is_waste:
                m.send_msg(r, "2B 80 30 07 64 00 00 00")
                time.sleep(0.1)
                m.send_msg(r, "2B 80 30 07 64 00 00 00")
                self.is_waste = True
        if m.waste_water_level <= 1:
            m.send_msg(r, "2B 80 30 07 00 00 00 00")

        if m.waste_water_level <= 1 and clean_water_level_add >= m.addingWater_limit_level:
            m.send_msg(r, "2B 80 30 07 00 00 00 00")
            time.sleep(0.1)
            m.send_msg(r, "2B 80 30 07 00 00 00 00")
            time.sleep(0.1)
            m.send_msg(r, "2B 80 30 07 00 00 00 00")
            r.setDO(m.addingWater_do, False)
            self.status = MoveStatus.FINISHED
        m_state["clean_water_level_add"] = clean_water_level_add
        m_state["waste_water_level"] = m.waste_water_level
        m_state["AddWater_status"] = "Adding Water ..."
        m_state["status"] = self.status
        m_state["is_open"] = self.is_open
        m.state["AddWater"] = m_state


class MeanValue:
    """均值滤波
    """

    def __init__(self, windowSize=2000):
        """_summary_

        Args:
            windowSize (_type_): 窗口大小，默认值为 2000
        """
        super().__init__()
        self.w = windowSize
        self.data = []
        self.threshold = 10

    def setValue(self, v):
        if abs(v - self.getMeanValue()) < self.threshold:
            self.data.append(v)
        while len(self.data) > self.w:
            self.data.pop(0)

    def getMeanValue(self) -> float:
        return sum(self.data) / len(self.data)


class DelayTime:
    """延时指定时间"""
    def __init__(self, time_delay):
        super().__init__()
        self.status = MoveStatus.NONE
        self.time_delay = time_delay
        self.start = time.time()
        self.init = True

    def reset(self, m: Module):
        self.status = MoveStatus.RUNNING

    def run(self, r: SimModule, m: Module):
        self.status = MoveStatus.RUNNING
        if self.init:
            self.start = time.time()
            self.init = False
        task_state = dict()
        if not self.init and time.time() - self.start >= self.time_delay:
            self.status = MoveStatus.FINISHED
        task_state["time"] = self.time_delay
        task_state["start"] = self.start
        task_state["status"] = self.status
        task_state["time"] = time.time()
        m.state["DelayTime"] = task_state