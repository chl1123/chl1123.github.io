import time

start_time = time.time()

import importlib.util
import os
import json
import sys
from enum import Enum
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing_extensions import TypeAlias
from typing import Any, Dict, List, Optional, Generator, Union, Tuple

SCRIPTS_DIR = "/opt/.data/rbk/resources/scripts"

PY_SUFFIX = ".py"
CONFIG_SUFFIX = "_config.json"
INPUT_SUFFIX = "_input.json"
prefix_dir = ""


def _get_prefix_dir(file):
    if not file.startswith(SCRIPTS_DIR):
        raise ValueError("script path error. It must be in the 'scripts' path")

    script_dir = file.replace(SCRIPTS_DIR, '')
    if not script_dir.endswith(PY_SUFFIX):
        raise ValueError(f"script file error. It must be in the {PY_SUFFIX} file")
    global prefix_dir
    script_right_dir, script_file_name = script_dir.rsplit('/', 1)
    config_dir = SCRIPTS_DIR + "/params" + script_right_dir
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

    def to_dict(self) -> Dict[str, Any]:
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
            result["children"] = [child.to_dict() for child in self.children]

        # 清理空值
        return {k: v for k, v in result.items() if v not in (None, "", [], {}) and not (isinstance(v, list) and not v)}


class ParamBuilder:
    """参数配置构建器，支持嵌套结构"""

    def __init__(self, caller_file: str = None, desc: str = ""):
        if not prefix_dir:
            _get_prefix_dir(caller_file)
        self.root = {"desc": desc, "groups": []}
        self._current_path: List[str] = []
        self._current_node: Optional[ParamField] = None
        self._current_children: List[ParamField] = self.root["groups"]
        self._context_stack: List[Tuple[Optional[ParamField], List[ParamField], List[str]]] = []

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

        # 将Python风格的字段名转换为JSON风格的字段名
        json_field_name = {
            "single_step": "singleStep",
            "is_clone": "isClone",
            "bind_type": "bindType",
            "is_read_only": "isReadOnly",
            "min_value": "minValue",
            "max_value": "maxValue",
            "default_value": "defaultValue"
        }.get(field_name, field_name)

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

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        groups = [group.to_dict() for group in self.root["groups"]]
        result = {"desc": self.root["desc"], "groups": groups}
        return result

    def to_json(self, indent: int = 2) -> str:
        """将配置转换为JSON字符串"""
        groups = [group.to_dict() for group in self.root["groups"]]
        result = {"desc": self.root["desc"], "groups": groups}
        return json.dumps(result, ensure_ascii=False, indent=indent)

    def save_to_file(self, filename: str = None, indent: int = 2) -> None:
        """将配置保存到文件"""
        if filename is None:
            filename = prefix_dir + INPUT_SUFFIX
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent))


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
                    self.leaf_param_keys.add(param['key'])

                # 特殊处理COMBO_BOX_BOOL类型
                if param.get('type') == ParamType.COMBO_BOX_BOOL:
                    for child in param.get('children', []):
                        # 使用整数0/1表示OFF/ON
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

        # 1. 提取operation参数
        operation = self._extract_operation(input_params)
        if operation:
            flat_params["operation"] = operation

        # 2. 处理其他参数
        for key, value in input_params.items():
            if key == "operation":
                continue  # 已处理

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

            # 检查是否是叶子节点参数
            if leaf_key in self.leaf_param_keys:
                param_def = self.param_index.get(leaf_key)
                # STRING_COMBO_LIST类型且value是整数，转换为子项键值
                if (param_def and param_def.get('type') == ParamType.STRING_COMBO_LIST and
                    isinstance(value, int)):
                    # 获取STRING_COMBO_LIST的子项
                    children = param_def.get('children', [])
                    if 0 <= value < len(children):
                        flat_params[leaf_key] = children[value]['key']
                    else:
                        # 索引无效，保持原值
                        flat_params[leaf_key] = value
                else:
                    flat_params[leaf_key] = value
            # 否则保留原始键（可能是中间节点）
            else:
                flat_params[key] = value

        return flat_params

    def _extract_operation(self, input_params: Dict[str, Any]) -> Optional[str]:
        """从输入参数中提取operation值"""
        if input_params is None or len(input_params) == 0:
            return None
        # 直接提供operation参数
        if "operation" in input_params:
            return input_params["operation"]

        # 从路径中提取operation
        for key in input_params:
            if key.startswith("operation."):
                parts = key.split('.')
                if len(parts) > 1:
                    # 返回第一个非"operation"的部分
                    for part in parts[1:]:
                        if part and part != "":
                            return part
        return None

    def validate(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入参数并返回处理后的参数"""
        # 1. 转换为平铺格式
        flat_params = self._flatten_input_params(input_params)
        validated_params = {}
        errors = []

        # 2. 验证全局参数
        for param_def in self.param_definition.get('groups', []):
            if 'type' in param_def:
                self._validate_param(
                    param_def,
                    flat_params.get(param_def['key']),
                    flat_params,
                    validated_params,
                    errors
                )

        # 3. 验证操作参数
        operation_def = None
        for group in self.param_definition.get('groups', []):
            if group.get('key') == 'operation':
                operation_def = group
                break

        # 检查operation是否为必需参数
        operation_required = operation_def and operation_def.get('required', False)
        operation = flat_params.get('operation')

        # 只有当operation为必需参数且未提供时才报错
        if operation_required and not operation:
            errors.append("Missing required parameter: operation")
        elif operation:
            op_def = self._find_operation_definition(operation)
            if op_def is None:
                errors.append(f"Invalid operation: {operation}")
            else:
                self._validate_operation_params(
                    op_def,
                    flat_params,
                    validated_params,
                    errors
                )

        if errors:
            raise ValueError("\n".join(errors))

        return validated_params

    def _find_operation_definition(self, operation: str) -> Optional[Dict[str, Any]]:
        """查找操作定义"""
        # 查找operation组
        for group in self.param_definition.get('groups', []):
            if group.get('key') == 'operation':
                # 在子节点中查找具体操作
                for child in group.get('children', []):
                    if child.get('key') == operation:
                        return child
        return None

    def _validate_operation_params(
            self,
            op_def: Dict[str, Any],
            input_params: Dict[str, Any],
            validated_params: Dict[str, Any],
            errors: List[str]
    ):
        """验证操作特定参数"""

        # 递归验证操作参数
        def validate_params(params_def: List[Dict[str, Any]], parent_path: str = ""):
            for param_def in params_def:
                full_path = f"{parent_path}.{param_def['key']}" if parent_path else param_def['key']

                # 验证当前参数
                self._validate_param(
                    param_def,
                    input_params.get(param_def['key']),
                    input_params,
                    validated_params,
                    errors,
                    full_path
                )

                # 递归验证子参数
                if 'children' in param_def and param_def['children']:
                    validate_params(param_def['children'], full_path)

        # 从操作定义的子节点开始验证
        if 'children' in op_def and op_def['children']:
            validate_params(op_def['children'])

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
        param_type = param_def['type']
        full_path = full_path or key

        # 检查必填参数
        if param_def.get('required', False) and value is None:
            errors.append(f"Missing required parameter: {full_path}")
            return

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
    full_path = SCRIPTS_DIR + "/" + script_name  # 替换为你的脚本路径
    gen_param(full_path)
