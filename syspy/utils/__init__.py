from enum import Enum

SCRIPTS_DIR = "/opt/.data/rbk/resources/scripts/"


class ScriptType(str, Enum):
    """ 脚本类型 """
    TASK = "task"
    GENERAL = "generic"


class Coordinate(str, Enum):
    """ 坐标系 """
    ROBOT = "robot"
    WORLD = "world"
