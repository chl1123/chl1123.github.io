import math
import sys
import syspy.dmx512.dmx512_base as dmx
import syspy.lib.udp_debug as ud
# _syslog = ud.syslogDebug("dmx512")
import syspy.lib.misc_utility as mu

class demo_dmx512(dmx.dmx512Base):

    def __init__(self):
        '''初始化基类,必须做'''
        super(demo_dmx512, self).__init__()
        self.__debug_out = ud.udpDebug()
        sys.stdout = self.__debug_out
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
        dmx_battery = self.createBatteryMessage()
        mu.sleep_s(2)
        while 1:
            mu.sleep_s(1)
            '''从其他插件获取所需相关数据信息'''
            movestatus_info = self.recMoveStatus()
            robotspeed_info = self.recRobotSpeed()
            '''cur_w:旋转度, cur_x:前进距离, cur_y:平移距离'''
            self.cur_w = robotspeed_info.rotate
            self.cur_x = robotspeed_info.x
            self.cur_y = robotspeed_info.y
            '''实时获取电池信息并转换为dmx类型 '''
            dmx_battery = self.recBattery()
            tem = (dmx_battery.percetage * 100.0)
            dmx512_info.battery = int(tem)
            '''非停止状态计数'''
            if self.getChassisStop() == True :
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

            '''判断是否从模型文件读取到'''
            self.battery_exist = self.modelDeviceEnable(self.str1)
            if self.warningExists(54001):
                self.battery_exist = False

            if (((self.getErrorNum()>0) and \
                    not(self.getErrorNum() == 1 and self.errorExists(52200)) and \
                    not(self.getErrorNum() == 1 and self.errorExists(52702)) and \
                    not(self.getErrorNum() == 2 and self.errorExists(52200) and self.errorExists(52702))) \
                    or self.getFatalNum()>0):
                '''报错状态下红色呼吸'''
                dmx512_info.type = dmx.LightType.Errofatal.value

            elif self.getEMCState() == True:
                '''急停状态下暗红色闪烁'''
                dmx512_info.type = dmx.LightType.FlowCalculator.value
                RGBW = [230, 30, 0, 0]
                dmx512_info.color_r = RGBW[0]
                dmx512_info.color_g = RGBW[1]
                dmx512_info.color_b = RGBW[2]
                dmx512_info.color_w = RGBW[3]

            elif movestatus_info.blocked:
                '''被阻挡状态下粉紫色跑马'''
                dmx512_info.type = dmx.LightType.MutableHorseRace.value
                RGBW = [30, 0, 30, 0]
                dmx512_info.color_r = RGBW[0]
                dmx512_info.color_g = RGBW[1]
                dmx512_info.color_b = RGBW[2]
                dmx512_info.color_w = RGBW[3]

            elif (not self.is_stop):
                '''not ym_dxm512'''
                if (not self.ym_dxm512_enable):
                    '''正常运动下蓝色呼吸'''
                    dmx512_info.type = dmx.LightType.MutableBreath.value
                    if (self.cur_w >= math.radians(1) * 3):
                        '''机身左旋'''
                        if (self.cur_x > 0.0):
                            '''机身左旋+前进'''
                            dmx512_info.turn_left_or_right=1
                        elif (self.cur_x < 0.0):
                            '''机身左旋+后退'''
                            dmx512_info.turn_left_or_right=1
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
                            dmx512_info.turn_left_or_right=2
                        else:
                            '''机身原地右旋'''
                            dmx512_info.turn_left_or_right=3

                    else:
                        # '''静止'''
                        if self.cur_x < 0.0:
                            RGBW = [255, 250, 250, 0]
                            dmx512_info.color_r = RGBW[0]
                            dmx512_info.color_g = RGBW[1]
                            dmx512_info.color_b = RGBW[2]
                            dmx512_info.color_w = RGBW[3]
                        dmx512_info.turn_left_or_right=0

                else:
                    '''ym_dxm512'''
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
                '''静止状态且battery存在'''
                maxPer = self.getBatteryMaxPercentage()
                if dmx_battery.is_charging:
                    '''充电中为橙黄色呼吸'''
                    dmx512_info.type = dmx.LightType.Charging.value
                elif (dmx_battery.percetage * 100 < maxPer):
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
                    tem = (dmx_battery.percetage * 100.0)
                    dmx512_info.battery = int(tem)
            else:
                '''电池类型未配置且机器人静止为彩虹灯'''
                dmx512_info.type = dmx.LightType.Rainbow.value

            self.sendDmx512(dmx512_info)

if __name__ == '__main__':
    client = demo_dmx512()
    client.run()


