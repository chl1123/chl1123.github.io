import colorsys
import math
import time
from abc import ABCMeta, abstractmethod
from typing import Union

from .light_type import LightType, Color
from ..utils.param_server import ParamServer


def adjust_color(rgb, brightness=1.0, saturation=1.0):
    # 将RGB值转换为0-1范围内的浮点数
    r, g, b = [v / 255.0 for v in rgb]

    # 转换到HSV颜色空间
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    # 调整饱和度和亮度
    s *= saturation
    v *= brightness

    # 确保s和v在有效范围内
    s = max(0.0, min(1.0, s))  # 明确使用浮点数
    v = max(0.0, min(1.0, v))

    # 转换回RGB颜色空间
    r, g, b = colorsys.hsv_to_rgb(h, s, v)

    # 将颜色值转换回0-255范围内的整数
    return [int(r * 255), int(g * 255), int(b * 255)]


class LightEffect(metaclass=ABCMeta):
    def __init__(self, dmx_led, rgbw=None, led_idx=None):
        self.dmx_led = dmx_led
        self.pos = 0
        self._rgbw = rgbw or dmx_led.rgbw
        self.led_idx = led_idx or list(range(1, dmx_led.light_total_num + 1))  # 控制的灯的索引
        self._brightness = None

    def set_rgbw(self, rgbw, brightness=None):
        # 判断brightness是否为数字
        if isinstance(brightness, (int, float)):
            rgb = adjust_color(rgbw[0:3], brightness=brightness)
            rgb.append(rgbw[3])
            self._rgbw = rgb
        elif isinstance(brightness, list):
            self._rgbw = rgbw
            self._brightness = brightness
        elif isinstance(self._brightness, (int, float)):
            rgb = adjust_color(rgbw[0:3], brightness=self._brightness)
            rgb.append(rgbw[3])
            self._rgbw = rgb
        else:
            self._rgbw = rgbw

    def set_brightness(self, brightness):
        if isinstance(brightness, (int, float)):
            self._brightness = brightness
        else:
            print("brightness is not a number")

    @abstractmethod
    def update(self):
        raise NotImplementedError("Subclasses must implement this method.")

    def data_packet(self, init_rgbw=None):
        if init_rgbw is None:
            init_rgbw = self._rgbw
        # 深拷贝rgbw
        rgbw = init_rgbw.copy()
        for index, led_idx_item in enumerate(self.led_idx):
            start_index = (led_idx_item - 1) * 4 + 1  # 每个灯的起始索引
            if isinstance(self._brightness, list):
                if index < len(self._brightness):
                    if self._brightness[index] is not None:
                        rgb = adjust_color(init_rgbw[0:3], brightness=self._brightness[index])
                        rgb.append(init_rgbw[3])
                        rgbw = rgb
            for channel, color in zip(self.dmx_led.rgbw_channel, rgbw):
                if start_index + channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[start_index + channel] = color


class ConstantLight(LightEffect):
    def __init__(self, dmx_led, rgbw=None, led_idx=None):
        super().__init__(dmx_led, rgbw)
        self.led_idx = led_idx or list(range(1, dmx_led.light_total_num + 1))  # 控制的灯的索引

    def update(self):
        self.data_packet()


class MutableBreath(LightEffect):
    def __init__(self, dmx_led, rgbw, period=3000):
        super().__init__(dmx_led, rgbw)
        self.breath_period = period
        self.next_period = period
        self.position_in_cycle = 0
        self.last_update_time = int(time.time() * 1000)

    def set_period(self, period):
        self.next_period = period

    def update(self):
        t_ms_now = int(time.time() * 1000)

        # 计算自上次更新以来的时间差
        delta_time = t_ms_now - self.last_update_time

        # 更新上次更新时间
        self.last_update_time = t_ms_now

        # 计算当前周期位置
        self.position_in_cycle = (self.position_in_cycle + delta_time) % self.breath_period

        # 归一化位置到 [0, 1)
        position_in_cycle = self.position_in_cycle / self.breath_period

        # 计算亮度
        sin_value = math.sin(position_in_cycle * 2 * math.pi - math.pi / 2)

        brightness = (sin_value + 1) / 2

        # 平滑过渡到新周期
        if self.breath_period != self.next_period:
            # 根据当前周期位置平滑过渡到新周期位置
            new_position_in_cycle = (self.position_in_cycle / self.breath_period) * self.next_period
            self.position_in_cycle = new_position_in_cycle
            self.breath_period = self.next_period

        # 计算 RGBW 值
        rgbw = list(self._rgbw)
        rgbw = [int(channel * brightness) for channel in rgbw]
        # 更新 DMX 数据
        self.data_packet(rgbw)


