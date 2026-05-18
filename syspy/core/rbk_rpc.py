import inspect
from collections.abc import Callable
from functools import wraps

from syspy import RBK_VERSION
import json
from google.protobuf import message
from google.protobuf import json_format
from typing import Type, Optional, Any, List, Union, Dict
import time

from syspy.utils import ScriptType


class RBKVersionError(Exception):
    """RBK版本不兼容异常"""

    def __init__(self, func_name: str = None, message: str = None):
        """初始化异常

        Args:
            func_name (str): 不兼容的函数名。缺省时将自动从调用堆栈中提取。
        """
        if func_name is None:
            # 从调用堆栈中提取函数名（向上以层，跳过__init__）
            frame = inspect.currentframe()
            try:
                caller_frame = frame.f_back
                func_name = caller_frame.f_code.co_name
            finally:
                del frame

        self.func_name = func_name
        self.message = f"Function '{func_name}' is not supported in RBK version {RBK_VERSION}. {message}"
        super().__init__(self.message)


class RpcClient:
    """统一RPC客户端接口"""
    def __init__(self, script_id: str = "", script_type: ScriptType = ScriptType.GENERAL):
        self.script_id = script_id
        self.script_type = script_type

    def get_message(self, topic: str, model_class: Type[message.Message], plugin: str = "") -> Optional[message.Message]:
        raise NotImplementedError

    def call_service(self, plugin: str, method: str, *args, **kwargs) -> Any:
        raise NotImplementedError


class V3RpcClient(RpcClient):
    # get_message 路径选择：
    #   "json"  — 原 JSON-RPC + protobuf JSON 双重序列化（baseline）
    #   "raw"   — 独立 ZMQ 二进制通道，直传 protobuf binary（绕过 JSON-RPC 协议）
    _MODE: str = "raw"
    _bin_client = None  # lazy 初始化

    def __init__(self, script_id: str = "", script_type: ScriptType = ScriptType.GENERAL):
        super().__init__(script_id, script_type)
        from ..v3.lib.rpc import client  # v3专用实现
        self._impl = client.RpcClient(identity=script_id)
        self._script_id = script_id
        # 环境变量优先
        import os as _os
        env_mode = _os.environ.get("RBK_GETMSG_MODE", "").strip().lower()
        if env_mode in ("json", "raw"):
            V3RpcClient._MODE = env_mode

    def _get_bin_client(self):
        if V3RpcClient._bin_client is None:
            from ..v3.lib.rpc import client
            V3RpcClient._bin_client = client.BinMsgClient(identity=self._script_id)
        return V3RpcClient._bin_client

    def get_message(self, topic: str, model_class: Type[message.Message], plugin: str = "RBKSim") -> message.Message:
        # 纯二进制通道
        if V3RpcClient._MODE == "raw":
            try:
                bin_data = self._get_bin_client().get_message(topic, plugin)
                if bin_data is None:
                    raise RuntimeError("BinMsgClient timeout/error")
                if not bin_data:
                    return None
                msg = model_class()
                msg.ParseFromString(bin_data)
                return msg
            except Exception:
                V3RpcClient._MODE = "json"  # 降级
        else:
            V3RpcClient._MODE = "json"  # 降级

        response = self._impl.get_message(topic, plugin)
        return json_format.Parse(response, model_class(), ignore_unknown_fields=True)

    def call_service(self, plugin: str, method: str, *args, **kwargs) -> Any:
        return self._impl.call_service(plugin, method, *args)


class V4RpcClient(RpcClient):
    def __init__(self, script_id: str = "", script_type: ScriptType = ScriptType.GENERAL):
        super().__init__(script_id, script_type)
        from ..v4.lib.rbk import datapool, service
        self.datapool = datapool
        self.service = service

    def get_message(self, topic: str, model_class: Type[message.Message], plugin = None) -> message.Message:
        return self.datapool.get(topic, model_class())

    def call_service(self, plugin: str, method: str, *args, **kwargs) -> Any:
        response = self.service.callService(plugin, method, request=kwargs)
        return tuple(json.loads(response.decode('utf-8'))) if response else None


class RpcServer:
    def __init__(self, script_id: str, script_type: ScriptType = ScriptType.GENERAL):
        self.script_id = script_id
        self.script_type = script_type

    def register_function(self, function: Callable, method_name: str = "", is_immediately: bool = False):
        raise NotImplementedError

    def start(self):
        pass


class V3RpcServer(RpcServer):
    def __init__(self, script_id: str, script_type: ScriptType = ScriptType.GENERAL):
        super().__init__(script_id, script_type)
        from syspy.lib.rpc import server
        self.__service = server.RpcServer(script_id, script_type)

    def register_function(self, function: Callable, method_name: str = "", is_immediately: bool = False):
        self.__service.registerFunction(function, method_name, is_immediately)

    def start(self):
        self.__service.start()


class V4RpcServer(RpcServer):
    def __init__(self, script_id: str, script_type: ScriptType = ScriptType.GENERAL):
        super().__init__(script_id, script_type)
        from ..v4.lib.rbk import service
        self.__service = service

    def register_function(self, function: Callable, method_name: str = "", is_immediately: bool = True):
        if not method_name:
            method_name = function.__name__
        self.__service.addService(self.script_id, method_name, function)


