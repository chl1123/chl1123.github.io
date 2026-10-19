import time
from syspy.core.rbk_rpc import Service
from syspy.utils import SCRIPTS_DIR

start_time = time.time()

import importlib.util
import os
import json
import sys
import tempfile
import stat
import threading
from enum import Enum
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Generator, Union, Tuple, Callable
from inspect import stack


PY_SUFFIX = ".py"
CONFIG_SUFFIX = "_config.json"
INPUT_SUFFIX = "_input.json"
ACTION_SUFFIX = "_action.json"
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
    # 必须用 exist_ok 而不是先 exists 再 makedirs：前者是原子的，后者是 TOCTOU。
    # 目录名只由脚本所在子目录决定（如 params/syspy 被所有 import syspy 的脚本共用），
    # 多个脚本进程同时首次 import 时会先后通过 exists 检查，后到者建目录失败，
    # 整个脚本以 FileExistsError 退出并被上报为 py@PyCrashed。
    os.makedirs(config_dir, exist_ok=True)
    prefix_dir = config_dir + '/' + script_file_name.replace(PY_SUFFIX, '')
    return prefix_dir


def _atomic_write_text(filename: str, content: str, encoding: str = "utf-8") -> None:
    """Write a text file without exposing a partially-written target.

    The temporary file is created next to the target so ``os.replace`` stays
    on the same filesystem. Flushing both the file and its directory makes
    the rename durable across a power loss on filesystems supporting fsync.
    """
    directory = os.path.dirname(os.path.abspath(filename)) or "."
    target_mode = 0o644
    try:
        target_mode = stat.S_IMODE(os.stat(filename).st_mode)
    except FileNotFoundError:
        pass

    fd, temporary = tempfile.mkstemp(
        prefix=f".{os.path.basename(filename)}.", suffix=".tmp", dir=directory
    )
    try:
        os.fchmod(fd, target_mode)
        with os.fdopen(fd, "w", encoding=encoding) as stream:
            fd = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, filename)
        temporary = None

        directory_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd is not None:
            os.close(fd)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


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
                    _atomic_write_text(
                        self.file,
                        json.dumps(self.data, indent=4, ensure_ascii=False),
                    )
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
    event_task_config = False
    file_instance = {}
    file_callback = {}  
    # 对外参数路径的统一顶层段，如 script.motorIoConfig.jackMaxHeight
    SCRIPT_PARAM_ROOT = "script"



    def __init__(self, script_file: str, callback: Callable[[], None] = None):

        if script_file is not None:
            script_file=_get_prefix_dir(script_file)
            self.config_file = prefix_dir + CONFIG_SUFFIX
            self.input_file = prefix_dir + INPUT_SUFFIX
            self.action_file = prefix_dir + ACTION_SUFFIX
        else:
            self.config_file = None
            self.input_file = None
            self.action_file = None
        self.config_full_params = {}
        self._actions = []
        self.__config_validator = None
        # 已注册的脚本参数读写方法名，避免重复注册
        self.__registered_methods = set()
        # 保护 config_full_params 的读改写，getScriptParam/setScriptParam 会被 RPC 线程调用
        self.__lock = threading.RLock()
        script_file=script_file.replace("/params","")
        ScriptParam.file_instance[script_file] = self
        if callback is not None:
            ScriptParam.file_callback[script_file] = callback
        self.script_file = script_file
        # 构造时已带配置变更回调（如 fork.py 这类由基类统一建实例的脚本），
        # 说明该脚本支持重载配置，直接注册 setScriptParam。
        # 否则只能靠 setConfigChangeCallBack() 注册，而该方法按调用栈定位实例，
        # 基类（fork.py）代为调用时拿到的是基类文件路径，匹配不到具体车型脚本的实例。
        if callback is not None:
            self._register_script_param_methods("setScriptParam")


    @classmethod
    def getInstance(cls,script_file: str = None) -> 'ScriptParam':
        script_file=script_file.replace(".py","")
        return ScriptParam.file_instance.get(script_file,None)

    def _register_script_param_methods(self, *method_names: str) -> None:
        """把本实例的脚本参数读写方法注册到 RPC 服务，重复调用只注册一次

        脚本无需显式调用注册接口：
        - 生成配置参数（调用 builderConfig()）时自动注册 getScriptParam；
        - 设置配置变更回调（调用 setConfigChangeCallBack()）时自动注册 setScriptParam。

        注册只写类级 RpcServer.FUNCS，Module.init() 启动服务时一次性上报，
        因此可以早于 Service.init() 调用；服务未就绪或注册失败时只记录日志，
        不影响脚本启动。
        """
        from syspy.lib.trace import Trace

        registered = self.__registered_methods
        todo = [name for name in method_names if name not in registered]
        if not todo:
            return

        try:
            server = Service.server()
        except Exception as error:
            Trace.log(f"register {todo} skipped: {error}", name="syspy.param")
            return

        for name in todo:
            function = getattr(self, name, None)
            if function is None:
                continue
            try:
                server.register_function(function, name, True)
            except Exception as error:
                Trace.log(f"register {name} failed: {error}", name="syspy.param")
                continue
            registered.add(name)

    def builderConfig(self):
        """创建配置参数构建器；调用即表明该脚本要生成配置参数

        同时自动注册 getScriptParam，使脚本不需要额外注册即可被 SPG 查询。
        """
        self._register_script_param_methods("getScriptParam")
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
        # 恢复任务时使用
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

    @staticmethod
    def _strip_script_prefix(path: str) -> str:
        """去掉参数路径顶层的 script 段，得到脚本内部的参数路径

        对外接口的参数路径统一以 script 开头（如
        script.motorIoConfig.jackMaxHeight），用于与设备、机型等其他参数
        命名空间区分；读写时忽略该段，脚本内部仍按 motorIoConfig.jackMaxHeight
        索引 config_full_params，不做任何转换。

        script 段之后可再接脚本名（如 script.straddleLiftFork.motorIoConfig.jackMaxHeight），
        该段仅用于对外标识，同样在解析时忽略，因此这里只剥掉最外层的 script 段。

        Args:
            path (str): 调用方传入的参数路径。

        Returns:
            str: 去掉 script 段后的参数路径（可能仍带脚本名段）。

        Raises:
            ValueError: 路径不以 script. 开头，或去掉后为空。
        """
        prefix = f"{ScriptParam.SCRIPT_PARAM_ROOT}."
        if not path.startswith(prefix):
            raise ValueError(
                f"param path must start with '{ScriptParam.SCRIPT_PARAM_ROOT}.', "
                f"got: {path}"
            )
        stripped = path[len(prefix):]
        if not stripped:
            raise ValueError("param path cannot be empty")
        return stripped

    def _resolve_inner_path(self, full_path: str) -> str:
        """把对外参数路径解析成 config_full_params 的内部键

        先按剥掉 script 段后的路径直接查；查不到且还剩至少两段时，再剥掉
        紧随其后的脚本名段重试。因此下面两种写法等价：
        - script.motorIoConfig.jackMaxHeight
        - script.straddleLiftFork.motorIoConfig.jackMaxHeight

        Args:
            full_path (str): 调用方传入的参数路径。

        Returns:
            str: config_full_params 的内部键。

        Raises:
            ValueError: 路径非法，或参数不存在。
        """
        stripped = self._strip_script_prefix(full_path)
        if stripped in self.config_full_params:
            return stripped

        segments = stripped.split('.')
        if len(segments) >= 2:
            without_script_name = '.'.join(segments[1:])
            if without_script_name in self.config_full_params:
                return without_script_name

        raise ValueError(f"Parameter not found: {full_path}")

    def _ensure_config_loaded(self) -> None:
        """确保配置参数已加载，未加载则读一次

        getScriptParam/setScriptParam 可能早于脚本自身的 loadConfig() 被调用，
        这里自动加载一次；仍加载不出内容（如配置文件缺失）时报错。
        调用方需已持有 self.__lock。

        Raises:
            RuntimeError: 配置参数无法加载。
        """
        if self.config_full_params:
            return
        try:
            self.loadConfig()
        except Exception as error:
            raise RuntimeError(f"Script config parameters are not loaded: {error}")
        if not self.config_full_params:
            raise RuntimeError("Script config parameters are not loaded")

    def _get_config_validator(self) -> 'ParamValidator':
        """获取配置参数定义校验器，优先复用 loadConfig() 已构建的实例"""
        if self.__config_validator is not None:
            return self.__config_validator
        if not self.config_file or not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        self.__config_validator = ParamValidator(config_data)
        return self.__config_validator

    def getScriptParam(self, params: Optional[List[str]] = None) -> Dict[str, Any]:
        """查询当前生效的脚本配置参数

        由 PyIDE 按脚本路由到本方法，因此不需要传入脚本路径。

        数据来源是内存中的 config_full_params，因此包含本次任务下发的临时覆盖；
        配置尚未加载时自动调用 loadConfig() 读一次，仍失败才报错。

        Args:
            params (Optional[List[str]]): 要查询的参数路径列表，点号分隔，顶层
                固定为 script（如 "script.motorIoConfig.jackMaxHeight"），
                其后可再接脚本名（如 "script.straddleLiftFork.motorIoConfig.jackMaxHeight"），
                两种写法等价。为空时返回全部配置参数。

        Returns:
            Dict[str, Any]: {params}，params 为 路径 -> 值 的字典。所有返回的键
                都带 script 前缀（如 "script.motorIoConfig.jackMaxHeight"），
                与传入 params 时的回显格式一致，可直接喂回 setScriptParam()。

        Raises:
            ValueError: 参数路径不以 script. 开头，或查询的参数不存在。
            RuntimeError: 脚本配置参数尚未加载。

        Examples:
        ```python
        from syspy import ScriptParam
        param_loader = ScriptParam(__file__)
        param_loader.getScriptParam(
            ["script.motorIoConfig.jackMaxHeight"],
        )
        # {"params": {"script.motorIoConfig.jackMaxHeight": 0.4}}

        # 不传 params 时返回全部，键同样带 script 前缀
        param_loader.getScriptParam()
        # {"params": {"script.motorIoConfig.jackMaxHeight": 0.4, ...}}
        ```
        """
        with self.__lock:
            self._ensure_config_loaded()

            if not params:
                # 全量与指定路径统一带 script 前缀，调用方无需区分两种形态
                root = self.SCRIPT_PARAM_ROOT
                result = {f"{root}.{key}": value
                          for key, value in self.config_full_params.items()}
            else:
                result = {}
                for name in params:
                    full_path = str(name).strip()
                    inner_path = self._resolve_inner_path(full_path)
                    result[full_path] = self.config_full_params[inner_path]

            return {"params": result}

    def setScriptParam(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """设置脚本配置参数，写入内存并落盘，随后通知脚本重新加载配置

        由 PyIDE 按脚本路由到本方法，因此不需要传入脚本路径。

        语义为"修改这个脚本的配置参数"：即使当前处于任务覆盖期间，改的也是
        配置参数本身——内存和配置文件同时更新，任务覆盖仍然优先生效。

        Args:
            params (Dict[str, Any]): 参数路径 -> 新值。键为点号分隔的完整路径，
                顶层固定为 script（如 "script.motorIoConfig.jackMaxHeight"），
                其后可再接脚本名（如 "script.straddleLiftFork.motorIoConfig.jackMaxHeight"），
                两种写法等价，读写时会忽略掉 script 与脚本名段；写入前按参数定义
                做类型与范围校验，任一参数非法则整体拒绝，不做部分写入。

        Returns:
            Dict[str, Any]: {applied, persisted}，applied 为
                路径 -> {old, new} 的改动明细，键与传入的 params 一致。

        Raises:
            ValueError: 参数路径不以 script. 开头、params 为空或非字典、
                路径不存在、参数只读，或取值校验失败。
            RuntimeError: 脚本配置参数无法加载。

        Examples:
        ```python
        from syspy import ScriptParam
        param_loader = ScriptParam(__file__)
        param_loader.setScriptParam(
            {"script.motorIoConfig.jackMaxHeight": 0.5},
        )
        ```
        """
        if not params or not isinstance(params, dict):
            raise ValueError("params must be a non-empty dict of path -> value")

        with self.__lock:
            self._ensure_config_loaded()

            validator = self._get_config_validator()
            param_index = validator.param_index

            applied: Dict[str, Any] = {}
            # 对外回显路径（含 script 段） -> 脚本内部路径，落盘与内存都用内部路径
            echo_paths: Dict[str, str] = {}
            # 先整体校验，全部通过后再写入，保证不会只改一半
            for name, value in params.items():
                full_path = str(name).strip()
                inner_path = self._resolve_inner_path(full_path)

                param_def = self._resolve_param_def(param_index, inner_path, full_path)
                if param_def.get('isReadOnly') or param_def.get('permission'):
                    raise ValueError(f"Parameter is read-only: {full_path}")

                validated_value = validator._validate_single(param_def, value, full_path)
                echo_paths[full_path] = inner_path
                applied[inner_path] = {
                    "old": self.config_full_params.get(inner_path),
                    "new": validated_value,
                }

            # 先落盘，成功后再改内存；盘上失败则内存不会出现“新值但未持久化”的割裂态
            persisted = self._persist_config_values(applied)
            for inner_path, change in applied.items():
                self.config_full_params[inner_path] = change["new"]

            # 通知脚本重新加载配置
            self._notify_config_changed()

            return {
                "applied": {
                    echo_path: applied[inner_path]
                    for echo_path, inner_path in echo_paths.items()
                },
                "persisted": persisted,
            }

    def _resolve_param_def(
            self,
            param_index: Dict[str, Dict[str, Any]],
            path: str,
            display_path: str = None,
    ) -> Dict[str, Any]:
        """按完整路径或叶子 key 解析参数定义，叶子 key 有歧义时报错

        Args:
            param_index (Dict[str, Dict[str, Any]]): 参数定义索引，键为脚本内部路径。
            path (str): 脚本内部的参数路径（已去掉 script 段）。
            display_path (str): 用于报错的路径，默认与 path 相同；外部接口应传入
                调用方原样的路径，使报错信息与调用方入参一致。
        """
        shown = display_path or path
        param_def = param_index.get(path)
        if param_def is not None and param_def.get('type'):
            if param_def.get('type') == ParamType.ARRAY:
                raise ValueError(f"Parameter is a group, not a value node: {shown}")
            return param_def

        if '.' not in path:
            raise ValueError(f"Parameter not found: {shown}")

        leaf_key = path.rsplit('.', 1)[-1]
        candidates = {
            id(defined): defined
            for indexed_path, defined in param_index.items()
            if defined.get('type')
            and defined.get('type') != ParamType.ARRAY
            and indexed_path.endswith('.' + leaf_key)
        }
        if not candidates:
            raise ValueError(f"Parameter not found: {shown}")
        if len(candidates) > 1:
            raise ValueError(
                f"Ambiguous parameter path: {shown}. "
                "Use the full dotted path (script.group.param)"
            )
        return next(iter(candidates.values()))

    def _persist_config_values(self, applied: Dict[str, Dict[str, Any]]) -> bool:
        """把新值写回配置文件叶子节点并原子落盘

        每次落盘都重新读盘，避免用可能已过期的定义缓存覆盖盘上的其他改动。

        Returns:
            bool: 是否已写入配置文件。
        """
        if not self.config_file:
            return False

        definition: Dict[str, Any] = {}
        if os.path.exists(self.config_file) and os.path.getsize(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                definition = json.load(f)

        touched = False
        for full_path, change in applied.items():
            if self._set_defined_value(definition, full_path.split('.'), change["new"]):
                touched = True

        if not touched:
            return False

        _atomic_write_text(
            self.config_file,
            json.dumps(definition, indent=2, ensure_ascii=False),
        )
        return True

    @staticmethod
    def _set_defined_value(definition: Dict[str, Any], segments: List[str], value: Any) -> bool:
        """按路径在配置定义树中就地更新叶子节点的值

        顶层为 groups 列表；只有定义了 type 且非 array 的节点才是真正的参数，
        分组/数组父节点不写值，避免把标量写进 groups 造成定义损坏。
        """
        node: Dict[str, Any] = {"children": definition.get('groups', [])}
        for index, segment in enumerate(segments):
            children = node.get('children')
            if not isinstance(children, list):
                return False
            node = next(
                (child for child in children if isinstance(child, dict) and child.get('key') == segment),
                None,
            )
            if node is None:
                return False
            if index == len(segments) - 1:
                if not node.get('type') or node.get('type') == ParamType.ARRAY:
                    return False
                node['value'] = value
                return True
        return False

    def _notify_config_changed(self) -> None:
        """通知脚本配置已改变，回调不存在时只记录日志"""
        from syspy.lib.trace import Trace
        Trace.log("setScriptParam()", name="syspy.param")
        callback = ScriptParam.file_callback.get(self.script_file)
        if callback:
            callback()

    @classmethod
    def setConfigChangeCallBack(cls, callback: Callable[[], None]):
        """设置脚本配置参数改变回调

        同时自动注册 setScriptParam，使脚本不需要额外注册即可被 SPG 修改；
        按调用者所在文件定位实例，因此需先创建 ScriptParam(__file__)。

        Args:
            callback (Callable[[], None]): 回调方法
        """
        caller_frame = stack()[1]
        caller_file = caller_frame.filename.replace(".py","")
        ScriptParam.file_callback[caller_file] = callback
        Service.server().register_function(callback, "script_config_changed", True)
        instance = ScriptParam.file_instance.get(caller_file)
        if instance is not None:
            instance._register_script_param_methods("setScriptParam")

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
            from syspy.lib.trace import Trace
            Trace.log("setTaskConfig()", name="syspy.param")
            if not self.config_full_params:
                self.config_full_params = config_data
            else:
                self.config_full_params.update(config_data)
                ScriptParam.event_task_config = True
                call_path = ScriptParam.file_callback.get(self.script_file)
                if call_path:
                    call_path()

    def clearTaskConfig(self):
        """恢复任务配置参数"""
        if ScriptParam.event_task_config:
            ScriptParam.event_task_config = False
            call_path = ScriptParam.file_callback.get(self.script_file)
            if call_path:
                from syspy.lib.trace import Trace
                Trace.log("clearTaskConfig()", name="syspy.param")
                call_path()

    def addAction(self, action_name: str,
                policy: Dict[str, Any] = None,
                args: Dict[str, Any] = None,
                config: Dict[str, Any] = None,
                stage: int = 2) -> Dict[str, Any]:
        """添加动作

        Args:
            action_name (str): 动作名称，如 "forkLoad", "forkUnLoad"
            policy (Dict[str, Any]): 策略配置
            args (Dict[str, Any]): 脚本任务参数
            config (Dict[str, Any]): 脚本配置参数
            stage (int): 脚本执行阶段。
                0 = 在前置点执行脚本, 脚本完成后开始导航;
                1 = 在前置点执行脚本, 脚本和导航同时运行;
                2 = 在目标点执行脚本
                3 = 在前置点执行脚本, 后续导航由脚本控制

        Returns:
            Dict[str, Any]: 动作示例数据结构

        Examples:
        ```python
        from syspy import ScriptParam
        param_loader = ScriptParam(__file__)
        # 添加 "load" 动作
        param_loader.addAction(
            action_name="load",
            policy={"goodsDir": 90},
            args={
                "operation": "load",
                "operation.load.height": 0.02,
            },
            config={"load.recognize": "on"},
            stage=3
        )
        ```
        """
        action_value = {
            "policy": policy or {},
            "script": {
                "name": script_dir,
                "args": args or {},
                "config": config or {},
                "stage": stage
            }
        }

        action = {
            "name": action_name,
            "value": action_value
        }
        self._actions.append(action)

        return action


    def saveAction(self) -> None:
        """保存动作到文件

        Examples:
        ```python
        from syspy import ScriptParam
        param_loader = ScriptParam(__file__)
        # 添加动作
        ...
        # 保存动作到文件
        param_loader.saveAction()
        Notice:
            调用前需要先调用 addAction() 方法添加动作
        ```
        """
        tasks_file_data = {}
        if os.path.exists(self.action_file) and os.path.getsize(self.action_file):
            with open(self.action_file, 'r', encoding='utf-8') as f:
                tasks_file_data = json.load(f)

        tasks_file_data["standard"] = self._actions

        _atomic_write_text(
            self.action_file,
            json.dumps(tasks_file_data, indent=4, ensure_ascii=False),
        )


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


class _BindTypeStr:
    """工厂方法返回的绑定类型，用于路径类绑定（device-item, app-item, app-item-self, script）"""
    __slots__ = ('value',)

    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value


class _BindStrEnum(str, Enum):
    """确保 str() 返回枚举值，兼容 Python 3.11+"""
    def __str__(self) -> str:
        return self.value


class BindType:
    """绑定类型常量

    Examples:
        # 使用枚举常量（单项绑定）
        BINDTYPE(BindType.Device.CAMERA)
        BINDTYPE(BindType.Device.CAMERA, multiple=True)

        # 使用工厂方法（路径类绑定）
        BINDTYPE(BindType.device_item("Model.moduleType.jackWithSpin.moduleScript"))
        BINDTYPE(BindType.app_item("control.trigger"))

        # 使用 BindItem 构建复杂绑定
        BINDTYPE(BindItem(BindType.Device.CAMERA) + BindItem(BindType.Device.LASER, multiple=True))
    """

    class Device(_BindStrEnum):
        DI = "device:DI"
        DI_SENSOR = "device:DISensor"
        DO = "device:DO"
        DO_MOTOR = "device:DOMotor"
        GNSS = "device:GNSS"
        AD_COLLISION_SENSOR = "device:AdCollisionSensor"
        BATTERY = "device:Battery"
        BUMPER = "device:Bumper"
        CHARGER = "device:Charger"
        CHARGING_PORT = "device:ChargingPort"
        CONTROLLER = "device:Controller"
        DISTANCE_SENSOR = "device:DistanceSensor"
        ENCODER = "device:Encoder"
        ETHERCAT_IO = "device:EthercatIO"
        MESH_MODULE = "device:MeshModule"
        MAGNETIC_SENSOR = "device:MagneticSensor"
        MODBUS_TCP = "device:ModbusTCP"
        CODE_SCANNER = "device:CodeScanner"
        SCREEN = "device:Screen"
        RFID_SENSOR = "device:RFIDSensor"
        OPTICAL_MOTION_CAPTURE = "device:OpticalMotionCapture"
        WEIGHING_DEV = "device:WeighingDev"
        RADIO = "device:Radio"
        RFID = "device:RFID"
        SERIAL_INTERFACE = "device:SerialInterface"
        TILT_SENSOR = "device:TiltSensor"
        MANIPULATORS = "device:Manipulators"
        GRIPPER = "device:Gripper"
        GAS_SENSOR = "device:GasSensor"
        FORCE_SENSOR = "device:ForceSensor"
        CAN = "device:CAN"
        MOTOR = "device:Motor"
        LASER = "device:Laser"
        CAMERA = "device:Camera"
        CHASSIS = "device:Chassis"
        MODEL = "device:Model"
        SONIC = "device:Sonic"
        INDICATOR = "device:Indicator"
        COLLISION_SENSOR = "device:CollisionSensor"
        LED = "device:LED"
        IMU = "device:IMU"
        MODBUS_IO = "device:ModbusIO"
        JOYSTICK = "device:Joystick"
        FIRMWARE = "device:Firmware"

    class App(_BindStrEnum):
        CONTROL = "app:control"
        FUNCTIONAL_SAFETY = "app:functionalSafety"
        LOCALIZATION = "app:localization"
        NAVIGATION = "app:navigation"
        RECOGNITION = "app:recognition"
        POWER = "app:power"

    class Shape(_BindStrEnum):
        RECTANGLE = "shape:rectangle"
        POLYGON = "shape:polygon"
        CIRCLE = "shape:circle"
        POLYLINE = "shape:polyline"

    class Map(_BindStrEnum):
        MARK = "map:mark"
        PATH = "map:path"
        LOCATION = "map:location"
        AREA = "map:area"

    class Script(_BindStrEnum):
        GENERIC = "script:generic"
        TASKS = "script:tasks"

    class Audio(_BindStrEnum):
        FILE = "audio:file"

    class BackgroundItem(_BindStrEnum):
        CHASSIS = "background-item:chassis"
        CARRIER = "background-item:carrier"
        CHARGER = "background-item:charger"

    class LocalFile(_BindStrEnum):
        CONTENT = "local-file:content"

    class RbkMap(_BindStrEnum):
        FILE_NAME = "rbk-map:fileName"

    class UrdfItem(_BindStrEnum):
        JOINT = "urdf-item:joint"

    @staticmethod
    def device_item(path: str) -> _BindTypeStr:
        """绑定设备模型中某个参数的值

        Args:
            path: 参数路径，如 "Model.moduleType.jackWithSpin.moduleScript"
        """
        if not path:
            raise ValueError("device-item path cannot be empty")
        return _BindTypeStr(f"device-item:{path}")

    @staticmethod
    def app_item(path: str) -> _BindTypeStr:
        """绑定参数配置中当前文件中参数的值

        Args:
            path: 参数路径，如 "control.trigger"
        """
        if not path:
            raise ValueError("app-item path cannot be empty")
        return _BindTypeStr(f"app-item:{path}")

    @staticmethod
    def app_item_self(path: str) -> _BindTypeStr:
        """绑定参数配置中当前文件中自身参数的值

        Args:
            path: 参数路径，如 "moduleType.jackWithSpin.moduleScript"
        """
        if not path:
            raise ValueError("app-item-self path cannot be empty")
        return _BindTypeStr(f"app-item-self:{path}")

    @staticmethod
    def script(path: str) -> _BindTypeStr:
        """绑定脚本目录下的相对路径

        Args:
            path: 相对路径，如 "generic", "generic/battery"
        """
        if not path:
            raise ValueError("script path cannot be empty")
        return _BindTypeStr(f"script:{path}")


# 各分类允许的属性
_BIND_ATTR_RULES: Dict[str, set] = {
    "device": {"multiple", "no-empty"},
    "device-item": {"no-empty"},
    "app": {"multiple", "no-empty"},
    "app-item": {"no-empty"},
    "app-item-self": {"no-empty"},
    "audio": {"multiple"},
    "shape": {"multiple", "no-rotate", "no-empty"},
    "map": {"multiple"},
    "script": {"multiple", "no-empty"},
    "background-item": {"no-empty"},
    "local-file": set(),
    "rbk-map": set(),
    "urdf-item": {"no-empty"},
}

# 所有有效的绑定枚举类型
_VALID_BIND_ENUMS = (
    BindType.Device, BindType.App, BindType.Shape, BindType.Map,
    BindType.Script, BindType.Audio, BindType.BackgroundItem,
    BindType.LocalFile, BindType.RbkMap, BindType.UrdfItem
)

# BINDTYPE 可接受的类型（枚举 + 工厂方法返回值）
_VALID_BIND_TYPES = _VALID_BIND_ENUMS + (_BindTypeStr,)


class BindItem:
    """绑定项构建器，用于程序化构建复杂的 bind_type 字符串

    Args:
        type_value: BindType 枚举常量或工厂方法返回值
        multiple: 多选
        no_rotate: 禁止旋转（仅 shape 类型支持）
        no_empty: 禁止为空，保存时报错

    Examples:
        # 单个设备
        BindItem(BindType.Device.CAMERA)  # -> "device:Camera"

        # 多个激光
        BindItem(BindType.Device.LASER, multiple=True)  # -> "device:Laser multiple"

        # 组合: 一个相机 + 多个激光
        BindItem(BindType.Device.CAMERA) + BindItem(BindType.Device.LASER, multiple=True)
        # -> "device:Camera;device:Laser multiple"

        # 带属性的形状
        BindItem(BindType.Shape.POLYGON, multiple=True, no_empty=True)
        # -> "shape:polygon multiple no-empty"

        # 形状 + 背景
        BindItem(BindType.Shape.POLYGON) + BindItem(BindType.BackgroundItem.CHASSIS)
        # -> "shape:polygon;background-item:chassis"
    """

    def __init__(self, type_value, *,
                 multiple: bool = False,
                 no_rotate: bool = False,
                 no_empty: bool = False):
        if not isinstance(type_value, _VALID_BIND_TYPES):
            raise TypeError(
                f"Invalid bind type: {type_value!r}. "
                "Use BindType enum constants (e.g. BindType.Device.CAMERA) "
                "or BindType factory methods (e.g. BindType.device_item('...'))."
            )

        if isinstance(type_value, _BindTypeStr):
            self.type_value = type_value.value
        else:
            self.type_value = type_value.value  # enum .value

        self._category = self.type_value.split(":")[0]

        # 校验属性是否允许
        allowed = _BIND_ATTR_RULES.get(self._category, set())
        if multiple and "multiple" not in allowed:
            raise ValueError(f"'{self._category}' category does not support 'multiple'")
        if no_rotate and "no-rotate" not in allowed:
            raise ValueError(f"'{self._category}' category does not support 'no_rotate'")
        if no_empty and "no-empty" not in allowed:
            raise ValueError(f"'{self._category}' category does not support 'no_empty'")

        self.multiple = multiple
        self.no_rotate = no_rotate
        self.no_empty = no_empty

    def __str__(self) -> str:
        parts = [self.type_value]
        if self.multiple:
            parts.append("multiple")
        if self.no_rotate:
            parts.append("no-rotate")
        if self.no_empty:
            parts.append("no-empty")
        return " ".join(parts)

    def __add__(self, other):
        if isinstance(other, BindItem):
            return _BindExpr([self, other])
        if isinstance(other, _BindExpr):
            return _BindExpr([self] + other._items)
        return NotImplemented


class _BindExpr:
    """BindItem 组合表达式（由 BindItem + BindItem 产生）"""

    def __init__(self, items: List[BindItem]):
        self._items = items

    def __add__(self, other):
        if isinstance(other, BindItem):
            return _BindExpr(self._items + [other])
        if isinstance(other, _BindExpr):
            return _BindExpr(self._items + other._items)
        return NotImplemented

    def __str__(self) -> str:
        return ";".join(str(item) for item in self._items)


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
        return {k: v for k, v in result.items() if v not in (None, []) and not (isinstance(v, list) and not v)}

# 输入参数和配置参数枚举
_COMBO_TYPES_REQUIRE_DEFAULT = {ParamType.STRING_COMBO_LIST, ParamType.COMBO_BOX_BOOL}
_VALID_COMBO_BOOL_KEYS = {"on", "off"}


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
        # COMBO_BOX_BOOL 子级 key 只能是 "on" 或 "off"
        if self._current_node and self._current_node.type == ParamType.COMBO_BOX_BOOL:
            if key not in _VALID_COMBO_BOOL_KEYS:
                raise ValueError(
                    f"Child key '{key}' of comboBoxBool parameter '{self._current_node.key}' "
                    f"must be one of {_VALID_COMBO_BOOL_KEYS}"
                )
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
            if child.type in _COMBO_TYPES_REQUIRE_DEFAULT and child.default_value is None:
                raise ValueError(
                    f"Parameter '{key}' of type '{child.type}' must have a default value (set via DEFAULTVALUE())"
                )
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
        if self._current_node and self._current_node.type == ParamType.COMBO_BOX_BOOL:
            if value not in _VALID_COMBO_BOOL_KEYS:
                raise ValueError(
                    f"comboBoxBool parameter '{self._current_node.key}' "
                    f"defaultValue must be one of {_VALID_COMBO_BOOL_KEYS}, got '{value}'"
                )
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

    def BINDTYPE(self, value, *,
                 multiple: bool = False,
                 no_rotate: bool = False,
                 no_empty: bool = False) -> None:
        """绑定类型到字段

        Args:
            value: 绑定类型，支持：
                - BindType 枚举常量 (如 BindType.Device.CAMERA)
                - BindType 工厂方法返回值 (如 BindType.device_item("..."))
                - BindItem 对象
                - BindItem 组合表达式 (如 BindItem(...) + BindItem(...))
            multiple: 是否多选（仅在 value 为枚举或工厂方法时有效）
            no_rotate: 是否禁止旋转（仅在 value 为枚举或工厂方法时有效）
            no_empty: 是否禁止为空（仅在 value 为枚举或工厂方法时有效）

        Examples:
            # 设备绑定
            builder.BINDTYPE(BindType.Device.CAMERA)                            # 绑定一个相机
            builder.BINDTYPE(BindType.Device.CAMERA, multiple=True)             # 绑定多个相机
            builder.BINDTYPE(BindType.device_item("Model.moduleType.jackWithSpin.moduleScript"))

            # 组合绑定（使用 BindItem）
            builder.BINDTYPE(                                                   # 一个相机 + 多个激光
                BindItem(BindType.Device.CAMERA)
                + BindItem(BindType.Device.LASER, multiple=True)
            )

            # 参数配置绑定
            builder.BINDTYPE(BindType.App.RECOGNITION)                          # 一个识别文件
            builder.BINDTYPE(BindType.App.RECOGNITION, multiple=True)           # 多个识别文件
            builder.BINDTYPE(BindType.app_item("control.trigger"))
            builder.BINDTYPE(BindType.app_item_self("moduleType.jackWithSpin.moduleScript"))

            # 音频绑定
            builder.BINDTYPE(BindType.Audio.FILE)                               # 一个音频
            builder.BINDTYPE(BindType.Audio.FILE, multiple=True)                # 多个音频

            # 形状绑定
            builder.BINDTYPE(BindType.Shape.RECTANGLE)                          # 单个矩形
            builder.BINDTYPE(BindType.Shape.POLYGON, no_rotate=True)            # 禁止旋转
            builder.BINDTYPE(BindType.Shape.POLYGON, multiple=True, no_empty=True)  # 多个，禁止为空
            builder.BINDTYPE(                                                   # 多边形 + 底盘背景
                BindItem(BindType.Shape.POLYGON)
                + BindItem(BindType.BackgroundItem.CHASSIS)
            )

            # 图元绑定
            builder.BINDTYPE(BindType.Map.MARK)                                 # 站点
            builder.BINDTYPE(BindType.Map.MARK, multiple=True)                  # 多个站点
            builder.BINDTYPE(BindItem(BindType.Map.MARK) + BindItem(BindType.Map.PATH))  # 多种图元

            # 脚本绑定
            builder.BINDTYPE(BindType.Script.GENERIC)                           # 设备文件夹脚本
            builder.BINDTYPE(BindType.script("generic/battery"))                # 电池文件夹脚本

            # 其他
            builder.BINDTYPE(BindType.LocalFile.CONTENT)                        # 本地文件
            builder.BINDTYPE(BindType.RbkMap.FILE_NAME)                         # rbk 地图文件
            builder.BINDTYPE(BindType.UrdfItem.JOINT)                           # URDF 关节
        """
        has_attrs = multiple or no_rotate or no_empty

        if isinstance(value, (_BindExpr, BindItem)):
            if has_attrs:
                raise ValueError(
                    "multiple/no_rotate/no_empty cannot be used with BindItem or combined expressions. "
                    "Set attributes on individual BindItem objects instead."
                )
            self.ADD_FIELD("bind_type", str(value))
        elif isinstance(value, _VALID_BIND_TYPES):
            item = BindItem(value, multiple=multiple, no_rotate=no_rotate, no_empty=no_empty)
            self.ADD_FIELD("bind_type", str(item))
        else:
            raise TypeError(
                f"Invalid bind type: {value!r}. "
                "Use BindType enum constants (e.g. BindType.Device.CAMERA), "
                "BindType factory methods (e.g. BindType.device_item('...')), "
                "or BindItem objects."
            )

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
        _atomic_write_text(filename, self.toJson(indent))

    def save(self, merge: bool = False) -> None:
        """将配置保存到文件

        Args:
            merge (bool): 是否和原参数文件合并。True：按新定义重建并保留可兼容 value；False：替换。
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
            _atomic_write_text(
                filename,
                json.dumps(merged_data, ensure_ascii=False, indent=2),
            )
        else:
            # 直接保存新数据
            _atomic_write_text(filename, self.toJson(2))

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
        1. 以新定义为准，输出结构与新定义一一对应（自动删除已废弃参数）
        2. 同 key 参数若类型不变，则保留旧 value
        3. 同 key 参数若类型变化，则 value 重置为新定义中的默认值
        """
        new_data = self.toDict()
        merged_groups = self._merge_children(
            existing_data.get("groups", []),
            new_data.get("groups", [])
        )
        return {"desc": new_data.get("desc", ""), "groups": merged_groups}

    @staticmethod
    def _get_node_default_value(node: Dict[str, Any]) -> Tuple[bool, Any]:
        """获取节点在代码定义中的默认值（defaultValue 优先，其次 value）"""
        if "defaultValue" in node:
            return True, node.get("defaultValue")
        if "value" in node:
            return True, node.get("value")
        return False, None

    def _merge_node_value(self, existing_node: Dict[str, Any], merged_node: Dict[str, Any]) -> None:
        """按类型规则合并单节点 value"""
        existing_type = existing_node.get("type")
        merged_type = merged_node.get("type")

        # 仅对有类型定义的参数节点处理 value，分组节点不处理
        if not existing_type or not merged_type:
            return

        if existing_type == merged_type:
            # 类型不变：保留旧 value（如果存在）
            if "value" in existing_node:
                merged_node["value"] = existing_node.get("value")
            return

        # 类型变化：重置为代码默认值；若无默认值则移除旧 value
        has_default, default_value = self._get_node_default_value(merged_node)
        if has_default:
            merged_node["value"] = default_value
        else:
            merged_node.pop("value", None)


    def _merge_children(self, existing_children: List[Dict[str, Any]], new_children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按新定义顺序合并子参数列表（不保留新定义外的旧参数）"""
        existing_map = {
            child.get("key"): child
            for child in existing_children
            if isinstance(child, dict) and child.get("key")
        }
        merged_children = []

        for new_child in new_children:
            if not isinstance(new_child, dict):
                continue

            child_key = new_child.get("key")
            existing_child = existing_map.get(child_key, {})
            merged_child = dict(new_child)

            if existing_child:
                self._merge_node_value(existing_child, merged_child)

            if "children" in new_child:
                merged_child_children = self._merge_children(
                    existing_child.get("children", []),
                    new_child.get("children", [])
                )
                if merged_child_children:
                    merged_child["children"] = merged_child_children
                else:
                    merged_child.pop("children", None)

            merged_children.append(merged_child)

        return merged_children


class ParamValidator:
    """参数验证器，基于参数定义文件验证输入参数"""

    def __init__(self, param_definition: Dict[str, Any]):
        self.param_definition = param_definition
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

        # 处理 COMBO_BOX_BOOL 类型参数
        if param_type == ParamType.COMBO_BOX_BOOL:
            if isinstance(value, str) and value.lower() == "on":
                return True
            elif isinstance(value, str) and value.lower() == "off":
                return False

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
                        target_key_lower = "on" if bool_value else "off"
                        # 查找对应分支并验证（大小写不敏感匹配）
                        for child in param_def.get('children', []):
                            if child['key'].lower() == target_key_lower:
                                should_validate_children = True
                                validate_all_params([child], full_path)
                                # 同时验证该分支下的所有子参数
                                self._validate_combo_bool_children(child, input_params, validated_params, errors, full_path + "." + child['key'])
                                break
                    else:
                        # 默认情况：检查是否在输入参数中或是否为必填项
                        in_input = False
                        for key in input_params.keys():
                            if key.lower().startswith(full_path.lower()) or param_def['key'] in str(input_params.get(key, '')):
                                in_input = True
                        if in_input or (not in_input and param_def.get('required', False) == True):
                            should_validate_children = True
                            validate_all_params(param_def['children'], full_path)

                    # 如果没有特殊处理但有子参数需要验证
                    if not should_validate_children:
                        in_input = any(key.lower().startswith(full_path.lower()) for key in input_params.keys())
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
        def _get_ignore_case(params: Dict[str, Any], key: str):
            val = params.get(key)
            if val is not None:
                return val
            key_lower = key.lower()
            for k, v in params.items():
                if k.lower() == key_lower:
                    return v
            return None

        def validate_recursive(node_def: Dict[str, Any], current_path: str):
            node_key = node_def.get('key')
            full_path = f"{current_path}.{node_key}" if current_path else node_key
            # 如果该节点在输入参数中，则验证它
            direct_value = input_params.get(node_key)
            path_value = _get_ignore_case(input_params, full_path)

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

            elif param_type in (ParamType.BOOL, ParamType.COMBO_BOX_BOOL):
                validated_value = self._validate_bool(value, full_path)

            elif param_type == ParamType.STRING:
                validated_value = self._validate_string(value, param_def, full_path)

            elif param_type == ParamType.IP:
                validated_value = self._validate_ip(value, full_path)

            else:
                # 其他类型不做转换
                validated_value = value

            # 存储验证后的值
            validated_params[key] = validated_value

        except ValueError as e:
            errors.append(str(e))

    def _validate_single(self, param_def: Dict[str, Any], value: Any, full_path: str) -> Any:
        """按参数定义校验并转换单个值，不符合定义时抛 ValueError

        供 setScriptParam 在写入前做类型与范围校验，与 validate() 共用同一套
        转换规则，避免两处校验口径不一致。

        Args:
            param_def (Dict[str, Any]): 参数定义节点。
            value (Any): 待校验的值。
            full_path (str): 参数完整路径，仅用于报错。

        Returns:
            Any: 转换后的值。
        """
        param_type = param_def.get('type')
        if not param_type or param_type == ParamType.ARRAY:
            raise ValueError(f"Parameter is not a value node: {full_path}")

        if param_def.get('required', False) and value is None:
            raise ValueError(f"Missing required parameter: {full_path}")
        if value is None:
            return None

        if param_type in (ParamType.INT, ParamType.INT32, ParamType.INT64,
                          ParamType.UINT, ParamType.UINT32, ParamType.UINT64):
            return self._validate_number(value, param_type, param_def, full_path)
        if param_type in (ParamType.FLOAT, ParamType.DOUBLE):
            return self._validate_float(value, param_type, param_def, full_path)
        if param_type in (ParamType.BOOL, ParamType.COMBO_BOX_BOOL):
            return self._validate_bool(value, full_path)
        if param_type == ParamType.STRING:
            return self._validate_string(value, param_def, full_path)
        if param_type == ParamType.IP:
            return self._validate_ip(value, full_path)
        return value

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


def load_module_from_path(script_path: str) -> Any:
    module_name = os.path.splitext(os.path.basename(script_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    end_time = time.time()
    # 本函数在脚本参数生成期被调用，此时可能尚未建立 RBK RPC，因此不能用 Trace。
    print("gen_param time: ", end_time - start_time)
    return module


def gen_param(script_path: str):
    load_module_from_path(script_path)


if __name__ == '__main__':
    script_name = sys.argv[1]
    full_path = SCRIPTS_DIR + script_name  # 替换为你的脚本路径
    gen_param(full_path)
