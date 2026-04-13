#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BehavFactory RPC 客户端。

只负责向 BehavFactory 发 service call，不依赖其他 behavs 模块。
"""

import json
import logging

log = logging.getLogger("rbk.behavs.rpc")


class BehavRpc(object):
    """BehavFactory service call 封装。"""

    def __init__(self):
        self._client = None
        self._use_ecal = False
        try:
            import ecal.nanobind_core as ecal_core
            self._ecal = ecal_core
            if not ecal_core.ok():
                cfg = ecal_core.Configuration()
                cfg.registration.local.transport_type = ecal_core.LocalTransportType.SHM
                ecal_core.initialize(cfg, "behavs_rpc")
            self._client = ecal_core.ServiceClient("BehavFactory")
            self._use_ecal = True
            log.info("BehavRpc initialized with eCAL nanobind")
        except Exception as e:
            log.warning(f"eCAL client init failed: {e}")

    def call(self, method, *args):
        """调用 BehavFactory 的指定 service。"""
        if not self._use_ecal:
            return None
        try:
            request = json.dumps(args).encode("utf-8")
            responses = self._client.call_with_response(method, request, 1000)
            if responses:
                print(f"RPC call response: {responses[0].response}")
                return json.loads(responses[0].response) if responses[0].response else None
            return None
        except Exception as e:
            log.warning(f"RPC call failed: {method}({args}): {e}")
            return None

    def set_action(self, channel, payload_dict):
        """通用 setAction 通道派发。"""
        action = json.dumps(payload_dict, sort_keys=True)
        return self.call("setAction", channel, action)
