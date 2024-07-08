from address.version import Version


class ALL(Version):
    # 用户数据
    @classmethod
    def DATA(cls):
        return cls._get_value_by_version(10504, 10504)

    # 模块类别代码
    @classmethod
    def TYPE(cls):
        return cls._get_value_by_version(30201, 10501)

    # 协议版本
    @classmethod
    def VERSION(cls):
        return 10502

    # 系统急停状态
    @classmethod
    def EMC(cls):
        return cls._get_value_by_version(10201, 501)

    # 模块运行模式
    @classmethod
    def MODE(cls):
        return cls._get_value_by_version(10202, 502)

    # 导航状态
    @classmethod
    def RUN_STATUS(cls):
        return cls._get_value_by_version(0, 511)

    # 报警状态
    @classmethod
    def ALERT_STATUS(cls):
        return cls._get_value_by_version(0, 512)

    # 系统错误代码
    @classmethod
    def ERROR_CODE(cls):
        return cls._get_value_by_version(39001, 10503)