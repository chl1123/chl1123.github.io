#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LED 灯带控制接口。"""

from typing import Optional

from syspy import RBK_VERSION
from syspy.core.rbk_rpc import RBKVersionError


class LedInterface:
    """LED 灯带控制接口类。

    灯带样式参数 ``light_type`` 与颜色参数 ``rgbw`` 均支持字符串枚举值，
    例如 ``light_type`` 取 ``"ConstantLight"``、``"MutableBreath"``、
    ``"Rainbow"``、``"Blink"``、``"Off"``；``rgbw`` 取 ``"Red"``、
    ``"Green"``、``"Blue"``、``"Yellow"``、``"White"``、``"Black"`` 等。
    """

    def trySet(self, light_type, rgbw, period: Optional[int] = None, led_idx: Optional[list] = None):
        """设置灯带样式（优先走 BehavFactory 直连通道）。

        Args:
            light_type: 灯带样式枚举值或名称。
            rgbw: 颜色枚举值或名称。
            period (Optional[int]): 闪烁/流动周期，单位 ms；缺省为 ``1000``。
            led_idx (Optional[list]): 需要点亮的灯珠序号列表（从 1 开始，最大 64）；
                缺省或空表示全部灯珠。

        Returns:
            (None): 无返回值。
        """
        raise RBKVersionError()

    def trySetByTopic(self, light_type, rgbw, period: Optional[int] = None, led_idx: Optional[list] = None):
        """设置灯带样式（优先走 topic 广播通道）。

        Args:
            light_type: 灯带样式枚举值或名称。
            rgbw: 颜色枚举值或名称。
            period (Optional[int]): 闪烁/流动周期，单位 ms；缺省为 ``1000``。
            led_idx (Optional[list]): 需要点亮的灯珠序号列表（从 1 开始，最大 64）；
                缺省或空表示全部灯珠。

        Returns:
            (None): 无返回值。
        """
        raise RBKVersionError()

    def tryOff(self):
        """关闭灯带（等效于 ``trySet("Off", "Black", 0)``）。

        Returns:
            (None): 无返回值。
        """
        raise RBKVersionError()


from syspy.v3.led import LedOutput, LegacyDmxOutput

if RBK_VERSION == 3:
    from syspy.v3.led import LedV3

    Led: LedInterface = LedV3()
elif RBK_VERSION == 4:
    from syspy.v4.led import LedV4

    Led: LedInterface = LedV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

__all__ = ["Led", "LedInterface", "LedOutput", "LegacyDmxOutput"]
