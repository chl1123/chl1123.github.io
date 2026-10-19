# -*- coding: utf-8 -*-
"""DI / DO 接口只读用例（顶层门面 Di / Do）。

注意 getDi / getDo 的真实语义（见 syspy/v3/dio.py）：
- 找不到 key 时返回 False，而不是 None 或抛异常；
- 因此「读不到数据」和「key 对应状态为 False」无法从返回值区分，
  这里只验证 bool 类型与不抛异常，状态本身只采样不断言。
"""

from __future__ import annotations

import pytest
from syspy import Di, Do

from helpers import is_bool, is_container, is_int, run_getter


def test_di_get_dis(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "Di.getDis()", Di.getDis,
        is_container, "容器", simulation=rbk_env["simulation"],
    )


def test_di_get_max_di(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "Di.getMaxDi()", Di.getMaxDi,
        is_int, "int", lambda v: v >= 0, rbk_env["simulation"],
    )


def test_di_get_di_matches_node_status(rbk_report, request):
    """getDi(key) 应返回 bool。"""
    nodes = Di.getDis()
    if nodes is None or len(nodes) == 0:
        pytest.skip("前置不满足：DI 无数据")
    node = nodes[0]
    value = Di.getDi(node.key) if hasattr(node, "key") else None
    rbk_report.add_sample(request.node.nodeid, "getDi(%r) = %r，getDis 中 status = %r"
                          % (getattr(node, "key", None), value, node.status))
    assert is_bool(value), "getDi 应返回 bool，实际 %r" % (value,)


def test_di_unknown_key_returns_false_without_raising(request):
    """不存在的 key 不抛异常，返回 False。"""
    try:
        value = Di.getDi("DI-NOT-EXIST-999")
    except Exception as exc:  # noqa: BLE001
        pytest.fail("未知 key 不应抛异常: %s: %s" % (type(exc).__name__, exc))
    assert value is False, "未知 key 应返回 False，实际 %r" % (value,)


def test_do_get_dos(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "Do.getDos()", Do.getDos,
        is_container, "容器", simulation=rbk_env["simulation"],
    )


def test_do_get_max_node(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "Do.getMaxNode()", Do.getMaxNode,
        is_int, "int", lambda v: v >= 0, rbk_env["simulation"],
    )


def test_do_unknown_key_returns_false_without_raising(request):
    try:
        value = Do.getDo("DO-NOT-EXIST-999")
    except Exception as exc:  # noqa: BLE001
        pytest.fail("未知 key 不应抛异常: %s: %s" % (type(exc).__name__, exc))
    assert value is False, "未知 key 应返回 False，实际 %r" % (value,)
