# -*- coding: utf-8 -*-
"""控制器状态只读用例（顶层门面 Controller）。

数值（温度、湿度、电压）因车而异，只校验类型与明显不合理的范围。
"""

from __future__ import annotations

import pytest
from syspy import Controller

from helpers import is_bool, is_float, run_getter

GETTERS = [
    ("getVoltage", is_float, "float", lambda v: v >= 0.0),
    ("getTemperature", is_float, "float", lambda v: -40.0 <= v <= 150.0),
    ("getHumidity", is_float, "float", lambda v: 0.0 <= v <= 100.0),
    ("getAdcVoltage", is_float, "float", None),
    ("getEmc", is_bool, "bool", None),
    ("getSoftEmc", is_bool, "bool", None),
    ("getDriverEmc", is_bool, "bool", None),
    ("getBrake", is_bool, "bool", None),
    ("getElectric", is_bool, "bool", None),
    ("getManualCharge", is_bool, "bool", None),
    ("getAutoCharge", is_bool, "bool", None),
    ("getIsExternalControl", is_bool, "bool", None),
    ("getIsImuCalibrating", is_bool, "bool", None),
]


@pytest.mark.parametrize("name,type_ok,type_name,range_ok", GETTERS, ids=[g[0] for g in GETTERS])
def test_controller_getter(name, type_ok, type_name, range_ok, rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "Controller.%s()" % name,
        getattr(Controller, name), type_ok, type_name, range_ok, rbk_env["simulation"],
    )
