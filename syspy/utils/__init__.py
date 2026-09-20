from enum import Enum, IntEnum

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


class TaskStage(IntEnum):
    """脚本 TASK 的调度阶段，即 ``Module.getTaskParams("stage")``，默认 2。

    语义是“前置点停不停、谁控制导航”，与原地任务、AutoPre 都没有绑定关系：

    - ``STOP_AT_PRE``（0）：在前置点导航停下，脚本任务完成后才会导航。
    - ``PASS_PRE``（1）：在前置点导航不停下，同时开始执行脚本。
    - ``AT_TARGET``（2，默认）：导航到终点完成后才会执行脚本。
    - ``SCRIPT_DRIVEN``（3）：在前置点停下，脚本控制导航和脚本任务。

    AutoPre 只是选了 3 方便（脚本要在前置点停下并接管导航），stage=3 本身
    并不表示 AutoPre；判定 AutoPre 要看 ``Module.getAutoPre()``。

    历史脚本用裸数字比较（``stage == 2`` / ``!= 3``），语义不自证，故提供
    命名常量。数值取值与平台下发一致，不要修改。
    """

    STOP_AT_PRE = 0
    PASS_PRE = 1
    AT_TARGET = 2
    SCRIPT_DRIVEN = 3


DEFAULT_TASK_STAGE = TaskStage.AT_TARGET


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
