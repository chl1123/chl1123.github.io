# -*- coding: utf-8 -*-
"""定位接口只读用例（顶层门面 Loc）。"""

from __future__ import annotations

import pytest
from syspy import Loc

from helpers import is_float, is_int, run_getter


def test_loc_get_pose(rbk_report, rbk_env, request):
    """getPose 返回含 x/y/z/yaw/roll/pitch 的 dict。"""
    value = run_getter(
        rbk_report, request.node.nodeid, "getPose()", Loc.getPose,
        lambda v: isinstance(v, dict), "dict", simulation=rbk_env["simulation"],
    )
    missing = [k for k in ("x", "y", "z", "yaw", "roll", "pitch") if k not in value]
    assert not missing, "getPose 缺少字段: %s" % missing
    bad = [k for k in ("x", "y", "yaw") if not isinstance(value[k], (int, float))]
    assert not bad, "getPose 字段类型不是数值: %s" % bad


def test_loc_get_confidence(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "getConfidence()", Loc.getConfidence,
        is_float, "float", lambda v: 0.0 <= v <= 1.0, rbk_env["simulation"],
    )


def test_loc_get_loc_state(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "getLocState()", Loc.getLocState,
        is_int, "int", simulation=rbk_env["simulation"],
    )


def test_loc_get_loc_method(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "getLocMethod()", Loc.getLocMethod,
        is_int, "int", simulation=rbk_env["simulation"],
    )
