#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""State 模块。

用法：
  from syspy.behavs.state import state
  state.taskStatus
  state.battery.percentage
"""

import time
from .state_node import StateNode
from . import _core


class State(object):
    """每次属性访问自动拿 eCAL 最新数据。首次访问时初始化 eCAL subscriber。"""

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)
        return getattr(self._node(), key)

    def get(self, key, default=None):
        return self._node().get(key, default)

    @property
    def raw(self):
        return self._data()

    def ok(self):
        return _core.is_running()

    def sleep(self, seconds):
        deadline = time.time() + max(0.0, seconds)
        while self.ok():
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 0.1))

    def _data(self):
        data = _core.get_ecal_sub().get_state_dict()
        return data if isinstance(data, dict) else {}

    def _node(self):
        return StateNode(self._data())


state = State()
