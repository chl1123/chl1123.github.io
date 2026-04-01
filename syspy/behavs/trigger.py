#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Trigger 输出模块。

用法：
  from syspy.behavs.trigger import trigger
  trigger.trySet("slow_light", True)
"""

from .outputs import TriggerOutput
from . import _core


class _LazyTrigger(object):
    _instance = None

    def __getattr__(self, name):
        if self._instance is None:
            _LazyTrigger._instance = TriggerOutput(_core.get_rpc())
        return getattr(self._instance, name)


trigger = _LazyTrigger()
