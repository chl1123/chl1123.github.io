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
            print("[ecal_sub] _setup: use_nanobind={}, ecal_core.ok()={}".format(
                self._use_nanobind, self.ecal_core.ok()))
            if not self.ecal_core.ok():
                if self._use_nanobind:
                    cfg = self.ecal_core.Configuration()
                    cfg.registration.local.transport_type = self.ecal_core.LocalTransportType.SHM
                    # Suppress optional runtime timesync module loading.
                    cfg.timesync.timesync_module_rt = ""
                    cfg.timesync.timesync_module_replay = ""
                    self.ecal_core.initialize(cfg, unit_name)
                else:
                    self.ecal_core.initialize(unit_name)
                self._initialized_here = True
                print("[ecal_sub] eCAL initialized (unit_name={})".format(unit_name))

            if self._use_nanobind:
                try:
                    from ecal.msg.string.core import Subscriber as StringSubscriber
                    sub_cfg = self.ecal_core.SubscriberConfiguration()
                    sub_cfg.layer.shm.enable = True
                    sub_cfg.layer.udp.enable = True
                    sub_cfg.layer.tcp.enable = False
                    self._subscriber = StringSubscriber(STATE_TOPIC, sub_cfg)
                    print("[ecal_sub] nanobind StringSubscriber created on '{}'".format(STATE_TOPIC))
                except Exception as e:
                    print("[ecal_sub] StringSubscriber failed: {}, falling back to raw Subscriber".format(e))
                    sub_cfg = self.ecal_core.SubscriberConfiguration()
                    sub_cfg.layer.shm.enable = True
                    sub_cfg.layer.udp.enable = True
                    sub_cfg.layer.tcp.enable = False
                    self._subscriber = self.ecal_core.Subscriber(
                        STATE_TOPIC,
                        self.ecal_core.DataTypeInformation(),
                        sub_cfg,
                    )
                    self._use_nanobind = "raw"
                    print("[ecal_sub] raw nanobind Subscriber created on '{}'".format(STATE_TOPIC))
            else:
                self._subscriber = self.ecal_core.subscriber(STATE_TOPIC)
                print("[ecal_sub] core subscriber created on '{}'".format(STATE_TOPIC))

            self._subscriber.set_receive_callback(self._on_receive)
            print("[ecal_sub] callback registered, subscriber.available={}".format(self.available))
            sys.stdout.flush()
        except Exception as exc:
            print("[ecal_sub] setup FAILED: {}".format(exc))
            import traceback; traceback.print_exc()
            self.close()

    def _on_receive(self, *args):
        # nanobind StringSubscriber: (topic_id, callback_data) — callback_data.message is str
        # nanobind raw Subscriber: (TopicId, DataTypeInformation, ReceiveCallbackData) — buffer
        # old core: (topic_name, msg, time) — payload is msg (bytes)
        try:
            if self._use_nanobind == "raw":
                payload = args[2].buffer if len(args) >= 3 else None
            elif self._use_nanobind:
                payload = args[1].message.encode("utf-8") if len(args) >= 2 else None
            else:
                payload = args[1] if len(args) >= 2 else None
        except Exception as e:
            print("[ecal_sub] _on_receive ERROR: {}, args_len={}, arg_types={}".format(
                e, len(args), [type(a).__name__ for a in args]))
            payload = None

        if payload and not hasattr(self, '_debug_first_recv'):
            self._debug_first_recv = True
            print("[ecal_sub] FIRST MESSAGE RECEIVED! payload_len={}, preview={}".format(
                len(payload), payload[:200] if payload else None))
            sys.stdout.flush()

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
