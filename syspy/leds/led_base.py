import logging
import math
import threading
import time
from typing import Union, Optional

from syspy import Abnormal
from .dmx_led import DmxLed, LightEffect
from .dmx_serial_comm import DmxSerialComm
from .light_type import Brightness, LightType, Color
from ..utils.param_server import ParamServer

log = logging.getLogger("rbk.script")
CODE_LED_CONN_ERRO = 53142

FASTEST_PERIOD = 1000
SLOWEST_PERIOD = 3000
MAX_LINE_SPEED = 0.3
MIN_LINE_SPEED = 0
MAX_ANGULAR_SPEED = 2 / math.pi
MIN_ANGULAR_SPEED = 0


class LedBase:
    __50305_error_v = []

    def __init__(self, param_server: ParamServer):
        self.dev = param_server.read("devName")
        self.turn_pos = param_server.read("turnPos")
        self.turn_num = param_server.read("turnNum")
        self.light_total_num = param_server.read("lightTotalNum")

        self.dmx_serial = DmxSerialComm(self.dev)
        self.__led = DmxLed(param_server)

        # 创建并启动发送串口数据
        send_thread = threading.Thread(target=self.send_data_thread, daemon=True, name="LedDmxSerialComm")
        send_thread.start()

    def __del__(self):
        self.dmx_serial.close()

    def init(self):
        if self.check_config():
            self.set50305("led model: turnlight config error")
            print("led model: turnlight config error")
            return False

        self.clear50305("led model: turnlight config error")
        print("Configuration is valid.")

        if self.dmx_serial is not None:
            self.dmx_serial.close()
        print("DMXLedTTY init() self.dev:", self.dev)

        if self.dmx_serial.open():
            print("DMXLed init success")
            if Abnormal.exists(50305):
                Abnormal.clear(50305)
        else:
            print("DMXLed init failed")
            Abnormal.setDevice(50305, "Error opening serial port", "Error opening serial port",
                               "check port baudrate", "battery/*.py", "battery")
            return False
        return True

    @classmethod
    def set50305(cls, msg):
        if msg not in cls.__50305_error_v:
            cls.__50305_error_v.append(msg)
            err = ' & '.join(cls.__50305_error_v)
            Abnormal.setDevice(50305, err, "turnlight config error", "check turnlight",
                               "battery/*.py", "battery")

    @classmethod
    def clear50305(cls, msg):
        if msg in cls.__50305_error_v:
            cls.__50305_error_v.remove(msg)
        if not cls.__50305_error_v:
            if Abnormal.exists(50305):
                Abnormal.clear(50305)
        else:
            err = ' & '.join(cls.__50305_error_v)
            Abnormal.setDevice(50305, err, "turnlight config error", "check turnlight",
                               "battery/*.py", "battery")

    @staticmethod
    def is_alarm():
        """获取报警条件"""
        abnormal_num = Abnormal.getNum()
        if abnormal_num == 0:
            return False
        exists_52200, exists_52702, exists_54004, exists_54025 = Abnormal.exists([52200, 52702, 54004, 54025])
        allowed_errors = [
            exists_52200,
            exists_52702,
            exists_54004,
            exists_54004 and exists_54025,
        ]
        return abnormal_num > sum(allowed_errors)

    def check_config(self):
        config_error = False
        # 对转向灯位置及对应编号排序
        sorted_positions = sorted(zip(self.turn_pos, self.turn_num))
        sorted_pos_array, sorted_num_array = zip(*sorted_positions)
        # 总的灯的数量 < 各转向灯数量之和：配置无效
        if self.light_total_num < sum(sorted_num_array):
            config_error = True
        else:
            # 检查位置是否重叠或紧密相邻
            for i in range(len(sorted_pos_array) - 1):
                # 检查当前位置与下一个位置是否相同
                if sorted_pos_array[i] == sorted_pos_array[i + 1]:
                    config_error = True
                    break

                # 计算当前转向灯的结束位置
                current_end_pos = sorted_pos_array[i] + sorted_num_array[i] - 1
                # 下一个转向灯的起始位置
                next_start_pos = sorted_pos_array[i + 1]

                # 当前转向灯的结束位置与下一个转向灯的起始位置重叠或相邻
                if current_end_pos >= next_start_pos and sorted_num_array[i] > 0 and sorted_num_array[i + 1] > 0:
                    config_error = True
                    break
        return config_error

    def turn_to_led_idx(self, turn_left_or_right):
        led_idx = []
        for pos, num in zip(self.turn_pos, self.turn_num):
            pos_idx = [pos + i for i in range(num)]
            led_idx.extend(pos_idx)
        if turn_left_or_right == 1:
            led_idx = led_idx[:len(led_idx) // 2]
        elif turn_left_or_right == 2:
            led_idx = led_idx[len(led_idx) // 2:]
        return led_idx

    def battery_to_color(self, battery):
        battery_percent = int(battery * 100.0)
        red = int(0xFF * ((100 - battery_percent) / 100.0))
        green = int(0xFF * (battery_percent / 100.0))
        return [red, green, 0, 0]

    def line_speed_to_period(self, speed):
        speed = abs(speed)
        # 限制速度在有效范围内
        if speed < MIN_LINE_SPEED:
            speed = MIN_LINE_SPEED
        elif speed > MAX_LINE_SPEED:
            speed = MAX_LINE_SPEED
        speed_range = MAX_LINE_SPEED - MIN_LINE_SPEED
        period_range = SLOWEST_PERIOD - FASTEST_PERIOD
        # 线性映射速度到周期
        period = int(period_range * (MAX_LINE_SPEED - speed) / speed_range + FASTEST_PERIOD)
        return period

    def angular_speed_to_period(self, speed):
        speed = abs(speed)
        # 限制速度在有效范围内
        if speed < MIN_ANGULAR_SPEED:
            speed = MIN_ANGULAR_SPEED
        elif speed > MAX_ANGULAR_SPEED:
            speed = MAX_ANGULAR_SPEED
        speed_range = MAX_ANGULAR_SPEED - MIN_ANGULAR_SPEED
        period_range = SLOWEST_PERIOD - FASTEST_PERIOD
        # 线性映射速度到周期
        period = int(period_range * (MAX_ANGULAR_SPEED - speed) / speed_range + FASTEST_PERIOD)
        return period

    def speed_to_color(self, speed):
        # 确保速度在指定范围内
        speed = max(min(speed, MAX_LINE_SPEED), MIN_LINE_SPEED)

        # 将速度映射到0-1之间
        normalized_speed = (speed - MIN_LINE_SPEED) / (MAX_LINE_SPEED - MIN_LINE_SPEED)

        # 定义颜色渐变的关键点
        color_stops = [
            (0, (0, 0, 255)),  # 蓝色
            (0.5, (114, 92, 158)),  # 青紫色
            (1, (255, 0, 255)),  # 紫红色
        ]

        # 计算颜色
        for i in range(len(color_stops) - 1):
            if normalized_speed >= color_stops[i][0] and normalized_speed <= color_stops[i + 1][0]:
                # 在两个颜色之间插值
                r = int(color_stops[i][1][0] + (color_stops[i + 1][1][0] - color_stops[i][1][0]) * (
                        normalized_speed - color_stops[i][0]) / (color_stops[i + 1][0] - color_stops[i][0]))
                g = int(color_stops[i][1][1] + (color_stops[i + 1][1][1] - color_stops[i][1][1]) * (
                        normalized_speed - color_stops[i][0]) / (color_stops[i + 1][0] - color_stops[i][0]))
                b = int(color_stops[i][1][2] + (color_stops[i + 1][1][2] - color_stops[i][1][2]) * (
                        normalized_speed - color_stops[i][0]) / (color_stops[i + 1][0] - color_stops[i][0]))
                return (r, g, b)
        return color_stops[-1][1]  # 如果速度超出范围，返回最后一个颜色

    def gen_brightness_by_battery(self, battery) -> float:
        """
        根据电池电量确定亮度。

        :param battery: 电池电量
        :return: 亮度值
        """
        if battery is not None:
            if battery >= 0.6:
                brightness = Brightness.Normal.value
            elif battery >= 0.1:
                brightness = Brightness.DIM.value
            else:
                brightness = Brightness.Dark.value
            return brightness
        return Brightness.Normal.value

    def set_rgbw(self, rgbw: Union[Color, list]):
        """设置RGBW，应用到全部灯效"""
        self.__led.set_rgbw(rgbw)

    def set_effect(
            self,
            light_effect: Union[LightType, LightEffect],
            *,
            rgbw: Optional[Union[Color, list]] = None,
            period: Optional[int] = None,
            led_idx: Optional[list] = None,
            brightness: Optional[Union[int, float, list]] = None,
    ):
        """设置灯效

        Args:
            light_effect (Union[LightType, LightEffect]): 预制灯效类型LightType 或 用户自定义灯效（继承LightEffect）
            rgbw (Optional[Union[Color, list]]): RGBW颜色值
            period (Optional[int]): 适用于呼吸灯、流水灯、跑马灯、闪烁灯的周期
            led_idx (Optional[list]): 常量灯和闪烁灯的索引。默认应用到所有LED灯
            brightness (Optional[Union[int, float, list]]): 灯光亮度。int、float应用到全部，list应用到指定索引
        """
        log.debug(f"{light_effect=}, {rgbw=}, {led_idx=}")
        self.__led.show_effect(light_effect, rgbw=rgbw, period=period, led_idx=led_idx, brightness=brightness)

    def send_data_thread(self):
        while True:
            """串口数据发送线程"""
            self.__led.update()
            self.dmx_serial.send(self.__led.dmx_data)
            # 发送数据的频率可以根据需要调整
            time.sleep(0.1)  # 发送频率可以低于状态获取频率
