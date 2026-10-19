# -*- coding: utf-8 -*-
"""pytest 公共夹具与报告钩子。

三件事：
1. 路径修复——绕开 syspy 的 script_dir 陷阱（symlink 安装下 __file__ 解析成
   物理路径会被 param_server 拒绝）；
2. 前置检查——RBK IPC socket 是否可用；
3. 结果收集——交给 report.py 生成 Markdown，同时保留逐用例文本日志。
"""

from __future__ import annotations

import logging
import os
import sys


# --------------------------------------------------------------------------
# 1) 路径修复：必须在任何 syspy 导入之前完成
# --------------------------------------------------------------------------
SCRIPTS_DIR = "/opt/.data/rbk/resources/scripts"
_PHYSICAL_ROOT = os.path.realpath(SCRIPTS_DIR)


def _is_physical_scripts_path(path: str) -> bool:
    """判断搜索项是否直接指向 scripts 的物理路径（如 /mnt/log/...）。"""
    if not path:
        path = os.getcwd()
    absolute = os.path.abspath(path)
    return absolute == _PHYSICAL_ROOT or absolute.startswith(_PHYSICAL_ROOT + os.sep)


# pytest 会把 /opt/.data 软链解析成 /mnt/log 并把物理目录插到搜索路径前面。
# 这里先剔除物理路径，再把逻辑路径放到最前，保证 syspy 从
# /opt/.data/rbk/resources/scripts 加载。
sys.path[:] = [p for p in sys.path if not _is_physical_scripts_path(p)]
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# 尽快导入 syspy：此后即使 pytest 重新插入物理路径，模块也已被正确加载。
try:
    import syspy  # noqa: F401,E402
except Exception as _exc:  # pragma: no cover - 环境问题，交给用例如实报错
    sys.stderr.write("conftest: syspy 预加载失败: %r\n" % (_exc,))

import pytest  # noqa: E402

# 测试目录自身（report.py / helpers.py 所在），供用例文件 import；
# pytest 的 rootdir 导入模式只会把 unit/ 插入 sys.path，不会带上级目录。
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from report import Report, STATUS_ERROR, STATUS_FAIL, STATUS_PASS, STATUS_SKIP  # noqa: E402


_LOGGER = logging.getLogger("rbk.api.tests")
_REPORT: "Report" = None


# --------------------------------------------------------------------------
# 2) 报告与日志初始化
# --------------------------------------------------------------------------
def pytest_configure(config):
    global _REPORT
    _REPORT = Report()
    config._rbk_report = _REPORT

    report_dir = os.environ.get("RBK_TEST_REPORT_DIR", "test-reports")
    log_path = os.environ.get("RBK_TEST_LOG", os.path.join(report_dir, "results.log"))
    parent = os.path.dirname(os.path.abspath(log_path))
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent)
        except OSError:
            log_path = "/tmp/rbk-tests-results.log"

    _LOGGER.setLevel(logging.INFO)
    _LOGGER.handlers = []
    try:
        handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        _LOGGER.addHandler(handler)
    except OSError:
        pass
    _LOGGER.propagate = False
    _LOGGER.info("RBK 接口测试开始（只读用例）")


