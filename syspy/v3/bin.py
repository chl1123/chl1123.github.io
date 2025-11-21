import ast
from typing import List, TYPE_CHECKING
from syspy.bin import BinInterface, ContainerInterface
from syspy.v3.lib.plyvel_db import LevelDBV3
from syspy.v3.navigation import NavigationV3
from syspy.core.rbk_rpc import call_service, default_plugin


@default_plugin("RecoFactory")
class BinV3(BinInterface):
    """库位类"""

    _TOPIC = "rbk.protocol.msgBins"
    _PLUGIN = "RecoFactory"
    _MODEL_CLASS = None
    if TYPE_CHECKING:
        from .protobuf import msgBins, msgBin  # IDE类型提示
        data: msgBins = None

    @classmethod
    def init_model_class(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgBins
            cls._MODEL_CLASS = msgBins

    def get_bins(cls) -> List["msgBin"]:
        if cls.update():
            return cls.data.bins

    @classmethod
    @call_service()
    def binDetection(cls, seq: int):
        """库位检测

        Args:
            seq (int): 时间戳
        """
        pass


class ContainerV3(ContainerInterface):
    """背篓类，用于管理机器人上的背篓及货物状态。

    Attributes:
        containers (dict): 存储所有背篓及货物的状态，key为背篓名称，值为包含 goods_name、desc 和 has_goods 的字典。
    """

    db = None
    containers = {}

    @staticmethod
    def _empty_container():
        return {
            "goodsName": "",
            "desc": "",
            "hasGoods": False
        }

    @classmethod
    def init_container(cls, number: int = 7):
        """初始化背篓数据。

        Args:
            number (str): 背篓数量。从模型中的moduleType.cartonTransferUnit.id参数获取
        """
        cls.db = LevelDBV3("containers")
        model_containers = []
        for i in range(number):
            model_containers.append(str(i))
        model_containers.append("999")
        raw_data = cls.db.gets(model_containers)
        for container_id, value in zip(model_containers, raw_data):
            if value is None:
                cls.containers[container_id] = cls._empty_container()
            else:
                try:
                    cls.containers[container_id] = ast.literal_eval(value)
                except (SyntaxError, ValueError):
                    cls.containers[container_id] = cls._empty_container()

    @classmethod
    def setContainer(cls, container_id: str, goods_name: str, desc: str) -> bool:
        """设置车子上库位或者背篓货物

        Args:
            container_id (str): 库位或者背篓id
            goods_name (str): 货物名
            desc (str): 货物描述

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        cls.containers[container_id] = {
            "goodsName": goods_name,
            "desc": desc,
            "hasGoods": True
        }
        return cls.db.put(container_id, str(cls.containers[container_id]))

    @classmethod
    def clearContainer(cls, container_id: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            container_id (str): 库位或者背篓id，container_id如果为"All"则全部清除

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        if container_id == "All":
            for key in cls.containers:
                cls.containers[key] = cls._empty_container()
            # 对cls.containers每一个的value都转为str
            str_containers = {key: str(cls.containers[key]) for key in cls.containers}
            cls.db.puts(str_containers)
            return True
        else:
            if container_id in cls.containers:
                cls.containers[container_id] = cls._empty_container()
                cls.db.put(container_id, str(cls._empty_container))
                return True
            return False

    @classmethod
    def clearContainerByGoods(cls, goods_name: str) -> bool:
        """清除车上特定库位或者背篓的状态

        Args:
            goods_name (str): 货物名称，货物名称如果为All则全部清除

        Returns:
            (bool): 如果没有库位或者背篓，则返回false
        """
        if goods_name == "All":
            for key in cls.containers:
                cls.containers[key] = cls._empty_container()
            str_containers = {key: str(cls.containers[key]) for key in cls.containers}
            return cls.db.puts(str_containers)
        else:
            for key in cls.containers:
                if cls.containers[key]["goodsName"] == goods_name:
                    cls.containers[key] = cls._empty_container()
                    cls.db.put(key, str(cls._empty_container))
                    return True
            return False

    @classmethod
    def getContainers(cls) -> list:
        """获取当前车子上库位或者背篓货物的状态。

        Returns:
            （list): 包含所有背篓状态的列表，每个元素是一个字典，包含 container_id、goods_name、desc 和 has_goods。
        """
        containers = []
        for c in cls.containers:
            cls.containers[c]["containerId"] = c
            containers.append(cls.containers[c])
        return containers

    @classmethod
    def has_goods(cls, container_id: str = '0') -> bool:
        """检查指定背篓是否包含货物。

        Args:
            container_id (str): 背篓id，默认为 '0'。

        Returns:
            (bool): 如果背篓中有货物，则返回True；否则返回False。
        """
        if container_id in cls.containers:
            return cls.containers[container_id].get("hasGoods", False)
        return False

    @classmethod
    def goods_exist(cls, goods_name) -> bool:
        """检查指定的货物是否存在。

        Args:
            goods_name (str): 要检查的货物名。

        Returns:
            (bool): 如果存在该货物，则返回True；否则返回False。
        """
        for c in cls.containers:
            if goods_name == cls.containers[c]["goodsName"]:
                return True
        return False

    @classmethod
    def get_task_goods(cls):
        """从任务参数中获取货物ID。

        Returns:
            (str): 货物ID，如果没有找到则返回空字符串。
        """
        move_task = NavigationV3.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsName':
                return p["stringValue"]
        return ""

    @classmethod
    def get_goods_by_container(cls, container_id: str = '0') -> str:
        """根据背篓名称获取对应的货物ID。

        Args:
            container_id (str): 背篓id，默认为 '0'。

        Returns:
            (str): 货物ID，如果找不到则返回空字符串。
        """
        if container_id in cls.containers:
            return cls.containers[container_id].get("goodsName", "")

    @classmethod
    def get_container_by_goods(cls, goods_name) -> str:
        """根据货物名查找其所在的背篓。

        Args:
            goods_name (str): 要查找的货物名。

        Returns:
            (str): 找到的背篓名称，如果没有找到或货物未装载，则返回空字符串。
        """
        for c in cls.containers:
            if goods_name == cls.containers[c]["goodsName"] and cls.containers[c]["hasGoods"]:
                return cls.containers[c]["containerId"]
        return ""

    @classmethod
    def get_json_containers(cls) -> dict:
        """以原始格式返回所有背篓的状态。

        Returns:
            (dict): key为背篓名称，值为包含 goods_name、desc 和 has_goods 的字典。
        """
        return cls.containers