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
            if len(self.data_buff) >= 116:  
                #校验帧头是否正确
                if self.data_buff[0] == 0x7E:  
                    #转换电池数据
                    a = []
                    # print(self.data_buff[21])
                    # print(self.data_buff[22])
                    # print(self.data_buff[15])
                    # print(self.data_buff[16])
                    lists = [self.data_buff[13],self.data_buff[14],self.data_buff[15],self.data_buff[16]]
                    def results(listes):
                        for voltage0 in listes:
                            if (voltage0 >= 0x30 and voltage0 <= 0x39) :
                                a.append(voltage0 - 0x30)
                            elif(voltage0 >= 0x41 and voltage0 <= 0x46):
                                a.append(voltage0 - 55)
                    results(lists)
                    voltage = (a[0] * 16**3 + a[1] * 16**2 + a[2] * 16**1 + a[3] * 16**0) * 0.001
                    # print(voltage)
                    #电压------------------------------------------
                    b = []
                    lists1 = [self.data_buff[17],self.data_buff[18],self.data_buff[19],self.data_buff[20]]
                    def resultss(listes0):
                        for current0 in listes0:
                            if (current0 >= 0x30 and current0 <= 0x39) :
                                b.append(current0 - 0x30)
                            elif(current0 >= 0x41 and current0 <= 0x46):
                                b.append(current0 - 55)
                    resultss(lists1)
                    current = (cu.u16Toint16(b[0] * 16**3 + b[1] * 16**2 + b[2] * 16**1 + b[3] * 16**0)) * 0.01
                    print(current)
                    #电流------------------------------------------
                    c = []
                    lists2 = [self.data_buff[21],self.data_buff[22]]
                    def resultsss(listes1):
                        for percetage0 in listes1:
                            if (percetage0 >= 0x30 and percetage0 <= 0x39) :
                                c.append(percetage0 - 0x30)
                            elif(percetage0 >= 0x41 and percetage0 <= 0x46):
                                c.append(percetage0 - 55)
                    resultsss(lists2)                    
                    percetage = (c[0] * 16**1 + c[1] * 16**0) * 0.01
                    # print(percetage)

                    #电量------------------------------------------
                    d = []
                    lists3 = [self.data_buff[55],self.data_buff[56],self.data_buff[57],self.data_buff[58]]
                    def resultssss(listes2):
                        for temperature0 in listes2:
                            if (temperature0 >= 0x30 and temperature0 <= 0x39) :
                                d.append(temperature0 - 0x30)
                            elif(temperature0 >= 0x41 and temperature0 <= 0x46):
                                d.append(temperature0 - 55)
                    resultssss(lists3)
                    temperature = (d[0] * 16**3 + d[1] * 16**2 + d[2] * 16**1 + d[3] * 16**0) * 0.01
                    #温度------------------------------------------

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
            request = [0x7E, 0x32, 0x30, 0x30, 0x30, 0x34, 0x41, 0x36, 0x31, 0x30, 0x30, 0x30, 0x30, 0x46, 0x44, 0x41, 0x32, 0x0D]
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