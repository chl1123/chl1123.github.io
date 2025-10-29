
# 导入电池基类
import syspy.battery_Can.can_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud
import syspy.lib.char_utility as cu
from syspy import Logger
log = Logger("battery")
class CanBattery(cb.CanBase):

    def __init__(self):
        # 初始化基类,必须做
        super(CanBattery, self).__init__()
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out
        # 用来表示数据是否已经正确接收
        self.port = self.getBatteryCanPort()
        self.battery_info = self.createBatteryMessage()
        self.connect_timeout_t = mu.Timer(5000)
        self.msg_ok = False
        self.tem = []

    def handleData(self, msg):
        # canframe = self.recCanframe(msg)
        self.clearTimeout()
        if msg.arbitration_id == 0x1AC:
            # tem = canframe.data.hex()
            tem = msg.data.hex()
            percentage = int(tem[2:4], 16) / 100
            voltage = round((int(tem[4:6], 16) * 256 + int(tem[6:8], 16)) / 1000, 2)
            # if cu.get_bit_val(canframe.data[0], 0) == 0:
                # current = -round((int(tem[8:10], 16) * 256 + int(tem[10:12], 16)) / 100, 2)
            current = round(cu.hexStr_to_int(tem[8:10] + tem[10:12], 16) * 0.01, 2)
            # else:
                # current = round((int(tem[8:10], 16) * 256 + int(tem[10:12], 16)) / 100, 2)
            if int(tem[12:14], 16) == 0:
                temperature = round(int(tem[14:16], 16), 2)
            else:
                temperature = -round(int(tem[14:16], 16), 2)

            self.battery_info.percentage = percentage
            self.battery_info.chargeVoltage = voltage
            self.battery_info.chargeCurrent = current
            self.battery_info.temperature = temperature
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
        mu.sleep_s(5)
        self.createCanBus(self.port, 125000)
        self.attachCanID( 0x1AC)
        while True:
            self.judgeMsgok()
            mu.sleep_s(2)


if __name__ == '__main__':
    client = CanBattery()
    client.loop()