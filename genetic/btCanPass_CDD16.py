# --coding:utf-8--

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
        self.connect_timeout_t = mu.Timer(5000)
        # 用来表示数据是否已经正确接收
        self.msg_ok = False
        self.tem = []

    def handleData(self, msg):
        canframe = self.recCanframe(msg)
        tem = canframe.Data.hex()
        self.clearTimeout()
        if canframe.ID == 0x019E:
            # 取date部分值将hex转int（根据实际协议自行设定，此处为示例）
            if self.isNeedCharge():
                print("start charge")
                self.sendCanframe(2, 0x18FF50E5, 8, True, '01 20 03 E8 00 00 00 00')
            battery_info = self.createBatteryMessage()
            current = -round((int(tem[6:8] + tem[4:6], 16) - 32000) * 0.1, 2)
            voltage = round(int(tem[2:4] + tem[0:2], 16) * 0.1, 2)
            percentage = round(int(tem[8:10], 16) * 0.004, 2)
            battery_info.charge_voltage = voltage
            battery_info.max_charge_current = 3000.00
            battery_info.max_charge_voltage = 36.00
            battery_info.charge_current = current
            battery_info.percetage = percentage
            self.publish(battery_info)
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
        self.attachCanID(1, False, 1, 0x019E, 0, 0, 0)
        while True:
            # 等待是否收到整包,若超时则报超时,并进入下次循环
            self.judgeMsgok()
            mu.sleep_s(2)

if __name__ == '__main__':
    client = testCanBattery()
    client.loop()








