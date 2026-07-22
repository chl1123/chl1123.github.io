from typing import Optional
from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.sound import SoundInterface


@default_plugin("BehavFactory")  # todo RBK4
class SoundV4(SoundInterface):
    """音频"""

    _TOPIC = ""  # todo RBK4
    _MODEL_CLASS = None

    @classmethod
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from syspy.v4.protobuf.message.messageV4_sound_pb2 import MessageV4_Sound
            cls._MODEL_CLASS = MessageV4_Sound

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

    def getSoundName(self) -> Optional[str]:
        if self.update():
            return self.data.sound_name

    def getLoop(self) -> Optional[bool]:
        if self.update():
            return self.data.loop

    def getCount(self) -> Optional[int]:
        if self.update():
            return self.data.count