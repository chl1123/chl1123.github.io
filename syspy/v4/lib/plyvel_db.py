import logging
import time
from abc import ABC
from typing import Dict, List
from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.lib.plyvel_db import LevelDBInterface

log = logging.getLogger("rbk.script")

# todo RBK4: 增加LevelDB方法
@default_plugin("LevelDB")  # todo RBK4
class LevelDBV4(LevelDBInterface):
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


# 示例使用方法
if __name__ == '__main__':
    # 创建LevelDB实例
    db = LevelDBV4("containers")
    while True:
        # 插入、获取和删除数据的示例
        print(db.put('key1', "123"))
        print(db.put('key2', "123"))
        print("db.get('key1'):", db.get('key1'))
        print("db.get('key2'):", db.get('key2'))

        # 批量插入和获取数据的示例
        print(db.puts(
            {
              'key4': 'value4',
              'key5': 'value5',
            }))
        print("db.gets('key4', 'key5'):", db.gets(["key4", "key5"]))

        # 删除数据的示例
        db.delete('key1')
        print("db.get('key1'):", db.get('key1'))
        # 暂停1秒
        time.sleep(1)
