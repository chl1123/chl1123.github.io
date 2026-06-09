import sys, json
# 导入电池基类
import syspy.battery_Serial.battery_base as bb
import syspy.lib.char_utility as cu
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
# 打印工具类

from syspy.utils.param_server import ParamType, ScriptParam
from syspy import Trace

from syspy.battery_runner import run_battery_script
param_loader = ScriptParam(__file__)

class ConfigParams:
    config = {}
    devName = None
    baudrate = None
    timeoutThreshold = None

    def __init__(self):
        self._build_and_load_config()

    @classmethod
    def _build_and_load_config(cls):
        builder = param_loader.builderConfig()
        with builder.GROUPS():
            with builder.GROUP(key="devName", name="Serial Port", desc="串行端口对应的设备名"):
                builder.TYPE(ParamType.STRING)
                builder.DEFAULTVALUE("/dev/ttyS8")
            with builder.GROUP(key="baudrate", name="Baudrate", desc="波特率"):
                builder.TYPE(ParamType.UINT)
                builder.DEFAULTVALUE(9600)
            with builder.GROUP(key="timeoutThreshold", name="timeoutThreshold", desc="超时时间阈值(ms)"):
                builder.TYPE(ParamType.UINT)
                builder.DEFAULTVALUE(8000)
        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        cls.config = param_loader.loadConfig()
        cls.devName = cls.config.get("devName")
        cls.baudrate = cls.config.get("baudrate")
        cls.timeoutThreshold = cls.config.get("timeoutThreshold")

config_params = ConfigParams()

