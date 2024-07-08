from address.version import Version


class ROLLER(Version):

    # 有无物料
    @classmethod
    def ROLLER_IS_FULL(cls):
        return cls._get_value_by_version(10203, 601)

    #  辊筒/皮带运行状态
    @classmethod
    def ROLLER_STATE(cls):
        return cls._get_value_by_version(31200, 10602)

    # 向左通过
    @classmethod
    def ROLLER_LEFT_PASS(cls):
        return cls._get_value_by_version(0, 632)

    # 向右通过
    @classmethod
    def ROLLER_RIGHT_PASS(cls):
        return cls._get_value_by_version(0, 633)

    # 前侧预上料
    @classmethod
    def ROLLER_FRONT_PRE_LOAD(cls):
        return cls._get_value_by_version(1012, 622)

    # 前侧上料
    @classmethod
    def ROLLER_FRONT_LOAD(cls):
        return cls._get_value_by_version(1005, 615)

    # 前侧下料
    @classmethod
    def ROLLER_FRONT_UNLOAD(cls):
        return cls._get_value_by_version(1006, 616)

    # 向前滚动（两测挡板均放下）
    @classmethod
    def ROLLER_FRONT_ROLL(cls):
        return cls._get_value_by_version(1016, 626)

    # 后侧预上料
    @classmethod
    def ROLLER_BACK_PRE_LOAD(cls):
        return cls._get_value_by_version(1013, 623)

    # 后侧上料
    @classmethod
    def ROLLER_BACK_LOAD(cls):
        return cls._get_value_by_version(1007, 617)

    # 后侧下料
    @classmethod
    def ROLLER_BACK_UNLOAD(cls):
        return cls._get_value_by_version(1008, 618)

    #  向后滚动（两测挡板均放下）
    @classmethod
    def ROLLER_BACK_ROLL(cls):
        return cls._get_value_by_version(1017, 627)

    # 左侧预上料
    @classmethod
    def ROLLER_LEFT_PRE_LOAD(cls):
        return cls._get_value_by_version(1010, 620)

    # 左侧上料
    @classmethod
    def ROLLER_LEFT_LOAD(cls):
        return cls._get_value_by_version(1001, 611)

    # 左侧下料
    @classmethod
    def ROLLER_LEFT_UNLOAD(cls):
        return cls._get_value_by_version(1002, 612)

    # 向左滚动（两测挡板均放下）
    @classmethod
    def ROLLER_LEFT_ROLL(cls):
        return cls._get_value_by_version(1014, 624)

    # 右侧预上料
    @classmethod
    def ROLLER_RIGHT_PRE_LOAD(cls):
        return cls._get_value_by_version(1011, 621)

    # 右侧上料
    @classmethod
    def ROLLER_RIGHT_LOAD(cls):
        return cls._get_value_by_version(1003, 613)

    # 右侧下料
    @classmethod
    def ROLLER_RIGHT_UNLOAD(cls):
        return cls._get_value_by_version(1004, 614)

    # 向右滚动（两测挡板均放下）
    @classmethod
    def ROLLER_RIGHT_ROLL(cls):
        return cls._get_value_by_version(1015, 625)

    # 辊筒/皮带停止
    @classmethod
    def ROLLER_STOP(cls):
        return cls._get_value_by_version(1009, 619)

    # 前后方向对换
    @classmethod
    def ROLLER_FRONT_BACK_INVERSE(cls):
        return cls._get_value_by_version(1102, 651)

    # 左右方向对换
    @classmethod
    def ROLLER_LEFT_RIGHT_INVERSE(cls):
        return cls._get_value_by_version(1101, 650)

    # 实时运行速度
    @classmethod
    def ROLLER_SPEED_LEVEL(cls):
        return cls._get_value_by_version(31201, 10604)

    # 辊筒/皮带错误代码
    @classmethod
    def ROLLER_ERROR_CODE(cls):
        return cls._get_value_by_version(39002, 10603)