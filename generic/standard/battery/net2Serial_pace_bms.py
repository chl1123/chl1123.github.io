import sys
import os

#导入电池基类
import syspy.battery_Serial.battery_base as bb 
#处理字符的工具类  
import syspy.lib.char_utility as cu 
#其他工具类,如定时器 
import syspy.lib.misc_utility as mu 

class testBattery(bb.batteryBase):
    """
    Inherit the battery base class
    """
    def __init__(self):
        #Initialize the base class
        super(testBattery,self).__init__()   
        #create a data buffer for saveing data
        self.data_buff = [] 
        # Mark whether the data has been received correctly
        self.msg_ok = False 
     
        self.buff_type=''
        # Create a protocol object with battery information
        
        self.rec_flag=[False,False,False]

    def handleData(self, msg:list):
        """
        Handle the recive data
        """
      
        # change data type to int
        self.data_buff.append(int(msg.hex(),16))     

        if len(self.data_buff) >= 7:
           
            # Judge header is 0x01 and 0x04 or not,
            # if not,then discard and clear this data buffer
            if self.data_buff[0]==0x01 and self.data_buff[1] == 0x03:
                datasize=self.data_buff[2] #byte 3 is data size
                if self.buff_type == 'electri' and len(self.data_buff) >= (5+datasize) :
                        # calculate the relate electrical information
                        current = cu.u16Toint16(cu.merge2bytesTo1(self.data_buff[3],\
                                      self.data_buff[4])) * 0.01 #convert to int16
                        voltage = cu.merge2bytesTo1(self.data_buff[5],self.data_buff[6]) * 0.01  
                       
            
                        # save to battery_info object
                        self.battery_info.charge_current = float("%.2f" % current) 
                        self.battery_info.charge_voltage = float("%.2f" % voltage)
                        self.data_buff = []          
                        self.msg_ok = True
                        self.rec_flag[0]=True
           
                elif self.buff_type == 'temp'and len(self.data_buff) >= (5+datasize):
                        temperature=cu.u16Toint16(cu.merge2bytesTo1(self.data_buff[3],self.data_buff[4]))*0.1
                        # save to battery_info object
                        self.battery_info.temperature = float("%.2f" % temperature)
                      
                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[1]=True

                elif self.buff_type == 'percents'and len(self.data_buff) >= (5+datasize):
                        percetage = cu.merge2bytesTo1(self.data_buff[3],self.data_buff[4])*0.01
                         # save to battery_info object
                        self.battery_info.percetage = float("%.2f" % percetage) 

                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[2]=True
            else:
                self.data_buff = []

        else:
            #check frame header,if not 0x01,then clear data buffer
            if self.data_buff[0]!=0x01:
                self.data_buff = []
        #if all recive data is right,then send battery_info object to rbk,and clear receive flag
        if not False in self.rec_flag: 
            print("okk")
            self.publish(self.battery_info)  
            self.rec_flag=[False,False,False] 
              
    def loop(self):
        """
        Loop,and handle send package and timeout logic
        """
        #create a timeout timer
        connect_timeout_t = mu.Timer(2000)
        # send package, use dictionary type to classify
        # #first byte is slave address
        sendmsg={'electri':[0x01,0x03,0x00,0x00,0x00,0x02,0xC4,0x0B], 
                 'temp':[0x01,0x03,0x00,0x20,0x00,0x01,0x85,0xC0],
                 'percents':[0x01,0x03,0x00,0x02,0x00,0x01,0x25,0xCA]}
        self.battery_info = self.createBatteryMessage()
        connect_timeout_t.reset()
        while True:
            for key,request in sendmsg.items():
                #send request package
                self.buff_type=key
                self.send(request)
                mu.sleep_ms(100) 
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

    
