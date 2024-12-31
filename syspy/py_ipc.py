import json
from typing import Optional, Type, TypeVar, Generic
from .lib.rpc_client import rpcClient
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class Service:
    default_plugin = None
    rpc_client = rpcClient()


class Message(Generic[T], Service):
    """
    Attributes:
      _TOPIC (str): 消息名
      _PLUGIN (str): 插件名
      _MODEL_CLASS (Type[T]): Pydantic模型类
    """
    _TOPIC = None
    _PLUGIN = "RBKSim"
    _MODEL_CLASS: Type[T]

    data: Optional[T] = None

    @classmethod
    def get_data(cls) -> Optional[T]:
        return cls.data

    @classmethod
    def update(cls):
        """刷新状态"""
        response = cls.rpc_client.get_message(cls._TOPIC, cls._PLUGIN)
        # print("parsed_data", response)
        if response:
            try:
                parsed_data = json.loads(response)
                cls.data = cls._MODEL_CLASS(**parsed_data)
                # parsed_data = json.loads(response)
                # cls._parse_response(response)
            except Exception as e:
                print(f"Error parsing response: {e}")
