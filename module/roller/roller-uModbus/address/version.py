import threading


class Version:
    # 保护对_version变量的访问
    _version_lock = threading.Lock()
    _version = 0

    @classmethod
    def set_version(cls, new_version):
        """
        设置_version的值，确保线程安全
        """
        with cls._version_lock:
            cls._version = new_version

    @classmethod
    def get_version(cls):
        """
        获取_version的值，确保线程安全
        """
        with cls._version_lock:
            return cls._version

    @classmethod
    def _get_value_by_version(cls, version_1_value, version_2_value):
        """根据版本号获取状态码"""
        if cls.get_version() == 1:
            return version_1_value
        elif cls.get_version() == 2:
            return version_2_value
        else:
            return 0