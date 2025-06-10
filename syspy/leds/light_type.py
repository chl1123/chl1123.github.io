import enum


class LightType(enum.Enum):
    ConstantLight = 1  # 常亮
    MutableBreath = 2  # 呼吸灯
    MutableHorseRace = 3  # 跑马灯
    Flow = 4  # 流水灯
    Rainbow = 5  # 彩虹灯
    Blink = 6  # 闪烁灯


class Brightness(enum.Enum):
    Bright = 1.0  # 明亮
    Normal = 0.3  # 正常 60%-100%
    DIM = 0.1  # 昏暗 6%-59%
    Dark = 0.05  # 黑暗 5%


class Color(enum.Enum):
    White = [255, 255, 255, 0]

    Red = [255, 0, 0, 0]
    RedDark = [170, 20, 0, 0]

    Green = [0, 255, 0, 0]

    Blue = [0, 0, 255, 0]
    BlueCobalt = [0, 80, 164, 0]

    Yellow = [255, 255, 0, 0]

    PinkPurple = [30, 0, 30, 0]