class Battery(bb.batteryBase):
    """
    继承电池基类
    """
    def __init__(self):
        # 初始化基类,必须做
        super(Battery, self).__init__()
        self.createSerial(config_params.devName, config_params.baudrate)
        self.connect_timeout_t = mu.Timer(config_params.timeoutThreshold)
        #
        self.state_info = 0
        self.battery_capacity = 0
        self.battery_health = 0
        self.max_cell_temp = 0
        self.min_cell_temp = 0
        self.max_cell_voltage = 0
        self.min_cell_voltage = 0
        self.battery_capacity = 0
        self.switch_state = ""
        # 创建一个列表用来缓冲接收数据
        self.data_buff = []
        self.voltage_list = []
        self.balance_list = []
        self.temperature_list = []
        self.mosfet_list = []
        # 用来表示数据是否已经正确接收
        self.case = "listen3"
        self.msg_ok2 = False
        self.msg_ok3 = False
        # 创建一个电池信息的proto对象
        self.battery_info = self.createBatteryMessage()

    def handleData(self, msg: list):
        self.judgeRecData(msg)
        self.judgePublish()

    def judgeRecData(self, msg: list):
        """
        必须实现基类中处理数据的handleData(msg)的函数)
        如下为示例
        """
        # 存入收到的数据到缓冲中
        self.data_buff.extend(msg)
        # 判断报文长度
        if len(self.data_buff) >= 26 and self.case == "listen2":
            # 校验帧头是否正确
            if self.data_buff[0] == 0x7F and self.data_buff[1] == 0x10 and self.data_buff[2] == 0x02 and self.data_buff[4] == 0x11:
                # 转换电池数据
                self.max_cell_voltage = round(cu.merge2BytesTo1(self.data_buff[12], self.data_buff[11]) * 0.001,2)
                self.min_cell_voltage = round(cu.merge2BytesTo1(self.data_buff[14], self.data_buff[13]) * 0.001,2)
                self.battery_info.chargeVoltage = cu.merge2BytesTo1(self.data_buff[16], self.data_buff[15]) * 0.01
                self.max_cell_temp = cu.u16ToInt16(self.data_buff[17])
                self.battery_info.temperature = self.max_cell_temp
                self.min_cell_temp = cu.u16ToInt16(self.data_buff[18])
                self.switch_state = hex(self.data_buff[25])
                # 清空缓冲区列表
                self.data_buff = []
                self.clearTimeout()
                # 标记该次数据接收完成且正确
                self.msg_ok1 = True
                self.case = "listen3"
                print("litsen2 finish")
            else:
                # 第一个字节有误则去除
                self.data_buff.pop(0)

        # 判断报文长度
        if len(self.data_buff) >= 56 and self.case == "listen3":
            # 校验帧头是否正确
            self.voltage_list = []
            self.balance_list = []
            self.temperature_list = []
            self.mosfet_list = []
            if self.data_buff[0] == 0x7F and self.data_buff[1] == 0x10 and self.data_buff[2] == 0x02 and self.data_buff[4] == 0x12:
                # 转换电池数据
                self.state_info = cu.merge4BytesTo1(self.data_buff[8], self.data_buff[7], self.data_buff[6],self.data_buff[5])

                self.battery_info.chargeCurrent = cu.u16ToInt16(cu.merge2BytesTo1(self.data_buff[10], self.data_buff[9])) * 0.1  # 是int16类型

                voltage_number = cu.u16ToInt16(self.data_buff[11])
                for i in range(12, voltage_number * 2 + 12, 2):
                    voltage_value = round(cu.merge2BytesTo1(self.data_buff[i+1], self.data_buff[i])*0.001,2)
                    self.voltage_list.append(voltage_value)
                for i in range(42, 44):
                    self.balance_list.append(self.data_buff[i])
                temperature_number = cu.u16ToInt16(self.data_buff[44])
                for i in range(45, temperature_number + 45):
                    self.temperature_list.append(self.data_buff[i])
                mosfet_number = cu.u16ToInt16(self.data_buff[47])
                for i in range(48, mosfet_number + 48):
                    self.mosfet_list.append(self.data_buff[i])

                self.battery_info.cycle = cu.merge2BytesTo1(self.data_buff[50], self.data_buff[49])

                temp_capacity = cu.merge2BytesTo1(self.data_buff[52], self.data_buff[51]) * 0.1  # 剩余容量
                battery_capacity = cu.merge2BytesTo1(self.data_buff[54], self.data_buff[53]) * 0.1  # 总容量
                self.battery_capacity = round(battery_capacity,2)
                self.battery_info.percentage = round(temp_capacity / battery_capacity, 2)  # 计算百分比
                self.battery_info.SOH = int(100)

                # 清空缓冲区列表
                self.data_buff = []

                # 标记该次数据接收完成且正确
                self.clearTimeout()
                self.msg_ok3 = True
                self.case = "listen2"
                print("litsen3 finish")
            else:
                # 第一个字节有误则去除
                self.data_buff.pop(0)

    def judgePublish(self):
        data_to_send = {
                "state_info": self.state_info,
                "battery_capacity": self.battery_capacity,
                "battery_health": self.battery_health,
                "max_cell_temp": self.max_cell_temp,
                "min_cell_temp": self.min_cell_temp,
                "max_cell_voltage": self.max_cell_voltage,
                "min_cell_voltage": self.min_cell_voltage,
                "voltage_list": self.voltage_list,
                "mosfet_temperature_list": self.mosfet_list,
                "temperature_list": self.temperature_list,
                "balance_list": self.balance_list,
                "switch_state": self.switch_state
        }
        print(data_to_send)
        self.battery_info.extra = json.dumps(data_to_send)
        if self.msg_ok3 or self.msg_ok2:
            self.publish(self.battery_info)

    def judgeMsgok(self, msg_ok):
        # 判断是否收到整包
        if msg_ok:
            # 清除超时错误,重置标志位
            msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                # 等待是否收到整包,若超时则报超时,并进入下次循环
                self.setTimeout()

    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        while True:
            # 初始化查询报文list
            if self.case == "listen3":
                request3 = [0x7F, 0x10, 0x02, 0x06, 0x12, 0x57]
                self.send(request3)
                print('send 3')
            elif self.case == "listen2":
                request2 = [0x7F, 0x10, 0x02, 0x06, 0x11, 0x58]
                self.send(request2)
                print('send 2')
            self.judgeMsgok(self.msg_ok2)
            self.judgeMsgok(self.msg_ok3)
            mu.sleepS(2)


if __name__ == '__main__':
    run_battery_script(Battery)
