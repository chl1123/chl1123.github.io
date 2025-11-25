
# import time
# 导入电池基类
import syspy.battery_Can.can_base as cb
# 其他工具类,如定时器
import syspy.lib.misc_utility as mu
import syspy.lib.udp_debug as ud
import syspy.lib.char_utility as cu
from syspy import Logger
log = Logger("battery")

error_dict = {
    1: "lowTemperature",
    2: "HighTemperature",
    3: "short_circuit",
    4: "over_current",
    5: "under_voltage",
    6: "over_voltage",
    7: "BMS_fault",
}


class ZLCanBattery(cb.CanBase):  # 创建中立电池类，继承电池基类

    def __init__(self):
        # 初始化基类,必须做
        super(ZLCanBattery, self).__init__()
        self.battery_info = self.createBatteryMessage()
        self.connect_timeout_t = mu.Timer(2000)
        self.id1 = self.id2 = False  # 定义电池id，上传状态，缺少id3协议充电
        self.msg_ok = False  # 定义电池信息传输状态
        self.port = self.getBatteryCanPort()
        self.cycle = 1
        self.cycle_time = mu.Timer(2000000)

    def handleData(self, msg):  
        self.judgeCanBattery(msg)
        self.judgePublish()

    def zl_hexStr_to_int(self, hex_str, Reserved_Digits):
        binary_str = bin(int(hex_str, 16))[2:].zfill(Reserved_Digits) 
        num = int(binary_str, 2)                            
        if binary_str[0] == '0':
            return 1 * num
        else:
            return num - 65535

    def judgeCanBattery(self, msg):  
        canframe = self.recCanframe(msg)  
        # --------------------------周期计时------------------------------------------- -------------------------
        if self.cycle_time.isTimeUp():
            self.cycle +=1
            self.battery_info.cycle = self.cycle
        # --------------------------电池电量电流电压解析------------------------------------------- -------------------------
        elif canframe.id == 0x3FC:  
            tem = canframe.data.hex()  
            voltage = round(int(tem[0:2] + tem[2:4], 16) * 0.1, 2)  # 解析电压 保留2位
            current = round(self.zl_hexStr_to_int(tem[4:6] + tem[6:8], 16) * 0.1, 2)  # 解析电流
            percentage = round(int(tem[12:14], 16) * 0.01, 2)  # 解析电池电量百分比
            self.battery_info.percentage = percentage  # 传入电池电量百分比
            self.battery_info.chargeVoltage = voltage  # 传入电池电压
            self.battery_info.chargeCurrent = current  # 传入电池电流
            for i in range(8):
                if cu.getBitVal(canframe.data[7], i) == 1:
                    if i == 0:
                        self.battery_info.isCharging = True
                    elif i in [1, 2, 3, 4, 5, 6, 7]:
                        pass
                        # error_msg = "Battery pack number:" + tem[14:16] + "error msg" + error_dict[i]
                        # self.setError(53140, error_msg)
                    else:
                        self.battery_info.isCharging = False
                    break
            self.msg_ok = True
            self.id1 = True
        # --------------------------电池温度------------------------------------------- -------------------------
        elif canframe.id == 0x4FC:
            tem = canframe.data.hex()
            MAXtemperature = round(int(tem[12:14], 16), 2)  # 解析电池单体最高温度,协议未明确说明时候有偏移量
            self.battery_info.temperature = MAXtemperature
            self.msg_ok = True
            self.id2 = True
        # -------------------------------电池协议充电-----------------------------------------------------
        # elif canframe.id == 0x0F4:
        #     tem = canframe.data.hex()
        #     if self.isNeedCharge():
        #         maxChargeVoltage = round(int(tem[0:2] + tem[2:4], 16) * 0.1, 2)
        #         maxChargeCurrent = round(int(tem[4:6] + tem[6:8], 16) * 0.1, 2)
        #         self.battery_info.maxChargeCurrent = maxChargeCurrent
        #         self.battery_info.maxChargeVoltage = maxChargeVoltage
        #     else:
        #         self.battery_info.maxChargeCurrent = 0
        #         self.battery_info.maxChargeVoltage = 0
        #     self.msg_ok = True
        #     self.id3 = True


    def judgePublish(self):  # 发布判断id是否正常接收
        if self.id1 and self.id2:
            self.publish(self.battery_info)
        else:
            print(f"wait 1 ids all recv: id1{self.id1} id2{self.id2}")

    def judgeMsgok(self):
        if self.msg_ok:
            # 清除超时错误,重置标志位
            self.msg_ok = False
            self.connect_timeout_t.reset()
            if not self.clear:
                if self.errorExists(57040):
                    print('clear')
                    self.clearTimeout()
                else:
                    self.clear = True
        else:
            if self.connect_timeout_t.isTimeUp():
                self.clear = False
                print('timeout')
                self.setTimeout()

    def loop(self):  # 重置底层
        mu.sleepS(5)
        # 绑定can通道和id
        self.attachCanID(self.port, 2, 0x3FC, 0x4FC)
        while True:  # 
            self.judgeMsgok()
            mu.sleepS(2)


if __name__ == '__main__':
    client = ZLCanBattery()
    client.loop()
