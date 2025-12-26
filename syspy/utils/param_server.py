import time
from syspy.core.rbk_rpc import Service
from syspy.utils import SCRIPTS_DIR

start_time = time.time()

import importlib.util
import os
import json
import sys
from enum import Enum
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing_extensions import TypeAlias
from typing import Any, Dict, List, Optional, Generator, Union, Tuple, Callable


PY_SUFFIX = ".py"
CONFIG_SUFFIX = "_config.json"
INPUT_SUFFIX = "_input.json"
TASK_SUFFIX = "_task.json"
prefix_dir = ""
script_dir = ""

def _get_prefix_dir(file):
    if not file.startswith(SCRIPTS_DIR):
        raise ValueError("script path error. It must be in the 'scripts' path")
    global prefix_dir, script_dir
    script_dir = file.replace(SCRIPTS_DIR, '')
    if not script_dir.endswith(PY_SUFFIX):
        raise ValueError(f"script file error. It must be in the {PY_SUFFIX} file")
    script_right_dir, script_file_name = script_dir.rsplit('/', 1)
    config_dir = SCRIPTS_DIR + "params/" + script_right_dir
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    prefix_dir = config_dir + '/' + script_file_name.replace(PY_SUFFIX, '')
    return prefix_dir


class ParamServer:
    """
    参数服务:构建的参数以json的格式保存在params的文件夹下，参数文件名为脚本名称，后缀为json。
    如果默认数据没有，则创建。否则用文件中的数据
    目前支持的数据格式为str, float, int, bool, list
    使用方式:
    p = ParamServer(__file__)
    param = p.loadParam("motor_name", "str", default = "motor1")
    """

    def __init__(self, file):
        _get_prefix_dir(file)

        self.file = prefix_dir + CONFIG_SUFFIX
        self.data = {}
        if os.path.exists(self.file) and os.path.getsize(self.file):
            try:
                with open(self.file, 'r', encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                raise IOError(f"read file error. {e}")

    def loadParam(self, name: str, type: str = "", group: str = "", default=None, **kw):
        def updateKey(data, key, value):
            if (key not in data) or (key in data and data[key] != value):
                return True
            else:
                return False

        update_file = False
        if type == "float" or type == "str" or type == "int" or type == "bool" or type == "list":
            if default is not None:
                if name not in self.data:
                    update_file = True
                    self.data[name] = {}
                if "value" not in self.data[name]:
                    update_file = True
                    self.data[name]["value"] = eval(type)(default)
                if "group" not in self.data[name]:
                    update_file = True
                    self.data[name]["group"] = group
                if "type" not in self.data[name]:
                    update_file = True
                    self.data[name]["type"] = type
                if updateKey(self.data[name], "default", default):
                    update_file = True
                    self.data[name]["default"] = default
                if type == "float" or type == "int":
                    if "maxValue" in kw and updateKey(self.data[name], "maxValue", kw["maxValue"]):
                        update_file = True
                        self.data[name]["maxValue"] = kw["maxValue"]
                    if "minValue" in kw and updateKey(self.data[name], "minValue", kw["minValue"]):
                        update_file = True
                        self.data[name]["minValue"] = kw["minValue"]
                if "comment" in kw and updateKey(self.data[name], "comment", kw["comment"]):
                    update_file = True
                    self.data[name]["comment"] = kw["comment"]
                if "type" in kw and updateKey(self.data[name], "type", kw["type"]):
                    update_file = True
                    self.data[name]["type"] = kw["type"]
                if "group" in kw and updateKey(self.data[name], "group", kw["group"]):
                    update_file = True
                    self.data[name]["group"] = kw["group"]
                if "unit" in kw and updateKey(self.data[name], "unit", kw["unit"]):
                    update_file = True
                    self.data[name]["unit"] = kw["unit"]
                if update_file:
                    with open(self.file, 'w', encoding="utf-8") as f:
                        json.dump(self.data, f, indent=4, ensure_ascii=False)
                return self.data[name]["value"]
            else:
                raise ValueError("loadParam no 'default' key")
        else:
            raise TypeError(f"loadParam Type (str, int, float, bool, list) Error. {type=}")

    def read(self, name: str):
        if name in self.data:
            return self.data[name]["value"]


# 参数加载器类 - 用于在运行时加载参数
class ScriptParam:
    """参数加载器，用于在运行时加载配置参数和输入参数"""
    _instance = None
    _initialized = False
    config_change_callback = None
    event_task_config = False
    def __new__(cls, script_file: str = None):
        if cls._instance is None:
            cls._instance = super(ScriptParam, cls).__new__(cls)
        return cls._instance

    def __init__(self, script_file: str = None):
        # 防止重复初始化
        if not ScriptParam._initialized:
            if script_file is not None:
                _get_prefix_dir(script_file)
                self.config_file = prefix_dir + CONFIG_SUFFIX
                self.input_file = prefix_dir + INPUT_SUFFIX
                self.task_file = prefix_dir + TASK_SUFFIX
            else:
                self.config_file = None
                self.input_file = None
                self.task_file = None
            self.config_full_params = {}
            self._tasks = []
            self.__config_validator = None
            ScriptParam._initialized = True

    @classmethod
    def getInstance(cls) -> 'ScriptParam':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def builderConfig(self):
        return ParamBuilder(self.config_file, "Script Configuration Parameters", "config")

    def builderInput(self):
        return ParamBuilder(self.input_file, "Script Input Parameters", "input")

    def loadConfig(self) -> Dict[str, Any]:
        """加载配置参数"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        if not self.config_full_params or not ScriptParam.event_task_config:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            # 使用ParamValidator验证配置
            self.__config_validator = ParamValidator(config_data)
        if not ScriptParam.event_task_config:
            self.config_full_params = self._extract_values(self.__config_validator.param_definition)
        return self.__config_validator.validate(self.config_full_params)

    def loadInput(self, input_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """加载输入参数"""
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

        with open(self.input_file, 'r', encoding='utf-8') as f:
            input_def = json.load(f)

        # 使用ParamValidator验证输入
        validator = ParamValidator(input_def)
        return validator.validate(input_params or {})

    @classmethod
    def setConfigChangeCallBack(cls, callback: Callable[[], None]):
        """设置脚本配置参数改变回调

        Args:
            callback (Callable[[], None]): 回调方法
        """
        cls.config_change_callback = callback
        Service.server().register_function(cls.config_change_callback, "script_config_changed", True)

    def _extract_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从参数定义中提取值"""
        values = {}

        def _extract_from_node(node: Dict[str, Any], parent_path: str = ''):

            full_path = f"{parent_path}.{node['key']}" if parent_path else node['key']

            if 'key' in node and ('value' in node or 'defaultValue' in node):
                value = node.get('value', node.get('defaultValue'))
                values[full_path] = value

            if 'children' in node:
                for child in node['children']:
                    _extract_from_node(child, full_path)

        for group in data.get('groups', []):
            _extract_from_node(group)

        return values

    def setTaskConfig(self, config_data: Dict[str, Any]):
        """合并任务配置参数"""
        if config_data:
            print("setTaskConfig()")
            if not self.config_full_params:
                self.config_full_params = config_data
            else:
                self.config_full_params.update(config_data)
                ScriptParam.event_task_config = True
                if ScriptParam.config_change_callback:
                    ScriptParam.config_change_callback()

    def clearTaskConfig(self):
        """恢复任务配置参数"""
        if ScriptParam.event_task_config:
            if ScriptParam.config_change_callback:
                print("clearTaskConfig()")
                ScriptParam.config_change_callback()
            ScriptParam.event_task_config = False

    def addTask(self, task_name: str = None,
                policy: Dict[str, Any] = None,
                args: Dict[str, Any] = None,
                config: Dict[str, Any] = None) -> Dict[str, Any]:
        """添加任务

        Args:
            task_name (str): 任务名称，如 "forkLoad", "forkUnLoad"
            policy (Dict[str, Any], optional): 策略配置
            args (Dict[str, Any], optional): 脚本参数
            config (Dict[str, Any], optional): 脚本配置

        Returns:
            Dict[str, Any]: 任务示例数据结构
        """
        task_value = {
            "policy": policy or {},
            "script": {
                "name": script_dir,
                "args": args or {},
                "config": config or {}
            }
        }

        task = {
            "name": task_name,
            "value": task_value
        }
        self._tasks.append(task)

        return task


    def saveTask(self) -> None:
        """保存任务到文件"""
        tasks_file_data = {}
        if os.path.exists(self.task_file) and os.path.getsize(self.task_file):
            with open(self.task_file, 'r', encoding='utf-8') as f:
                tasks_file_data = json.load(f)

        tasks_file_data["standard"] = self._tasks

        with open(self.task_file, 'w', encoding='utf-8') as f:
            json.dump(tasks_file_data, f, indent=4, ensure_ascii=False)


# 参数类型常量
class ParamType:
    INT = "int"
    UINT = "uint"
    UINT32 = "uint32"
    UINT64 = "uint64"
    INT64 = "int64"
    INT32 = "int32"
    STRING = "string"
    DOUBLE = "double"
    FLOAT = "float"
    BOOL = "bool"
    COMBO_BOX = "comboBox"
    ARRAY = "array"
    IP = "ip"
    HEX = "hex"
    BUTTON = "button"
    BIND_TYPE = "bindType"
    JSON = "json"
    STRING_COMBO_LIST = "stringComboList"
    COMBO_BOX_BOOL = "comboBoxBool"
    SHAPE = "shape"


class BindType:
    class Device(Enum):
        SCREEN = "device:Screen"
        CHARGING_PORT = "device:ChargingPort"
        MODEL = "device:Model"
        CODE_SCANNER = "device:CodeScanner"
        DO_MOTOR = "device:DoMotor"
        DI = "device:Di"
        GNSS = "device:GNSS"
        LED = "device:LED"
        MAGNETIC_SENSOR = "device:MagneticSensor"
        INDICATOR = "device:Indicator"
        IMU = "device:IMU"
        MODBUS_IO = "device:ModbusIO"
        DI_SENSOR = "device:DiSensor"
        DISTANCE_SENSOR = "device:DistanceSensor"
        COLLISION_SENSOR = "device:CollisionSensor"
        MANIPULATORS = "device:Manipulators"
        LASER = "device:Laser"
        DO = "device:DO"
        CAMERA = "device:Camera"
        MOTOR = "device:Motor"
        BATTERY = "device:Battery"
        CAN = "device:Can"

    class App(Enum):
        CONTROL = "app:Control"
        FUNCTIONAL_SAFETY = "app:FunctionalSafety"
        LOCALIZATION = "app:Localization"
        NAVIGATION = "app:Navigation"
        RECOGNITION = "app:Recognition"

    class Shape(Enum):
        RECTANGLE = "shape:rectangle"
        POLYGON = "shape:polygon"

    class Map(Enum):
        MARK = "map:mark"
        PATH = "map:path"
        LOCATION = "map:location"
        AREA = "map:area"

    class Script(Enum):
        GENERIC = "script:generic"
        STANDARD_BATTERY = "script:generic/standard/battery"
        STANDARD_LED = "script:generic/standard/led"

    class Audio(Enum):
        FILE = "audio:file"


# 定义联合类型
BindTypeValue: TypeAlias = Union[
    BindType.Device,
    BindType.App,
    BindType.Shape,
    BindType.Map,
    BindType.Script,
    BindType.Audio,
    str  # 允许直接使用字符串
]


@dataclass
class ParamField:
    """表示参数配置中的一个字段"""
    key: str
    name: str
    desc: str = ""
    type: str = ""
    value: Optional[Any] = None
    unit: Optional[str] = None
    single_step: Optional[float] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    is_clone: Optional[bool] = None
    tag: Optional[List[str]] = None
    children: Optional[List["ParamField"]] = field(default_factory=list)
    bind_type: Optional[str] = None
    is_read_only: Optional[bool] = None
    decimals: Optional[int] = None
    enable: Optional[bool] = None
    permission: Optional[int] = None
    required: bool = False
    default_value: Any = None

    def toDict(self) -> Dict[str, Any]:
        """将ParamField对象转换为字典"""
        result = {
            "key": self.key,
            "name": self.name,
            "desc": self.desc,
            "type": self.type,
            "unit": self.unit,
            "singleStep": self.single_step,
            "isClone": self.is_clone,
            "tag": self.tag,
            "bindType": self.bind_type,
            "isReadOnly": self.is_read_only,
            "decimals": self.decimals,
            "enable": self.enable,
            "permission": self.permission,
            "required": self.required
        }

        # 添加值字段，优先使用default_value
        if self.default_value is not None:
            result["defaultValue"] = self.default_value
        elif self.value is not None:
            result["value"] = self.value

        # 添加可选数值范围
        if self.min_value is not None:
            result["minValue"] = self.min_value
        if self.max_value is not None:
            result["maxValue"] = self.max_value

        # 递归处理子节点
        if self.children:
            result["children"] = [child.toDict() for child in self.children]

        # 清理空值
        return {k: v for k, v in result.items() if v not in (None, [], {}) and not (isinstance(v, list) and not v)}

# 输入参数和配置参数枚举
class ParamBuilder:
    """参数配置构建器，支持嵌套结构"""

    def __init__(self, caller_file: str = None, desc: str = "", p_type: str = "input"):
        if not prefix_dir:
            _get_prefix_dir(caller_file)
        self.root = {"desc": desc, "groups": []}
        self._current_path: List[str] = []
        self._current_node: Optional[ParamField] = None
        self._current_children: List[ParamField] = self.root["groups"]
        self._context_stack: List[Tuple[Optional[ParamField], List[ParamField], List[str]]] = []
        self.p_type = p_type

    @contextmanager
    def GROUPS(self) -> Generator[None, None, None]:
        """进入groups上下文"""
        # 保存当前上下文
        self._context_stack.append((self._current_node, self._current_children, self._current_path.copy()))
        # 设置新上下文
        self._current_children = self.root["groups"]
        self._current_node = None
        self._current_path = []

        try:
            yield
        finally:
            # 恢复上下文
            if self._context_stack:
                self._current_node, self._current_children, self._current_path = self._context_stack.pop()

    @contextmanager
    def GROUP(self, key: str, name: str, desc: str = "", **kwargs) -> Generator[None, None, None]:
        """创建并进入一个组"""
        # 创建新组
        group = ParamField(key=key, name=name, desc=desc, **kwargs)
        self._current_children.append(group)

        # 保存当前上下文
        self._context_stack.append((self._current_node, self._current_children, self._current_path.copy()))

        # 设置新上下文
        self._current_path.append(key)
        self._current_children = group.children
        self._current_node = group

        try:
            yield
        finally:
            # 恢复上下文
            if self._context_stack:
                self._current_node, self._current_children, self._current_path = self._context_stack.pop()

    @contextmanager
    def CHILDREN(self) -> Generator[None, None, None]:
        """进入当前节点的子节点上下文"""
        if not self._current_node:
            raise RuntimeError("CHILDREN must be called within a GROUP or CHILD context")

        # 保存当前上下文
        self._context_stack.append((self._current_node, self._current_children, self._current_path.copy()))

        # 设置新上下文
        self._current_children = self._current_node.children

        try:
            yield
        finally:
            # 恢复上下文
            if self._context_stack:
                self._current_node, self._current_children, self._current_path = self._context_stack.pop()

    @contextmanager
    def CHILD(self, key: str, name: str, desc: str = "", **kwargs) -> Generator[None, None, None]:
        """创建并进入一个子节点"""
        # 创建新子节点
        child = ParamField(key=key, name=name, desc=desc, **kwargs)
        self._current_children.append(child)

        # 保存当前上下文
        self._context_stack.append((self._current_node, self._current_children, self._current_path.copy()))

        # 设置新上下文
        self._current_path.append(key)
        self._current_children = child.children
        self._current_node = child

        try:
            yield
        finally:
            # 恢复上下文
            if self._context_stack:
                self._current_node, self._current_children, self._current_path = self._context_stack.pop()

    def ADD_FIELD(self, field_name: str, value: Any) -> None:
        """添加字段到当前节点"""
        if not self._current_node:
            raise RuntimeError("ADD_FIELD must be called within a GROUP or CHILD context")

        # 设置属性值
        setattr(self._current_node, field_name, value)

    # 便捷方法
    def NAME(self, value: str) -> None:
        self.ADD_FIELD("name", value)

    def DESC(self, value: str) -> None:
        self.ADD_FIELD("desc", value)

    def TYPE(self, value: str) -> None:
        self.ADD_FIELD("type", value)

    def VALUE(self, value: Any) -> None:
        self.ADD_FIELD("value", value)

    def MIN_VALUE(self, value: Union[int, float]) -> None:
        self.ADD_FIELD("min_value", value)

    def MAX_VALUE(self, value: Union[int, float]) -> None:
        self.ADD_FIELD("max_value", value)

    def DEFAULTVALUE(self, value: Any, min_value: Optional[Union[int, float]] = None,
                     max_value: Optional[Union[int, float]] = None) -> None:
        self.ADD_FIELD("default_value", value)
        # 校验min_value和max_value
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError("min_value must be less than max_value")
        if min_value is not None:
            self.ADD_FIELD("min_value", min_value)
        if max_value is not None:
            self.ADD_FIELD("max_value", max_value)

    def UNIT(self, value: str) -> None:
        self.ADD_FIELD("unit", value)

    def SINGLESTEP(self, value: float) -> None:
        self.ADD_FIELD("single_step", value)

    def CLONEABLE(self, value: bool) -> None:
        self.ADD_FIELD("is_clone", value)

    def TAG(self, *tags: str) -> None:
        self.ADD_FIELD("tag", list(tags))

    def BINDTYPE(
            self,
            value: Union[BindTypeValue, List[BindTypeValue]],
            multiple_choice: bool = False
    ) -> None:
        """绑定类型到字段

        Args:
            value (Union[BindTypeValue, List[BindTypeValue]]): 要绑定的值，可以是单个类型或多个类型
            multiple_choice (bool): 是否为多选
        """

        # 转换枚举值为字符串
        def to_str(v: Any) -> str:
            if isinstance(v, Enum):
                return v.value
            return v  # 已经是字符串

        if not multiple_choice:
            # 单选模式
            if isinstance(value, (list, tuple)):
                value_str = ",".join(to_str(v) for v in value)
            else:
                value_str = to_str(value)
            self.ADD_FIELD("bind_type", value_str)
        else:
            # 多选模式
            if not isinstance(value, (list, tuple)):
                value = [value]
            # 转换为字符串列表
            str_values = [to_str(v) for v in value]
            processed_value = f"multiple:{','.join(str_values)}"
            self.ADD_FIELD("bind_type", processed_value)

    def READONLY(self, value: bool) -> None:
        self.ADD_FIELD("is_read_only", value)

    def DECIMALS(self, value: int) -> None:
        self.ADD_FIELD("decimals", value)

    def ENABLE(self, value: bool) -> None:
        self.ADD_FIELD("enable", value)

    def PERMISSION(self, value: int) -> None:
        self.ADD_FIELD("permission", value)

    def REQUIRED(self, value: bool) -> None:
        self.ADD_FIELD("required", value)

    def toDict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        groups = [group.toDict() for group in self.root["groups"]]
        result = {"desc": self.root["desc"], "groups": groups}
        return result

    def toJson(self, indent: int = 2) -> str:
        """将配置转换为JSON字符串"""
        groups = [group.toDict() for group in self.root["groups"]]
        result = {"desc": self.root["desc"], "groups": groups}
        return json.dumps(result, ensure_ascii=False, indent=indent)

    def save_to_file(self, filename: str = None, indent: int = 2) -> None:
        """将配置保存到文件"""
        if filename is None:
            filename = prefix_dir + INPUT_SUFFIX
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.toJson(indent))

    def save(self, merge: bool = False) -> None:
        """将配置保存到文件

        Args:
            merge (bool): 是否和原参数文件合并。True：合并（不会删除旧参数）；False：替换。
        """
        if self.p_type ==  "config":
            suffix = CONFIG_SUFFIX
        else:
            # 后缀
            suffix = INPUT_SUFFIX
        filename = prefix_dir + suffix

        # 如果是配置参数且需要合并，则读取现有文件并合并
        if merge and os.path.exists(filename) and os.path.getsize(filename):
            existing_data = {}
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception as e:
                raise IOError(f"read file error. {e}")
            # 合并现有数据
            merged_data = self._merge_with_existing(existing_data)
            # 保存合并后的数据
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)
        else:
            # 直接保存新数据
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.toJson(2))

    def _index_params(self, node: Dict[str, Any], index: Dict[str, Any], parent_path: str = "") -> None:
        """递归索引参数"""
        key = node.get("key")
        if key:
            full_path = f"{parent_path}.{key}" if parent_path else key
            index[full_path] = node

        # 递归处理子节点
        for child in node.get("children", []):
            self._index_params(child, index, parent_path=key if key else parent_path)

    def _merge_with_existing(self, existing_data: Dict[str, Any]) -> Dict[str, Any]:
        """将新定义与现有数据合并

        策略：
        1. 保留现有文件中的所有参数（不删除任何参数）
        2. 如果参数在新定义中存在，则更新其属性（名称、描述、类型等）
        3. 如果参数在新定义中不存在，则保留原样
        4. 新增的参数添加到对应的组中
        """
        new_data = self.toDict()
        # 创建现有参数的索引
        existing_params = {}
        for group in existing_data.get("groups", []):
            self._index_params(group, existing_params)

        # 创建新参数的索引
        new_params = {}
        for group in new_data.get("groups", []):
            self._index_params(group, new_params)

        # 合并数据
        merged_groups = []

        # 首先处理现有组
        for existing_group in existing_data.get("groups", []):
            group_key = existing_group.get("key")

            # 查找对应的新组定义
            new_group = None
            for ng in new_data.get("groups", []):
                if ng.get("key") == group_key:
                    new_group = ng
                    break

            # 如果新定义中有这个组，则合并组属性
            if new_group:
                merged_group = {**existing_group, **new_group}

                # 合并子参数
                merged_children = self._merge_children(
                    existing_group.get("children", []),
                    new_group.get("children", [])
                )

                if merged_children:
                    merged_group["children"] = merged_children

                merged_groups.append(merged_group)
            else:
                # 新定义中没有这个组，保留原样
                merged_groups.append(existing_group)

        # 添加新定义中新增的组
        for new_group in new_data.get("groups", []):
            group_key = new_group.get("key")
            if not any(g.get("key") == group_key for g in merged_groups):
                merged_groups.append(new_group)

        return {"desc": new_data.get("desc", ""), "groups": merged_groups}


    def _merge_children(self, existing_children: List[Dict[str, Any]], new_children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并子参数列表"""
        merged_children = []

        # 首先处理现有参数
        for existing_child in existing_children:
            child_key = existing_child.get("key")

            # 查找对应的新参数定义
            new_child = None
            for nc in new_children:
                if nc.get("key") == child_key:
                    new_child = nc
                    break

            # 如果新定义中有这个参数，则合并属性
            if new_child:
                merged_child = {**existing_child, **new_child}

                # 递归合并子参数
                if "children" in existing_child or "children" in new_child:
                    merged_child_children = self._merge_children(
                        existing_child.get("children", []),
                        new_child.get("children", [])
                    )

                    if merged_child_children:
                        merged_child["children"] = merged_child_children

                merged_children.append(merged_child)
            else:
                # 新定义中没有这个参数，保留原样
                merged_children.append(existing_child)

        # 添加新定义中新增的参数
        for new_child in new_children:
            child_key = new_child.get("key")
            if not any(c.get("key") == child_key for c in merged_children):
                merged_children.append(new_child)

        return merged_children


class ParamValidator:
    """参数验证器，基于参数定义文件验证输入参数"""

    def __init__(self, param_definition: Dict[str, Any]):
        self.param_definition = param_definition
        self.combo_box_bool_mapping = {
            "OFF": [],
            "ON": [],
        }  # 存储COMBO_BOX_BOOL类型映射
        self.leaf_param_keys = set()  # 存储所有叶子节点的键
        # 构建参数查找字典
        self.param_index = self._build_param_index()

    def _build_param_index(self) -> Dict[str, Dict[str, Any]]:
        """构建参数索引字典（key -> 参数定义）"""
        param_index = {}

        def traverse(params: List[Dict[str, Any]], parent_path: str = ""):
            for param in params:
                full_path = f"{parent_path}.{param['key']}" if parent_path else param['key']

                # 记录叶子节点
                if 'type' in param:
                    param_index[param['key']] = param
                    param_index[full_path] = param
                    if param['type'] != ParamType.ARRAY:
                        self.leaf_param_keys.add(param['key'])

                # 特殊处理COMBO_BOX_BOOL类型
                if param.get('type') == ParamType.COMBO_BOX_BOOL:
                    for child in param.get('children', []):
                        # 使用布尔值 False/True 表示 OFF/ON
                        bool_value = False if child['key'] == "OFF" else True
                        self.combo_box_bool_mapping[child['key']].append(
                            {
                                "parent": param['key'],
                                "value": bool_value
                            }
                        )

                # 递归处理子节点
                if 'children' in param and param['children']:
                    traverse(param['children'], full_path)

        for group in self.param_definition.get('groups', []):
            traverse([group])

        return param_index

    def _flatten_input_params(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        if input_params is None:
            return {}
        """将路径格式参数转换为平铺格式"""
        flat_params = {}

        # 处理所有参数
        for key, value in input_params.items():
            parts = key.split('.')
            leaf_key = parts[-1]

            # 检查是否是COMBO_BOX_BOOL选项
            if leaf_key in self.combo_box_bool_mapping:
                for mapping in self.combo_box_bool_mapping[leaf_key]:
                    combo_box_boo_key = parts[-2]
                    if mapping["parent"] == combo_box_boo_key:
                        flat_params[mapping["parent"]] = mapping["value"]
                        break
                continue

            # 添加对中间节点的处理
            # 对于路径参数，需要同时保留完整路径和各个节点
            if len(parts) > 1:
                # 保留中间节点的值（用于组合框等参数识别）
                for i in range(len(parts)):
                    node_key = parts[i]
                    if node_key in self.leaf_param_keys:
                        # 检查参数类型并做相应处理
                        param_def = self.param_index.get(node_key)
                        processed_value = self._process_param_value(param_def, value, node_key)
                        # 只有当该节点还没有值时才设置，避免覆盖
                        if node_key not in flat_params:
                            flat_params[node_key] = processed_value
            else:
                # 检查是否是叶子节点参数
                if leaf_key in self.leaf_param_keys:
                    param_def = self.param_index.get(leaf_key)
                    processed_value = self._process_param_value(param_def, value, leaf_key)
                    flat_params[leaf_key] = processed_value
                # 否则保留原始键（可能是中间节点）
                else:
                    flat_params[key] = value

        return flat_params

    # 在 ParamValidator 类中添加新的辅助方法
    def _process_param_value(self, param_def: Dict[str, Any], value: Any, param_key: str) -> Any:
        """处理参数值，根据参数类型做相应的转换"""
        if not param_def:
            return value

        param_type = param_def.get('type')

        # 处理 COMBO_BOX 类型参数
        if param_type == ParamType.COMBO_BOX and isinstance(value, int):
            children = param_def.get('children', [])
            if 0 <= value < len(children):
                return children[value]['key']
            else:
                # 索引无效，保持原值
                return value

        # 处理 STRING_COMBO_LIST 类型参数
        elif param_type == ParamType.STRING_COMBO_LIST and isinstance(value, int):
            children = param_def.get('children', [])
            if 0 <= value < len(children):
                return children[value]['key']
            else:
                # 索引无效，保持原值
                return value

        # 其他类型保持原值
        return value

    def validate(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入参数并返回处理后的参数（通用版本）"""
        # 1. 转换为平铺格式
        flat_params = self._flatten_input_params(input_params)
        validated_params = {}
        errors = []

        # 2. 递归验证所有参数
        def validate_all_params(params_def: List[Dict[str, Any]], parent_path: str = ""):
            for param_def in params_def:
                full_path = f"{parent_path}.{param_def['key']}" if parent_path else param_def['key']
                # 验证当前参数
                self._validate_param(
                    param_def,
                    flat_params.get(param_def['key']),
                    flat_params,
                    validated_params,
                    errors,
                    full_path
                )

                # 递归验证子参数
                if 'children' in param_def and param_def['children']:
                    should_validate_children = False

                    # 对于COMBO_BOX类型，根据选择的值决定验证哪个子项
                    if param_def.get('type') == ParamType.COMBO_BOX and param_def['key'] in flat_params:
                        selected_key = flat_params.get(param_def['key'])
                        # 查找选中的子项
                        for child in param_def['children']:
                            if child['key'] == selected_key:
                                should_validate_children = True
                                validate_all_params([child], full_path)
                                break
                    # 对于COMBO_BOX_BOOL类型，根据值决定验证哪个分支
                    elif param_def.get('type') == ParamType.COMBO_BOX_BOOL and param_def['key'] in flat_params:
                        bool_value = flat_params.get(param_def['key'])
                        target_key = "ON" if bool_value else "OFF"
                        # 查找对应分支并验证
                        for child in param_def.get('children', []):
                            if child['key'] == target_key:
                                should_validate_children = True
                                validate_all_params([child], full_path)
                                # 同时验证该分支下的所有子参数
                                self._validate_combo_bool_children(child, input_params, validated_params, errors, full_path + "." + target_key)
                                break
                    else:
                        # 默认情况：检查是否在输入参数中或是否为必填项
                        in_input = False
                        for key in input_params.keys():
                            if key.startswith(full_path) or param_def['key'] in str(input_params.get(key, '')):
                                in_input = True
                        if in_input or (not in_input and param_def.get('required', False) == True):
                            should_validate_children = True
                            validate_all_params(param_def['children'], full_path)

                    # 如果没有特殊处理但有子参数需要验证
                    if not should_validate_children:
                        in_input = any(key.startswith(full_path) for key in input_params.keys())
                        if in_input or param_def.get('required', False):
                            validate_all_params(param_def['children'], full_path)

        # 从根节点开始验证所有参数
        validate_all_params(self.param_definition.get('groups', []))

        # 输入参数
        for key, value in input_params.items():
            # 如果该参数未被处理过
            if key not in validated_params:
                validated_params[key] = value

        if errors:
            raise ValueError("\n".join(errors))
        return validated_params

    def _validate_combo_bool_children(self, parent_def: Dict[str, Any], input_params: Dict[str, Any],
                                      validated_params: Dict[str, Any], errors: List[str], parent_path: str):
        """验证COMBO_BOX_BOOL子参数"""
        def validate_recursive(node_def: Dict[str, Any], current_path: str):
            node_key = node_def.get('key')
            full_path = f"{current_path}.{node_key}" if current_path else node_key
            # 如果该节点在输入参数中，则验证它
            direct_value = input_params.get(node_key)
            path_value = input_params.get(full_path)

            value = direct_value if direct_value is not None else path_value
            self._validate_param(node_def, value, input_params, validated_params, errors, full_path)

            # 递归验证子节点
            if 'children' in node_def:
                for child in node_def['children']:
                    validate_recursive(child, full_path)

        # 验证所有子节点
        if 'children' in parent_def:
            for child in parent_def['children']:
                validate_recursive(child, parent_path)

    def _validate_param(
            self,
            param_def: Dict[str, Any],
            value: Any,
            input_params: Dict[str, Any],
            validated_params: Dict[str, Any],
            errors: List[str],
            full_path: str = ""
    ):
        """验证单个参数"""
        key = param_def['key']
        param_type = param_def.get('type')
        full_path = full_path or key

        # 如果没有类型定义，说明是分组节点，不需要验证值
        if not param_type:
            return

        # 检查必填参数
        if param_def.get('required', False) and value is None:
            errors.append(f"Missing required parameter: {full_path}")
            raise ValueError("Missing required parameter: " + full_path)

        # 如果值仍然为空，跳过验证
        if value is None:
            return

        try:
            # 根据类型验证和转换值
            if param_type in (ParamType.INT, ParamType.INT32, ParamType.INT64,
                              ParamType.UINT, ParamType.UINT32, ParamType.UINT64):
                validated_value = self._validate_number(
                    value, param_type, param_def, full_path
                )

            elif param_type in (ParamType.FLOAT, ParamType.DOUBLE):
                validated_value = self._validate_float(
                    value, param_type, param_def, full_path
                )

            elif param_type == ParamType.BOOL:
                validated_value = self._validate_bool(value, full_path)

            elif param_type == ParamType.STRING:
                validated_value = self._validate_string(value, param_def, full_path)

            elif param_type == ParamType.IP:
                validated_value = self._validate_ip(value, full_path)

            elif param_type == ParamType.COMBO_BOX_BOOL:
                validated_value = self._validate_combo_bool(value, full_path)

            elif param_type == ParamType.COMBO_BOX:
                # 对于COMBO_BOX类型，如果是数字索引则转换为对应的key
                if isinstance(value, int):
                    children = param_def.get('children', [])
                    if 0 <= value < len(children):
                        validated_value = children[value]['key']
                    else:
                        validated_value = value  # 保持原值
                else:
                    validated_value = value

            else:
                # 其他类型不做转换
                validated_value = value

            # 存储验证后的值
            validated_params[key] = validated_value

        except ValueError as e:
            errors.append(str(e))

    def _validate_number(
            self,
            value: Any,
            param_type: str,
            param_def: Dict[str, Any],
            full_path: str
    ) -> Union[int, float]:
        """验证数值类型参数"""
        try:
            # 转换为整数
            if param_type in (ParamType.INT, ParamType.INT32, ParamType.INT64,
                              ParamType.UINT, ParamType.UINT32, ParamType.UINT64):
                num_value = int(value)
            # 转换为浮点数
            else:
                num_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"Parameter {full_path} must be a number, got {type(value).__name__}")

        # 检查范围
        min_val = param_def.get('minValue')
        max_val = param_def.get('maxValue')

        if min_val is not None and num_value < min_val:
            raise ValueError(
                f"Parameter {full_path} value {num_value} is less than minimum {min_val}"
            )

        if max_val is not None and num_value > max_val:
            raise ValueError(
                f"Parameter {full_path} value {num_value} is greater than maximum {max_val}"
            )

        # 检查无符号
        if 'uint' in param_type and num_value < 0:
            raise ValueError(
                f"Parameter {full_path} must be non-negative, got {num_value}"
            )

        return num_value

    def _validate_float(
            self,
            value: Any,
            param_type: str,
            param_def: Dict[str, Any],
            full_path: str
    ) -> float:
        """验证浮点类型参数"""
        try:
            float_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"Parameter {full_path} must be a float, got {type(value).__name__}")

        # 检查范围
        min_val = param_def.get('minValue')
        max_val = param_def.get('maxValue')

        if min_val is not None and float_value < min_val:
            raise ValueError(
                f"Parameter {full_path} value {float_value} is less than minimum {min_val}"
            )

        if max_val is not None and float_value > max_val:
            raise ValueError(
                f"Parameter {full_path} value {float_value} is greater than maximum {max_val}"
            )

        return float_value

    def _validate_bool(self, value: Any, full_path: str) -> bool:
        """验证布尔类型参数"""
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ('true', '1', 'yes', 'on'):
                return True
            if lower_val in ('false', '0', 'no', 'off'):
                return False

        if isinstance(value, int):
            if value == 1:
                return True
            if value == 0:
                return False

        raise ValueError(
            f"Parameter {full_path} must be a boolean, got {type(value).__name__}"
        )

    def _validate_string(self, value: Any, param_def: Dict[str, Any], full_path: str) -> str:
        """验证字符串类型参数"""
        if not isinstance(value, str):
            try:
                # 尝试转换为字符串
                str_value = str(value)
            except:
                raise ValueError(
                    f"Parameter {full_path} must be a string, got {type(value).__name__}"
                )
            return str_value
        return value

    def _validate_ip(self, value: Any, full_path: str) -> str:
        """验证IP地址参数"""
        if not isinstance(value, str):
            value = str(value)

        # 简单的IP地址验证
        parts = value.split('.')
        if len(parts) != 4:
            raise ValueError(f"Parameter {full_path} is not a valid IP address: {value}")

        for part in parts:
            try:
                num = int(part)
                if num < 0 or num > 255:
                    raise ValueError
            except:
                raise ValueError(f"Parameter {full_path} is not a valid IP address: {value}")

        return value

    def _validate_combo_bool(self, value: Any, full_path: str) -> int:
        """验证组合框布尔类型参数"""
        try:
            # 转换为整数
            int_value = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Parameter {full_path} must be an integer for comboBoxBool, got {type(value).__name__}"
            )

        # 组合框布尔类型通常使用0/1表示
        if int_value not in (0, 1):
            raise ValueError(
                f"Parameter {full_path} must be 0 or 1 for comboBoxBool, got {int_value}"
            )

        return value


def load_module_from_path(script_path: str) -> Any:
    module_name = os.path.splitext(os.path.basename(script_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    end_time = time.time()
    print("gen_param time: ", end_time - start_time)
    return module


def gen_param(script_path: str):
    load_module_from_path(script_path)


if __name__ == '__main__':
    script_name = sys.argv[1]
    full_path = SCRIPTS_DIR + script_name  # 替换为你的脚本路径
    gen_param(full_path)
