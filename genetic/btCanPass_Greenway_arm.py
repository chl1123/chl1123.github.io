import sys
# 导入电池基类
import syspy.battery_Can.canpass_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud
import syspy.lib.char_utility as cu

error_dict = {
    (1, 0): "first-level overvoltage",
    (1, 1): "second-level overvoltage",
    (1, 2): "Overcharge protection",
    (1, 3): "Overcurrent during charging",
    (1, 4): "high temperature during charging",
    (1, 5): "low temperature during charging",
    (1, 6): "charging timeout",
    (1, 7): "first-level undervoltage",
    (2, 0): "second-level undervoltage",
    (2, 1): "first-level overcurrent during discharge",
    (2, 2): "second-level overcurrent during discharge",
    (2, 3): "short circuit",
    (2, 4): "high temperature during discharge",
    (2, 5): "low temperature during discharge",
    (2, 6): "MOS high temperature protection",
    (2, 7): "low voltage prohibits charging and discharging",
    (3, 0): "large difference in inter-group cycling times",
    (3, 1): "excessive individual cell pressure difference",
}


class testCanBattery(cb.canPassBase):

    def __init__(self):
        super(testCanBattery, self).__init__()
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out
        self.battery_info = self.createBatteryMessage()
        self.connect_timeout_t = mu.Timer(7000)
        self.id1,self.id2,self.id3,self.id4 = False,False,False,False
        self.msg_ok = False
        self.msg_userdata = False
        self.first = True
        self.port1 = 'can0'
        self.port2 = 'can1'
        self.port3 = 'can2'
        self.id = ""
        self.year = ""
        self.week = ""
        self.number = ""

    def handleData(self, msg):
        self.judgeCanframe(msg)
        self.judgePublish()

    def judgeCanframe(self, msg):
        if msg.arbitration_id == 0x0DA2F40D and not self.msg_userdata:
            self.clearTimeout()
            tem = msg.data.hex()
            if tem[2:14] == 'ffffffffffff':
                self.msg_userdata = True
                self.msg_ok = True
            else:
                if int(tem[1:2], 16) == 1:
                    self.id = hex(int(tem[3:4] + tem[5:6]))[2:].zfill(2)
                    self.year = hex(int(tem[7:8] + tem[9:10] + tem[11:12] + tem[13:14]))[2:].zfill(4)
                elif int(tem[1:2], 16) == 2:
                    self.week = hex(int(tem[3:4] + tem[5:6]))[2:].zfill(2)
                elif int(tem[1:2], 16) == 3:
                    self.number = hex(int(tem[15:16]))[2:].zfill(8)
                if (self.id and self.year and self.week and self.number) != "":
                    self.battery_info.user_data = bytes(self.id + self.year + self.week + self.number, encoding='utf-8')
                    self.msg_userdata = True
                    self.msg_ok = True
        if msg.arbitration_id == 0x0EA0F40D:
            self.clearTimeout()
            tem = msg.data.hex()
            percentage = round(int(tem[0:2], 16) * 0.01, 2)
            cycle = int(tem[4:6] + tem[6:8], 16)
            if int(tem[12:14], 16) == 1:
                self.battery_info.is_charging = True
            else:
                self.battery_info.is_charging = False
            self.battery_info.percetage = percentage
            self.battery_info.cycle = cycle
            self.msg_ok = True
            self.id1 = True
        elif msg.arbitration_id == 0x0EA1F40D:
            self.clearTimeout()
            tem = msg.data.hex()
            current = round(cu.hexStr_to_int(tem[0:4] + tem[4:8], 18) * 0.001, 2)
            voltage = round(int(tem[8:12] + tem[12:16], 16) * 0.001, 2)
            self.battery_info.charge_voltage = voltage
            self.battery_info.charge_current = current
            self.msg_ok = True
            self.id2 = True
        elif msg.arbitration_id == 0x0EA2F40D:
            self.clearTimeout()
            tem = msg.data.hex()
            temperature = round(int(tem[4:6], 16) - 40, 2)
            if temperature <= -19:
                self.setError("The current temperature has reached " + str(temperature) + " degrees , low temperature error!")
            elif -19 < temperature <= -15:
                self.setWarning("The current temperature has reached " + str(temperature) + " degrees , low temperature warning.")
            elif 55 <= temperature < 59:
                self.setWarning("The current temperature has reached " + str(temperature) + " degrees , high temperature warning.")
            elif temperature >= 59:
                self.setError("The current temperature has reached " + str(temperature) + " degrees , high temperature error!")
            self.battery_info.temperature = temperature
            self.msg_ok = True
            self.id3 = True
        elif msg.arbitration_id == 0x0EA4F40D:
            self.clearTimeout()
            tem = msg.data.hex()
            if self.isNeedCharge():
                print("start charge")
                max_charge_voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.01, 2)
                max_charge_current = round(int(tem[4:6] + tem[6:8], 16) * 0.01, 2)
                self.battery_info.max_charge_current = max_charge_current
                self.battery_info.max_charge_voltage = max_charge_voltage
            else:
                self.battery_info.max_charge_current = 0
                self.battery_info.max_charge_voltage = 0
            self.msg_ok = True
            self.id4 = True
        elif msg.arbitration_id == 0x1EA7F40D:
            self.clearTimeout()
            tem = msg.data.hex()
            for i in range(1, 4):
                for j in range(8):
                    if cu.get_bit_val(msg.data[i], j) == 1:
                        if (i == 3 and j == 0) or (i == 1 and j == 2) or (i == 1 and j == 0) or (i == 1 and j == 1):
                            error_msg = "Battery pack number: " + tem[0:2] + " warning msg: " + error_dict[(i, j)]
                            self.setWarning(error_msg)
                        else:
                            error_msg = "Battery pack number: " + tem[0:2] + " error msg: " + error_dict[(i, j)]
                            self.setError(error_msg)
                        break

    def judgePublish(self):
        if self.id1 and self.id2 and self.id3 and self.id4:
            self.publish(self.battery_info)
        else:
            print("not")

    def judgeMsgok(self):
        if self.msg_ok:
            self.msg_ok = False
            self.connect_timeout_t.reset()
        else:
            if self.connect_timeout_t.isTimeUp():
                self.setTimeout()

    def loop(self):
        mu.sleep_s(2)
        """
        这里的self.portX对应实际can通道接线的portX，CAN模型需要同步配置,880配置与实际接线通道相反需注意
        """
        self.createCanBus(self.port3, 250000)
        self.attachCanID(0x0DA2F40D, 0x0EA0F40D, 0x0EA1F40D, 0x0EA2F40D, 0x0EA4F40D, 0x1EA7F40D)
        while True:
            if not self.msg_userdata:
                self.sendCanframe(self.port3, 0x0DA20DF4, 8, True, [0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00])
            self.judgeMsgok()
            mu.sleep_s(2)

if __name__ == '__main__':
    client = testCanBattery()
    client.loop()








