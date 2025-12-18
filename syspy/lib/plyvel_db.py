import logging
import time
from abc import ABC
from typing import Dict, List, Type, Union
from syspy.core.rbk_rpc import Service, RBKVersionError

log = logging.getLogger("rbk.script")

class LevelDBInterface(ABC, Service):
    """提供LevelDB数据库的操作接口"""
    def __init__(self, name):
        """初始化LevelDB实例。

        Args:
            name (str): 数据库的名称。
        """
        ...

    @classmethod
    def __initDB(cls, name: str):
        """初始化数据库

        Args:
            name (str): 数据库的名称。
        """
        raise RBKVersionError()

    def add(self, key: str, value: Union[str, int, float], isProtected: bool = False):
        """向数据库中增加键值对（支持增加私有字段）。

        Args:
            key (str): 键。
            value (Union[str, int, float]): 值。
            isProtected (bool): 是否受保护（不能通过 Roboshop 清空）。默认不保护。
        """
        raise RBKVersionError()

    def put(self, key: str, value: Union[str, int, float]):
        """向数据库中插入一条键值对。

        Args:
            key (str): 键。
            value (Union[str, int, float]): 值。
        """
        raise RBKVersionError()

    def puts(self, key_value_maps: Dict[str, str]):
        """批量向数据库中插入键值对。

        Args:
            key_value_maps (Dict[str, str]): 包含多条键值对的字典。
        """
        raise RBKVersionError()

    def get(self, key: str, value_type: str = "str"):
        """从数据库中获取指定键的值。

        Args:
            key (str): 键。
            value_type (str): 值的类型，支持填入 'str', 'int' or 'float'
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
    # 创建 containers 数据库
    container_db = LevelDB("containers")

    # 创建运行信息数据库实例，名字必须为 "run"
    runDb = LevelDB("run")
    # 增加数据示例
    runDb.add("jack1", "123", False)  # 增加 jack1 字段、值为"123"、str类型、不受保护（可以通过 Roboshop 清空）
    runDb.add("jack2", 3, False)  # 增加 jack2 字段、值为 3、int类型、不受保护（可以通过 Roboshop 清空）
    runDb.add("jack3", 3.14, True)  # 增加 jack3 字段、值为 3.14、float类型、受保护（不能通过 Roboshop 清空）
    jack1 = runDb.get("jack1", "str")  # 获取 jack1 的值，str类型
    jack2 = runDb.get("jack2", "int")  # 获取 jack2 的值，int类型
    jack3 = runDb.get("jack3", "float")  # 获取 jack3 的值，float类型
    print(f"{type(jack1)}, {jack1=}")
    print(f"{type(jack2)}, {jack2=}")
    print(f"{type(jack3)}, {jack3=}")

    while True:
        """container_db"""
        # 插入、获取和删除数据的示例
        print(container_db.put('key1', "123"))
        print(container_db.put('key2', "123"))
        print("db.get('key1'):", container_db.get('key1'))
        print("db.get('key2'):", container_db.get('key2'))

        # 批量插入和获取数据的示例
        print(container_db.puts(
            {
                'key4': 'value4',
                'key5': 'value5',
            }))
        print("db.gets('key4', 'key5'):", container_db.gets(["key4", "key5"]))

        # 删除数据的示例
        container_db.delete('key1')
        print("db.get('key1'):", container_db.get('key1'))

        """runDb"""
        # 修改数据示例
        runDb.put("jack1", "456")  # 修改 jack1 的值，值为"456"
        runDb.put("jack2", 4)  # 修改 jack2 的值，值为 4
        runDb.put("jack3", 4.25)  # 修改 jack3 的值，值为 4.25

        # 获取数据示例
        jack1 = runDb.get("jack1", "str")  # 获取 jack1 的值，str类型
        jack2 = runDb.get("jack2", "int")  # 获取 jack2 的值，int类型
        jack3 = runDb.get("jack3", "float")  # 获取 jack3 的值，float类型
        print(f"{type(jack1)}, {jack1=}")
        print(f"{type(jack2)}, {jack2=}")
        print(f"{type(jack3)}, {jack3=}")

        # 删除数据示例
        runDb.delete("jack1")
        runDb.delete("jack2")
        runDb.delete("jack3")

        # 获取数据
        jack1 = runDb.get("jack1", "str")
        jack2 = runDb.get("jack2", "int")
        jack3 = runDb.get("jack3", "float")
        print(f"{type(jack1)}, {jack1=}")
        print(f"{type(jack2)}, {jack2=}")
        print(f"{type(jack3)}, {jack3=}")
        print()
        # 暂停1秒
        time.sleep(1)
