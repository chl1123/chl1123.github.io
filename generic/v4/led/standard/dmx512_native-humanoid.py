import signal
import time
from typing import Optional

from syspy import Battery, Controller, NavStatus, NavSpeed
from syspy import Logger
from syspy import ParamServer
from syspy.leds.led_base import LedBase
from syspy.leds.light_type import LightType, Color

log = Logger("led_native")


def signal_handler(signal, frame):
    exit(0)


class ConfigParam:
    ## 基本参数
    devName =  "/dev/ttyS4"
    rgbwColor = Color.BlueCobalt.value 

    rgbwChannel = [0, 2, 3, 1]
    lightTotalNum = 4
    dmx_test_flag = False
    
    ## 以下参数用于转向灯或其他状态显示配置
    turnPos = [4, 3, 1, 2]   # 前左、前右、后左、后右转向灯位置
    turnNum = [0, 0, 0, 0]   # 前左、前右、后左、后右转向灯数量
    is_show_charging = True   # 是否显示充电状态
    is_show_battery = True    # 是否显示电池状态
    is_back_breath = False    # 是否后退时亮白色呼吸灯
    #log.warning("light_total_num=" + str(light_total_num) + " turn_pos=" + str(turn_pos) + " turn_num=" + str(turn_num))


class LedChassis(LedBase):
    def __init__(self):
        self.robot_status = None
        self.pre_robot_status = None
        super().__init__(ConfigParam)

    def run(self):
        if self.init():
            while True:
                self.set_light_type()
                time.sleep(0.1)

    def set_light_type(self):
        percentage = Battery.getPercentage()
        if percentage is None:
            percentage = 0.0
        if int(percentage * 100.0) == 0:
            battery_exist = False
        else:
            battery_exist = True
        
        if ConfigParam.dmx_test_flag:
            self.set_effect(LightType.MutableBreath, rgbw=Color.Red, period=3200)
        else:
            self.handle_light_effects(percentage, battery_exist)

    def handle_light_effects(self, dmx_battery: Optional[float], battery_exist: bool):
        # Args:
        #     light_effect (Union[LightType, LightEffect]): 预制灯效类型LightType 或 用户自定义灯效（继承LightEffect）
        #     rgbw (Optional[Union[Color, list]]): RGBW颜色值
        #     period (Optional[int]): 适用于呼吸灯、流水灯、跑马灯、闪烁灯的周期
        #     led_idx (Optional[list]): 灯索引，适用UintLed
        # 支持的格式：
        #     - 3
        #     - [1,3,5]
        #     - slice(1,5)
        #     - "1:5"
        #     - "1:10:2"
        #     brightness (Optional[Union[int, float, list]]): 灯光亮度。int、float应用到全部，list应用到指定索引
        
        # Simple light effect handling
        self.robot_status = "Normal"
        # self.set_effect(LightType.ConstantLight, rgbw=ConfigParam.rgbwColor)
        # log.info("Effect set to ConstantLight with rgbw=" + str(ConfigParam.rgbwColor))

        self.set_effect(LightType.Uint, rgbw=Color.Red, led_idx=slice(1,3))
        self.set_effect(LightType.Uint, rgbw=Color.BlueCobalt, led_idx=3)
        self.set_effect(LightType.Uint, rgbw=Color.Yellow, led_idx="4:5")
        log.info("Effect set to Uint with various colors on different LEDs.")
        
        
        
        
    ##     Advanced light effect handling (commented for future use)    
    #     """
    #     根据当前状态处理灯光效果。

    #     :param dmx_battery: 电池电量
    #     :param battery_exist: 是否存在电池
    #     """

    #     # 报警状态下红色呼吸
    #     if self.is_alarm():
    #         self.robot_status = "Alarm"
    #         self.set_effect(
    #             LightType.MutableBreath, rgbw=Color.Red, period=3200
    #         )
    #     # 急停状态下暗红色流水
    #     elif Controller.getEmc():
    #         self.robot_status = "EStop"
    #         self.set_effect(
    #             LightType.Flow, rgbw=Color.RedDark, period=10
    #         )
    #     # 被阻挡状态下粉紫色跑马
    #     elif NavStatus.getBlock():
    #         self.robot_status = "Blocked"
    #         self.set_effect(
    #             LightType.MutableHorseRace, rgbw=Color.PinkPurple, period=3200
    #         )
    #     # 机器移动时的灯光效果
    #     elif not NavStatus.getChassisStop():
    #         self.robot_status = "Moving"
    #         self.handle_movement_effect()
    #     # 电池相关的灯光效果
    #     elif battery_exist:
    #         self.handle_battery_effects(dmx_battery)
    #     # 其他情况
    #     else:
    #         self.set_effect(LightType.Rainbow)
    #         log.warning("Effect set to Rainbow.")

    #     # 仅在状态变化时打印
    #     if self.robot_status != self.pre_robot_status:
    #         log.info("robot_status=" + self.robot_status)
    #         self.pre_robot_status = self.robot_status

    # def handle_movement_effect(self) -> None:
    #     """
    #     处理机器移动时的灯光效果。
    #     """
    #     v_x, _, v_w = NavSpeed.getSpeeds()
    #     turn = NavStatus.getTurn(v_x, v_w)
    #     if turn == 0:
    #         self.robot_status = "MovingRotation"
    #         if ConfigParam.is_back_breath and v_x < 0:
    #             self.set_effect(LightType.MutableBreath, rgbw=Color.White, period=3200)
    #         else:
    #             self.set_effect(LightType.MutableBreath, period=3200)
    #     else:
    #         self.robot_status = "MovingTurn"
    #         led_idx = self.turn_to_led_idx(turn)
    #         self.set_effect(LightType.Blink, rgbw=Color.Yellow, led_idx=led_idx)

    # def handle_battery_effects(self, dmx_battery: Optional[float]) -> None:
    #     """
    #     处理电池相关的灯光效果。

    #     :param dmx_battery: 电池电量
    #     """
    #     # 充电中为呼吸灯，颜色根据电池电量变化
    #     if ConfigParam.is_show_charging and Battery.get_is_charging():
    #         self.robot_status = "Charging"
    #         rgbw = self.battery_to_color(dmx_battery)
    #         self.set_effect(
    #             LightType.MutableBreath, rgbw=rgbw, period=3200
    #         )
    #     # 电量过低为暗红色跑马灯
    #     elif dmx_battery * 100 < 10:
    #         self.robot_status = "LowBattery"
    #         self.set_effect(
    #             LightType.MutableHorseRace, rgbw=Color.RedDark,period=2000
    #         )
    #     # 常亮灯，颜色根据电池电量变化
    #     elif ConfigParam.is_show_battery:
    #         self.robot_status = "Battery"
    #         rgbw = self.battery_to_color(dmx_battery)
    #         self.set_effect(
    #             LightType.ConstantLight, rgbw=rgbw
    #         )
    #     # 蓝色常亮
    #     else:
    #         self.robot_status = "Normal"
    #         self.set_effect(LightType.ConstantLight)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    tape_light = LedChassis()
    tape_light.run()

    


    