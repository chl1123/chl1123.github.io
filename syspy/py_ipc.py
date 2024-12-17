import json
import sys
sys.path.append('/opt/.data/rbk/resources/scripts/')
from syspy.lib.rpc_client import rpcClient

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

    def __init__(self, topic: str, plugin: str = "RBKSim"):
        self.rpc_client = rpcClient()
        response = self.rpc_client.get_message(topic, plugin)
        # 解析响应并设置成员变量
        self.parse_response(response)

    def parse_response(self, response):
        # print("response", response)
        data = json.loads(response)
        # print("data: ", data)
        for key, value in data.items():
            mapped_key = self._key_to_attribute.get(key, key)
            setattr(self, mapped_key, value)