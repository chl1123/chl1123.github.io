#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""共享单例：eCAL subscriber + RPC client。

所有 behavs 子模块从这里拿依赖，避免重复初始化。
"""

import atexit
import os
import signal
import sys

_ecal_sub = None
_rpc = None
_running = True
_ecal_initialized = False


def _get_unit_name():
    return "behavs_{}".format(
        os.path.splitext(os.path.basename(sys.argv[0]))[0] or "behavs"
    )


def _ensure_ecal():
    """确保 eCAL 只初始化一次。"""
    global _ecal_initialized
    if _ecal_initialized:
        return
    try:
        import ecal.nanobind_core as ecal_core
        if not ecal_core.ok():
            cfg = ecal_core.Configuration()
            cfg.registration.local.transport_type = ecal_core.LocalTransportType.SHM
            ecal_core.initialize(cfg, _get_unit_name())
        _ecal_initialized = True
    except Exception:
        pass


def get_ecal_sub():
    global _ecal_sub
    if _ecal_sub is None:
        _ensure_ecal()
        from .ecal_sub import EcalStateSubscriber
        _ecal_sub = EcalStateSubscriber(_get_unit_name())
        atexit.register(_ecal_sub.close)
    return _ecal_sub


def get_rpc():
    global _rpc
    if _rpc is None:
        _ensure_ecal()
        from .rpc import BehavRpc
        _rpc = BehavRpc()
    return _rpc


def is_running():
    return _running


def stop():
    global _running
    _running = False
    if _ecal_sub is not None:
        _ecal_sub.close()


def _handle_signal(_signum, _frame):
    stop()


# 注册信号处理
for _sig_name in ("SIGINT", "SIGTERM"):
    _sig = getattr(signal, _sig_name, None)
    if _sig:
        try:
            signal.signal(_sig, _handle_signal)
        except Exception:
            pass
