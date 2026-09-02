from enum import Enum

RESOURCES_DIR = "/opt/.data/rbk/resources/"
SCRIPTS_DIR = RESOURCES_DIR + "scripts/"


class ScriptType(str, Enum):
    """ 脚本类型 """
    TASK = "task"
    GENERAL = "generic"


class Coordinate(str, Enum):
    """ 坐标系 """
    ROBOT = "robot"
    WORLD = "world"


def _TR(text: str) -> str:
    """文本翻译

    Args:
        text: 要翻译的文本。RBK 编译时会自动添加到 rbk.ts

    Examples:
        1. 接口使用
        ```python
        from syspy import _TR
        print(_TR("Hello World"))
        param1 = 1
        param2 = 2
        print(_TR(f"Hello World, {param1=}, {param2=}"))
        ```

        2. RBK 编译后 rbk.ts 文件中会增加2行
        ```txt
            Hello World ~-~
            Hello World, {1}, {2} ~-~
        ```

        3. 手动编辑 rbk.ts 文件
        ```txt
        Hello World ~-~ 你好，世界
        Hello World, {1}, {2} ~-~ 你好，世界, {1}, {2}
        ```
    """
    return text
