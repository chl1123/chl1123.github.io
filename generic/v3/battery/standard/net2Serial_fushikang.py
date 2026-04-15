
#导入电池基类
import syspy.battery_Serial.battery_base as bb
#处理字符的工具类  
import syspy.lib.char_utility as cu 
#其他工具类,如定时器 
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud
from syspy import Trace

class Battery(bb.batteryBase):
    def __init__(self):
        #初始化基类,必须做
        super(Battery,self).__init__()
        # 创建一个超时定时器
        self.connect_timeout_t = mu.Timer(6000)
        # self.__debug_out = ud.udpDebug()
        # sys.stdout = self.__debug_out
        #创建一个列表用来缓冲接收数据
        self.data_buff = [] 
        #用来表示数据是否已经正确接收
        self.msg_ok = False
    def handleData(self, msg:list):
        #存入收到的数据到缓冲中
        self.data_buff.extend(msg)
        print(len(self.data_buff))
        while len(self.data_buff) >= 45:
            print("start")
            if self.data_buff[0] == 0xDD:
                voltage = cu.merge2BytesTo1(self.data_buff[4], self.data_buff[5]) * 0.01  # 电池电压
                current = cu.u16ToInt16(cu.merge2BytesTo1(self.data_buff[6], self.data_buff[7])) * 0.01  # 是int16类型
                temp16_1 = (cu.merge2BytesTo1(self.data_buff[27], self.data_buff[28]) - 2731) * 0.1
                temp16_2 = (cu.merge2BytesTo1(self.data_buff[29], self.data_buff[30]) - 2731) * 0.1
                temperature = temp16_1  # 电池温度
                if temp16_1 < temp16_2:
                    temperature = temp16_2
                percentage = cu.u16ToInt16(self.data_buff[23]) * 0.01  # 电池电量百分比
                cycle = cu.merge2BytesTo1(self.data_buff[12], self.data_buff[13])  # 电池循环次数
                dianchi_str = "富士康-20221206"
                userData = dianchi_str.encode('utf-8')
                # 创建一个电池信息的proto对象
                battery_info = self.createBatteryMessage()
                # 解析后塞入相应字段
                battery_info.percentage = percentage
                battery_info.temperature = temperature
                battery_info.chargeCurrent = current  # 电池电流：正表示在充电，负表示在放电
                battery_info.chargeVoltage = voltage
                battery_info.cycle = cycle
                battery_info.maxChargeVoltage = 58.4  # 最大充电电压
                battery_info.maxChargeCurrent = 30  # 最大持续充电电流
                battery_info.userData = userData
                battery_info.SOH = int(100)
                # 发步电池数据给rbk
                self.publish(battery_info)
                self.clearTimeout()
                # 清空缓冲区列表
                self.data_buff = []
                # 标记该次数据接收完成且正确
                self.msg_ok = True
                print("finish")
            else:
                self.data_buff.pop(0)

    def judgeMsgok(self):
        # 判断是否收到整包
        if self.msg_ok:
            # 清除超时错误,重置标志位
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                # 等待是否收到整包,若超时则报超时,并进入下次循环
                self.setTimeout()

    def loop(self):
        while True:
            #初始化查询报文list
            request = [0xDD,0xA5,0x03,0x00,0xFF,0xFD,0x77]
            #发送查询报文
            self.send(request)
            self.judgeMsgok()
            mu.sleepS(2)

if __name__ == '__main__':
    client = Battery()
    client.loop()