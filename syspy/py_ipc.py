import json
from .lib.rpc_client import rpcClient

class Status:
    """
    Attributes:
      _TOPIC (dict): 消息名
      _key_to_attribute (dict):
        key: 原始proto转json的属性名
        value: 封装的Python类属性名
    """
    _TOPIC = None
    _key_to_attribute = None
    _PLUGIN = "RBKSim"
    _data = None
    rpc_client = rpcClient()

    @classmethod
    def get_data(cls):
        return cls._data

    def __init__(self):
        self.update()

    @classmethod
    def __parse_response(cls, response):
        # print("response", response)
        data = json.loads(response)
        cls._data = data
        # print("data: ", data)
        for key, value in data.items():
            mapped_key = cls._key_to_attribute.get(key, key)
            setattr(cls, mapped_key, value)

    @classmethod
    def update(cls):
        """刷新状态"""
        response = cls.rpc_client.get_message(cls._TOPIC, cls._PLUGIN)
        cls.__parse_response(response)