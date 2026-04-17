#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LED 输出模块。

用法：
  from syspy.behavs.led import led
  led.trySet("green", "breath")
"""

from .outputs import LedOutput
from . import _core


class _LazyLed(object):
    """首次调用时才初始化 RPC 连接。"""
    _instance = None

    def __getattr__(self, name):
        if self._instance is None:
            _LazyLed._instance = LedOutput(_core.get_rpc())
        return getattr(self._instance, name)

    def reset(self):
        """重置缓存实例，用于热更新场景。"""
        _LazyLed._instance = None


led = _LazyLed()
