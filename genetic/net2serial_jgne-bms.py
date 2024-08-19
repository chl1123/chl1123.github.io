import sys
import os
#import bettery base class
import syspy.battery_Serial.battery_base as bb 
#import the tool of handling string type
import syspy.lib.char_utility as cu 
#other tools,like Timer
import syspy.lib.misc_utility as mu
import message_battery_pb2

class testBattery(bb.batteryBase):
   
    def __init__(self):
        super(testBattery,self).__init__()   
        self.data_buff = [] 
        self.msg_ok = False

    def handleData(self, msg:list):
        for i in range(0, len(msg)):
            self.data_buff.append(msg[i])
            # print(len(self.data_buff))
        if len(self.data_buff) >= 27:  
            if self.data_buff[0] == 0x7f:  
                voltage = cu.merge2bytesTo1(self.data_buff[16],self.data_buff[15]) * 0.01
                current = cu.u16Toint16(cu.merge2bytesTo1(self.data_buff[10],self.data_buff[9])) * 0.1
                temp = cu.u16Toint16(self.data_buff[17])
                percetage = (cu.merge2bytesTo1(self.data_buff[22],self.data_buff[21]) / cu.merge2bytesTo1(self.data_buff[24],self.data_buff[23]))
                battery_info = self.createBatteryMessage() 
                battery_info.percetage = ( percetage)  
                battery_info.temperature = (temp) 
                battery_info.charge_current = (current)
                battery_info.charge_voltage = (voltage)
                self.publish(battery_info)  
                self.data_buff = []
                # print("true")
                self.msg_ok = True
    def loop(self):
        connect_timeout_t = mu.Timer(2000)
        while True:
            request = [0x7f,0x10,0x02,0x06,0x11,0x58]
            self.send(request)
            # print("ok")
            if self.msg_ok:
                # print("ok")
                self.clearTimeout()
                self.msg_ok = False
                connect_timeout_t.reset()
            while not self.msg_ok:
                # print("ok")
                if connect_timeout_t.isTimeUp():
                    self.data_buff = []
                    print("time up")
                    self.setTimeout()   
                    break
            mu.sleep_ms(1000)
         
if __name__ == '__main__':
    client = testBattery()
    client.loop()

