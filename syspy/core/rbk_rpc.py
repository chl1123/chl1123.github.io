import inspect
from functools import wraps

from syspy.config import RBK_VERSION
import json
from google.protobuf import message
from google.protobuf import json_format
from typing import Type, Optional, Any, Callable
import time


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

    def get_message(self, topic: str, model_class: Type[message.Message], plugin: str = "") -> Optional[message.Message]:
        raise NotImplementedError

    def call_service(self, plugin: str, method: str, *args, **kwargs) -> Any:
        raise NotImplementedError


class V3RpcClient(RpcClient):
    def __init__(self):
        from ..v3.rpc import client  # v3专用实现
        self._impl = client.RpcClient()

    def get_message(self, topic: str, model_class: Type[message.Message], plugin: str = "RBKSim") -> message.Message:
        response = self._impl.get_message(topic, plugin)
        return json_format.Parse(response, model_class())

    def call_service(self, plugin: str, method: str, *args, **kwargs) -> Any:
        return self._impl.call_service(plugin, method, *args)


class V4RpcClient(RpcClient):
    def __init__(self):
        from ..v4.include.rbk import datapool, service
        self.datapool = datapool
        self.service = service

    def get_message(self, topic: str, model_class: Type[message.Message], plugin = None) -> message.Message:
        return self.datapool.get(topic, model_class())

    def call_service(self, plugin: str, method: str, *args, **kwargs) -> Any:
        response = self.service.callService(plugin, method, request=kwargs)
        return tuple(json.loads(response.decode('utf-8'))) if response else None


class Service:
    _client: RpcClient = None

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


class Message(Service):
    _TOPIC: str = None  # 消息订阅主题
    _PLUGIN = "RBKSim"  # 消息发布插件-3.5
    _MODEL_CLASS: Type[message.Message] = None  # 消息模型类
    _UPDATE_INTERVAL: float = 0.05
    data: message.Message = None
    _last_update: float = 0.0

    def init_model_class(self):
        pass

    def set_update_interval(self, interval: float):
        self._UPDATE_INTERVAL = interval

    def update(self) -> bool:
        if self._MODEL_CLASS is None:
            self.init_model_class()
        """获取最新数据，返回是否更新成功"""
        if not self._requires_update():
            return bool(self.data)
        try:
            self.data = Service.client().get_message(
                self._TOPIC,
                self._MODEL_CLASS,
                self._PLUGIN
            )
            if not self.data:
                return False
            self._last_update = time.time()
            return True
        except Exception as e:
            # 添加日志记录
            return False

    def _requires_update(self) -> bool:
        """检查是否需要更新"""
        return (
                self.data is None or
                (time.time() - self._last_update) > self._UPDATE_INTERVAL
        )

    def get_data(self) -> Optional[message.Message]:
        """获取当前数据（不触发更新）"""
        return self.data


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