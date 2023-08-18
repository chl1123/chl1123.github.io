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
        self.battery_info = self.createBatteryMessage()
        self.connect_timeout_t = mu.Timer(5000)
        self.msg_ok = False
        self.is_charging = False
        self.tem = []

    def handleData(self, msg):
        canframe = self.recCanframe(msg)
        self.clearTimeout()
        if canframe.ID == 0x0EA0F40D:
            tem = canframe.Data.hex()
            percentage = round(int(tem[0:2], 16) * 0.01, 2)
            cycle = int(tem[4:6] + tem[6:8], 16)
            if int(tem[12:14], 16) == 1:
                self.is_charging = True
            else:
                self.is_charging = False
            self.battery_info.percetage = percentage
            self.battery_info.is_charging = self.is_charging
            self.battery_info.cycle = cycle
            self.publish(self.battery_info)
            self.msg_ok = True
        elif canframe.ID == 0x0EA1F40D:
            tem = canframe.Data.hex()
            current = round(cu.hexStr_to_int(tem[0:4] + tem[4:8], 18) * 0.001, 2)
            voltage = round(int(tem[8:12] + tem[12:16], 16) * 0.001, 2)
            self.battery_info.charge_voltage = voltage
            self.battery_info.charge_current = current
            self.publish(self.battery_info)
            self.msg_ok = True
        elif canframe.ID == 0x0EA2F40D:
            tem = canframe.Data.hex()
            temperature = round(int(tem[4:6], 16) - 40, 2)
            self.battery_info.temperature = temperature
            self.publish(self.battery_info)
            self.msg_ok = True
        elif canframe.ID == 0x0EA4F40D:
            tem = canframe.Data.hex()
            max_charge_voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.01, 2)
            max_charge_current = round(int(tem[4:6] + tem[6:8], 16) * 0.01, 2)
            self.battery_info.max_charge_current = max_charge_current
            self.battery_info.max_charge_voltage = max_charge_voltage
            self.publish(self.battery_info)
            self.msg_ok = True

    def judgeMsgok(self):
        if self.msg_ok:
            # 清除超时错误,重置标志位
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()

    def loop(self):
        # 需要至少5s来等待底层初始化,否则将会覆盖操作
        mu.sleep_s(5)
        self.attachCanID(2, 4, 0x0EA0F40D, 0x0EA1F40D, 0x0EA2F40D, 0x0EA4F40D)
        self.battery_info = self.createBatteryMessage()
        while True:
            self.judgeMsgok()
            mu.sleep_s(2)

if __name__ == '__main__':
    client = testCanBattery()
    client.loop()








