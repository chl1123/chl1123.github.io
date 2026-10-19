# -*- coding: utf-8 -*-
"""导航状态 / 导航速度只读用例（顶层门面 NavStatus / NavSpeed）。

getTurn 是纯函数（不依赖 RBK），做确定性断言；其余 getter 读消息，按统一口径采样。
getChassisStop 走 DSPChassis RPC：仿真无该插件，未注册时跳过，实车必须可用。
"""

from __future__ import annotations

import math

import pytest
from syspy import NavSpeed, NavStatus

from helpers import is_bool, is_container, is_int, is_str, is_triple, run_getter

# 与 syspy/v3/navigation.py 中 getTurn 的阈值一致：角速度 >= 3 度/秒 才算转向
TURN_THRESHOLD = math.radians(1) * 3


# ---------------------------------------------------------------------------
# getTurn：纯逻辑，期望值来自接口注释（1/2 为带平移的转向，3 为原地自转，0 为直行）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "v_x,v_w,expected",
    [
        (0.5, 0.0, 0),                       # 直行
        (-0.5, 0.0, 0),                      # 直退
        (0.0, 0.0, 0),                       # 静止
        (0.5, TURN_THRESHOLD, 1),            # 左旋 + 前进（阈值边界，含等号）
        (-0.5, TURN_THRESHOLD, 2),           # 左旋 + 后退
        (0.0, TURN_THRESHOLD, 3),            # 原地左旋
        (0.5, -TURN_THRESHOLD, 2),           # 右旋 + 前进
        (-0.5, -TURN_THRESHOLD, 1),          # 右旋 + 后退
        (0.0, -TURN_THRESHOLD, 3),           # 原地右旋
        (0.5, TURN_THRESHOLD * 0.99, 0),     # 略低于阈值：不算转向
        (0.5, -TURN_THRESHOLD * 0.99, 0),
    ],
)
def test_nav_status_get_turn(v_x, v_w, expected):
    assert NavStatus.getTurn(v_x, v_w) == expected, (
        "getTurn(v_x=%r, v_w=%r) 期望 %d" % (v_x, v_w, expected)
    )


# ---------------------------------------------------------------------------
# NavStatus：MoveStatus channel 读取
# ---------------------------------------------------------------------------
def test_nav_status_get_block(rbk_report, rbk_env, request):
    run_getter(rbk_report, request.node.nodeid, "NavStatus.getBlock()",
               NavStatus.getBlock, is_bool, "bool", simulation=rbk_env["simulation"])


def test_nav_status_get_block_device(rbk_report, rbk_env, request):
    # 空串合法（未被阻挡时没有阻挡设备）
    run_getter(rbk_report, request.node.nodeid, "NavStatus.getBlockDevice()",
               NavStatus.getBlockDevice, is_str, "str", simulation=rbk_env["simulation"])


def test_nav_status_get_task_status(rbk_report, rbk_env, request):
    run_getter(rbk_report, request.node.nodeid, "NavStatus.getTaskStatus()",
               NavStatus.getTaskStatus, is_int, "int", simulation=rbk_env["simulation"])


def test_nav_status_get_running_status(rbk_report, rbk_env, request):
    run_getter(rbk_report, request.node.nodeid, "NavStatus.getRunningStatus()",
               NavStatus.getRunningStatus, is_int, "int", simulation=rbk_env["simulation"])


def test_nav_status_get_current_station(rbk_report, rbk_env, request):
    # 空串合法（不在任何站点附近）
    run_getter(rbk_report, request.node.nodeid, "NavStatus.getCurrentStation()",
               NavStatus.getCurrentStation, is_str, "str", simulation=rbk_env["simulation"])


def test_nav_status_get_chassis_stop(rbk_report, rbk_env, request):
    """走 DSPChassis RPC，不是消息：仿真未加载该插件时跳过，实车必须返回 bool。"""
    run_getter(rbk_report, request.node.nodeid, "NavStatus.getChassisStop()",
               NavStatus.getChassisStop, is_bool, "bool", simulation=rbk_env["simulation"])


# ---------------------------------------------------------------------------
# NavSpeed：NavSpeed channel 读取
# ---------------------------------------------------------------------------
def test_nav_speed_get_speeds(rbk_report, rbk_env, request):
    run_getter(rbk_report, request.node.nodeid, "NavSpeed.getSpeeds()",
               NavSpeed.getSpeeds, is_triple, "三元数值序列", simulation=rbk_env["simulation"])


def test_nav_speed_get_motor_cmd(rbk_report, rbk_env, request):
    run_getter(rbk_report, request.node.nodeid, "NavSpeed.getMotorCmd()",
               NavSpeed.getMotorCmd, is_container, "容器", simulation=rbk_env["simulation"])
