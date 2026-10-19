# -*- coding: utf-8 -*-
"""里程计接口只读用例（顶层门面 Odometer）。"""

from __future__ import annotations

import pytest
from syspy import Odometer

from helpers import is_bool, is_container, is_int, is_triple, run_getter


def test_odometer_get_cycle(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "getCycle()", Odometer.getCycle,
        is_int, "int", lambda v: v >= 0, rbk_env["simulation"],
    )


def test_odometer_get_position(rbk_report, rbk_env, request):
    """getPosition 返回 (x, y, theta) 三元组。"""
    run_getter(
        rbk_report, request.node.nodeid, "getPosition()", Odometer.getPosition,
        is_triple, "三元数值序列", simulation=rbk_env["simulation"],
    )


def test_odometer_get_speeds(rbk_report, rbk_env, request):
    """getSpeeds 返回 (vx, vy, w) 三元组。"""
    run_getter(
        rbk_report, request.node.nodeid, "getSpeeds()", Odometer.getSpeeds,
        is_triple, "三元数值序列", simulation=rbk_env["simulation"],
    )


def test_odometer_get_is_stop(rbk_report, rbk_env, request):
    run_getter(
        rbk_report, request.node.nodeid, "getIsStop()", Odometer.getIsStop,
        is_bool, "bool", simulation=rbk_env["simulation"],
    )


def test_odometer_get_motor_infos(rbk_report, rbk_env, request):
    """不传 device_key：返回全部电机信息的容器。"""
    run_getter(
        rbk_report, request.node.nodeid, "getMotorInfos()", Odometer.getMotorInfos,
        is_container, "容器", simulation=rbk_env["simulation"],
    )
