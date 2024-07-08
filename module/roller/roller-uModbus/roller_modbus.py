# -*- coding: utf-8 -*-
# @Date : 2024/4/22
# @Author : CHL
# @File :
# @Version : 1.0
# @Update :
# 通过ModbusTcp的通讯方式与客户的PLC进行通讯
# 根据不同的上下料往相应的地址为里面写值，滚筒机构的上下料运行和到位检测均为客户的PLC自行判断运行
"""
依赖uModbus库：
方式1: pip安装
pip install uModbus
方式2: whl安装, 依次安装pyserial和uModbus
# 下载pyserial
https://files.pythonhosted.org/packages/0d/e4/2a744dd9e3be04a0c0907414e2a01a7c88bb3915cbe3c8cc06e209f59c30/pyserial-3.4-py2.py3-none-any.whl
# 安装uModbus
/usr/bin/python3 -m pip install pyserial-3.4-py2.py3-none-any.whl
# 下载uModbus
https://files.pythonhosted.org/packages/d1/b9/664b226d34cc5154dfd0f92ccfaa6cb03dd3d2f77951c0d67eedb74ace5b/uModbus-1.0.4-py2.py3-none-any.whl
# 安装uModbus
/usr/bin/python3 -m pip install uModbus-1.0.4-py2.py3-none-any.whl
"""

import json

from rbkSim import SimModule
from rbk import MoveStatus, BasicModule, ParamServer

from address.all import ALL
from address.roller import ROLLER
from address.version import Version

from socket import create_connection
from umodbus import conf
from umodbus.client import tcp

# 定义机构脚本运行时用户需要传入的参数
# 脚本运行时，Robokit会检测脚本参数，若参数格式无误，则脚本参数会传给Module类方法中args参数，args参数为dict类型
"""
####BEGIN DEFAULT ARGS####
{
    "operation_roller":{
        "value": "",
        "default_value":[
            "front_pre_load", "front_load", "front_unload", "front_roll",
            "back_pre_load", "back_load", "back_unload", "back_roll",
            "left_pre_load", "left_load", "left_unload", "left_roll",
            "right_pre_load", "right_load", "right_unload", "right_roll",
            "stop", "front_back_inverse", "left_right_inverse", "left_pass", "right_pass"
        ],
        "tips": "选择roller模式",
        "type": "complex"
    },

    "ip":{
        "value": "192.168.192.6",
        "default_value":"192.168.192.6",
        "tips": "外设IP",
        "type": "string"
    },
    "port":{
        "value": "502",
        "default_value": "502",
        "tips": "Modbus TCP端口",
        "type": "int"
    },
    "salve_id":{
        "value": "1",
        "default_value":1,
        "tips": "从机设备ID",
        "type": "int"
    } 
}
####END DEFAULT ARGS####
"""


