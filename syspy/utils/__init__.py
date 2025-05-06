from enum import Enum

SCRIPTS_DIR = "/opt/.data/rbk/resources/scripts"


class ScriptType(str, Enum):
    TASK = "task"
    GENERAL = "generic"
