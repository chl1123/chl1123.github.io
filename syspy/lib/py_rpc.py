import inspect
import json
import time
from functools import wraps
from typing import Optional, Type, TypeVar, Generic, Union, List

from pydantic import BaseModel

from .logger import log
from .rpc.client import rpcClient

T = TypeVar('T', bound=BaseModel)


class Service:
    default_plugin = None
    rpc_client = rpcClient()


class Message(Generic[T], Service):
    _TOPIC = None  # 消息名
    _PLUGIN = "RBKSim"  # 插件名
    _MODEL_CLASS: Type[T]  # Pydantic模型类

    data: T
    _last_update_time: float = 0.0  # 记录上次更新时间
    _update_time: float = 0.05  # 缓存时间，单位为秒

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 初始化时创建默认数据对象
        cls.data = cls._MODEL_CLASS()

    @classmethod
    def set_update_time(cls, update_time: Union[float, int]):
        cls._update_time = update_time

    @classmethod
    def get_data(cls, args: Optional[List[str]] = None) -> Union[tuple, dict]:
        if cls.update():
            if args is not None:
                return tuple(getattr(cls.data, arg) for arg in args)
            return cls.data.model_dump()

    @classmethod
    def update(cls):
        """刷新状态"""
        if cls.data is None or (time.time() - cls._last_update_time) > cls._update_time:
            response = cls.rpc_client.get_message(cls._TOPIC, cls._PLUGIN)
            if response:
                try:
                    parsed_data = json.loads(response)
                    cls.data = cls._MODEL_CLASS(**parsed_data)
                    cls._last_update_time = time.time()  # 更新最后更新时间
                except Exception as e:
                    log.error(f"Error parsing response: {e}")
                    return False
            else:
                log.warning(f"{cls.__name__} message data is null")
                return False
        return True


def get_function_name():
    """
    获取正在运行函数(或方法)名称
    """
    return inspect.stack()[1][3]


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
            # 调用原始函数
            result = func(cls, *args, **kwargs)
            # 判断是否为 rpcClient 类的实例
            if hasattr(cls, "rpc_client") and isinstance(cls.rpc_client, rpcClient):
                return cls.rpc_client.call_service(service_plugin, func_name or func.__name__, *args, **kwargs)
            return result

        return wrapper

    return decorator
