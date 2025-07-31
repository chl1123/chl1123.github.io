
# 导入电池基类
import syspy.battery_Can.canpass_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.char_utility as cu
import json

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
        self.battery_info = self.createBatteryMessage()
        self.connect_timeout_t = mu.Timer(2000)
        self.abnormal_timeout_t = mu.Timer(5000)
        self.id1=self.id2=self.id3=self.id4=self.msg_ok=self.is_abnormal=self.msg_userdata=self.wake_up=self.clear = False
        self.first = True
        self.port = self.getBatteryCanPort()
        self.id=self.year=self.week=self.number = ""
        self.previous_temperature = None
        self.temperature_buffer = []

    def handleData(self, msg):
        self.judgeCanframe(msg)
        self.judgePublish()

    def judgeCanframe(self, msg):
        canframe = self.recCanframe(msg)
        if canframe.ID == 0x0DA2F40D and not self.msg_userdata:
            tem = canframe.Data.hex()
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
        if canframe.ID == 0x0EA0F40D:
            tem = canframe.Data.hex()
            percentage = round(int(tem[0:2], 16) * 0.01, 2)
            SOH = round(int(tem[2:4], 16) * 0.01, 2)
            cycle = int(tem[4:6] + tem[6:8], 16)
            if int(tem[12:14], 16) == 1:
                self.battery_info.is_charging = True
            else:
                self.battery_info.is_charging = False
            self.battery_info.percetage = percentage
            self.battery_info.extra = json.dumps({"SOH": SOH})
            self.battery_info.cycle = cycle
            self.msg_ok = True
            self.id1 = True
        elif canframe.ID == 0x0EA1F40D:
            tem = canframe.Data.hex()
            current = round(cu.hexStr_to_int(tem[0:4] + tem[4:8], 18) * 0.001, 2)
            voltage = round(int(tem[8:12] + tem[12:16], 16) * 0.001, 2)
            self.battery_info.charge_voltage = voltage
            self.battery_info.charge_current = current
            self.msg_ok = True
            self.id2 = True
        elif canframe.ID == 0x0EA2F40D:
            tem = canframe.Data.hex()
            temperature = round(int(tem[4:6], 16) - 40, 2)

            if self.previous_temperature is not None and abs(temperature - self.previous_temperature) > 10:
                self.temperature_buffer.append(temperature)
                if len(self.temperature_buffer) >= 3:
                    self.previous_temperature = temperature  # 更新上次温度值
                    self.temperature_buffer = []  # 清空缓冲区
            else:
                self.previous_temperature = temperature
                self.temperature_buffer = []  # 如果温差小于10度，重置缓冲区
                if temperature <= -19:
                    self.setError(53140, "The current temperature has reached " + str(
                        temperature) + " degrees , low temperature error!")
                elif -19 < temperature <= -15:
                    self.setWarning(54400, "The current temperature has reached " + str(
                        temperature) + " degrees , low temperature warning.")
                elif 55 <= temperature < 59:
                    self.setWarning(54400, "The current temperature has reached " + str(
                        temperature) + " degrees , high temperature warning.")
                elif temperature >= 59:
                    self.setError(53140, "The current temperature has reached " + str(
                        temperature) + " degrees , high temperature error!")

            self.battery_info.temperature = temperature
            self.msg_ok = True
            self.id3 = True
        elif canframe.ID == 0x0EA4F40D:
            tem = canframe.Data.hex()
            if self.isNeedCharge():
                max_charge_voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.01, 2)
                max_charge_current = round(int(tem[4:6] + tem[6:8], 16) * 0.01, 2)
                self.battery_info.max_charge_current = max_charge_current
                self.battery_info.max_charge_voltage = max_charge_voltage
            else:
                self.battery_info.max_charge_current = 0
                self.battery_info.max_charge_voltage = 0
            self.msg_ok = True
            self.id4 = True
        elif canframe.ID == 0x1EA7F40D:
            tem = canframe.Data.hex()
            for i in range(1, 4):
                for j in range(8):
                    if cu.get_bit_val(canframe.Data[i], j) == 1:
                        if (i, j) == (1, 2):
                            # 过滤过充保护warning
                            continue
                        if (i == 3 and j == 0) or (i == 1 and j == 0) or (i == 1 and j == 1):
                            error_msg = "Battery pack number: " + tem[0:2] + " warning msg: " + error_dict[(i, j)]
                            self.setWarning(54400, error_msg)
                        else:
                            error_msg = "Battery pack number: " + tem[0:2] + " error msg: " + error_dict[(i, j)]
                            self.setError(53140,error_msg)
                        self.is_abnormal = True
                        break

    def judgePublish(self):
        if self.id1 and self.id2 and self.id3 and self.id4:
            self.publish(self.battery_info)
        else:
            print(f"wait 4 ids all recv: id1{self.id1} id2{self.id2} id3{self.id3} id4{self.id4}")

    def judgeMsgok(self):
        if self.msg_ok:
            # 清除超时错误,重置标志位
            self.msg_ok = False
            self.connect_timeout_t.reset()
            self.wake_up = False
            if not self.clear:
                if self.warningExists(54001):
                    print('clear')
                    self.clearTimeout()
                else:
                    self.clear = True
        else:
            if self.connect_timeout_t.isTimeUp():
                if not self.wake_up and (self.id == "0b" or self.id == "0d" or self.id == "0e"):
                    self.sendCanframe(self.port, 0x0DA20DF4, 8, True, '01 00 00 00 00 00 00 00')
                    self.wake_up = True # 主动唤醒
                    print("wake_up")
                else:
                    self.clear = False
                    print('timeout')
                    self.setTimeout()
        if (self.id == "0e") and (self.isNeedCharge()) : #继电器没有打开且需要打开
            self.sendCanframe(self.port, 0x0DA30DF4, 8, True, "01,00,00,00,00,00,00,00")

        self.handle_abnormal_state()

    def handle_abnormal_state(self, warning_code=54400):
        if self.is_abnormal:
            self.is_abnormal = False
            self.abnormal_timeout_t.reset()
            print('is_abnormal')
        elif self.abnormal_timeout_t.isTimeUp() and self.warningExists(warning_code):
            print('clearWarning')
            self.clearWarning(warning_code)

    def loop(self):
        mu.sleep_s(5)
        self.attachCanID(self.port, 1, 0x0DA2F40D)
        while True:
            self.sendCanframe(self.port, 0x0DA20DF4, 8, True, '01 00 00 00 00 00 00 00')
            mu.sleep_s(2)
            if self.msg_userdata:
                break
        self.attachCanID(self.port, 5, 0x0EA0F40D, 0x0EA1F40D, 0x0EA2F40D, 0x0EA4F40D, 0x1EA7F40D)
        while True:
            self.judgeMsgok()
            mu.sleep_s(2)

if __name__ == '__main__':
    client = testCanBattery()
    client.loop()








