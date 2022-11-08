import time
import math

import syspy.dmx512.dmx512_base as dmx

class demo_dmx512(dmx.dmx512Base):

    def __init__(self):
        # 初始化基类,必须做
        super(demo_dmx512, self).__init__()
        self.str1 = "battery"
        self.battery_exist = False
        self.is_chassis_stop = True
        self.is_stop = True
        self._last_emc_pressed = True
        self.ym_dxm512_enable = False
        self.is_show_charging = True
        self.is_show_battery = True
        self.cur_w = 0.0
        self.cur_x = 0.0
        self.cur_y = 0.0


    def run(self):

        global not_stop_counts

        while 1:
            time.sleep(2)

            movestatus_info = self.rec_moveStatus()
            robotspeed_info = self.rec_robotSpeed()
            dmx512_info = self.createDmx512Message()

            self.cur_w = robotspeed_info.rotate
            self.cur_x = robotspeed_info.x
            self.cur_y = robotspeed_info.y

            dmx_battery = self.rec_battery()
            tem = (dmx_battery.percetage * 100.0)
            dmx512_info.battery = int(tem)
            print(dmx512_info.battery)

            if self.is_chassis_stop:
                not_stop_counts = 0
            else:
                if not_stop_counts >= 1:
                    self.is_stop = False
                    print(self.is_stop)
                else:
                    not_stop_counts = not_stop_counts + 1

            dmx512_info.type = dmx.LightType.Rainbow.value

            RGBW = [0, 80, 164, 0]
            dmx512_info.color_r = RGBW[0]
            dmx512_info.color_g = RGBW[1]
            dmx512_info.color_b = RGBW[2]
            dmx512_info.color_w = RGBW[3]

            self.battery_exist = self.modelDeviceEnable(self.str1)
            if self.warningExists(54001):
                self.battery_exist = False

            if (((self.getErrorNum()>0) and \
                    not(self.getErrorNum() == 1 and self.errorExists(52200)) and \
                    not(self.getErrorNum() == 1 and self.errorExists(52702)) and \
                    not(self.getErrorNum() == 2 and self.errorExists(52200) and self.errorExists(52702))) \
                    or self.getFatalNum()>0):

                dmx512_info.type = dmx.LightType.Errofatal.value

            elif self._last_emc_pressed:
                print(self._last_emc_pressed)
                print("_last_emc_pressed")
                dmx512_info.type = dmx.LightType.FlowCalculator.value
                RGBW = [230, 30, 0, 0]
                dmx512_info.color_r = RGBW[0]
                dmx512_info.color_g = RGBW[1]
                dmx512_info.color_b = RGBW[2]
                dmx512_info.color_w = RGBW[3]

            elif movestatus_info.blocked:
                print("movestatus_info.blocked")
                dmx512_info.type = dmx.LightType.MutableHorseRace.value
                RGBW = [30, 0, 30, 0]
                dmx512_info.color_r = RGBW[0]
                dmx512_info.color_g = RGBW[1]
                dmx512_info.color_b = RGBW[2]
                dmx512_info.color_w = RGBW[3]

            elif (not self.is_stop):
                print("not self.is_stop")
                if (not self.ym_dxm512_enable):
                    dmx512_info.type = dmx.LightType.MutableBreath.value
                    if (self.cur_w >= math.radians(1) * 3):
                        if (self.cur_x > 0.0):
                            dmx512_info.turn_left_or_right=1
                        elif (self.cur_x < 0.0):
                            dmx512_info.turn_left_or_right=2
                        else:
                            dmx512_info.turn_left_or_right=3

                    elif (self.cur_w <= math.radians(-1) * 3):
                        if (self.cur_x > 0.0):
                            dmx512_info.turn_left_or_right=2
                        elif (self.cur_x < 0.0):
                            dmx512_info.turn_left_or_right=1
                        else:
                            dmx512_info.turn_left_or_right=3

                    else:
                        dmx512_info.turn_left_or_right=0

                else:
                    dmx512_info.type = dmx.LightType.MutableBreath.value
                    if (self.cur_x != 0.0):
                        dmx512_info.turn_left_or_right=4
                    else:
                        if (self.cur_x > 0.0):
                            if (self.cur_y == 0.0):
                                dmx512_info.turn_left_or_right=0
                            else:
                                dmx512_info.turn_left_or_right=4
                        elif (self.cur_x < 0.0):
                            if (self.cur_y == 0.0):
                                dmx512_info.turn_left_or_right=1
                            else:
                                dmx512_info.turn_left_or_right=4
                        else:
                            if (self.cur_y > 0.0):
                                dmx512_info.turn_left_or_right=2
                            elif (self.cur_y < 0.0):
                                dmx512_info.turn_left_or_right=3
                            else:
                                dmx512_info.turn_left_or_right=4

            elif self.battery_exist:
                maxPer = self.getBatteryMaxPercentage()
                if (dmx_battery.is_charging and self.is_show_charging):
                    dmx512_info.type = dmx.LightType.Charging.value
                elif (dmx_battery.percetage * 100 < maxPer):
                    dmx512_info.type = dmx.LightType.MutableHorseRace.value
                    RGBW = [170, 20, 0, 0]
                    dmx512_info.color_r = RGBW[0]
                    dmx512_info.color_g = RGBW[1]
                    dmx512_info.color_b = RGBW[2]
                    dmx512_info.color_w = RGBW[3]
                elif (self.is_show_battery):
                    dmx512_info.type = dmx.LightType.Battery.value
                    tem = (dmx_battery.percetage * 100.0)
                    dmx512_info.battery = int(tem)
                else:
                    dmx512_info.type = dmx.LightType.ConstantLight.value

            else:
                dmx512_info.type = dmx.LightType.Rainbow.value

            self.send_dmx512(dmx512_info)

if __name__ == '__main__':
    client = demo_dmx512()
    client.run()


