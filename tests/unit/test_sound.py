# -*- coding: utf-8 -*-
"""声音状态只读用例（顶层门面 Sound）。

只测 getter；播放、停止等写接口放到 dangerous 用例。
"""

from __future__ import annotations

import pytest
from syspy import Sound

from helpers import is_bool, is_int, is_str, run_getter

# (getter 名, 类型校验, 类型名, 范围校验)
GETTERS = [
    ("getStatus", is_int, "int", None),
    ("getSoundName", is_str, "str", None),   # 空串合法（未播放时无音频名）
    ("getLoop", is_bool, "bool", None),
    ("getCount", is_int, "int", lambda v: v >= 0),
]


@pytest.mark.parametrize("name,type_ok,type_name,range_ok", GETTERS, ids=[g[0] for g in GETTERS])
def test_sound_getter(name, type_ok, type_name, range_ok, rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "Sound.%s()" % name,
        getattr(Sound, name), type_ok, type_name, range_ok, rbk_env["simulation"],
    )
