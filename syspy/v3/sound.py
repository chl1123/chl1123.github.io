from typing import Optional, TYPE_CHECKING

from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.sound import SoundInterface


@default_plugin("MoveFactory")
class SoundV3(SoundInterface):
    """音频"""

    _TOPIC = "rbk.protocol.msgSound"
    _PLUGIN = "SoundPlayer"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgSound
        data: msgSound = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgSound
            cls._MODEL_CLASS = msgSound

    @classmethod
    @call_service()
    def setSound(cls, name: str, flag: bool) -> None:
        pass

    @classmethod
    @call_service()
    def setSoundCount(cls, name: str, count: int) -> None:
        pass

    @classmethod
    @call_service()
    def stopSound(cls, flag: bool):
        pass

    def getStatus(self) -> Optional[int]:
        if self.update():
            return self.data.status

    def getSoundName(self) -> str:
        if self.update():
            return self.data.soundName

    def getLoop(self) -> Optional[bool]:
        if self.update():
            return self.data.loop

    def getCount(self) -> Optional[int]:
        if self.update():
            return self.data.count