import math
import time
import syspy.dmx512.dmx512_base as dmx
import syspy.lib.misc_utility as mu
from syspy import Battery, Controller, NavStatus, NavSpeed
from syspy import Logger,RobotParam, Abnormal,Module
from typing import List, Dict, Any
log = Logger("led")

'''
Model Params
'''
robot_param = {}
def load_robot_config_params():
    """加载机器人配置参数"""
    global robot_param
    robot_param.update(
        {
            "errorPercentage": RobotParam.getConfig("power", "lowBatteryManage.errorPercentage"),
            "automaticShutdown": RobotParam.getConfig("power", "lowBatteryManage.automaticShutdown"),
        }
    )
    
    if robot_param['automaticShutdown'] == 'ON':
        robot_param.update(
            {
                "shutdownPercentage": RobotParam.getDevice("power", "lowBatteryManage.automaticShutdown.on.shutdownPercentage"),
            }
        )
    
def _robot_config_change_callback(diff_map: Dict[str, Any]):
    """机器人配置参数变化回调"""
    global robot_param
    for key, value in diff_map.items():
        if key == "lowBatteryManage.errorPercentage":
            robot_param["errorPercentage"] = value
        elif key == "lowBatteryManage.automaticShutdown":
            robot_param["automaticShutdown"] = value
        elif key == "lowBatteryManage.automaticShutdown.on.shutdownPercentage":
            robot_param["shutdownPercentage"] = value

load_robot_config_params()
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

    @staticmethod
    def is_alarm():
        """获取报警条件"""
        abnormal_num = Abnormal.getNum()
        if abnormal_num == 0:
            return False
        exists_52200, exists_54506, exists_52201, exists_57049 = Abnormal.exists([52200, 54506, 52201, 57049])
        allowed_errors = [
            exists_52200,
            exists_54506,
            exists_52201,
            exists_57049
        ]
        return abnormal_num > sum(allowed_errors)
    
    def run(self):
        dmx512_info = self.createDmx512Message()
        mu.sleepS(20)
        while 1:
            """cur_w:旋转度, cur_x:前进距离, cur_y:平移距离"""
            self.cur_x, self.cur_y, self.cur_w = NavSpeed.getSpeeds()

            '''cur_w:旋转度, cur_x:前进距离, cur_y:平移距离'''
            percentage = Battery.getPercentage()
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

            if self.errorExists(57040):
                self.battery_exist = False

            if self.is_alarm():
                '''报错状态下红色呼吸'''
                dmx512_info.type = dmx.LightType.Errofatal.value

            elif Controller.getEmc():
                '''急停状态下暗红色闪烁'''
                dmx512_info.type = dmx.LightType.FlowCalculator.value
                RGBW = [230, 30, 0, 0]
                dmx512_info.colorRed = RGBW[0]
                dmx512_info.colorGreen = RGBW[1]
                dmx512_info.colorBlue = RGBW[2]
                dmx512_info.colorWhite = RGBW[3]

            elif NavStatus.getBlock():
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
                if Battery.getIsCharging():
                    '''充电中为橙黄色呼吸'''
                    dmx512_info.type = dmx.LightType.Charging.value
                # 低于关机 红色呼吸灯
                elif robot_param.get('automaticShutdown','OFF') == 'ON' and percentage * 100 <= robot_param.get('shutdownPercentage', -1):
                    dmx512_info.type = dmx.LightType.Errofatal.value
                #低于错误 暗红色跑马灯
                elif percentage * 100 < robot_param.get('errorPercentage',-1):
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
    Module.init()
    RobotParam.setDeviceChangeCallBack(load_robot_config_params)
    client = demo_dmx512()
    client.run()
