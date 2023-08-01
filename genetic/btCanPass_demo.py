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
        # 创建一个超时定时器
        self.connect_timeout_t = mu.Timer(2000)
        # 用来表示数据是否已经正确接收
        self.battery_info = self.createBatteryMessage()
        self.msg_ok = False
        self.tem = ""

    def handleData(self,msg):
        # 清除超时错误
        self.clearTimeout()
        # 当打开充电开关
        if self.isNeedCharge():
            print("start charge")
            # 自问自答模式，需发送如此canframe信息等待上报，若主动上报模式则无需发送
            self.sendCanframe(2, 0x36, 8, False, "10 20 33 54 66 18 77 00")
        canframe = self.recCanframe(msg)
        # 当id为54时，取电压，当id为55时，取电流
        # 取date部分值将hex转int（根据实际协议自行设定，此处为示例）
        if canframe.ID == 0x36:
            print("voltage")
            tem = canframe.Data.hex()
            voltage = round(int(tem[2:4] + tem[0:2], 16) * 0.1, 2)
            self.battery_info.charge_voltage = voltage
            # 发步电池数据给rbk
            self.publish(self.battery_info)
            self.msg_ok = True
        elif canframe.ID == 0x37:
            tem = canframe.Data.hex()
            current = round(cu.hexStr_to_int(tem[0:2] + tem[2:4], 8) * 0.1, 2)
            self.battery_info.charge_current = current
            # 发步电池数据给rbk
            self.publish(self.battery_info)
            self.msg_ok = True

    def judgeMsgok(self):
        # 判断是否收到整包
        if self.msg_ok:
            # 重置标志位
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            # 等待是否收到整包,若超时则报超时,并进入下次循环
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()
    def loop(self):
        # 需要至少5s来等待底层初始化,否则将会覆盖操作
        mu.sleep_s(5)
        # 绑定多个can邮箱，为绑定的邮箱个数，54，55，56分别为绑定的三个邮箱编号，0表示未绑定第四个邮箱
        self.attachCanID(2, 3, 0x36, 0x37, 0x38, 0)
        while True:
            self.judgeMsgok()
            mu.sleep_s(2)

if __name__ == '__main__':
    client = testCanBattery()
    client.loop()





