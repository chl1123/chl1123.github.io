import sys
# 导入电池基类
import syspy.battery_Can.canpass_base as cb
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
        self.tem = []
        self.battery_info = self.createBatteryMessage()
        self.sendCanframe(1, 0x101, 8, True, '02 00 00 00 00 00 00 00')
        self.byte3 = 0b00

    def handleData(self, msg):
        canframe = self.recCanframe(msg)
        if canframe.ID == 0x11:
            tem = canframe.Data.hex()
            byte3 = canframe.Data[2] & 0b01111111
            current_H = str(byte3)
            # 取date部分值将hex转int（根据实际协议自行设定，此处为示例）
            voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.01, 2)
            percentage = round(int(tem[8:10], 16) * 0.01, 2)
            temperature = round(int(tem[10:12], 16) - 40, 2)
            if int(tem[12:14], 16) == 1:
                is_charging = True
                current = round(int(current_H + tem[6:8], 16) * 0.01, 2)
            else:
                is_charging = False
                current = -round(int(current_H + tem[6:8], 16) * 0.01, 2)
            self.battery_info.charge_voltage = voltage
            self.battery_info.charge_current = current
            self.battery_info.percetage = percentage
            self.battery_info.temperature = temperature
            self.battery_info.is_charging = is_charging
            self.publish(self.battery_info)
            self.msg_ok = True
        elif canframe.ID == 0x18:
            tem = canframe.Data.hex()
            max_charge_voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.1, 2)
            max_charge_current = round(int(tem[4:6] + tem[6:8], 16) * 0.1, 2)
            self.battery_info.max_charge_current = max_charge_current
            self.battery_info.max_charge_voltage = max_charge_voltage
            self.publish(self.battery_info)
            self.msg_ok = True
        # 发步电池数据给rbk

    def loop(self):
        # 创建一个超时定时器
        connect_timeout_t = mu.Timer(2000)
        # 需要至少7s来等待底层初始化,否则将会覆盖操作
        mu.sleep_s(7)
        self.attachCanID(1, True, 2, 0x00000011, 0x00000018, 0, 0)
        self.battery_info = self.createBatteryMessage()
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
            mu.sleep_s(2)

if __name__ == '__main__':
    client = testCanBattery()
    client.loop()








