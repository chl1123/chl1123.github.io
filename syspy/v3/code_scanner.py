from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.code_scanner import CodeScannerInterface
from syspy.registry.channel import device
from .protobuf.compat import IS_RBK35, channel_or_topic

if TYPE_CHECKING:
    from .protobuf.message.message_codescanner_pb2 import msgCodeScanner, msgCodeScannerDMT


@channel_or_topic(topic="rbk.protocol.msgCodeScanner",
                  channel=device.TOPIC_PREFIX_CODESCANNER)
class CodeScannerV3(CodeScannerInterface):
    """扫码器类

    3.6 起改读 channel ``/CodeScanner/<key>``（按设备拆分），
    3.5 则读单个聚合 topic ``rbk.protocol.msgCodeScanner``。
    不传 device_key 时枚举模型里的扫码器设备并合并结果（仅 3.6）。
    """

    data: msgCodeScanner = None

    _PLUGIN = "DSPChassis"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_codescanner_pb2 import msgCodeScanner
            cls._MODEL_CLASS = msgCodeScanner

    def _read_devices(self) -> "msgCodeScanner":
        """枚举报码器设备并合并各自 channel 的数据。"""
        from syspy import RobotParam
        from .protobuf.message.message_codescanner_pb2 import (
            msgCodeScanner, msgCodeScannerDMT,
        )
        merged = msgCodeScanner()
        for key in RobotParam.getDeviceList("CodeScanner") or []:
            if self.update_channel(device.TOPIC_PREFIX_CODESCANNER + key, msgCodeScannerDMT):
                node = self._topic_data.get(device.TOPIC_PREFIX_CODESCANNER + key)
                if node is not None:
                    merged.codeScanners.append(node)
            elif self.update_channel(device.TOPIC_PREFIX_CODESCANNER + key, msgCodeScanner):
                data = self._topic_data.get(device.TOPIC_PREFIX_CODESCANNER + key)
                if data is not None:
                    merged.MergeFrom(data)
        return merged

    def getCodeScanners(self, device_key: str = None):
        """不传 device_key：合并全部设备（3.6）/ 读聚合 topic（3.5）；传入则只读该设备。"""
        if IS_RBK35:
            if not self.update():
                return None
            return self.data.codeScanners
        if device_key is None:
            merged = self._read_devices()
            if len(merged.codeScanners) == 0 and not merged.ListFields():
                return None
            self.data = merged
            return merged.codeScanners
        if not device_key or "/" in device_key:
            raise ValueError("device_key must be a device key, not a channel path")
        data = self.get_channel_data(device.TOPIC_PREFIX_CODESCANNER + device_key,
                                     self._MODEL_CLASS)
        return data or None
