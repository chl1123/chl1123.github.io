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
    继承电池基类
    """
    def __init__(self):
        #Initialize the base class
        super(Battery,self).__init__()
        self.port = self.getBatterySerialPort()
        self.baudrate = self.getBatterySerialBaudrate()
        self.timeoutThreshold = 4000
        self.createSerial(self.port, self.baudrate)
        #create a data buffer for saveing data
        self.packeddata_buff = []
        self.realdata_buff = []
        # Mark whether the data has been received correctly
        self.msg_ok = False
        self.rec_flag=[False,False,False]
        self.soc = 0
        self.voltage = 0
        self.current = 0
        self.max_temp = 0

    def handleData(self, msg:list):
        """
        Handle the recive data
        """
        #save to buffer
        for i in range(0, len(msg)):
            self.packeddata_buff.append(int(msg[i]))
        # change data type to int
        if self.packeddata_buff[0]==0x02:
            if self.packeddata_buff[-1]==0x03:
                for index in range(1,len(self.packeddata_buff)-1):
                    if self.packeddata_buff[index]==0x10 and self.packeddata_buff[index+1]==0x82:
                        self.packeddata_buff[index+1]=0x02
                        continue
                    elif self.packeddata_buff[index]==0x10 and self.packeddata_buff[index+1]==0x83:
                        self.packeddata_buff[index+1]=0x03
                        continue
                    elif self.packeddata_buff[index]==0x10 and self.packeddata_buff[index+1]==0x8f:
                        self.packeddata_buff[index+1]=0x10
                        continue
                    else:
                        self.realdata_buff.append(self.packeddata_buff[index])

                if len(self.realdata_buff)!=12:
                    self.realdata_buff=[]
                    self.packeddata_buff=[]

            elif self.packeddata_buff[-1]!=0x03 and len(self.packeddata_buff)>26:
                self.packeddata_buff=[]
        else:
            self.packeddata_buff=[]

        if len(self.realdata_buff)==12:
            ID = cu.merge4BytesTo1(self.realdata_buff[3], self.realdata_buff[2],self.realdata_buff[1],self.realdata_buff[0])
            if (ID == 0x351): #Summary
                self.soc = cu.merge2BytesTo1(self.realdata_buff[5], self.realdata_buff[4])*0.001 #SOC
                self.rec_flag[0]=True
            elif (ID == 0x352): #PackValue
                self.voltage = cu.merge2BytesTo1(self.realdata_buff[5], self.realdata_buff[4])*0.1 #P_Volt
                self.current  = cu.u16ToInt16(cu.merge2BytesTo1(self.realdata_buff[7], self.realdata_buff[6]))*0.1 #P_Curr
                self.rec_flag[1]=True
            elif (ID == 0x354): #Temperature
                self.max_temp = cu.u8ToInt8(self.realdata_buff[0])
                self.rec_flag[2]=True
            self.realdata_buff = []
            if True in self.rec_flag:
                self.clearTimeout()
                self.connect_timeout_t.reset()

        if not False in self.rec_flag:
            self.battery_info.percentage = self.soc
            self.battery_info.temperature = self.max_temp
            self.battery_info.chargeCurrent = self.current
            self.battery_info.chargeVoltage = self.voltage
            self.battery_info.SOH = int(100)
            self.publish(self.battery_info)
            self.rec_flag=[False,False,False]
            self.clearTimeout()
            self.connect_timeout_t.reset()

    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        self.battery_info = self.createBatteryMessage()
        self.clearTimeout()

        self.connect_timeout_t = mu.Timer(self.timeoutThreshold)
        request = [0x02, 0x01, 0x00, 0x00, 0x01, 0x1E, 0x2D, 0x03]
        self.send(request)

        while True:
            mu.sleepMs(10)
            if self.connect_timeout_t.isTimeUp():
                self.connect_timeout_t.reset()
                self.setTimeout()

if __name__ == '__main__':
    run_battery_script(Battery)
