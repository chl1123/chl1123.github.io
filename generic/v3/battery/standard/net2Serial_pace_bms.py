import sys
import os

#导入电池基类
import syspy.battery_Serial.battery_base as bb
#处理字符的工具类
import syspy.lib.char_utility as cu
#其他工具类,如定时器
import syspy.lib.misc_utility as mu
from syspy import Trace

from syspy.battery_runner import run_battery_script

class Battery(bb.batteryBase):
    """
    Inherit the battery base class
    """
    def __init__(self):
        #Initialize the base class
        super(Battery,self).__init__()
        self.port = self.getBatterySerialPort()
        self.baudrate = self.getBatterySerialBaudrate()
        self.timeoutThreshold = 2000
        self.createSerial(self.port, self.baudrate)
        self.connect_timeout_t = mu.Timer(self.timeoutThreshold)
        #create a data buffer for saveing data
        self.data_buff = []
        # Mark whether the data has been received correctly
        self.msg_ok = False
        self.buff_type=''
        self.rec_flag=[False,False,False]

    def handleData(self, msg:list):
        self.data_buff.append(int(msg.hex(),16))
        if len(self.data_buff) >= 7:
            if self.data_buff[0]==0x01 and self.data_buff[1] == 0x04:
                datasize=self.data_buff[2]
                if self.buff_type == 'elect' and len(self.data_buff) >= (5+datasize):
                        current = cu.u16ToInt16(cu.merge2BytesTo1(self.data_buff[3],\
                                      self.data_buff[4])) * 0.1
                        voltage = cu.merge2BytesTo1(self.data_buff[5],self.data_buff[6]) * 0.1
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
                elif self.buff_type == 'percentage'and len(self.data_buff) >= (5+datasize):
                        percentage = (cu.merge2BytesTo1(self.data_buff[3],self.data_buff[4]) /
                                      cu.merge2BytesTo1(self.data_buff[5],self.data_buff[6]))
                        self.battery_info.percentage = percentage
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
        self.battery_info = self.createBatteryMessage()
        while True:
            for key,request in sendmsg.items():
                self.buff_type=key
                self.send(request)
                mu.sleepMs(100)
            self.judgeMsgok()
            mu.sleepS(2)

if __name__ == '__main__':
    run_battery_script(Battery)
