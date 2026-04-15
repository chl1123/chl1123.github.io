# --coding:utf-8--


# 导入电池基类
import syspy.battery_Can.can_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud
from syspy import Logger
from syspy import Trace
class CanBattery(cb.CanBase):

    def __init__(self):
        # 初始化基类,必须做
        super(CanBattery, self).__init__()
        #self.__debug_out = ud.udpDebug()
        #sys.stdout = self.__debug_out
        # 用来表示数据是否已经正确接收
        self.battery_info = self.createBatteryMessage()
        self.connect_timeout_t = mu.Timer(5000)
        self.wait = mu.Timer(10000)
        self.msg_ok = False
        self.first = True
        self.tem = []

    def handleData(self, msg):
        self.judgeCanframe(msg)
        self.judgePublish()

    def judgeCanframe(self, msg):
        canframe = self.recCanframe(msg)

        if canframe.id == 0x019E:
            self.clearTimeout()
            tem = canframe.data.hex()
            current = -round((int(tem[6:8] + tem[4:6], 16) - 32000) * 0.1, 2)
            voltage = round(int(tem[2:4] + tem[0:2], 16) * 0.1, 2)
            percentage = round(int(tem[8:10], 16) * 0.004, 2)
            self.battery_info.chargeVoltage = voltage
            self.battery_info.chargeCurrent = current
            self.battery_info.percentage = percentage
            self.battery_info.SOH = int(100)
            self.msg_ok = True
        elif canframe.id == 0x1806E5F4:
            self.clearTimeout()
            tem = canframe.data.hex()
            if self.isNeedCharge():
                Trace.log("start charge")
                can_data = [tem[0:2], tem[2:4], tem[4:6], tem[6:8], '00', '00', '00', '00']
                can_string = ' '.join(can_data).upper()
                Trace.log(can_string)
                self.sendCanframe(2, 0x18FF50E5, 8, True, can_string)
            max_voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.1, 2)
            max_current = round(int(tem[4:6] + tem[6:8], 16) * 0.1, 2)
            self.battery_info.maxChargeCurrent = max_current
            self.battery_info.maxChargeVoltage = max_voltage
            self.msg_ok = True
        elif canframe.id == 0x1800FFF4:
            self.clearTimeout()
            tem = canframe.data.hex()
            temperature = round(int(tem[10:12], 16) - 40, 2)
            self.battery_info.temperature = temperature
            self.msg_ok = True

    def judgePublish(self):
        if self.first:
            if self.wait.isTimeUp():
                self.publish(self.battery_info)
                self.first = False
        else:
            self.publish(self.battery_info)

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
        mu.sleepS(5)
        self.attachCanID(2, 3, 0x1806E5F4, 0x1800FFF4, 0x019E, 0)
        #self.attachCanID(1, 1, 0x019E, 0, 0, 0)
        while True:
            # 等待是否收到整包,若超时则报超时,并进入下次循环
            self.judgeMsgok()
            mu.sleepS(2)

if __name__ == '__main__':
    client = CanBattery()
    client.loop()








