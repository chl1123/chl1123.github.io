from enum import Enum, IntEnum

SCRIPTS_DIR = "/opt/.data/rbk/resources/scripts"


class ScriptType(str, Enum):
    TASK = "task"
    GENERAL = "generic"


class Coordinate(Enum):
    """ 坐标系枚举 """
    ROBOT = "robot"
    WORLD = "world"
