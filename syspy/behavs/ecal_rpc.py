#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BehavFactory eCAL RPC/topic client."""

import atexit
import json
import logging
import os
import signal
import sys
import time

log = logging.getLogger("rbk.behavs.ecal_rpc")

CONNECT_RETRY_MAX = 10
CONNECT_RETRY_INTERVAL_SEC = 0.1


class EcalRpc(object):
    """Owns eCAL lifecycle and BehavFactory service/topic communication."""

    SERVICE_NAME = "BehavFactory"
    LED_TOPIC_NAME = "/rbk/behav/action/led"
    LORA_RX_TOPIC_NAME = "/rbk/behav/lora/rx"

    def __init__(self):
        self._ecal = None
        self._ecal_initialized = False
        self._ecal_initialized_here = False
        self._client = None
        self._topic_send = None
        self._lora_rx_subscribers = []
        self._running = True

    @staticmethod
    def _unit_name():
        return "behavs_{}".format(
            os.path.splitext(os.path.basename(sys.argv[0]))[0] or "behavs"
        )

    def ensure_ecal(self):
        if self._ecal_initialized:
            return True
        try:
            import ecal.nanobind_core as ecal_core

            self._ecal = ecal_core
            if not ecal_core.ok():
                cfg = ecal_core.Configuration()
                cfg.registration.local.transport_type = ecal_core.LocalTransportType.SHM
                cfg.timesync.timesync_module_rt = ""
                cfg.timesync.timesync_module_replay = ""
                ecal_core.initialize(cfg, self._unit_name())
                self._ecal_initialized_here = True
            self._ecal_initialized = True
            return True
        except Exception as exc:
            log.warning("eCAL init failed: %s", exc)
            return False

    def _ensure_client(self):
        if self._client is not None:
            return True
        if not self.ensure_ecal():
            return False
        try:
            self._client = self._ecal.ServiceClient(self.SERVICE_NAME)
            return True
        except Exception as exc:
            log.warning("BehavFactory client init failed: %s", exc)
            self._client = None
            return False

    def is_connected(self):
        if not self._ensure_client():
            return False
        try:
            return bool(self._client.is_connected())
        except Exception:
            return False

    def _wait_until_connected(
        self,
        retry_max=CONNECT_RETRY_MAX,
        retry_interval_sec=CONNECT_RETRY_INTERVAL_SEC,
    ):
        attempts = max(1, int(retry_max))
        sleep_sec = max(0.0, float(retry_interval_sec))
        for attempt in range(1, attempts + 1):
            if self.is_connected():
                return True
            if attempt < attempts and sleep_sec > 0.0:
                time.sleep(sleep_sec)
        return False

    def call(self, method, *args):
        if not self._wait_until_connected():
            return None
        try:
            request = json.dumps(args).encode("utf-8")
            responses = self._client.call_with_response(method, request, 1000)
            if responses:
                return json.loads(responses[0].response) if responses[0].response else None
        except Exception as exc:
            log.warning("RPC call failed: %s(%s): %s", method, args, exc)
        return None

    def set_action(self, channel, payload):
        action = json.dumps(payload, sort_keys=True)
        return self.call("setAction", channel, action)

    def _ensure_led_topic_sender(self):
        if self._topic_send is not None:
            return self._topic_send
        if not self.ensure_ecal():
            return None
        try:
            from ecal.msg.string.core import Publisher as StringPublisher

            pub_cfg = self._ecal.PublisherConfiguration()
            pub_cfg.layer.shm.enable = True
            pub_cfg.layer.udp.enable = False
            pub_cfg.layer.tcp.enable = False
            topic_pub = StringPublisher(self.LED_TOPIC_NAME, pub_cfg)

            for name in ("send", "Send", "publish", "Publish"):
                fn = getattr(topic_pub, name, None)
                if callable(fn):
                    self._topic_send = fn
                    return self._topic_send
        except Exception as exc:
            log.warning("LED topic publisher init failed: %s", exc)
        return None

    def publish_led(self, payload_text):
        sender = self._ensure_led_topic_sender()
        if sender is None:
            return False
        try:
            sender(payload_text)
            return True
        except Exception as exc:
            log.warning("LED topic publish failed: %s", exc)
            return False

    @staticmethod
    def _decode_string_topic_payload(*args):
        message = args[1] if len(args) >= 2 else (args[0] if args else "")
        text = getattr(message, "message", message)
        try:
            payload = json.loads(text)
        except (TypeError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None

    def subscribe_lora_rx(self, callback):
        """Subscribe to the shared unsolicited LoRa RX stream.

        The returned handle must be passed to ``unsubscribe_lora_rx``.  The
        subscriber is retained by this object so callback lifetime is tied to
        the eCAL client, not to a temporary local variable.
        """
        if not callable(callback):
            raise TypeError("callback must be callable")
        if not self.ensure_ecal():
            return None
        try:
            from ecal.msg.string.core import Subscriber as StringSubscriber

            sub_cfg = self._ecal.SubscriberConfiguration()
            sub_cfg.layer.shm.enable = True
            sub_cfg.layer.udp.enable = False
            sub_cfg.layer.tcp.enable = False
            subscriber = StringSubscriber(self.LORA_RX_TOPIC_NAME, sub_cfg)

            def on_message(*args):
                payload = self._decode_string_topic_payload(*args)
                if payload is None:
                    return
                try:
                    callback(payload)
                except Exception:
                    log.exception("LoRa RX topic callback failed")

            subscriber.set_receive_callback(on_message)
            self._lora_rx_subscribers.append(subscriber)
            return subscriber
        except Exception as exc:
            log.warning("LoRa RX topic subscriber init failed: %s", exc)
            return None

    def unsubscribe_lora_rx(self, handle):
        if handle is None:
            return
        try:
            handle.remove_receive_callback()
        except Exception:
            pass
        try:
            self._lora_rx_subscribers.remove(handle)
        except ValueError:
            pass

    def lora_rx_publisher_count(self, discovery_timeout=3.0):
        """等待 eCAL 发现完成后，返回 LoRa RX topic 的发布者数量。"""
        if not self.ensure_ecal():
            return None
        try:
            from ecal.msg.string.core import Subscriber as StringSubscriber

            sub_cfg = self._ecal.SubscriberConfiguration()
            sub_cfg.layer.shm.enable = True
            sub_cfg.layer.udp.enable = False
            sub_cfg.layer.tcp.enable = False
            subscriber = StringSubscriber(self.LORA_RX_TOPIC_NAME, sub_cfg)
            try:
                deadline = time.monotonic() + max(0.0, discovery_timeout)
                while True:
                    count = int(subscriber.get_publisher_count())
                    if count or time.monotonic() >= deadline:
                        return count
                    time.sleep(max(0.0, min(0.1, deadline - time.monotonic())))
            finally:
                subscriber.remove_receive_callback()
        except Exception as exc:
            log.warning("LoRa RX topic publisher query failed: %s", exc)
            return None

    def is_running(self):
        return self._running

    def close(self):
        self._running = False
        self._client = None
        self._topic_send = None
        for subscriber in list(self._lora_rx_subscribers):
            self.unsubscribe_lora_rx(subscriber)
        try:
            if (
                self._ecal_initialized_here
                and self._ecal_initialized
                and self._ecal is not None
                and self._ecal.ok()
            ):
                self._ecal.finalize()
        except Exception:
            pass
        self._ecal_initialized = False
        self._ecal_initialized_here = False


_ecal_rpc = None


def get_ecal_rpc():
    global _ecal_rpc
    if _ecal_rpc is None:
        _ecal_rpc = EcalRpc()
    return _ecal_rpc


def get_rpc():
    return get_ecal_rpc()


def stop():
    global _ecal_rpc
    if _ecal_rpc is not None:
        _ecal_rpc.close()
        _ecal_rpc = None


def _handle_signal(_signum, _frame):
    stop()


for _sig_name in ("SIGINT", "SIGTERM"):
    _sig = getattr(signal, _sig_name, None)
    if _sig:
        try:
            signal.signal(_sig, _handle_signal)
        except Exception:
            pass


atexit.register(stop)
