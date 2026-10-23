from __future__ import annotations
import math
from typing import Optional, Tuple, TYPE_CHECKING

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from syspy.odometer import OdometerInterface
from syspy.registry.channel import localization
from .protobuf.compat import channel_or_topic
if TYPE_CHECKING:
    from .protobuf.message.message_odometer_pb2 import msgOdometer
    from .protobuf.message.message_motorinfos_pb2 import msgMotorInfo


@channel_or_topic(topic="rbk.protocol.msgOdometer",
                  channel=localization.TOPIC_ODOMETER)
class OdometerV3(OdometerInterface):
    """里程类"""

    data: msgOdometer = None

    _PLUGIN = "MCLoc"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_odometer_pb2 import msgOdometer
            cls._MODEL_CLASS = msgOdometer

    def getCycle(self) -> Optional[int]:
        if self.update():
            return self.data.cycle

    def getPosition(self) -> Optional[Tuple[float, float, float]]:
        if self.update():
            return self.data.x, self.data.y, math.degrees(self.data.angle)

    def getSpeeds(self) -> Optional[Tuple[float, float, float]]:
        if self.update():
            return self.data.velX, self.data.velY, self.data.velRotate

    def getIsStop(self) -> Optional[bool]:
        if self.update():
            return self.data.isStop

    def getMotorInfos(self, device_key: str = None) -> Optional[RepeatedCompositeFieldContainer["msgMotorInfo"]]:
        if device_key is not None:
            from syspy import Motor
            return Motor.getMotorInfos(device_key)
        if self.update():
            return self.data.motorInfo

    def getData(self, fields=None, *, topic: str = None) -> dict:
        """里程消息字典（兼容式读取）。

        3.6 下 ``data.motorInfo`` 来源已弃用（改由 ``/MotorInfo/<key>`` 提供），
        但脚本里仍有 ``Odometer.getData()["motorInfo"]`` 的读法，这里用
        :meth:`getMotorInfos` 的返回值覆盖该字段，保证老读法拿到的是
        ``/MotorInfo/<key>`` 的数据而不是空的/过期的 odometer 字段。
        """
        data = super().getData(fields, topic=topic)
        if data and (fields is None or "motorInfo" in fields):
            motor_infos = self.getMotorInfos() or []
            data["motorInfo"] = [
                self._message_to_dict(motor) for motor in motor_infos
            ]
        return data
