from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.sound import SoundInterface
from syspy.registry.channel import behave
from .protobuf.compat import channel_or_topic
if TYPE_CHECKING:
    from .protobuf.message.message_sound_pb2 import msgSound


@default_plugin("BehavFactory")
@channel_or_topic(topic="rbk.protocol.msgSound", channel=behave.TOPIC_BEHAVE_SOUND)
class SoundV3(SoundInterface):
    """音频"""

    data: msgSound = None

    _PLUGIN = "BehavFactory"
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf.message.message_sound_pb2 import msgSound
            cls._MODEL_CLASS = msgSound

    @classmethod
    def setSound(cls, name: str, flag: bool, volume: int = 100) -> None:
        """播放音频。

        插件签名：``BehavFactory::setSound(name, loop, volume=100)``，
        其中 ``volume`` 是 2026-08 新增的（m-7067752899）。

        这里不用 ``@call_service()``：它只转发调用方实际传入的参数，
        Python 的默认值不会被送到插件；而插件侧 RPC 按参数个数分发，
        缺参时 ``int`` 默认构造为 0，于是变成静音播放。所以显式把
        ``volume`` 作为第三个位置参数传出去。
        """
        plugin = getattr(cls, "default_plugin", "BehavFactory")
        return cls.client().call_service(plugin, "setSound", name, flag, int(volume))

    @classmethod
    def setSoundCount(cls, name: str, count: int, volume: int = 100) -> None:
        """播放音频指定次数（``volume`` 同上，必须显式传递）。"""
        plugin = getattr(cls, "default_plugin", "BehavFactory")
        return cls.client().call_service(plugin, "setSoundCount", name, count, int(volume))

    @classmethod
    @call_service()
    def stopSound(cls, flag: bool):
        pass

    def getStatus(self) -> Optional[int]:
        if self.update():
            return self.data.status

    def getSoundName(self) -> Optional[str]:
        if self.update():
            return self.data.soundName

    def getLoop(self) -> Optional[bool]:
        if self.update():
            return self.data.loop

    def getCount(self) -> Optional[int]:
        if self.update():
            return self.data.count