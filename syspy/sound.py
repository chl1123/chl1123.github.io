from .lib.py_rpc import Message, call_service, default_plugin


@default_plugin("MoveFactory")
class Sound(Message["Message_Sound"]):
    """音频"""

    _TOPIC = "rbk.protocol.Message_Sound"
    _PLUGIN = "SoundPlayer"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Sound
            cls._MODEL_CLASS = Message_Sound

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

    @classmethod
    def get_status(cls) -> int:
        """获取声音状态，0表示停止（未播放），1表示暂停，2表示正在播放

        Returns:
            int: 声音状态值
        """
        if cls.update():
            return cls.data.status

    @classmethod
    def get_sound_name(cls) -> str:
        """获取带有后缀的声音名称

        Returns:
            str: 声音名称字符串
        """
        if cls.update():
            return cls.data.sound_name

    @classmethod
    def get_loop(cls) -> bool:
        """获取声音是否循环播放的状态

        Returns:
            bool: True表示循环播放，False表示不循环播放
        """
        if cls.update():
            return cls.data.loop

    @classmethod
    def get_count(cls) -> int:
        """获取声音播放次数

        Returns:
            int: 声音播放次数
        """
        if cls.update():
            return cls.data.count
