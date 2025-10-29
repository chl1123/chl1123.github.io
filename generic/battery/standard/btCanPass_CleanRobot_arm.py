

# 导入电池基类
import syspy.battery_Can.canpass_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud
import syspy.lib.char_utility as cu 
from syspy import Logger
log = Logger("battery")
class CanBattery(cb.canPassBase):

    def __init__(self):
        # 初始化基类,必须做
        super(CanBattery, self).__init__()
        # self.__debug_out = ud.udpDebug()
        # sys.stdout = self.__debug_out
        # 创建一个超时定时器
        self.connect_timeout_t = mu.Timer(5000)
        # 用来表示数据是否已经正确接收
        self.battery_info = self.createBatteryMessage()
        self.msg_ok = False
        self.port1 = 'can0'
        self.port2 = 'can1'
        self.port3 = 'can2'
        self.tem = []

    def handleData(self, msg):
        if msg.arbitration_id == 0x112:
            self.clearTimeout()
            tem = msg.data.hex()
            voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.1, 2)
            percentage = round(int(tem[8:10], 16) * 0.004, 2)
            temperature = round(int(tem[10:12], 16)-40, 2)
            current = round(cu.hexStr_to_int(tem[4:6] + tem[6:8],16) * 0.1, 2)
            if current < 0:
                isCharging = False
            else:
                isCharging = True
            self.battery_info.chargeVoltage = voltage
            self.battery_info.chargeCurrent = current
            self.battery_info.percentage = percentage
            self.battery_info.temperature = temperature
            self.battery_info.isCharging = isCharging
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
        mu.sleep_s(2)
        """
        这里的self.portX对应实际can通道接线的portX，CAN模型需要同步配置,880配置与实际接线通道相反需注意
        """
        self.createCanBus(self.port2, 500000)
        self.attachCanID(0x112)
        while True:
            self.judgeMsgok()
            mu.sleep_s(2)

if __name__ == '__main__':
    client = CanBattery()
    client.loop()








