#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""eCAL State subscriber using eCAL Python bindings.

订阅 BehavFactory 发布的 rbk.state topic (UDP transport)。
"""

import atexit
import ctypes
import json
import logging
import os
import threading
import sys

log = logging.getLogger("rbk.behavs.ecal_sub")

STATE_TOPIC = "/rbk/state"


def _preload_ecal_core():
    """Pre-load the nanobind-matching libecal_core used by the Python package.

    The Python bindings in this workspace are linked against libecal_core.so.6.
    Pre-loading rbk's shipped libecal_core.so.0 causes two eCAL runtimes to be
    resident in one Python process, which led to double-free crashes in testing.
    Keep Python on its own runtime until matching bindings are provided.
    """
    for p in sys.path:
        candidate = os.path.join(p, "ecal", "libecal_core.so.6")
        if os.path.exists(candidate):
            try:
                ctypes.CDLL(candidate, mode=ctypes.RTLD_GLOBAL)
                return candidate
            except OSError as exc:
                log.warning("preload site-packages libecal_core failed: %s", exc)
    return None


class EcalStateSubscriber(object):
    """Subscribe to rbk.state eCAL topic via Python bindings."""

    def __init__(self, unit_name):
        self._lock = threading.Lock()
        self._last_payload = None
        self._subscriber = None
        self._initialized_here = False
        self._use_nanobind = False

        self._preloaded_ecal_core_path = _preload_ecal_core()

        try:
            import ecal.nanobind_core as ecal_core
            self.ecal_core = ecal_core
            self._use_nanobind = True
        except ImportError:
            try:
                import ecal.core.core as ecal_core
                self.ecal_core = ecal_core
            except Exception as e:
                log.warning("eCAL Python bindings not found: %s", e)
                self.ecal_core = None
                return

        self._setup(unit_name)
        atexit.register(self.close)

    @property
    def available(self):
        return self._subscriber is not None

    def _setup(self, unit_name):
        try:
            if not self.ecal_core.ok():
                if self._use_nanobind:
                    cfg = self.ecal_core.Configuration()
                    cfg.registration.local.transport_type = self.ecal_core.LocalTransportType.SHM
                    self.ecal_core.initialize(cfg, unit_name)
                else:
                    self.ecal_core.initialize(unit_name)
                self._initialized_here = True

            if self._use_nanobind:
                sub_cfg = self.ecal_core.SubscriberConfiguration()
                sub_cfg.layer.shm.enable = True
                sub_cfg.layer.udp.enable = False
                sub_cfg.layer.tcp.enable = False
                self._subscriber = self.ecal_core.Subscriber(
                    STATE_TOPIC,
                    self.ecal_core.DataTypeInformation(),
                    sub_cfg,
                )
            else:
                self._subscriber = self.ecal_core.subscriber(STATE_TOPIC)

            self._subscriber.set_receive_callback(self._on_receive)
            log.info("eCAL subscriber ready on topic '%s'", STATE_TOPIC)
        except Exception as exc:
            log.warning("eCAL state subscriber setup failed: %s", exc)
            self.close()

    def _on_receive(self, *args):
        # nanobind: (TopicId, DataTypeInformation, ReceiveCallbackData) — payload in args[2].buffer
        # old core: (topic_name, msg, time) — payload is msg directly
        if self._use_nanobind:
            payload = args[2].buffer if len(args) >= 3 else None
        else:
            payload = args[1] if len(args) >= 2 else None
        with self._lock:
            self._last_payload = payload

    def get_state_dict(self):
        with self._lock:
            payload = self._last_payload

        if not payload:
            return None

        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                return data
        except Exception as exc:
            log.debug("parse eCAL state payload failed: %s", exc)
        return None

    def close(self):
        if self._subscriber:
            if hasattr(self._subscriber, 'destroy'):
                self._subscriber.destroy()
            elif hasattr(self._subscriber, 'remove_receive_callback'):
                self._subscriber.remove_receive_callback()
            self._subscriber = None

        if self._initialized_here and self.ecal_core:
            try:
                self.ecal_core.finalize()
            except Exception:
                pass
            self._initialized_here = False
