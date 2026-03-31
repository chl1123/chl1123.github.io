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
    def initModelClass(cls):
        if cls._MODEL_CLASS is None:
            from .protobuf import msgBins
            cls._MODEL_CLASS = msgBins

    def getBins(self) -> List["msgBin"]:
        if self.update():
            return self.data.bins

    @classmethod
    @call_service()
    def binDetection(cls, seq: int):
        """库位检测

        Args:
            seq (int): 时间戳
        """
        pass


class ContainerV3(ContainerInterface):
    """容器类"""

    db = None
    containers = {}

    @staticmethod
    def _emptyContainer():
        return {
            "goodsName": "",
            "desc": "",
            "hasGoods": False
        }

    @classmethod
    def initContainer(cls, number: int = 0):
        cls.db = LevelDBV3("containers")
        model_containers = []
        for i in range(number):
            model_containers.append(str(i))
        model_containers.append("999")
        raw_data = cls.db.gets(model_containers)
        for container_id, value in zip(model_containers, raw_data):
            if value is None:
                cls.containers[container_id] = cls._emptyContainer()
            else:
                try:
                    cls.containers[container_id] = ast.literal_eval(value)
                except (SyntaxError, ValueError):
                    cls.containers[container_id] = cls._emptyContainer()

    @classmethod
    def bindContainer(cls, container_id: str, goods_name: str, desc: str) -> bool:
        cls.containers[container_id] = {
            "goodsName": goods_name,
            "desc": desc,
            "hasGoods": True
        }
        return cls.db.put(container_id, str(cls.containers[container_id]))

    @classmethod
    def unbindContainer(cls, container_id: str = "", goods_name: str = "") -> bool:
        result = False
        if not container_id and not goods_name:
            for key in cls.containers:
                cls.containers[key] = cls._emptyContainer()
                # 对cls.containers每一个的value都转为str
                str_containers = {key: str(cls.containers[key]) for key in cls.containers}
                cls.db.puts(str_containers)
            result = True
        elif container_id:
            if container_id in cls.containers:
                cls.containers[container_id] = cls._emptyContainer()
                cls.db.put(container_id, str(cls._emptyContainer()))
                result = True
        elif goods_name:
            for key in cls.containers:
                if cls.containers[key]["goodsName"] == goods_name:
                    cls.containers[key] = cls._emptyContainer()
                    cls.db.put(key, str(cls._emptyContainer()))
                    result = True
        # 如果所有容器都没有货物，则清除货物形状
        if all(not cls.containers[key]["hasGoods"] for key in cls.containers):
            NavigationV3.clearGoodsShape()
        return result

    @classmethod
    def getContainers(cls) -> list:
        containers = []
        for c in cls.containers:
            cls.containers[c]["containerId"] = c
            containers.append(cls.containers[c])
        return containers

    @classmethod
    def hasGoods(cls, container_id: str = '0') -> bool:
        if container_id in cls.containers:
            return cls.containers[container_id].get("hasGoods", False)
        return False

    @classmethod
    def goodsExist(cls, goods_name) -> bool:
        for c in cls.containers:
            if goods_name == cls.containers[c]["goodsName"]:
                return True
        return False

    @classmethod
    def getTaskGoods(cls):
        move_task = NavigationV3.moveTask()
        for p in move_task['params']:
            if p['key'] == 'goodsName':
                return p["stringValue"]
        return ""

    @classmethod
    def getGoodsByContainer(cls, container_id: str = '0') -> str:
        if container_id in cls.containers:
            return cls.containers[container_id].get("goodsName", "")

    @classmethod
    def getContainerByGoods(cls, goods_name) -> str:
        for c in cls.containers:
            if goods_name == cls.containers[c]["goodsName"] and cls.containers[c]["hasGoods"]:
                return cls.containers[c]["containerId"]
        return ""

    @classmethod
    def getJsonContainers(cls) -> dict:
        return cls.containers