#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Output helpers for BehavFactory scripts.

所有输出是"请求"语义（trySet / tryPlay），C++ 侧最终仲裁决定是否执行。
只依赖 BehavRpc，不依赖 runtime 或 state。
"""

import json
import logging

from .rpc import BehavRpc

log = logging.getLogger("rbk.behavs.outputs")


class _OutputBase(object):
    """Base: tryXxx → BehavFactory service call, fallback setAction。"""

    def __init__(self, rpc, channel, direct_method=None, direct_arg_names=None):
        self._rpc = rpc
        self._channel = channel
        self._direct_method = direct_method
        self._direct_arg_names = tuple(direct_arg_names or ())
        self._prefer_direct = bool(direct_method)
        self._warned = False
        self._last_payload = None

    def _try_direct(self, values):
        if not self._prefer_direct or self._direct_method is None:
            return False
        try:
            self._rpc.call(self._direct_method, *values)
            return True
        except Exception as exc:
            self._prefer_direct = False
            if not self._warned:
                log.warning(
                    "BehavFactory.%s failed, fallback to setAction '%s': %s",
                    self._direct_method, self._channel, exc,
                )
                self._warned = True
            return False

    def _send(self, payload, direct_values=None):
        payload_text = json.dumps(payload, sort_keys=True)
        if payload_text == self._last_payload:
            return
        if direct_values is not None and self._try_direct(direct_values):
            self._last_payload = payload_text
            return
        self._rpc.set_action(self._channel, payload)
        self._last_payload = payload_text

    def _clear(self, direct_values=None):
        self._send({}, direct_values=direct_values)


class LedOutput(_OutputBase):
    def __init__(self, rpc):
        super().__init__(rpc, "led", "requestLed", ("color", "pattern"))

    def trySet(self, color, pattern):
        """请求设置 LED。C++ 仲裁可能拒绝（如急停态）。"""
        self._send({"color": color, "pattern": pattern}, direct_values=(color, pattern))

    def tryOff(self):
        self._clear(direct_values=("off", "steady"))


class TricolorOutput(_OutputBase):
    def __init__(self, rpc):
        super().__init__(rpc, "tricolor", "requestTricolor", ("red", "yellow", "green"))

    def trySet(self, red, yellow, green):
        """请求设置三色灯。C++ 仲裁可能拒绝。"""
        payload = {"red": bool(red), "yellow": bool(yellow), "green": bool(green)}
        self._send(payload, direct_values=(payload["red"], payload["yellow"], payload["green"]))

    def tryOff(self):
        self._clear(direct_values=(False, False, False))


class AudioOutput(_OutputBase):
    def __init__(self, rpc):
        super().__init__(rpc, "audio", "requestAudio", ("sound_id", "loop"))

    def tryPlay(self, sound_id, loop=False):
        """请求播放音频。C++ 仲裁可能拒绝。"""
        payload = {"sound_id": sound_id, "loop": bool(loop)}
        self._send(payload, direct_values=(payload["sound_id"], payload["loop"]))

    def tryStop(self):
        """请求停止音频。"""
        try:
            self._rpc.call("requestAudioStop")
            self._last_payload = "{}"
        except Exception as exc:
            log.warning("requestAudioStop failed: %s", exc)
            self._clear()


class TriggerOutput(_OutputBase):
    def __init__(self, rpc):
        super().__init__(rpc, "trigger", "requestTrigger", ("key", "value"))

    def trySet(self, key, value):
        """请求设置 trigger。C++ 仲裁可能拒绝。"""
        payload = {"key": key, "value": bool(value)}
        self._send(payload, direct_values=(payload["key"], payload["value"]))
