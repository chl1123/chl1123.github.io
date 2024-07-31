import sys
# 导入电池基类
import syspy.battery_Can.canpass_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud


class RuiBoTe(cb.canPassBase):

    def __init__(self):
        super(RuiBoTe, self).__init__()
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out
        self.battery_info = self.createBatteryMessage()
        self.connect_timeout_t = mu.Timer(7000)
        self.msg_ok = False
        self.open_charge = False
        self.srcname = self.getSrcName()
        if self.srcname == 'SRC880':
            self.port1 = 'can1'
            self.port2 = 'can0'
        else:
            self.port1 = 'can0'
            self.port2 = 'can1'
        self.port3 = 'can2'
        
        
    def getSrcName(self):
        with open('/etc/srcname', 'r') as file:
            srcname = file.readline().strip()
        return srcname


    def handleData(self, msg):
        self.judgeCanframe(msg)
        self.publish(self.battery_info)

    def judgeCanframe(self, msg):
        if msg.arbitration_id == 0x18FFA2F4:
            self.clearTimeout()
            tem = msg.data.hex()
            current = -round(int(tem[6:8] + tem[4:6], 16) * 0.1 - 400 , 2)
            voltage = round(int(tem[2:4] + tem[0:2], 16) * 0.1, 2)
            percentage = round(int(tem[8:10], 16) * 0.01, 2)
            self.battery_info.charge_current = current
            self.battery_info.charge_voltage = voltage
            self.battery_info.percetage = percentage
            self.msg_ok = True
        elif msg.arbitration_id == 0x18FFA5F4:
            self.clearTimeout()
            tem = msg.data.hex()
            temperature = round(int(tem[0:2], 16) - 50, 2)
            self.battery_info.temperature = temperature
            self.msg_ok = True
        elif msg.arbitration_id == 0x112:
            self.clearTimeout()
            tem = msg.data.hex()
            if int(tem[8:10], 16) == 1:
                self.battery_info.is_charging = True
            else:
                self.battery_info.is_charging = False
            self.msg_ok = True
        elif msg.arbitration_id == 0x111:
            self.clearTimeout()
            tem = msg.data.hex()
            if self.isNeedCharge():
                max_charge_voltage = round(int(tem[2:4] + tem[0:2], 16) * 0.01, 2)
                max_charge_current = round(int(tem[6:8] + tem[4:6], 16) * 0.01, 2)
                self.battery_info.max_charge_current = max_charge_current
                self.battery_info.max_charge_voltage = max_charge_voltage
                self.open_charge = True
            else:
                self.battery_info.max_charge_current = 0
                self.battery_info.max_charge_voltage = 0
                self.open_charge = False
            self.msg_ok = True
        elif msg.arbitration_id == 0x1A1:
            self.clearTimeout()
            tem = msg.data.hex()
            if int(tem[10:12], 16) == 1:
                self.battery_info.is_manually_connected = True
            else:
                self.battery_info.is_manually_connected = False
            self.msg_ok = True


    def judgeMsgok(self):
        if self.msg_ok:
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()

    def loop(self):
        mu.sleep_s(5)
        #self.port1 2 3,对应不用实际接线can通道，可按需修改
        self.attachCanID(self.port2, 5, 0x18FFA2F4, 0x18FFA5F4, 0x112, 0x111, 0x1A1)
        while True:
            if self.open_charge:
                self.sendCanframe(self.port2, 0x110, 8, False, [0x01,0x01,0x00,0x01,0x01,0xff,0x00,0x00])
            else:
                self.sendCanframe(self.port2, 0x110, 8, False, [0x01,0x00,0x01,0x01,0x00,0xff,0x00,0x00])
            self.judgeMsgok()
            mu.sleep_s(2)

if __name__ == '__main__':
    client = RuiBoTe()
    client.loop()








