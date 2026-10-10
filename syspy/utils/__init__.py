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


class ChassisType(str, Enum):
    """底盘类型，即设备模型 ``Model-000.chassisType`` 的取值。

    取值与设备模型文件的枚举项 key 一一对应（见 ``/opt/.data/rbk/resources/devices/robot.model``
    的 chassisType 节点），不要改名；新增车型需同步模型文件。

    需要判断“底盘能不能横移”时用 :data:`OMNI_CHASSIS_TYPES`，不要在各脚本里重新列举。

    Note:
        继承 ``str`` 使成员与模型文件读出的裸字符串可直接比较：
        ``ChassisType.OMNI == "omni"`` 为 True，因此 ``chassis_type == ChassisType.OMNI``
        和 ``chassis_type in OMNI_CHASSIS_TYPES`` 对字符串与枚举成员都成立。
    """

    TWO_WHEEL_DIFF = "twoWheelDiff"
    FOUR_WHEEL_DIFF = "fourWheelDiff"
    SINGLE_STANDARD_STEER = "singleStandardSteer"
    SINGLE_DIFF_STEER = "singleDiffSteer"
    VARIABLE_WHEELBASE_SINGLE_STANDARD_STEER = "variableWheelbaseSingleStandardSteer"
    VARIABLE_WHEELBASE_SINGLE_DIFFERENTIAL_STEER = "variableWheelbaseSingleDifferentialSteer"
    STANDARD_ACKERMANN = "standardAckermann"
    DIFFERENTIAL_ACKERMANN = "differentialAckermann"
    SINGLE_WALK_DUAL_STEERS = "singleWalkDualSteers"
    TWO_TRACKS = "twoTracks"
    MULTIPLE_DIFFERENTIAL_STEERS = "multipleDifferentialSteers"
    MULTI_STANDARD_AND_DIFFERENTIAL_STEERS = "multiStandardAndDifferentialSteers"
    MULTI_STEERS = "multiSteers"
    OMNI = "omni"
    RGV4 = "RGV4"
    RGV2 = "RGV2"
    STACKER = "stacker"
    WHEELED_LEGGED_QUADRUPED = "wheeledLeggedQuadruped"
    QUADRUPED = "quadruped"


#: 支持全向运动（可原地/横移）的底盘类型集合。成员同时接受 ``ChassisType`` 成员
#: 与模型文件读出的裸字符串；用 ``in`` 判断即可。
OMNI_CHASSIS_TYPES = frozenset({
    ChassisType.MULTIPLE_DIFFERENTIAL_STEERS,
    ChassisType.MULTI_STANDARD_AND_DIFFERENTIAL_STEERS,
    ChassisType.MULTI_STEERS,
    ChassisType.OMNI,
    ChassisType.QUADRUPED,
    ChassisType.WHEELED_LEGGED_QUADRUPED,
})


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
