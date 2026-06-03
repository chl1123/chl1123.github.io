import os

#导入电池基类
import syspy.battery_Serial.battery_base as bb
#处理字符的工具类
import syspy.lib.char_utility as cu
#其他工具类,如定时器
import syspy.lib.misc_utility as mu
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

class Battery(bb.batteryBase):
    """
    继承电池基类
    """
    def __init__(self):
        #初始化基类,必须做
        super(Battery,self).__init__()
        self.createSerial(config_params.devName, config_params.baudrate)
        self.connect_timeout_t = mu.Timer(config_params.timeoutThreshold)
        #创建一个列表用来缓冲接收数据
        self.data_buff = []
        #用来表示数据是否已经正确接收
        self.msg_ok = False

    def handleData(self, msg:list):
        """
        必须实现基类中处理数据的handleData(msg)的函数)
        如下为示例
        """
        #存入收到的数据到缓冲中
        for i in range(0, len(msg)):
            self.data_buff.append(msg[i])
            #判断报文长度
            if len(self.data_buff) >= 116:
                #校验帧头是否正确
                if self.data_buff[0] == 0x7E:
                    #转换电池数据
                    a = []
                    lists = [self.data_buff[13],self.data_buff[14],self.data_buff[15],self.data_buff[16]]
                    def results(listes):
                        for voltage0 in listes:
                            if (voltage0 >= 0x30 and voltage0 <= 0x39) :
                                a.append(voltage0 - 0x30)
                            elif(voltage0 >= 0x41 and voltage0 <= 0x46):
                                a.append(voltage0 - 55)
                    results(lists)
                    voltage = (a[0] * 16**3 + a[1] * 16**2 + a[2] * 16**1 + a[3] * 16**0) * 0.001
                    #电压------------------------------------------
                    b = []
                    lists1 = [self.data_buff[17],self.data_buff[18],self.data_buff[19],self.data_buff[20]]
                    def resultss(listes0):
                        for current0 in listes0:
                            if (current0 >= 0x30 and current0 <= 0x39) :
                                b.append(current0 - 0x30)
                            elif(current0 >= 0x41 and current0 <= 0x46):
                                b.append(current0 - 55)
                    resultss(lists1)
                    current = (cu.u16ToInt16(b[0] * 16**3 + b[1] * 16**2 + b[2] * 16**1 + b[3] * 16**0)) * 0.01
                    print(current)
                    #电流------------------------------------------
                    c = []
                    lists2 = [self.data_buff[21],self.data_buff[22]]
                    def resultsss(listes1):
                        for percentage0 in listes1:
                            if (percentage0 >= 0x30 and percentage0 <= 0x39) :
                                c.append(percentage0 - 0x30)
                            elif(percentage0 >= 0x41 and percentage0 <= 0x46):
                                c.append(percentage0 - 55)
                    resultsss(lists2)
                    percentage = (c[0] * 16**1 + c[1] * 16**0) * 0.01
                    #电量------------------------------------------
                    d = []
                    lists3 = [self.data_buff[55],self.data_buff[56],self.data_buff[57],self.data_buff[58]]
                    def resultssss(listes2):
                        for temperature0 in listes2:
                            if (temperature0 >= 0x30 and temperature0 <= 0x39) :
                                d.append(temperature0 - 0x30)
                            elif(temperature0 >= 0x41 and temperature0 <= 0x46):
                                d.append(temperature0 - 55)
                    resultssss(lists3)
                    temperature = (d[0] * 16**3 + d[1] * 16**2 + d[2] * 16**1 + d[3] * 16**0) * 0.01
                    #温度------------------------------------------

                        #创建一个电池信息的proto对象
                    battery_info = self.createBatteryMessage()
                        #解析后塞入相应字段
                    battery_info.percentage = percentage
                    battery_info.temperature = temperature
                    battery_info.chargeCurrent = current
                    battery_info.chargeVoltage = voltage
                    battery_info.SOH = int(100)
                        #发步电池数据给rbk
                    self.publish(battery_info)
                        #清空缓冲区列表
                    self.data_buff = []
                        #标记该次数据接收完成且正确
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
            #初始化查询报文list
            request = [0x7E, 0x32, 0x30, 0x30, 0x30, 0x34, 0x41, 0x36, 0x31, 0x30, 0x30, 0x30, 0x30, 0x46, 0x44, 0x41, 0x32, 0x0D]
            #发送查询报文
            self.send(request)
            self.judgeMsgok()
            mu.sleepS(2)

if __name__ == '__main__':
    run_battery_script(Battery)
