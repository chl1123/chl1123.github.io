# -*- coding: utf-8 -*-
"""电池接口只读用例（走顶层 syspy 门面 Battery）。

断言口径：
- 读不到（None）不算失败，记为跳过（前置不满足：电池无数据）；
- 数值不做具体断言，只校验类型与明显不合理的范围；
- 空 str / 空 bytes 合法；SoH=-1 表示无效，仍是合法 int。
"""

from __future__ import annotations

import pytest
from syspy import Battery

BATTERY_KEY = "Battery-000"


def _is_int(value):
    # bool 是 int 子类，这里要求严格 int
    return type(value) is int


# (getter 名, 类型校验函数, 期望类型描述, 额外范围校验)
GETTERS = [
    ("getPercentage", lambda v: isinstance(v, float), "float", lambda v: 0.0 <= v <= 1.0),
    ("getChargeCurrent", lambda v: isinstance(v, float), "float", None),
    ("getChargeVoltage", lambda v: isinstance(v, float), "float", lambda v: v >= 0.0),
    ("getIsCharging", lambda v: isinstance(v, bool), "bool", None),
    ("getTemperature", lambda v: isinstance(v, float), "float", lambda v: -40.0 <= v <= 120.0),
    ("getCycle", _is_int, "int", lambda v: v >= 0),
    ("getMaxChargeCurrent", lambda v: isinstance(v, float), "float", lambda v: v >= 0.0),
    ("getMaxChargeVoltage", lambda v: isinstance(v, float), "float", lambda v: v >= 0.0),
    ("getExtra", lambda v: isinstance(v, str), "str", None),
    ("getUserData", lambda v: isinstance(v, bytes), "bytes", None),
    ("getSoh", _is_int, "int", lambda v: v == -1 or 0 <= v <= 100),
    ("getIsManuallyConnected", lambda v: isinstance(v, bool), "bool", None),
]


@pytest.mark.parametrize(
    "name,type_ok,type_name,range_ok", GETTERS, ids=[g[0] for g in GETTERS]
)
def test_battery_getter(name, type_ok, type_name, range_ok, rbk_report, request):
    """每个 getter：类型正确、范围合理；读不到则跳过；实际值记入报告。"""
    value = getattr(Battery, name)(device_key=BATTERY_KEY)
    rbk_report.add_sample(request.node.nodeid, "%s(%s) = %r" % (name, BATTERY_KEY, value))

    if value is None:
        pytest.skip("前置不满足：电池无数据（电池脚本未启动或消息未发布）")

    assert type_ok(value), "%s 应为 %s，实际 %s (%r)" % (
        name, type_name, type(value).__name__, value,
    )
    if range_ok is not None:
        assert range_ok(value), "%s 取值不合理: %r" % (name, value)


def test_battery_device_key_does_not_raise():
    """不存在的 device_key 允许返回 None，但不得抛异常（防入参被误处理）。"""
    try:
        value = Battery.getPercentage(device_key="Battery-999")
    except Exception as exc:  # noqa: BLE001
        pytest.fail("不存在的 device_key 不应抛异常: %s: %s" % (type(exc).__name__, exc))
    assert value is None or isinstance(value, float), "实际 %r" % (value,)
