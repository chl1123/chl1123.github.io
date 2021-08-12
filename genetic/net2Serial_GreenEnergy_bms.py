import sys
import os
#导入电池基类
import syspy.battery.battery_base as bb
#处理字符的工具类
import syspy.lib.char_utility as cu
#其他工具类,如定时器
import syspy.lib.misc_utility as mu
#crc16
def crc16_cal(datalist):#crc16 check
    test_crc=0xFFFF            
    poly=0xa001
    # poly=0x8005
    numl=len(datalist)
    for num in range(numl):
        data=datalist[num]
        test_crc=(data&0xFF)^test_crc 
        for bit in range(8):
            if(test_crc&0x1)!=0:
                test_crc>>=1
                test_crc^=poly
            else:
                test_crc>>=1

    return test_crc&0xff,(test_crc>>8)&0xff

class testBattery(bb.batteryBase):
    """
    Inherit the battery base class
    """
    def __init__(self):
        #Initialize the base class
        super(testBattery,self).__init__()
        #create a data buffer for saveing data
        self.packeddata_buff = []
    
        self.realdata_buff = [] # this number depends on how many realdata message we will receive
        
    # Mark whether the data has been received correctly
        self.msg_ok = False

        # Create a protocol object with battery information

    def handleData(self, msg:list):
        """
        Handle the recive data
        """
        #save to buffer
        for i in range(len(msg)):
            self.packeddata_buff.append(int(msg[i]))
        print("")
        # change data type to int

        if self.packeddata_buff[0]==0x02:
            if self.packeddata_buff[-1]==0x03:
                #self.msg_ok = True
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
            self.battery_info.percetage = percetage  
            self.battery_info.temperature = temperature
            self.battery_info.charge_current = current
            self.battery_info.charge_voltage = voltage
            #发步电池数据给rbk
            self.publish(self.battery_info)  
            #清空缓冲区列表
            self.realdata_buff = []
            #标记该次数据接收完成且正确
            self.msg_ok = True



    def loop(self):
        """
        Loop,and handle send package and timeout logic
        """
        self.battery_info = self.createBatteryMessage()
        #create a timeout timer
        connect_timeout_t = mu.Timer(2000)
        # send package, use dictionary type to classify
     # send package, use dictionary type to classify
        # #first byte is slave address
        sendmsg=[0x02,0x10,0x00,0x00,0x01,0x1E,0x2D,0x03]
        
        connect_timeout_t.reset()
        while True:
                self.send(sendmsg)

                #Wait for one data package has been received or not.
                while not self.msg_ok:
                    # If timer is time up, it will report a timeout and enter the next cycle
                    if connect_timeout_t.isTimeUp():
                        self.setTimeout()
                        break
                #if one data package has been received completly
                if self.msg_ok:
                    #Clear timeout error, reset flag bit
                    self.clearTimeout()
                    self.msg_ok = False
                    connect_timeout_t.reset()

                mu.sleep_s(1)
            


if __name__ == '__main__':
    client = testBattery()
    client.loop()

    
