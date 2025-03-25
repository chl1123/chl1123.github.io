import signal
import time
from typing import Optional

from syspy import Battery, Controller, NavStatus, NavSpeed
from syspy.leds.led_base import LedBase
from syspy.leds.light_type import LightType, Color
from syspy.lib.logger import Logger
from syspy.utils.param_server import ParamServer

log = Logger(log_prefix="led", console=True).get_logger()


def signal_handler(signal, frame):
    exit(0)


class LedChassis(LedBase):
    def __init__(self):
        param_server = ParamServer(__file__)
        self.dev = param_server.loadParam('devName', type="str", default="/dev/ttyS8", comment="串行端口对应的设备名")
        self.rgbw = param_server.loadParam('rgbwColor', type="list", default=Color.BlueCobalt.value,
                                           comment="RGBW十进制代码")
        self.rgbw_channel = param_server.loadParam('rgbwChannel', type="list", default=[0, 2, 3, 1],
                                                   comment="RGBW通道")
        self.turn_pos = param_server.loadParam('turnPos', type="list", default=[4, 3, 1, 2],
                                               comment="左前/左后/右前/右后方向的灯的位置")
        self.turn_num = param_server.loadParam('turnNum', type="list", default=[1, 1, 1, 1],
                                               comment="左前/左后/右前/右后方向的灯的灯条数")
        self.light_total_num = param_server.loadParam('lightTotalNum', type="int", default=4,
                                                      comment="灯条总数")
        self.is_show_charging = param_server.loadParam('showCharging', type="bool", default=True,
                                                       comment="是否显示充电状态")
        self.is_show_battery = param_server.loadParam('showBattery', type="bool", default=True,
                                                      comment="是否显示电池状态")
        self.is_back_breath = param_server.loadParam('isBackBreath', type="bool", default=False,
                                                     comment="是否后退时亮白色呼吸灯")
        self.dmx_test_flag = param_server.loadParam('DmxTestFlag', type="bool", default=False,
                                                    comment="DMX测试标志")

        super().__init__(param_server)

    def run(self):
        if self.init():
            while True:
                self.set_light_type()
                time.sleep(1)

    def set_light_type(self):
        percentage = Battery.get_percentage()
        if int(percentage * 100.0) == 0:
            battery_exist = False
        else:
            battery_exist = True
        self.handle_light_effects(percentage, battery_exist)
        if self.dmx_test_flag:
            self.set_effect(LightType.MutableBreath)

    def handle_light_effects(self, dmx_battery: Optional[float], battery_exist: bool):
        """
        根据当前状态处理灯光效果。

        :param dmx_battery: 电池电量
        :param battery_exist: 是否存在电池
        """

        # 报警状态下红色呼吸
        if self.is_alarm():
            self.set_effect(
                LightType.MutableBreath, rgbw=Color.Red, period=1000
            )
        # 急停状态下暗红色流水
        elif Controller.get_emc():
            self.set_effect(
                LightType.Flow, rgbw=Color.RedDark, period=10
            )
        # 被阻挡状态下粉紫色跑马
        elif NavStatus.get_block():
            self.set_effect(
                LightType.MutableHorseRace, rgbw=Color.PinkPurple, period=1000
            )
        # 机器移动时的灯光效果
        elif not NavStatus.getChassisStop():
            self.handle_movement_effect()
        # 电池相关的灯光效果
        elif battery_exist:
            self.handle_battery_effects(dmx_battery)
        # 其他情况
        else:
            self.set_effect(LightType.Rainbow)
            log.warning("Effect set to Rainbow.")

    def handle_movement_effect(self) -> None:
        """
        处理机器移动时的灯光效果。
        """
        v_x, _, v_w = NavSpeed.get_speeds()
        turn = NavStatus.get_turn(v_x, v_w)
        if turn == 0:
            if self.is_back_breath and v_x < 0:
                self.set_effect(LightType.MutableBreath, rgbw=Color.White, period=1000)
            self.set_effect(LightType.MutableBreath, period=1000)
        else:
            led_idx = self.turn_to_led_idx(turn)
            self.set_effect(LightType.Blink, rgbw=Color.Yellow, led_idx=led_idx)

    def handle_battery_effects(self, dmx_battery: Optional[float]) -> None:
        """
        处理电池相关的灯光效果。

        :param dmx_battery: 电池电量
        """
        # 充电中为呼吸灯，颜色根据电池电量变化
        if self.is_show_charging and Battery.get_is_charging():
            rgbw = self.battery_to_color(dmx_battery)
            self.set_effect(
                LightType.MutableBreath, rgbw=rgbw
            )
        # 电量过低为暗红色跑马灯
        elif dmx_battery * 100 < 10:
            self.set_effect(
                LightType.MutableHorseRace, rgbw=Color.RedDark
            )
        # 常亮灯，颜色根据电池电量变化
        elif self.is_show_battery:
            rgbw = self.battery_to_color(dmx_battery)
            self.set_effect(
                LightType.ConstantLight, rgbw=rgbw
            )
        # 蓝色常亮
        else:
            self.set_effect(LightType.ConstantLight)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    tape_light = LedChassis()
    tape_light.run()
