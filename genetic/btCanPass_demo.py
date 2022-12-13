
import sys
# 导入电池基类
import syspy.battery_CAN.canpass_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud

class testCanBattery(cb.canPassBase):

    def __init__(self):
        # 初始化基类,必须做
        super(testCanBattery, self).__init__()
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out
        # 用来表示数据是否已经正确接收
        self.msg_ok = False
        self.tem = ""

    def handleData(self,msg):
        print("handleData")
        canframe = self.recCanframe(msg)
        battery_info = self.createBatteryMessage()
        # 当id为54时，取电压，当id为55时，取电流
        # 取date部分值将hex转int（根据实际协议自行设定，此处为示例）
        if canframe.ID == 54:
            print("voltage")
            tem = canframe.Data.hex()
            voltage = int(tem[10:16],16)/1024
            battery_info.charge_voltage = voltage
        elif canframe.ID == 55:
            print("current")
            tem = canframe.Data.hex()
            current = int(tem[10:16],16)/1024
            battery_info.charge_current = current
        # 发步电池数据给rbk
        self.publish(battery_info)
        self.msg_ok = True

    def loop(self):
        # 创建一个超时定时器
        connect_timeout_t = mu.Timer(2000)
        # 需要至少7s来等待底层初始化,否则将会覆盖操作
        mu.sleep_s(7)
        # 绑定多个can邮箱，3为绑定的邮箱个数，54，55，56分别为绑定的三个邮箱编号，0表示未绑定第四个邮箱
        self.attachCanID(3, 54, 55, 56, 0)
        while True:
            mu.sleep_s(2)
            # 自问自答模式，需发送如此canframe信息等待上报，若主动上报模式则无需发送
            self.sendCanframe(2, 54, 8, False, "10 20 33 54 66 18 77 00")
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
            mu.sleep_s(1)

if __name__ == '__main__':
    client = testCanBattery()
    client.loop()





