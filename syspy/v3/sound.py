import typing

from syspy.core.rbk_rpc import call_service, default_plugin
from syspy.sound import SoundInterface


@default_plugin("MoveFactory")
class SoundV3(SoundInterface):
    """音频"""

    _TOPIC = "rbk.protocol.msgSound"
    _PLUGIN = "SoundPlayer"
    _MODEL_CLASS = None
    if typing.TYPE_CHECKING:
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
        """播放音乐

        Args:
            name (str): 音频名称
            flag (bool): 是否循环播放
        """
        pass

    @classmethod
    @call_service()
    def setSoundCount(cls, name: str, count: int) -> None:
        """播放音乐

        Args:
            name (str): 音频名称
            count (int): 播放次数，需要大于0
        """
        pass

    @classmethod
    @call_service()
    def stopSound(cls, flag: bool):
        """停止播放音乐

        Args:
            flag (bool): 如果为True则为停止播放音乐
        """
        pass

    def getStatus(self) -> int:
        """获取声音状态，0表示停止（未播放），1表示暂停，2表示正在播放

        Returns:
            (int): 声音状态值
        """
        if self.update():
            return self.data.status

    def getSoundName(self) -> str:
        """获取带有后缀的声音名称

        Returns:
            (str): 声音名称字符串
        """
        if self.update():
            return self.data.sound_name

    def getLoop(self) -> bool:
        """获取声音是否循环播放的状态

        Returns:
            (bool): True表示循环播放，False表示不循环播放
        """
        if self.update():
            return self.data.loop

    def getCount(self) -> int:
        """获取声音播放次数

        Returns:
            (int): 声音播放次数
        """
        if self.update():
            return self.data.count