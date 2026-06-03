import sys
import os

# 导入电池基类
import syspy.battery_Serial.battery_base as bb
# 处理字符的工具类
import syspy.lib.char_utility as cu
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
from syspy.utils.param_server import ParamType, ScriptParam
from syspy import Trace

from syspy.battery_runner import run_battery_script
"""
霍克能源集团有限公司YY系列BMS均支持标准工业modbus 协议

武汉彦阳物联科技 YY-BCU系列 MODBUS协议 V1
"""

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
                builder.DEFAULTVALUE(2000)
        builder.save(merge=True)
        cls.reload_config()

    @classmethod
    def reload_config(cls):
        cls.config = param_loader.loadConfig()
        cls.devName = cls.config.get("devName")
        cls.baudrate = cls.config.get("baudrate")
        cls.timeoutThreshold = cls.config.get("timeoutThreshold")

config_params = ConfigParams()


class BatteryHuoKeYy(bb.batteryBase):
    """
    继承电池基类
    """

    def __init__(self):
        # 初始化基类,必须做
        super(BatteryHuoKeYy, self).__init__()
        self.createSerial(config_params.devName, config_params.baudrate)
        self.connect_timeout_t = mu.Timer(config_params.timeoutThreshold)
        # 创建一个列表用来缓冲接收数据
        self.data_buff = []
        # 用来表示数据是否已经正确接收
        self.msg_ok = False

    def handleData(self, msg: list):
        print("报文长度：", len(msg))
        """
        必须实现基类中处理数据的handleData(msg)的函数)
        如下为示例
        """
        # 存入收到的数据到缓冲中
        for i in range(0, len(msg)):
            self.data_buff.append(msg[i])
        # 判断报文长度 [01 03 18 26 ae 00 0b 67 66 00 00 00 c7 00 00 44 43 00 00 0c f1 0c ea 00 a2 08 34 e3 c4]
        if len(self.data_buff) >= 29:  # 1（从机ID） + 1（功能码） + 1（数据域字节数） + 24 + 2（CRC校验码） = 29
            # 校验帧头是否正确
            if self.data_buff[0] == 0x01:
                # 转换电池数据
                voltage = cu.merge2BytesTo1(self.data_buff[7], self.data_buff[8]) * 0.001
                current = cu.u16ToInt16(cu.merge2BytesTo1(self.data_buff[11], self.data_buff[12])) * 0.1  # 是int16类型
                temp16_1 = cu.merge2BytesTo1(0x00, self.data_buff[15]) - 40  # max
                temp16_2 = cu.merge2BytesTo1(0x00, self.data_buff[16]) - 40  # min
                temperature = temp16_1
                if temp16_1 < temp16_2:
                    temperature = temp16_2
                percentage = cu.merge2BytesTo1(self.data_buff[23], self.data_buff[24]) * 0.04
                # 创建一个电池信息的proto对象
                battery_info = self.createBatteryMessage()
                # 解析后塞入相应字段
                battery_info.percentage = percentage
                battery_info.temperature = temperature
                battery_info.chargeCurrent = current
                battery_info.chargeVoltage = voltage
                battery_info.SOH = int(100)
                # 发步电池数据给rbk
                self.publish(battery_info)
                # 清空缓冲区列表
                self.data_buff = []
                # 标记该次数据接收完成且正确
                self.msg_ok = True

    def judgeMsgok(self):
        if self.msg_ok:
            self.clearTimeout()
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()

    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        while True:
            # 初始化查询报文list
            request = [0x01, 0x03, 0x00, 0x0A, 0x00, 0x0C, 0x65, 0xCD]  # 返回 [01 03 18 26 ae 00 0b 67 66 00 00 00 c7 00 00 44 43 00 00 0c f1 0c ea 00 a2 08 34 e3 c4]
            # 发送查询报文
            self.send(request)
            self.judgeMsgok()
            mu.sleepS(2)


if __name__ == '__main__':
    run_battery_script(BatteryHuoKeYy)
