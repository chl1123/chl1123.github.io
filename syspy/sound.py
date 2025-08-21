from abc import ABC
from syspy.core.rbk_rpc import Message, RBKVersionError


class SoundInterface(ABC, Message):
    """音频"""

    @classmethod
    def setSound(cls, name: str, flag: bool) -> None:
        """播放音乐

        Args:
            name (str): 音频名称
            flag (bool): 是否循环播放
        """
        raise RBKVersionError()

    @classmethod
    def setSoundCount(cls, name: str, count: int) -> None:
        """播放音乐

        Args:
            name (str): 音频名称
            count (int): 播放次数，需要大于0
        """
        raise RBKVersionError()

    @classmethod
    def stopSound(cls, flag: bool):
        """停止播放音乐

        Args:
            flag (bool): 如果为True则为停止播放音乐
        """
        raise RBKVersionError()

    @classmethod
    def get_status(cls) -> int:
        """获取声音状态，0表示停止（未播放），1表示暂停，2表示正在播放

        Returns:
            int: 声音状态值
        """
        raise RBKVersionError()

    @classmethod
    def get_sound_name(cls) -> str:
        """获取带有后缀的声音名称

        Returns:
            str: 声音名称字符串
        """
        raise RBKVersionError()

    @classmethod
    def get_loop(cls) -> bool:
        """获取声音是否循环播放的状态

        Returns:
            bool: True表示循环播放，False表示不循环播放
        """
        raise RBKVersionError()

    @classmethod
    def get_count(cls) -> int:
        """获取声音播放次数

        Returns:
            int: 声音播放次数
        """
        raise RBKVersionError()


from syspy.config import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.sound import SoundV3
    Sound: SoundInterface = SoundV3()
elif RBK_VERSION == 4:
    from syspy.v4.sound import SoundV4
    Sound: SoundInterface = SoundV4()
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")
