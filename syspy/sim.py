# -*- coding: utf-8 -*-
"""
仿真环境辅助工具：
1) is_simulation()：统一判断当前是否仿真环境
2) @sim_only：默认在仿真中显式跳过并继续；可提供 on_sim 重写分支
"""

from __future__ import annotations

import functools
import os
from typing import Any, Callable, Optional, TypeVar, cast

from syspy.config import RBK_SIMULATION

F = TypeVar("F", bound=Callable[..., Any])


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on", "y", "t"):
            return True
        if text in ("0", "false", "no", "off", "n", "f"):
            return False
    return default


def is_simulation() -> bool:
    """
    是否仿真环境。

    优先读取环境变量 RBK_SIMULATION，其次读取 syspy.config.RBK_SIMULATION。
    """
    env_value = os.getenv("RBK_SIMULATION")
    if env_value is not None:
        return _to_bool(env_value, False)
    return bool(RBK_SIMULATION)


def sim_only(
    func: Optional[F] = None,
    *,
    on_sim: Optional[Callable[..., Any]] = None,
    skip_return: Any = None,
    reason: str = "",
) -> Callable[[F], F] | F:
    """
    在仿真环境下的默认行为：
    - 若提供 on_sim：执行 on_sim（建议与原函数保持同签名和类型注解）
    - 否则：显式打印 skip 日志，并返回 skip_return（默认 None）

    实机环境总是执行原函数。
    """

    def _decorate(target: F) -> F:
        @functools.wraps(target)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            if is_simulation():
                if on_sim is not None:
                    return on_sim(*args, **kwargs)
                msg = f"[sim_only] skip {target.__qualname__}"
                if reason:
                    msg += f", reason={reason}"
                print(msg)
                return skip_return
            return target(*args, **kwargs)

        setattr(_wrapped, "__sim_only__", True)
        setattr(_wrapped, "__sim_on_sim__", on_sim)
        return cast(F, _wrapped)

    if func is not None:
        return _decorate(func)
    return _decorate

