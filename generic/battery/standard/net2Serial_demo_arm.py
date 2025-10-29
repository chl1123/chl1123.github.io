
import os

#导入电池基类
import syspy.battery_Serial.battery_base as bb
#处理字符的工具类，处理字符的工具类，如将uint16_t的数据转换成int16_t,
#用途:负号转换，将两个字节数据组合成一个16位的数据，其他数据处理需要自行编写。
import syspy.lib.char_utility as cu
#其他工具类,如定时器
import syspy.lib.misc_utility as mu
from syspy import Logger
from syspy import ParamServer

log = Logger("battery")
class ConfigParam:
    def __init__(self):
        self.param_server = ParamServer(__file__)
        self.dev = self.param_server.loadParam('devName', type="str", default="/dev/ttyS8", comment="串行端口对应的设备名")
        self.baudrate = self.param_server.loadParam('baudrate', type="int", default=9600,comment="波特率")
        self.timeoutThreshold = self.param_server.loadParam('timeoutThreshold', type="int", default=2000,comment="超时时间阈值(ms)")
        log.info("dev_name=" + str(self.dev) + " baudrate=" + str(self.baudrate) + " timeoutThreshold=" + str(self.timeoutThreshold))
class Battery(bb.batteryBase):
    """
    继承电池基类
    """
    def __init__(self):
        #初始化基类,必须做
        super(Battery,self).__init__()
        self.params = ConfigParam()
        # aarch64穿透需要初始化串口信息，880控制器串口uart0对应/dev/ttyS8
        self.createSerial(self.params.dev, self.params.baudrate)
        #创建一个超时定时器
        self.connect_timeout_t = mu.Timer(self.params.timeoutThreshold)
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
        self.data_buff.extend(msg)
        print(len(self.data_buff))
        #判断报文长度
        while len(self.data_buff) >= 105:
            #校验帧头是否正确
            if self.data_buff[0] == 0x01:
                #转换电池数据
                voltage = cu.merge2bytesTo1(self.data_buff[39],self.data_buff[40]) * 0.01
                current = cu.u16Toint16(cu.merge2bytesTo1(self.data_buff[41],self.data_buff[42])) * 0.01    #是int16类型
                temp16_1 = (cu.merge2bytesTo1(self.data_buff[77],self.data_buff[78]) - 2731) * 0.1
                temp16_2 = (cu.merge2bytesTo1(self.data_buff[79],self.data_buff[80]) - 2731) * 0.1
                temperature = temp16_1
                if temp16_1 < temp16_2:
                    temperature = temp16_2
                percentage = cu.merge2bytesTo1(self.data_buff[83],self.data_buff[84]) * 0.01
                #创建一个电池信息的proto对象
                battery_info = self.createBatteryMessage()
                #解析后塞入相应字段
                battery_info.percentage = percentage
                battery_info.temperature = temperature
                battery_info.chargeCurrent = current
                battery_info.chargeVoltage = voltage
                #发步电池数据给rbk
                self.publish(battery_info)
                # 清除超时报警
                self.clearTimeout()
                #清空缓冲区列表
                self.data_buff = []
                #标记该次数据接收完成且正确
                self.msg_ok = True
                print("finish")
            else:
                # 第一个字节有误则去除
                self.data_buff.pop(0)


    def judgeMsgok(self):
        # 超时检测函数
        if self.msg_ok:
            # 清除超时错误,重置标志位
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()

    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        while True:
            # 初始化查询报文list
            request = [0x01, 0x03, 0x00, 0x00, 0x00, 0x32, 0xC4, 0x1F]
            # 发送查询报文
            self.send(request)
            # 循环检测是否超时
            self.judgeMsgok()
            mu.sleep_s(2)

if __name__ == '__main__':
    client = Battery()
    client.loop()