class Service:
    _client: RpcClient = None
    _server: RpcServer = None
    _script_id: str = ""
    _script_type: ScriptType = ScriptType.GENERAL

    @classmethod
    def init(cls, script_id: str, script_type: ScriptType = ScriptType.GENERAL):
        cls._script_id = script_id
        cls._script_type = script_type
        if RBK_VERSION == 3:
            cls._client = V3RpcClient(script_id, script_type)
            cls._server = V3RpcServer(script_id, script_type)
        elif RBK_VERSION == 4:
            from syspy.v4.lib.rbk import core
            core.Init(script_id)
            cls._client = V4RpcClient(script_id, script_type)
            cls._server = V4RpcServer(script_id, script_type)
        else:
            raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

    @classmethod
    def client(cls) -> RpcClient:
        if not cls._client:
            cls._client = cls._create_client()
        return cls._client

    @classmethod
    def _create_client(cls) -> RpcClient:
        if RBK_VERSION == 3:
            return V3RpcClient()
        elif RBK_VERSION == 4:
            return V4RpcClient()
        raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

    @classmethod
    def server(cls) -> RpcServer:
        if not cls._server:
            cls._server = cls._create_server()
        return cls._server

    @classmethod
    def _create_server(cls) -> RpcServer:
        if RBK_VERSION == 3:
            return V3RpcServer(cls._script_id, cls._script_type)
        elif RBK_VERSION == 4:
            return V4RpcServer(cls._script_id, cls._script_type)
        raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")

class Message(Service):
    _TOPIC: str = ""  # 消息订阅主题
    _PLUGIN = "RBKSim"  # 消息发布插件-3.5
    _MODEL_CLASS: Type[message.Message] = None  # 消息模型类
    _UPDATE_INTERVAL: float = 0.05
    data: message.Message = None
    _last_update: float = 0.0

    def __init__(self, topic_prefix: str = "", topic_suffix: str = ""):
        self._TOPIC_PREFIX = topic_prefix
        self._TOPIC_SUFFIX = topic_suffix
        # 为每个topic维护独立的数据和更新时间
        self._topic_data: Dict[str, message.Message] = {}  # 存储每个topic的数据
        self._topic_last_update: Dict[str, float] = {}  # 存储每个topic的最后更新时间

    def initModelClass(self):
        pass

    def setUpdateInterval(self, interval: float = 0.05):
        """设置消息更新间隔。

        Args:
            interval (float): 间隔时间，单位 s。多次调用消息时，间隔时间大于 interval 才会更新消息。
        """
        self._UPDATE_INTERVAL = interval

    def update(self, topic: str = None) -> bool:
        if self._MODEL_CLASS is None:
            self.initModelClass()

        """获取最新数据，返回是否更新成功"""
        full_topic = self._TOPIC_PREFIX + (topic or self._TOPIC) + self._TOPIC_SUFFIX
        if not self._requires_update(topic):
            if topic is None:
                return bool(self.data)
            else:
                return bool(self._topic_data.get(topic))
        try:
            data = Service.client().get_message(
                full_topic,
                self._MODEL_CLASS,
                self._PLUGIN
            )
            if not data:
                return False
            # 为该topic存储数据和更新时间
            if topic is None:
                self.data = data
                self._last_update = time.time()
            else:
                self._topic_data[topic] = data
                self._topic_last_update[topic] = time.time()
            return True
        except Exception as e:
            # 添加日志记录
            return False

    def _requires_update(self, topic: str = None) -> bool:
        """检查指定topic是否需要更新"""
        if topic is None:
            last_update = self._last_update
            data = self.data
        else:
            last_update = self._topic_last_update.get(topic, 0)
            data = self._topic_data.get(topic)
        return (
                data is None or
                (time.time() - last_update) > self._UPDATE_INTERVAL
        )

    def getData(self, fields: Optional[List[str]] = None, *, topic: str = None) -> dict:
        """通用获取消息接口

        Args:
            fields (Optional[List[str]]): 需要的字段列表。缺省或 None 返回全部字段。
            topic (str): 指定消息话题。

        Returns:
            (dict): 包含请求字段的字典数据。
        """
        if self.update(topic):
            if topic is None:
                data = self.data
            else:
                data = self._topic_data.get(topic)
            if data:
                data_dict = json_format.MessageToDict(data, preserving_proto_field_name=True, use_integers_for_enums=True)
                if fields:
                    result = {}
                    for field in fields:
                        if field in data_dict:
                            result[field] = data_dict[field]
                    return result
                return data_dict
        return {}


def default_plugin(name=None):
    def decorator(self):
        self.default_plugin = name
        return self

    return decorator


def call_service(plugin_name=None, func_name=None):
    def decorator(func):
        @wraps(func)
        def wrapper(cls, *args, **kwargs):
            # 使用提供的 plugin_name 或者从对象获取
            service_plugin = plugin_name or getattr(cls, "default_plugin")
            # 获取函数参数名（排除 cls）
            func_params = func.__code__.co_varnames[1:func.__code__.co_argcount]

            if RBK_VERSION == 3:
                # RBK3：将 kwargs 转为位置参数，合并到 args
                merged_args = list(args)
                for i, name in enumerate(func_params):
                    if name in kwargs:
                        if i < len(merged_args):
                            merged_args[i] = kwargs[name]  # 替换已有的位置参数
                        else:
                            merged_args.append(kwargs[name])  # 补充新的位置参数
                return cls.client().call_service(service_plugin, func_name or func.__name__, *merged_args)

            elif RBK_VERSION == 4:
                # RBK4：将 args 转为关键字参数，合并到 kwargs
                args_as_kwargs = {name: args[i] for i, name in enumerate(func_params) if i < len(args)}
                merged_kwargs = {**args_as_kwargs, **kwargs}
                return cls.client().call_service(service_plugin, func_name or func.__name__, **merged_kwargs)

        return wrapper

    return decorator