class MutableHorseRace(LightEffect):
    def __init__(self, dmx_led, rgbw, period=1000):
        super().__init__(dmx_led, rgbw)
        self.__next_case = 1
        self.start_time = int(time.time() * 1000)
        self.update_period = period  # 初始化周期为1秒

    def set_period(self, period):
        # 设置跑马灯的更新周期（毫秒）
        self.update_period = period

    def update(self):
        t_ms_now = int(time.time() * 1000)
        if t_ms_now - self.start_time >= self.update_period:
            self.start_time = t_ms_now
            self.__next_case += 1
            if self.__next_case > 2:
                self.__next_case = 1
        if self.__next_case == 1:
            for i in range(1, len(self.dmx_led.dmx_data) + 1, 8):
                if i + self.dmx_led.red_channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[i + self.dmx_led.red_channel] = self._rgbw[0]
                if i + self.dmx_led.green_channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[i + self.dmx_led.green_channel] = self._rgbw[1]
                if i + self.dmx_led.blue_channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[i + self.dmx_led.blue_channel] = self._rgbw[2]
                if i + self.dmx_led.white_channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[i + self.dmx_led.white_channel] = self._rgbw[3]
        elif self.__next_case == 2:
            for i in range(5, len(self.dmx_led.dmx_data) + 1, 8):
                if i + self.dmx_led.red_channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[i + self.dmx_led.red_channel] = self._rgbw[0]
                if i + self.dmx_led.green_channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[i + self.dmx_led.green_channel] = self._rgbw[1]
                if i + self.dmx_led.blue_channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[i + self.dmx_led.blue_channel] = self._rgbw[2]
                if i + self.dmx_led.white_channel < len(self.dmx_led.dmx_data):
                    self.dmx_led.dmx_data[i + self.dmx_led.white_channel] = self._rgbw[3]


class Flow(LightEffect):
    def __init__(self, dmx_led, rgbw, period=10):
        super().__init__(dmx_led, rgbw)
        self.__next_position = 1
        self.__flow_speed_control = int(time.time() * 1000)
        self.update_period = period  # 初始化周期为10毫秒

    def set_period(self, period):
        # 设置流水的更新周期（毫秒）
        self.update_period = period

    def update(self):
        t_ms_now = int(time.time() * 1000)  # Get current time in milliseconds
        if t_ms_now - self.__flow_speed_control >= self.update_period:
            self.__flow_speed_control = t_ms_now
            self.dmx_led.dmx_data[:] = [0x00] * len(self.dmx_led.dmx_data)
            self.__next_position += 4
            if self.__next_position >= len(self.dmx_led.dmx_data):
                self.__next_position = 1
            self.dmx_led.dmx_data[self.__next_position] = self._rgbw[0]
            self.dmx_led.dmx_data[self.__next_position + 2] = self._rgbw[1]
            if self.__next_position + 3 < len(self.dmx_led.dmx_data):
                self.dmx_led.dmx_data[self.__next_position + 3] = self._rgbw[2]
            self.dmx_led.dmx_data[self.__next_position + 1] = self._rgbw[3]


class Rainbow(LightEffect):
    def __init__(self, dmx_led):
        super().__init__(dmx_led)
        self.__increment = 0
        self.rgb_7_pool = [
            [255, 0, 0, 0], [255, 128, 0, 0], [255, 255, 0, 0],
            [0, 255, 0, 0], [0, 255, 255, 0], [0, 0, 255, 0],
            [128, 0, 255, 0]
        ]

    def set_rgbw(self, rgb_7_pool: list, __=None):
        if isinstance(rgb_7_pool, list) and len(rgb_7_pool) == 7:
            self.rgb_7_pool = rgb_7_pool

    def update(self):
        self.__increment += 2
        final_value = abs(self.__increment) * 2
        if final_value > 255:
            final_value = 255
        index_pool = 0

        for i in range(1, len(self.dmx_led.dmx_data) + 1, 4):
            if i + self.dmx_led.red_channel < len(self.dmx_led.dmx_data):
                self.dmx_led.dmx_data[i + self.dmx_led.red_channel] = int(
                    self.rgb_7_pool[index_pool][0] * final_value / 255)
            if i + self.dmx_led.green_channel < len(self.dmx_led.dmx_data):
                self.dmx_led.dmx_data[i + self.dmx_led.green_channel] = int(
                    self.rgb_7_pool[index_pool][1] * final_value / 255)
            if i + self.dmx_led.blue_channel < len(self.dmx_led.dmx_data):
                self.dmx_led.dmx_data[i + self.dmx_led.blue_channel] = int(
                    self.rgb_7_pool[index_pool][2] * final_value / 255)
            if i + self.dmx_led.white_channel < len(self.dmx_led.dmx_data):
                self.dmx_led.dmx_data[i + self.dmx_led.white_channel] = int(
                    self.rgb_7_pool[index_pool][3] * final_value / 255)
            index_pool += 1
            if index_pool >= 7:
                index_pool = 0


