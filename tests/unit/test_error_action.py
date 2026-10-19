# -*- coding: utf-8 -*-
"""错误注入动作用例（dangerous：短暂改变机器人错误状态）。

闭环在仿真已验证：setSystemError → existSystemError=True →
clearSystemError → existSystemError=False。

安全设计：
- 所有注入的错误 key 带 rbk-test- 前缀，便于辨识；
- 每个用例 finally 必清理，绝不让测试错误留在车上；
- 清理失败视为用例失败（比留下脏状态更严重）。
"""

from __future__ import annotations

import time

import pytest
from syspy import Navigation, RobotError

TEST_SYS_ERROR_KEY = "ts@rbk-test-sys-error"
TEST_TASK_ERROR_KEY = "ms@rbk-test-task-error"
TEST_ERROR_DESC = "rbk api test temporary error, safe to clear"


@pytest.mark.dangerous
def test_robot_error_set_exist_clear_cycle(rbk_report, request):
    """注入系统错误 → existSystemError 为 True → 清除 → 恢复 False。"""
    try:
        RobotError.setSystemError(TEST_SYS_ERROR_KEY, TEST_ERROR_DESC)
        # 给错误上报留一点传播时间
        deadline = time.time() + 5
        existed = False
        while time.time() < deadline:
            if RobotError.existSystemError():
                existed = True
                break
            time.sleep(0.2)
        rbk_report.add_sample(request.node.nodeid, "注入后 existSystemError = %r" % existed)
        assert existed, "注入系统错误后 existSystemError 未变 True"
    finally:
        RobotError.clearSystemError(TEST_SYS_ERROR_KEY)
        deadline = time.time() + 5
        cleared = False
        while time.time() < deadline:
            if not RobotError.existSystemError():
                cleared = True
                break
            time.sleep(0.2)
        rbk_report.add_sample(request.node.nodeid, "清除后 existSystemError 恢复 = %r" % cleared)
        assert cleared, "清除后 existSystemError 仍为 True，测试错误未清理干净"


@pytest.mark.dangerous
def test_navigation_task_error_set_clear(rbk_report, request):
    """任务错误注入/清除不抛异常，且 finally 保证清理。"""
    set_result = None
    try:
        set_result = Navigation.setTaskError(TEST_TASK_ERROR_KEY, TEST_ERROR_DESC)
        rbk_report.add_sample(request.node.nodeid, "setTaskError 返回 %r" % (set_result,))
    finally:
        clear_result = Navigation.clearTaskError(TEST_TASK_ERROR_KEY)
        rbk_report.add_sample(request.node.nodeid, "clearTaskError 返回 %r" % (clear_result,))


@pytest.mark.dangerous
def test_navigation_stop_robot_no_raise(rbk_report, request):
    """stopRobot(False)（不急停，仅下发停止指令）不抛异常。

    注意：这是写入动作，但停车是安全方向的动作；不会主动运动。
    """
    result = Navigation.stopRobot(False)
    rbk_report.add_sample(request.node.nodeid, "stopRobot(False) 返回 %r" % (result,))
