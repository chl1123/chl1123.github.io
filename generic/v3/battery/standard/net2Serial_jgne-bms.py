import sys
import os
#导入电池基类
import syspy.battery_Serial.battery_base as bb
#处理字符的工具类
import syspy.lib.char_utility as cu
#其他工具类,如定时器
import syspy.lib.misc_utility as mu
from syspy.utils.param_server import ParamType, ScriptParam
from syspy import Trace

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

    def __init__(self):
        super(Battery,self).__init__()
        self.createSerial(config_params.devName, config_params.baudrate)
        self.connect_timeout_t = mu.Timer(config_params.timeoutThreshold)
        self.data_buff = []
        self.msg_ok = False
        self.buff_type=''
        self.rec_flag=[False,False,False]

    def handleData(self, msg:list):
        self.data_buff.append(int(msg.hex(),16))
        if len(self.data_buff) >= 7:
            if self.data_buff[0]==0x01 and self.data_buff[1] == 0x03:
                datasize=self.data_buff[2]
                if self.buff_type == 'electri' and len(self.data_buff) >= (5+datasize):
                        current = cu.u16ToInt16(cu.merge2BytesTo1(self.data_buff[3],\
                                      self.data_buff[4])) * 0.01
                        voltage = cu.merge2BytesTo1(self.data_buff[5],self.data_buff[6]) * 0.01
                        self.battery_info.chargeCurrent = float("%.2f" % current)
                        self.battery_info.chargeVoltage = float("%.2f" % voltage)
                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[0]=True
                elif self.buff_type == 'temp'and len(self.data_buff) >= (5+datasize):
                        temperature=cu.u16ToInt16(cu.merge2BytesTo1(self.data_buff[3],self.data_buff[4]))*0.1
                        self.battery_info.temperature = float("%.2f" % temperature)
                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[1]=True
                elif self.buff_type == 'percents'and len(self.data_buff) >= (5+datasize):
                        percentage = cu.merge2BytesTo1(self.data_buff[3],self.data_buff[4])*0.01
                        self.battery_info.percentage = float("%.2f" % percentage)
                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[2]=True
                self.battery_info.SOH = int(100)
            else:
                self.data_buff = []
        else:
            if self.data_buff[0]!=0x01:
                self.data_buff = []
        if not False in self.rec_flag:
            print("okk")
            self.publish(self.battery_info)
            self.rec_flag=[False,False,False]

    def judgeMsgok(self):
        if self.msg_ok:
            self.clearTimeout()
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()

    def loop(self):
        sendmsg={'electri':[0x01,0x03,0x00,0x00,0x00,0x02,0xC4,0x0B],
                 'temp':[0x01,0x03,0x00,0x20,0x00,0x01,0x85,0xC0],
                 'percents':[0x01,0x03,0x00,0x02,0x00,0x01,0x25,0xCA]}
        self.battery_info = self.createBatteryMessage()
        while True:
            for key,request in sendmsg.items():
                self.buff_type=key
                self.send(request)
                mu.sleepMs(100)
            self.judgeMsgok()
            mu.sleepS(2)

if __name__ == '__main__':
    client = Battery()
    client.loop()
