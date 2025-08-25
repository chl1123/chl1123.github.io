import logging
import time
from abc import ABC
from typing import Dict, List, Type
from syspy.core.rbk_rpc import Service, RBKVersionError

log = logging.getLogger("rbk.script")

class LevelDBInterface(ABC, Service):
    """提供LevelDB数据库的操作接口"""
    def __init__(self, name):
        """初始化LevelDB实例。

        Args:
            name (str): 数据库的名称。
        """
        raise RBKVersionError()

    @classmethod
    def __initDB(cls, name: str):
        """初始化数据库

        Args:
            name (str): 数据库的名称。
        """
        raise RBKVersionError()

    def put(self, key: str, value: str):
        """向数据库中插入一条键值对。

        Args:
            key (str): 键。
            value (str): 值。
        """
        raise RBKVersionError()

    def puts(self, key_value_maps: Dict[str, str]):
        """批量向数据库中插入键值对。

        Args:
            key_value_maps (Dict[str, str]): 包含多条键值对的字典。
        """
        raise RBKVersionError()

    def get(self, key: str):
        """从数据库中获取指定键的值。

        Args:
            key (str): 键。
        """
        raise RBKVersionError()

    def gets(self, keys: List[str]):
        """批量从数据库中获取指定键的值。

        Args:
            keys (List[str]): 键的列表。
        """
        raise RBKVersionError()

    def delete(self, key: str):
        """从数据库中删除指定键的值。

        Args:
            key (str): 键。
        """
        raise RBKVersionError()


from syspy import RBK_VERSION
if RBK_VERSION == 3:
    from syspy.v3.lib.plyvel_db import LevelDBV3
    LevelDB: Type[LevelDBInterface] = LevelDBV3
elif RBK_VERSION == 4:
    from syspy.v4.lib.plyvel_db import LevelDBV4
    LevelDB: Type[LevelDBInterface] = LevelDBV4
else:
    raise ValueError(f"Unsupported RBK version: {RBK_VERSION}")


# 示例使用方法
if __name__ == '__main__':
    # 创建LevelDB实例
    db = LevelDB("containers")
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
