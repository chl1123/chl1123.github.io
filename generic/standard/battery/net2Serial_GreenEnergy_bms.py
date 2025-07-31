import sys
import os
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
#导入电池基类
import syspy.battery_Serial.battery_base as bb 
#处理字符的工具类  
import syspy.lib.char_utility as cu 
#其他工具类,如定时器 
import syspy.lib.misc_utility as mu 


class testBattery(bb.batteryBase):
    """
    继承电池基类
    """
    def __init__(self):
        #Initialize the base class
        super(testBattery,self).__init__()
        #create a data buffer for saveing data
        self.packeddata_buff = []
        self.realdata_buff = [] # this number depends on how many realdata message we will receive
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
                # self.msg_ok = True
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

                if len(self.realdata_buff)!=12: #check whether the length of realdata is 12 or not
                    self.realdata_buff=[]
                    self.packeddata_buff=[]

            elif self.packeddata_buff[-1]!=0x03 and len(self.packeddata_buff)>26: #
                self.packeddata_buff=[]
        else:
            self.packeddata_buff=[]

        if len(self.realdata_buff)==12:
            """
             write parse code
            """

            ID = cu.merge4bytesTo1(self.realdata_buff[3], self.realdata_buff[2],self.realdata_buff[1],self.realdata_buff[0])
            if (ID == 0x351): #Summary
                self.soc = cu.merge2bytesTo1(self.realdata_buff[5], self.realdata_buff[4])*0.001 #SOC
                self.rec_flag[0]=True
                #print(self.soc)

            elif (ID == 0x352): #PackValue
                self.voltage = cu.merge2bytesTo1(self.realdata_buff[5], self.realdata_buff[4])*0.1 #P_Volt
                self.current  = cu.u16Toint16(cu.merge2bytesTo1(self.realdata_buff[7], self.realdata_buff[6]))*0.1 #P_Curr
                self.rec_flag[1]=True
                #print("voltage :", self.voltage, "current :", self.current)

            elif (ID == 0x354): #Temperature
                self.max_temp = cu.u8Toint8(self.realdata_buff[0]) 
                self.rec_flag[2]=True
                #print("max temp :", self.max_temp)

            self.realdata_buff = []
            
            if True in self.rec_flag:
                self.clearTimeout()
                self.connect_timeout_t.reset()

        if not False in self.rec_flag:
            self.battery_info.percetage = self.soc #percentage
            self.battery_info.temperature = self.max_temp #temperature
            self.battery_info.charge_current = self.current
            self.battery_info.charge_voltage = self.voltage
            #发步电池数据给rbk
            self.publish(self.battery_info)  
            #清空缓冲区列表
            self.rec_flag=[False,False,False]
            #when receive all right information
            self.clearTimeout()
            self.connect_timeout_t.reset()

    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        #创建一个超时定时器
        self.battery_info = self.createBatteryMessage()
        self.clearTimeout()

        self.connect_timeout_t = mu.Timer(4000)
        request = [0x02, 0x01, 0x00, 0x00, 0x01, 0x1E, 0x2D, 0x03]
        self.send(request)

        while True:
            mu.sleep_ms(10)
            if self.connect_timeout_t.isTimeUp():
                self.connect_timeout_t.reset()
                self.setTimeout()

if __name__ == '__main__':
    client = testBattery()
    client.loop()
    
