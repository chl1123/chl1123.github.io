
import sys
# 导入电池基类
import syspy.battery_Can.canpass_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud
import syspy.lib.char_utility as cu 

class testCanBattery(cb.canPassBase):

    def __init__(self):
        # 初始化基类,必须做
        super(testCanBattery, self).__init__()
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out
        # 用来表示数据是否已经正确接收
        self.msg_ok = False
        self.tem = []

    def handleData(self,msg):
        canframe = self.recCanframe(msg)
        battery_info = self.createBatteryMessage()
        # 取date部分值将hex转int（根据实际协议自行设定，此处为示例）
        if canframe.ID == 0x2F0:
            print("huafu infomation")
            tem = canframe.Data.hex()
            if cu.get_bit_val(canframe.Data[7],0) == 0:
                current = -round(int(tem[6:8] + tem[4:6], 16) * 0.1, 2)
            else:
                current = round(int(tem[6:8] + tem[4:6], 16) * 0.1, 2)
            voltage = round(int(tem[2:4] + tem[0:2], 16) * 0.1, 2)
            percentage = round(int(tem[8:10],16)*0.001,2)
            battery_info.charge_voltage = voltage
            battery_info.charge_current = current
            battery_info.percetage = percentage
        # 发步电池数据给rbk
        self.publish(battery_info)
        self.msg_ok = True

    def loop(self):
        # 创建一个超时定时器
        connect_timeout_t = mu.Timer(3000)
        # 需要至少7s来等待底层初始化,否则将会覆盖操作
        mu.sleep_s(7)
        # 绑定多个can邮箱，1为绑定的邮箱个数，false表示非扩展帧，0x2F0表示第一个邮箱canid号，0表示未绑定第四个邮箱
        self.attachCanID(1, False, 1, 0x2F0, 0, 0, 0)
        while True:
            # 判断是否收到整包
            if self.msg_ok:
                # 清除超时错误,重置标志位
                self.clearTimeout()
                self.msg_ok = False
                connect_timeout_t.reset()
            # 等待是否收到整包,若超时则报超时,并进入下次循环
            while not self.msg_ok:
                if connect_timeout_t.isTimeUp():
                    self.setTimeout()
                    break

if __name__ == '__main__':
    client = testCanBattery()
    client.loop()





