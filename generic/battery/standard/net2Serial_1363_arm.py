
import os
import threading
#导入电池基类
import syspy.battery_Serial.battery_base as bb
#处理字符的工具类，处理字符的工具类，如将uint16_t的数据转换成int16_t,
#用途:负号转换，将两个字节数据组合成一个16位的数据，其他数据处理需要自行编写。
import syspy.lib.char_utility as cu
#其他工具类,如定时器
import syspy.lib.misc_utility as mu
from syspy import Logger
log = Logger("battery")
from syspy import ParamServer

class ConfigParam:
    def __init__(self):
        self.param_server = ParamServer(__file__)
        self.dev = self.param_server.loadParam('devName', type="str", default="/dev/RS485_0", comment="串行端口对应的设备名")
        self.baudrate = self.param_server.loadParam('baudrate', type="int", default=9600,comment="波特率")
        self.timeoutThreshold = self.param_server.loadParam('timeoutThreshold', type="int", default=2000,comment="超时时间阈值(ms)")
        log.info("dev_name=" + str(self.dev) + " baudrate=" + str(self.baudrate) + " timeoutThreshold=" + str(self.timeoutThreshold))


class testBattery(bb.batteryBase):
    """
    继承电池基类
    """
    def __init__(self):
        #初始化基类,必须做
        super(testBattery,self).__init__()
        self.params = ConfigParam()
        # aarch64穿透需要初始化串口信息，880控制器串口uart0对应/dev/ttyS8
        self.createSerial(self.params.dev, self.params.baudrate)
        log.info(f'Create Serial Finished')
        #创建一个超时定时器
        self.connect_timeout_t = mu.Timer(self.params.timeoutThreshold)
        #创建一个列表用来缓冲接收数据
        self.data_buff = []
        #用来表示数据是否已经正确接收
        self.msg_ok = False
        self.sema_a = threading.Semaphore(1)  
        self.sema_b = threading.Semaphore(0)
        log.info(f'Class Init Finished')

    def handleData(self, msg:list):
        """
        必须实现基类中处理数据的handleData(msg)的函数)
        如下为示例
        """
        #存入收到的数据到缓冲中
        if len(self.data_buff)==0 or len(self.data_buff)>112:
            if len(self.data_buff)>112:
                self.data_buff = []
                log.info(f'sema_a release')
                self.sema_a.release()
            log.info(f'sema_b acquire')
            self.sema_b.acquire()
        self.data_buff.extend(msg)
        #print(len(self.data_buff))
        while len(self.data_buff) >= 112:
            if self.data_buff[0] == 0x7E:
                self.data_buff=self.data_buff[1:-1]
                result = []
                try:
                    for i in range(0, len(self.data_buff), 2):  
                        if i + 1 < len(self.data_buff): 
                            combined_value = int(chr(self.data_buff[i]) + chr(self.data_buff[i + 1]) ,16) 
                            result.append(combined_value)   
                    cell_num=result[8]
                    temper_base=8+2*cell_num+1
                    temper_num=result[temper_base]
                    pack_base=temper_base+2*temper_num+1

                    current=(result[pack_base] << 8 & 0xFF00)|(result[pack_base+1]& 0x00FF)
                    if current >= 0x8000:
                        current -= 0x10000
                    current*=(0.01)


                    voltage=(result[pack_base+2] << 8 & 0xFF00)|(result[pack_base+3]& 0x00FF)
                    voltage*=(0.001)

                    percentage=(result[pack_base+4] << 8 & 0xFF00)|(result[pack_base+5]& 0x00FF)

                    percentage/=(result[pack_base+7] << 8 & 0xFF00)|(result[pack_base+8]& 0x00FF)
                    circle=(result[pack_base+9] << 8 & 0xFF00)|(result[pack_base+10]& 0x00FF)
                    temp16_0=(result[temper_base+1] << 8 & 0xFF00)|(result[temper_base+2]& 0x00FF)
                    temp16_1=(result[temper_base+3] << 8 & 0xFF00)|(result[temper_base+4]& 0x00FF)
                    temp16_2=(result[temper_base+5] << 8 & 0xFF00)|(result[temper_base+6]& 0x00FF)

                    temperature=max(temp16_0,temp16_1,temp16_2)-40


                    battery_info = self.createBatteryMessage()
                    #解析后塞入相应字段
                    battery_info.percentage = percentage
                    battery_info.temperature = temperature
                    battery_info.cycle=circle
                    battery_info.chargeCurrent = current
                    battery_info.chargeVoltage = voltage
                    #发步电池数据给rbk
                    self.publish(battery_info)
                    # 清除超时报警
                    log.warning("finish")
                except Exception as e:
                        log.warning(f"Error in handleData: {e}")
                finally:
                    # 确保释放 sema_a
                    log.info(f'sema_a release')
                    self.sema_a.release()
                    self.clearTimeout()
                    #清空缓冲区列表
                    self.data_buff = []
                    #标记该次数据接收完成且正确
                    self.msg_ok = True

            else:
                # 第一个字节有误则去除
                self.data_buff = []
                log.info(f'sema_a release')
                self.sema_a.release()


    def judgeMsgok(self):
        # 超时检测函数
        if self.msg_ok:
            # 清除超时错误,重置标志位
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()
                log.warning(f"Connection timeout")

    def loop(self):
        """
        循环,处理发送及超时逻辑
        """
        while True:
            # 初始化查询报文list
            log.info(f'sema_a acquire')
            self.sema_a.acquire(timeout=5)
            request = [0x7E, 0x32, 0x30, 0x30, 0x31, 0x34, 0x36, 0x34, 0x32, 0x45, 0x30, 0x30, 0x32, 0x30, 0x31, 0x46,
                       0x44, 0x33, 0x35, 0x0D]
            # 发送查询报文
            self.send(request)
            log.info(f'sema_b release')
            self.sema_b.release() 
            # 循环检测是否超时
            self.judgeMsgok()
            mu.sleep_s(2)


if __name__ == '__main__':
    log.info(f"Scripts Start.")
    client = testBattery()
    client.loop()