#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Output helpers for BehavFactory scripts.

所有输出是"请求"语义（trySet / tryPlay），C++ 侧最终仲裁决定是否执行。
只依赖 BehavRpc，不依赖 runtime 或 state。
"""

import json
import logging
from typing import List, Optional

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
    """
    tryLed(light_type, rgbw, period=1000)
    
    light_type: "MutableBreath" | "Flow" | "MutableHorseRace" |"Steady" | "Rainbow" | "Errofatal" | "Off"
    rgbw      : "Red" | "RedDark" | "PinkPurple" | "Green" | "GreenDark" |
                "Blue" | "BlueDark" | "Yellow" | "White" | "Off"
    period    : ms，默认 1000
    
    fallback setAction payload:
        {"light_type": "...", "rgbw": "...", "period": 1000}
    """

    DEFAULT_PERIOD = 1000

    TOPIC_NAME = "/rbk/behav/action/led"

    def __init__(self, rpc):
        super().__init__(
            rpc,
            "led",                # setAction channel
            "tryLed",                           # direct method
            ("light_type", "rgbw", "period", "led_idx"),   # arg names（仅文档用）
        )
        self._topic_send = None

    @staticmethod
    def _normalize_led_idx(led_idx: Optional[list]) -> List[int]:
        if not led_idx:
            return []
        out: List[int] = []
        for value in led_idx:
            try:
                idx = int(value)
            except Exception:
                continue
            if idx > 0:
                out.append(idx)
        return out

    def _ensure_topic_sender(self):
        if self._topic_send is not None:
            return self._topic_send
        try:
            import ecal.nanobind_core as ecal_core
            from ecal.msg.string.core import Publisher as StringPublisher

            if not ecal_core.ok():
                cfg = ecal_core.Configuration()
                cfg.registration.local.transport_type = ecal_core.LocalTransportType.SHM
                # Suppress optional runtime timesync module loading.
                cfg.timesync.timesync_module_rt = ""
                cfg.timesync.timesync_module_replay = ""
                ecal_core.initialize(cfg, "behavs_led_topic")

            pub_cfg = ecal_core.PublisherConfiguration()
            pub_cfg.layer.shm.enable = True
            pub_cfg.layer.udp.enable = False
            pub_cfg.layer.tcp.enable = False
            topic_pub = StringPublisher(self.TOPIC_NAME, pub_cfg)

            for name in ("send", "Send", "publish", "Publish"):
                fn = getattr(topic_pub, name, None)
                if callable(fn):
                    self._topic_send = fn
                    return self._topic_send
        except Exception as exc:
            log.warning("LED topic publisher init failed: %s", exc)
        return None

    def trySet(self, light_type, rgbw, period=None, led_idx=None):
        if period is None:
            period = self.DEFAULT_PERIOD
        payload = {"light_type": light_type, "rgbw": rgbw, "period": period}
        idx = self._normalize_led_idx(led_idx)
        if idx:
            payload["led_idx"] = idx
        self._send(payload, direct_values=(light_type, rgbw, period, idx))

    def trySetByTopic(self, light_type, rgbw, period=None, led_idx=None):
        """仅通过 topic 下发；失败时回落到 trySet（RPC/setAction）。"""
        if period is None:
            period = self.DEFAULT_PERIOD
        payload = {"light_type": light_type, "rgbw": rgbw, "period": period}
        idx = self._normalize_led_idx(led_idx)
        if idx:
            payload["led_idx"] = idx

        payload_text = json.dumps(payload, sort_keys=True)
        if payload_text == self._last_payload:
            return

        sender = self._ensure_topic_sender()
        if sender is not None:
            try:
                sender(payload_text)
                self._last_payload = payload_text
                return
            except Exception as exc:
                log.warning("LED topic publish failed, fallback RPC: %s", exc)

        self._send(payload, direct_values=(light_type, rgbw, period, idx))

    def tryOff(self):
        """关灯：light_type=Off, rgbw=Off, period=0"""
        self._send({"light_type": "Off", "rgbw": "Off", "period": 0},
                   direct_values=("Off", "Off", 0))


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
