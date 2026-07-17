#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LED strip control helpers."""

import json
import logging
import os
from typing import List, Optional

from syspy.config import RBK_VERSION
from syspy.core.rbk_rpc import RBKVersionError, Service, call_service, default_plugin
from syspy.behavs.ecal_rpc import get_ecal_rpc

log = logging.getLogger("rbk.led")


class _LegacyDmxLightType(object):
    ConstantLight = 0x04
    MutableBreath = 0x03
    Charging = 0x05
    MutableHorseRace = 0x06
    FlowCalculator = 0x07
    Rainbow = 0x08
    Blink = 0x0A


_RGBW_TABLE = {
    "Red": (255, 0, 0, 0),
    "RedDark": (170, 20, 0, 0),
    "PinkPurple": (30, 0, 30, 0),
    "Green": (0, 255, 0, 0),
    "Blue": (0, 0, 255, 0),
    "BlueCobalt": (0, 80, 164, 0),
    "Yellow": (255, 180, 0, 0),
    "ChargeYellow": (255, 120, 0, 0),
    "White": (255, 250, 250, 0),
    "Black": (0, 0, 0, 0),
}

_LEGACY_LIGHT_TYPE_TABLE = {
    "ConstantLight": _LegacyDmxLightType.ConstantLight,
    "MutableBreath": _LegacyDmxLightType.MutableBreath,
    "MutableHorseRace": _LegacyDmxLightType.MutableHorseRace,
    "Flow": _LegacyDmxLightType.FlowCalculator,
    "Rainbow": _LegacyDmxLightType.Rainbow,
    "Blink": _LegacyDmxLightType.Blink,
    "Off": _LegacyDmxLightType.ConstantLight,
}


def _enum_value(value):
    return getattr(value, "value", value)


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


def _led_idx_to_mask(led_idx: Optional[list]) -> int:
    mask = 0
    for idx in _normalize_led_idx(led_idx):
        if 1 <= idx <= 64:
            mask |= 1 << (idx - 1)
    return mask


def _sim_dmx512_ports():
    env_port = os.getenv("DMX512_SIM_PORT", "").strip()
    ports = []
    if env_port:
        ports.append(env_port)
    ports.extend(["/dev/RS485_0", "/tmp/ttyS8"])
    out = []
    for port in ports:
        if port and port not in out:
            out.append(port)
    return out


def _send_sim_dmx512_payload(payload: bytes) -> bool:
    for port in _sim_dmx512_ports():
        try:
            fd = os.open(port, os.O_WRONLY | os.O_NONBLOCK)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            return True
        except Exception:
            continue
    return False


@default_plugin("DSPChassis")
class _DmxService(Service):
    """Internal compatibility path for legacy DMX512 message pass-through."""

    @classmethod
    @call_service()
    def sendX86DmxInfo(cls, dmx512_info: str) -> int:
        raise RBKVersionError()

    @classmethod
    @call_service()
    def sendArmDmxInfo(cls, dmx512_info: str) -> int:
        raise RBKVersionError()


class LedOutput(object):
    """LED strip request helper backed by BehavFactory RPC/topic."""

    DEFAULT_PERIOD = 1000

    def __init__(self, ecal_rpc=None):
        self._ecal_rpc = ecal_rpc or get_ecal_rpc()
        self._prefer_direct = True
        self._direct_warned = False
        self._last_payload = None

    @staticmethod
    def _normalize_led_idx(led_idx: Optional[list]) -> List[int]:
        return _normalize_led_idx(led_idx)

    def _try_direct(self, light_type, rgbw, period, led_idx):
        if not self._prefer_direct:
            return False
        try:
            result = self._ecal_rpc.call("tryLed", light_type, rgbw, period, led_idx)
            return result is not None
        except Exception as exc:
            self._prefer_direct = False
            if not self._direct_warned:
                log.warning("BehavFactory.tryLed failed, fallback to setAction: %s", exc)
                self._direct_warned = True
            return False

    def _send_payload(self, payload, direct_values=None, topic_first=False):
        payload_text = json.dumps(payload, sort_keys=True)
        if payload_text == self._last_payload:
            return

        if topic_first and self._ecal_rpc.publish_led(payload_text):
            self._last_payload = payload_text
            return

        if direct_values is not None and self._try_direct(*direct_values):
            self._last_payload = payload_text
            return

        result = self._ecal_rpc.set_action("led", payload)
        if result is not None:
            self._last_payload = payload_text

    def trySet(self, light_type, rgbw, period=None, led_idx=None):
        if period is None:
            period = self.DEFAULT_PERIOD
        idx = self._normalize_led_idx(led_idx)
        payload = {"light_type": light_type, "rgbw": rgbw, "period": period}
        if idx:
            payload["led_idx"] = idx
        self._send_payload(payload, direct_values=(light_type, rgbw, period, idx))

    def trySetByTopic(self, light_type, rgbw, period=None, led_idx=None):
        if period is None:
            period = self.DEFAULT_PERIOD
        idx = self._normalize_led_idx(led_idx)
        payload = {"light_type": light_type, "rgbw": rgbw, "period": period}
        if idx:
            payload["led_idx"] = idx
        self._send_payload(
            payload,
            direct_values=(light_type, rgbw, period, idx),
            topic_first=True,
        )

    def tryOff(self):
        self._send_payload(
            {"light_type": "Off", "rgbw": "Black", "period": 0},
            direct_values=("Off", "Black", 0, []),
        )


class _LazyLed(object):
    """Initialize BehavFactory RPC only when the LED strip API is first used."""

    _instance = None

    def __getattr__(self, name):
        if self._instance is None:
            _LazyLed._instance = LedOutput()
        return getattr(self._instance, name)

    def reset(self):
        _LazyLed._instance = None


if RBK_VERSION not in (3, 4):
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

Led = _LazyLed()


class LegacyDmxOutput(object):
    """SRC2000 legacy DMX512 adapter.

    The public input is normalized to light_type/rgbw/period/led_idx.
    """

    def __init__(self, dmx=None):
        if dmx is None:
            from syspy.dmx512.dmx512_base import dmx512Base

            dmx = dmx512Base()
        self._dmx = dmx

    def send(self, light_type, rgbw, period=1000, led_idx=None) -> None:
        light_type_name = str(_enum_value(light_type))
        rgbw_name = str(_enum_value(rgbw))

        msg = self._dmx.createDmx512Message()
        msg.type = _LEGACY_LIGHT_TYPE_TABLE.get(
            light_type_name,
            _LegacyDmxLightType.ConstantLight,
        )
        if light_type_name == "MutableBreath" and rgbw_name == "ChargeYellow":
            msg.type = _LegacyDmxLightType.Charging

        msg.period = int(period)
        msg.ledIdxMask = _led_idx_to_mask(led_idx)

        red, green, blue, white = _RGBW_TABLE.get(rgbw_name, (0, 0, 0, 0))
        msg.colorRed = int(red)
        msg.colorGreen = int(green)
        msg.colorBlue = int(blue)
        msg.colorWhite = int(white)
        self._dmx.sendDmx512(msg)


def _send_x86_dmx_info(dmx512_info: str) -> int:
    return _DmxService.sendX86DmxInfo(dmx512_info)


def _send_arm_dmx_info(dmx512_info: str) -> int:
    return _DmxService.sendArmDmxInfo(dmx512_info)
