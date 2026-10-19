# -*- coding: utf-8 -*-
"""Markdown 测试报告生成（纯标准库，无额外依赖）。

设计取舍：不引入 allure / pytest-html。
- 终端输出交给 pytest 自带（-v 已经够读）；
- 落盘用 Markdown：人能直接看、能贴群/贴 PR、能进 git 当留档；
- 额外记录「采样值」——每台车读数只打印不断言，出问题时这份数据比 PASS 有用。
"""

from __future__ import annotations

import os
import platform
import time
from typing import Dict, List, Optional

# 用例所在文件名 -> 接口中文名。用于报告分组与统计。
CATEGORY_BY_FILE = {
    "test_battery.py": "电池",
    "test_dio.py": "DI/DO",
    "test_loc.py": "定位",
    "test_odometer.py": "里程计",
    "test_laser.py": "激光",
    "test_sound.py": "声音",
    "test_sound_action.py": "声音",
    "test_error_action.py": "错误注入",
    "test_map.py": "地图",
    "test_navigation.py": "导航",
    "test_controller.py": "控制器",
    "test_distance.py": "距离传感器",
    "test_unsupported.py": "未迁移/未配置",
}

# 用例总数少，直接固定顺序，报告更稳定。
CATEGORY_ORDER = list(CATEGORY_BY_FILE.values())

STATUS_PASS = "通过"
STATUS_FAIL = "失败"
STATUS_SKIP = "跳过"
STATUS_ERROR = "错误"

# 跳过原因分类：区分「预期跳过」和「环境不满足」，否则一堆 skip 看不出正常异常。
SKIP_KIND_NOT_MIGRATED = "未迁移/未配置"
SKIP_KIND_PRECONDITION = "前置不满足"
SKIP_KIND_DISABLED = "未启用"
SKIP_KIND_OTHER = "其它"


def category_of(nodeid: str) -> str:
    """从 nodeid 推断接口中文名。"""
    for filename, category in CATEGORY_BY_FILE.items():
        if filename in nodeid:
            return category
    return "其它"


def classify_skip(reason: str) -> str:
    """把跳过原因归类，便于一眼看出是否正常。"""
    text = (reason or "").lower()
    if any(key in text for key in ("dangerous", "run_dangerous", "未启用", "disabled")):
        return SKIP_KIND_DISABLED
    if any(key in text for key in ("未迁移", "未配置", "not migrated", "not configured", "unsupported")):
        return SKIP_KIND_NOT_MIGRATED
    if any(key in text for key in ("需要", "requires", "无地图", "前置", "not ready", "precondition")):
        return SKIP_KIND_PRECONDITION
    return SKIP_KIND_OTHER


class Result:
    """单个用例的结果。"""

    def __init__(self, nodeid: str) -> None:
        self.nodeid = nodeid
        self.category = category_of(nodeid)
        self.status = "运行中"
        self.duration = 0.0
        self.message = ""
        self.samples: List[str] = []
        self.skips: List[str] = []