def pytest_sessionstart(session):
    """会话开始时做一次 RBK IPC 前置检查，结果写进日志（不阻断）。"""
    for sock in ("/tmp/python2cpp_rpc.ipc", "/tmp/python2cpp_binmsg.ipc"):
        state = "存在" if os.path.exists(sock) else "缺失"
        _LOGGER.info("RBK IPC socket %s：%s", sock, state)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    rbk_report: Report = getattr(item.config, "_rbk_report", None)
    if rbk_report is None:
        return

    rbk_report.add_duration(item.nodeid, getattr(report, "duration", 0.0))

    if report.when == "call":
        if report.passed:
            rbk_report.set_status(item.nodeid, STATUS_PASS)
        elif report.skipped:
            reason = _skip_reason(report)
            rbk_report.add_skip(item.nodeid, reason)
            rbk_report.set_status(item.nodeid, STATUS_SKIP, reason)
        else:
            rbk_report.set_status(
                item.nodeid, STATUS_FAIL, getattr(report, "longreprtext", "") or str(report.longrepr)
            )
        _log_result(item.nodeid, rbk_report)

    elif report.when == "setup" and not report.passed:
        if report.skipped:
            reason = _skip_reason(report)
            rbk_report.add_skip(item.nodeid, reason)
            rbk_report.set_status(item.nodeid, STATUS_SKIP, reason)
        else:
            rbk_report.set_status(
                item.nodeid, STATUS_ERROR, getattr(report, "longreprtext", "") or str(report.longrepr)
            )
        _log_result(item.nodeid, rbk_report)

    elif report.when == "teardown" and report.failed:
        rbk_report.set_status(
            item.nodeid, STATUS_FAIL, getattr(report, "longreprtext", "") or str(report.longrepr)
        )
        _log_result(item.nodeid, rbk_report)


def _skip_reason(report) -> str:
    try:
        return str(report.longrepr[2]) if isinstance(report.longrepr, tuple) else str(report.longrepr)
    except Exception:
        return ""


def _log_result(nodeid: str, rbk_report: Report):
    result = rbk_report.get(nodeid)
    level = logging.ERROR if result.status in (STATUS_FAIL, STATUS_ERROR) else logging.INFO
    _LOGGER.log(
        level, "[%s][%s] %s，耗时 %.3f 秒",
        result.category, result.status, nodeid, result.duration,
    )
    if result.message and result.status in (STATUS_FAIL, STATUS_ERROR):
        _LOGGER.log(level, "详细信息:\n%s", result.message)


def pytest_sessionfinish(session, exitstatus):
    rbk_report: Report = getattr(session.config, "_rbk_report", None)
    if rbk_report is None:
        return
    path = rbk_report.write()
    counts = rbk_report.counts()
    _LOGGER.info(
        "测试结束：通过 %d，失败 %d，错误 %d，跳过 %d，pytest 退出码 %d",
        counts[STATUS_PASS], counts[STATUS_FAIL], counts[STATUS_ERROR],
        counts[STATUS_SKIP], exitstatus,
    )
    session.config._rbk_report_path = path


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    path = getattr(config, "_rbk_report_path", None)
    terminalreporter.write_sep("=", "测试产物")
    if path:
        terminalreporter.write_line("Markdown 报告: %s" % os.path.abspath(path))
        terminalreporter.write_line("最近一次报告: %s" % os.path.abspath(
            os.path.join(os.path.dirname(path), "latest.md")
        ))
    log_path = os.environ.get("RBK_TEST_LOG")
    if log_path:
        terminalreporter.write_line("逐用例日志: %s" % os.path.abspath(log_path))


# --------------------------------------------------------------------------
# 3) 公共夹具
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def rbk_report():
    """给用例提供报告对象，用于记录采样值。"""
    return _REPORT


@pytest.fixture(scope="session")
def rbk_env():
    """返回当前 RBK 环境信息，供用例判断仿真/实车、版本。"""
    try:
        import syspy

        return {
            "version": syspy.RBK_FULL_VERSION,
            "simulation": bool(syspy.RBK_SIMULATION),
        }
    except Exception:
        return {"version": "unknown", "simulation": True}


def pytest_collection_modifyitems(config, items):
    """未显式启用时，自动跳过 dangerous 用例。

    run_tests.sh 第一轮只跑只读接口，但保留该机制，动作测试进来后无需改这里。
    """
    if os.environ.get("RUN_DANGEROUS") == "1":
        return
    skip_marker = pytest.mark.skip(reason="未启用（需 RUN_DANGEROUS=1）")
    for item in items:
        if "dangerous" in item.keywords:
            item.add_marker(skip_marker)
