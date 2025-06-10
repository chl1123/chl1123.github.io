import time
from functools import wraps
from typing import TypeVar, Generic, Union, Optional, List, Type

from google.protobuf.message import Message

T = TypeVar('T', bound=Message)


class Service:
    default_plugin = None
    _rpc_client = None

    @classmethod
    def client(cls):
        if cls._rpc_client is None:
            # log.debug("Lazy initializing RpcClient")
            from .rpc.client import RpcClient
            cls._rpc_client = RpcClient()
        return cls._rpc_client


class Message(Generic[T], Service):
    _TOPIC = None  # 消息名
    _PLUGIN = "RBKSim"  # 插件名
    _MODEL_CLASS: Type[T]  # Pydantic模型类

    data: T = None
    _last_update_time: float = 0.0  # 记录上次更新时间
    _update_time: float = 0.05  # 缓存时间，单位为秒

    @classmethod
    def set_update_time(cls, update_time: Union[float, int]):
        cls._update_time = update_time

    @classmethod
    def get_data(cls, args: Optional[List[str]] = None) -> Union[tuple, dict]:
        if cls.update():
            if args is not None:
                return tuple(getattr(cls.data, arg) for arg in args)
            from google.protobuf import json_format
            return json_format.MessageToDict(cls.data)

    @classmethod
    def init_model_class(cls):
        pass

    @classmethod
    def update(cls):
        """刷新状态"""
        if cls._MODEL_CLASS is None:
            cls.init_model_class()
        if cls.data is None or (time.time() - cls._last_update_time) > cls._update_time:
            response = cls.client().get_message(cls._TOPIC, cls._PLUGIN)
            if response:
                try:
                    from google.protobuf import json_format
                    cls.data = json_format.Parse(response, cls._MODEL_CLASS(), ignore_unknown_fields=True)
                    cls._last_update_time = time.time()  # 更新最后更新时间
                except Exception as e:
                    raise f"Error parsing response: {e}"
            else:
                # log.warning(f"{cls.__name__} message data is null")
                return False
        return True


def default_plugin(name=None):
    def decorator(cls):
        cls.default_plugin = name
        return cls

    return decorator


def call_service(plugin_name=None, func_name=None):
    def decorator(func):
        @wraps(func)
        def wrapper(cls, *args, **kwargs):
            # 使用提供的 plugin_name 或者从对象获取
            service_plugin = plugin_name or getattr(cls, "default_plugin")
            return cls.client().call_service(service_plugin, func_name or func.__name__, *args, **kwargs)

        return wrapper

    return decorator