class Module(BasicModule):
    def __init__(self, r: SimModule, args):
        super(Module, self).__init__()

        p = ParamServer(__file__)
        self.ip = p.loadParam("ModbusIP", type="str", default="192.168.192.6", comment="外设 ModbusTCP IP 地址")
        r.logInfo("ip: " + str(self.ip))
        self.port = p.loadParam("ModbusPort", type="int", default=502, minValue=0, maxValue=65535,
                                comment="外设 ModbusTCP 端口")
        r.logInfo("port: " + str(self.port))
        self.use_input = p.loadParam("UseInput", type="bool", default=True, comment="外设 ModbusTCP 允许使用只读地址位")
        r.logInfo("use_input: " + str(self.use_input))
        self.err_report_thresh = p.loadParam("ErrReportThresh", type="int", default=1, minValue=1, maxValue=100,
                                             comment="外设 ModbusTCP 连接有问题次数>该参数才进行报错")
        self.re_control_cnts = p.loadParam("ReControlCnts", type="int", default=1, minValue=1, maxValue=100,
                                           comment="Action中允许失败该参数次才进行报错")
        self.user_data_max_count = p.loadParam("UserDataMaxCount", type="int", default=16, minValue=16, maxValue=128,
                                               comment="外围用户数据最大计数")

        self.report_info = dict()
        self.state = dict()
        self.status = MoveStatus.NONE
        self.ip = args.get("ip", self.ip)
        self.port = args.get("port", self.port)
        self.slave_id = args.get("salve_id", 1)
        self.operation_roller = args.get("operation_roller", None)
        # 如果operation_roller操作为空，则报错
        if self.operation_roller is None:
            self.status = MoveStatus.FAILED
            r.setError("operation error")
        self.modbus_sock = None

        self.roller_state = 0
        self.roller_error_code = 0

    def modbus_connect(self, r: SimModule):
        # 如果已经建立连接，退出函数
        if self.modbus_sock is not None:
            return True
        # Enable values to be signed (default is False).
        conf.SIGNED_VALUES = True

        try:
            self.modbus_sock = create_connection((self.ip, self.port), timeout=1.5)
            version = self.modbus_read_register(r, ALL.VERSION())
        except Exception as e:
            if self.modbus_sock is not None:
                self.modbus_sock.close()
                self.modbus_sock = None
            r.setError(f"Peripheral connect error|{e}")
            return False
        else:
            r.logInfo("Peripheral connect success")
            if version == 1:
                Version.set_version(1)
            if version == 2:
                Version.set_version(2)
            else:
                r.setError(f"Peripheral protocol version {version} , error")
            return True
        finally:
            r.logInfo("get_version: " + str(Version.get_version()))

    def run(self, r: SimModule, args):
        self.status = MoveStatus.RUNNING

        # 建立连接
        if not self.modbus_connect(r):
            self.status = MoveStatus.FAILED
            return MoveStatus.FAILED
        # 读取辊筒状态
        self.handle_status(r)

        if self.operation_roller == "front_pre_load":
            self.modbus_write_register(r, ROLLER.ROLLER_FRONT_PRE_LOAD(), 1)
        if self.operation_roller == "front_load":
            self.modbus_write_register(r, ROLLER.ROLLER_FRONT_LOAD(), 1)
        if self.operation_roller == "front_unload":
            self.modbus_write_register(r, ROLLER.ROLLER_FRONT_UNLOAD(), 1)
        if self.operation_roller == "front_roll":
            self.modbus_write_register(r, ROLLER.ROLLER_FRONT_ROLL(), 1)
        if self.operation_roller == "back_pre_load":
            self.modbus_write_register(r, ROLLER.ROLLER_BACK_PRE_LOAD(), 1)
        if self.operation_roller == "back_load":
            self.modbus_write_register(r, ROLLER.ROLLER_BACK_LOAD(), 1)
        if self.operation_roller == "back_unload":
            self.modbus_write_register(r, ROLLER.ROLLER_BACK_UNLOAD(), 1)
        if self.operation_roller == "back_roll":
            self.modbus_write_register(r, ROLLER.ROLLER_BACK_ROLL(), 1)
        if self.operation_roller == "left_pre_load":
            self.modbus_write_register(r, ROLLER.ROLLER_LEFT_PRE_LOAD(), 1)
        if self.operation_roller == "left_load":
            self.modbus_write_register(r, ROLLER.ROLLER_LEFT_LOAD(), 1)
        if self.operation_roller == "left_unload":
            self.modbus_write_register(r, ROLLER.ROLLER_LEFT_UNLOAD(), 1)
        if self.operation_roller == "left_roll":
            self.modbus_write_register(r, ROLLER.ROLLER_LEFT_ROLL(), 1)
        if self.operation_roller == "right_pre_load":
            self.modbus_write_register(r, ROLLER.ROLLER_RIGHT_PRE_LOAD(), 1)
        if self.operation_roller == "right_load":
            self.modbus_write_register(r, ROLLER.ROLLER_RIGHT_LOAD(), 1)
        if self.operation_roller == "right_unload":
            self.modbus_write_register(r, ROLLER.ROLLER_RIGHT_UNLOAD(), 1)
        if self.operation_roller == "right_roll":
            self.modbus_write_register(r, ROLLER.ROLLER_RIGHT_ROLL(), 1)
        if self.operation_roller == "stop":
            self.modbus_write_register(r, ROLLER.ROLLER_STOP(), 1)
        if self.operation_roller == "front_back_inverse":
            self.modbus_write_register(r, ROLLER.ROLLER_FRONT_BACK_INVERSE(), 1)
        if self.operation_roller == "left_right_inverse":
            self.modbus_write_register(r, ROLLER.ROLLER_LEFT_RIGHT_INVERSE(), 1)
        if self.operation_roller == "left_pass":
            self.modbus_write_register(r, ROLLER.ROLLER_LEFT_PASS(), 1)
        if self.operation_roller == "right_pass":
            self.modbus_write_register(r, ROLLER.ROLLER_RIGHT_PASS(), 1)
        self.operation_roller = None

        if self.status is MoveStatus.FAILED or self.status is MoveStatus.FINISHED:
            if self.modbus_sock is not None:
                self.modbus_sock.close()
                self.modbus_sock = None

        status = dict()
        status["roller_state"] = self.roller_state
        status["roller_error_code"] = self.roller_error_code
        self.report_info['args'] = args
        self.report_info['task_status'] = self.status
        self.report_info['status'] = status

        r.setInfo(json.dumps(self.report_info))
        r.logInfo(json.dumps(self.report_info))
        return self.status

    def send_message(self, r: SimModule, message, addr):
        try:
            response = tcp.send_message(message, self.modbus_sock)
        except Exception as e:
            r.setError(f"[send_message]|[addr:{addr}]|error:{e}")
            return None
        else:
            return response

    def modbus_read_input_bit(self, r: SimModule, addr):
        if self.use_input:
            message = tcp.read_discrete_inputs(self.slave_id, addr, 1)
        else:
            message = tcp.read_coils(self.slave_id, addr, 1)
        response = self.send_message(r, message, addr)
        if response is None:
            return None
        return response

    def modbus_read_register(self, r: SimModule, addr):
        if self.use_input:
            message = tcp.read_input_registers(self.slave_id, addr, 1)
        else:
            message = tcp.read_holding_registers(self.slave_id, addr, 1)
        response = self.send_message(r, message, addr)
        if response is None:
            return None
        return response[0]

    def modbus_write_register(self, r: SimModule, addr, value=1):
        message = tcp.write_single_coil(self.slave_id, addr, value)
        response = self.send_message(r, message, addr)
        if response is None:
            self.status = MoveStatus.FAILED
            r.setError(f"roller error, modbus_write_register: {addr}")
            return False
        self.status = MoveStatus.FINISHED
        return True

    def getErrorCode(self, r: SimModule, error_code_addr):
        error_code = self.modbus_read_register(r, ALL.ERROR_CODE())
        # 读取系统错误码失败
        if error_code is None:
            r.setError(f"getErrorCode ALL.ERROR_CODE error, modbus_read_register: {ALL.ERROR_CODE()}")
            return None
        # 系统没有错误码
        if error_code == 0:
            error_code = self.modbus_read_register(r, error_code_addr)
            # 读取滚筒错误码失败
            if error_code is None:
                r.setError(f"getErrorCode ROLLER.ROLLER_ERROR_CODE error, modbus_read_register: {error_code_addr}")
                return None
            return error_code
        return error_code

    def handle_status(self, r: SimModule):
        # Roller
        roller_emc = self.modbus_read_input_bit(r, ALL.EMC())
        roller_mode = self.modbus_read_input_bit(r, ALL.MODE())
        roller_is_full = self.modbus_read_input_bit(r, ROLLER.ROLLER_IS_FULL())
        roller_state = self.modbus_read_register(r, ROLLER.ROLLER_STATE())
        roller_speed = self.modbus_read_register(r, ROLLER.ROLLER_SPEED_LEVEL())
        roller_error_code = self.getErrorCode(r, ROLLER.ROLLER_ERROR_CODE())
        roller_status = [roller_emc, roller_mode, roller_is_full, roller_state, roller_speed, roller_error_code]
        r.logInfo("roller_status:" + str(roller_status))
        # 读取成功
        if roller_status is not None:
            self.roller_state = roller_state
            self.roller_error_code = roller_error_code
            # server有系统错误码
            if roller_error_code != 0:
                # 如果仿真还没有错误码52030，则设置错误码52030
                if not r.errorExits(52030):
                    r.setError(f"[52030][Roller error][Modbus error code: {roller_error_code}]")
                r.logDebug(
                    f"SeerRoller error: {roller_error_code}, emc: {roller_emc}, state: {roller_state}, "
                    f"is_full: {roller_is_full}, mode: {roller_mode}")
                return False
            # server没有错误码
            else:
                # 如果仿真还存在错误码52030，则清除错误码52030
                if r.errorExits(52030):
                    r.clearError(52030)
                r.logDebug(
                    f"RollerStatus: {self.roller_state}, error_code: {self.roller_error_code}, mode: {roller_mode}, "
                    f"is_full: {roller_is_full}, speed: {roller_speed}, emc: {roller_emc}")
                return True
        else:
            return False

    def cancel(self, r):
        # =====处理任务取消时的业务=====
        r.setNotice(f"cancel task")
        if self.modbus_sock is not None:
            self.modbus_sock.close()
        self.status = MoveStatus.NONE

    def suspend(self, r):
        # =====处理任务暂停时的业务=====
        r.setNotice(f"suspend task")
        self.status = MoveStatus.SUSPENDED