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
        self.buff_type=''
        self.rec_flag=[False,False,False]

    def handleData(self, msg:list):
        self.battery_info = self.createBatteryMessage()
        msghex=msg.hex()
        self.data_buff.append(int(msghex,16))
        if len(self.data_buff) >= 7:
            if self.data_buff[0]==0x01 and self.data_buff[1] == 0x04:
                datasize=self.data_buff[2]
                if self.buff_type == 'elect' and len(self.data_buff) >= (5+datasize) :
                        voltage = cu.merge2BytesTo1(self.data_buff[3],self.data_buff[4]) * 0.1
                        current = cu.u16ToInt16(cu.merge2BytesTo1(self.data_buff[5],self.data_buff[6])) * 0.1
                        self.battery_info.chargeCurrent = float("%.2f" % current)
                        self.battery_info.chargeVoltage = float("%.2f" % voltage)
                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[0]=True
                elif self.buff_type == 'temp'and len(self.data_buff) >= (5+datasize):
                        temperature=cu.u16ToInt16(cu.merge2BytesTo1(self.data_buff[3],self.data_buff[4]))
                        self.battery_info.temperature = float("%.2f" % temperature)
                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[1]=True
                elif self.buff_type == 'percentage'and len(self.data_buff) >= (5+datasize):
                        percentage = cu.merge2BytesTo1(self.data_buff[5],self.data_buff[6]) / cu.merge2BytesTo1(self.data_buff[3],self.data_buff[4])
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
        sendmsg={'elect':[0x01,0x04,0x04,0x1A,0x00,0x02,0x51,0x3C],
                 'temp':[0x01,0x04,0x04,0xB0,0x00,0x01,0x31,0x1D],
                 'percentage':[0x01,0x04,0x03,0xF6,0x00,0x02,0x91,0xBD]}
        while True:
            for key,request in sendmsg.items():
                self.buff_type=key
                self.send(request)
                mu.sleepMs(100)
            self.judgeMsgok()
            mu.sleepS(2)


if __name__ == '__main__':
    run_battery_script(Battery)
