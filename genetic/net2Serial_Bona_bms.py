# -*- coding: UTF-8 -*-
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

    def handleData(self, msg:list):
        """
        必须实现基类中处理数据的handleData(msg)的函数)
        如下为示例
        """
        #存入收到的数据到缓冲中
        for i in range(0, len(msg)):
            self.data_buff.append(msg[i])
        #判断报文长度
        if len(self.data_buff) >= 63:
            #校验帧头是否正确
            if self.data_buff[0] == 0x01:  
                #转换电池数据
                voltage = cu.merge2bytesTo1(self.data_buff[3],self.data_buff[4]) * 0.01
                current = - (cu.u16Toint16(cu.merge2bytesTo1(self.data_buff[13],self.data_buff[14])) * 0.01)    #是int16类型
                temp16_1 = cu.merge2bytesTo1(self.data_buff[17],self.data_buff[18])
                temperature = temp16_1
                percetage = cu.merge2bytesTo1(self.data_buff[7],self.data_buff[8]) * 0.01
                #创建一个电池信息的proto对象
                battery_info = self.createBatteryMessage() 
                #解析后塞入相应字段
                battery_info.percetage = percetage  
                battery_info.temperature = temperature
                battery_info.charge_current = current
                battery_info.charge_voltage = voltage
                #发步电池数据给rbk
                self.publish(battery_info)  
                #清空缓冲区列表
                self.data_buff = []
                #标记该次数据接收完成且正确
                self.msg_ok = True
                
    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        #创建一个超时定时器
        connect_timeout_t = mu.Timer(2000)
        while True:
            #初始化查询报文list
            request = [0x01, 0x03, 0x00, 0x00, 0x00, 0x1D, 0x85, 0xC3]
            #发送查询报文
            self.send(request)
            #判断是否收到整包
            if self.msg_ok:
                #清除超时错误,重置标志位
                self.clearTimeout()
                self.msg_ok = False
                connect_timeout_t.reset()
            #等待是否收到整包,若超时则报超时,并进入下次循环
            while not self.msg_ok:
                if connect_timeout_t.isTimeUp():
                    self.setTimeout()   #
                    break
            mu.sleep_s(1)

if __name__ == '__main__':
    client = testBattery()
    client.loop()
    
