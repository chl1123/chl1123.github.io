# 导入电池基类
import syspy.battery_Can.can_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu

import syspy.lib.char_utility as cu
import sys
from syspy import Trace

from syspy.battery_runner import run_battery_script
class CanBattery(cb.CanBase):

    def __init__(self):
        # 初始化基类,必须做
        super(CanBattery, self).__init__()
        # 用来表示数据是否已经正确接收
        self.port = self.getBatteryCanPort()
        self.battery_info = self.createBatteryMessage()
        self.connect_timeout_t = mu.Timer(5000)
        self.msg_ok = False
        self.tem = []

    def handleData(self, msg):
        canframe = self.recCanframe(msg)
        self.clearTimeout()
        if canframe.id == 0x1AC:
            tem = canframe.data.hex()
            percentage = int(tem[2:4], 16) / 100
            voltage = round((int(tem[4:6], 16) * 256 + int(tem[6:8], 16)) / 1000, 2)
            current = round(cu.hexStrToInt(tem[8:10] + tem[10:12], 16) * 0.01, 2)
            if int(tem[12:14], 16) == 0:
                temperature = round(int(tem[14:16], 16), 2)
            else:
                temperature = -round(int(tem[14:16], 16), 2)

            self.battery_info.percentage = percentage
            self.battery_info.chargeVoltage = voltage
            self.battery_info.chargeCurrent = current
            self.battery_info.temperature = temperature
            self.battery_info.SOH = int(100)
            self.publish(self.battery_info)
            self.msg_ok = True

        elif canframe.id == 0x1806E5F4:
            tem = canframe.data.hex()
            if self.isNeedCharge():
                print("start charge")
                self.sendCanframe(self.port, 0x18FF50E5, 8, True, [0x01, 0x20, 0x03, 0xe8, 0x00, 0x00, 0x00, 0x00])
            max_voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.1, 2)
            max_current = round(int(tem[4:6] + tem[6:8], 16) * 0.1, 2)
            self.battery_info.maxChargeCurrent = max_current
            self.battery_info.maxChargeVoltage = max_voltage
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
        # 需要至少7s来等待底层初始化,否则将会覆盖操作
        mu.sleepS(5)
        self.createCanBus(self.port, 125000)
        self.attachCanID(self.port, 2, 0x1AC, 0x1806E5F4)
        while True:
            self.judgeMsgok()
            mu.sleepS(2)


if __name__ == '__main__':
    run_battery_script(CanBattery)
