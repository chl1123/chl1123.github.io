# -*- coding: utf-8 -*-
"""激光只读用例（顶层门面 Laser / Laser3D）。

Laser.getData() 不带参数时按设备枚举 /Laser2D/<key> 并聚合成 {"laser": [...]}，
没有可用设备时回落到聚合 channel，仍读不到则返回空 dict —— 这里把「空 dict」
视为无数据而不是失败。
"""

from __future__ import annotations

import pytest
from syspy import Laser, Laser3D
from syspy.v3.protobuf.compat import IS_RBK35

from helpers import is_container, run_getter


def test_laser_get_data_aggregated(rbk_report, rbk_env, request):
    """getData() 返回含 laser 列表的 dict；每个元素是一路激光的字典。"""
    def read():
        data = Laser.getData()
        return data if data else None  # 空 dict 视为无数据

    value = run_getter(
        rbk_report, request.node.nodeid, "Laser.getData()", read,
        lambda v: isinstance(v, dict), "dict", simulation=rbk_env["simulation"],
    )
    assert "laser" in value, "getData 缺少 laser 字段，实际 keys=%s" % list(value.keys())
    assert isinstance(value["laser"], list), "laser 应为 list，实际 %s" % type(value["laser"]).__name__
    for index, item in enumerate(value["laser"]):
        assert isinstance(item, dict), "laser[%d] 应为 dict，实际 %s" % (index, type(item).__name__)


def test_laser_get_data_with_unknown_device_key_does_not_hang(request):
    """未知 device_key 允许返回空 dict，但不得抛出与参数无关的异常。"""
    try:
        Laser.getData(device_key="Laser-NOT-EXIST-999")
    except ValueError:
        # 参数校验类异常是接口约定的一部分
        pass
    except Exception as exc:  # noqa: BLE001
        pytest.fail("未知 device_key 抛了非预期异常 %s: %s" % (type(exc).__name__, exc))


@pytest.mark.skipif(IS_RBK35, reason="3.6 专属：3.5 无 channel，device_key 不参与拼路径")
def test_laser_get_data_rejects_channel_path_as_device_key():
    """device_key 传 channel 路径应被拒绝（接口约定：必须是设备 key）。"""
    with pytest.raises(ValueError):
        Laser.getData(device_key="/Laser2D/Laser-000")


@pytest.mark.skipif(IS_RBK35, reason="3.6 专属：3.5 无 channel")
def test_laser_get_data_rejects_channel_and_device_key_together():
    """channel 与 device_key 互斥。"""
    with pytest.raises(ValueError):
        Laser.getData(channel="/Laser2D/Laser-000", device_key="Laser-000")


def test_laser3d_get_lasers3d(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "Laser3D.getLasers3d()", Laser3D.getLasers3d,
        is_container, "容器", simulation=rbk_env["simulation"],
    )


def test_laser3d_rejects_channel_path_as_device_key():
    with pytest.raises(ValueError):
        Laser3D.getLasers3d(device_key="/Laser3D/Laser-002")
