# -*- coding: utf-8 -*-
"""距离传感器只读用例（顶层门面 Distance）。

3.6 起距离传感器改为按设备拆 channel（``/DistanceSensor/<key>``），
接口层原先没有任何 getter，本次迁移一并补上了 getDistances/getData。

现场未接入设备时读不到数据属预期（跳过），接入后这些用例会自动转为通过。
"""

from __future__ import annotations

import pytest
from syspy import Distance
from syspy.v3.protobuf.compat import IS_RBK35

from helpers import is_container, run_getter


def test_distance_get_distances_all_devices(rbk_report, rbk_env, request):
    """不传 device_key：合并全部设备；无数据返回 None。"""
    run_getter(
        rbk_report, request.node.nodeid, "Distance.getDistances()",
        Distance.getDistances, is_container, "容器", simulation=rbk_env["simulation"],
    )


def test_distance_get_data_compat(rbk_report, request):
    """getData 为兼容式读取：无数据返回空列表（不是 None）。"""
    value = Distance.getData()
    rbk_report.add_sample(request.node.nodeid, "Distance.getData() 条数 = %d" % len(value))
    assert isinstance(value, list), "getData 应返回 list，实际 %s" % type(value).__name__


@pytest.mark.skipif(IS_RBK35, reason="3.6 专属：3.5 无 channel，device_key 不参与拼路径")
def test_distance_rejects_channel_path_as_device_key():
    """device_key 传 channel 路径应被拒绝。"""
    with pytest.raises(ValueError):
        Distance.getDistances(device_key="/DistanceSensor/DistanceSensor-000")


def test_distance_unknown_device_key_returns_none():
    """合法格式但不存在的设备 key：返回 None，不抛异常。"""
    try:
        value = Distance.getDistances(device_key="DistanceSensor-999")
    except Exception as exc:  # noqa: BLE001
        pytest.fail("不存在的 device_key 不应抛异常: %s: %s" % (type(exc).__name__, exc))
    assert value is None, "未配置设备应返回 None，实际 %r" % (value,)
