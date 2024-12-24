import math
import sys
sys.path.append('/usr/local/etc/.SeerRobotics/rbk/resources/scripts/site-packages')
sys.path.append('/opt/.data/rbk/resources/scripts/')
import syspy.dmx512.dmx512_base as dmx
# import syspy.lib.udp_debug as ud
import syspy.lib.misc_utility as mu
from syspy.move import Move
from syspy.navigation import NavSpeed
from syspy.battery import Battery
from syspy.controller import Controller

class demo_dmx512(dmx.dmx512Base):

    def __init__(self):
        '''初始化基类,必须做'''
        super(demo_dmx512, self).__init__()
        # self.__debug_out = ud.udpDebug()
        # sys.stdout = self.__debug_out
        self.str1 = "battery"
        self.not_stop_counts = 0
        self.battery_exist = False
        self.is_stop = True
        self.ym_dxm512_enable = False
        self.cur_w = 0.0
        self.cur_x = 0.0
        self.cur_y = 0.0

    def run(self):
        dmx512_info = self.createDmx512Message()
        mu.sleep_s(10)
        while 1:
            '''从其他插件获取所需相关数据信息'''
            Move.update()
            NavSpeed.update()
            Battery.update()
            Controller.update()

            '''cur_w:旋转度, cur_x:前进距离, cur_y:平移距离'''
            self.cur_w = NavSpeed.rotate
            self.cur_x = NavSpeed.x
            self.cur_y = NavSpeed.y

            '''实时获取电池信息并转换为dmx类型 '''
            tem = (Battery.percentage * 100.0)
            dmx512_info.battery = int(tem)

            '''非停止状态计数'''
            if Move.getChassisStop() == True :
                self.is_stop = True
            else:
                if self.not_stop_counts >= 1:
                    self.is_stop = False
                else:
                    self.not_stop_counts = self.not_stop_counts + 1

            '''设定初始正常运动状态蓝色rgbw'''
            RGBW = [0, 80, 164, 0]
            dmx512_info.color_r = RGBW[0]
            dmx512_info.color_g = RGBW[1]
            dmx512_info.color_b = RGBW[2]
            dmx512_info.color_w = RGBW[3]

            '''判断是否有电池信息'''''
            if dmx512_info.battery != 0:
                self.battery_exist = True
            else:
                self.battery_exist = False

            if self.warningExists(54001):
                self.battery_exist = False

            if (((self.getErrorNum()>0) and \
                    not(self.getErrorNum() == 1 and self.errorExists(52200)) and \
                    not(self.getErrorNum() == 1 and self.errorExists(52702)) and \
                    not(self.getErrorNum() == 2 and self.errorExists(52200) and self.errorExists(52702))) \
                    or self.getFatalNum()>0):
                '''报错状态下红色呼吸'''
                dmx512_info.type = dmx.LightType.Errofatal.value

            elif Controller.emc:
                '''急停状态下暗红色闪烁'''
                dmx512_info.type = dmx.LightType.FlowCalculator.value
                RGBW = [230, 30, 0, 0]
                dmx512_info.color_r = RGBW[0]
                dmx512_info.color_g = RGBW[1]
                dmx512_info.color_b = RGBW[2]
                dmx512_info.color_w = RGBW[3]

            elif Move.blocked:
                '''被阻挡状态下粉紫色跑马'''
                dmx512_info.type = dmx.LightType.MutableHorseRace.value
                RGBW = [30, 0, 30, 0]
                dmx512_info.color_r = RGBW[0]
                dmx512_info.color_g = RGBW[1]
                dmx512_info.color_b = RGBW[2]
                dmx512_info.color_w = RGBW[3]

            elif (not self.is_stop):
                '''正常运动下蓝色呼吸'''
                dmx512_info.type = dmx.LightType.MutableBreath.value
                if (self.cur_w >= math.radians(1) * 3):
                    '''机身左旋'''
                    if (self.cur_x > 0.0):
                        '''机身左旋+前进'''
                        dmx512_info.turn_left_or_right=1
                    elif (self.cur_x < 0.0):
                        '''机身左旋+后退'''
                        dmx512_info.turn_left_or_right=2
                    else:
                        '''机身原地左旋'''
                        dmx512_info.turn_left_or_right=3

                elif (self.cur_w <= math.radians(-1) * 3):
                    '''机身右旋'''
                    if (self.cur_x > 0.0):
                        '''机身右旋+前进'''
                        dmx512_info.turn_left_or_right=2
                    elif (self.cur_x < 0.0):
                        '''机身右旋+后退'''
                        dmx512_info.turn_left_or_right=1
                    else:
                        '''机身原地右旋'''
                        dmx512_info.turn_left_or_right=3

                else:
                    '''无转向状态'''
                    if self.cur_x < 0.0:
                        RGBW = [255, 250, 250, 0]
                        dmx512_info.color_r = RGBW[0]
                        dmx512_info.color_g = RGBW[1]
                        dmx512_info.color_b = RGBW[2]
                        dmx512_info.color_w = RGBW[3]
                    dmx512_info.turn_left_or_right=0

            elif self.battery_exist:
                '''静止状态且battery存在'''
                maxPer = self.getBatteryMaxPercentage()
                if Battery.is_charging:
                    '''充电中为橙黄色呼吸'''
                    dmx512_info.type = dmx.LightType.Charging.value
                elif (Battery.percentage * 100 < maxPer):
                    '''电量低于20 %（可配置）为暗红色跑马灯'''
                    dmx512_info.type = dmx.LightType.MutableHorseRace.value
                    RGBW = [170, 20, 0, 0]
                    dmx512_info.color_r = RGBW[0]
                    dmx512_info.color_g = RGBW[1]
                    dmx512_info.color_b = RGBW[2]
                    dmx512_info.color_w = RGBW[3]
                else:
                    '''显示电量，从绿色至暗红色渐变'''
                    dmx512_info.type = dmx.LightType.Battery.value
                    tem = (Battery.percentage * 100.0)
                    dmx512_info.battery = int(tem)

            else:
                '''电池类型未配置且机器人静止为彩虹灯'''
                dmx512_info.type = dmx.LightType.Rainbow.value

            self.sendDmx512(dmx512_info)

if __name__ == '__main__':
    client = demo_dmx512()
    client.run()


