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
    继承电池基类
    """
    def __init__(self):
        #初始化基类,必须做
        super(testBattery,self).__init__()   
        #创建一个列表用来缓冲接收数据
        self.data_buff = [] 
        #用来表示数据是否已经正确接收
        self.msg_ok = False 
     
        self.buff_type=''
        
        self.rec_flag=[False,False,False]

    def handleData(self, msg:list):
        """
        Handle the recive data
        """
        # Create a protocol object with battery information
        self.battery_info = self.createBatteryMessage()
        msghex=msg.hex()
        # change data type to init
        self.data_buff.append(int(msghex,16))
 
         
        if len(self.data_buff) >= 7:
            if self.data_buff[0]==0x01 and self.data_buff[1] == 0x04:
                datasize=self.data_buff[2]
                if self.buff_type == 'elect' and len(self.data_buff) >= (5+datasize) :
                        # calculate the relate electrical information
                        voltage = cu.merge2bytesTo1(self.data_buff[3],self.data_buff[4]) * 0.1  
                        current = cu.u16Toint16(cu.merge2bytesTo1(self.data_buff[5],self.data_buff[6])) * 0.1 #exchange to int16
            
                        # save to battery_info object
                        self.battery_info.charge_current = float("%.2f" % current) 
                        self.battery_info.charge_voltage = float("%.2f" % voltage)
                        self.data_buff = []          
                        self.msg_ok = True
                        self.rec_flag[0]=True
                      



                elif self.buff_type == 'temp'and len(self.data_buff) >= (5+datasize):
                        temperature=cu.u16Toint16(cu.merge2bytesTo1(self.data_buff[3],self.data_buff[4]))
                        # save to battery_info object
                        self.battery_info.temperature = float("%.2f" % temperature)
                      
                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[1]=True

                elif self.buff_type == 'percentage'and len(self.data_buff) >= (5+datasize):
                        percetage = cu.merge2bytesTo1(self.data_buff[5],self.data_buff[6]) / cu.merge2bytesTo1(self.data_buff[3],self.data_buff[4])
                         # save to battery_info object
                        self.battery_info.percetage = float("%.2f" % percetage) 

                        self.data_buff = []
                        self.msg_ok = True
                        self.rec_flag[2]=True
            else:
                self.data_buff = []



        else:
            if self.data_buff[0]!=0x01: #check frame header,if not ox01,then clear data buffer
                self.data_buff = []

        if not False in self.rec_flag: #if all recive data is right,then send battery_info object to rbk,and clear receive flag
           
            self.publish(self.battery_info)  
            self.rec_flag=[False,False,False] 
               
        
              
                
    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        #创建一个超时定时器
        connect_timeout_t = mu.Timer(2000)

        sendmsg={'elect':[0x01,0x04,0x04,0x1A,0x00,0x02,0x51,0x3C],
                 'temp':[0x01,0x04,0x04,0xB0,0x00,0x01,0x31,0x1D],
                 'percentage':[0x01,0x04,0x03,0xF6,0x00,0x02,0x91,0xBD]}

        connect_timeout_t.reset()
        while True:
            for key,request in sendmsg.items():
                #发送查询报文
                self.buff_type=key
                self.send(request)
                mu.sleep_ms(100) 
               #等待是否收到整包,若超时则报超时,并进入下次循环
            while not self.msg_ok:
                if connect_timeout_t.isTimeUp():
                    self.setTimeout()   #
                    break
            #判断是否收到整包
            if self.msg_ok:
                #清除超时错误,重置标志位
                self.clearTimeout()
                self.msg_ok = False
                connect_timeout_t.reset()
   
                
            mu.sleep_s(1)


if __name__ == '__main__':
    client = testBattery()
    client.loop()

    