class Report:
    """收集用例结果并生成 Markdown。"""

    def __init__(self) -> None:
        self._results: Dict[str, Result] = {}
        self._start = time.time()
        self._start_wall = time.strftime("%Y-%m-%d %H:%M:%S %z")

    # ---------------- 收集 ----------------

    def get(self, nodeid: str) -> Result:
        return self._results.setdefault(nodeid, Result(nodeid))

    def add_sample(self, nodeid: str, text: str) -> None:
        """记录一条采样值（实际读数），报告里单独成块。"""
        result = self.get(nodeid)
        if text and text not in result.samples:
            result.samples.append(text)

    def add_skip(self, nodeid: str, reason: str) -> None:
        result = self.get(nodeid)
        if reason:
            result.skips.append(reason)

    def set_status(self, nodeid: str, status: str, message: str = "") -> None:
        result = self.get(nodeid)
        result.status = status
        r = message or ""
        result.message = r

    def add_duration(self, nodeid: str, seconds: float) -> None:
        self.get(nodeid).duration += max(0.0, seconds)

    # ---------------- 汇总 ----------------

    @property
    def results(self) -> List[Result]:
        order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
        return sorted(
            self._results.values(),
            key=lambda r: (order.get(r.category, len(order)), r.nodeid),
        )

    def counts(self) -> Dict[str, int]:
        out = {STATUS_PASS: 0, STATUS_FAIL: 0, STATUS_SKIP: 0, STATUS_ERROR: 0}
        for result in self._results.values():
            if result.status in out:
                out[result.status] += 1
        return out

    def _counts_by_category(self) -> Dict[str, Dict[str, int]]:
        out: Dict[str, Dict[str, int]] = {}
        for result in self._results.values():
            bucket = out.setdefault(
                result.category,
                {STATUS_PASS: 0, STATUS_FAIL: 0, STATUS_SKIP: 0, STATUS_ERROR: 0},
            )
            if result.status in bucket:
                bucket[result.status] += 1
        return out

    # ---------------- 渲染 ----------------

    def render(self) -> str:
        counts = self.counts()
        total = sum(counts.values())
        elapsed = time.time() - self._start

        lines: List[str] = []
        lines.append("# RBK 接口测试报告")
        lines.append("")
        lines.append("- 时间：%s" % self._start_wall)
        lines.append("- 主机：%s (%s)" % (_hostname(), _primary_ip()))
        lines.append("- 环境：%s" % _rbk_env())
        lines.append("- 耗时：%.1f 秒" % elapsed)
        lines.append(
            "- 结果：**通过 %d / 失败 %d / 错误 %d / 跳过 %d**（共 %d）"
            % (
                counts[STATUS_PASS], counts[STATUS_FAIL], counts[STATUS_ERROR],
                counts[STATUS_SKIP], total,
            )
        )
        lines.append("")

        # ---- 按接口 ----
        lines.append("## 按接口")
        lines.append("")
        lines.append("| 接口 | 通过 | 失败 | 错误 | 跳过 | 状态 |")
        lines.append("|---|---:|---:|---:|---:|---|")
        by_category = self._counts_by_category()
        for category in CATEGORY_ORDER:
            bucket = by_category.get(category)
            if not bucket:
                continue
            total_cat = sum(bucket.values())
            if bucket[STATUS_FAIL] or bucket[STATUS_ERROR]:
                mark = "❌"
            elif bucket[STATUS_PASS] == 0 and bucket[STATUS_SKIP] == total_cat:
                mark = "⏭️"
            else:
                mark = "✅"
            lines.append(
                "| %s | %d | %d | %d | %d | %s |"
                % (
                    category, bucket[STATUS_PASS], bucket[STATUS_FAIL],
                    bucket[STATUS_ERROR], bucket[STATUS_SKIP], mark,
                )
            )
        lines.append("")

        # ---- 失败/错误详情 ----
        failures = [r for r in self.results if r.status in (STATUS_FAIL, STATUS_ERROR)]
        lines.append("## 失败详情")
        lines.append("")
        if not failures:
            lines.append("（无）")
        else:
            for result in failures:
                lines.append("### %s" % result.nodeid)
                lines.append("")
                lines.append("- 状态：%s" % result.status)
                if result.message:
                    lines.append("- 信息：")
                    lines.append("")
                    lines.append("```")
                    lines.append(result.message.strip()[:4000])
                    lines.append("```")
                lines.append("")
        lines.append("")

        # ---- 跳过详情（分类）----
        lines.append("## 跳过详情")
        lines.append("")
        skipped = [r for r in self.results if r.status == STATUS_SKIP]
        if not skipped:
            lines.append("（无）")
        else:
            lines.append("| 分类 | 用例 | 原因 |")
            lines.append("|---|---|---|")
            for result in skipped:
                reason = (result.skips[-1] if result.skips else result.message) or ""
                reason = " ".join(reason.split())
                lines.append(
                    "| %s | %s | %s |"
                    % (classify_skip(reason), result.nodeid, reason[:160])
                )
        lines.append("")

        # ---- 采样值 ----
        sampled = [r for r in self.results if r.samples]
        lines.append("## 采样值")
        lines.append("")
        lines.append("实际读数，只记录不判定（不同车/不同版本数值本就不同）。")
        lines.append("")
        if not sampled:
            lines.append("（无）")
        else:
            for result in sampled:
                lines.append("### %s" % result.nodeid)
                lines.append("")
                for sample in result.samples:
                    lines.append("- %s" % sample)
                lines.append("")
        lines.append("")

        return "\n".join(lines)

    def write(self) -> str:
        """写入 <report_dir>/rbk-<env>-<时间>.md 与 latest.md，返回主文件路径。"""
        report_dir = os.environ.get("RBK_TEST_REPORT_DIR", "test-reports")
        try:
            os.makedirs(report_dir, exist_ok=True)
        except OSError:
            report_dir = "/tmp/rbk-test-reports"
            os.makedirs(report_dir, exist_ok=True)

        content = self.render()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        version = _rbk_version_slug()
        path = os.path.join(report_dir, "rbk-%s-%s.md" % (version, stamp))
        latest = os.path.join(report_dir, "latest.md")

        for target in (path, latest):
            try:
                with open(target, "w", encoding="utf-8") as stream:
                    stream.write(content)
            except OSError:
                pass
        return path


def _hostname() -> str:
    try:
        return platform.node() or "unknown"
    except Exception:
        return "unknown"


def _primary_ip() -> str:
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        finally:
            sock.close()
    except Exception:
        return "n/a"


def _rbk_env() -> str:
    try:
        import syspy

        mode = "仿真" if syspy.RBK_SIMULATION else "实车"
        return "RBK %s（%s），Python %s" % (
            syspy.RBK_FULL_VERSION, mode, platform.python_version(),
        )
    except Exception as exc:
        return "syspy 导入失败：%s" % type(exc).__name__


def _rbk_version_slug() -> str:
    try:
        import syspy

        return str(syspy.RBK_FULL_VERSION)
    except Exception:
        return "unknown"
