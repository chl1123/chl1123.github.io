import math
import time
import syspy.dmx512.dmx512_base as dmx
import syspy.lib.misc_utility as mu
from syspy import Battery, Controller, NavStatus, NavSpeed
from syspy import Logger

log = Logger("led")


class demo_dmx512(dmx.dmx512Base):

    def __init__(self):
        '''初始化基类,必须做'''
        super().__init__()
        # self.__debug_out = ud.udpDebug()
        # sys.stdout = self.__debug_out
        self.battery_exist = False
        self.ym_dxm512_enable = False
        self.cur_w = 0.0
        self.cur_x = 0.0
        self.cur_y = 0.0

    def run(self):
        dmx512_info = self.createDmx512Message()
        mu.sleep_s(20)
        while 1:
            """cur_w:旋转度, cur_x:前进距离, cur_y:平移距离"""
            self.cur_x, self.cur_y, self.cur_w = NavSpeed.get_speeds()

            '''cur_w:旋转度, cur_x:前进距离, cur_y:平移距离'''
            percentage = Battery.get_percentage()
            tem = percentage * 100.0
            dmx512_info.battery = int(tem)

            '''设定初始正常运动状态蓝色rgbw'''
            RGBW = [0, 80, 164, 0]
            dmx512_info.colorRed = RGBW[0]
            dmx512_info.colorGreen = RGBW[1]
            dmx512_info.colorBlue = RGBW[2]
            dmx512_info.colorWhite = RGBW[3]

            '''判断是否有电池信息'''''
            if dmx512_info.battery != 0:
                self.battery_exist = True
            else:
                self.battery_exist = False

            if self.warningExists(54001):
                self.battery_exist = False

            if (((self.getErrorNum() > 0) and \
                 not (self.getErrorNum() == 1 and self.errorExists(52200)) and \
                 not (self.getErrorNum() == 1 and self.errorExists(52201)) and \
                 not (self.getErrorNum() == 2 and self.errorExists(52200) and self.errorExists(52201))) \
                   ):
                '''报错状态下红色呼吸'''
                dmx512_info.type = dmx.LightType.Errofatal.value

            elif Controller.get_emc():
                '''急停状态下暗红色闪烁'''
                dmx512_info.type = dmx.LightType.FlowCalculator.value
                RGBW = [230, 30, 0, 0]
                dmx512_info.colorRed = RGBW[0]
                dmx512_info.colorGreen = RGBW[1]
                dmx512_info.colorBlue = RGBW[2]
                dmx512_info.colorWhite = RGBW[3]

            elif NavStatus.get_block():
                '''被阻挡状态下粉紫色跑马'''
                dmx512_info.type = dmx.LightType.MutableHorseRace.value
                RGBW = [30, 0, 30, 0]
                dmx512_info.colorRed = RGBW[0]
                dmx512_info.colorGreen = RGBW[1]
                dmx512_info.colorBlue = RGBW[2]
                dmx512_info.colorWhite = RGBW[3]

            elif not NavStatus.getChassisStop():
                '''正常运动下蓝色呼吸'''
                dmx512_info.type = dmx.LightType.MutableBreath.value
                if self.cur_w >= math.radians(1) * 3:
                    '''机身左旋'''
                    if self.cur_x > 0.0:
                        '''机身左旋+前进'''
                        dmx512_info.turnLeftOrRight = 1
                    elif self.cur_x < 0.0:
                        '''机身左旋+后退'''
                        dmx512_info.turnLeftOrRight = 2
                    else:
                        '''机身原地左旋'''
                        dmx512_info.turnLeftOrRight = 3

                elif self.cur_w <= math.radians(-1) * 3:
                    '''机身右旋'''
                    if self.cur_x > 0.0:
                        '''机身右旋+前进'''
                        dmx512_info.turnLeftOrRight = 2
                    elif self.cur_x < 0.0:
                        '''机身右旋+后退'''
                        dmx512_info.turnLeftOrRight = 1
                    else:
                        '''机身原地右旋'''
                        dmx512_info.turnLeftOrRight = 3

                else:
                    '''无转向状态'''
                    if self.cur_x < 0.0:
                        RGBW = [255, 250, 250, 0]
                        dmx512_info.colorRed = RGBW[0]
                        dmx512_info.colorGreen = RGBW[1]
                        dmx512_info.colorBlue = RGBW[2]
                        dmx512_info.colorWhite = RGBW[3]
                    dmx512_info.turnLeftOrRight = 0

            elif self.battery_exist:
                '''静止状态且battery存在'''
                maxPer = self.getBatteryMaxPercentage()
                if Battery.get_is_charging():
                    '''充电中为橙黄色呼吸'''
                    dmx512_info.type = dmx.LightType.Charging.value
                elif percentage * 100 < maxPer:
                    '''电量低于20 %（可配置）为暗红色跑马灯'''
                    dmx512_info.type = dmx.LightType.MutableHorseRace.value
                    RGBW = [170, 20, 0, 0]
                    dmx512_info.colorRed = RGBW[0]
                    dmx512_info.colorGreen = RGBW[1]
                    dmx512_info.colorBlue = RGBW[2]
                    dmx512_info.colorWhite = RGBW[3]
                else:
                    '''显示电量，从绿色至暗红色渐变'''
                    dmx512_info.type = dmx.LightType.Battery.value
                    tem = percentage * 100.0
                    dmx512_info.battery = int(tem)

            else:
                '''电池类型未配置且机器人静止为彩虹灯'''
                dmx512_info.type = dmx.LightType.Rainbow.value
            log.info(f"{dmx512_info=}")
            self.sendDmx512(dmx512_info)
            time.sleep(0.3)


if __name__ == '__main__':
    client = demo_dmx512()
    client.run()
