#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""三色灯输出模块。

用法：
  from syspy.behavs.tricolor import tricolor
  tricolor.trySet(False, False, True)
"""

from .outputs import TricolorOutput
from . import _core


class _LazyTricolor(object):
    _instance = None

    def __getattr__(self, name):
        if self._instance is None:
            _LazyTricolor._instance = TricolorOutput(_core.get_rpc())
        return getattr(self._instance, name)


tricolor = _LazyTricolor()
