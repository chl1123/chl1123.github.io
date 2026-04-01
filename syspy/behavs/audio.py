#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""音频输出模块。

用法：
  from syspy.behavs.audio import audio
  audio.tryPlay("arrive.wav")
"""

from .outputs import AudioOutput
from . import _core


class _LazyAudio(object):
    _instance = None

    def __getattr__(self, name):
        if self._instance is None:
            _LazyAudio._instance = AudioOutput(_core.get_rpc())
        return getattr(self._instance, name)


audio = _LazyAudio()
