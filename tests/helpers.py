# -*- coding: utf-8 -*-
"""测试公共助手。

断言口径（全项目统一，避免误报）：
- 不 assert 具体数值：电量/里程/温度/位置因车而异，只记录采样；
- 空 str / 空 bytes 合法（如 getExtra()==''）；
- -1 等语义值合法（如 SoH=-1 表示无效）；
- 读不到（None）不算失败，记为「前置不满足」跳过；
- 仿真环境没有 DSPChassis 插件，RPC 报「方法未注册」属预期，仿真下跳过，
  实车上则必须算失败（否则会掩盖真实缺陷）。
"""

from __future__ import annotations

import collections.abc as abc
from typing import Any, Callable, Optional

import pytest


def is_int(value: Any) -> bool:
    """严格 int（bool 是 int 子类，需排除）。"""
    return type(value) is int


def is_float(value: Any) -> bool:
    return isinstance(value, float)


def is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def is_str(value: Any) -> bool:
    return isinstance(value, str)


def is_bytes(value: Any) -> bool:
    return isinstance(value, bytes)


def is_container(value: Any) -> bool:
    """protobuf repeated / list / tuple：序列且有长度，但不是 str/bytes/dict。

    不能用 hasattr(value, "__iter__") 判断：cpp 版 protobuf 的
    RepeatedCompositeContainer 没有 __iter__ 属性（走 __getitem__ 迭代协议），
    但它在 collections.abc 里是 Sequence，所以用 abc 判断。
    """
    if isinstance(value, (str, bytes, dict)):
        return False
    return isinstance(value, abc.Sequence) and isinstance(value, abc.Sized)


def is_triple(value: Any) -> bool:
    """长度为 3 的数值序列，如 (x, y, theta) / (vx, vy, w)。"""
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        return False
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)


def _is_unregistered_rpc(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "-32601" in text or "haven't registered" in text or "method not found" in text


def run_getter(
    report,
    nodeid: str,
    label: str,
    fn: Callable[[], Any],
    type_ok: Callable[[Any], bool],
    type_name: str,
    range_ok: Optional[Callable[[Any], bool]] = None,
    simulation: bool = False,
) -> Any:
    """调用一个 getter 并按统一口径判定。

    - 记录采样值到报告；
    - 抛异常：仿真下遇到「RPC 方法未注册」跳过，其余一律失败；
    - 返回 None：跳过（前置不满足）；
    - 否则校验类型与（可选的）范围。
    """
    try:
        value = fn()
    except Exception as exc:  # noqa: BLE001
        report.add_sample(nodeid, "%s -> 抛异常 %s: %s" % (label, type(exc).__name__, str(exc)[:120]))
        if simulation and _is_unregistered_rpc(exc):
            pytest.skip("前置不满足：仿真环境未加载对应插件（RPC 方法未注册）")
        pytest.fail("%s 抛异常 %s: %s" % (label, type(exc).__name__, exc))

    report.add_sample(nodeid, "%s = %s" % (label, _short(value)))

    if value is None:
        pytest.skip("前置不满足：%s 无数据（消息未发布或尚未就绪）" % label)

    assert type_ok(value), "%s 应为 %s，实际 %s (%s)" % (
        label, type_name, type(value).__name__, _short(value),
    )
    if range_ok is not None:
        assert range_ok(value), "%s 取值不合理: %s" % (label, _short(value))
    return value


def _short(value: Any, limit: int = 160) -> str:
    try:
        if is_container(value) and not isinstance(value, (tuple, list)):
            return "%s(len=%d)" % (type(value).__name__, len(value))
        text = repr(value)
    except Exception:  # noqa: BLE001
        text = "<unrepr %s>" % type(value).__name__
    return text if len(text) <= limit else text[: limit - 3] + "..."
