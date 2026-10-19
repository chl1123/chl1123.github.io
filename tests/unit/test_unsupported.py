# -*- coding: utf-8 -*-
"""现场未配置的接口：只验证「调用不抛异常」。

这些接口已完成 channel 迁移，但当前现场未接入对应设备（仿真/实车均无数据）：
- Magnetic：已迁到 ``/Magnetic/<key>``，未配置磁传感器；
- Rfid / CodeScanner：已迁到 ``/RFID/<key>`` / ``/CodeScanner/<key>``，设备未配置；
- Bin：地图上没有库位，没有数据（registry 无对应 channel，仍走 topic）。

所以读不到数据是预期，不算失败；有数据时再校验容器类型。
设备接入后这些用例会自动由「跳过」变成「通过」，届时应补充字段级断言。
"""

from __future__ import annotations

import pytest
from syspy import Bin, CodeScanner, Magnetic, Rfid

from helpers import is_container, run_getter

CASES = [
    ("Magnetic.getMagnetics", Magnetic, "getMagnetics", "磁传感器未配置（channel /Magnetic/<key>）"),
    ("Rfid.getRfids", Rfid, "getRfids", "RFID 设备未配置（channel /RFID/<key>）"),
    ("CodeScanner.getCodeScanners", CodeScanner, "getCodeScanners", "扫码器未配置（channel /CodeScanner/<key>）"),
    ("Bin.getBins", Bin, "getBins", "地图上没有库位（registry 无 channel，仍走 topic）"),
]


@pytest.mark.parametrize("label,obj,method,why", CASES, ids=[c[0] for c in CASES])
def test_unsupported_getter_does_not_raise(label, obj, method, why, rbk_report, rbk_env, request):
    """调用不抛异常；无数据时按「未迁移/未配置」跳过，有数据则必须是容器。"""
    getter = getattr(obj, method)

    def read():
        value = getter()
        # 空容器等同无数据
        if value is not None and is_container(value) and len(value) == 0:
            return None
        return value

    try:
        run_getter(
            rbk_report, request.node.nodeid, label + "()", read,
            is_container, "容器", simulation=rbk_env["simulation"],
        )
    except pytest.skip.Exception as skipped:
        # 把通用的「前置不满足」改写成更具体的「未配置」，报告里才能归到正确分类
        pytest.skip("未迁移/未配置：%s（%s）" % (why, skipped))
