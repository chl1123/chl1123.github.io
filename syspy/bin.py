import ast
from typing import List, TYPE_CHECKING

from syspy.lib.plyvel_db import LevelDB
from syspy.navigation import Navigation
from .lib.py_rpc import Message

if TYPE_CHECKING:
    from .protobuf import Message_Bin  # IDE类型提示


class Bin(Message["Message_Bins"]):
    """库位类"""

    _TOPIC = "rbk.protocol.Message_Bins"
    _PLUGIN = "RecoFactory"
    _MODEL_CLASS = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import Message_Bins
            cls._MODEL_CLASS = Message_Bins

    @classmethod
    def get_bins(cls) -> List["Message_Bin"]:
        if cls.update():
            return cls.data.bins


class Container:
    """背篓类，用于管理机器人上的背篓及货物状态。

    Attributes:
        containers (dict): 存储所有背篓及货物的状态，key为背篓名称，值为包含 goods_id、desc 和 has_goods 的字典。
    """

    db = LevelDB("containers")
    containers = {}

    @staticmethod
    def _empty_container():
        return {
            "goods_id": "",
            "desc": "",
            "has_goods": False
        }

    @classmethod
    def init_container_data(cls):
        model_container_names = []
        # todo 从模型文件中获取背篓名称
        raw_data = cls.db.gets(model_container_names)
        for name, value in zip(model_container_names, raw_data):
            if value is None:
                cls.containers[name] = cls._empty_container()
            else:
                try:
                    cls.containers[name] = ast.literal_eval(value)
                except (SyntaxError, ValueError):
                    cls.containers[name] = cls._empty_container()

    @classmethod
    def setContainer(cls, container_name: str, goods_id: str, desc: str) -> bool:
        """设置车子上库位或者背篓货物

        Args:
            container_name (str): 库位或者背篓名称
            goods_id (str): 货物的id
            desc (str): 描述

        Returns:
            bool: 如果没有库位或者背篓，则返回false
        """
        cls.containers[container_name] = {
            "goods_id": goods_id,
            "desc": desc,
            "has_goods": True
        }
        return cls.db.put(container_name, str(cls.containers[container_name]))

    @classmethod
    def clearContainer(cls, container_name: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            container_name (str): 库位或者背篓名称，container_name如果为"All"则全部清除

        Returns:
            bool: 如果没有库位或者背篓，则返回false
        """
        if container_name == "All":
            for key in cls.containers:
                cls.containers[key] = cls._empty_container()
            # 对cls.containers每一个的value都转为str
            str_containers = {key: str(cls.containers[key]) for key in cls.containers}
            cls.db.puts(str_containers)
            return True
        else:
            if container_name in cls.containers:
                cls.containers[container_name] = cls._empty_container()
                cls.db.put(container_name, str(cls._empty_container))
                return True
            return False

    @classmethod
    def clearContainerByGoodsId(cls, goods_id: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            goods_id (str): 货物名称，货物名称如果为All则全部清除
        Returns:
            bool: 如果没有库位或者背篓，则返回false
        """
        if goods_id == "All":
            for key in cls.containers:
                cls.containers[key] = cls._empty_container()
            str_containers = {key: str(cls.containers[key]) for key in cls.containers}
            return cls.db.puts(str_containers)
        else:
            for key in cls.containers:
                if cls.containers[key]["goods_id"] == goods_id:
                    cls.containers[key] = cls._empty_container()
                    cls.db.put(key, str(cls._empty_container))
                    return True
            return False

    @classmethod
    def getContainers(cls) -> list:
        """获取当前车子上库位或者背篓货物的状态。

        Returns:
            list: 包含所有背篓状态的列表，每个元素是一个字典，包含 container_name、goods_id、desc 和 has_goods。
        """
        containers = []
        for c in cls.containers:
            cls.containers[c]['container_name'] = c
            containers.append(cls.containers[c])
        return containers

    @classmethod
    def has_goods(cls, container_name: str = '0') -> bool:
        """检查指定背篓是否包含货物。

        Args:
            container_name (str): 背篓名称，默认为 '0'。

        Returns:
            bool: 如果背篓中有货物，则返回True；否则返回False。
        """
        if container_name in cls.containers:
            return cls.containers[container_name].get("has_goods", False)
        return False

    @classmethod
    def goods_id_exist(cls, goods_id) -> bool:
        """检查指定的货物ID是否存在。

        Args:
            goods_id (str): 要检查的货物ID。

        Returns:
            bool: 如果存在该货物ID，则返回True；否则返回False。
        """
        for c in cls.containers:
            if goods_id == cls.containers[c]['goods_id']:
                return True
        return False

    @classmethod
    def get_task_goodsId(cls):
        """从任务参数中获取货物ID。

        Returns:
            str: 货物ID，如果没有找到则返回空字符串。
        """
        move_task = Navigation.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsId':
                return p['string_value']
        return ""

    @classmethod
    def get_goodsId_by_container(cls, container_name: str = '0') -> str:
        """根据背篓名称获取对应的货物ID。

        Args:
            container_name (str): 背篓名称，默认为 '0'。

        Returns:
            str: 货物ID，如果找不到则返回空字符串。
        """
        if container_name in cls.containers:
            return cls.containers[container_name].get("goods_id", "")

    @classmethod
    def get_container_by_goodsId(cls, goods_id) -> str:
        """根据货物ID查找其所在的背篓名称。

        Args:
            goods_id (str): 要查找的货物ID。

        Returns:
            str: 找到的背篓名称，如果没有找到或货物未装载，则返回空字符串。
        """
        for c in cls.containers:
            if goods_id == cls.containers[c]['goods_id'] and cls.containers[c]['has_goods']:
                return cls.containers[c]['container_name']
        return ""

    @classmethod
    def get_json_containers(cls) -> dict:
        """以原始格式返回所有背篓的状态。

        Returns:
            dict: key为背篓名称，值为包含 goods_id、desc 和 has_goods 的字典。
        """
        return cls.containers


if __name__ == '__main__':
    Container.init_container_data()
    print("init data", Container.getContainers())
    Container.setContainer("0", "0", "c0")
    Container.setContainer("1", "1", "c1")
    Container.setContainer("2", "2", "c2")
    print("getContainers 0 1 2: ", Container.getContainers())

    Container.clearContainer("0")
    print("clearContainer 0: ", Container.getContainers())
    Container.clearContainer("All")
    print("clearContainer All: ", Container.getContainers())

    Container.setContainer("0", "0", "c0")
    Container.setContainer("1", "1", "c1")
    Container.setContainer("2", "2", "c2")
    print("setContainer 0 1 2: ", Container.getContainers())

    Container.clearContainerByGoodsId("1")
    print("clearContainerByGoodsId 1: ", Container.getContainers())

    Container.clearContainerByGoodsId("All")
    print("clearContainerByGoodsId All: ", Container.getContainers())

    Container.setContainer("0", "0", "c0")
    Container.setContainer("1", "1", "c1")
    Container.setContainer("2", "2", "c2")
    print("setContainer 0 1 2: ", Container.getContainers())

    print("has_goods() 0", Container.has_goods("0"))
    print("has_goods() -1", Container.has_goods("-1"))
    print("goods_id_exist() 0", Container.goods_id_exist("0"))
    print("goods_id_exist() -1", Container.goods_id_exist("-1"))
    print("get_task_goodsId()", Container.get_task_goodsId())
    print("get_goodsId_by_container()", Container.get_goodsId_by_container("0"))
    print("get_goodsId_by_container()", Container.get_goodsId_by_container("-1"))
    print("get_container_by_goodsId()", Container.get_container_by_goodsId("1"))
    print("get_container_by_goodsId()", Container.get_container_by_goodsId("-1"))
    print("get_json_containers()", Container.get_json_containers())