class BlinkLight(LightEffect):
    def __init__(self, dmx_led, rgbw, period=500):
        super().__init__(dmx_led, rgbw)
        self.__next_position = 1
        self.update_period = period  # 闪烁周期：500毫秒
        self.last_blink_time = 0
        self.__next_case = 1

    def set_period(self, period):
        # 设置闪烁的周期（毫秒）
        self.update_period = period

    def update(self):
        t_ms_now = int(time.time() * 1000)
        if t_ms_now - self.last_blink_time >= self.update_period:
            self.last_blink_time = t_ms_now
            self.__next_case += 1
            if self.__next_case > 2:
                self.__next_case = 1

        if self.__next_case == 1:
            self.data_packet()


class DmxLed(object):
    def __init__(self, param_server: ParamServer):
        self.rgbw = param_server.read("rgbwColor")
        self.brightness = 1.0
        self.rgbw_channel = param_server.read('rgbwChannel')

        self.red_channel = self.rgbw_channel[0]
        self.green_channel = self.rgbw_channel[1]
        self.blue_channel = self.rgbw_channel[2]
        self.white_channel = self.rgbw_channel[3]

        self.light_total_num = param_server.read('lightTotalNum')
        self.dmx_data = [0x00] * (1 + 4 * self.light_total_num)
        self.turn_left_or_right = 0

        self.current_effect = None

        # 灯效类实例
        self.effects = {
            LightType.ConstantLight: ConstantLight(self, self.rgbw),
            LightType.MutableBreath: MutableBreath(self, self.rgbw),
            LightType.MutableHorseRace: MutableHorseRace(self, self.rgbw),
            LightType.Flow: Flow(self, self.rgbw),
            LightType.Rainbow: Rainbow(self),
            LightType.Blink: BlinkLight(self, self.rgbw)
        }

    def set_rgbw(self, rgbw: Union[Color, list]):
        """设置RGBW，应用到全部灯效"""
        if isinstance(rgbw, Color):
            self.rgbw = rgbw.value
        else:
            self.rgbw = rgbw
        if isinstance(self.current_effect, LightEffect):
            self.current_effect.set_rgbw(self.rgbw)

    def set_brightness(self, brightness: Union[int, float]):
        """设置亮度，应用到全部灯效"""
        self.brightness = brightness
        if isinstance(self.current_effect, LightEffect):
            self.current_effect.set_brightness(brightness)

    def show_effect(
            self,
            light_effect: Union[LightType, LightEffect] = None,
            *,
            rgbw: Union[Color, list] = None,
            period=None,
            led_idx=None,
            brightness: Union[int, float, list] = None,
    ):
        # 用户自定义灯效
        if isinstance(light_effect, LightEffect):
            self.current_effect = light_effect
        # 内置灯效类型
        elif isinstance(light_effect, LightType):
            self.current_effect = self.effects[light_effect]
        else:
            raise ValueError("Unsupported effect type.")
        if rgbw is not None:
            if isinstance(rgbw, Color):
                rgbw = rgbw.value
            self.current_effect.set_rgbw(rgbw, brightness)
        elif not isinstance(self.current_effect, Rainbow):
            self.current_effect.set_rgbw(self.rgbw, self.brightness)
        if brightness is not None:
            self.set_brightness(brightness)
        if period is not None:
            self.current_effect.set_period(period)
        if led_idx is not None:
            self.current_effect.led_idx = led_idx

    def update(self):
        if self.current_effect is None:
            return False
        self.dmx_data = [0x00] * (1 + 4 * self.light_total_num)
        self.current_effect.update()
        return True
