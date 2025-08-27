import logging
from typing import Dict, List
from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.lib.plyvel_db import LevelDBInterface

log = logging.getLogger("rbk.script")

@default_plugin("LevelDB")
class LevelDBV3(LevelDBInterface):
    """提供LevelDB数据库的操作接口"""
    def __init__(self, name):
        """初始化LevelDB实例。

        Args:
            name (str): 数据库的名称。
        """
        super().__init__(name)
        self.name = name
        # 初始化数据库
        self.__initDB(name)

    @classmethod
    @call_service(func_name="initDB")
    def __initDB(cls, name: str):
        """初始化数据库

        Args:
            name (str): 数据库的名称。
        """
        pass

    def put(self, key: str, value: str):
        """向数据库中插入一条键值对。

        Args:
            key (str): 键。
            value (str): 值。
        """
        return self.client().call_service("LevelDB", "putValue", self.name, key, value)

    def puts(self, key_value_maps: Dict[str, str]):
        """批量向数据库中插入键值对。

        Args:
            key_value_maps (Dict[str, str]): 包含多条键值对的字典。
        """
        return self.client().call_service("LevelDB", "putValues", self.name, key_value_maps)

    def get(self, key: str):
        """从数据库中获取指定键的值。

        Args:
            key (str): 键。
        """
        return self.client().call_service("LevelDB", "getValue", self.name, key)

    def gets(self, keys: List[str]):
        """批量从数据库中获取指定键的值。

        Args:
            keys (List[str]): 键的列表。
        """
        return self.client().call_service("LevelDB", "getValues", self.name, keys)

    def delete(self, key: str):
        """从数据库中删除指定键的值。

        Args:
            key (str): 键。
        """
        self.client().call_service("LevelDB", "delValue", self.name, key)
