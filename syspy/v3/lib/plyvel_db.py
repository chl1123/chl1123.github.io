import logging
from typing import Dict, List, Union
from syspy.core.rbk_rpc import default_plugin, call_service
from syspy.lib.plyvel_db import LevelDBInterface

log = logging.getLogger("rbk.script")

@default_plugin("LevelDB")
class LevelDBV3(LevelDBInterface):
    """提供LevelDB数据库的操作接口"""
    def __init__(self, name):
        super().__init__(name)
        self.name = name
        # 初始化数据库
        self.__initDB(name)

    @classmethod
    @call_service(func_name="initDB")
    def __initDB(cls, name: str):
        pass

    def add(self, key: str, value: Union[str, int, float], isProtected: bool = False):
        # 判断value的类型
        if isinstance(value, str):
            return self.client().call_service("LevelDB", "addValueString", self.name, key, value, isProtected)
        elif isinstance(value, int):
            return self.client().call_service("LevelDB", "addValueInt", self.name, key, value, isProtected)
        elif isinstance(value, float):
            return self.client().call_service("LevelDB", "addValueFloat", self.name, key, value, isProtected)
        else:
            raise TypeError("value must be 'str', 'int' or 'float'")

    def put(self, key: str, value: Union[str, int, float]):
        if isinstance(value, str):
            return self.client().call_service("LevelDB", "putValueString", self.name, key, value)
        elif isinstance(value, int):
            return self.client().call_service("LevelDB", "putValueInt", self.name, key, value)
        elif isinstance(value, float):
            return self.client().call_service("LevelDB", "putValueFloat", self.name, key, value)
        else:
            raise TypeError("value must be 'str', 'int' or 'float'")

    def puts(self, key_value_maps: Dict[str, str]):
        return self.client().call_service("LevelDB", "putValues", self.name, key_value_maps)

    def get(self, key: str, value_type: str = "str"):
        if value_type in ["str", "string"]:
            return self.client().call_service("LevelDB", "getValueString", self.name, key)
        elif value_type == "int":
            return self.client().call_service("LevelDB", "getValueInt", self.name, key)
        elif value_type == "float":
            return self.client().call_service("LevelDB", "getValueFloat", self.name, key)
        else:
            raise TypeError("value_type must be 'str', 'int' or 'float'")

    def gets(self, keys: List[str]):
        return self.client().call_service("LevelDB", "getValues", self.name, keys)

    def delete(self, key: str):
        self.client().call_service("LevelDB", "delValue", self.name, key)
